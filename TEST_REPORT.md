# ESCIM 测试报告：Issue #2 / #3

2026-11-06（Asia/Shanghai），Linux，Python3.12.14。结果来自实际执行；Mock/合成回归不算Live验收。

## PASS：本地自动验证

完整命令：`/workspace/.venvs/supply-chain/bin/pytest -q --junitxml=runtime/test-results.xml`

结果：**93 passed in 9.84s；0 failed、0 skipped**。JUnit位于本地忽略路径runtime/test-results.xml。

`ruff check src tests`：**All checks passed**。`git diff --check`通过。

保留原有47项测试路径，新增46项。两处旧断言随Review修正：历史生效日期不再自动实施；原文更新增加系统前后状态审计，预期日志多一条。没有删除失败场景、禁用断言或用Mock冒充真实采集。

| 本轮验证 | 状态 | 证据 |
|---|---|---|
| 明确废止+过去生效日期 | PASS | 英文与中文回归，废止不会被日期覆盖 |
| 提案含历史日期/旧法规引用 | PASS | 提案保留；明确矛盾进入未知，不以日期升级 |
| 独立生效/到期/废止日期 | PASS | 多日期分字段；日期歧义保留未知与证据 |
| 未来日期/已到期/否定法规状态 | PASS | 矛盾需核实、到期不保证继续适用 |
| 撤回、取消罢工、恢复作业/港口重开 | PASS | 生命周期解除/取消，不能抬高当前港口预警 |
| 多句矛盾、旧标题/解除正文、解除标题/进行中正文 | PASS | 矛盾为unknown；不自动抬高预警 |
| 假设/条件示例、历史日期/旧事件 | PASS | 与当前事件分开，不产生当前高风险 |
| 多港口范围 | PASS | Rotterdam无罢工不掩盖Hamburg关闭；未归属文字不复制到各港 |
| 严重度/生命周期/来源可信度独立 | PASS | announced最多中；active按原文；unknown/legacy不进入当前分级 |
| 001→002真实SQLite升级 | PASS | 临时001库保留原文，升级后重算并记录审计 |
| 原文/规则版本变化前后审计与幂等重算 | PASS | 原文/旧分析保留，ReviewLog前后JSON，再次reassess=0 |
| 每来源/每日覆盖 | PASS | 缺日志、过期、Mock、无发布日期、最新失败不能证明当日Live覆盖 |
| 失败日/缺测日报与周报 | PASS | 明示“采集覆盖不足”，不宣称无重要新闻 |
| 采集遥测 | PASS | Mock测试耗时、文章样例、发布日期年龄及注入客户端标签；不更新真实成功时间 |
| robots同域重定向与403处理 | PASS | 跳转到禁止路径在请求前停止；确定性代理403只尝试1次 |
| 原有无API核心、去重、来源失败隔离、ETA、HTML、六页面 | PASS | 原测试路径完整执行，未引入付费依赖 |
| 页面不确定性与覆盖警示 | PASS | Streamlit AppTest校验生命周期、日期/证据、来源可信度和Live覆盖不足 |

## 本实例实际运行

- PASS：迁移/重算、重复init/reassess、真实空间日报/周报HTML生成；报告明确采集覆盖不足。
- PASS：10个来源分别完成**访问尝试和失败审计**；这不是采集成功。
- BLOCKED：真实正文0、真实Live事件0，10/10来源在robots.txt的CONNECT阶段403。正文/原始发布日期解析、真实事件到UI/报告和人工事实核对NOT TESTED。
- BLOCKED：Issue #2至少2个官方来源成功的Live验收。详见SOURCE_AUDIT与docs/LIVE_ACCEPTANCE。
- PASS：正常GitHub公开网页读取PR #1 Review、Issue #2/#3及基线Actions成功状态；写入API仍Forbidden。
- PASS：本轮修复提交64e1016的push与PR synchronize两次Actions，公开网页显示completed successfully；PR Checks显示test succeeded（44s）。不是旧CI或本地pytest替代。
- NOT TESTED：真实LLM、Windows原生、持续跨日调度、人工浏览器视觉验收。没有付费API、内部数据或公网部署。

## GitHub Actions观察

旧基线9160f0d：公开Actions列表及PR Checks显示成功。PR运行：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42149871304 ；push运行：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42149599779 。本轮新提交的最终观察附后。


## 本轮修复提交CI与协作写入

- Commit：64e1016（风险规则、覆盖、迁移及全部93项测试）。
- Push Actions PASS：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42155814204
- PR synchronize Actions PASS：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42155815831
- 观察方式：正常GitHub公开Actions列表及PR #1 Checks；分别显示46s、48s完成成功，PR test显示44s成功。完整签入日志需要登录，未宣称下载远程JUnit或核对远程测试数量。
- API实际写入：PATCH PR #1、POST Issue #2 comments、POST Issue #3 comments均Forbidden。PR代码随Git推送更新；描述/评论未发布，Issue状态未改变。准备文本在docs/PR_DESCRIPTION、docs/ISSUE_RESULTS。
- 最终依赖一致性：`python -m pip check` → No broken requirements found。
