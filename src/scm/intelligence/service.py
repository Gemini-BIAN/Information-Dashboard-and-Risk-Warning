import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select

from scm.database.models import Analysis, Event, PortOverride, RawRevision, ReviewLog, Source
from scm.intelligence.providers import RuleProvider, configured_provider
from scm.risk.lifecycle import RULE_VERSION, assess, port_signals
from scm.risk.rules import LEVELS, PORT_ALIASES, classify
from scm.settings import utcnow


def canonical_url(url):
    p = urlsplit(str(url))
    query = sorted(
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in ["fbclid", "gclid"]
    )
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", urlencode(query), ""))


def ingest(session, article, provider=None):
    url = canonical_url(article.url)
    normalized = re.sub(r"\s+", " ", article.title + "\n" + article.body).strip()
    published = article.published_at.isoformat() if article.published_at else "unknown"
    digest = hashlib.sha256((normalized + "\n" + published).encode()).hexdigest()
    event = session.scalar(
        select(Event).where(Event.canonical_url == url, Event.data_mode == article.data_mode)
    )
    if event is None:
        # Content deduplication is scoped to source and mode. Different sources remain attributable.
        event = session.scalar(
            select(Event).where(
                Event.content_hash == digest,
                Event.source_id == article.source,
                Event.data_mode == article.data_mode,
            )
        )
    if (
        event is not None
        and event.rule_version == RULE_VERSION
        and event.content_hash == digest
        and event.published_at == (article.published_at.isoformat() if article.published_at else None)
    ):
        event.fetched_at = article.fetched_at.isoformat()
        return "unchanged", event
    source = session.get(Source, article.source)
    if source is None:
        raise ValueError("Source must be registered before ingestion")
    before = None
    if event is not None:
        before = {
            name: getattr(event, name)
            for name in [
                "rule_version",
                "policy_status",
                "effective_at",
                "expiry_at",
                "repeal_at",
                "risk_level",
                "risk_reasons_json",
                "lifecycle",
                "lifecycle_reasons_json",
                "port_signals_json",
                "review_status",
            ]
        }
    metadata = classify(article.title, article.body)
    assessment = assess(article.title, article.body, demo=article.data_mode == "demo")
    level, reasons = assessment["severity"], assessment["reasons"]
    created = event is None
    if created:
        event = Event(canonical_url=url, data_mode=article.data_mode, source_id=article.source)
        session.add(event)
    event.title = article.title
    event.published_at = article.published_at.isoformat() if article.published_at else None
    event.fetched_at = article.fetched_at.isoformat()
    event.updated_at = utcnow().isoformat()
    event.content_hash = digest
    event.event_type = metadata["event_type"]
    event.countries_json = json.dumps(metadata["countries"], ensure_ascii=False)
    event.ports_json = json.dumps(metadata["ports"])
    event.policy_status = metadata["policy_status"]
    event.effective_at = metadata["effective_at"]
    event.expiry_at, event.repeal_at = metadata["expiry_at"], metadata["repeal_at"]
    event.policy_reasons_json = json.dumps(metadata["policy_reasons"], ensure_ascii=False)
    event.lifecycle = assessment["lifecycle"]
    event.lifecycle_reasons_json = json.dumps(assessment["reasons"], ensure_ascii=False)
    event.port_signals_json = json.dumps(
        port_signals(
            article.title, article.body, metadata["ports"], PORT_ALIASES, demo=article.data_mode == "demo"
        ),
        ensure_ascii=False,
    )
    event.rule_version = RULE_VERSION
    event.source_confidence = "demo" if article.data_mode == "demo" else "unreviewed_public"
    event.topic = metadata["topic"]
    event.risk_level = level
    event.risk_reasons_json = json.dumps(reasons, ensure_ascii=False)
    # Updated evidence must be reviewed again.
    event.review_status = "pending"
    if before is not None:
        after = {name: getattr(event, name) for name in before}
        session.add(
            ReviewLog(
                target_type="event",
                target_id=str(event.id),
                actor="system",
                action="rule_reassessment" if before["rule_version"] != RULE_VERSION else "evidence_update",
                reason=json.dumps({"before": before, "after": after}, ensure_ascii=False),
                created_at=utcnow().isoformat(),
                data_mode=event.data_mode,
            )
        )
    session.flush()
    revision = session.scalar(
        select(RawRevision).where(RawRevision.event_id == event.id, RawRevision.content_hash == digest)
    )
    if revision is None:
        revision = RawRevision(
            event_id=event.id,
            title=article.title,
            body=article.body,
            source_url=str(article.url),
            published_at=event.published_at,
            fetched_at=event.fetched_at,
            content_hash=digest,
        )
        session.add(revision)
        session.flush()
    error = None
    try:
        selected = provider or configured_provider()
        payload = selected.analyze(article, metadata)
        name = selected.name
    except Exception as exc:
        # No API response body or key in stored errors.
        error = type(exc).__name__ + ": LLM unavailable or evidence validation failed"
        selected = RuleProvider()
        name = selected.name
        payload = selected.analyze(article, metadata)
    session.add(
        Analysis(
            event_id=event.id,
            revision_id=revision.id,
            provider=name,
            analyzed_at=utcnow().isoformat(),
            payload_json=json.dumps(payload, ensure_ascii=False),
            error=error,
        )
    )
    return ("inserted" if created else "updated"), event


def review(session, event_id, action, actor, reason):
    if action not in ["confirmed", "rejected", "pending", "note"] or not actor.strip() or not reason.strip():
        raise ValueError("Valid action, actor and reason required")
    event = session.get(Event, event_id)
    if event is None:
        raise ValueError("Event not found")
    if action != "note":
        event.review_status = action
    session.add(
        ReviewLog(
            target_type="event",
            target_id=str(event_id),
            actor=actor,
            action=action,
            reason=reason,
            created_at=utcnow().isoformat(),
            data_mode=event.data_mode,
        )
    )


def override_port(session, port, mode, level, actor, reason, expires_at):
    if (
        port not in PORT_ALIASES
        or mode not in ["live", "demo"]
        or level not in LEVELS
        or not actor.strip()
        or not reason.strip()
        or expires_at <= utcnow()
    ):
        raise ValueError("Valid port, mode, risk, actor, reason and future expiry required")
    row = session.scalar(
        select(PortOverride).where(PortOverride.port == port, PortOverride.data_mode == mode)
    )
    if row is None:
        row = PortOverride(port=port, data_mode=mode)
        session.add(row)
    row.risk_level, row.actor, row.reason = level, actor, reason
    row.updated_at, row.expires_at = utcnow().isoformat(), expires_at.isoformat()
    session.add(
        ReviewLog(
            target_type="port",
            target_id=port,
            actor=actor,
            action=level,
            reason=reason,
            created_at=row.updated_at,
            data_mode=mode,
        )
    )


def reassess_events(session):
    """Reapply changed rules to saved evidence; never relabel demo/live or refetch."""
    from datetime import datetime

    from scm.intelligence.providers import RuleProvider
    from scm.schemas import RawArticle

    count = 0
    for event in session.scalars(select(Event).where(Event.rule_version != RULE_VERSION)).all():
        raw = session.scalar(
            select(RawRevision).where(
                RawRevision.event_id == event.id, RawRevision.content_hash == event.content_hash
            )
        )
        if raw is None:
            continue  # Legacy remains unknown in current port aggregation.
        ingest(
            session,
            RawArticle(
                title=raw.title,
                body=raw.body,
                url=raw.source_url,
                source=event.source_id,
                published_at=datetime.fromisoformat(raw.published_at) if raw.published_at else None,
                fetched_at=datetime.fromisoformat(event.fetched_at),
                data_mode=event.data_mode,
            ),
            RuleProvider(),
        )
        count += 1
    return count
