# ESCIM Phase 4 — Execution handoff (cloud runner unavailable)

Date: 2026-11-13. This handoff was prepared from GitHub repository files at Phase 3 commit `8ede177808089620dbc2e4b34dabbf1c5aa8ede9` after the Codex runner returned "No usable execution environment is available". It is **not** an executed Phase 4 or a claim of completed tests.

## Verified baseline
- Draft PR #8: `feature/escim-intelligence-platform` → `feature/supply-chain-risk-mvp`; head `8ede177808089620dbc2e4b34dabbf1c5aa8ede9` before adding this handoff.
- Phase 3 existing engineering: event/evidence model, decision cards, audit, reports, incremental CLI. Phase 3 acceptance: 281 pytest and 10 browser checks (historical, not re-run here).
- Live baseline at Phase 3: 0 qualifying current port operational events; 0 verified company/factory projects; 4 public fuel observations from a single EC XLSX workbook. Background news is not qualifying operations evidence.
- Independent user-authored global diesel scraper already exists; **do not rebuild it**.

## Critical corrected source permissions

**Do not automatically retrieve/retain Rotterdam Port Information Notices or Rotterdam official news under the current permissions.** The existing `docs/phase3/SOURCE_MATRIX.json` marks:
- `port01-rotterdam-restricted` (`https://pin.portofrotterdam.com/`): `permission=blocked`, `access_method=disabled`, zero attempts.
- `candidate-rotterdam`: `permission=prohibited`, catalog only.
Public discoverability does not grant automated reuse. Treat a fresh written authorization, an explicitly offered API, or a separately verified permissively licensed feed as a prerequisite for LIVE automated use. Otherwise provide official links and a **user-directed, rights-compliant** manual metadata/summary import workflow without scraping or rehosting protected content. A successful mock parser must not count as LIVE coverage.

Other candidate sources currently disabled: `catl`, `maersk`, `candidate-hapag` and additional candidate ports. Never flip `enabled` or `automatic_access_allowed` without documented authority and tests.

## Execution plan, ordered by business value

### P0. Existing baseline / permissions / regression
1. Start by reading `docs/PHASE3_ACCEPTANCE.md`, `docs/phase3/SOURCE_MATRIX.json`, `config/platform_sources.json`, `src/scm/platform/decision.py`, `src/scm/platform/cli.py` and current tests.
2. Confirm current branch, state and migration 005. Keep existing pure-world-map behavior, evidence isolation, risk rules and frozen regulatory PR #7 unchanged. No merge.
3. Establish permitted source inventory and document actual license/request evidence. Fail closed on unknown rights.

### P1. Port operational event lifecycle (build even if LIVE unavailable)
- Add or verify typed lifecycle state: scheduled/active/resolved/cancelled/expired/unknown, event time vs publication/fetch time, event identifier, official notice revision, geographic scope (port vs terminal/channel), confidence and status changes.
- Prevent a notice of restoration or cancellation from being interpreted as an independent active disruption. Preserve complete original evidence and historical versions.
- For forbidden/unapproved Rotterdam pages, use clearly synthetic fixtures for unit and browser tests; enable rights-compliant manual link/meta import when user provides a permitted item. No direct unapproved HTTP.
- Prove 12 original port map markers and detail flow remain unchanged. If Rotterdam absent from registry, do not silently change the map; record it as separate registry review.

### P2. Company/factory project intelligence
- Develop multi-source project identity resolution on explicit company + facility + location + product + project ID evidence (not name similarity alone).
- Distinguish announced / approved / construction / trial production / commissioned / operating / delayed / cancelled, and separate `planned_capacity` vs `actual_operating_capacity`, preserving units (GWh or tonnes/year).
- Source material must have provenance, dates, rights and structured field quotations. Plan/actual and site identity conflicts become review tasks, not silent overwrites.
- Candidate companies: CATL, LG Energy Solution, Samsung SDI, SK On, Panasonic Energy, Envision AESC and electrolyte/material makers. First source should be verifiably reusable company-government/IR feeds or explicitly licensed documents; if none, use approved manual imports and report LIVE zero rather than fabricate.
- Deliver an end-to-end project history, decision card and report using separate DEMO fixtures; independent real sources counted only if actually acquired under permission.

### P3. Existing diesel code integration, without duplication
- User's separate diesel scraper may not be available in this repository. Search accessible project repositories for the existing script; if inaccessible report precisely.
- Build a narrow CSV/JSON import contract with provenance: `source_id, country_iso, observed_date, fuel_type, value, currency, unit, fetched_at, method`. Include optional raw-document hash.
- Idempotent import and duplicate keys need the source + country + date + product + unit, with explicit treatment of revisions/corrections.
- Do not silently merge EC Weekly Oil Bulletin and existing scraper rows if they describe the same underlying EU bulletin. Preserve actual publisher separately from the scraper tool.
- Price trends or percent changes only for comparable observations with real historical series.

### P4. Decision quality & scheduling
- Operational event + business context -> evidenced `impact=unknown|potential_unconfirmed` and verification steps. No fake delay/cost estimates.
- Project changes -> planned vs actual change, declared product and capacity context, tracked contradictions, follow-up tasks.
- Produce daily/weekly decision reports with source timestamp, validity, duplicates and open questions.
- Local scheduled-task-ready Windows script: no system task installation, no external notifications, no repeated writes when source unchanged. Observe existing `scm.platform.cli update`.
- Isolate source HTTP failures; fail closed and preserve last verified snapshot with explicit staleness.

## Minimal acceptance gate
- Full existing pytest, Ruff, migration forward/backward, and static checks PASS; 12-port map and deep link unchanged.
- Port lifecycle: publish/update/resolution/retraction/expiry tested; same event not double-counted; no event -> UNKNOWN.
- Factory identity and staged project updates, plan-vs-operating capacity, units, duplicate detection.
- Existing diesel import adapter tested on synthetic non-secret files; same-source data not double counted.
- Source permissions audit: no automatic requests to blocked/unknown sources. Record each actual HTTP request and source rights.
- Separate counts for LIVE facts, DEMO fixtures, manually reviewed data, background news and inactive items.
- Browser tests desktop and 390px for decision details/reports; Windows-native tests explicitly NOT TESTED until executed.
- Never represent a mock event as a real 2026 event. Preserve real URL, revision evidence, original publication/effective time, uncertainty and human-review state.

## Developer instructions when execution becomes available
1. Fetch current PR #8 head and read this handoff. Reconcile any newer commits before editing.
2. Implement P1 and P2 independently wherever permissions block live acquisition. P3 only reuses the user's existing program; do not write a second diesel crawler. Complete P4 with existing CLI.
3. Run tests and browser checks, fix regressions, commit to the current feature branch, retain PR #8 as Draft, do not merge main, do not touch frozen regulatory PR #7.
4. Deliver `PHASE4_ACCEPTANCE.md` plus real-source audit, source-specific counts, test logs, Windows-local verification and final SHA.

### Current status
Phase 4 ENGINEERING: BLOCKED in Codex cloud runner. This handoff is planning/evidence only; no Phase 4 collection, code execution or browser testing has been performed by this handoff.
