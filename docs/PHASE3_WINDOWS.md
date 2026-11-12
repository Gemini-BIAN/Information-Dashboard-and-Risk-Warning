# Phase3 Windows/PyCharm验收步骤

Windows基础启动由用户此前验证；本轮新增功能在原生Windows未实际复验（NOT TESTED），Linux281自动测试及桌面/390px浏览器已验。

拉取feature/escim-intelligence-platform后停止旧Streamlit/PyCharm运行进程。解释器Python3.12、工作目录仓库根；沿用.venv，不用付费Key：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m scm.platform.cli init
.\.venv\Scripts\python.exe -m scm.platform.cli collect --source ec-weekly-fuel
.\.venv\Scripts\python.exe -m scm.platform.cli decisions --mode live
.\.venv\Scripts\python.exe -m scm.platform.cli decision-report --mode live --kind weekly --output runtime/phase3/live-weekly.html
.\.venv\Scripts\python.exe -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false
```

init自动迁移至005，先自行备份本地DB；不把暂停法规库指定为platform库。默认runtime/platform/platform.db，旧runtime/scm.db不自动迁移/复制。本次无新Python依赖。CLI全局--database-url须放子命令前；Streamlit库可用SCM_PLATFORM_DATABASE_URL指定。

人工验收：

1. 统一中心Live看到官方柴油观测；检查observed_at来自工作簿A2、发布日期未知、单位转换和原文SHA；无关联时影响未知。
2. 展开卡片，确认来源主张/规则/人工核实/用户数据/行动分开，不因处理confirmed自动确认事实。
3. Demo显式加载，保存“处理中”及原因；切回Live/Manual无DEMO数据。核实勾选仅在真正检查引文后用，不在Live练习虚假核实。
4. Reports生成weekly并下载decision_weekly HTML；今日无新增不凑数。Sources查看实际HTTP尝试样本，许可未知来源禁用。
5. 港口01仍只有纯地图，四标签保留；地图底图稳定性/视觉后续单独优化。
6. 中文路径、CSV UTF-8/UTF-8-SIG和XLSX关联导入、HTML中文与终端显示；Windows任务计划环境另行验证。

脱敏关联：下载统一中心模板或config/decision_links.template.csv；link_id/entity_type/entity_id必填，类型port/company/project/factory/route/transport/cost_category，country可选约束；柴油成本类别ID=diesel。仅DEMO使用DEMO-前缀，不能将演示关联送Live。导入会原子替换本空间typed links，必须提供actor/reason并完整审计；既有港口Profile复用，显式typed port links优先。

```powershell
.\.venv\Scripts\python.exe -m scm.platform.cli import-links C:\local\redacted-links.csv --mode manual --actor reviewer --reason initial-context
# 本机增量一次运行；无常驻服务/外发消息
.\.venv\Scripts\python.exe -m scm.platform.cli update --output-dir runtime/platform/updates
# 示例脚本，可由用户自行配置Windows任务计划程序，不会注册任务
powershell.exe -NoProfile -File scripts/run_decision_update.ps1
```

建议任务计划“起始于”仓库根、程序本地PowerShell或.venv解释器。频率由source.frequency_minutes控制，人工单源诊断可随时执行。退出2=任务已完成但至少一来源失败，检查update.json；不循环重试或伪造。许可证据过30日会阻断，需真实重新核实，不把日期随意改新。

自动验收：pytest -q；ruff check src tests scripts。浏览器重放需额外Playwright/Chromium，本轮脚本scripts/phase3_browser_uat.py使用Linux/usr/bin/chromium和localhost8530、已有4条真实燃油数据；Windows浏览器脚本未移植，不冒称能直接运行。不要上传敏感数据/密钥，不公开部署。
