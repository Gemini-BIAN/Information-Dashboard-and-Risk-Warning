# 情报数据标准 V1

第一阶段独立 Pydantic 契约：`src/scm/content/contracts.py`。机器 JSON Schema：`docs/schemas/intelligence.v1.schema.json` 与 `source_registry.v1.schema.json`；版本 1.0.0，禁止额外字段。未迁移现有数据库，不宣称现有页面已经使用本标准。

| 字段组 | 标准 |
|---|---|
| 身份/来源 | record_id、source_id/name/type、organization_id、canonical_url、original_title/title_zh |
| 许可 | permitted_method、license_name、reuse_audit_ref；link_only 不得存原文摘录；候选许可未知不视为授权 |
| 时间 | source_published_at、event_occurred_at、fetched_at、last_verified_at；适用范围中 effective/expiry/repeal_at；时区必填，未知 null，精度单列 |
| 分类 | primary_domain、secondary_tags、event_kind；建设 priority 与领域匹配，severity 独立且须理由 |
| 地理/主体 | countries、ports、routes、entities、products；generic_assets 只允许公开通用对象，candidate_unverified 不等于确定运输关联 |
| 法规 | applicability 的法标识、辖区、纳入/排除产品、电解液 direct/indirect/not_applicable/unknown、状态及证据，不能由日期推导 |
| 相关性 | business_relevance 四态、原因码、中文理由、明确供应链关联与评估时间 |
| 证据 | evidence_snippets 的 ID、URL、短引用、locator、raw_revision_id/sha256、capture_mode；事实与分析引用必须存在 |
| 分析 | factual_summary_zh 独立于 hypotheses/potential_impacts；后两者强制 hypothesis；行动含验证问题 |
| 运营 | lifecycle、operational_state、confidence、review_status、currentness_checked_at 互相独立；当前已确认中断需 A 类、active、人工确认、当期核查和证据 |
| 质量/更新 | status、dedup_key、update_version、previous_record_ref、quality_flags；具体规范化去重/更新策略待第二阶段接入 |
| 隔离 | data_mode live/demo/fixture 必须与全部证据 capture_mode 相同；未知日期、翻译、时效不补造 |

Pydantic 跨字段校验是运行时契约；JSON Schema 供结构交换，不涵盖全部业务校验。无 LLM 仍能验证结构，但不能等同于语义事实核验；契约不会自行翻译、抓取、分类或计算风险。原始信息与分析层继续分开；本阶段没有新建原始正文库。
