"""Separate Module02 foundation UI; existing Module01 and six-page app untouched."""

import json
import os
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
st.title("ESCIM Module02｜法规资料库与检索基础设施")
st.warning("基础设施阶段：五份调研资料尚未接入；未完成真实法规闭环，不提供AI法律结论。")
research = Path(os.getenv("SCM_REGULATORY_RESEARCH", str(ROOT / "data/regulatory/research")))
with st.expander("输入资料检查", expanded=True):
    for item in input_status(research):
        st.write(item["name"] + "：" + ("已找到（未自动导入）" if item["present"] else "BLOCKED · 未找到"))
url = os.getenv("SCM_REGULATORY_DATABASE_URL", "sqlite:///runtime/regulatory/library.db")
root = Path(os.getenv("SCM_REGULATORY_STORAGE", str(ROOT / "runtime/regulatory/files")))
factory = session_factory(url)
with factory() as session:
    rows = list(session.scalars(select(RegulationDocument)))
    # Synthetic/mock artifacts are never listed as Live source documents.
    rows = [r for r in rows if r.verification_type in [None, "LIVE_HTTP"]]
    query = st.text_input("搜索法规编号、名称或主题")
    rows = [
        r
        for r in rows
        if not query
        or query.casefold() in " ".join(str(v) for v in json.loads(r.metadata_json).values()).casefold()
    ]
    st.caption(f"可见目录记录 {len(rows)}；有文件不等于法律状态已核实。")
    if not rows:
        st.info("暂无已导入的真实法规目录。请先提供调研文件；未创建57条推测目录。")
        st.text_input("中文问题（知识库为空时只返回证据不足）", key="empty_question")
        if st.button("检索原文证据"):
            st.warning("证据不足：尚无已下载并解析的法规原文。")
    else:
        by_id = {r.id: r for r in rows}
        selected = st.selectbox(
            "选择法规与精确版本",
            list(by_id),
            format_func=lambda id: (
                json.loads(by_id[id].metadata_json)["regulation_number"]
                + " | "
                + json.loads(by_id[id].metadata_json)["version_kind"]
                + " | "
                + str(json.loads(by_id[id].metadata_json).get("version_date") or "未知")
                + " | "
                + json.loads(by_id[id].metadata_json)["format"]
            ),
        )
        row = by_id[selected]
        meta = json.loads(row.metadata_json)
        st.json(meta)
        st.write(
            "下载：" + row.download_status + "；解析：" + row.parse_status + "；法律效力/适用日期：待核实"
        )
        st.link_button("官方原文", meta["official_url"])
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
            for c in chunks:
                st.write(
                    f"{c.unit_type} {c.unit_label} | 页码范围 {c.page_start}–{c.page_end} | " + c.quality_json
                )
        question = st.text_input("中文问题")
        if st.button("检索原文证据"):
            result = answer(session, question, selected, root)
            st.write(result["answer_zh"])
            st.caption(result["indirect_electrolyte_impact"])
            for e in result["evidence"]:
                st.markdown(f"**{e['unit_type']} {e['unit_label']} · {e['celex']}**")
                st.code(e["quote"], language=None)
                st.caption(
                    e["locator"] + " | " + e["source_sha256"] + " | 待核实；" + str(e["quality_flags"])
                )
                st.link_button("引用原文", e["official_url"], key="cite-" + str(e["chunk_id"]))
