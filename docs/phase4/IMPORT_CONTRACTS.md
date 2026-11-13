# Phase 4 local imports and entity semantics

## User's existing diesel tool

Searched accessible `/workspace` files for diesel/fuel names; found only this repository's existing EC workbook adapter. No independent user script was read. **No new diesel crawler was developed.** Integration needs only: accessible output path or repository, one non-sensitive CSV/JSON sample, actual publisher identifiers/aliases, currency/unit/tax basis, and date/timezone meaning. Do not provide credentials, customer prices or internal orders.

`python -m scm.platform.cli import-diesel path/to/output.json --actor operator --reason "reuse existing collector output"`

Accept a JSON array or UTF-8/BOM CSV with these exact columns:

```text
origin_source_id,source_url,country,observed_date,fuel_type,value,currency,unit,fetched_at,method
```

Use publisher ID, **not tool name**, e.g. `ec-weekly-fuel` for underlying Weekly Oil Bulletin. Aliases from another tool must be mapped to that ID before import. country ISO alpha2 or supported alias; currency EUR/USD/GBP/CNY/JPY; diesel only; value finite positive; date ISO day; fetched_at timezone-aware; source_url public HTTPS. Current normalized diesel unit: EUR/litre; EUR/1000l explicitly divided1000. Other units accepted only if already supported by Record; unsupported currencies/unit combinations fail, no FX or guessed tax conversions. Tax-inclusive and tax-exclusive series must have distinct canonical publisher-series IDs; never compare them together.

All imported results remain **Manual**, even if an external tool fetched them. Entire batch validates before any write. Key: original publisher-series + country + observation day + currency + unit + diesel. Same-source same-value already in Live or Manual skips. Conflicting incoming value is retained in audit and never overwrites official observations; review required. The caller's `method`, input original units/value and fetched timestamp remain in immutable JSON body. History remains separate by source, country, currency and unit. Weekly change requires an exact7-day comparable observation; missing baseline yields null. Absolute weekly move >20% is only a review flag, not a claim of bad data. No volatility figure is produced from insufficient history.

## Rotterdam / other user-authored notice metadata

`python -m scm.platform.cli import-notice-metadata local.json --actor operator --reason "read official notice and authored summary"`

Input is a JSON array. Each row supplies `rights_basis: "user_authored_summary"`, `summary` (your own words, not copied restricted body), `external_id` (notice ID), `title`, `url` (official link), optional original `published_at`, `operational_event_id` (same stable ID for activation/restoration of **one occurrence**), `operational_status`, `event_scope`, timezone-aware `status_at`, optional `effective_at`/`expires_at`, `country`, `transport`, and `field_evidence: {"operational_status": "literal supporting text from your own summary"}`. No automatic HTTP, no rights assertion from URL visibility, no Live promotion. This tool cannot determine whether an operator actually authored a summary; responsibility remains with the operator. Do not import company-sensitive content.

Statuses: scheduled / active / resolved / cancelled / expired / unknown. Scope: port / terminal / channel / route / carrier_service. Activate/Deactivate are two notices linked to one explicit event occurrence; repeated restrictions need new occurrence IDs, not a global evergreen title. Same stable ID with different scopes stays separate. Latest status_at controls, capture order does not; same-time contradictory status becomes unknown. Future status cannot overwrite current; expiration overrides active; active older than24hours becomes unknown even if “until further notice”. Restoration does not establish all-port normal. Rejected current revisions do not control current state. Events are conservative evidence-only in platform Module01 detail; Manual does not alter the original verified operational map state.

## Projects and rollback

company_id uses configured exact aliases; project_id/factory_id are curated explicit identity, not headline similarity. Country/location/product/factory conflict retains all source claims. Same-date contradictory stage/capacity becomes review conflict. Different dates form timeline, **not automatic numeric growth**. Planned/nameplate/actual_operating/unknown capacity basis is explicit. GWh/year, MWh/year and tonnes/year are never summed. Exact actual_start needs dated field evidence; publication date and opening announcement do not fill it. An “opened” facility is not automatically full production.

No new SQL migration: existing immutable Evidence.raw_json and audited projections are reused; 005 remains head. JSON fields are additive and existing default-only records retain old fingerprints. CSV/XLSX `field_evidence` must be a JSON object serialized in one cell (`{}` when empty); JSON import uses an object.

Before importing new fields into an existing installation, stop the app and use SQLite backup (Python sqlite3.Connection.backup) to a local protected file. To roll back application code, restore that backup as well: older strict Record contracts do not understand newly populated fields. Do not delete evidence or restore a database under a running process. Acceptance tests downgrade/upgrade005 in an isolated temporary DB only; original business/regulatory databases are untouched. Actual production backup recovery and native Windows rollback remain NOT TESTED.
