# 下一任务清单（给后续AI）

## P0：外部访问及验收

- [ ] 网络设置生效后，运行 `scm collect`、`scm audit`，验证10个官方候选源；任何失败保持BLOCKED，不绕过限制。
- [ ] 完成人工robots/使用条款确认；逐站核实正文及发布日期。未验证的解析器不可标稳定。
- [x] 已通过允许的公开网页读取Issue #2/#3与PR #1 Owner Review；API写入仍403，不合并。
- [x] 已核实64e1016修复提交的push与PR synchronize CI成功；其他未核实SHA不据此推断。

## P1：可独立开发

- [ ] 基于可合法保存的官方公告增添站点适配器及真实解析回归Fixtures（标明来源、时间及许可，不编写假新闻）。
- [ ] 政策状态/生效日期解析支持更多语言与条款级时间，建立人工修正机制。
- [ ] 公告解除/撤回状态、多来源事件实体聚合、同一周期报告版本化。
- [ ] 航次分段及挂靠序号；保留待核实关联，不据港口拥堵判断甩柜。
- [ ] Windows原生验证、跨日调度与SQLite备份恢复演练。

## 规则

先读 README、PROJECT_STATUS、DECISIONS、TEST_REPORT、SOURCE_AUDIT、KNOWN_LIMITATIONS；不把演示数据转成真实数据，不提交runtime或密钥。现有checkout已隔离，不建worktree。新的开发走feature分支。付费API、内部敏感数据、公网部署、核心目标改变及高风险操作需批准；常规技术选择自行完成。

## 本轮更新：Issue #2/#3

- [x] 通过正常GitHub公开网页读取Draft PR #1、Owner Review及Issue #2/#3；基线Actions成功已核实。
- [x] 政策状态/日期与运营生命周期修复，93项pytest及ruff通过，旧数据库升级/重算与前后审计验证。
- [x] 覆盖不足报告、来源遥测、真实与注入客户端区分；10源重新真实访问并保存CONNECT403证据。
- [ ] Issue #2继续OPEN/BLOCKED：使网络配置在实例生效，再补至少2源真实采集、官方原文回归及人工事实核对。
- [x] 本轮64e1016的Actions运行42155814204及42155815831均实际观察成功。
- [ ] API写入可用后提交docs/ISSUE_RESULTS结果、更新PR描述；Issue #3由Owner据结果确认关闭，PR保持Draft直到Live验收通过。


## 网络发布后的最新进展（2026-11-06）

- [x] 新实例策略生效，GitHub API读取与官方站点HTTP访问恢复，未重新应用旧配置或发布内容。
- [x] 选定3个欧委会部门，15篇真实全文/日期；重复真实采集15 unchanged；实际Live页面/原发布日期日报/源HTML对照通过。
- [x] gzip缺陷、欧委会导语解析、CC许可标识及99项测试通过；证据见最新SOURCE_AUDIT和docs/LIVE_ACCEPTANCE。
- [ ] Issue #2由Owner评审有限范围Live验收；保留OPEN。上方旧“0/10网络BLOCKED”是前轮历史记录，不能当当前结果。
- [ ] 业务优先：合法取得电池/电解液直接相关官方消息、真实港口公告；其他候选分别解决许可、robots、跨域审核或站点结构，不绕过。
- [ ] 复用限制未解除时保持Rotterdam停用。Maersk/Hapag未核实复用前不进行正文采集；其他站点同样需条款确认。

- [x] 本轮代码85e261d及证据8a3f2fc的push/PR检查均实际确认success；API描述更新及Issue #2评论已实际发布，见PROJECT_STATUS回执。Issue #3按Owner评审流程处理，不替其自行关闭。

## Issue #5 暂停点（2026-11-09）

第一阶段交付后停止，等待用户第二阶段指示。届时按 SOURCE_MATRIX 核实条款及文章日期，选择 2–3 个允许来源，完成最小采集→标准化→相关性→证据/规则→中文日报；验证去重、新鲜度与 Live/Demo 隔离。当前不扩 UI，不将 PARTIAL 写成 Live 验收成功。
