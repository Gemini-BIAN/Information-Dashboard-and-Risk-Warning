# Issue #2：真实官方情报 Live 验收

验证日期：2026-11-06（Asia/Shanghai）。**总状态 BLOCKED，不得关闭Issue #2或将PR转为正式Live验收通过。**

## 实际执行

在仓库根目录：

```bash
/workspace/.venvs/supply-chain/bin/scm init
/workspace/.venvs/supply-chain/bin/scm collect
/workspace/.venvs/supply-chain/bin/scm audit --output SOURCE_AUDIT.md
/workspace/.venvs/supply-chain/bin/scm report --kind daily --mode live --output runtime/reports/daily-live.html
/workspace/.venvs/supply-chain/bin/scm report --kind weekly --mode live --output runtime/reports/weekly-live.html
```

10个配置来源均由真实HTTP客户端尝试。实际请求停在各站 `https://<host>/robots.txt`；平台HTTPS代理返回 `CONNECT 403`。每源1次确定性拒绝，不盲目重试，不改代理、不直连、不绕TLS/robots/登录/CAPTCHA。逐源请求URL、验证UTC时间、耗时、失败阶段和最近真实成功时间均见SOURCE_AUDIT生成记录。

当前实例网络观察：restricted/enforced，custom_allowed_hosts=[]，只有package_managers预设；所需官方主机和api.github.com的配置草稿先前已保存，但未作用于此实例。GitHub公开网页在允许范围内，可正常读取Issue/Review/Actions；API域名访问被拒绝。

## 验收结果

| 项目 | 状态 | 证据 |
|---|---|---|
| 10个来源访问尝试、失败隔离和日志 | PASS | 每源独立BLOCKED记录，系统继续可运行 |
| 至少2个官方来源真实正文/日期获取 | BLOCKED | 成功来源0/10 |
| 真实正文取得/真实Live事件入库 | BLOCKED | 本轮及当前空间均0 |
| 真实事件样例URL及时间核对 | NOT TESTED | 没有取得真实正文，不伪造示例；候选入口不是新闻样例 |
| 原文→解析→去重→规则→UI→日报真实链路 | BLOCKED | 真实事件0；合成/Mock端到端通过不能替代此项 |
| 每来源覆盖/耗时/失败/最后成功遥测 | PASS | 功能已运行；本次最后成功为空，无虚构成功日期 |
| 失败日不宣称没有重要新闻 | PASS | 实际Live日报/周报含“采集覆盖不足”；自动回归覆盖 |
| 站点专用正文适配器与官方原文Fixtures | NOT TESTED | 站点正文未获准访问，无合法取得的官方文章可作为回归基线；未编造官方Fixtures |
| 正常GitHub公开网页Review/CI基线 | PASS | 已读取Owner Review及基线成功运行；新提交CI另见TEST_REPORT |

## 恢复后的验收步骤

使保存的允许域名配置在运行实例生效后，先重试2–3个官方来源。每站确认robots与使用条款允许、列表/feed可用、文章 canonical URL、真实正文和原始发布日期；再依据真实结构补专用解析器及许可允许的回归材料。

至少一条真实事件必须经去重重跑不增记录、规则与原文对照、Live页面查看、当日/指定发布日期日报输出。人工核对事实/状态/日期/引文，记录具体样例URL和采集时间，不把泛用解析器Mock成功记为站点适配成功。通过后更新本报告，Issue #2才具备申请关闭的依据。
