# PR8 Windows GBK 默认编码修复验收

2026-11-11（Asia/Shanghai）。用户已报告Windows/PyCharm可以启动，但港口配置读取报GBK UnicodeDecodeError。本轮在feature/escim-intelligence-platform修复，不修改法规分支或合并main。

## 修改范围

14个已有Python文件、35处此前隐式编码的Path.read_text/write_text调用统一指定UTF-8；新增tests/test_text_encoding.py。

- 运行代码：src/scm/ports/registry.py（ports.json及port_sources.json两处）、src/scm/platform/demo.py（DEMO JSON）。
- 脚本：audit_content_sources.py、run_phase2a.py、validate_phase2a.py、validate_platform_live.py、validate_platform_artifacts.py、platform_browser_uat.py、port_browser_uat.py。
- 原测试：test_content_contracts.py、test_core.py、test_official_parsers.py、test_ui.py、test_ui_v2.py。

审计覆盖所有Git跟踪的Python文件，并检查文本open、文件日志与序列化调用。JSON/CSV/Markdown/HTML/TOML配置和报告已明确UTF-8；原有UTF-8-SIG CSV入口保留。StringIO/内存JSON无需文件编码；str.encode/decode默认UTF-8不依赖Windows代码页。二进制read_bytes/write_bytes、CAS/PDF/XLSX及临时二进制写入不变，HTTP响应按第三方声明的解码逻辑不变。没有强制修改全局locale/PYTHONUTF8或用errors=ignore掩盖坏字节。

## 测试结果

PASS：254 pytest passed in16.56s，0失败/跳过，包含原Module01测试；ruff check src tests scripts migrations/versions/004_intelligence_platform.py及git diff --check通过。JUnit：runtime/platform/windows-encoding-tests.xml。

新增3项：

1. io.open文本默认/locale编码模拟为GBK，读取真实ports.json确实抛UnicodeDecodeError（负对照），修复后12港和多佛中文名、来源配置均正常读取。
2. GBK默认下DEMO真实项目配置读取、5条合成记录入库、Live隔离、日报/周报生成及中文/欧元符号/箭头的UTF-8文件往返通过；JSON/CSV/MD/HTML文本均检查实际字节。
3. AST检查src/scripts/tests/migrations及docs/ui_uat中的Path文本读取/写出必须指定编码，避免后续重新引入隐式locale。

这是Linux/Python3.12下的GBK默认I/O模拟，不能写成原生Windows PASS。完整自动回归验证原Module01风险、地图/页面和通知功能；本轮未重新采集真实新闻或重复桌面/移动浏览器全套验收，之前证据保持历史日期，不冒称本次新结果。法规分支仍8a31da45cf03be67f52c83737b31fc1f0ac8cc10，PR7未修改。

## Windows仍需人工复验

拉取PR8分支最新提交后，彻底停止旧Streamlit/PyCharm运行进程再启动（避免旧Python导入缓存），不必把系统默认编码改成UTF-8作为前提。

- 在原GBK环境重新进入港口页，确认12地点地图和详情切换、多佛中文与来源信息无UnicodeDecodeError。
- DEMO加载、企业/市场页、Sources配置、日报周报生成/下载；用编辑器按UTF-8打开HTML/JSON，确认中文与符号完整。
- UTF-8及带BOM的CSV导入、Excel导入、CSV导出，以及含中文路径的工作目录。
- PyCharm/PowerShell终端中文输出与实际浏览器交互；本轮只修复文件I/O，不承诺所有终端代码页显示。

原生Windows修复后运行、中文路径和上述人工操作：NOT TESTED。CI结果与最终SHA以PR8实际回执为准。不进行公网部署、无付费API、无敏感数据。
