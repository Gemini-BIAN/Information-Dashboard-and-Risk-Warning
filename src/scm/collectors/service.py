import json
import logging
import time
from collections import Counter
from statistics import median
from urllib.parse import urljoin, urlsplit

from sqlalchemy import select

from scm.collectors.http import AccessBlocked, SafeFetcher
from scm.collectors.parsers import discover_links, parse_article, parse_feed
from scm.database.models import CollectionLog, Source
from scm.intelligence.service import ingest
from scm.schemas import RawArticle
from scm.settings import ROOT, utcnow

logger = logging.getLogger(__name__)


def register_sources(session, path=None):
    specs = json.loads((path or ROOT / "config/sources.json").read_text(encoding="utf-8"))
    for spec in specs:
        row = session.get(Source, spec["id"])
        if row is None:
            row = Source(id=spec["id"])
            session.add(row)
        row.name, row.url, row.method = spec["name"], spec["url"], spec["method"]
        row.enabled = spec.get("enabled", True)
    return specs


def collect_one(spec, fetcher):
    started = time.monotonic()
    initial_requests = fetcher.request_count
    audit = {
        "verification_type": fetcher.verification_type,
        "url": spec["url"],
        "method": spec["method"],
        "parser": spec.get("parser", "generic"),
        "reuse_policy": spec.get("reuse_policy", {}),
        "access_success": False,
        "publication_date_parsed": False,
        "body_obtained": False,
        "restriction": None,
        "failure_stage": "robots_or_listing",
        "article_errors": [],
        "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
    }
    articles = []
    try:
        if spec.get("reuse_policy", {}).get("status") == "restricted":
            raise AccessBlocked("Source reuse policy prohibits collection; no requests made")
        response = fetcher.get(spec["url"])
        audit["access_success"] = True
        audit["http_status"] = response.status_code
        audit["failure_stage"] = "article_discovery_or_parse"
        if spec["method"] == "rss":
            candidates = parse_feed(response.content)
        else:
            candidates = [
                {"url": url}
                for url in discover_links(
                    response.text, spec["url"], spec["article_pattern"], spec.get("limit", 5)
                )
            ]
        audit["discovered"] = len(candidates)
        for candidate in candidates:
            try:
                if urlsplit(candidate["url"]).hostname != urlsplit(spec["url"]).hostname:
                    raise AccessBlocked("Cross-host feed article requires explicit source review")
                raw = fetcher.get(candidate["url"])
                parsed = parse_article(raw.text, candidate["url"], spec.get("parser", "generic"))
                if spec.get("use_canonical"):
                    from bs4 import BeautifulSoup

                    tag = BeautifulSoup(raw.text, "html.parser").find("link", rel="canonical")
                    if tag and tag.get("href"):
                        canonical = urljoin(candidate["url"], tag["href"])
                        p = urlsplit(canonical)
                        if (
                            p.scheme != "https"
                            or p.hostname != urlsplit(spec["url"]).hostname
                            or p.port not in [None, 443]
                            or p.username
                            or p.password
                        ):
                            raise AccessBlocked("Unsupported article canonical URL")
                        parsed["url"] = canonical
                if parsed["published_at"] is None:
                    parsed["published_at"] = candidate.get("published_at")
                articles.append(
                    RawArticle(**parsed, source=spec["id"], fetched_at=utcnow(), data_mode="live")
                )
            except Exception as exc:
                audit["article_errors"].append({"url": candidate["url"], "error": safe_error(exc)})
        audit["publication_date_parsed"] = any(a.published_at is not None for a in articles)
        audit["body_obtained"] = bool(articles)
        audit["dated_articles"] = sum(a.published_at is not None for a in articles)
        audit["parsed_articles"] = len(articles)
        audit["status"] = (
            "PASS" if articles and not audit["article_errors"] else "PARTIAL" if articles else "BLOCKED"
        )
        if not articles:
            audit["restriction"] = (
                "No parseable articles; source layout/feed must be reviewed. Not a successful collection."
            )
    except Exception as exc:
        audit["status"] = "BLOCKED"
        audit["restriction"] = safe_error(exc)
    if audit["status"] == "PASS":
        audit["failure_stage"] = None
    audit["last_request_url"] = fetcher.last_request_url
    audit["request_count"] = fetcher.request_count - initial_requests
    audit["robots"] = dict(fetcher.robots_audit)
    audit["verified_at"] = utcnow().isoformat()
    audit["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
    audit["article_samples"] = [
        {
            "url": str(a.url),
            "title": a.title,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "fetched_at": a.fetched_at.isoformat(),
        }
        for a in articles
    ]
    latencies = [(a.fetched_at - a.published_at).total_seconds() / 3600 for a in articles if a.published_at]
    audit["median_publication_age_hours"] = round(median(latencies), 2) if latencies else None
    return articles, audit


def safe_error(exc):
    if isinstance(exc, AccessBlocked):
        return str(exc)
    if isinstance(exc, ValueError):
        return str(exc)[:300]
    # Avoid recording request headers, credentials or complete response bodies.
    import httpx

    if isinstance(exc, httpx.ProxyError) and "403" in str(exc):
        return "ProxyError: CONNECT 403; environment proxy denied destination"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    return type(exc).__name__ + ": request/parse failed"


def run_collection(factory, specs=None, fetcher=None, provider=None):
    owned = fetcher is None
    fetcher = fetcher or SafeFetcher()
    results = []
    try:
        with factory.begin() as session:
            configured = register_sources(session)
            if specs is None:
                specs = configured
            else:
                for spec in specs:
                    existing = session.get(Source, spec["id"])
                    if existing is not None:
                        existing.name, existing.url, existing.method = (
                            spec["name"],
                            spec["url"],
                            spec["method"],
                        )
                    else:
                        session.add(
                            Source(
                                id=spec["id"],
                                name=spec["name"],
                                url=spec["url"],
                                method=spec["method"],
                                enabled=True,
                            )
                        )
        for spec in specs:
            if not spec.get("enabled", True):
                continue
            started = utcnow().isoformat()
            try:
                articles, audit = collect_one(spec, fetcher)
                counts = Counter()
                with factory.begin() as session:
                    for article in articles:
                        # A broken individual article cannot roll back unrelated articles.
                        try:
                            with session.begin_nested():
                                outcome, _ = ingest(session, article, provider=provider)
                                counts[outcome] += 1
                        except Exception as exc:
                            audit["article_errors"].append(
                                {"url": str(article.url), "error": safe_error(exc)}
                            )
                    if articles and not (counts["inserted"] + counts["updated"] + counts["unchanged"]):
                        audit["status"] = "BLOCKED"
                    elif audit["article_errors"] and audit["status"] == "PASS":
                        audit["status"] = "PARTIAL"
                    row = session.get(Source, spec["id"])
                    row.last_checked_at, row.last_status = audit["verified_at"], audit["status"]
                    audit["stored_articles"] = sum(counts.values())
                    if audit["stored_articles"] and audit["verification_type"] == "LIVE_HTTP":
                        row.last_success_at = audit["verified_at"]
                    audit["last_success_at"] = row.last_success_at
                    row.audit_json = json.dumps(audit, ensure_ascii=False)
                    session.add(
                        CollectionLog(
                            source_id=spec["id"],
                            started_at=started,
                            finished_at=utcnow().isoformat(),
                            status=audit["status"],
                            collected=len(articles),
                            inserted=counts["inserted"],
                            updated=counts["updated"],
                            error=audit["restriction"],
                            details_json=json.dumps(audit, ensure_ascii=False),
                        )
                    )
                results.append({"source": spec["id"], **audit, "writes": dict(counts)})
            except Exception as exc:
                logger.error("Source failed: %s (%s)", spec["id"], type(exc).__name__)
                with factory.begin() as session:
                    source = session.get(Source, spec["id"])
                    source.last_status = "BLOCKED"
                    source.last_checked_at = utcnow().isoformat()
                    source.audit_json = json.dumps({"status": "BLOCKED", "restriction": safe_error(exc)})
                    session.add(
                        CollectionLog(
                            source_id=spec["id"],
                            started_at=started,
                            finished_at=utcnow().isoformat(),
                            status="BLOCKED",
                            error=safe_error(exc),
                        )
                    )
                results.append({"source": spec["id"], "status": "BLOCKED", "restriction": safe_error(exc)})
    finally:
        if owned:
            fetcher.close()
    return results


def load_demo(factory):
    with factory.begin() as session:
        if session.get(Source, "demo-fixtures") is None:
            session.add(
                Source(
                    id="demo-fixtures",
                    name="演示Fixtures（非真实新闻）",
                    url="https://example.invalid/demo",
                    method="fixture",
                    enabled=False,
                )
            )
            session.flush()
        counts = Counter()
        for raw in json.loads((ROOT / "fixtures/articles.json").read_text(encoding="utf-8")):
            result, _ = ingest(session, RawArticle.model_validate(raw))
            counts[result] += 1
    return dict(counts)


def write_source_audit(factory, destination):
    lines = [
        "# 真实数据源验证报告",
        "",
        f"报告生成时间（UTC）：{utcnow().isoformat()}",
        "",
        "PASS 仅表示本次取得可解析正文，不保证覆盖完整、法律适用或未来持续可用。PARTIAL 表示部分文章失败。BLOCKED 不计为采集成功。未测试的字段不推断为成功。",
        "",
        "仅公开页面；先检查 robots，拒绝登录/CAPTCHA/访问受限内容。未自动确认网站全部使用条款，生产使用前需人工复核；当前仅内部研究。",
        "",
    ]
    with factory() as session:
        for source in session.scalars(select(Source).where(Source.method != "fixture")):
            audit = json.loads(source.audit_json)
            lines += [
                f"## {source.name}",
                "",
                f"- URL：{source.url}",
                f"- 方法：{source.method}",
                f"- 状态：{source.last_status}",
                f"- 最后验证：{source.last_checked_at or 'NOT TESTED'}",
                f"- 最近真实正文入库成功：{source.last_success_at or '无成功证据'}",
                f"- 验证类型：{audit.get('verification_type', 'NOT TESTED')}",
                f"- 启用：{source.enabled}",
                f"- 复用政策：{json.dumps(audit.get('reuse_policy', {}), ensure_ascii=False)}",
                f"- 耗时ms：{audit.get('duration_ms', 'NOT TESTED')}",
                f"- 正文数/带发布日期数：{audit.get('parsed_articles', 0)}/{audit.get('dated_articles', 0)}",
                f"- 列表访问成功：{audit.get('access_success', 'NOT TESTED')}",
                f"- 正文获取：{audit.get('body_obtained', 'NOT TESTED')}",
                f"- 文章发布日期解析：{audit.get('publication_date_parsed', 'NOT TESTED')}",
                f"- 限制/错误：{audit.get('restriction') or '无已观察到的限制（不等于无限制）'}",
                "",
                "```json",
                json.dumps(audit, ensure_ascii=False, indent=2),
                "```",
                "",
            ]
    destination.write_text("\n".join(lines), encoding="utf-8")
