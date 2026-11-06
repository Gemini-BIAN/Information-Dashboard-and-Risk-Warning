## ESCIM：供应链情报MVP + Issue #2真实验收

继续feature/supply-chain-risk-mvp，保持Draft，不合并main。

### 最新实际结果（2026-11-06）

新发布环境网络与GitHub API读取已恢复。选定欧委会DG MOVE、DG TRADE、DG GROW三个部门来源，各5篇，**15篇真实文章**保留正文、原始发布日期、URL和抓取/分析时间。三部门是同一机构，不冒充三个独立机构。

- 再次真实采集15篇全部unchanged，无重复。
- 真实原文→专用解析→SQLite→独立风险规则→实际Live Overview/Intelligence/Reports→原发布日期日报通过；源HTML的标题/datePublished/正文与当前RawRevision独立对照通过。
- 99项本地pytest全部通过、0失败/0跳过；ruff与pip check通过。代码85e261d的push/PR两次CI已从API观察成功：42169750468、42169754791。
- 真实采集与离线Fixture/Mock明确区分；Demo仍5条虚构事件，与Live隔离；没有把旧文章改为今日新闻。

### 实现与修复

原MVP六工作台、SQLite/Alembic、采集、版本/审核、ETA快照、HTML报告和调度保留。前轮Issue #3政策/生命周期修复继续通过。

本轮修复HTTPX流式响应的双重gzip解压，保持TLS与解码后4MB限制；欧委会article/独立导语解析，提供CC署名的真实最小摘录回归。规则2026-11-06.4补充反倾销信号，不由LLM决定风险。

### 许可与剩余问题

欧委会文本CC BY 4.0，来源/页面/HTML/Fixture标明署名、许可和修改。Rotterdam明确限制下载/复制，停用并清理本轮5份临时正文/分析/HTML副本，不计入15篇，未提交受限正文。

EUR-Lex robots202、CATL跨域跳转停止；Antwerp/Hamburg正文发现/解析未成功。Maersk/Hapag仅robots探测，正文及复用NOT TESTED。今日总体覆盖仍不足，不宣称没有重要新闻。无可靠等待时间、真实航次、CATL/电池专题完整覆盖或预测准确率保证。

仅工程原文对照，不冒称用户业务/法律签核；真实LLM、Windows、跨日调度仍NOT TESTED。Issue #2保持OPEN待Owner评审此有限范围验收，PR保持Draft。

### 可复核交付

SOURCE_AUDIT.md、TEST_REPORT.md、docs/LIVE_ACCEPTANCE.md、docs/LIVE_EVIDENCE_2026-11-06.json、fixtures/official/provenance.json。重现：先scm collect --source ec --source ec-trade --source ec-industry，再python scripts/validate_live.py。

没有付费API、公司敏感信息上传或公网部署，不自动合并main。
