# ESCIM 项目状态

2026-11-06（Asia/Shanghai）。唯一仓库Gemini-BIAN/Information-Dashboard-and-Risk-Warning，分支feature/supply-chain-risk-mvp，PR #1保持Draft，不合并main。

## 本轮 Issue #2

**有限范围Live技术验收通过**：新发布实例网络unrestricted/enforced，GitHub API读取恢复。三个欧委会部门来源（DG MOVE、DG TRADE、DG GROW，同一机构的三个来源）各5篇，共15篇真实正文和原始发布日期保留。两次真实采集后均无重复，第二次15 unchanged。实际Live Overview/Intelligence/Reports通过AppTest；原发布日期日报HTML生成、引文/风险/许可可追溯。三样例HTML标题/日期/正文与入库独立对照通过。

完整pytest **99 passed，0 failed/0 skipped**；ruff通过。源审核/验收JSON及测试报告已更新。Issue #2保留OPEN等待Owner验收，不宣称已生产就绪或所有来源打通。

## 修复

- 修复SafeFetcher双重gzip解压：iter_bytes已解码，重建响应不能保留压缩头；继续限制解码后4MB，保留TLS。
- 欧委会专用article范围和独立导语合并，不漏掉PET产品/征税核心事实；两个署名CC BY 4.0真实摘录Fixture提供离线回归。
- 规则2026-11-06.4增补反倾销/进口税信号分类，风险仍由规则决定；#3政策/生命周期保护继续通过。
- 页面/HTML明确© European Union、CC BY 4.0、原始链接及提取/中文模板修改说明。没有实际LLM调用。

## 权利与失败

首次修复后Rotterdam临时取得5篇；随后核实其copyright页面明确限制下载/复制，立即停用并清理本轮正文/分析及本地HTML副本，仅留URL/状态审计，**不计入15篇**。未提交受限正文。

EUR-Lex robots202 fail closed；CATL跨域robots重定向未跟随；Antwerp/Hamburg仍缺合格文章解析；Maersk/Hapag仅robots探测，正文/复用尚未测试。其他来源不是当前网络403，不能再笼统归为“网络未配置”。详见SOURCE_AUDIT。

今日配置来源覆盖仍不足；历史文章按10月原发布日期生成样例日报，不伪造为11月6日新新闻。无可靠港口等待时间、实际航次、CATL/电池法规全覆盖，无用户业务/法律人工签核，无付费API、敏感数据上传或公网部署。

## 验收证据与后续

- docs/LIVE_ACCEPTANCE.md：样例URL、状态、步骤和边界。
- docs/LIVE_EVIDENCE_2026-11-06.json：实际采集/原始发布时间/分析时间、源正文哈希、风险理由、重复与页面结果。
- scripts/validate_live.py：需要先有近24小时真实采集，验证现有数据库和页面，不制造数据或把离线Fixture计作Live。
- 下一步由Owner审阅有限范围验收；再按业务优先级解决其他来源许可/解析与相关主题覆盖。不能用15篇部门新闻替代实时港口预警或电池行业完整覆盖。

## GitHub

已用恢复后的API读取Owner两轮Review及Issue #2。第二轮Review认可#3代码层面修复，#2仍要求真实验收。代码提交85e261d已推送PR #1；本轮CI和PR/Issue结果写入待实际确认后追加。旧环境的API403仅为历史，不能当当前阻碍。


## 最终外部写入与运行回执

- GitHub API PATCH PR #1描述成功，保持draft=true；更新时间2026-11-06 13:45:53（Asia/Shanghai）。
- Issue #2评论POST成功：https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/issues/2#issuecomment-6677957601 。保留OPEN等待Owner评审，没有自行关闭或合并。
- 代码85e261d的CI成功；文档/证据8a3f2fc的push与PR两次CI亦由API确认completed/success：42170291262、42170295767。
- 新实例最新Streamlit已在127.0.0.1:8501启动；health与首页均HTTP200。实际15篇Live页面另由AppTest验证。没有公开预览、生产部署或调度常驻承诺。
- 收尾只更新写入/检查回执，无代码或验收数据变更。GitHub API已读写成功，旧403不是本轮剩余问题。

## Issue #4 V2 有界收尾

现有V2已于f911ad5原样提交/推送，PR #1保持Draft。按Owner限定停止旧Streamlit，使用新进程/新Chromium会话后，贸易首卡及前8条全序列与后端一致；没有修改业务排序，也没有加入缓存/热重载重构。

实际排序验收与48项相关UI测试执行于2026-11-06（48 passed in 9.33s）；2026-11-09保存收尾文档。业务原库8张表的行数/内容哈希保持不变。完整证据与未测边界见docs/UI_UAT.md；不宣称全浏览器/移动端流程已验收。前轮137全量通过仅作历史，本轮未重跑全量。代码f911ad5自动CI两次success，main未合并。
