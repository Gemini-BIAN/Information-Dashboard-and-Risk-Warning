"""Conservative evidence-triggered rules; risk is a signal, never a prediction."""

import re
from datetime import timedelta

from scm.settings import utcnow

PORT_ALIASES = {
    "Rotterdam": ["rotterdam", "鹿特丹", "nlrtm"],
    "Antwerp-Bruges": ["antwerp", "bruges", "安特卫普", "泽布吕赫", "beanr", "bezee"],
    "Hamburg": ["hamburg", "汉堡", "deham"],
}
PORT_COUNTRIES = {"Rotterdam": "荷兰", "Antwerp-Bruges": "比利时", "Hamburg": "德国"}
LEVELS = {"未知": -1, "低": 0, "中": 1, "高": 2}


def normalize_port(value):
    text = value.casefold().strip()
    for name, aliases in PORT_ALIASES.items():
        if text == name.casefold() or text in aliases:
            return name
    return value.strip()


def contains(text, words):
    return any(
        re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text) if w.isascii() else w in text
        for w in words
    )


def classify(title, body):
    text = (title + "\n" + body).casefold()
    ports = [name for name, aliases in PORT_ALIASES.items() if contains(text, aliases)]
    countries = {PORT_COUNTRIES[p] for p in ports}
    for country, words in {
        "中国": ["china", "中国", "catl"],
        "德国": ["germany", "德国"],
        "匈牙利": ["hungary", "匈牙利"],
        "欧盟": ["european union", "european commission", "欧盟"],
        "美国": ["united states", "美国"],
    }.items():
        if contains(text, words):
            countries.add(country)
    categories = [
        ("港口运营", ["strike", "罢工", "port closure", "港口关闭", "operations suspended", "作业中断"]),
        ("航线调整", ["port omission", "blank sailing", "跳港", "航次取消", "red sea", "红海", "rerouting"]),
        ("关税贸易", ["tariff", "customs", "关税", "海关"]),
        ("电池法规", ["battery passport", "batteries regulation", "电池护照", "电池法规"]),
        (
            "行业产能",
            [
                "catl",
                "gigafactory",
                "capacity",
                "产能",
                "宁德时代",
                "northvolt",
                "acc",
                "lg energy",
                "samsung sdi",
            ],
        ),
    ]
    event_type = next((name for name, words in categories if contains(text, words)), "综合动态")
    # Only explicit phrases establish a status; no interpretation from publication date.
    statuses = [
        ("废止", ["is repealed", "已废止"]),
        ("提案", ["proposal", "proposed", "提案", "拟议"]),
        ("实施", ["has entered into force", "is in force", "已实施", "正式生效"]),
        ("通过", ["has adopted", "was adopted", "已通过"]),
    ]
    policy_status = (
        next((name for name, words in statuses if contains(text, words)), "未知")
        if event_type in ["关税贸易", "电池法规"]
        else "未知"
    )
    effective_at = None
    if event_type in ["关税贸易", "电池法规"]:
        # Only explicitly labelled dates; never infer a date from publication time.
        from datetime import date, datetime

        patterns = [
            r"(?:shall apply from|enters into force on|effective from)\s+(\d{4}-\d{2}-\d{2})",
            r"(?:shall apply from|enters into force on|effective from)\s+(\d{1,2} [a-z]+ \d{4})",
            r"(?:自|于)(\d{4}年\d{1,2}月\d{1,2}日)(?:起)?(?:生效|实施)",
        ]
        for pattern, fmt in zip(patterns, ["%Y-%m-%d", "%d %B %Y", "%Y年%m月%d日"]):
            match = re.search(pattern, text)
            if match:
                try:
                    effective_at = datetime.strptime(match[1], fmt).date().isoformat()
                    break
                except ValueError:
                    pass
        if effective_at and date.fromisoformat(effective_at) <= utcnow().date() and policy_status != "提案":
            policy_status = "实施"
    return {
        "event_type": event_type,
        "ports": ports,
        "countries": sorted(countries),
        "policy_status": policy_status,
        "effective_at": effective_at,
        "topic": event_type + ":" + ",".join(ports or sorted(countries) or ["全球"]),
    }


def grade(title, body, event_type):
    """Quote the sentence that triggered each grade; hedging prevents automatic high."""
    sentences = re.split(r"(?<=[.!?。；])\s*|\n", title + "\n" + body)
    triggers = [
        ("高", ["port closure", "operations suspended", "港口关闭", "作业中断", "strike", "罢工"]),
        (
            "中",
            [
                "port omission",
                "blank sailing",
                "跳港",
                "航次取消",
                "tariff",
                "关税",
                "red sea",
                "红海",
                "delay",
                "延误",
                "proposal",
                "提案",
            ],
        ),
    ]
    hits = []
    for level, words in triggers:
        for sentence in sentences:
            t = sentence.casefold()
            if not contains(t, words):
                continue
            if contains(
                t,
                [
                    "no strike",
                    "strike ended",
                    "strike averted",
                    "not suspended",
                    "no port closure",
                    "无罢工",
                    "罢工结束",
                    "取消罢工",
                    "恢复作业",
                ],
            ):
                continue
            uncertain = contains(
                t, ["may", "could", "possible", "potential", "planned", "可能", "拟", "计划"]
            )
            actual_level = "中" if uncertain and level == "高" else level
            hits.append((actual_level, f"规则关键词命中（需核实当前有效性）：{sentence[:400]}"))
    if hits:
        level = max(hits, key=lambda h: LEVELS[h[0]])[0]
        return level, [h[1] for h in hits if h[0] == level][:4]
    return "低", ["未命中已配置的中高风险信号；低风险不代表无风险。"]


def port_risk(session, port, mode, now=None):
    import json

    from sqlalchemy import select

    from scm.database.models import Event, PortOverride

    now = now or utcnow()
    cutoff = now - timedelta(days=30)
    events = []
    from datetime import datetime

    for event in session.scalars(
        select(Event).where(Event.data_mode == mode, Event.review_status != "rejected")
    ):
        # Unknown publication dates are displayed in details but cannot assert current port risk.
        if (
            port in json.loads(event.ports_json)
            and event.published_at
            and cutoff <= datetime.fromisoformat(event.published_at) <= now
        ):
            events.append(event)
    level = max((e.risk_level for e in events), key=lambda level: LEVELS[level], default="未知")
    reasons = (
        [f"近30天有效期内公告信号 {len(events)} 条；不等于实时作业状态。"]
        if events
        else ["近30天无可用、带发布日期的公告；数据不足。"]
    )
    override = session.scalar(
        select(PortOverride).where(PortOverride.port == port, PortOverride.data_mode == mode)
    )
    if override and datetime.fromisoformat(override.expires_at) > now:
        return override.risk_level, [f"人工调整（截至 {override.expires_at}）：{override.reason}"], events
    return level, reasons, events
