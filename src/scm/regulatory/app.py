"""Existing Module02 library: research candidates and verified local original excerpts."""

import json
import os
from collections import defaultdict
from pathlib import Path

import streamlit as st
from sqlalchemy import select

from scm.database.session import session_factory
from scm.regulatory.manifest import input_status
from scm.regulatory.models import RegulationChunk, RegulationDocument
from scm.regulatory.retrieval import answer
from scm.regulatory.storage import checked_path
from scm.settings import ROOT

st.set_page_config(page_title="ESCIM Module02｜法规资料库", layout="wide")
st.title("ESCIM Module02｜法规资料库与原文检索")
research = Path(os.getenv("SCM_REGULATORY_RESEARCH", str(ROOT / "data/regulatory/research")))
inputs = input_status(research)
if not all(x["present"] for x in inputs):
    st.warning("调研输入尚未齐备；不生成替代目录，不提供AI法律结论。")
else:
    st.info("调研文件已找到；候选/页面核实状态保留，不等于当前法律适用已核实。")
with st.expander("输入资料检查", expanded=not all(x["present"] for x in inputs)):
    for item in inputs:
        st.write(item["name"] + "：" + ("已找到" if item["present"] else "BLOCKED · 未找到"))
url = os.getenv("SCM_REGULATORY_DATABASE_URL", "sqlite:///runtime/regulatory/library.db")
root = Path(os.getenv("SCM_REGULATORY_STORAGE", str(ROOT / "runtime/regulatory/files")))
factory = session_factory(url)
with factory() as session:
    rows = [
        r for r in session.scalars(select(RegulationDocument)) if r.verification_type in [None, "LIVE_HTTP"]
    ]
    all_rows = rows
    query = st.text_input("搜索法规编号、名称或主题")
    snapshot_path = Path(
        os.getenv("SCM_REGULATORY_SNAPSHOT", str(ROOT / "runtime/regulatory/research-snapshot.json"))
    )
    if all(x["present"] for x in inputs) and snapshot_path.is_file():
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        with st.expander(f"研究主目录 · {len(snapshot['catalog'])}条候选", expanded=False):
            records = []
            for c in snapshot["catalog"]:
                if query and query.casefold() not in " ".join(str(v) for v in c.values()).casefold():
                    continue
                docs = [r for r in all_rows if json.loads(r.metadata_json)["celex"] == c.get("CELEX")]
                records.append(
                    {
                        "法规": c["法规/规则编号"],
                        "优先级": c["优先级"],
                        "主题": c["主题"],
                        "Work原核实级别": c["核实级别"],
                        "Work原下载状态": c["下载状态"],
                        "本地原文状态": "已下载"
                        if any(r.download_status == "downloaded" for r in docs)
                        else "未下载/候选",
                        "当前法律状态": "待核实",
                    }
                )
            st.dataframe(records, hide_index=True)
    rows = [
        r
        for r in rows
        if not query
        or query.casefold()
        in " ".join(
            str(v) for k, v in json.loads(r.metadata_json).items() if k != "research_metadata"
        ).casefold()
    ]
    st.caption(f"可见文档/版本记录 {len(rows)}；有文件不等于法律状态已核实。")
    if not rows:
        st.info("暂无匹配的真实法规文档；未创建推测目录，筛选或知识库未覆盖时不编造法律依据。")
        st.text_input("中文问题（知识库为空时只返回证据不足）", key="empty_question")
        if st.button("检索原文证据"):
            st.warning("证据不足：尚无已下载并解析的法规原文。")
    else:
        by_id = {r.id: r for r in rows}

        def version_label(id):
            m = json.loads(by_id[id].metadata_json)
            return " | ".join(
                [
                    m["regulation_number"],
                    m["version_kind"],
                    str(m.get("version_date") or m.get("publication_date") or "日期待核实"),
                    m["format"],
                ]
            )

        selected = st.selectbox(
            "选择法规与精确版本", list(by_id), format_func=version_label, key="reg_document"
        )
        row = by_id[selected]
        meta = json.loads(row.metadata_json)
        st.write(
            "下载：" + row.download_status + "；解析：" + row.parse_status + "；法律效力/适用日期：待核实"
        )
        st.caption(
            "整合文本仅作阅读便利，不是独立法源。原始OJ快照也不自动代表现行已修订要求。无LLM：本地检索与原文摘录，不是AI法律分析。"
        )
        with st.expander("元数据与研究原核实状态"):
            st.json(meta)
        st.link_button("官方原文记录", meta["official_url"])
        if row.download_status == "downloaded":
            try:
                path = checked_path(row, root)
                mime = {"pdf": "application/pdf", "html": "text/html", "xml": "application/xml"}[
                    meta["format"]
                ]
                st.download_button("打开/下载已校验原文", path.read_bytes(), file_name=path.name, mime=mime)
                st.caption("SHA256：" + row.sha256 + "；字节：" + str(row.byte_size))
            except ValueError:
                st.error("本地原文缺失或哈希不符，已停止引用。")
        chunks = list(
            session.scalars(
                select(RegulationChunk)
                .where(RegulationChunk.document_id == selected)
                .order_by(RegulationChunk.ordinal)
            )
        )
        with st.expander("Article / Annex结构"):
            grouped = defaultdict(list)
            for c in chunks:
                grouped[(c.unit_type, c.unit_label)].append(c)
            st.dataframe(
                [
                    {
                        "单元": kind + " " + label,
                        "检索片段数": len(items),
                        "起始页": min((x.page_start for x in items if x.page_start), default=None),
                        "结束页": max((x.page_end for x in items if x.page_end), default=None),
                        "核实": "待复核；表格/附件不能仅凭提取文本认定",
                    }
                    for (kind, label), items in grouped.items()
                ],
                hide_index=True,
            )
        question = st.text_input("中文问题", key="reg_question")
        if st.button("检索原文证据", key="reg_search"):
            result = answer(session, question, selected, root)
            st.write(result["answer_zh"])
            st.caption(result["direct_requirements"])
            st.caption(result["indirect_electrolyte_impact"])
            for e in result["evidence"]:
                st.markdown(f"**{e['unit_type']} {e['unit_label']} · {e['celex']}**")
                st.code(e["quote"], language=None)
                st.caption(
                    f"原文页码 {e['page_start']}–{e['page_end']} | 版本 {e['version_kind']} / {e['version_date'] or '未知'} | "
                    + e["source_sha256"]
                    + " | "
                    + str(e["quality_flags"])
                )
                st.link_button("打开引用原文页", e["citation_url"], key="cite-" + str(e["chunk_id"]))
