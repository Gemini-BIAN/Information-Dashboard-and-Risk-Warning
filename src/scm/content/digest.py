"""Evidence-backed Chinese daily brief; no LLM, padding or currentness inference."""

import json
from collections import Counter
from html import escape

from sqlalchemy import select

from scm.content.contracts import IntelligenceRecord
from scm.database.models import Analysis, Event
from scm.reports.service import period_bounds
from scm.settings import utcnow


def generate_digest(session, day, mode="live", now=None):
    if mode not in {"live", "demo"}:
        raise ValueError("mode must be live/demo")
    now = now or utcnow()
    start, end = period_bounds("daily", day)
    end = min(end, now)
    records, counts = [], Counter()
    for event in session.scalars(
        select(Event).where(Event.data_mode == mode, Event.review_status != "rejected")
    ):
        analysis = session.scalar(
            select(Analysis).where(Analysis.event_id == event.id).order_by(Analysis.id.desc())
        )
        data = json.loads(analysis.payload_json).get("content_v1") if analysis else None
        if not data:
            continue
        record = IntelligenceRecord.model_validate(data)
        if record.data_mode != mode:
            continue
        counts[record.business_relevance.decision] += 1
        if (
            record.source_published_at
            and start <= record.source_published_at < end
            and record.business_relevance.decision == "relevant"
            and record.event_lifecycle not in {"resolved", "cancelled"}
        ):
            records.append((record, event.content_hash))
    records.sort(key=lambda pair: (pair[0].source_published_at, pair[0].record_id), reverse=True)
    records = records[:8]
    parts = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>ESCIM 中文情报日报</title><body>',
        f"<h1>ESCIM 中文情报日报｜{day.isoformat()}</h1>",
        f"<p>空间：{escape(mode)}；生成时间：{now.isoformat()}；按原始发布日期统计，不按抓取日搬移旧闻。</p>",
        "<p>采集覆盖不足：仅有有限来源及最多3篇候选/来源，不能推断市场平静或港口正常。无LLM：中文规则模板与原文摘录，非全文翻译或同等语义分析。</p>",
        f"<p>已保存评估：{escape(str(dict(counts)))}；本日日报合格事件 {len(records)} 条；excluded与待核实背景不作为优先信号。</p>",
    ]
    if not records:
        parts.append(
            "<p>本期没有符合日期和相关性门槛的已采集新增事件；覆盖不足，不用旧新闻或模拟信息凑数。</p>"
        )
    manifest = {}
    for record, fingerprint in records:
        manifest[record.record_id] = fingerprint
        parts += [
            f"<article><h2>{escape(record.title_zh or record.original_title)}</h2>",
            f"<p>公布：{record.source_published_at.isoformat()}；核验：{record.last_verified_at.isoformat()}；生命周期：{escape(record.event_lifecycle)}；规则严重度：{escape(record.content_severity)}（非当前港口风险）。生效及电解液适用性：未知/待核实。</p>",
            "<h3>事实与原文证据</h3>",
        ]
        for evidence in record.evidence_snippets:
            parts.append(
                f"<blockquote>{escape(evidence.quote)}</blockquote><p>证据定位：{escape(evidence.locator)}；原始版本：{escape(evidence.raw_revision_id or '未知')}</p>"
            )
        parts += [
            f"<p>业务筛选理由：{escape('；'.join(record.business_relevance.reasons_zh))}</p>",
            f"<p>风险依据：{escape('；'.join(record.severity_reasons))}</p>",
            "<h3>条件性影响（分析推测）</h3>",
        ]
        parts += [f"<p>{escape(x.text_zh)}</p>" for x in record.potential_impacts]
        parts += ["<h3>核实与行动</h3>"] + [
            f"<p>{escape(x.text_zh)} {escape(x.verification_question)}</p>"
            for x in record.suggested_checks_actions
        ]
        parts += [
            f"<p>质量限制：{escape('；'.join(record.quality_flags))}</p>",
            f"<p>来源：{escape(record.source_name)}；许可：{escape(record.license_name or '未知')}；© European Union / CC BY 4.0，仅限EU自有文字，已提取并添加中文模板，排除图片/Logo。"
            if record.source_id == "ec-batteries"
            else f"<p>来源：{escape(record.source_name)}；HHM/原公告发布者，文字原文与本系统分析分开，排除图片。",
            f'<a href="{escape(str(record.canonical_url), quote=True)}">官方原文</a></p></article>',
        ]
    parts.append("</body></html>")
    return "".join(parts), {
        "day": day.isoformat(),
        "mode": mode,
        "selected": len(records),
        "assessment_counts": dict(counts),
        "record_fingerprints": manifest,
        "coverage_adequate": False,
    }
