# ESCIM Module02 验收 — 基础设施PARTIAL / 真实闭环BLOCKED

2026-11-10（Asia/Shanghai）。本轮没有完成“至少一份真实法规下载→解析→检索→引用”验收，不能宣称RAG完成。

## 输入阻塞与范围依据

用户明确要求：若五份Work文件全部不可用，“只完成不依赖文件的基础设施并报告阻塞，不要自行虚构57条目录”。本轮检查工作区、data/regulatory/research、library-files/shared/scratch、任务可用附件能力与仓库；五个文件皆未找到。已测试manifest的Library链接，仅返回HTTP200、text/html、标题ChatGPT，无文件名或下载链接，不是CSV。没有测试其余四个Library URL的登录流程，不声称它们逐一403/失败；没有试探私有下载端点或绕过登录。

缺失：EU_Regulation_Master_Catalog.xlsx、EU_Regulation_Source_Audit.xlsx、EU_Regulation_RAG_Schema.md、EU_Regulation_Research_Report.md、EU_Regulation_Download_Manifest.csv。57/P0/P1/P2数量只来自用户描述，未核实/导入；未自行补法规目录。

恢复后需要实际附件或本地五文件，先读取真实列名、Schema和源审计，再映射标准化manifest及审查下载权限。目前permissions.json未批准任何源，未尝试实际EUR-Lex/Cellar法规下载；不能把输入缺失称作EUR-Lex网络阻断。

## 分支与Module01保护

- 远程main：3a399d5c82aa36434806ece47ab47330c7d38f38，仍初始化空提交。
- Module01功能分支：7d6fbc99181644ce4a4c55a3d6283e036ecdf148。
- 新feature/regulatory-rag-mvp从后者派生；Module01代码/UI/港口配置/003迁移未改变。新增004隔离法规表，复用SQLAlchemy/Alembic基础设施，默认另建runtime/regulatory/library.db。
- 新Draft PR以feature/supply-chain-risk-mvp为base，仅看Module02增量，显式依赖PR1；不更改PR1、合并main或自动变基。PR/最终SHA/CI结果在GitHub实际回执补充。

## 已实现基础设施

| 范围 | 结果 | 实际验证 |
|---|---|---|
| 标准化CSV/XLSX contract | PASS（内部契约） | CELEX/ELI官方域、语言、正式/整合版本日期/格式身份；校验冲突与重复；只有空模板，无目录数据。未映射未读Work列名 |
| 许可与下载门槛 | PASS（合成） | 自动访问+保留许可、证据、30日复核期限；默认源列表为空，许可未知在HTTP前阻断 |
| 字节存储 | PASS（合成） | HTTP200、MIME、PDF头/尾/可读页、HTML容器/XML实体限制；SHA256/大小/下载时间；CAS原子写/重复去重/损坏隔离与安全重跑，失败不记成功 |
| 文本/结构基础解析 | PASS（合成） | 生成的测试PDF、HTML识别Article7/AnnexI；页范围仅PDF可靠时保留；表格/附件/PDF布局/XML结构标记人工复核，空文本不产生成功引用 |
| 本地检索/引用契约 | PASS（合成） | 持久化Chunk词频JSON、本地BM25、中英术语表；必须明确单一document_id，跨版本不混；坏文件/未下载/失败/Mock默认不可作为Live检索 |
| 无LLM降级页面 | PASS（实际空库） | 独立Streamlit资料库/搜索入口；五输入BLOCKED、目录0，三个用户问题只给证据不足，不产生条款或适用日期 |
| Module01回归 | PASS | 完整223 pytest中包含原204测试；代码/配置与7d6fbc9范围比较无差异 |

这不是已验证的EUR-Lex/Cellar正式适配器：当前只建立官方域受限的通用下载基础，实际终点、跨主机跳转、内容协商、权限及原文身份均待manifest与官方现场验证。同主机保护不绕过。继承SafeFetcher的4MB解码后上限、20秒超时/最多1重试；更大PDF会明确阻断，尚未实测大型REACH/P0文本。安全重跑采用整文件重下，不承诺HTTP Range续传。

## 关键真实验收逐项

| 用户验收项 | 状态 | 本轮结果 |
|---|---|---|
| 一份P0官方原文真实下载/SHA256 | BLOCKED | 0，缺实际manifest/源审计，未下载2023/1542；无真实SHA可提供 |
| 真实Article与Annex定位 | BLOCKED | 真实解析0；仅合成结构单元测试 |
| 中文问题检索到正确真实英文条款 | NOT TESTED | 没有真实知识库，不以测试文本冒充 |
| 真实问答引用与原文一致 | NOT TESTED | 真实引用0；仅合成引用可追溯校验 |
| 不同版本不混 | PASS（单元） | 正式/整合不同身份，检索强制指定版本；相同字节CAS去重不合并版本元数据 |
| 未下载/失败/无依据降级 | PASS（单元+浏览器） | 不产生引用，三个问题均明确证据不足 |
| Module01原有测试 | PASS | 全套223通过、未更改Module01功能代码 |
| Windows原生运行 | NOT TESTED | 命令已给出；依赖纯Python，不冒称Windows验收 |

**实际计数：目录导入0、真实下载0、真实解析0、真实Article/Annex0、真实检索闭环0。** 数据库三表实际均0行，未把合成PDF/Mock请求纳入Live计数。机器证据：regulatory/INPUT_AND_TEST_EVIDENCE.json。

## 测试与浏览器

- `pytest -q --junitxml=runtime/regulatory/test-results.xml`：**223 passed in14.45s**，无失败/跳过。新增18基础设施+1空库UI测试；原204通过。
- `ruff check src tests scripts migrations/versions/004_regulatory.py`：PASS；`pip check`无依赖冲突。
- 实际Chromium155，本地独立空库、所有外部资源阻断：显示五缺失输入/目录0，三个问题分别输入后返回证据不足、无引用/法律结论、无pageerror。仅空库/阻塞降级验收PASS，不能称为真实RAG浏览器通过。
- [浏览器JSON](evidence/regulatory/browser.json)；[实际截图](evidence/regulatory/missing-inputs-empty-library.png)。原文下载/版本选择/真实引用链接的浏览器流程NOT TESTED。

## 本地存储与Windows/PyCharm

本轮没有法规原文文件。默认后续存储：`runtime/regulatory/files/objects/<SHA前2位>/<SHA>.<pdf|html|xml>`；法规库`runtime/regulatory/library.db`，独立页面测试库`runtime/regulatory/uat.db`。研究输入应放`data/regulatory/research/`；runtime及data/regulatory均被Git忽略。只提交代码、无数据模板与验收证据，没有PDF、原始Work文件、密钥或公司数据。

在仓库根目录，Python3.12：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m scm.regulatory.cli inputs
.\.venv\Scripts\python.exe -m streamlit run src/scm/regulatory/app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true --browser.gatherUsageStats false
.\.venv\Scripts\python.exe -m pytest -q
```

PyCharm选择`.venv\Scripts\python.exe`作为解释器，工作目录设为仓库根目录；Run Configuration模块`streamlit`，参数同上。资料库不改变原Module01启动方式/页面/端口。只有实际文件提供并完成字段映射/源许可审查后，才用标准化manifest：

```powershell
.\.venv\Scripts\python.exe -m scm.regulatory.cli import-manifest <normalized_manifest.csv>
.\.venv\Scripts\python.exe -m scm.regulatory.cli download
.\.venv\Scripts\python.exe -m scm.regulatory.cli parse <document_id>
.\.venv\Scripts\python.exe -m scm.regulatory.cli search <document_id> "Article 7 对碳足迹有什么要求？"
```

默认download仍NEEDS_PERMISSION；不能为了让命令成功而填写虚构许可。Linux验证命令可用已安装的`/workspace/.venvs/supply-chain/bin/python`；批量任务建议外层`timeout 120s`，按失败阶段记录而不循环重试。页面本地运行，不公开部署。

## 待完成与停止

实际五文件读取/Work映射、EUR-Lex/Cellar权限/终点验证、一份2023/1542真实PDF/HTML、真实结构/法律身份核对、中文真实检索引用均BLOCKED/NOT TESTED。OCR、准确复杂表格、精确XML语义、跨多法规比较、真实LLM法律分析未实现；轻量词表/BM25非语义检索，未做准确率评估。法效/适用性永远待核实，不由日期自动推导。

请提供五份实际附件或放入指定目录，才能继续最重要的真实闭环验收。本轮按缺输入限定完成基础设施后停止，不自动扩大法规目录或伪造成功。
