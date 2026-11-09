# 真实数据源验证报告

报告生成时间（UTC）：2026-11-06T05:39:40.427823+00:00

PASS 仅表示本次取得可解析正文，不保证覆盖完整、法律适用或未来持续可用。PARTIAL 表示部分文章失败。BLOCKED 不计为采集成功。未测试的字段不推断为成功。

仅公开页面；先检查 robots，拒绝登录/CAPTCHA/访问受限内容。未自动确认网站全部使用条款，生产使用前需人工复核；当前仅内部研究。

## Port of Rotterdam

- URL：https://www.portofrotterdam.com/en/news-and-press-releases
- 方法：html
- 状态：BLOCKED
- 最后验证：2026-11-06T05:32:39.763191+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：POLICY_REVIEW
- 启用：False
- 复用政策：{"status": "restricted", "notice_url": "https://www.portofrotterdam.com/en/copyright", "note": "Official notice prohibits reproducing/downloading content; no permission obtained. Disabled; no body collection or reuse."}
- 耗时ms：NOT TESTED
- 正文数/带发布日期数：0/0
- 列表访问成功：NOT TESTED
- 正文获取：NOT TESTED
- 文章发布日期解析：NOT TESTED
- 限制/错误：Copyright policy prohibits reproducing/downloading content. Source disabled; newly fetched body/analysis copies discarded before acceptance.

```json
{
  "status": "BLOCKED",
  "verification_type": "POLICY_REVIEW",
  "verified_at": "2026-11-06T05:32:39.763191+00:00",
  "failure_stage": "reuse_policy",
  "restriction": "Copyright policy prohibits reproducing/downloading content. Source disabled; newly fetched body/analysis copies discarded before acceptance.",
  "discarded_articles": 5,
  "parsed_articles": 0,
  "dated_articles": 0,
  "stored_articles": 0,
  "reuse_policy": {
    "status": "restricted",
    "notice_url": "https://www.portofrotterdam.com/en/copyright",
    "note": "Official notice prohibits reproducing/downloading content; no permission obtained. Disabled; no body collection or reuse."
  }
}
```

## Port of Antwerp-Bruges

- URL：https://www.portofantwerpbruges.com/en/news
- 方法：html
- 状态：BLOCKED
- 最后验证：2026-11-06T05:29:23.283322+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{}
- 耗时ms：1734.28
- 正文数/带发布日期数：0/0
- 列表访问成功：True
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：No parseable articles; source layout/feed must be reviewed. Not a successful collection.

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://www.portofantwerpbruges.com/en/news",
  "method": "html",
  "access_success": true,
  "publication_date_parsed": false,
  "body_obtained": false,
  "restriction": "No parseable articles; source layout/feed must be reviewed. Not a successful collection.",
  "failure_stage": "article_discovery_or_parse",
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "http_status": 200,
  "discovered": 0,
  "dated_articles": 0,
  "parsed_articles": 0,
  "status": "BLOCKED",
  "last_request_url": "https://www.portofantwerpbruges.com/en/news",
  "request_count": 2,
  "robots": {
    "https://www.portofrotterdam.com": "200 parsed",
    "https://www.portofantwerpbruges.com": "200 parsed"
  },
  "verified_at": "2026-11-06T05:29:23.283322+00:00",
  "duration_ms": 1734.28,
  "article_samples": [],
  "median_publication_age_hours": null,
  "stored_articles": 0,
  "last_success_at": null
}
```

## Port of Hamburg

- URL：https://www.hafen-hamburg.de/en/press/news/
- 方法：html
- 状态：BLOCKED
- 最后验证：2026-11-06T05:29:25.925345+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{}
- 耗时ms：2639.23
- 正文数/带发布日期数：0/0
- 列表访问成功：True
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：No parseable articles; source layout/feed must be reviewed. Not a successful collection.

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://www.hafen-hamburg.de/en/press/news/",
  "method": "html",
  "access_success": true,
  "publication_date_parsed": false,
  "body_obtained": false,
  "restriction": "No parseable articles; source layout/feed must be reviewed. Not a successful collection.",
  "failure_stage": "article_discovery_or_parse",
  "article_errors": [
    {
      "url": "https://www.hafen-hamburg.de/cn/press/news/",
      "error": "No article/main content container"
    }
  ],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "http_status": 200,
  "discovered": 1,
  "dated_articles": 0,
  "parsed_articles": 0,
  "status": "BLOCKED",
  "last_request_url": "https://www.hafen-hamburg.de/cn/press/news/",
  "request_count": 3,
  "robots": {
    "https://www.portofrotterdam.com": "200 parsed",
    "https://www.portofantwerpbruges.com": "200 parsed",
    "https://www.hafen-hamburg.de": "404 no robots file (RFC 9309)"
  },
  "verified_at": "2026-11-06T05:29:25.925345+00:00",
  "duration_ms": 2639.23,
  "article_samples": [],
  "median_publication_age_hours": null,
  "stored_articles": 0,
  "last_success_at": null
}
```

## Maersk Advisories

- URL：https://www.maersk.com/news/category/advisories
- 方法：html
- 状态：NOT TESTED
- 最后验证：2026-11-06T05:38:01.958986+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP_ROBOTS_PROBE
- 启用：True
- 复用政策：{}
- 耗时ms：NOT TESTED
- 正文数/带发布日期数：0/0
- 列表访问成功：NOT TESTED
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：Robots allows listing; body collection withheld pending reuse-policy review (no article requested)

```json
{
  "verification_type": "LIVE_HTTP_ROBOTS_PROBE",
  "url": "https://www.maersk.com/news/category/advisories",
  "last_request_url": "https://www.maersk.com/robots.txt",
  "failure_stage": "robots_or_reuse_review",
  "body_obtained": false,
  "publication_date_parsed": false,
  "request_count": 1,
  "parsed_articles": 0,
  "dated_articles": 0,
  "stored_articles": 0,
  "robots_http_status": 200,
  "robots_allows_listing": true,
  "status": "NOT TESTED",
  "restriction": "Robots allows listing; body collection withheld pending reuse-policy review (no article requested)",
  "verified_at": "2026-11-06T05:38:01.958986+00:00"
}
```

## Hapag-Lloyd Operational Updates

- URL：https://www.hapag-lloyd.com/en/services-information/news.html
- 方法：html
- 状态：NOT TESTED
- 最后验证：2026-11-06T05:38:02.432723+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP_ROBOTS_PROBE
- 启用：True
- 复用政策：{}
- 耗时ms：NOT TESTED
- 正文数/带发布日期数：0/0
- 列表访问成功：NOT TESTED
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：Robots allows listing; body collection withheld pending reuse-policy review (no article requested)

```json
{
  "verification_type": "LIVE_HTTP_ROBOTS_PROBE",
  "url": "https://www.hapag-lloyd.com/en/services-information/news.html",
  "last_request_url": "https://www.hapag-lloyd.com/robots.txt",
  "failure_stage": "robots_or_reuse_review",
  "body_obtained": false,
  "publication_date_parsed": false,
  "request_count": 1,
  "parsed_articles": 0,
  "dated_articles": 0,
  "stored_articles": 0,
  "robots_http_status": 200,
  "robots_allows_listing": true,
  "status": "NOT TESTED",
  "restriction": "Robots allows listing; body collection withheld pending reuse-policy review (no article requested)",
  "verified_at": "2026-11-06T05:38:02.432723+00:00"
}
```

## European Commission Transport

- URL：https://transport.ec.europa.eu/news-events/news_en
- 方法：html
- 状态：PASS
- 最后验证：2026-11-06T05:36:42.924454+00:00
- 最近真实正文入库成功：2026-11-06T05:36:42.924454+00:00
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{"status": "reviewed_allowed", "license": "CC BY 4.0", "notice_url": "https://commission.europa.eu/legal-notice_en", "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."}
- 耗时ms：6112.6
- 正文数/带发布日期数：5/5
- 列表访问成功：True
- 正文获取：True
- 文章发布日期解析：True
- 限制/错误：无已观察到的限制（不等于无限制）

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://transport.ec.europa.eu/news-events/news_en",
  "method": "html",
  "parser": "european_commission",
  "reuse_policy": {
    "status": "reviewed_allowed",
    "license": "CC BY 4.0",
    "notice_url": "https://commission.europa.eu/legal-notice_en",
    "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."
  },
  "access_success": true,
  "publication_date_parsed": true,
  "body_obtained": true,
  "restriction": null,
  "failure_stage": null,
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "http_status": 200,
  "discovered": 5,
  "dated_articles": 5,
  "parsed_articles": 5,
  "status": "PASS",
  "last_request_url": "https://transport.ec.europa.eu/news-events/news/keynote-speech-director-general-magda-kopczynska-european-unions-role-ensuring-competitive-european-2026-10-16_en",
  "request_count": 7,
  "robots": {
    "https://transport.ec.europa.eu": "200 parsed"
  },
  "verified_at": "2026-11-06T05:36:42.924454+00:00",
  "duration_ms": 6112.6,
  "article_samples": [
    {
      "url": "https://transport.ec.europa.eu/news-events/news/commission-strengthens-europes-position-worlds-leading-tourism-destination-2026-11-04_en",
      "title": "Commission strengthens Europe’s position as the world’s leading tourism destination",
      "published_at": "2026-11-04T11:05:24+00:00",
      "fetched_at": "2026-11-06T05:36:38.959846+00:00"
    },
    {
      "url": "https://transport.ec.europa.eu/news-events/news/road-safety-statistics-2025-confirm-drop-eu-road-deaths-2026-10-27_en",
      "title": "Road safety statistics for 2025 confirm drop in EU road deaths",
      "published_at": "2026-10-27T10:30:28+00:00",
      "fetched_at": "2026-11-06T05:36:39.874720+00:00"
    },
    {
      "url": "https://transport.ec.europa.eu/news-events/news/joint-press-release-19th-implementation-meeting-eu-china-maritime-transport-agreement-2026-10-20_en",
      "title": "Joint press release on the 19th implementation meeting of the EU–China Maritime Transport Agreement",
      "published_at": "2026-10-20T08:03:49+00:00",
      "fetched_at": "2026-11-06T05:36:40.939006+00:00"
    },
    {
      "url": "https://transport.ec.europa.eu/news-events/news/solidarity-lanes-latest-figures-september-2026-2026-10-19_en",
      "title": "Solidarity Lanes: Latest figures – September 2026",
      "published_at": "2026-10-19T12:02:55+00:00",
      "fetched_at": "2026-11-06T05:36:41.915226+00:00"
    },
    {
      "url": "https://transport.ec.europa.eu/news-events/news/keynote-speech-director-general-magda-kopczynska-european-unions-role-ensuring-competitive-european-2026-10-16_en",
      "title": "Keynote speech by Director-General Magda Kopczyńska: The European Union’s role in ensuring a competitive European aviation in a challenging geopolitical landscape",
      "published_at": "2026-10-19T09:17:01+00:00",
      "fetched_at": "2026-11-06T05:36:42.924372+00:00"
    }
  ],
  "median_publication_age_hours": 405.55,
  "stored_articles": 5,
  "last_success_at": "2026-11-06T05:36:42.924454+00:00"
}
```

## EUR-Lex Official Journal

- URL：https://eur-lex.europa.eu/collection/eu-law/oj.html
- 方法：html
- 状态：BLOCKED
- 最后验证：2026-11-06T05:28:40.841478+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{}
- 耗时ms：313.36
- 正文数/带发布日期数：0/0
- 列表访问成功：False
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：robots.txt HTTP 202; fail closed

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://eur-lex.europa.eu/collection/eu-law/oj.html",
  "method": "html",
  "access_success": false,
  "publication_date_parsed": false,
  "body_obtained": false,
  "restriction": "robots.txt HTTP 202; fail closed",
  "failure_stage": "robots_or_listing",
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "status": "BLOCKED",
  "last_request_url": "https://eur-lex.europa.eu/robots.txt",
  "request_count": 1,
  "robots": {
    "https://www.hafen-hamburg.de": "404 no robots file (RFC 9309)"
  },
  "verified_at": "2026-11-06T05:28:40.841478+00:00",
  "duration_ms": 313.36,
  "article_samples": [],
  "median_publication_age_hours": null,
  "stored_articles": 0,
  "last_success_at": null
}
```

## CATL Official News

- URL：https://www.catl.com/en/news/
- 方法：html
- 状态：BLOCKED
- 最后验证：2026-11-06T05:28:41.352937+00:00
- 最近真实正文入库成功：无成功证据
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{}
- 耗时ms：509.34
- 正文数/带发布日期数：0/0
- 列表访问成功：False
- 正文获取：False
- 文章发布日期解析：False
- 限制/错误：Cross-host redirect or unsupported URL; manual source review required

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://www.catl.com/en/news/",
  "method": "html",
  "access_success": false,
  "publication_date_parsed": false,
  "body_obtained": false,
  "restriction": "Cross-host redirect or unsupported URL; manual source review required",
  "failure_stage": "robots_or_listing",
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "status": "BLOCKED",
  "last_request_url": "https://www.catl.com/robots.txt",
  "request_count": 1,
  "robots": {
    "https://www.hafen-hamburg.de": "404 no robots file (RFC 9309)"
  },
  "verified_at": "2026-11-06T05:28:41.352937+00:00",
  "duration_ms": 509.34,
  "article_samples": [],
  "median_publication_age_hours": null,
  "stored_articles": 0,
  "last_success_at": null
}
```

## European Commission Internal Market & Industry

- URL：https://single-market-economy.ec.europa.eu/news_en
- 方法：html
- 状态：PASS
- 最后验证：2026-11-06T05:36:49.013487+00:00
- 最近真实正文入库成功：2026-11-06T05:36:49.013487+00:00
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{"status": "reviewed_allowed", "license": "CC BY 4.0", "notice_url": "https://commission.europa.eu/legal-notice_en", "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."}
- 耗时ms：6075.81
- 正文数/带发布日期数：5/5
- 列表访问成功：True
- 正文获取：True
- 文章发布日期解析：True
- 限制/错误：无已观察到的限制（不等于无限制）

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://single-market-economy.ec.europa.eu/news_en",
  "method": "html",
  "parser": "european_commission",
  "reuse_policy": {
    "status": "reviewed_allowed",
    "license": "CC BY 4.0",
    "notice_url": "https://commission.europa.eu/legal-notice_en",
    "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."
  },
  "access_success": true,
  "publication_date_parsed": true,
  "body_obtained": true,
  "restriction": null,
  "failure_stage": null,
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "http_status": 200,
  "discovered": 5,
  "dated_articles": 5,
  "parsed_articles": 5,
  "status": "PASS",
  "last_request_url": "https://single-market-economy.ec.europa.eu/news/eu-tests-reveal-compliance-issues-safety-footwear-2026-10-13_en",
  "request_count": 7,
  "robots": {
    "https://transport.ec.europa.eu": "200 parsed",
    "https://single-market-economy.ec.europa.eu": "200 parsed"
  },
  "verified_at": "2026-11-06T05:36:49.013487+00:00",
  "duration_ms": 6075.81,
  "article_samples": [
    {
      "url": "https://single-market-economy.ec.europa.eu/news/eu-campaign-highlights-lift-buffer-safety-performance-2026-10-29_en",
      "title": "EU campaign highlights lift buffer safety performance",
      "published_at": "2026-10-29T09:40:56+00:00",
      "fetched_at": "2026-11-06T05:36:45.200887+00:00"
    },
    {
      "url": "https://single-market-economy.ec.europa.eu/news/new-brand-association-joins-industry-led-cooperation-tackle-online-counterfeiting-2026-10-29_en",
      "title": "New brand association joins the industry-led cooperation to tackle online counterfeiting",
      "published_at": "2026-10-29T09:50:46+00:00",
      "fetched_at": "2026-11-06T05:36:46.008133+00:00"
    },
    {
      "url": "https://single-market-economy.ec.europa.eu/news/enterprise-europe-network-annual-conference-2026-agile-network-changing-world-2026-10-23_en",
      "title": "Enterprise Europe Network Annual Conference 2026: An Agile Network in a Changing World",
      "published_at": "2026-10-23T11:33:31+00:00",
      "fetched_at": "2026-11-06T05:36:47.040184+00:00"
    },
    {
      "url": "https://single-market-economy.ec.europa.eu/news/eu-tests-put-thermal-insulating-materials-under-spotlight-2026-10-19_en",
      "title": "EU tests put thermal insulating materials under the spotlight",
      "published_at": "2026-10-19T12:25:59+00:00",
      "fetched_at": "2026-11-06T05:36:48.117876+00:00"
    },
    {
      "url": "https://single-market-economy.ec.europa.eu/news/eu-tests-reveal-compliance-issues-safety-footwear-2026-10-13_en",
      "title": "EU tests reveal compliance issues in safety footwear",
      "published_at": "2026-10-13T09:55:52+00:00",
      "fetched_at": "2026-11-06T05:36:49.013402+00:00"
    }
  ],
  "median_publication_age_hours": 330.05,
  "stored_articles": 5,
  "last_success_at": "2026-11-06T05:36:49.013487+00:00"
}
```

## European Commission Trade News

- URL：https://policy.trade.ec.europa.eu/news_en
- 方法：html
- 状态：PASS
- 最后验证：2026-11-06T05:36:55.104319+00:00
- 最近真实正文入库成功：2026-11-06T05:36:55.104319+00:00
- 验证类型：LIVE_HTTP
- 启用：True
- 复用政策：{"status": "reviewed_allowed", "license": "CC BY 4.0", "notice_url": "https://commission.europa.eu/legal-notice_en", "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."}
- 耗时ms：6079.62
- 正文数/带发布日期数：5/5
- 列表访问成功：True
- 正文获取：True
- 文章发布日期解析：True
- 限制/错误：无已观察到的限制（不等于无限制）

```json
{
  "verification_type": "LIVE_HTTP",
  "url": "https://policy.trade.ec.europa.eu/news_en",
  "method": "html",
  "parser": "european_commission",
  "reuse_policy": {
    "status": "reviewed_allowed",
    "license": "CC BY 4.0",
    "notice_url": "https://commission.europa.eu/legal-notice_en",
    "note": "© European Union. EU-owned article text only; excludes logos, images and third-party works. Extracted text and Chinese rule templates are modifications; original source linked."
  },
  "access_success": true,
  "publication_date_parsed": true,
  "body_obtained": true,
  "restriction": null,
  "failure_stage": null,
  "article_errors": [],
  "terms_review": "Automated terms interpretation unavailable; public pages only, obey robots and stop on access restrictions.",
  "http_status": 200,
  "discovered": 5,
  "dated_articles": 5,
  "parsed_articles": 5,
  "status": "PASS",
  "last_request_url": "https://policy.trade.ec.europa.eu/news/commission-acts-against-imports-pea-protein-china-2026-09-25_en",
  "request_count": 7,
  "robots": {
    "https://transport.ec.europa.eu": "200 parsed",
    "https://single-market-economy.ec.europa.eu": "200 parsed",
    "https://policy.trade.ec.europa.eu": "200 parsed"
  },
  "verified_at": "2026-11-06T05:36:55.104319+00:00",
  "duration_ms": 6079.62,
  "article_samples": [
    {
      "url": "https://policy.trade.ec.europa.eu/news/commission-aims-unlock-business-opportunities-eu-medical-device-companies-china-2026-11-05_en",
      "title": "Commission aims to unlock business opportunities for EU medical device companies in China",
      "published_at": "2026-11-05T11:01:54+00:00",
      "fetched_at": "2026-11-06T05:36:51.150192+00:00"
    },
    {
      "url": "https://policy.trade.ec.europa.eu/news/commission-acts-against-imports-pet-spunbond-china-2026-10-30_en",
      "title": "Commission acts against imports of PET Spunbond from China",
      "published_at": "2026-10-30T10:59:23+00:00",
      "fetched_at": "2026-11-06T05:36:52.059123+00:00"
    },
    {
      "url": "https://policy.trade.ec.europa.eu/news/eu-and-canada-conclude-negotiations-digital-trade-agreement-2026-10-30_en",
      "title": "EU and Canada conclude negotiations on a digital trade agreement",
      "published_at": "2026-10-30T16:45:24+00:00",
      "fetched_at": "2026-11-06T05:36:53.091333+00:00"
    },
    {
      "url": "https://policy.trade.ec.europa.eu/news/screening-foreign-direct-investment-continues-advance-eu-security-and-public-order-2026-10-14_en",
      "title": "Screening of foreign direct investment continues to advance EU security and public order",
      "published_at": "2026-10-14T10:00:39+00:00",
      "fetched_at": "2026-11-06T05:36:54.142342+00:00"
    },
    {
      "url": "https://policy.trade.ec.europa.eu/news/commission-acts-against-imports-pea-protein-china-2026-09-25_en",
      "title": "Commission acts against imports of pea protein from China",
      "published_at": "2026-09-25T10:10:55+00:00",
      "fetched_at": "2026-11-06T05:36:55.104267+00:00"
    }
  ],
  "median_publication_age_hours": 162.62,
  "stored_articles": 5,
  "last_success_at": "2026-11-06T05:36:55.104319+00:00"
}
```


## 本轮真实验收摘要（2026-11-06，Asia/Shanghai）

新实例网络为unrestricted/enforced，GitHub API GET实际成功。此前全源CONNECT403已解除；下列不是统一网络阻碍。

- 合格保留正文/日期：15篇；DG MOVE、DG TRADE、DG GROW各5篇，三部门属于同一欧委会机构。重复真实采集各5 unchanged，没有新增重复。
- 三样例已验证原文→解析→入库→独立规则→实际Live页面→原发布日期日报，标题/JSON-LD日期/正文与源HTML逐项对照。证据见docs/LIVE_EVIDENCE_2026-11-06.json与docs/LIVE_ACCEPTANCE.md。
- 复用：© European Union，CC BY 4.0，https://commission.europa.eu/legal-notice_en 。仅EU拥有的文字，正文抽取及中文模板修改已标注，不复用照片/Logo。
- Rotterdam：初次许可审查前临时取得5篇，发现copyright禁止下载/复制后，停用并清理正文/分析/HTML副本，仅保留来源/失败元数据；不计入15篇，不提交受限正文。
- EUR-Lex：robots HTTP202后停止；CATL：robots跨域301后停止；Antwerp/Hamburg：列表可访问但正文发现/解析未成功。
- Maersk/Hapag：修复解压后仅重新探测robots，200且允许列表；正文和复用政策尚未验收（NOT TESTED），未请求文章。不把前一版本的DecodingError继续描述为当前站点阻断。
- 没有改写文章发布日期、伪造官方消息/人工签核，也没有真实等待时间或完整行业覆盖的证明。Issue #2等待Owner审阅，继续OPEN。

## 2026-11-09 Issue #5 第一阶段候选审计

详见 [来源矩阵](docs/SOURCE_MATRIX.md) 与 [逐请求证据](docs/content_source_audit.v1.json)。23 候选：16 PARTIAL、7 BLOCKED，其中 Rotterdam 沿用禁止限制且未请求；22 个执行真实 HTTP 验证。网站访问成功不代表正文许可/文章解析验收。新增真实入库 **0**；既有 15 篇为历史基线。新鲜文章数量未知，不记作零。没有新增 Live 连接器。
