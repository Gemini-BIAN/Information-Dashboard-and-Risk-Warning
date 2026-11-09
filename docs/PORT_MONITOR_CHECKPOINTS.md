# Module 01 checkpoints

2026-11-09, Asia/Shanghai. Authoritative Issue6 revision6735021252; London replaced by Dover.

## Checkpoint 1

12 configurable distinct business locations; city/port-area approximate coordinates, no unverified UN/LOCODE. Teesport/Middlesbrough remain separate, Tangier mapping explicitly uncertain. Offline public-domain Natural Earth map with clickable markers + right detail panel, keyboard/select fallback, country/search filter, risk and coverage separated. No map/CDN/API call. Empty evidence = unknown; last fetch != publication. Existing three-port tools retained explicitly as separate historical/manual tools.

Tests: registry invariants and all-12 Streamlit AppTest transitions; source/event integration in later checkpoints. Browser rendering separately checkpoint4, not inferred from AppTest. No current live operational coverage claimed.

## Checkpoint 2

Bounded actual HTTP audit of Le Havre, PD Ports and HPA: no source clears automatic-use/reuse gate. Le Havre two listing timeouts; PD no affirmative reuse permission; HPA explicitly requires prior written consent. No live connector enabled, no operational body/PDF collected, real operational records=0. Source-specific timestamps and HTTP/robots/errors committed in PORT_SOURCE_AUDIT.json; registry coverage remains unverified/restricted, not working_verified. Rotterdam/PIN untouched. This checkpoint is PARTIAL for business collection, PASS for fail-closed permission gate; no synthetic Live substitution.

## Checkpoint 3

Additive migration003 preserves existing tables and evidence; PortSignal identity=(source,numbered notice,namespace), PortAlert unique per substantive version. Shared River Tees scope is one signal/alert, two business locations. Dual axes, explicit current evidence, stale/resolved/normal protections, source-gated RSS-text adapter (all real candidates disabled), opt-in Demo, optional LLM evidence validation/fallback, in-app unread/read inbox and port_daily HTML reports implemented. No external notifications or numeric vessel/ETA metrics.

Actual regression: 201 passed in13.13s; ruff src/tests/scripts + migration003 passed. All-12 Streamlit transitions pass. Closure, future interval, old/current evidence, resolved/cancelled notices, false aliases, blank sailing/omission, permission expiry/zero requests, source isolation, duplicate ingestion/alerts, escalation/resolution, AI failure/ungrounded quotes, Demo/Live and additive migration tested. These are synthetic tests, not Live operational data.

Isolated QA actual run: permission-gated collect attempted no network request for any configured unapproved source; 12 Live unknown, 0 operational notices/alerts. Live empty daily HTML generated. Explicit Demo seed gives2 signals/2 notifications (Tees shared + Dover planned), never copied toLive. Browser checkpoint4 follows.
