# Issue #2：有限范围真实官方情报验收

日期：2026-11-06（Asia/Shanghai）。**技术验收PASS（3个部门来源、15篇）；业务/法律人工终审NOT TESTED，Issue保留OPEN待Owner评审。**

三个来源为欧委会不同部门，属于同一机构；不是三个独立机构，也不表示港口/电池主题已完整覆盖。

## 实际执行

```bash
scm collect --source ec --source ec-trade --source ec-industry
# 再执行一次同命令：每源5 unchanged，共15，无重复
python scripts/validate_live.py
scm audit --output SOURCE_AUDIT.md
```

真实获取：3源各5篇，15篇均有标题、原始发布日期、正文、来源及抓取时间。解压缺陷修复后取得；没有降低TLS校验、绕过robots/挑战/登录/跨域限制。欧委会公开复用许可CC BY 4.0已读取并保留署名/修改说明。

验收时间：2026-11-06T13:37:58.012003+08:00

## 真实样例与核对

### ec

- 原始文章：https://transport.ec.europa.eu/news-events/news/joint-press-release-19th-implementation-meeting-eu-china-maritime-transport-agreement-2026-10-20_en
- 标题：Joint press release on the 19th implementation meeting of the EU–China Maritime Transport Agreement
- 原始发布（保留UTC）：2026-10-20T08:03:49+00:00
- 实际采集：2026-11-06T05:36:40.939006+00:00
- 分析：2026-11-06T05:34:33.273843+00:00
- 严重度/生命周期：低 / unknown；规则 2026-11-06.4
- 原始正文SHA256：43030c8aefdad5ab8213010dd5ea5a340c4c332a3514a4b4069e7093be74c6e3
- 重复入库：unchanged，事件ID 13
- 日报：2026-10-20，报告ID 5
- 源HTML独立对照：PASS: retained source HTML independently parsed; original title, datePublished and complete extracted text match stored current raw revision

### ec-trade

- 原始文章：https://policy.trade.ec.europa.eu/news/commission-acts-against-imports-pet-spunbond-china-2026-10-30_en
- 标题：Commission acts against imports of PET Spunbond from China
- 原始发布（保留UTC）：2026-10-30T10:59:23+00:00
- 实际采集：2026-11-06T05:36:52.059123+00:00
- 分析：2026-11-06T05:34:48.766555+00:00
- 严重度/生命周期：中 / unknown；规则 2026-11-06.4
- 原始正文SHA256：f3a14d502b89df02741adbae6c341e0d8485615a5e0e67c1ca020ade7579c548
- 重复入库：unchanged，事件ID 22
- 日报：2026-10-30，报告ID 6
- 源HTML独立对照：PASS: retained source HTML independently parsed; original title, datePublished and complete extracted text match stored current raw revision

### ec-industry

- 原始文章：https://single-market-economy.ec.europa.eu/news/eu-campaign-highlights-lift-buffer-safety-performance-2026-10-29_en
- 标题：EU campaign highlights lift buffer safety performance
- 原始发布（保留UTC）：2026-10-29T09:40:56+00:00
- 实际采集：2026-11-06T05:36:45.200887+00:00
- 分析：2026-11-06T05:34:42.182738+00:00
- 严重度/生命周期：低 / unknown；规则 2026-11-06.4
- 原始正文SHA256：33434edd8d9e95680fe52f106e2f9a6d3b93f3aa551cc8297030f4c3043662a9
- 重复入库：unchanged，事件ID 16
- 日报：2026-10-29，报告ID 7
- 源HTML独立对照：PASS: retained source HTML independently parsed; original title, datePublished and complete extracted text match stored current raw revision

## 逐项事实/范围核对

由Codex对实际HTML和JSON-LD作工程核对，不冒称用户人工签核：

- DG MOVE：会议于2026-10-19在上海举行；原始datePublished是2026-10-20T10:03:49+02:00（入库转UTC08:03:49），没有把会议时间当发布时间。没有公告证明某港正在中断，生命周期unknown，不形成港口高风险。
- DG TRADE：导语明确产品为中国PET Spunbond；正文的39.8%–48.1%最终反倾销税、五年期限与数据库一致。导语在article之外，已专门提取。不能把这个产品范围推定为电解液或所有中国商品；准确适用范围、HS编码及原法规生效条款仍需核实，所以effective_at为空、政策状态不凭猜测升级。
- DG GROW：样例为lift buffer安全测试，与电解液业务只有间接相关性。标题/原发布日期/正文与实际HTML一致，不冒充电池政策或港口告警。

## 页面与日报

对当前15篇Live、原5篇Demo的数据库运行Streamlit AppTest：Overview计数15；Intelligence呈现三样例、来源、许可和不确定性，无Demo混入；Reports逐一选中三个实际HTML报告，无异常。
样例日报按10月20/29/30原发布日期生成，不将采集日当成新闻日。当天Live日报仍说明覆盖不足。HTML有来源链接、引文、条件性分析、风险依据、CC许可；完整正文不进Git，只在本地SQLite，公共许可的最小摘录用于回归。

## 未完成/限制

- Rotterdam：copyright禁止下载/复制，来源停用，本轮临时取得的5篇正文/分析已删除，排除验收计数。
- EUR-Lex robots202、CATL跨域跳转、Antwerp/Hamburg正文发现/解析未通过；未反复请求或绕过。
- Maersk/Hapag仅robots200/允许列表的探测，正文和复用条款NOT TESTED。
- 15篇来自同一欧委会机构的三个部门；没有真实港口等待时间、具体运输柜号、CATL/电池主题完整覆盖或预测准确率验证。
- 仅无LLM规则模板及原文摘录；真实LLM与用户人工业务/法律审核NOT TESTED。

证据文件：docs/LIVE_EVIDENCE_2026-11-06.json；完整逐源访问阶段：SOURCE_AUDIT.md；自动测试与CI：TEST_REPORT.md。
