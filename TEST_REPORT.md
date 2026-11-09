# ESCIM 测试报告：Issue #2 真实采集验收

验证：2026-11-06（Asia/Shanghai），新发布环境，Linux/Python3.12.14。Mock/离线Fixture测试与真实HTTP分开计数。

## 自动测试：PASS

实际命令：`/workspace/.venvs/supply-chain/bin/pytest -q --junitxml=runtime/test-results.xml`

**99 passed in 8.82s；0 failed、0 skipped**。原93项路径继续通过；新增gzip解码/解码后4MB上限、受限复用前置阻断、两份真实欧委会摘录解析与专用解析器拒绝列表壳等6项测试。

`ruff check src tests scripts`：All checks passed。`git diff --check`通过。JUnit在忽略的runtime/test-results.xml。

官方摘录Fixture来自实际取得的CC BY 4.0欧委会页面，保留原URL、捕获时间、原HTML及摘录SHA256、原始日期、署名与修改说明。它们是**离线回归，不算Live请求或当前新闻覆盖**。没有提交受限Rotterdam正文。

## 真实运行验收

| 检查 | 状态 | 实际结果 |
|---|---|---|
| 当前网络策略 | PASS | 新实例unrestricted/enforced，observations_current=true，继承代理与TLS校验 |
| GitHub API读取 | PASS | 实际GET Issue #2、PR #1 reviews/comments成功；已读第二轮Owner Review |
| 三官方部门来源真实采集 | PASS | DG MOVE、DG TRADE、DG GROW各5篇，共15篇保留正文及发布日期 |
| 重复真实采集 | PASS | 再次真实获取同15篇，三源各5 unchanged，未新增重复事件 |
| 原始正文→解析→数据库→规则 | PASS | 原文/分析分离，原始日期保留，反倾销样例中风险且可解释，其他状态未知不伪造 |
| 源HTML独立对照 | PASS | 三样例标题、datePublished及完整抽取正文与数据库当前RawRevision一致；详见证据JSON |
| 实际Live页面 | PASS | 对实际15篇Live数据库执行Streamlit AppTest，Overview=15，Intelligence展示三样例和许可，无Demo混入 |
| 日报生成及Reports页面 | PASS | 三样例按原发布日期生成HTML并在实际Reports页面选择，无异常；源链接、原文、风险及CC许可齐全 |
| Demo隔离 | PASS | 原有5条虚构Demo事件不进入Live，Live验收不加载seed；重复入库前后两空间数量不变 |
| 当日覆盖不足说明 | PASS | 今日配置候选仍非全覆盖，Live日报明确覆盖不足；不把旧文章重定为今日新闻 |
| Rotterdam复用限制 | BLOCKED | 官方条款禁止下载/复制；停用来源并清理本轮5份正文/分析副本，排除验收计数 |
| EUR-Lex | BLOCKED | robots.txt HTTP202，fail closed；未绕过挑战或继续请求正文 |
| CATL | BLOCKED | robots跨主机301触发保护，未自动跟随 |
| Antwerp/Hamburg正文 | BLOCKED | 列表可访问但未发现/解析合格文章；不算源适配成功 |
| Maersk/Hapag正文 | NOT TESTED | 修复后robots200且允许列表；仅做robots探测，复用政策待核实，未请求正文 |
| 人工业务/法律签核 | NOT TESTED | Codex做源HTML逐项工程核对，不冒称用户人工审核通过 |
| 真实LLM/港口等待时间/真实航次/Windows/跨日调度 | NOT TESTED | 无新增付费调用、内部数据或公网部署 |

## 实际端到端工具

`python scripts/validate_live.py`在当前真实数据库执行，返回PASS、live_events=15、sources=3。过程要求近24小时LIVE_HTTP日志及许可，校验逐字引文、本地重入幂等、原发布日期日报和真实页面；不会通过模拟新闻填充。

时间和逐源证据：docs/LIVE_EVIDENCE_2026-11-06.json。完整SOURCE_AUDIT保留其他来源失败阶段和未测边界。三来源都是欧委会不同部门，不表示三个独立机构或电池/港口完整覆盖；也不是预测准确率验证。

## GitHub Actions

代码修复提交85e261d已推送现有feature分支，触发push/PR检查。当前轮CI与PR更新结果在本节后续记录；此前基线成功不作为本轮成功证明。99是本地实际测试数量，不冒称已读取远程JUnit。


## 本轮代码CI

代码SHA：85e261dd436048b2d5ea2b4310bb4ca96431cc55。已通过恢复的GitHub API实际读取status=completed、conclusion=success：

- https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42169750468
- https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42169754791

这是本轮SHA的实际检查，不是沿用基线。远程CI执行离线回归，不把它当真实HTTP验收；真实15篇与页面证据由本实例另行执行。未下载远程JUnit，不冒称核对了远程测试计数。依赖一致性pip check：No broken requirements found。


## 最终回执（仅文档收尾）

- 证据提交8a3f2fc的两次CI经API确认success：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42170291262 与 https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42170295767 。
- GitHub API写入PASS：PR #1描述PATCH成功且Draft保留；Issue #2评论POST成功：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/issues/2#issuecomment-6677957601 。Issue未关闭，main未合并。
- 新实例本地服务PASS：Streamlit绑定127.0.0.1:8501，GET /_stcore/health→200/ok，GET /→200。页面数据渲染另由实际Live AppTest验证，未冒称人工浏览器视觉验收。

## 2026-11-09 Issue #5 第一阶段

PASS：完整 pytest **157 passed in 12.08s**；新增20个契约/合成边界测试，不宣称自动分类准确率。`ruff check src tests scripts/audit_content_sources.py` 全部通过。版本化 JSON Schema 与 Pydantic 一致性验证通过。

PARTIAL：23 候选来源真实网络审计 16 PARTIAL、7 BLOCKED（Rotterdam未请求、沿用禁止规则）。NOT TESTED：新增正文许可/逐篇日期/鲜度/连接器/业务流/日报端到端；新增真实入库0，旧15篇不计新增。UI保持冻结，本阶段未运行浏览器测试。详见 docs/CONTENT_ACCEPTANCE.md 与 docs/content_source_audit.v1.json。
