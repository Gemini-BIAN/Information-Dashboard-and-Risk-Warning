"""Document-evidence state, not a legal opinion about present applicability."""

import re
from datetime import date

from scm.settings import utcnow

MONTHS = {
    name.lower(): number
    for number, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}
DATE = r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[a-z]+\s+\d{4}|\d{4}年\d{1,2}月\d{1,2}日)"


def clauses(text):
    return [
        v.strip()
        for v in re.split(r"(?<=[.!?。；;])\s*|\n|\s+(?:but|however|whereas)\s+|但是|然而", text, flags=re.I)
        if v.strip()
    ]


def read_date(value):
    try:
        if "年" in value:
            y, m, d = re.findall(r"\d+", value)
            return date(int(y), int(m), int(d)).isoformat()
        if "-" in value:
            return date.fromisoformat(value).isoformat()
        d, m, y = value.lower().split()
        return date(int(y), MONTHS[m], int(d)).isoformat()
    except (ValueError, KeyError):
        return None


def policy_state(title, body, today=None):
    today = today or utcnow().date()
    text = title + "\n" + body
    reasons = []
    scoped = []
    for sentence in clauses(text):
        if re.search(
            r"\b(previous|former|earlier|old regulation|historical)\b|旧法规|原法规|此前法规", sentence, re.I
        ):
            reasons.append("排除历史/其他法规上下文：" + sentence[:400])
        else:
            scoped.append(sentence)
    text = "\n".join(scoped)
    dates = {}
    labels = {
        "effective_at": r"(?:shall apply from|enters into force on|effective from)\s+"
        + DATE
        + r"|(?:自|于)"
        + DATE
        + r"(?:起)?(?:生效|实施)",
        "expiry_at": r"(?:expires? on|expiry date[:：]?|ceases? to apply on)\s+"
        + DATE
        + r"|(?:于)?"
        + DATE
        + r"(?:到期|失效)",
        "repeal_at": r"(?:repealed (?:on|from|with effect from)|repeal date[:：]?)\s+"
        + DATE
        + r"|(?:于)?"
        + DATE
        + r"(?:起)?废止",
    }
    for field, pattern in labels.items():
        found = set()
        for match in re.finditer(pattern, text, re.I):
            raw = next((g for g in match.groups() if g), None)
            parsed = read_date(raw) if raw else None
            if parsed:
                found.add(parsed)
                reasons.append(f"{field}明确日期证据：{match[0]}")
        dates[field] = next(iter(found)) if len(found) == 1 else None
        if len(found) > 1:
            reasons.append(f"{field}存在多个不同日期，条款范围不明，需人工核实：" + ", ".join(sorted(found)))
    patterns = {
        "废止": r"\b(?:is|was|has been) repealed\b|已废止",
        "提案": r"\bproposal\b|\bproposed\b|提案|拟议",
        "实施": r"\bhas entered into force\b|\bis in force\b|已实施|正式生效",
        "通过": r"\bhas adopted\b|\bwas adopted\b|\bhas been adopted\b|已通过",
    }
    signals = set()
    for sentence in scoped:
        for state, pattern in patterns.items():
            if re.search(pattern, sentence, re.I):
                if re.search(
                    r"\b(?:not|never)\b.{0,20}(?:adopted|in force|repealed)|尚未|未通过|未实施|未废止",
                    sentence,
                    re.I,
                ):
                    reasons.append("否定政策状态，需核实：" + sentence[:400])
                    continue
                signals.add(state)
                reasons.append(f"{state}原文证据：{sentence[:400]}")
    if "废止" in signals and dates["repeal_at"] and dates["repeal_at"] > today.isoformat():
        state = "未知"
        reasons.append("废止表述与未来废止日期并存，不能自动推断当前适用，需核实。")
    elif "废止" in signals:
        state = "废止"  # Terminal precedence: an earlier effective date cannot overwrite repeal.
        reasons.append("明确废止优先于历史生效/通过证据。")
    elif "提案" in signals and "实施" in signals:
        state = "未知"
        reasons.append("提案与实施证据冲突，范围不明，需人工审核。")
    elif "提案" in signals:
        state = "提案"
    elif "实施" in signals:
        state = "实施"
    elif "通过" in signals:
        state = "通过"
    else:
        state = "未知"
    if state == "实施" and dates["effective_at"] and dates["effective_at"] > today.isoformat():
        state = "未知"
        reasons.append("实施表述与未来生效日期冲突，需人工审核。")
    if state in ["实施", "通过"] and dates["expiry_at"] and dates["expiry_at"] <= today.isoformat():
        state = "未知"
        reasons.append("明确到期日期已过；不能声称当前适用，需核实延期/替代法规。")
    return {
        "policy_status": state,
        **dates,
        "policy_reasons": reasons or ["没有明确状态依据，日期本身不证明当前适用。"],
    }
