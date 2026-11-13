# 本轮来源接入/复用审计

2026-11-11。本轮复用Phase2A已有批准，并实际重新读取两份声明；摘录、HTTP状态、SHA、robots和时间见LIVE_EVIDENCE.json。HTML正文与原始响应仅本地合法保留，不取图片/Logo，不绕过挑战。权限门槛独立于robots、默认未知拒绝；30日失效。

| 来源 | 方式 | 访问/正文/日期 | 许可 | 本轮结果 |
|---|---|---|---|---|
| Hamburg HHM | HTML列表+原专用正文解析 | robots404按RFC9309；列表/3正文200，3日期 | 显示信息可存储分享、不改变/歪曲、署名；图片另有权利；不称HHM原创所有第三方文字 | 3条真实背景，excluded |
| EC Batteries | HTML列表+原EC解析/canonical | robots200，列表/正文200，原2025-07-04 | EU自有文字CC BY4.0，署名/修改说明；排除第三方/Logo | 1条历史政策possibly_relevant |
| CATL | 待许可HTML | 本轮未请求 | 未批准 | unavailable；不可称接入成功 |
| Maersk | 待许可HTML | 本轮未请求 | 未批准 | unavailable |
| price-api占位配置 | JSON API契约，disabled | 本轮未请求，无供应商 | 未配置/未批准 | unavailable，无实时价格 |

真实完整响应4篇文章+2入口已在本地CAS保存；RAW_CAPTURE_EVIDENCE.json逐篇重开字节和解析比对通过。第一轮沙箱仅ConnectError、robots连接未完成；沙箱外相同代理与TLS成功，失败日志保留。重跑4 unchanged，未把来源检查时间改成新闻发布日期。

权限验证说明页：https://www.hafen-hamburg.de/en/imprint/ 与 https://commission.europa.eu/legal-notice_en 。本审计是工程/公开条款核查，不冒称用户法务签核；source candidate状态不自动变成业务verified。

原始证据元数据与文章链接见LIVE_EVIDENCE.json；当前4篇不能填充真实当前运营/实际产能/价格覆盖。Module01原来源配置与权限判断不变。
