# Global Supply Chain Intelligence & Risk Monitor

面向新能源电解液企业海外供应链规划的本地运行 MVP，Python 3.12 + Streamlit + SQLite/SQLAlchemy。**默认不需要 API Key、不使用付费服务、不连接内部系统。**

已可运行：采集框架、原始证据及分析分离、解释型风险规则、航次 ETA 快照、人工审核、六个中文工作台、日报/周报 HTML 和独立调度。

**当前真实数据状态：已在新环境从欧委会运输、贸易、产业三个部门来源取得并保留15篇真实文章，完成Live页面/风险/日报验证；这三个来源属于同一机构。没有港口等待时间序列，其他候选来源尚未通过验收。** 演示空间有 5 条明确虚构的情报和 3 条脱敏虚构航次快照，绝不能作业务事实使用。详见 [SOURCE_AUDIT.md](SOURCE_AUDIT.md)。

## 快速启动（Linux / macOS，Python 3.12）

在本仓库根目录：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
scm init                           # 自动迁移并按新规则重算旧记录（保留证据/审计）
scm demo
python -m streamlit run src/scm/ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

浏览器本地访问端口 8501。工作台默认 Live 空间；在左侧切到 Demo 查看演示。**不会自动把演示记录填入 Live。** `scm demo` 可重复执行，不会重复写入。

此云环境已经安装在 `/workspace/.venvs/supply-chain`，可直接运行该目录 `bin/` 下的命令。每个任务已隔离，使用现有 checkout，无需另建 worktree。

## Windows（PowerShell）

```powershell
cd Information-Dashboard-and-Risk-Warning
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\scm.exe init
.\.venv\Scripts\scm.exe demo
.\.venv\Scripts\python.exe -m streamlit run src/scm/ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

不需要更改 PowerShell 脚本执行策略。Windows 命令已提供，**未在 Windows 主机实际验证**。运行测试：`.\.venv\Scripts\python.exe -m pytest -q`。若没有 Python 3.12，先从官方 Python 安装器安装该版本。

## 功能

| 工作台 | 能力 |
|---|---|
| Overview | 数据空间、数量、分级、待审核、最新事件与证据 |
| Intelligence | 日期/国家/类型/等级筛选、未知日期控制、确认/驳回/备注、CSV、安全原文下载 |
| Port Monitor | Rotterdam、Antwerp-Bruges、Hamburg 独立详情视图；查询参数 port；公告风险、人工调整及有效期、历史事件 |
| Shipment Monitor | CSV模板、分空间导入、逐次快照、相对上一快照和最初快照的ETA变化、候选港口关联 |
| Reports | 按日期生成日报/周报，浏览保存的HTML历史记录、下载 |
| Sources & System | 来源配置、真实采集、访问审计、采集失败日志、人工审核日志 |

港口等待时间无可靠真实数据时明确显示“数据暂不可用”，不绘制假趋势。风险是外部信号，不是延误概率；人工调整与自动规则分别保留。

## 数据采集及来源验证

`config/sources.json` 配置10个官方候选入口，覆盖港口、承运人、欧盟运输/产业/贸易、EUR-Lex、CATL。**候选 URL 不表示已验证稳定可用。** 每个来源记录方法、列表访问结果、正文和发布日期获取、限制及最后验证时间。

```bash
scm collect                         # 逐来源隔离失败，最长可能数分钟
scm collect --source rotterdam     # 也可重复指定 --source
scm audit --output SOURCE_AUDIT.md
```

支持 HTML 列表 + 同站文章抓取及 RSS/Atom（将 method 配为 rss；不会把摘要假装为全文）。先检查 robots，1秒请求间隔，遵守更长 Crawl-delay/Request-rate；20秒请求超时，最多重试2次，限制重定向和4MB响应。不跟随跨域跳转、不绕过 robots、验证码、登录或代理限制。robots 404/410按 RFC 9309 允许公开抓取；其他无法判断情况停止。

泛用 HTML 解析支持 `<article>`/`<main>`、h1、meta、JSON-LD和time日期；缺少正文或JS壳不计为采集成功。未能识别日期保持未知；无时区的网页日期按UTC记录（日期精度可能仅到天），报告业务周期使用 Asia/Shanghai。

来源内容和 robots 可能变化；生产化前需人工核对使用条款、采集许可与文章解析准确性。当前并未确认全部站点条款。不要未经验证把候选列表描述成稳定生产数据源。

## 航次与ETA

```bash
scm import-shipments fixtures/demo_shipments.csv --mode demo
# 经授权的、非敏感或脱敏本地CSV才可用 --mode live；无需内部系统连接
```

模板：`fixtures/shipment_template.csv`。标题及顺序必须完全一致；时间用带时区的 ISO 8601，例如 `2026-11-06T08:00:00+08:00` 或 `2026-11-06T00:00:00Z`。ETA、Updated At及身份字段必填；ETD/ATD/ATA可空。整批先校验，导入在事务中执行；冲突回滚、重复跳过。

快照键：柜号 + 船舶 + 航次 + POL + POD + Updated At + 数据空间。风险比较同一柜号、同船同航次同起讫港；更新时间排序，支持乱序导入。ETA相对上一快照延后24h为中、72h为高；一条快照为未知；已填ATA标记当前到港、保留历史变化。超过48h更新会标记陈旧。

港口事件只按POD和公告时间窗口（ETD/ATD至ETA/ATA前后7天）给出**待核实**候选关联。未提供承运人确认，不能据此断定跳港、甩柜或某事件导致延误。Demo 导入要求 DEMO- 柜号；Live 拒绝示例标识。系统仍依赖操作者诚实标记数据来源。

## 分析与可选LLM

复制 `.env.example` 到 `.env` 可改变数据库路径、时区和Provider；文件已忽略。默认 `SCM_LLM_PROVIDER=none`：中文分类/标题模板、原文证据摘录、条件性业务影响及行动建议；**不是完整中文语义翻译或同等AI能力。**

可选 OpenAI-compatible provider 通过环境变量 `SCM_LLM_PROVIDER=openai-compatible`、`SCM_LLM_BASE_URL`、`SCM_LLM_MODEL`、`SCM_LLM_API_KEY` 配置。API Key不进数据库/仓库；仅用于公开情报，航次数据不会送入Provider。默认不调用任何付费API。启用任何收费服务前须获得用户批准。

Provider返回严格 Pydantic JSON，facts 必须带原文连续逐字引文；不在原文的引文会触发回退。网络、配置或校验失败也回退规则分析并记录安全错误。**引文校验无法保证翻译或推断完全忠实，人工审核仍必要。** LLM不决定最终风险，规则从原文独立分级。

政策状态与日期分离：提案、通过、实施、废止或未知均需文内状态依据。**过去的生效日期不会自动升级为“实施”，明确废止优先于历史生效证据**；生效/到期/废止日期独立存储，多条款日期冲突保留未知并给出依据。它们是文内状态，不是法律当前适用性的保证。

运营生命周期独立为 announced / active / resolved / cancelled / unknown。原文严重度不等于当前港口风险；取消、解除、矛盾、假设、历史上下文和未知状态不自动抬高当前预警。已宣布事件最多中级提示，进行中信号才按严重度计入；30天只是候选检索窗口，不证明仍在中断。多港口内容按明确港口所在语句拆分，不把一个港口的中断复制给另一个港口。来源可信度独立标记为未经审核，不因LLM或关键词分数自动变高。

规则版本为 `2026-11-06.4`（补充真实反倾销公告的贸易分类/中级信号）。`scm init` 或网页首次加载会幂等重算旧版本；也可显式运行 `scm reassess`。旧原文/分析保留，规则或证据变化的前后状态写入ReviewLog，重置人审。旧规则未重算的记录不用于当前港口预警。规则的否定、条件、跨文档事件关联和时间理解仍有限，见已知限制。

## 报告与自动调度

```bash
scm report --kind daily --mode demo --day 2026-11-06 --output runtime/reports/daily-demo.html
scm report --kind weekly --mode demo --day 2026-11-06 --output runtime/reports/weekly-demo.html
scm report --kind daily --mode live --output runtime/reports/daily-live.html
scm schedule
```

HTML可在Reports页查看/下载；原始文本进行HTML转义。日报包括重点、行业政策、物流港口、潜在业务影响、关注事项、来源质量。周报按专题归并、最多5项重点、条件性1–3个月规划建议、追踪与人工核实问题。专题相同不等于确认是同一事件。无重要新增明确说明，不补新闻凑数。

Live报告先核对每个启用来源在周期内逐日的最新采集日志。只有真实HTTP、成功入库、全文及发布日期齐备的PASS才能计入该日覆盖；Mock/Fixture、失败、未知日期或缺日不能计入。**覆盖不足时写“采集覆盖不足”，不得将失败日描述为没有重要新闻**。即使样本采集成功，也不代表全站或全球完整覆盖。来源审计增加实际请求URL/阶段、请求次数、耗时、文章样例、发布日期年龄及最后真实成功时间。

周期依据**原文发布日期**；未知日期不混入今日新闻，计入质量说明。已驳回事件不计入报告。当前周期的报告注明可能未结束。相同空间/周期/种类再次生成会刷新该报告；不同周期保留历史，不保留同一周期每次生成的多版本。

调度独立于网页，需要单独保持运行：每6小时采集一次；每天08:00生成昨日Live日报；周一08:10生成上周Live周报，时区默认Asia/Shanghai。单进程限制同一任务并发，SQLite持久化报告；重启后重新注册任务，不回补停机期间全部任务。无需等待任何LLM才能生成报告。

## 测试与结构

```bash
python -m pytest -q --junitxml=runtime/test-results.xml
ruff check src tests
```

```
src/scm/collectors/    robots、HTTP、HTML/RSS、来源隔离与审计
src/scm/database/      SQLAlchemy表、SQLite连接
src/scm/intelligence/  幂等写入、原始版本、Provider、人工审核
src/scm/risk/          风险规则、港口风险聚合
src/scm/shipments/     CSV、快照、ETA变化与待核实关联
src/scm/reports/       日报/周报HTML
src/scm/ui/            Streamlit六个工作台
migrations/           Alembic版本化迁移（scm init执行）
config/ fixtures/ tests/ docs/
runtime/              本地SQLite/HTML/测试结果；忽略提交
```

数据库以Alembic为版本依据，不以 `create_all` 替代迁移。原文版本和分析分别保存，内容/发布日期更新生成新版本并重置审核。URL规范化和来源内内容哈希去重；不同媒体相同报道不强行丢弃证据，周报再按专题组织。

详见 [TEST_REPORT.md](TEST_REPORT.md)、[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)、[DECISIONS.md](DECISIONS.md)、[PROJECT_STATUS.md](PROJECT_STATUS.md)、[NEXT_TASKS.md](NEXT_TASKS.md)、[NEXT_STEPS.md](NEXT_STEPS.md)。

## 安全与协作

默认仅监听127.0.0.1；没有身份认证或企业权限隔离，不能直接公网部署。不上传内部敏感资料、不提交真实柜号/客户/报价/API密钥。CSV导出防公式注入；原文按不可信数据处理。人工审核人是自报标签，审计不是不可篡改合规日志。

唯一协作仓库为 Gemini-BIAN/Information-Dashboard-and-Risk-Warning。首次初始化 main，仅作为空基线；代码在 `feature/supply-chain-risk-mvp`。后续 feature 分支、测试、清晰提交、推送、PR，不自行合并 main。开发前读取Issues、未解决PR Review和项目状态文档；无法访问时记录限制，继续独立可验证工作。当前网络策略已发布生效，GitHub API读取与Git HTTPS可用。现有Draft PR #1继续使用此feature分支，不合并main。最新真实采集与写入验证见项目进度和docs/LIVE_ACCEPTANCE.md。


## 本轮真实数据验收（2026-11-06）

```bash
scm collect --source ec --source ec-trade --source ec-industry
python scripts/validate_live.py
```

三来源各5篇，原始发布日期齐全；重复真实采集15篇均unchanged。验证脚本检查24小时内真实HTTP采集日志、原文/引文、幂等入库、规则、实际Live页面与日报；不新发网络请求、不加载模拟数据，不能用过期快照当新采集。证据输出runtime/live_acceptance.json；本轮可复核摘要在docs/LIVE_EVIDENCE_2026-11-06.json。

欧委会使用CC BY 4.0，页面、报告及官方摘录Fixture保留署名、许可链接、提取与中文模板修改说明。Rotterdam明确限制下载/复制，已停用，初次许可审查前临时取得的5篇正文及分析副本已清理，不计入15篇。其他候选未验证即不算PASS。没有复用受限图片/Logo或上传内部数据。

文章日期没有改成采集当天；样例日报分别按2026-10-20、10-29、10-30原始发布日期生成。今日采集覆盖仍不足，不能声称今日全球无重要新闻。剩余站点/主题和用户业务法律签核待完成，参见SOURCE_AUDIT和docs/LIVE_ACCEPTANCE。

## Issue #5 Phase 2A：独立内容链路（不改变 UI）

```bash
# 已安装依赖的 Python3.12；默认独立SQLite，不读取/修改原业务库
python scripts/run_phase2a.py
python scripts/validate_phase2a.py
```

该路径仅允许经过审查的Hamburg/EC Batteries文字来源，无需LLM Key，输出`runtime/phase2a/daily.html`。Linux验证使用外层`timeout 160s`。Windows可用`.\.venv\Scripts\python.exe scripts\run_phase2a.py`，尚未在Windows实跑。

本轮4篇新增入库，重复采集4 unchanged；其中3条排除、1条历史背景、0条当日合格情报。真实验证的日报为空并说明覆盖不足；不宣称已获得实时业务预警。许可复核超过30日需重新确认，不绕过限制。详见[Phase2A验收](docs/PHASE2_ACCEPTANCE.md)。

## 模块01：12业务港口运营监控

Port Monitor新增离线世界地图/12标记、右侧详情、搜索/国家筛选、默认30日历史、运营严重度/业务相关性、站内收件箱与独立日报。Dover替换London；Teesport和Middlesbrough分开；Tangier/Tanger Med映射待确认。AIS/ETA/拥堵只保留未接入区，无虚构数值。

```bash
scm init
scm collect-ports
scm port-digest --mode live --output runtime/port01/daily.html
```

**当前获准自动运营源0、真实运营事件0，12地点均未知，业务验收PARTIAL。** Le Havre访问超时、PD Ports权限未知、HPA要求书面同意；不启用采集、不取PDF、不请求Rotterdam/PIN。模块Demo需显式点击“加载模块01虚构演示”，与Live隔离。不需LLM Key；可选LLM只做分析，失败规则降级。配置：`config/ports.json`、`config/port_sources.json`。完整结果与实际截图见[PORT_MONITOR_ACCEPTANCE](docs/PORT_MONITOR_ACCEPTANCE.md)。

Windows PowerShell可用`.\.venv\Scripts\scm.exe init`、`.\.venv\Scripts\scm.exe collect-ports`、`.\.venv\Scripts\scm.exe port-digest --mode live`；Windows主机尚未实际测试。


## 统一供应链情报平台（2026-11-11）

新增独立入口，复用原12港口地图/服务；提供海外产能与竞争、物流市场与成本、统一情报、日报周报、预警和Sources。原Module01入口保持。这里的Module02指产能情报；法规RAG暂停在独立分支/PR7，没有并入本分支。

```bash
python -m scm.platform.cli init
python -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
# 显式DEMO，不填充Live
python -m scm.platform.cli demo
python -m scm.platform.cli collect --source hamburg
python -m scm.platform.cli report --mode live --kind daily --output runtime/platform/live-daily.html
```

独立库runtime/platform/platform.db；Live/DEMO/Manual严格分开，CSV/XLSX只进入Manual。企业及来源配置分别为config/platform_companies.json和config/platform_sources.json，未知/过期许可拒绝自动请求。当前真实采集4篇背景信息，不是当前运营/企业投产/实时价格；12港当前状态未知。无LLM、无付费API、无公网部署。**FRAMEWORK PASS / MOCK PASS / LIVE PARTIAL / WINDOWS NOT TESTED**。251pytest、16组桌面/390px浏览器检查通过；[验收报告](docs/PLATFORM_ACCEPTANCE.md)、[Windows/PyCharm命令](docs/PLATFORM_WINDOWS.md)、[来源审计/待接入](docs/platform/SOURCE_AUDIT.md)。


## 港口二级详情页

统一平台的01港口页支持地图摘要→查看详情→概览/公告时间线/来源证据/业务影响，返回保留港口，支持深链接。沿用原风险服务，历史/背景资料不证明当前运营。脱敏配置按Live/DEMO/Manual隔离，缺配置业务影响未知。操作与截图见[PORT_DETAIL_ACCEPTANCE](docs/PORT_DETAIL_ACCEPTANCE.md)。旧六工作台入口和Windows UTF-8修复保留。


## 当前港口首页：纯交互式世界地图

统一平台01入口默认只有Leaflet世界图与12标点，无默认选择/侧卡/标题/下拉。点标点才弹锚定卡，查看详情进入原四标签；返回恢复视角并关闭卡片。在线OSM保留署名，失败明确降级为离线可交互矢量。运行命令不变，详见[WORLD_MAP_ACCEPTANCE](docs/WORLD_MAP_ACCEPTANCE.md)及默认/弹窗/缩放三类真实截图。旧PORT_DETAIL_ACCEPTANCE的一级侧卡截图只作历史，二级详情仍保留。
