"""Business link imports and decision reports use existing namespace/audit/report infrastructure."""

import csv
import io
import json
import zipfile
from datetime import datetime, timedelta
from html import escape

from sqlalchemy import select

from scm.platform.decision import BusinessLink, cards, save_links
from scm.platform.models import Audit, Report
from scm.platform.service import specs
from scm.settings import TIMEZONE, utcnow


def import_links(factory, content, filename, mode, actor, reason):
    if len(content) > 2_000_000:
        raise ValueError("Business file exceeds2MB")
    if filename.lower().endswith(".csv"):
        values = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    elif filename.lower().endswith(".xlsx"):
        from openpyxl import load_workbook

        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if sum(f.file_size for f in z.infolist()) > 20_000_000:
                raise ValueError("Workbook expansion limit")
        w = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        try:
            rows = w.active.iter_rows()
            header = [c.value for c in next(rows)]
            values = []
            for row in rows:
                if any(c.data_type == "f" for c in row):
                    raise ValueError("Formula not allowed")
                values.append(dict(zip(header, [c.value for c in row], strict=True)))
        finally:
            w.close()
    else:
        raise ValueError("CSV/XLSX only")
    if not 1 <= len(values) <= 500:
        raise ValueError("1–500 links required")
    cleaned = [{k: v for k, v in r.items() if v not in [None, ""]} for r in values]
    for r in cleaned:
        BusinessLink.model_validate(r)
    with factory.begin() as session:
        return save_links(session, mode, cleaned, actor, reason)


def source_health(session):
    result = []
    from scm.platform.models import PlatformSource

    for spec in specs():
        row = session.get(PlatformSource, spec["id"])
        logs = [
            json.loads(a.payload_json)
            for a in session.scalars(select(Audit).where(Audit.mode == "live", Audit.source_id == spec["id"]))
        ]
        attempts = [
            a
            for a in logs
            if a.get("verification_type") == "LIVE_HTTP" and "writes" in a and a.get("requests", 0) > 0
        ]
        succeeded = sum(bool(sum(a["writes"].values())) for a in attempts)
        scoped = [c for c in cards(session, "live") if c["source_id"] == spec["id"]]
        result.append(
            {
                "source_id": spec["id"],
                "official_url": spec["url"],
                "publisher": spec["name"],
                "module": spec["module"],
                "data_type": spec["adapter"],
                "access_method": spec["adapter"],
                "permission": spec.get("reuse_policy", {}).get("permission", "unknown"),
                "frequency_minutes": spec.get("frequency_minutes"),
                "live_attempts": len(attempts),
                "observed_success_rate": succeeded / len(attempts) if attempts else None,
                "success_rate_scope": "本库实际尝试样本，非SLA；不含DEMO",
                "valid_business_events": sum(c["high_value"] for c in scoped),
                "structured_events": sum(bool(c["event"]["types"]) for c in scoped),
                "last_success": row.last_success_at if row else None,
                "blocker": spec.get("blocker")
                or (None if row and row.last_success_at else "尚无成功采集证据"),
            }
        )
    return result


def decision_report(session, mode, kind="daily", day=None):
    if kind not in ["daily", "weekly"]:
        raise ValueError("daily/weekly required")
    start = (day or utcnow()).astimezone(TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    if kind == "weekly":
        start -= timedelta(days=start.weekday())
    end = start + timedelta(days=1 if kind == "daily" else 7)
    all_cards = cards(session, mode)
    selected = [
        c
        for c in all_cards
        if (c["published_at"] or c.get("observed_at"))
        and start <= datetime.fromisoformat(c["published_at"] or c["observed_at"]) < end
        and c["high_value"]
        and c["handling_state"] != "ignored"
    ]
    sections = []
    for c in selected:
        facts = (
            "".join("<blockquote>" + escape(f["quote"]) + "</blockquote>" for f in c["verified_facts"])
            or "<p>无人工核实事实；以下均为来源主张或规则推断。</p>"
        )
        actions = "".join("<li>" + escape(a) + "</li>" for a in c["candidate_actions"])
        sections.append(
            f'<article><h2>{escape(c["title"])}</h2><p>处理状态 {c["handling_state"]} · 证据版本{c["version"]}</p><h3>已核实重要变化（人工声明）</h3>{facts}<h3>来源主张/提取（待核实）</h3><pre>{escape(json.dumps(c["facts"], ensure_ascii=False))}</pre><h3>结构化值/规则换算</h3><pre>{escape(json.dumps(c["structured_extraction"], ensure_ascii=False))}</pre><p>{escape(c["normalization_note"])}</p><h3>潜在影响（规则推断）</h3><p>严重度 {c["severity"]}；业务相关度 {c["business_relevance"]}；影响 {c["impact_level"]}。</p><p>{escape(c["impact"])}</p><h3>用户业务数据</h3><pre>{escape(json.dumps(c["user_context"], ensure_ascii=False))}</pre><h3>候选行动</h3><ul>{actions}</ul><h3>仍缺失的信息</h3><p>{escape("；".join(c["missing"]))}</p><p>发布日期{escape(c["published_at"] or "未知")}；观测日期{escape(c.get("observed_at") or "未知")}；采集{escape(c["fetched_at"])}</p><p><a href="{escape(c["source_url"], quote=True)}">原文来源</a> · SHA256 {c["sha256"]}</p></article>'
        )
    body = (
        f'<!doctype html><html lang="zh"><meta charset="utf-8"><title>ESCIM决策支持</title><body><h1>{mode.upper()} 决策支持 {kind}</h1><p>{start.date()} 至 {end.date()}（不含结束日）Asia/Shanghai；价格观测按观测日期，不伪装发布日期。</p>'
        + ("".join(sections) or "<p>本期无合格高价值事件；覆盖不足，不代表无风险。</p>")
        + "<h2>来源覆盖与数据质量</h2><p>无LLM，无真实订单/合同报价，不给延误天数、损失、节省金额或最优方案。历史、未知或未核实主张不自动变为事实。</p><p>©European Union，CC BY4.0；燃油单元格提取及EUR/1000l→EUR/l单位换算为修改。来源样本不代表全覆盖。</p></body></html>"
    )
    record = session.scalar(
        select(Report).where(
            Report.mode == mode, Report.kind == "decision_" + kind, Report.period_start == start.isoformat()
        )
    )
    if record is None:
        record = Report(
            mode=mode,
            kind="decision_" + kind,
            period_start=start.isoformat(),
            generated_at=utcnow().isoformat(),
            html=body,
        )
        session.add(record)
    else:
        record.html = body
        record.generated_at = utcnow().isoformat()
    session.flush()
    return record
