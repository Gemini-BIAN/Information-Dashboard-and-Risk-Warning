# Module02 真实法规验收 — 首份闭环 PASS / 扩展 PARTIAL

2026-11-11（Asia/Shanghai）；本报告替代 2026-11-10 的缺输入报告，旧结果保留在 Git 历史。

## 范围、输入和分支

执行环境与附件已恢复，未重新搭建基础设施。基于 `bf705f46903c9ada405cdbbd59552f816d7ce290`，继续 `feature/regulatory-rag-mvp` / Draft PR #7；依赖 Module01 `7d6fbc9`，PR base 保持 `feature/supply-chain-risk-mvp`，不合并 main。Module01 港口/UI/配置未改；仅共享 HTTP 工具增加可选、有上界的响应大小参数，旧默认 4MB 不变。

五份真实 Work 文件均可读取，原字节复制到 `data/regulatory/research/`，均忽略提交：主目录57条（P0 18/P1 31/P2 8），原研究核实级别9条标题/链接核实、48条候选，来源审计11条，manifest18条。原研究字段/核实状态不改写，不把候选自动升级为法律核实。精确列名、各文件 SHA256 与字段映射见 [WORK_FIELD_MAPPING.json](regulatory/WORK_FIELD_MAPPING.json)。支持 `EU_Regulation_Download_Manifest(1).csv`，两个不同副本冲突会拒绝。

18条 manifest 中16条 EU 原始文本目标和3条带日期整合文本目标共19个文档版本；ADR/IMDG两条无CELEX、非当前获准域，隔离而非伪造EU身份。完整原始行快照在本地 `runtime/regulatory/research-snapshot.json`。实际3个文档下载成功、1个候选整合版失败、15个未下载；未尝试其余13份EU正式文本。57条不是已下载量。

## 官方来源与实际文件

EUR-Lex robots 与法律声明实际 HTTP200。声明允许法律文件商业/非商业复用（特殊权利除外），编辑/整合内容 CC BY4.0，保留来源、修改说明；第三方/商标等不在授权内。Cellar公共接口说明读取成功，**未将其算作实际下载链路**。仅批准 EUR-Lex；审计 [OFFICIAL_SOURCE_AUDIT.json](regulatory/OFFICIAL_SOURCE_AUDIT.json)，许可30日复核。沿用代理、TLS、robots-first、同主机重定向和超时/有限重试，不绕过限制。

实际使用 `https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A<CELEX>`。以下均为英文原始 OJ 文本，不冒称最新整合版：

| CELEX | 文件字节 | PDF页 | SHA256 |
|---|---:|---:|---|
| 32023R1542 | 1,341,523 | 117 | `e9745513fabe68c8c15cc9f487c4d13da81d40394712f3e0b4c2588b3238d09a` |
| 32006R1907 | 1,864,477 | 849 | `005c7db3fc75ac2062264c0e3ae58715d6365d52dcbbeb60a81c10ab98e5e766` |
| 32008R1272 | 6,909,004 | 1355 | `64f4540f2b6ce34be837e2583ba540b125b5c4dfec3826739c3a148b5d9d872e` |

本地路径 `runtime/regulatory/files/objects/<SHA前2位>/<SHA>.pdf`；数据库 `runtime/regulatory/library.db`。成功要求HTTP状态、MIME、PDF头尾/可读性、实际字节与SHA一致；新增原文正式法律标题身份检查，避免把仅引用目标法规的其他PDF算作目标。已有下载也重新打开核对。PDF及Work附件未提交Git。

CLP首次超过4MB被正确拒绝；法规下载专用上限调整32MB后仅重试一次成功。共享采集默认4MB保持；解压后流式上限仍执行，未移除其他保护。CLP有xref索引修正读取警告，未重写文件或SHA，不保证全部复杂表格语义。

候选 `02023R1542-20260813` 的 Work ELI `/2026-08-13/eng/pdf` 返回HTTP200、`text/html`，在字节验证阶段拒绝，数据库failed/not_parsed，未保存法规文件/建索引。原始失败与有限重试证据见 [expansion.json](evidence/regulatory/live/expansion.json)、[clp-size-retry.json](evidence/regulatory/live/clp-size-retry.json)。不据此确认该整合日期有效或当前适用性。

## 真实解析、检索与引用

| 原始文本 | Article单元 | Annex单元 | Chunk | 解析状态 |
|---|---:|---:|---:|---|
| 电池法规 | 96 | 15 | 287 | needs_review |
| REACH | 141 | 17 | 564 | needs_review |
| CLP | 62 | 7 | 1315 | needs_review |

数量为识别的结构单元，不能当全文法律语义准确率。页码均物理PDF页，不混用OJ页号。修复真实PDF暴露的行内Article交叉引用误识别、附件对照表误作正文Article、前置空白页范围、跨页Chunk定位问题；附录/前言/布局/复杂表格保留待复核标志，不静默丢弃。重复解析相同文本保持Chunk ID，原研究重导入保留文件证据和实际出版日期，不提升legal_status。

首份正式文本出版日期核对为2023-07-28；**Article7位于物理31–33页，Annex I位于84页**。中文问题“Regulation (EU) 2023/1542 Article 7 对碳足迹有什么要求？”命中该版本Article7，返回5段有定位的英文摘录，例如：

> a carbon footprint declaration shall be drawn up for each battery model per manufacturing plant

官方引用：[Article7 PDF物理31页](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32023R1542#page=31)。引用对应库内真实Chunk及文件SHA；每段摘录重新打开对应PDF页、归一化空白后逐段比对通过。Annex I检索命中84页原文汞/镉/铅限制，并标记附件表格待复核；[PDF页图](evidence/regulatory/live/annex1-page84.png)。全文证据、下载时间、出版日期、文档/Chunk身份见 [LIVE_EVIDENCE.json](regulatory/LIVE_EVIDENCE.json)。

索引采用本地持久化词频+BM25和有限中英词表，**无LLM调用、无向量模型、无语义准确率承诺**。每次检索指定单一版本。REACH/CLP比较、ISO Tank运输、当前适用性在电池原文范围内返回证据不足，不凭常识补条款；跨法规综合未实现。法律效力/适用日期仍unknown/pending，原始OJ不能替代已核实的现行修订链。

## 验收与测试

| 检查 | 状态 | 实际证据 |
|---|---|---|
| 五附件及57/18真实字段映射 | PASS | 原字节SHA、完整本地快照、映射JSON |
| 首份法规下载→解析→索引→中文检索→引用 | PASS | 实际117页PDF，Article7/AnnexI定位，逐段原文比对 |
| REACH/CLP有限扩展 | PARTIAL | 原文下载/身份/SHA/结构解析通过，未全面审查条款或业务问答 |
| 版本隔离/失败/空结果降级 | PASS | 候选整合版无Chunk，不借用原版；未覆盖问题无结论 |
| 安全重跑/重导入/重复解析 | PASS | SHA缓存UNCHANGED，Chunk ID不变、研究状态/证据保留 |
| 浏览器实际闭环 | PASS | Chromium155，6组检查、0 page_errors；下载并重新打开实际PDF |
| 完整pytest（含Module01） | PASS | 229 passed，0失败/跳过，15.98s；JUnit本地保存 |
| Ruff | PASS | `ruff check src tests scripts` |
| 候选电池整合版 | BLOCKED | HTTP200 HTML非PDF，fail closed，不算下载成功 |
| 原生Windows/PyCharm、真实LLM | NOT TESTED | 未实际运行，不称PASS |
| 全部法规/复杂表格/现行修订链 | NOT TESTED | 未完成逐条法律复核 |

首份浏览器验收先通过，随后才扩展P0。[先行闭环JSON](evidence/regulatory/live/browser-first-pass.json)、[最终浏览器JSON](evidence/regulatory/live/browser.json)、[Article7页面](evidence/regulatory/live/article7-query.png)、[AnnexI页面](evidence/regulatory/live/annex1-query.png)、[原PDF31页图](evidence/regulatory/live/article7-page31.png)。浏览器从站内下载真实PDF并由PdfReader重新打开核对；物理页另外实际渲染检查。未宣称操作系统原生PDF查看器或远程PDF标签验收。

自动回归含合成/Mock边界测试，与上述真实文件/HTTP证据分别计数。CI回执见PR7和项目进度最新记录，不把本地测试等同远程CI。`scripts/validate_regulatory_live.py`仅核对本地真实已下载文件/索引，不填充Fixture；`scripts/regulatory_live_browser_uat.py`测试现有页面。

## Windows/PyCharm复现（命令提供，原生运行NOT TESTED）

在仓库根目录，放入原始五文件；不会从Git取得忽略的附件/PDF。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m scm.regulatory.cli inputs
.\.venv\Scripts\python.exe -m scm.regulatory.cli import-work
# 先复核permissions.json的有效证据/30日期限，不填虚构批准
.\.venv\Scripts\python.exe -m scm.regulatory.cli download --celex 32023R1542
.\.venv\Scripts\python.exe -m scm.regulatory.cli parse 30fcab0af43d1b9657136ec582ad7b71693c6248df52b02a1e3139b8e03a21bf
.\.venv\Scripts\python.exe -m scm.regulatory.cli search 30fcab0af43d1b9657136ec582ad7b71693c6248df52b02a1e3139b8e03a21bf "Article 7 对碳足迹有什么要求？"
.\.venv\Scripts\python.exe -m streamlit run src/scm/regulatory/app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
```

PyCharm选`.venv\Scripts\python.exe`，工作目录仓库根，模块streamlit；Module01原启动方式不变。权限/下载失败需按实际阶段报告，不自动循环试探路径。PDF断点策略为校验已完成文件后安全重跑，未实现HTTP Range续传。

## 归属与停止

© European Union，来源EUR-Lex；法律文件复用遵照[官方声明](https://eur-lex.europa.eu/content/legal-notice/legal-notice.html)，编辑/整合内容CC BY4.0。证据中的摘录、PDF页图、页面截图为原文提取/渲染和本系统检索展示，并非官方中文法律意见；未改写法规PDF。无付费API、无敏感数据、无公网部署。到此停止，不自动扩展新法规/新模块；现行版本、运输法源与法律业务审查交由后续审核决定。
