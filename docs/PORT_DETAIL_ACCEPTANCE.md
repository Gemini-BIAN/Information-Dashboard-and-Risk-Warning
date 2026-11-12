> 更新：一级页面已由纯交互世界地图替代，不再常驻摘要卡；本报告的旧一级截图仅为历史，四标签内容保留。最新验收见[WORLD_MAP_ACCEPTANCE](WORLD_MAP_ACCEPTANCE.md)。

# PR8 港口二级详情页验收

2026-11-12（Asia/Shanghai）。功能与本地自动化/真实浏览器验收PASS；Windows原生本轮NOT TESTED。基线db05c81，继续feature/escim-intelligence-platform及Draft PR8，未合并main，法规分支/PR7不改。

## 实现

统一平台入口`src/scm/platform/app.py`的港口页新增「地图→简洁摘要→查看详情→四标签页→返回地图」流程。复用原离线MAP组件、Registry、snapshots风险服务及原始数据空间。原六工作台入口和旧Module01 renderer保留，不改变其风险、通知、规则或来源配置。

- **概览**：Registry名称/国家/UNLOCODE/位置与精度、范围说明；原服务运营状态和风险、相关度、原因、最近资料、来源核查/成功/权限审计时间、覆盖情况、船舶指标未知；本港既有Alert及已读操作。
- **公告时间线**：明确生效/发布时间、实际发生时间未知；类型、状态、时间范围筛选；原始RawRevision/Evidence历史版本，历史记录不继承新版本的生效时间。当前状态仅由原snapshots判定；背景资料不计为当前运营公告。筛选日期按Asia/Shanghai。
- **来源证据**：机构/保存的来源名、转发主体待核实提示、原文链接、摘录、发布/采集时间、审核状态、原始内容指纹及正文SHA256；说明内容指纹包含标题/日期/字段，不冒充原始HTTP字节SHA。原始HTTP响应校验证据仍见docs/platform/RAW_CAPTURE_EVIDENCE.json。
- **业务影响**：规则运营风险和公告相关度独立显示；用户可填脱敏使用情况、航线、运输方式、货物、既有12地点内候选替代港；企业影响始终待核实，不凭配置推导真实运输或影响等级。未配置明确未知，不虚构低/中/高影响。配置按port+live/demo/manual分开，以既有Audit追加保存修改人/原因，不建新库或新业务表。

深链接`?port=hamburg&port_view=detail`支持新会话/刷新。返回后保留所选港口；独立持久会话值不依赖被详情页卸载的地图selectbox键，防止筛选重跑后退回Antwerp。无付费地图、LLM或外部资产。

## 数据与可追溯性

`src/scm/ports/detail.py`只读投影既有Event/RawRevision/Analysis/PortSignal、platform Item/Evidence和PortAlert；不复制正文进新表，不覆盖原分析。规范URL改变仍通过已保存Analysis.port01的源+通告编号找回旧RawRevision。记录有事件内版本序号、原始ID、当前/旧版本标记。没有保存的旧元数据不自行重建；普通历史审核状态不冒充当前人工确认。

真实数据库沿用runtime/platform/platform.db。本轮没有新抓新闻，复用上轮实际取得并校验的公开文章。汉堡有3条匹配原文明示港名的背景记录，TangerMed有1条共享背景引用；不是新增/独立新闻数。关联只用于背景证据展示，不提升状态或覆盖。Live各港无合格当前运营证据，仍unknown。

浏览器实际打开platform-6证据：

- 原文：https://www.hafen-hamburg.de/en/press/news/11th-chainport-annual-meeting-at-tanger-med-focuses-on-scaling-ai-in-ports/
- 已保存内容指纹：`7db6ae110ee88f387a24d457c9c273696bf9f88acc5cfb78217ca787895be1d5`
- 原文正文SHA256：`6a83e75a2541cce18ecc818ce46d4c544fdb23634528236344515a32b04b45bb`

来源名不自动等于转发文章的原发布机构，页面提示待核实。DEMO仅显式加载，Manual信息不能改变运营快照；同一港口三空间证据/配置不互相借用。

## 测试与验收

- 完整pytest：**258 passed in20.47s，0失败/跳过**；含原Module01、GBK编码回归及平台测试。JUnit runtime/port-detail/tests.xml。新增4项测试覆盖12详情/多次重跑/返回，旧URL版本与原文SHA，历史事件不为当前正常，DEMO与Live/Manual及不同港口配置隔离，无配置未知。
- `ruff check src tests scripts`、`git diff --check` PASS。原engine/service/risk、Registry数据和来源配置、迁移均无改动。
- Chromium155：桌面1440×1000和390×844各7组，共**14组PASS**，0pageerrors，均无页面横向溢出。每视口全部12港完成摘要→详情→返回；地图点击Hamburg摘要、真实证据SHA/原文链接、当前筛选为空、未知业务影响、深链刷新、DEMO配置保存及Live/Manual隔离均实际验证。
- [机器回执](evidence/port-detail/browser.json)、[桌面地图摘要](evidence/port-detail/desktop-map-summary.png)、[移动地图摘要](evidence/port-detail/mobile390-map-summary.png)、[桌面概览](evidence/port-detail/desktop-overview-top.png)、[390px概览](evidence/port-detail/mobile390-overview-top.png)、[来源证据](evidence/port-detail/desktop-real-evidence.png)、[移动时间线空态](evidence/port-detail/mobile390-timeline-empty.png)、[业务影响](evidence/port-detail/desktop-business-top.png)。完整截图同目录。
- 开发中发现选择控件卸载后回地图丢失选择，已修复并增加详情多次重跑回归；浏览器瞬时旧新标题并存与刷新早于URL提交属于测试等待问题，已按完成的路由/DOM状态等待。失败尝试记录[iterations.json](evidence/port-detail/iterations.json)，不当作PASS。最终使用全新Streamlit进程与浏览器会话。

## 本地运行与限制

原命令不变：`python -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false`，选择01港口与物流，地图选港→查看详情。Windows/PyCharm详见PLATFORM_WINDOWS.md，更新代码后应先停止旧进程再启动。没有新依赖或迁移。

`python scripts/port_detail_browser_uat.py`要求localhost8530、既有真实背景验收数据，写入仅限DEMO脱敏测试配置/DEMO已读状态；不用于用户未知数据工作库的无提示自动操作。截图及正文来源©European Union/HHM许可见既有来源审计，仅复用已获准文字，无源站图片/Logo。配置字段请勿填敏感业务资料。

原生Windows/触屏设备、真实拥堵/AIS/等待时间/ETA、真实企业业务适用、替代港可用性均NOT TESTED/未知。没有当前运营通告时空状态不证明正常；背景证据命中港名不证明运输影响。后续真实源覆盖仍受原许可限制，本轮不新增爬虫/数据购买/对外部署。不合并PR，完成后停止等待审核。
