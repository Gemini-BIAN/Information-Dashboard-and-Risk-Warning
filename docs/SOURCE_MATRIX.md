# 官方来源矩阵 V1 — 第一阶段

2026-11-09（Asia/Shanghai）。23 个候选，22 个实际网络验证，Rotterdam 仅复核既有禁止规则，未发请求。一次有超时审计，不自动接入生产。

本轮：{'PARTIAL': 16, 'BLOCKED': 7}。PASS=访问、权限和所声明解析均完成；PARTIAL=列表可达但许可/文章解析未验收；BLOCKED=明确限制或请求失败；NOT TESTED=未验证。所有正文、逐篇发布日期和七日新鲜数量尚未验收（null，不是 0）。

机器目录：`config/content_sources.v1.json`（独立于运行配置）；逐请求 URL/HTTP、错误、robots、时延证据：`docs/content_source_audit.v1.json`。`publication_date` 是列表首个可见日期元数据，不是已核对的文章发布日期。

| 来源/机构 | 领域/优先级 | 方法/建议间隔 | 本次状态/阶段 | HTTP/错误 | 日期样本/秒 |
|---|---|---|---|---|---|
| [EC DG MOVE](https://transport.ec.europa.eu/news-events/news_en) / european-commission | A/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 2026-11-04T12:00:00Z / 2.59 |
| [EC DG TRADE](https://policy.trade.ec.europa.eu/news_en) / european-commission | B/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 2026-11-06T12:00:00Z / 2.29 |
| [EC DG GROW](https://single-market-economy.ec.europa.eu/news_en) / european-commission | C/P1 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 2026-10-29T12:00:00Z / 6.48 |
| [EC Environment Batteries](https://environment.ec.europa.eu/topics/waste-and-recycling/batteries_en) / european-commission | B/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.46 |
| [EC Dangerous Goods](https://transport.ec.europa.eu/transport-themes/dangerous-goods_en) / european-commission | B/P0 | html_metadata / 6h | BLOCKED / robots/listing | 200, 404; Client error '404 Not Found' for url 'https://transport.ec.europa.eu/transport-themes/dangerous-goods_en' | 未知 / 1.88 |
| [EUR-Lex Official Journal](https://eur-lex.europa.eu/collection/eu-law/oj.html) / eu-publications-office | B/P0 | html_metadata / 6h | BLOCKED / robots/listing | 200, 404; Client error '404 Not Found' for url 'https://eur-lex.europa.eu/collection/eu-law/oj.html' | 未知 / 10.46 |
| [IMO Dangerous Goods / IMDG](https://www.imo.org/en/OurWork/Safety/Pages/DangerousGoods-default.aspx) / imo | B/P0 | html_metadata / 6h | BLOCKED / robots/listing | 301, 301, 301, 301; Too many redirects | 未知 / 3.13 |
| [UNECE ADR 2025](https://unece.org/transport/dangerous-goods/adr-2025-files) / unece | B/P0 | html_metadata / 6h | BLOCKED / robots/listing | 403; robots.txt HTTP 403; fail closed | 未知 / 0.35 |
| [Port of Rotterdam](https://www.portofrotterdam.com/en/news-and-press-releases) / port-rotterdam | A/P0 | link_only / Noneh | BLOCKED / restriction_review | 未请求; 禁止下载/复制；先前正文已清理，没有新许可不得恢复。 | 未知 / 0.02 |
| [Port of Antwerp-Bruges](https://www.portofantwerpbruges.com/en/news) / port-antwerp-bruges | A/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 3.2 |
| [Port of Hamburg](https://www.hafen-hamburg.de/en/press/news/) / port-hamburg-marketing | A/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 404, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.77 |
| [Maersk Advisories](https://www.maersk.com/news/category/advisories) / maersk | A/P0 | html_metadata / 6h | PARTIAL / terms | 200, 200, 404; Client error '404 Not Found' for url 'https://www.maersk.com/terms-and-conditions' | 未知 / 2.57 |
| [Hapag-Lloyd Operational Updates](https://www.hapag-lloyd.com/en/services-information/news.html) / hapag-lloyd | A/P0 | html_metadata / 6h | PARTIAL / terms | 200, 200, 404; Client error '404 Not Found' for url 'https://www.hapag-lloyd.com/en/legal.html' | 未知 / 2.53 |
| [MSC Customer Advisories](https://www.msc.com/en/newsroom/customer-advisories) / msc | A/P0 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.46 |
| [US EIA Weekly Diesel (fuel proxy)](https://www.eia.gov/petroleum/gasdiesel/) / us-eia | D/P1 | dataset_reference / 168h | PARTIAL / completed_metadata_audit | 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.15 |
| [EC Weekly Oil Bulletin (retail fuel proxy)](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) / european-commission | D/P1 | dataset_reference / 168h | PARTIAL / completed_metadata_audit | 200, 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.32 |
| [Shanghai Shipping Exchange SCFI](https://en.sse.net.cn/indices/scfinew.jsp) / shanghai-shipping-exchange | D/P1 | dataset_reference / 168h | PARTIAL / completed_metadata_audit | 404, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.18 |
| [CATL Official News](https://www.catl.com/en/news/) / catl | C/P1 | html_metadata / 6h | BLOCKED / robots/listing | 301; Cross-host redirect or unsupported URL; manual source review required | 未知 / 0.37 |
| [BASF News Releases](https://www.basf.com/global/en/media/news-releases) / basf | C/P1 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.48 |
| [LG Energy Solution Press Releases](https://news.lgensol.com/company-news/press-releases/) / lg-energy-solution | C/P1 | html_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 3.11 |
| [Samsung SDI News](https://www.samsungsdi.com/sdi-now/sdi-news.html) / samsung-sdi | C/P1 | html_metadata / 6h | BLOCKED / robots/listing | 200, 404; Client error '404 Not Found' for url 'https://www.samsungsdi.com/sdi-now/sdi-news.html' | 未知 / 3.36 |
| [UNCTAD Review of Maritime Transport](https://unctad.org/topic/transport-and-trade-logistics/review-of-maritime-transport) / unctad | D/P1 | dataset_reference / 168h | PARTIAL / terms | 200, 200, 404; Client error '404 Not Found' for url 'https://unctad.org/about/terms-and-conditions' | 未知 / 7.45 |
| [NOAA NHC Atlantic Advisories](https://www.nhc.noaa.gov/index-at.xml) / noaa-nhc | E/P1 | rss_metadata / 6h | PARTIAL / completed_metadata_audit | 200, 200, 404, 200; Listing accessible; article dates, freshness, body reuse and connector not accepted. | 未知 / 2.56 |

## 权限与可重复性

所有目录 `terms_url` 为候选或本轮可达 URL；HTTP 可达不等于已经许可。完整许可、复用条件及未知项见机器目录 reuse_permission/reuse_notes；本轮条款页仅验证可达与标题，法律语义复核仍 NOT TESTED。既有欧委会 CC BY 4.0 审查只作历史基线，排除第三方图片/Logo，第二阶段重新核实；其多个总司不计多个机构。

Rotterdam 禁止下载/再利用，保持 link_only，last_verified_at=null 表示本轮没有 HTTP 验证；限制证据沿用 SOURCE_AUDIT.md 历史记录，不能以本轮复核时间冒充网站验证时间。Maersk/Hapag/UNCTAD 条款失败仍允许记录已成功的列表访问，不能升级为许可。SSE 不假定免费指数授权，EIA/欧盟油价不冒充船燃/海运价格。

复现：`timeout 400s python scripts/audit_content_sources.py`，使用现有代理/TLS，retries=0，robots-first，同主机 HTTPS 重定向，失败来源本轮不重试。首次沙箱网络 socket 被禁；获准环境网络执行后得到本报告的实际 HTTP 证据，未变更网络策略。审计不保存正文、不写数据库。

## 第二阶段入口（等待授权）

优先核实 UNECE ADR、IMO 跳转和欧委会危险品/EUR-Lex 有效入口；不绕过 robots 或跨主机重定向保护。Antwerp、Hamburg、MSC、BASF、LG 的页面可达，需条款许可/文章日期/正文解析验证后再选 2–3 个连接器。成本指标和 NOAA 只按代理/背景事件使用。没有新独立机构完成可重复真实入库，不能宣称 Issue #5 整体验收通过。

## Phase 2A 后续（2026-11-09）

上述23源结果保留为Phase1历史。有限6源权限/逐篇验证更新见PHASE2_SOURCE_MATRIX.md：Hamburg与EC Batteries有条件文字许可并真实入库3+1；MSC/BASF/LG link_only、Antwerp unknown。当前2机构仅相对EC新增1个；真实业务相关性与空日报的PARTIAL验收见PHASE2_ACCEPTANCE.md，不把网站可达等同于业务通过。
