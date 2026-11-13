# ESCIM Phase3 决策支持验收

2026-11-12（Asia/Shanghai）。**ENGINEERING PASS / DEMO PASS / LIVE PRICE CLOSED LOOP PASS / OPERATIONAL & CAPACITY COVERAGE BLOCKED/PARTIAL / WINDOWS NOT TESTED本轮**。基于c11155f继续feature/escim-intelligence-platform，已有DraftPR8；没有基于/修改法规分支，未合并main。第一提交c62207e交付主流程，最终修复/证据另提交。

## A：审计与真实来源

原平台HTML列表/HTML文档、RSS、Atom、JSON API、PDF、CSV/XLSX、原文/版本/审核/报告能力复用，未重建。初始Live4条为HHM3背景+EC电池历史政策1，没有当前运营/真实企业项目/价格数据。原M1官方运营源依然许可不足，CATL/船公司/受限运价未擅自启用。

[来源矩阵30条](phase3/SOURCE_MATRIX.json)含source_id/URL/机构/模块/类型/方式/许可/频率/实际尝试成功率/候选业务数量/最近成功/阻塞。30是配置/旧候选目录并集，不是30个新验证/接入源。未请求来源成功率null，旧候选不自动升级许可。本轮实际再次采集HHM/EC Batteries，并接入EC Weekly Oil Bulletin；另检查EC Industry入口但近期为一般建筑/合规新闻，不填充无关项目。原候选A–E类别另保留catalog_domain；政策候选不启用/不恢复法规RAG。

仅EU公共燃油工作簿新启用：官方https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en ，声明https://commission.europa.eu/legal-notice_en实际HTTP200，EU自有内容CC BY4.0、署名及修改说明，第三方/图片/商标例外不扩展。实际审查见[SOURCE_REVIEW](phase3/SOURCE_REVIEW.json)。原港口/船公司/企业许可未知或受限者保持禁用，人工导入或官方订阅待进一步确认。

## 真实闭环和计数

官方HTML→发现同主机XLSX→robots/TLS/超时/0自动重试→原始HTTP完整响应CAS→工作簿格式/ZIP20MB/非公式数值/币种/单位/日期单元格校验→4条结构化观测→关联明确未知→4决策卡→周报HTML。HTML/XLSX不是Mock，不把文件名日期当事实。

- 真实XLSX：**16,928字节**；SHA256 `8d48ab28011bee8ca5a85a4e0d6725bcdfba62af1ee8a1ca9a5ff48eb03eccdb`。
- 本地`runtime/platform/artifacts/live/8d/8d48ab28011bee8ca5a85a4e0d6725bcdfba62af1ee8a1ca9a5ff48eb03eccdb.bin`，原始下载链接及响应元数据见[LIVE_ACCEPTANCE.json](phase3/LIVE_ACCEPTANCE.json)。不提交工作簿/原始HTML。
- 下载链接文件名含2026-09-21，但**Sheet1!A2为2026-11-09**。来源发布日期未知保留null；观测日按UTC午夜约定存observed_at，并声明日精度，不冒称精确发布时刻。
- A1=in EUR、C1=Automotive gas oil/Dieselkraftstoff、C2=1000 l。Germany C13=2253，显式除1000得**2.253 EUR/litre**；不是换汇、运价或企业合同成本。原始数值、单位、日期和单元格位置序列化存为证据，转换单独标规则换算，不伪装连续网页原文引文。
- Germany/France/Belgium/Netherlands各1条，共**4观测，来自1份工作簿/1机构数据源**。再次实际采集4unchanged、0重复；独立重新打开保存字节逐国核对数值与日期及换算通过。全平台现存Live8条（旧4+新4）。

| 模块 | 当前合格业务数据 | 边界 |
|---|---:|---|
| 港口物流 | 0当前运营通告 | HHM3篇背景不作为港口中断/正常证据；12港状态仍按原服务，未知 |
| 海外产能 | 0真实企业项目 | EC历史政策1篇不是工厂投产；计划不等实际 |
| 市场成本 | 4近期官方燃油观测 | 国家周度含税公共统计，不是实时价/海运指数/合同运费；无上期对照，不报告涨跌幅 |

本周按观测日期纳入4条，今日按原日期为空，不把采集日改成发布日期。本轮没有真实企业订单/成本/路线关联：**Live影响未知、人工核实事实为空、处理pending**，没有自动写“已核实”。源文件/单元格机械核验通过与人类业务核实明确分开。

## B–D：事件、业务关联与决策卡

- 统一原Record/Evidence追加可选effective_at/expires_at/observed_at/transport，显式时区/有效期约束；旧记录None字段不改变原内容指纹，避免升级制造重复。原文不被分析覆盖。
- 规则识别罢工/停工/拥堵/航道/码头/服务中断，新厂/扩产/投资/计划/投产/延迟/取消，燃油/附加费/航线/指数/运价；输出命中原句、实体、时间有效性、状态及置信依据。无工厂/项目/已配置企业上下文的一般投资政策不当企业项目；否定/可能/传闻不变已核实事实；识别能力有限，无语义准确率承诺。
- 关联港口、公司角色、项目、工厂、显式航线/运输方式、柴油成本类别；country可约束国别。配置/CSV/XLSX原子替换、去重/公式/大小/500行校验，来源是USER_PROVIDED。DEMO关联不得进Live。复用既有港口使用Profile，显式typed links优先；仅配置替代港不认定实际使用，Tangier范围未确认仍影响未知。
- 严重度沿用原平台规则，业务匹配和影响potential_unconfirmed/unknown分别显示，无单一综合分数。无业务数据不判低风险。
- 每个当前Evidence绑定DecisionCard，旧Evidence卡保留、当前列表排除旧版本；新证据卡pending，不继承旧处理/事实核实。配置/时间/规则变化可刷新现有投影，原始Evidence与Assessment不覆盖。
- 卡片有摘要、原文/指纹、来源主张、人工已核实声明、未核实假设、结构化值/换算、实体/业务关联、潜在影响、未知/核实事项、候选行动和反馈。
- 处理状态pending/confirmed/ignored/in_progress/resolved，修改人/原因/版本追加Audit。**处理confirmed不等于事实已核实**；另需显式勾选核实当前全部非假设引文，并保留人类声明来源，不声称独立外部核实。
- 候选行动按类型匹配：港口/服务核实货代/在途/候选替代，产能核实项目及投产，市场重询口径与报价。没有延误天数/损失/节省/最优运输方案；历史只核实后续，不作为当前调整依据。

示例：Germany 2026-11-09柴油，原数2253EUR/1000l，规则换算2.253EUR/l；来源主张待核实，严重度unknown，业务相关度unknown，影响unknown。候选行动“重新向承运人/货代获取适用航线、有效期和费用口径的报价”“关注同币种同单位后续观测”；不是建议提高预算某个百分比。

## E–F：UI、报告及运行

统一情报中心增加决策区，默认高价值筛选，关闭可看背景；Sources展示实际样本健康和质量定义。日报/周报复用Report表，增加decision_daily/decision_weekly，区分人工核实、来源主张、推断、用户上下文、候选行动、缺失与来源。忽略/驳回和非本期不填重点；没有新事件明确为空。原报告保留。

新增005_decision仅加decision_cards表，down_revision004_platform；单元测试实际降级/再升级，原Evidence表保留。业务关联和状态/核实审计复用Audit。不修改法规分支、M1风险/纯地图、模块02/03原业务数据，不复制数据库。

本地一次性`python -m scm.platform.cli update`：只到期且enabled来源、单源隔离、增量写入、Live卡刷新、日报周报和source health JSON。退出2表示完成但有来源失败，JSON保留详情；失败不编数据，不加载DEMO。提供PowerShell示例，不注册后台任务。采集失败后既有观测仍明确为原日期快照，不冒充新数据。

## 实际验证

- **281 pytest通过，19.90s，0失败/跳过**；23项新增覆盖时间/计划/实体/影响未知/核实与状态/证据版本/导入/工作簿单位/健康/旧配置复用/迁移回滚/增量到期。原M1、地图框架、GBK等全部通过。
- Ruff src/tests/scripts/新迁移、git diff --check PASS；无Key运行，无付费LLM。
- Chromium155桌面1440和390px，共**10组PASS，0pageerrors**：真实Germany卡/未知影响与核实状态、Live周报渲染下载含2.253和原文、健康披露、DEMO项目匹配和反馈、Manual空/Live隔离，以及港口页仍只有12点纯地图。未重新美化地图或重复整套瓦片SLA测试。
- [浏览器JSON](evidence/phase3/browser.json)、[真实卡](evidence/phase3/desktop-real-card.png)、[390px真实卡](evidence/phase3/mobile390-real-card.png)、[真实周报示例](evidence/phase3/LIVE-weekly-example.html)、[DEMO反馈](evidence/phase3/desktop-demo-feedback.png)。失败尝试单独记录iterations.json：状态控件改为明确中文单选，下载竞争重跑采用on_click=ignore修复，最终新进程/会话通过。
- 原生Windows修复后/PowerShell任务计划/实体触屏本轮NOT TESTED；用户此前Windows基础启动已反馈成功，不把本轮Linux模拟/浏览器称Windows原生通过。

## 限制、后续最少输入与停止

生产覆盖仍PARTIAL：运营源许可/企业公告/运价指数未获准，不抓未知许可正文；只有4国柴油观测，不做时序涨跌或企业成本预测。原文模式/存在引文不保证语义或真实性，人工需核实，候选不是执行指令。date-only午夜是存储约定。反馈不自动训练模型/改风险等级；Audit自报身份，不是企业认证或不可篡改审计。新报告是本地单用户MVP。

用户最低可选输入：一份脱敏关联（港口或国家/路线、运输方式、成本类别、公司角色/项目编号），不给也能运行但影响未知；不需要真实订单、客户、报价或内部产量。其他来源需先核实许可或官方订阅，无需本轮购买API。运行/Windows步骤见[PHASE3_WINDOWS](PHASE3_WINDOWS.md)。代码/证据推送现有PR8，保持Draft，不合并，不自动恢复PR7；完成后停止等待验收。
