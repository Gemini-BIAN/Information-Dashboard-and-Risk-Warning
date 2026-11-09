# ESCIM 模块01验收 — 技术PASS / 业务PARTIAL

2026-11-09（Asia/Shanghai）。依据Issue #6最新修订评论6735021252，在feature/supply-chain-risk-mvp完成四检查点；PR1保持Draft，main不合并，Issue5 Phase2B继续暂停。

## 交付与真实数量

- 12个独立业务地点、离线世界地图/12标记、右侧详情、搜索/国家筛选、30日默认历史和扩展检索。London已替换为Dover；Teesport/Middlesbrough不合并；Tangier→Tanger Med仍待确认，不能据此确认当前运营状态。
- 运营严重度与电解液/危险品/ISO Tank业务相关性分开；公布、抓取、有效期、生命周期、来源置信度独立保存；原文、中文规则/可选AI推测及核实任务分开。明确正常必须有当前原文；解除一条通告不代表整个港口正常。
- 编号通告身份、共享范围、版本、去重站内收件箱、已读、升级/解除通知与独立port_daily日报。只发站内通知，无邮件/企微。AIS/ETA/拥堵/等待时间均预留未接入，没有数字或预测。
- **真实运营源接入0、真实运营通告0、已确认当前真实事件0。** 审计3个优先源，均未通过自动使用/复用双门槛。没有取通告PDF、没有请求Rotterdam新闻/PIN，没有把HHM或Phase2A四篇背景当作运营数据。
- 明确Demo种子仅用于功能验收：2条虚构通告（共享River Tees、Dover计划限制），2条事件级通知；不进Live。Live空日报实际生成/下载，不用旧闻或Demo填充。

## 四个检查点与证据

| 检查点 | 状态 | 可验证结果 |
|---|---|---|
| 1 注册表+世界地图+侧详情 | PASS（技术） | a5a0a62；config/ports.json、离线Natural Earth公共领域底图；注册表及12切换AppTest3项通过；浏览器后续逐点点击全部12 |
| 2 官方来源权限与接入门槛 | 审计PASS / 真实业务BLOCKED | 94a306b；PORT_SOURCE_AUDIT.json逐请求HTTP/robots/时间/失败阶段；3源无获准自动接入，0运营正文/PDF；严格零请求门槛实跑 |
| 3 事件/双风险/AI/通知/日报 | PASS（离线/合成+空Live） | 1f4d116及最终修复；已有ingest/RawRevision/Analysis复用，新增003隔离表；旧数据保留；真实非空通告链路NOT TESTED |
| 4 浏览器+回归+文档 | PASS（有限范围） | 204 pytest、ruff；Chromium155真实10组浏览器检查及最新日报局部复核通过；PNG/HTML/JSON与SHA256清单归档 |

最终提交和同SHA CI结论以PR/Issue实际回执为准，不用前一SHA成功代替本轮；不将技术PASS等同于12港口实时业务覆盖。

## 12地点实际覆盖

所有地点Live当前状态**未知**，最近成功运营抓取**无**，运营通告**0**，船舶/ETA/拥堵指标**未接入**。权限审计时间不当作运营数据刷新时间。

| 业务地点 | 国家 | 来源覆盖 | 实际限制 |
|---|---|---|---|
| ANTWERP | Belgium | unverified / 人工链接 | Phase2A条款未知，不自动抓取 |
| BREMERHAVEN | Germany | none | 无获准配置来源 |
| HAMBURG | Germany | restricted / HPA人工链接 | HPA Terms of Use须事先书面同意；HHM营销不当运营证据 |
| LE HAVRE | France | unverified，访问BLOCKED | robots200后列表两次读超时；未取得条款/逐篇日期 |
| ROTTERDAM | Netherlands | restricted | 新闻禁用，PIN未授权；本轮均未请求 |
| TANGIER | Morocco | none | 城市范围近似定位；Tanger Med映射待确认 |
| KOPER | Slovenia | none | 无获准配置来源 |
| PIRAEUS | Greece | none | 无获准配置来源 |
| TEESPORT | UK | unverified / PD Ports人工链接 | 自动采集/再利用无明确许可；未取PDF |
| MIDDLESBROUGH | UK | unverified / 同一PD候选 | 业务地点独立；River Tees通告可共享，只有一条事件级通知 |
| FELIXSTOWE | UK | none | 无获准配置来源 |
| DOVER | UK | unverified / 人工链接 | Community Portal不登录/不绕过；未宣称运营接入 |

坐标为城市/港区范围示意，不作导航；所有未经核实的UN/LOCODE保持null。详细机器状态与门槛运行见PORT_MONITOR_EVIDENCE.json。

## 实际测试

`timeout 120s /workspace/.venvs/supply-chain/bin/pytest -q --junitxml=runtime/port01/tests.xml`：**204 passed in12.96s**，无失败/跳过。新增26项相对178基线。`ruff check src tests scripts migrations/versions/003_port_monitor.py`通过，`git diff --check`通过。

覆盖：12地点/国家筛选、明确关闭/正常、已解决/取消、计划/过去/未知日期、过期抓取、不用fetch激活事件、地点误匹配、Tangier映射、共享范围/通知去重、升级/解除、改URL仍同编号、权限/时效门槛、故障隔离、重复RSS（仅Mock）、AI配置/调用/引文失败降级、Live/Demo、日报/已读隔离，以及002→003旧证据保留。

规则时效：24小时内核查且公布24小时内，或原文明示有效区间仍覆盖当前；还需明确active/normal原文、实际LIVE_HTTP与合格来源。未来计划、未知时间、解除、测试客户端、撤销权限或源失败均不能由抓取时间升级为当前确认。保守词法可能漏报，非预测模型或准确率。

## 真实浏览器证据

Chromium155.0.8059.79，新Streamlit进程/新会话、1440×1000及1000×900；仅localhost，拦截所有外部资源，底图无CDN/瓦片/API。最终QA库从空库创建，不复制公司/原业务数据；Live运营空，Demo显式虚构。

- [浏览器JSON](evidence/port01/browser.json)：10组PASS、page_errors=[]；实际地图12点逐一点击、右详情及未知状态、视图/缩放、搜索/空结果/清除、空Live日报、独立Tees地点/共享通知、已读、Demo日报、回Live无Demo、六页面和紧凑桌面。
- [地图Live](evidence/port01/01-live-map.png)、[Dover详情](evidence/port01/02-dover-panel.png)、[共享Tees Demo](evidence/port01/03-demo-shared-tee.png)、[紧凑桌面](evidence/port01/04-compact-live.png)、[Demo收件箱](evidence/port01/05-demo-inbox.png)、[最终收件箱](evidence/port01/06-final-inbox.png)。
- [日报最终局部复核](evidence/port01/report-followup.json)：随后对最终12地点状态表实际下载复核PASS；[Live HTML](evidence/port01/live-daily.html)0事件卡，[Demo HTML](evidence/port01/demo-daily.html)2张虚构事件卡，两者均含12地点表。
- 早期失败保留在runtime：先是脚本点隐藏radio，改为实际可见标签；随后发现SVG文字/热区拦截邻港，分离标记与文字、调整字号/位置；搜索需按Enter提交。修复后没有force点击或改风险规则来迎合测试。
- 国家筛选通过AppTest；手机原生/Windows/长期运行/真实LLM/真实非空运营日报仍NOT TESTED。不能以紧凑桌面截图冒称手机验收。

## 运行与复现

```bash
# README的Python3.12/依赖环境；不需要API Key
scm init                           # 003加表，不重建现有证据
scm collect-ports                  # 当前全部NEEDS_PERMISSION，0网络请求，不冒称采集成功
scm port-digest --mode live --output runtime/port01/daily.html
python -m streamlit run src/scm/ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

模块日报通过页面或CLI触发，保存为独立port_daily类型，可在Reports查看；旧通用调度未自动启用本模块未授权来源。选择Demo后“加载模块01虚构演示”才创建2条示例。所有真实来源权限不明时继续人工链接。仅有经过确认许可/保留条件的rss_text源才允许门槛后进入适配器；目前没有任何启用的真实源，PDF/法语/私有Portal适配器未做。

浏览器复现：创建新的独立QA数据库，调用`scm.ports.demo.seed(factory)`显式种Demo并启动本地独立进程，然后`timeout 240s python scripts/port_browser_uat.py --isolated-qa --url http://127.0.0.1:8512`。脚本有已读操作，要求干净Demo收件箱；不得指向原业务库。下载文件/截图默认runtime/port01/browser。Playwright/Chromium为验收工具，非生产必需依赖；Windows原生未实测。

## 代码审计与剩余限制

模块01不会调用旧通用未审来源采集；独立permission_gate强制自动访问+正文保留许可、审计证据、30日复核期限，任何不满足都在HTTP前阻断。旧通用采集/调度是独立既有能力，不宣称已完成其所有来源的权限认证；生产前仍应统一复核旧配置。模块只接运营Signal，不以既有HHM/EC新闻自动建立当前状态。

没有真实运营连接器获准，故业务PARTIAL；不申请付费API、不自行联系站方、不上传敏感数据或部署公网。当前AI中文为规则模板/原文证据，配置与调用失败降级已测试；真实LLM未调用，机器翻译/法律/业务人工签核未做。词法解析不保证复杂否定、跨段范围和解除公告完全正确；当前源覆盖不足时必须人工核实。SQLite单用户，无认证/RBAC、不可篡改审计或长期运行承诺；低流量世界地图使用近似坐标与标记偏移引线，不是实时地理定位。

下一步只等待Owner审核，决定是否申请明确书面许可或另行授权可合法用的运营RSS/API。Issue6保持OPEN、PR1 Draft；不自动进入Issue5 Phase2B。
