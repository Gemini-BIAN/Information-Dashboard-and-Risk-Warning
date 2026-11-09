# Phase 2A 权限与逐篇日期检查点

2026-11-09（Asia/Shanghai）。仅6候选；详细HTTP/URL/时间/逐篇日期与HTML哈希见 PHASE2_SOURCE_EVIDENCE.json。这里是工程权限审查，不冒称法律专业签核或已入库。

| 候选 | 权限决策 | 实际验证与边界 |
|---|---|---|
| Antwerp-Bruges | unknown | 列表/Disclaimer 200，但仅页面壳，未得到可解释正文条款，不采集正文 |
| Hamburg | allowed_full_text（有条件） | Imprint明确允许存储/分享未改变信息并署名；仅文字，图片排除，原文与分析分开，保留第三方发布主体；3篇各自页面可见日期已核对；现有通用解析失败，需最小专用适配器 |
| MSC | link_only | Terms明确保留权利，复制/下载只允许个人非商业或书面授权；企业用途不满足；不采正文 |
| BASF | link_only | Disclaimer版权条款要求复制/处理/分发书面同意；无授权，不采正文 |
| LG Energy Solution | link_only | 实际Terms of Use只允许个人非商业副本，企业商业复制须授权；不采正文 |
| EC 电池/环境 | allowed_full_text（有条件） | 实际Legal notice核对EU文字CC BY4.0，排除第三方作品/图片/Logo；3篇独立JSON-LD datePublished核对；电池专题页只链接2025-07-04旧新闻，不能作今日新增 |

Hamburg 实际新入口是站内链接 /en/current/news/；旧 /en/press/news/ 不是可用新闻列表。每篇发布时间取标题后可见日历/时钟，站点未注明时区：按 Europe/Berlin 约定并明确质量标记，不当作精确UTC证据。所有日期均来自文章页，不用URL或列表代替。

可重复接入候选仅Hamburg与EC Environment；后者属于已有欧委会同一机构，不能声称新增独立机构。单轮候选核查与站内有效入口跟进，没有绕过跨主机保护或反复尝试受限源。Rotterdam未请求。本检查点尚无新增入库，不计真实采集成功。

许可证据（原文关键条件，保留链接）：Hamburg “The displayed information may be stored and shared, provided it is not altered or distorted in any way. ... the source must be acknowledged.”；EC “reuse is allowed, provided appropriate credit is given and changes are indicated.” 其余来源的未知/限制状态不可由HTTP200覆盖。
