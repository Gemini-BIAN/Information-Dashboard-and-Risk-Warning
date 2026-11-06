# Global Supply Chain Intelligence & Risk Monitor

面向新能源电解液企业海外供应链规划的本地运行 MVP，Python 3.12 + Streamlit + SQLite/SQLAlchemy。**默认不需要 API Key、不使用付费服务、不连接内部系统。**

已可运行：采集框架、原始证据及分析分离、解释型风险规则、航次 ETA 快照、人工审核、六个中文工作台、日报/周报 HTML 和独立调度。

**当前真实数据状态：官方来源在此云环境被代理拒绝；没有采集成功的真实新闻，也没有港口等待时间序列。** 演示空间有 5 条明确虚构的情报和 3 条脱敏虚构航次快照，绝不能作业务事实使用。详见 [SOURCE_AUDIT.md](SOURCE_AUDIT.md)。

## 快速启动（Linux / macOS，Python 3.12）

在本仓库根目录：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
scm init
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

政策状态来自明确短语；不能推断的为未知。明确标注的有限中英文生效日期格式可解析，否则待核实；未来适用日期不自动等同已经实施。风险规则的否定、条件和时间理解仍有限，见已知限制。

## 报告与自动调度

```bash
scm report --kind daily --mode demo --day 2026-11-06 --output runtime/reports/daily-demo.html
scm report --kind weekly --mode demo --day 2026-11-06 --output runtime/reports/weekly-demo.html
scm report --kind daily --mode live --output runtime/reports/daily-live.html
scm schedule
```

HTML可在Reports页查看/下载；原始文本进行HTML转义。日报包括重点、行业政策、物流港口、潜在业务影响、关注事项、来源质量。周报按专题归并、最多5项重点、条件性1–3个月规划建议、追踪与人工核实问题。专题相同不等于确认是同一事件。无重要新增明确说明，不补新闻凑数。

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

唯一协作仓库为 Gemini-BIAN/Information-Dashboard-and-Risk-Warning。首次初始化 main，仅作为空基线；代码在 `feature/supply-chain-risk-mvp`。后续 feature 分支、测试、清晰提交、推送、PR，不自行合并 main。开发前读取Issues、未解决PR Review和项目状态文档；无法访问时记录限制，继续独立可验证工作。当前 Git HTTPS 可推送，GitHub API 访问被代理拒绝，PR状态见项目进度。
