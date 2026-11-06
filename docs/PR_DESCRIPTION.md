## ESCIM：本地MVP及Issue #2/#3修复

继续feature/supply-chain-risk-mvp，保持Draft，不合并main。原MVP含六工作台、SQLite/Alembic、HTML/RSS框架、风险/人审、ETA快照及报告/调度。

### 本轮实际完成

- 修复政策状态：历史生效日期不自动升级实施，明确废止优先；生效/到期/废止日期独立，矛盾未知，保留原文依据。
- 独立运营生命周期、文内严重度和来源可信度；解除/取消/矛盾/历史/假设/范围不明不自动抬高当前港口风险。多港口分句归属，announced上限中，active按证据。
- 002迁移、旧记录幂等重算、原文/分析保留、前后规则判断审计，失效人审。UI/报告显示依据和不确定性。
- 按来源/日期检查Live覆盖，失败、未测、Mock或缺日期不声称无重要新闻。新增耗时、失败URL/阶段、次数、发布日期年龄和最近真实成功时间。
- 同域重定向逐跳遵守robots；跨站RSS须明确复核；代理确定性403不盲目重试。

### 实际测试

完整pytest：93 passed，0 failed/0 skipped；ruff通过。保留47项原测试路径并按Review增强2处断言，新增46项。覆盖迁移、法规优先级、生命周期/归属、覆盖报告、遥测、无API核心、六页面、ETA、HTML和审计。

### 阻碍与问题

10个官方源实际HTTP尝试全部在robots.txt CONNECT阶段403，真实正文0、Live事件0。**Issue #2保持OPEN/BLOCKED，尚不满足至少2个官方源及真实事件全链路验收。** 不伪造真实原文Fixtures或采集成功。

Issue #3代码和本地验收完成，仍需Owner审阅；词法规则不承诺完整法律语义、当前港口实况或延误准确率。真实LLM、Windows、持续跨日调度未测试。

GitHub公开网页可读，已读Owner Review及Issue #2/#3；API写入仍Forbidden。修复提交64e1016的push与PR synchronize两次Actions均已从公开网页确认成功（运行42155814204、42155815831）；未以旧CI代替。

### 后续

将保存的域名策略实际应用到实例，复测2–3官方源并补真实解析、原文回归、人工事实核验和Live端到端。详见SOURCE_AUDIT、TEST_REPORT、docs/LIVE_ACCEPTANCE、docs/ISSUE_RESULTS、PROJECT_STATUS及KNOWN_LIMITATIONS。

无付费API、公司敏感数据上传或公网部署。请保持Draft，不自动合并。
