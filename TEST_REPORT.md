# MVP 测试与验收报告

验证日期：2026-11-06（Asia/Shanghai）。Python 3.12.14，Linux，此仓库独立feature分支。测试结果是实际执行结果，不代表模型准确率或生产就绪。

## 自动测试：PASS

命令：

```bash
/workspace/.venvs/supply-chain/bin/pytest -q --junitxml=runtime/test-results.xml
```

最近完整结果：**47 passed in 10.26s**；0 failed、0 skipped。JUnit结果保存在本地忽略路径 `runtime/test-results.xml`。测试不依赖真实网站或LLM API；HTTP行为以MockTransport验证，真实来源访问另见下表。

| 检查 | 结果 | 实际证据 |
|---|---|---|
| Alembic迁移、外键、重复初始化 | PASS | 临时SQLite真实建库、重复upgrade head |
| 无API Key核心运行 | PASS | 子进程移除Key；init→demo两次→日报/周报 |
| Fixture端到端入库、来源保留 | PASS | 5条事件、5条分析，原文和分析分表 |
| 重复采集幂等、URL/内容去重 | PASS | 同源重复不新增；第二次演示5 unchanged |
| 内容/发布日期更新保留版本 | PASS | 新RawRevision、重新审核，不覆盖旧原文 |
| 单一来源失败不影响其他来源 | PASS | Mock 403来源与成功来源同批执行、独立日志 |
| robots拒绝、异常HTML、跨域跳转 | PASS | 受限请求在文章抓取前停止 |
| 超时/有限重试设计、503重试 | PASS | Mock 503后成功；httpx timeout配置 |
| RSS与HTML、发布日期/正文解析 | PASS | RSS只定位文章，另抓正文；未知日期保持空 |
| 可解释风险、否定与不确定性 | PASS | 高/中/低关键词规则及原句依据 |
| 政策状态与有限生效日期解析 | PASS | 提案/通过/实施/废止/未知，未来日期不假定已实施 |
| 港口风险缺数据、陈旧公告、驳回 | PASS | 未知、30天窗口、审核排除、空间隔离 |
| 人工风险调整与原因/到期/审计 | PASS | 服务层与Streamlit真实表单交互 |
| 人工确认/驳回/备注 | PASS | 服务层状态与ReviewLog断言 |
| ETA快照与变化 | PASS | DEMO-0001两快照+72h；单快照未知；ATA到港 |
| 乱序与同港比较边界 | PASS | 乱序按Updated At；不同POD不跨港比较 |
| CSV校验、重复、冲突、空间保护 | PASS | 带时区、严格表头、重复跳过、冲突拒绝 |
| 港口公告候选关联 | PASS | 时间窗口+POD，明确待核实及非甩柜证据 |
| LLM可替换、引文校验/失败回退 | PASS | Mock合法引文通过，编造引文拒绝回退；分级仍规则 |
| 日报/周报HTML与历史记录 | PASS | 实际写SQLite和HTML；专题聚合、时区、无新闻说明 |
| HTML及CSV安全输出 | PASS | 原文HTML转义、CSV公式注入保护 |
| Demo/Live隔离 | PASS | Live Overview为0、不出现Demo事件/航次 |
| Streamlit六页面 | PASS | AppTest执行Overview、Intelligence、Port、Shipment、Reports、Sources，无异常 |
| 新临时库CLI端到端 | PASS | init/demo重复/报告实际子进程，校验事件/快照/HTML |

## 实例运行验证

| 检查 | 状态 | 结果 |
|---|---|---|
| 依赖安装与可重复刷新 | PASS | 实际创建venv；锁定依赖安装；再次pip install -r requirements.lock及editable安装成功 |
| 静态检查 | PASS | `ruff check src tests`：All checks passed |
| Streamlit本地启动 | PASS | 127.0.0.1:8501，Uvicorn已启动；未公网部署 |
| 本地功能请求 | PASS | GET /_stcore/health →200/ok，GET / →200且包含Streamlit HTML |
| 演示数据库 | PASS | 当前5条Demo事件、3条Demo快照、2份Demo报告 |
| Live空间及无新闻报告 | PASS | 0条真实事件、0条真实航次；2份Live日报/周报明确无重要新增及来源失败 |
| HTML实物文件 | PASS | runtime/reports/daily-demo.html、weekly-demo.html、daily-live.html、weekly-live.html |
| 调度启动与回调 | PASS | 3个任务注册、Scheduler started；测试执行报告job callback，随后停止冒烟调度进程 |
| 跨日/整周持续调度 | NOT TESTED | 未等待实际日历触发；不将启动成功当作多日运行证明 |
| 10个官方候选源采集 | BLOCKED | 代理连接拒绝，0篇成功；逐源审计详见SOURCE_AUDIT |
| 实际LLM服务 | NOT TESTED | 没有购买服务或调用真实API，使用可选Provider的Mock契约测试 |
| 真实港口拥堵/等待时间 | BLOCKED | 未有可靠合法接入的数据源，无真实时间序列，无模拟冒充 |
| Windows原生运行 | NOT TESTED | 已提供PowerShell命令，当前只有Linux执行证据 |
| 人工浏览器视觉/全部点击路径 | NOT TESTED | 使用AppTest与本地HTTP，未宣称人工浏览器视觉验收完成 |
| GitHub HTTPS推送 | PASS | 初始main及feature成功推送；后续提交状态见PROJECT_STATUS |
| GitHub Issues/PR Review/PR创建 | BLOCKED | GitHub API Forbidden；不能读取/创建即不宣称成功 |
| 远程GitHub Actions结果 | NOT TESTED | 已提供workflow；未读取远程运行结果 |
| 公网部署、付费API、内部系统连接 | NOT TESTED | 未请求、未执行，不是本地MVP验收前提 |

## 结论

无API、Fixtures和本地网页开发路径已实际运行；所有已执行pytest通过。真实情报监控仍受外部网络限制，不能宣称具备生产实时数据覆盖。真实LLM、港口时序、Windows、跨日调度和远程CI没有验证的能力均单独标记。后续行动见NEXT_TASKS.md。
