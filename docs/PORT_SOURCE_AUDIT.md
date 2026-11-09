# Module 01 官方运营来源权限门槛

2026-11-09（Asia/Shanghai）。仅3个优先来源；逐请求HTTP、robots、阶段、时间与错误见PORT_SOURCE_AUDIT.json。先审计列表/条款，未取通告PDF或运营正文。所有候选需独立授权，不沿用HHM许可。

| 来源 | 实际访问 | 权限结论 | 运营接入 |
|---|---|---|---|
| Le Havre S-WiNG /avis | 两次robots200，随后列表ReadTimeout（20秒请求超时） | NEEDS_PERMISSION/访问BLOCKED；条款、逐篇日期未取得 | 0；停止重试，人工链接 |
| PD Ports Notice to Mariners | robots200，列表200，Terms & Conditions200 | NEEDS_PERMISSION；一般免责声明/All Rights Reserved不是自动复用许可 | 0；不取PDF；Teesport/Middlesbrough共享候选，但不算实际覆盖 |
| Hamburg HPA Traffic Tower | robots404按RFC9309；列表/Imprint/Terms of Use200 | restricted；Terms of Use明确要求商业/非商业内容使用均事先书面同意 | 0；不以Imprint较宽松表述覆盖更严格条款 |

Rotterdam新闻与PIN未请求，保留restricted/未授权。Dover仅人工链接，Community Portal不访问；Antwerp沿用Phase2A未知许可；其余未列新来源，不扩展为12个爬虫。真实运营情报0，非空真实运营日报NOT TESTED；不得把Phase2A四篇背景文章作12港口覆盖。

只为审计请求公开列表/法律页面，不绕过限制。真实来源“可访问”不等于“working verified”；本轮没有满足自动采集+内容保留双门槛的来源，因此不启用任何Live运营连接器。后续可取得书面许可或明确允许的官方RSS/API，再以相同保护接入。现阶段产品业务验收PARTIAL，但12港口空状态、风险/预警逻辑仍可独立验证。
