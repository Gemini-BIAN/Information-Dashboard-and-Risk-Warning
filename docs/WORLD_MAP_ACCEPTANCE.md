# PR8 纯交互式世界地图验收

2026-11-12（Asia/Shanghai）。本报告取代旧版港口一级页的常驻摘要卡设计；四标签详情内容保留。继续feature/escim-intelligence-platform / Draft PR8，不合并main，不修改法规分支/PR7。

## 页面结果

一级内容区仅Leaflet1.9.4交互地图及12个Registry标点，无大标题/指标/统计/新闻/港口下拉/筛选/常驻卡片。初次fitWorld，无默认选港/弹窗；导航与数据空间留在Streamlit侧栏。在线OSM浅色底图有海洋陆地/国界与随级别显示的地名，另加基础洲名。右下角仅小型放大、缩小、世界视图按钮；原生滚轮、拖动、触控缩放。

鼠标点击标点才在点位附近打开Leaflet原生锚定Popup，只有港名/国家、正常/异常/未知、最近有效运营公告或明确没有、核实时间、查看详情和关闭。空白地图/关闭按钮均关闭卡片，不触发详情；只有查看详情发送一次Streamlit事件，进入原概览/公告时间线/来源证据/业务影响四标签。

进入详情时保存Leaflet实际center/zoom；返回按该视角恢复，弹窗关闭，标点坐标不变。从其他工作台重新进入默认世界图，不继承旧详情。通过详情URL直接进入仍保留。地图与详情没有复制数据库、改风险规则/模块02/03业务或新增消息发送。

点位直接使用Registry经纬度，不做屏幕偏移。部分Registry坐标仍为approximate、Tangier范围仍待核实，不能宣称已验证到具体码头导航坐标。世界尺度邻近港口自然重叠；可放大、键盘聚焦和真实点击，验收在放大后逐个鼠标点击了全部12点。

## 地图资源与合法性

LeafletJS/CSS本地随包交付，BSD2许可完整保留；无运行时CDN依赖/付费Key。实际在线浏览器请求 https://tile.openstreetmap.org/{z}/{x}/{y}.png ，©OpenStreetMap contributors署名与版权链接始终在地图角落。使用政策 https://operations.osmfoundation.org/policies/tiles/ 和版权页实际HTTP200，见[资源审计](evidence/world-map/ASSET_AND_POLICY_AUDIT.json)。只按当前交互视口请求/使用浏览器缓存，updateWhenIdle、无缓冲预取；不批量下载或离线保存OSM瓦片。

在线瓦片错误或8秒没有任何瓦片成功时明确提示「在线底图不可用」，切换为本地Natural Earth公共领域GeoJSON的Leaflet矢量层，保留交互、国界/洲名和港口。降级明确无街道细节，不把空白或离线层声称在线成功；离线文件也失败则显示底图不可用。详见src/scm/ui/port_world/ATTRIBUTION.md。离线几何不是静态地图图片或散点图。

测试环境浏览器外网使用继承Cloud代理且localhost保留本地直连；产品没有硬编码Cloud代理/禁用TLS。早期代理误路由loopback只属测试配置。早期关闭世界循环时向瓦片源发出负数/越界x，HTTP400；已使用正常世界循环避免非法瓦片编号，不是绕过访问限制。未请求受限/付费地图服务。

## 实际验收

| 验收 | 结果 | 证据 |
|---|---|---|
| 初次纯地图/12标点/无默认弹窗、无标题下拉指标 | PASS | 两视口实际在线瓦片成功，等待整批可见瓦片完成后截图 |
| 缩放和平移 | PASS | 实际鼠标wheel改变Leaflet zoom，鼠标down/move/up改变地理center；不是仅检查按钮存在 |
| Hamburg锚定卡片 | PASS | 实际鼠标点击，验证卡片位置近标点、未知状态、关闭按钮和空白地图关闭；截图等待卡片完全不透明 |
| 12点全部可点击 | PASS | 放大UI按钮、原生键盘聚焦自动平移至可视范围，再逐点实际鼠标点击和核对对应port_id，非直接调用openPopup或虚构点击 |
| 四标签详情与返回 | PASS | 真实点击查看详情/返回，center差值<0.01度、zoom相同，卡片关闭 |
| 390px触控 | PASS | Chromium触控模式，CDP实际双指touchStart/move/end改变地图zoom，不是直接setZoom |
| 世界按钮 | PASS | 实际点击恢复全球范围，不自动选择或打开卡片 |
| 外部瓦片失败降级 | PASS | 另会话真实拦断瓦片请求，提示可见，Leaflet矢量层>100几何路径，明确offline而非空白成功 |
| 原风险及数据隔离 | PASS | 当前无合格运营证据为未知；原引擎/来源配置/模块02/03业务服务无改动，完整回归覆盖 |
| 原生Windows/真实触屏设备 | NOT TESTED | Chrome390px/CDP不冒称物理设备/Windows实测 |

Chromium155，桌面1440×1000、移动390×844，共14组检查PASS、0pageerrors。机器回执[浏览器JSON](evidence/world-map/browser.json)包含实际瓦片HTTP状态、保存/恢复的视角及逐组结果。脚本scripts/world_map_browser_uat.py没有用map.setView/setZoom伪造操作，只从实际Leaflet实例读取观测值。原port_detail_browser_uat入口委托新验收脚本；综合平台脚本同步新弹窗定位。

完整pytest **258通过**（含Module01、平台、详情及WindowsGBK），ruff src/tests/scripts、node --check内联JS、git diff --check通过。JUnit在runtime/world-map/tests.xml。新增/更新纯地图无默认控件、12详情RPC往返/视角保存、从其他页进入重置的自动回归。最终准确耗时以JUnit/TEST_REPORT最新记录为准。CI链接在PR8实际回执补充，不将本地结果当远程CI。

开发中导航栏/署名控件挡住焦点标点的问题已修复：地图避开导航，原生聚焦自动平移留足控制区边距。Popup淡出时旧DOM短暂保留，浏览器测试明确等待关闭再点下一港。[失败记录](evidence/world-map/iterations.json)保留，不混成PASS。

## 视觉证据与运行

- 默认纯地图：[桌面](evidence/world-map/desktop-default-world.png) / [390px](evidence/world-map/mobile390-default-world.png)
- Hamburg弹窗：[桌面](evidence/world-map/desktop-hamburg-popup.png) / [390px](evidence/world-map/mobile390-hamburg-popup.png)
- 实际缩放拖动后：[桌面](evidence/world-map/desktop-zoomed-panned.png) / [390px](evidence/world-map/mobile390-zoomed-panned.png)
- [明确离线降级](evidence/world-map/mobile390-explicit-offline-fallback.png)

启动仍为python -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true --browser.gatherUsageStats false，选择01港口与物流。Windows更新后停止旧进程再启动。Leaflet资源已包括package-data，无新Python依赖或数据库迁移。

在线瓦片可用性取决于实际浏览器网络；不能承诺全球可达或街道数据最新。地图瓦片不是新增真实运营新闻，本轮未新增采集/改变现有4条情报计数；无有效运营证据不显示正常。保留法规分支8a31da4和PR7，不公开部署、不合并PR。完成后等待用户实际视觉审核，不自动扩大功能。
