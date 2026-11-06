"""Conservative operational lifecycle: explicit claims, scope and uncertainty."""

import re
from datetime import timedelta

from scm.risk.policy import clauses
from scm.settings import utcnow

RULE_VERSION = "2026-11-06.4"
LIFECYCLE_LABELS = {
    "announced": "已宣布/待发生",
    "active": "原文称正在发生",
    "resolved": "已解除",
    "cancelled": "已取消",
    "unknown": "未知/待人工核实",
}
HAZARD = r"\b(?:strike|port closure|port is closed|port remains closed|operations (?:(?:are|remain) )?suspended|port omission|blank sailing)\b|罢工|港口关闭|作业中断|跳港|航次取消"
CANCEL = r"\b(?:(?:strike|industrial action|closure|disruption)(?:\s+\w+){0,4}\s+(?:cancelled|canceled|called off|withdrawn|averted)|(?:cancelled|canceled|withdrawn|averted)\s+(?:strike|industrial action|closure))\b|\bno strike\b|\bno port closure\b|取消罢工|无罢工|罢工取消|罢工撤回"
RESOLVE = r"\b(?:strike (?:has )?ended|strike is over|operations (?:have )?resumed|port (?:has )?reopened|closure (?:has been )?lifted)\b|罢工结束|恢复作业|重新开放|解除关闭"
ACTIVE = r"\b(?:operations (?:(?:are|remain) )?suspended|port is closed|port remains closed|strike is ongoing|strike continues|on strike|strike began|ongoing strike|closure continues)\b|正在罢工|罢工仍在继续|港口关闭|作业中断"
UNCERTAIN = (
    r"\b(?:may|could|possible|potential|planned|plans?|announced|will|scheduled)\b|可能|拟|计划|宣布|将于"
)
HYPOTHETICAL = r"\b(?:fictional|hypothetical|simulation|scenario|drill)\b|假设|演练|虚构|示例"
HISTORICAL = r"\b(?:last year|last month|historical|previously|in 20\d{2})\b|去年|往年|历史事件|此前"
NEGATIVE = r"\b(?:not|no longer|never)\s+(?:currently\s+)?(?:on strike|suspended|closed|ongoing)|\bno disruption\b|\b(?:will not|won't)\s+strike\b|不会罢工|无中断|并未|没有|未发生"


def assess(title, body, *, demo=False):
    """Severity is an article signal; lifecycle determines eligibility for current alert."""
    all_text = title + "\n" + body
    # Demo scenarios may show simulated severity, but can never become live evidence.
    if not demo and re.search(HYPOTHETICAL, all_text, re.I):
        return {
            "lifecycle": "unknown",
            "severity": "未知",
            "reasons": ["假设/示例文本不构成实际事件证据，待人工核实。"],
        }
    primary = [s for s in clauses(body) if re.search("|".join([HAZARD, CANCEL, RESOLVE, NEGATIVE]), s, re.I)]
    headline_terminal = [
        s for s in clauses(title) if re.search("|".join([CANCEL, RESOLVE, NEGATIVE]), s, re.I)
    ]
    sentences = primary + headline_terminal if primary else clauses(title)
    states = set()
    reasons = []
    eligible = []
    for sentence in sentences:
        if not re.search("|".join([HAZARD, CANCEL, RESOLVE, NEGATIVE]), sentence, re.I):
            continue
        if not demo and re.search(r"\b(?:example|if|would)\b|例如|假如|如果|若发生", sentence, re.I):
            reasons.append("条件/示例语句不证明事件已发生：" + sentence[:400])
            continue
        old_dates = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", sentence)
        ongoing = re.search(
            r"\b(?:continues|ongoing|remain|remains|still|currently)\b|仍在|仍然|正在", sentence, re.I
        )
        if old_dates and max(old_dates) < (utcnow().date() - timedelta(days=30)).isoformat() and not ongoing:
            reasons.append("历史事件日期不证明当前中断：" + sentence[:400])
            continue
        if re.search(HISTORICAL, sentence, re.I) and not ongoing:
            # A historical reference never demonstrates a present incident.
            years = re.findall(r"\bin (20\d{2})\b", sentence, re.I)
            if not years or any(int(year) < utcnow().year for year in years):
                reasons.append("历史上下文不证明当前中断：" + sentence[:400])
                continue
        if re.search(r"\bnot\b.{0,20}(?:cancelled|canceled|withdrawn|ended|lifted)", sentence, re.I):
            states.add("unknown")
        elif re.search(CANCEL, sentence, re.I):
            states.add("cancelled")
        elif re.search(RESOLVE, sentence, re.I):
            states.add("resolved")
        elif re.search(NEGATIVE, sentence, re.I):
            states.add("unknown")
        elif re.search(UNCERTAIN, sentence, re.I):
            states.add("announced")
            eligible.append(sentence)
        elif re.search(ACTIVE, sentence, re.I):
            states.add("active")
            eligible.append(sentence)
        else:
            states.add("unknown")
            eligible.append(sentence)
        reasons.append("生命周期原文证据：" + sentence[:400])
    terminal = states & {"cancelled", "resolved"}
    if terminal and states & {"active", "announced"}:
        lifecycle = "unknown"
        severity = "未知"
        reasons.append("存在进行中/已宣布与解除/取消的矛盾证据；不自动抬高当前港口风险，待人工审核。")
    elif terminal:
        lifecycle = "cancelled" if "cancelled" in terminal else "resolved"
        severity = "低"
        reasons.append("解除/取消信号不构成当前中断；低是关键词严重度，不代表港口运行正常。")
    else:
        lifecycle = "active" if "active" in states else "announced" if "announced" in states else "unknown"
        severity = "低"
        # Score the scoped eligible statements (body preferred over stale headline).
        scored = eligible or ([title] if not reasons else [])
        for sentence in scored:
            if re.search(HAZARD, sentence, re.I):
                candidate = (
                    "高"
                    if re.search(
                        r"\bstrike\b|port closure|operations (?:(?:are|remain) )?suspended|port is closed|port remains closed|罢工|港口关闭|作业中断",
                        sentence,
                        re.I,
                    )
                    else "中"
                )
                if re.search(UNCERTAIN, sentence, re.I):
                    candidate = "中"
                if candidate == "高" or severity == "低":
                    severity = candidate
                reasons.append("严重度规则命中：" + sentence[:400])
        if severity == "低" and re.search(
            r"\b(?:tariff|anti-dumping|anti-subsidy|import duties|red sea|delay|proposal)\b|关税|红海|延误|提案",
            all_text,
            re.I,
        ):
            severity = "中"
            reasons.append("非港口运营专题关键词信号，不作为当前港口中断证据。")
    return {
        "lifecycle": lifecycle,
        "severity": severity,
        "reasons": reasons or ["未识别明确运营状态，待核实；低关键词分数不是低运行风险。"],
    }


def port_signals(title, body, ports, aliases, *, demo=False):
    output = {}
    for port in ports:
        selected = []
        for sentence in clauses(body):
            mentioned = [
                name
                for name in ports
                if any(
                    re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", sentence, re.I)
                    if a.isascii()
                    else a in sentence
                    for a in aliases[name]
                )
            ]
            if mentioned == [port] or not mentioned and len(ports) == 1:
                selected.append(sentence)
        # A multi-port title cannot attribute an unnamed body claim to an individual port.
        scoped_title = title if len(ports) == 1 else ""
        if not demo and re.search(HYPOTHETICAL, title + "\n" + body, re.I):
            output[port] = {
                "lifecycle": "unknown",
                "severity": "未知",
                "reasons": ["文档含明确虚构/假设标识，不作为真实港口事件。"],
            }
        else:
            output[port] = assess(scoped_title, "\n".join(selected), demo=demo)
    return output
