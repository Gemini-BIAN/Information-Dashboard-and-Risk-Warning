# 下一任务清单（给后续AI）

## P0：外部访问及验收

- [ ] 网络设置生效后，运行 `scm collect`、`scm audit`，验证10个官方候选源；任何失败保持BLOCKED，不绕过限制。
- [ ] 完成人工robots/使用条款确认；逐站核实正文及发布日期。未验证的解析器不可标稳定。
- [ ] 读取 GitHub Issues、未解决PR Review；当前API 403，PR状态以PROJECT_STATUS.md为准。访问恢复后创建/更新PR，不合并。
- [ ] 检查远程CI运行结果；本地PASS不能冒充远程CI PASS。

## P1：可独立开发

- [ ] 基于可合法保存的官方公告增添站点适配器及真实解析回归Fixtures（标明来源、时间及许可，不编写假新闻）。
- [ ] 政策状态/生效日期解析支持更多语言与条款级时间，建立人工修正机制。
- [ ] 公告解除/撤回状态、多来源事件实体聚合、同一周期报告版本化。
- [ ] 航次分段及挂靠序号；保留待核实关联，不据港口拥堵判断甩柜。
- [ ] Windows原生验证、跨日调度与SQLite备份恢复演练。

## 规则

先读 README、PROJECT_STATUS、DECISIONS、TEST_REPORT、SOURCE_AUDIT、KNOWN_LIMITATIONS；不把演示数据转成真实数据，不提交runtime或密钥。现有checkout已隔离，不建worktree。新的开发走feature分支。付费API、内部敏感数据、公网部署、核心目标改变及高风险操作需批准；常规技术选择自行完成。
