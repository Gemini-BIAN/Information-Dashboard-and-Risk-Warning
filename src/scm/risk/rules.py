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
        (
            "关税贸易",
            [
                "tariff",
                "customs",
                "anti-dumping",
                "anti-subsidy",
                "import duties",
                "关税",
                "海关",
                "反倾销",
                "反补贴",
            ],
        ),
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
    from scm.risk.policy import policy_state

    policy = (
        policy_state(title, body)
        if event_type in ["关税贸易", "电池法规"]
        else {
            "policy_status": "未知",
            "effective_at": None,
            "expiry_at": None,
            "repeal_at": None,
            "policy_reasons": ["非政策类情报，不推断政策状态。"],
        }
    )
    return {
        "event_type": event_type,
        "ports": ports,
        "countries": sorted(countries),
        **policy,
        "topic": event_type + ":" + ",".join(ports or sorted(countries) or ["全球"]),
    }


def grade(title, body, event_type):
    from scm.risk.lifecycle import assess

    result = assess(title, body)
    return result["severity"], result["reasons"]


def port_risk(session, port, mode, now=None):
    import json

    from sqlalchemy import select

    from scm.database.models import Event, PortOverride
    from scm.risk.lifecycle import RULE_VERSION

    now = now or utcnow()
    cutoff = now - timedelta(days=30)
    candidates = []
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
            candidates.append(event)
            signal = json.loads(event.port_signals_json).get(port, {})
            if (
                event.rule_version == RULE_VERSION
                and signal.get("lifecycle") in ["active", "announced"]
                and signal.get("severity") in ["中", "高"]
            ):
                events.append(event)
    scores = []
    for event in events:
        signal = json.loads(event.port_signals_json)[port]
        scores.append("中" if signal["lifecycle"] == "announced" else signal["severity"])
    level = max(scores, key=lambda level: LEVELS[level], default="未知")
    reasons = [
        f"近30天候选公告 {len(candidates)} 条，明确进行中/已宣布信号 {len(events)} 条；发布时间不证明持续中断。"
    ]
    if not events:
        reasons.append(
            "未获得可用于当前预警的明确运营证据，风险未知；已解除、取消、矛盾或状态未知不抬高预警。"
        )
    for event in candidates:
        signal = json.loads(event.port_signals_json).get(port, {})
        reasons.append(
            f"事件#{event.id} 生命周期={signal.get('lifecycle', 'unknown')}；来源可信度={event.source_confidence}；原文={event.canonical_url}"
        )
        reasons.extend(signal.get("reasons", []))
    override = session.scalar(
        select(PortOverride).where(PortOverride.port == port, PortOverride.data_mode == mode)
    )
    if override and datetime.fromisoformat(override.expires_at) > now:
        return override.risk_level, [f"人工调整（截至 {override.expires_at}）：{override.reason}"], events
    return level, reasons, events
