# Issue #5 Phase 2A 验收 — PARTIAL

执行：2026-11-09（Asia/Shanghai），Python 3.12；现有 feature/supply-chain-risk-mvp，PR #1 保持 Draft，不合并 main。授权依据：Issue #5 评论 6730810249。仅6候选、2个最小连接器；本轮结束后停止等待评审。

## 实际结果

| 项目 | 状态 | 实际证据与边界 |
|---|---|---|
| 权限与逐篇日期检查点 | PASS（有限范围） | 0b94b26：PHASE2_SOURCE_MATRIX.md、PHASE2_SOURCE_EVIDENCE.json；6候选中2个有条件允许文字、3个link_only、1个unknown；不是6源正文采集通过 |
| 新连接器→真实HTTP→解析→SQLite原文/分析 | PASS（技术链路） | Hamburg 3篇、EC Batteries 1篇，共4个新入库URL，原始公布时间保留；没有把旧15篇拷贝来计数 |
| 独立机构 | PARTIAL | 2个门户发布机构：HHM官方门户（行业协会，不是监管机构）与European Commission；相对旧EC基线只新增1个机构，未达到新增2–3个机构的理想目标；HHM文章也可能转载其他官方发布者，不代表独立交叉核验 |
| 真正业务优先信号 | PARTIAL | relevant=0、possibly_relevant=1（2025年电池法规背景）、excluded=3（交流/一般技术背景）；不能声称已有当前可行动警报 |
| 新鲜度 | PASS（测量，不代表覆盖） | 7日内1篇；当日0篇合格。日期取逐篇页面，HHM站内时间按Europe/Berlin约定并标明假设；不以URL/列表/抓取时间替代 |
| 实际重复采集 | PASS | HTTP再次获取相同4篇；每次3+1 unchanged，inserted=0；events/raw_revisions/analyses保持4/4/4，日期/内容指纹不变 |
| 中文日报生成 | PASS（空结果路径） | 实际2026-11-09 HTML选入0条，明确覆盖不足、无合格当日新增，不用旧新闻凑数；实际HTML在 docs/evidence/phase2a_daily_2026-11-09.html |
| 有合格真实事件的中文日报 | NOT TESTED | 本轮没有合格当日真实事件，非空日报只在合成HTTP/DB测试通过，不能冒充真实验收 |
| 分级与生命周期保护 | PASS（代码与回归） | relevance不写risk_level/lifecycle；V1严重度只映射现有规则枚举，背景不成为当前已确认中断；不将电池法规直接认定电解液适用 |
| Live/Demo、来源故障隔离 | PASS（回归） | 独立Live验收库，不seed Demo；权限失败零文章请求、单源失败不阻止下一源、Demo日报不混Live、排除记录仍可审计 |
| 完整pytest / ruff | PASS | 178 passed in 11.71s；ruff check src tests scripts全通过；新增21个行为测试（不计作真实新闻或准确率） |
| UI/原业务库冻结 | PASS（范围检查） | src/scm/ui、运行sources.json、数据库模型/迁移均未改；原runtime/scm.db八表行数与基线一致；未运行浏览器或Windows验证 |
| 整体生产/业务情报验收 | PARTIAL | 新链路可运行，但缺当日业务信号和非空真实日报，覆盖不足；Issue #5保持OPEN |

## 实际入库文章

逐篇URL/标题/日期/原始版本/内容指纹、风险理由、相关性原因码、重复计数和请求HTTP见 [PHASE2_LIVE_EVIDENCE.json](PHASE2_LIVE_EVIDENCE.json)。其中：

- Hamburg：11th chainPORT meeting，2026-11-05；eFuel/DAC competence center，2026-10-20；Prague reception，2026-10-12。均保留，但不是优先供应链预警。
- EC：waste batteries recycling rules，2025-07-04。是本轮新获取的旧文章；不能称作今日新闻，适用主体/具体条款/电解液范围待核实。使用站内声明的同主机canonical URL，不自动跟随外域canonical。

## 实现与数据标准

复用SafeFetcher robots-first/速率/超时/解码后4MB/同主机HTTPS保护、现有ingest去重及RawRevision/Analysis。只补Hamburg #body文字和可见日期解析。新增Phase2A配置与严格权限门槛；unknown/metadata_only/link_only/blocked不执行新闻正文请求；许可复核超过30日需重新确认。

两阶段：先将合规来源全部候选原文/元数据入库保留，再在Analysis.payload_json.content_v1附加有理由的业务相关性评估；excluded不删除、不进入新日报优先条目。既有UI仍展示既有事件列表，未声称UI已采用此筛选。没有改数据库结构、风险规则或LLM Provider；该路径明确强制RuleProvider，不发LLM请求。

V1通过raw_revision_id关联原始层；raw_sha256沿用现有含标题/正文/日期的revision内容指纹（不是响应HTML字节hash），precision_note明确算法范围；响应HTML哈希另见证据JSON。事实只引用原文；中文标题/影响/行动是标明局限的模板，不宣称全文翻译或人工法律签核。协议修订及前版本引用有回归。

## 复现（本地，无API Key）

在仓库根目录，使用已安装依赖的Python3.12：

```bash
timeout 160s /workspace/.venvs/supply-chain/bin/python scripts/run_phase2a.py
timeout 160s /workspace/.venvs/supply-chain/bin/python scripts/validate_phase2a.py
/workspace/.venvs/supply-chain/bin/ruff check src tests scripts
timeout 120s /workspace/.venvs/supply-chain/bin/pytest -q
```

默认独立数据库runtime/phase2a/live.db，HTML与运行结果在runtime/phase2a/。validator要求先有真实采集；网络返回变更会导致幂等快照校验失败，应检查证据，不改业务规则迎合断言。测试依赖Mock的部分不计Live。所有HTTP继续继承代理及TLS；retries=0的验收、外层160秒限时，不绕过robots/条款/验证码。

Windows PowerShell可用 `.\.venv\Scripts\python.exe scripts\run_phase2a.py`（需要已有README依赖安装步骤），Windows原生执行仍NOT TESTED；脚本在终端运行，不改Streamlit。

## 阻碍与停止点

MSC/BASF/LG仅个人非商业或需书面同意，企业研究用途不能自动获得许可；Antwerp条款无法解析，维持unknown。Rotterdam未请求。未转向更多网站或付费API来填充数量。没有真实港口等待时间、船期确认或柜号因果判断。

下一步由Owner评审是否接受保守空日报与本轮相关性边界；若继续，再单独授权验证高价值运营/危险品来源。不得以当前4篇背景样本宣称业务目标完全达成。本轮结束后不自动进入Phase 2B。
