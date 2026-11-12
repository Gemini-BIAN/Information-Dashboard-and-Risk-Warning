## 2026-11-12 纯交互世界地图（最新）

纯交互地图最终回归：258 passed in17.79s；ruff src/tests/scripts、node --check、diff check通过。Chromium155桌面1440×1000/移动390×844共14组，实际OSM瓦片200、真实鼠标缩放拖动与12点点击、两种关闭、详情返回center/zoom相同、CDP双指缩放、阻断瓦片后矢量降级均通过。截图与机器证据docs/evidence/world-map/；旧常驻摘要截图是历史，不是当前UI。Windows/实体触屏NOT TESTED。

## 2026-11-12 港口详情页（最新）

完整258pytest通过20.47s，ruff/diff检查通过。新增4项详情回归：12入口、返回状态、历史/URL更改版本追溯、SHA与配置空间隔离。Chromium155桌面/390px共14检查、0页面错误/无页面横溢。真实保存证据platform-6 SHA/URL实际比对；Windows原生仍NOT TESTED。详见docs/PORT_DETAIL_ACCEPTANCE.md。

## 2026-11-11 PR8 Windows编码修复（最新）

PR8编码回归：254 passed in16.56s，0失败/跳过；ruff和diff check通过。GBK负对照复现真实ports.json错误，修复后港口/配置、DEMO、中文HTML/JSON/CSV/MD往返通过；新增AST防遗漏。Linux模拟不是原生Windows PASS。详见docs/WINDOWS_ENCODING_ACCEPTANCE.md。

## 2026-11-11 统一平台本轮结果（最新）

完整pytest251 passed in17.63s（含原204），无失败/跳过；ruff src/tests/scripts/新迁移、pip check、diff check通过。真实HTTP4篇，重复4 unchanged，实际保存HTML逐篇SHA/重解析通过；当前空日报与原日期历史日报通过。Chromium155桌面1440和移动390两视口16组检查PASS/0pageerrors/无横向溢出。开发失败迭代及最终证据均保留，Windows原生NOT TESTED。详见docs/PLATFORM_ACCEPTANCE.md和docs/evidence/platform/。

---

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

## 2026-11-09 Issue #5 Phase 2A

PASS：`pytest -q --junitxml=runtime/phase2a/test-results.xml` → **178 passed in 11.71s**；`ruff check src tests scripts` → All checks passed。新增21项覆盖正/负业务相关性、旧/已解决事件、日期未知/未来、Hamburg正文与日期、未知/非正文许可零请求、故障隔离、canonical/修订引用、重复与Live/Demo日报隔离。合成HTTP用例不计为真实采集或分类准确率。

真实HTTP技术链路PASS：Hamburg3+EC Batteries1，共4篇新增入库；多次读取相同4篇均unchanged，原文/日期和4/4/4计数不变。2门户机构，相对历史EC只新增1个；7日内1篇。相关性：relevant0、possibly_relevant1、excluded3。当日空日报HTML实际生成并检查无旧闻条目。PARTIAL：可行动内容覆盖不足；NOT TESTED：含合格真实当日事件的非空日报、Windows、页面/浏览器、人工法律/业务签核。详见docs/PHASE2_ACCEPTANCE.md与逐请求证据。CI以本轮SHA实际结果另在PR/Issue回执，不沿用旧SHA成功。

## 2026-11-09 Issue6模块01

PASS：完整pytest **204 passed in12.96s**（相对178新增26）；ruff src/tests/scripts及迁移003通过。覆盖生命周期/双维度风险、未知/过期/未来时效、明确正常、否定/解除/取消、地点误配/Tangier待核实、Tees共享去重、编号身份、升级/解除通知、读标记/空间隔离、AI配置/调用/引文失败降级、权限门槛/故障隔离/MockRSS幂等、002→003旧证据保留和12 UI切换/国家筛选。

浏览器PASS（有限范围）：新进程/新Chromium155、1440及1000px，离线底图与12标记实际点击，搜索/空结果/回清，收件箱、双空间日报下载、六页面；10组检查无pageerror，最终12地点日报表局部复核另PASS。早期热区/定位器失败修复后通过，不使用force。证据见docs/evidence/port01及PORT_MONITOR_EVIDENCE.json。

BLOCKED/NEEDS_PERMISSION：3真实运营来源均未通过；实际运营源0/真实事件0。Live空日报实际通过；Demo2条仅虚构功能验收，不算Live或模型准确率。NOT TESTED：真实非空运营链路、真实LLM/人工业务法律签核、手机、Windows、长期调度。业务PARTIAL，不把UI技术通过等同12港口实况覆盖；CI结论按最终SHA在PR/Issue补充。
