# Windows / PyCharm 本地运行

Python3.12；Windows原生尚未实跑，状态NOT TESTED。Linux相同模块命令/Streamlit/pytest已运行。无需LLM Key、Docker或付费服务，默认仅127.0.0.1。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m scm.platform.cli init
.\.venv\Scripts\python.exe -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

打开http://127.0.0.1:8503。左侧Live/Demo/Manual显式切换；演示需在Demo点击加载按钮，不在Live自动填充。三个业务模块、统一中心、报告、收件箱和Sources都在同一入口。旧Module01仍可按原README启动，不改端口/页面。

PyCharm解释器选择`.venv\Scripts\python.exe`，工作目录仓库根目录，Run Configuration模块`streamlit`，参数`run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false`。停止旧进程再验证代码变更，避免Python导入模块缓存造成旧新实现混用。

```powershell
# 无Key演示、报告、获准源单次采集（30日许可过期将阻断）
.\.venv\Scripts\python.exe -m scm.platform.cli demo
.\.venv\Scripts\python.exe -m scm.platform.cli report --mode demo --kind daily --output runtime/platform/demo-daily.html
.\.venv\Scripts\python.exe -m scm.platform.cli report --mode live --kind weekly --output runtime/platform/live-weekly.html
.\.venv\Scripts\python.exe -m scm.platform.cli collect --source hamburg
# 周期执行入口，可自行配置本机Task Scheduler；本轮未创建常驻任务
.\.venv\Scripts\python.exe -m scm.platform.cli collect --due
.\.venv\Scripts\python.exe -m scm.platform.cli import-file C:\local\public-notices.csv
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests scripts
```

默认库`runtime/platform/platform.db`；可设置`$env:SCM_PLATFORM_DATABASE_URL="sqlite:///runtime/platform/other.db"`用于Streamlit。CLI覆盖库使用全局`--database-url`，放在子命令前。首次调用自动Alembic迁移，重复init安全；不要指向暂停的法规库。SQLite本地文件不放同步共享盘并发写入，原业务库不自动复制或改写。

Sources可下载空CSV模板，或使用相同字段的XLSX。必填external_id/module/title/body/url；module为ports/capacity/market；日期使用带时区ISO8601，如2026-11-11T08:00:00+08:00。导入强制Manual；不要上传公司敏感信息，也不能将Demo改名放入Live。可选字段见模板；状态/单位受枚举校验，结构化主张需evidence_quote逐字存在于body。原文URL要求无凭据HTTPS。2MB/1000行，Excel解压总量20MB，拒绝公式。

企业名称与别名：config/platform_companies.json。来源：config/platform_sources.json。未知许可保持禁用，不仅凭robots允许就批准复用。JSON API约定为`{"records":[Record字段对象]}`，不自动猜测第三方API；需经许可与实际契约验证后才启用。HTML/PDF文档适配器并不使用暂停的法规RAG代码。

浏览器复现需额外安装Playwright和Chromium（开发工具，不是运行依赖）；`scripts/platform_browser_uat.py`默认Linux `/usr/bin/chromium`，Windows浏览器脚本未移植/实测。验收数据/命令详见PLATFORM_ACCEPTANCE，不要拿空新库直接运行要求4条Live的验收脚本并宣称通过。
