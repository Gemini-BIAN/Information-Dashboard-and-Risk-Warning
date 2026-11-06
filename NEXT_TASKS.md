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
