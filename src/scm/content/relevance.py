"""Bounded, explainable business filter. Never changes severity or lifecycle."""

import re
from datetime import timedelta

from scm.content.contracts import Relevance

VERSION = "2a.2"


def relevance(title, body, published_at, now, lifecycle="unknown"):
    text = title + "\n" + body
    low = text.lower()
    decision, code, reason = (
        "excluded",
        "NO_BUSINESS_LINK",
        "未发现明确欧洲供应链、电池/电解液或海运运营关联。",
    )
    domain, kind = None, "unknown"
    if re.search(r"\b(aviation|airbus|aircraft|airline|aerospace)\b", title, re.I) and not re.search(
        r"batter|electrolyte|port omission", title, re.I
    ):
        code, reason = "GENERIC_AVIATION", "一般航空产能新闻，不推导电池/电解液供应链影响。"
    elif re.search(r"\b(port omission|omit(?:ting|ted)? .{0,40}port|blank sailing)\b", low):
        domain, kind = "A", "port_omission" if "blank sailing" not in low else "blank_sailing"
        decision, code, reason = (
            "relevant",
            "EXPLICIT_CARRIER_CHANGE",
            "正文明确跳港/停航信号；具体线路与航次仍需核实。",
        )
    elif re.search(r"\bADR\b|\bIMDG\b", text) and re.search(r"amend|revis|dangerous goods|regulat", low):
        domain, kind = "B", "dangerous_goods_rule"
        decision, code, reason = (
            "relevant",
            "DG_RULE",
            "正文明确危险品规则及修订关联，适用货物和实施条款待核实。",
        )
    elif re.search(r"batter(?:y|ies)|electrolyte", low):
        if re.search(r"regulat|passport|recycl|rules|carbon footprint", low):
            domain, kind = "B", "battery_regulation"
            decision, code, reason = (
                "relevant",
                "BATTERY_POLICY",
                "电池法规/回收主题明确；不得直接认定电解液适用。",
            )
        elif re.search(r"\b(plant|factory|production|expansion|capacity)\b", low):
            domain, kind = "C", "unknown"
            decision, code, reason = (
                "relevant",
                "BATTERY_PLANT",
                "电池/电解液制造设施动态，计划与实际状态待核实。",
            )
    elif re.search(r"tariff|customs|anti-dumping", low):
        domain, kind = "B", "tariff"
        if re.search(r"european union|\bEU\b|european commission", text):
            decision, code, reason = "relevant", "EU_TRADE", "欧盟贸易/海关主题，商品编码和适用对象待核实。"
        else:
            code, reason = "UNRELATED_TARIFF", "未见欧洲或电池/电解液业务关联的关税信息。"
    elif re.search(r"strike|port closure", low):
        domain, kind = "A", "strike"
        decision, code, reason = (
            "possibly_relevant",
            "PORT_EVENT_UNVERIFIED",
            "港口事件候选，状态和范围待核实。",
        )
    elif re.search(r"reception|annual meeting|direct.air.capture", title, re.I):
        code, reason = "NON_OPERATIONAL_BACKGROUND", "交流接待/一般技术背景，未见具体运输限制或电池业务变化。"
    elif re.search(r"container|terminal|port|shipping", title, re.I):
        domain, kind = "A", "unknown"
        decision, code, reason = (
            "possibly_relevant",
            "PORT_BACKGROUND",
            "港航背景信息，不构成已确认运营中断。",
        )
    codes, reasons = [code], [reason]
    if lifecycle in {"resolved", "cancelled"}:
        decision = "excluded"
        codes.append("RESOLVED_OR_CANCELLED")
        reasons.append("已解决/取消，仅保留历史审计，不进入优先信号。")
    if published_at is None:
        if decision == "relevant":
            decision = "possibly_relevant"
        codes.append("UNKNOWN_PUBLICATION")
        reasons.append("发布日期未知，不进入当日日报。")
    elif published_at > now:
        decision = "excluded"
        codes.append("FUTURE_PUBLICATION")
        reasons.append("发布日期在未来，待核实，不进入优先信号。")
    elif now - published_at > timedelta(days=30):
        if decision == "relevant":
            decision = "possibly_relevant"
        codes.append("HISTORICAL_ONLY")
        reasons.append("超过30日，仅历史背景；不冒充当前新增风险。")
    return (
        domain,
        kind,
        Relevance(
            decision=decision,
            reason_codes=codes,
            reasons_zh=reasons,
            explicit_supply_chain_link=decision == "relevant",
            assessed_at=now,
        ),
    )
