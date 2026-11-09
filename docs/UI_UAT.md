# Issue #4 V2 收尾验收

收尾记录：2026-11-09（Asia/Shanghai）。下述实际浏览器及本地UI测试执行于2026-11-06；保留原始时间，不将旧截图/采集记录冒充今日实时证据。

## 范围与提交顺序

按Owner本轮限制：不新增产品功能、不重构、不修改业务排序。先将全部现有V2原样提交并推送至feature/supply-chain-risk-mvp：**f911ad555a7612c8d78c210c6cdb69e231b814b9**。PR #1保持Draft，main未合并。

随后只处理浏览器的贸易文章排序失败：终止旧Streamlit进程，启动新进程并创建全新Chromium会话；检查已有排序与实际页面。收尾阶段没有修改src/、业务规则、数据库结构、来源配置或依赖声明，只保存验收文档/脚本副本/日志/截图。

## 结果

| 检查 | 状态 | 实际证据 |
|---|---|---|
| 原样保存/推送既有V2 | PASS | f911ad5，包含此前全部未提交修改和阶段性截图 |
| 停止旧Streamlit进程 | PASS | 终止15885（8502）、16603（8503），SIGTERM等待上限5秒，必要时强制终止；未修改数据 |
| 全新Streamlit进程 | PASS | 隔离QA库、127.0.0.1:8503；health返回200 |
| 全新Chromium会话 | PASS | Chromium 155.0.8059.79，新临时context，无旧storage/session；只允许localhost请求 |
| 贸易首卡排序 | PASS | 第一条为事件22：Commission acts against imports of PET Spunbond from China |
| 完整首屏队列顺序 | PASS | 前8条浏览器标题与后端既有排序逐项完全一致；没有降低或替换排序断言 |
| 页面异常 | PASS | 排序检查过程中无browser pageerror、无Streamlit异常 |
| 相关UI测试 | PASS | 48 passed in 9.33s；仅tests/test_ui.py和tests/test_ui_v2.py |
| 相关静态检查 | PASS | ruff检查UI模块、两份UI测试与两份已存在验收脚本，All checks passed |
| 业务排序代码未改 | PASS | presentation.py与f911ad5逐字节一致，SHA256见完整性证据 |
| 原有业务记录保留 | PASS | 原库8张表的行数/内容哈希与此前留存快照一致；浏览器读取隔离副本 |
| 全项目pytest | NOT TESTED（本轮未重跑） | 前轮完整137 passed属历史结果，本轮按限制只运行48项相关UI测试 |
| 全浏览器流程/移动端/上传交互 | NOT TESTED（本轮） | 原全流程脚本未完成，不能以本次排序通过宣称整个Issue所有浏览器验收通过 |
| Windows原生运行 | NOT TESTED | 提供复现命令，当前执行证据来自Linux |

## 原因与处理

旧进程中浏览器显示的顺序与独立Python查询不一致。终止旧进程并同时更换浏览器会话后，排序首次即通过，因此**不需要修改业务排序规则，也没有增加热重载/缓存重构代码**。

结果与旧进程/会话的陈旧状态一致；本轮没有进一步拆分Python模块缓存与浏览器缓存的各自影响，不将推测写成已独立证明的根因。首次成功后仅完善原生KPI/按钮加载等待以保存稳定截图，再做一次有界只读检查；没有重复运行整套浏览器业务流程。

已有排序仍为：确认/时效分层 → 业务相关性 → 发布时间 → 内容严重度。泛“产能”分类缺少原始标题中的电池证据时仍标相关性待核实，不会为通过测试提升贸易权重、篡改类别或人为置顶指定文章。

## 可复核证据

- [新进程排序结果JSON](ui_uat/sorting-fresh-results.json)：时间、代码SHA、预期/实际8条序列、浏览器版本、截图哈希。
- [排序与原库完整性](ui_uat/closeout-integrity.json)：presentation.py哈希、原库行数/内容哈希。
- [本轮实际执行的只读检查代码](ui_uat/verify_sorting.py)：从临时执行文件原样保存，不属于产品功能。
- [48项UI测试日志](ui_uat/ui-tests.txt)；JUnit保留在本机runtime/ui-qa/pytest-ui.xml。
- [变更前截图](ui_uat/before-live-1366.png)：a0700b1阶段，1366×768。
- [全新进程最终排序截图](ui_uat/after-live-fresh-1366.png)：1366×768，原始未裁剪/未编辑。
- ui_uat/after-live-1366.png仅是已保留的中间版本截图，**不能作为最终验收截图**。

截图只含公开欧委会情报元数据及本地UI；© European Union，CC BY 4.0，原始来源及复用许可参见既有SOURCE_AUDIT和fixtures/official/provenance.json。没有私人运输数据、专有设计素材或图片编辑；没有修改、隐藏或移除外部企业水印/覆盖层。

## 复现与超时

只读排序检查前先停止旧Streamlit（Ctrl+C），不要复用旧测试会话。复制现有SQLite到隔离QA库，**不要把原业务库当测试写入目标**。本轮未触发来源采集、付费API或公开部署。

Linux示例（仓库根目录；QA副本需已建立）：

```bash
SCM_DATABASE_URL=sqlite:///runtime/ui-qa/browser.db \
  /workspace/.venvs/supply-chain/bin/python -m streamlit run src/scm/ui/app.py \
  --server.address 127.0.0.1 --server.port 8503 --server.headless true
# 另一终端：
SCM_DATABASE_URL=sqlite:///runtime/ui-qa/browser.db \
  timeout 120s /workspace/.venvs/supply-chain/bin/python docs/ui_uat/verify_sorting.py
timeout 120s /workspace/.venvs/supply-chain/bin/pytest -q tests/test_ui.py tests/test_ui_v2.py
```

Playwright检查需要此前安装的playwright==1.56.0和/usr/bin/chromium；不是UI运行时依赖。健康请求10秒、导航30秒、断言15秒、检查整体120秒；UI测试整体120秒，ruff30秒；GitHub请求20秒、最终推送30秒。失败退出并记录，不无限重试。

Windows本地正常启动（PowerShell；依赖沿用README已安装的Python3.12环境）：

```powershell
git pull --ff-only origin feature/supply-chain-risk-mvp
# 如仍运行旧进程，先在其终端Ctrl+C，再全新启动：
.\.venv\Scripts\python.exe -m streamlit run src/scm/ui/app.py --server.address 127.0.0.1 --server.port 8501 --server.maxUploadSize 5 --browser.gatherUsageStats false
# 可选：只运行相关UI测试
.\.venv\Scripts\python.exe -m pytest -q tests/test_ui.py tests/test_ui_v2.py
```

服务启动后刷新浏览器；不要求Owner继续截图或决定技术实现。现有.streamlit/config.toml和单文件控件均使用5MB配置，应用仍保留5,000,000字节/1万行校验。本轮没有新增或修改上传逻辑。

## GitHub检查

f911ad5的两次既有自动CI实际读取均为completed/success：

- https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42194271037
- https://github.com/Gemini-BIAN/Information-Dashboard-and-Risk-Warning/actions/runs/42194278552

这是推送触发的既有workflow，本轮没有手动重跑全量测试或修改CI。PR保持Draft；Issue #4完整浏览器DoD未宣称全部通过，收尾结果限于本次指定的排序问题及相关UI回归。
