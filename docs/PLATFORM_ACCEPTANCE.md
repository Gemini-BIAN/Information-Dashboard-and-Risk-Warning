# ESCIM 统一供应链情报平台验收

2026-11-11（Asia/Shanghai）。**FRAMEWORK PASS / MOCK PASS / LIVE PARTIAL / WINDOWS NOT TESTED**。

## 分支保护与可运行范围

本分支 `feature/escim-intelligence-platform` 直接从 `feature/supply-chain-risk-mvp@7d6fbc99181644ce4a4c55a3d6283e036ecdf148` 创建，不包含法规RAG提交。`feature/regulatory-rag-mvp@8a31da45cf03be67f52c83737b31fc1f0ac8cc10` / Draft PR7保持不动。main、PR1、PR7未合并/覆盖。这里 Module02 是海外产能与竞争情报；暂停的法规RAG不属于本分支。

Module01 的 `src/scm/ports`、`src/scm/ui`、`config/ports.json`、`config/port_sources.json` 与基线无差异；新入口复用其完整renderer、离线地图、通知和状态服务。原六工作台启动命令不变。新增平台页面、企业与市场流程及迁移独立，默认库`runtime/platform/platform.db`，未迁移/写入用户原`runtime/scm.db`或法规库。

## 功能验收

| 范围 | 实现与证据 | 状态 |
|---|---|---|
| Module01 | 12地点原地图/侧栏、搜索、独立国家地点、双风险、历史与原收件箱；新统一页亦展示候选港口资讯及审核；AIS/等待时间/ETA仍未知 | FRAMEWORK PASS；当前运营Live覆盖不足 |
| Module02 | 配置企业/别名，国家、工厂、项目ID、计划产能/单位、投资/币种、计划投产日期、7种状态；明确ID+企业关联新闻时间线，每条保留版本与来源；不将计划当实际产能 | FRAMEWORK/MOCK PASS；真实企业项目0 |
| Module03 | 航线、企业/承运人、公告/观测价格/指数/人工输入/模型估计独立类型、金额币种单位验证；人工CSV/XLSX，待批准API适配契约 | FRAMEWORK/MOCK PASS；实时价格0 |
| 统一中心 | 三空间、主题/模块、文本、国家、企业、风险、日期、审核状态筛选；原文、SHA、发布时间/抓取时间/更新版本、规则理由、条件影响、人工确认/驳回/原因、CSV导出 | PASS |
| 原始证据 | 追加Evidence和独立Assessment，正文不被分析覆盖；获准HTTP完整响应CAS保存为.bin，校验已有文件，原始HTML重新解析与库内正文一致 | PASS（4真实文章） |
| 版本/事务 | 源+外部ID+空间唯一；忽略抓取时间的业务内容哈希；相同不新增、变化追加、旧审核失效、倒序抓取拒绝、单记录savepoint/单源异常隔离、事务回滚 | PASS（自动测试） |
| 报告 | daily/weekly HTML和历史记录，按Asia/Shanghai原发布日期；排除驳回/业务排除记录，明确项目分组并保留各原始来源；12港生成时状态明确区别于报告周期实况；空日报不凑数 | PASS |
| 预警 | 规则文本证据、pending/read/handled、本地收件箱，旧版本提醒；Module01沿用原服务可标已读；无邮件/外部发送 | PASS |
| Sources | 配置来源类型、许可、频率/覆盖/可信度、最近真实成功和失败日志、请求数/重试0、原始响应路径和SHA；单源执行/测试；未批准在HTTP前拒绝 | PASS |
| 适配器 | HTML列表/单页文档、RSS、Atom、约定JSON API、PDF文字、手动CSV/XLSX | MOCK PASS；仅两HTML列表真实接入 |

数据库迁移004_platform增8表，down_revision003，保留既有表。与暂停RAG的004是两个不同分支，未来若合并两条分支需要显式协调迁移图；本轮不做合并/迁移重排。首次提交b564a41为框架，后续提交为原始响应校验、浏览器修复与验收文档。

## 真实来源与业务边界

实际使用此前已获准两来源，30日有效证据及本次法律声明重新HTTP读取见[来源审计](platform/SOURCE_AUDIT.md)、[LIVE_EVIDENCE](platform/LIVE_EVIDENCE.json)。仅继承代理、TLS、SafeFetcher robots-first、同主机重定向/4MB解压后限制、速率控制；本平台自动重试0，不绕过限制。HTML正文许可不扩展到图片/Logo或受限第三方内容。

| 来源 | 实际入库 | 真实业务结论 |
|---|---:|---|
| Hamburg HHM | 3 | 会议、技术背景、接待；均excluded，不当作当前港口中断 |
| EC Batteries | 1 | 2025-07-04历史政策背景，possibly_relevant；无企业项目/产能/实际投产事实，结构字段unknown/空 |

共**4篇真实记录、0真实当前运营通告、0企业项目、0价格观测**。最近文章2026-11-05，其他为2026-10-20/10-12与2025-07-04，未改成今日新闻。当前Live日报实际为空并解释覆盖不足；按原2025-07-04生成历史日报能显示实际电池政策。12港口Live当前状态全部unknown；不能从缺资讯断定正常。

重复真实采集4 unchanged、0新增；独立重新获取两篇样例比对标题/正文/日期通过。后续原始响应捕获也是4 unchanged。[原始响应校验](platform/RAW_CAPTURE_EVIDENCE.json)逐篇校验实际字节/SHA，并重新解析已保存HTML；含官方canonical URL与请求URL不同时的合法关联。抓取时页面整体HTML可能变化而正文不变：响应SHA与业务正文指纹分别保留，不制造内容版本。

第一轮沙箱在robots连接阶段ConnectError，未取得远端响应；按环境规则在沙箱外用同一代理/TLS请求后成功；[失败证据](platform/SANDBOX_NETWORK_FAILURE.json)保留，不称网站403或绕过限制。

## 数据隔离和业务判断

- Live仅经显式许可门槛及真实HTTP；注入Mock客户端强制DEMO，不写Live来源成功时间。Manual导入不能指定Live/DEMO来源类型。数据空间贯穿Item、Evidence归属、Alert、Report、Audit及查询。
- 合成5条平台记录仅显式加载DEMO；另复用原Module01的2条虚构通知。合成企业/项目/价格不作为真实接入数量。Manual有效/错误/重复/XLSX/公式测试在临时测试库完成，实际验收库Manual0。
- 数据状态verified/candidate/unavailable/failed独立于审核和来源连通性。自动Live记录保持candidate，人工确认只记审核，不自动把所有结构字段或法律适用性变为verified。
- 复用原业务相关性筛选；数据源覆盖模块不等于文章已证明该模块业务事件。EC法规背景列在容量模块的背景候选，但企业/项目/产能未知，不当作企业投资新闻；后续须接入获准企业源。
- 规则保留原句、评估版本及时间。近期明确文内信号最多为待核实medium，其余unknown；不提供概率、高等级预测或LLM虚构结论。历史/未来/未知日期及否定词有降级。当前展示按当前时间重新评估，存储的原分析不覆盖；长期已过期记录不会继续冒充当前风险。
- 项目/状态/数值需要原文中存在的引文，但这只是工程门槛，不保证语义完全支持；CSV/API声明仍需人工核实。不会从模糊新闻自动提取“投产”或计划产能作为事实。
- 币种不做暗中换汇；不同计量单位不自动合计。国家代码采用常见别名与alpha2格式，非完整地缘身份数据库。日期要求时区、统一UTC，报告按Asia/Shanghai；旧HTML日期精度沿用原解析器约定。

## 实际测试

- Python3.12.14/Linux：`pytest -q --junitxml=runtime/platform/test-results.xml`，**251 passed in17.63s，0 failed/0 skipped**；原204项全部通过，新增47项。
- `ruff check src tests scripts migrations/versions/004_intelligence_platform.py` PASS；`pip check` PASS；`git diff --check` PASS。
- 三模块均有空数据、错误输入、失败/重复采集、事务回滚与纵向测试。Mock HTTP→解析→存储→规则→报告→预警在三个模块参数化验证。RSS/Atom/API/HTML/PDF成功与错误/空壳均有合成测试；不把它们算Live适配验收。
- Chromium155：桌面1440×1000与移动390×844，**16组检查PASS，0pageerror**，两视口均无页面级横向溢出。逐视口实际导航七工作台，原12点地图显示/点击Dover详情，真实4条和CSV导出，DEMO项目时间线/市场数据/HTML下载/预警已读，Manual空结果、Live隔离、搜索无结果与重置。
- [浏览器JSON](evidence/platform/browser.json)、[桌面地图](evidence/platform/desktop-ports-live.png)、[390px地图](evidence/platform/mobile390-ports-live.png)、[产能](evidence/platform/desktop-capacity-demo.png)、[市场](evidence/platform/desktop-market-demo.png)、[DEMO报告](evidence/platform/DEMO-sample-report.html)。其余截图同目录。
- 浏览器开发迭代发生覆盖原生radio输入/同名卡片定位/日报选到旧周报等脚本问题；按实际可见标签和具体卡片修复。报告历史按生成时间排序修正；开发进程旧导入模块导致一次source_confidence KeyError，全新进程最终通过。失败记录见[迭代证据](platform/BROWSER_ITERATIONS.json)，未把失败尝试冒称PASS。最终浏览器使用全新进程与会话。
- Windows原生、真实价格API/企业项目API、Live RSS/Atom/PDF、外部消息、跨日常驻调度 **NOT TESTED**；复杂PDF/OCR/图表语义未实现。已给PowerShell/PyCharm命令，不冒称实跑。

## 存储、运行与后续

本地库`runtime/platform/platform.db`；完整响应`runtime/platform/artifacts/<live|demo>/<SHA前2位>/<SHA>.bin`，原始Evidence/分析分别在DB。日报HTML与JUnit在runtime/platform下。runtime与data/regulatory均忽略Git，不提交源站完整HTML/PDF、研究附件、真实内部物流数据或密钥。证据只提交获准摘录/元数据/本地页面截图；原始响应.bin不直接在浏览器执行。

[Windows/PyCharm运行说明](PLATFORM_WINDOWS.md)；[待接入清单](platform/SOURCE_BACKLOG.md)。报告/采集CLI可被本机任务计划程序调用，`collect --due`按配置间隔选到期来源；未安装常驻调度器或外发消息。GitHub CI/最终SHA见新Draft PR回执，不能拿本地PASS替代远程CI。本轮结束后等待审核，不自动进入法规RAG或扩大付费接入。
