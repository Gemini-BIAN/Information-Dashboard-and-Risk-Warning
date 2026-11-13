# ESCIM Phase 4 acceptance

2026-11-13 (Asia/Shanghai). Branch feature/escim-intelligence-platform; Draft PR8 retained; no main merge and no PR7/regulatory changes. Started from remote3deb8b2 (Phase4 handoff), whose parent is supplied baseline8ede177.

## Actual business coverage (separate from fixtures)

| Coverage added this round | Count | Meaning |
|---|---:|---|
| Rotterdam official automated operational events | 0 | Rights BLOCKED; original notice bodies not fetched |
| Confirmed current port disruptions, original12-port registry | 0 | All12 remain unknown; no events is not normal |
| Real carrier operational notice identities | 2 | Hapag official RSS: Valencia acceptance restriction and London Gateway rail suspension; older than24h, continuing state **unknown**, not current-confirmed risk |
| Current-confirmed carrier disruptions | 0 | No later corroboration; do not project ongoing disruption |
| Real enterprise/factory projects | 1 | AESC Sunderland Plant2, linked from3 official government historical documents; not3 factories, not today's new project |
| New diesel observations | 0 | Independent user's collector not available; not redeveloped |
| Remaining feed records | 8 | Retained background only; not counted as new qualifying business events |
| DEMO/Manual included in above counts | 0 | Synthetic tests and manual import tests excluded |

Phase3's4 diesel observations and4 older background articles were **not present in this fresh checkout's runtime database**. They are historical reported baseline, not re-created or added to this round's13 Live items. Five real source collection passes: first13inserted; later typed-field revisions on2 notices; final13unchanged,0new. Raw permitted response bytes stay local ignored CAS. Actual HTTP dates, bytes/SHA, robots, per-source failures, original links, counts and final reparse/DB agreement: [LIVE_ACCEPTANCE.json](phase4/LIVE_ACCEPTANCE.json). No raw restricted content committed.

## Delivered behavior

- Explicit scoped operational event occurrence ID/status timestamp links Activate/Deactivate notices; one representative card per entity, immutable notice/version history, cancellation/expiry/restoration/staleness rules, simultaneous contradictory status fails to unknown. Multiple evidence can support one ID; no fuzzy automatic merging. Module01 detail receives evidence metadata/status; original authoritative map stays conservative. Rotterdam already existed; registry and map files unchanged.
- Project register/time histories reuse Evidence and current item revisions; exact company aliases produce stable company_id, curated project/factory identity, country/product/location, planned/nameplate/actual capacity basis, independent planned and actual dates. Same-time stage/capacity or facility-location conflicts remain visible, never summed or silently overwritten. Full trial-production and plan/actual regressions are synthetic tests, not live company observations.
- Real project closed loop: 2025-05-09 government financing support → 2025-06-02 UKEF planned15.8GWh/year → 2025-12-16 government says facility opened. Actual output, exact actual_start and full-production state remain unknown. December article only says15.8GWh; it is not silently converted to actual annual output. Source field quotes must still match on subsequent fetch or adapter fails for review.
- Unified decision card separates source claim, structured source values, rule inference, configured business links, unknown impact, candidate actions and human attestation. Historical AESC card is visible with high-value filter off; latest representative includes all3 evidence links and planned-capacity history. It recommends checking product/project status and later official notices, not purchasing or estimating demand. No user context provided, so impact unknown. Weekly report includes an explicitly historical project register, not an invented current alert.
- RSS-only Hapag adapter never fetches article links; permission is restricted to the exact subscribed feed/adapter. Valencia's source announcement concerns export acceptance windows, not proven company delay days. No surcharge amounts inferred; no ordinary announcement treated as actual freight. Maersk and restricted company/port sources remain disabled.
- User-authored summary/link workflow always Manual with actor/reason/rights basis audit. It cannot validate that a user actually authored their summary; no copied restricted text is authorized. Full Rotterdam lifecycle acceptance uses explicitly synthetic DEMO tests; **no official Rotterdam sample or manual official event was ingested**.
- Diesel CSV/JSON output importer makes no network requests, requires publisher-series identity/date/unit/currency/provenance, validates atomically, retains history and conflicts, skips same-source official values across Live/Manual, computes week change only with exact7-day baseline. Currency/tax/unit aliases need configuration by operator; no guessed FX, tax basis or volatility. See [import contracts](phase4/IMPORT_CONTRACTS.md).
- Bounded update command supports selected sources, due checks, failure isolation, decision/report refresh and per-run UTF-8 JSON logs. Three actual repeated updates of the4 selected source configs had no due HTTP calls, all13cards unchanged, no event/evidence growth; this proves immediate idempotence, not cross-day endurance. Existing Windows script does not install tasks or send messages.

## Validation

- Full Python3.12 pytest: **296 passed in21.63s**,0failed/0skipped. Original281 included. Existing CSV/XLSX test fixture serializes newly nested field_evidence as JSON in one cell; no assertion removed. Declared openpyxl/pypdf dependencies were initially missing in runner; installed from lock before final execution. Earlier missing-dependency/2flat-format failures corrected, not reported as passes.
- Ruff src/tests/scripts PASS; pip check PASS; diff check PASS.
- New regressions cover one-event restoration, cancellation/expiry/unknown, stale/conflicting status, Manual isolation/atomic validation, project histories/trial stage/unit/location conflicts, exact dated actual evidence, diesel same-publisher duplicate/conflict/historical missing-week handling, RSS no-follow/test-client DEMO and feed permission cannot enable HTML.
- Existing pure-map/12port/GBK/UI tests all pass. No registry/map renderer changes.
- No schema006 needed: additive JSON evidence fields and read projections use existing005. Actual temporary SQLite005→004→005 PASS; [migration record](phase4/MIGRATION_ACCEPTANCE.json). Production rollback requires pre-import backup plus matching application revision because old strict schema cannot read populated new JSON fields. No production restore claimed.
- Browser results and exact-head GitHub CI receipt appended below after actual verification. Native Windows **NOT TESTED**. Steps: [PHASE4_WINDOWS.md](PHASE4_WINDOWS.md).

## Remaining blockers and limits

Rotterdam automated rights and API guest authorization; Maersk/other company website reuse; independent diesel script/sample output; current business associations; current operational corroboration; actual factory production/date; native Windows/task-scheduler endurance and production backup restoration. AESC ingest is3 known historical document monitors, not comprehensive new-project discovery. No company-private data, paid services, account registration, external messages, public deployment, task installation or main merge.

**ENGINEERING PASS / DEMO PASS / LIVE PARTIAL / WINDOWS NOT TESTED**. LIVE PARTIAL refers to acquired official project history and subscribed carrier claims; it does not assert real-time port disruption coverage.

## Final browser receipt

Chromium155.0.8059.79, fresh Streamlit process port8532: **10 checks PASS**, desktop1440×1000 +390×844,0pageerrors, no page-wide overflow. Real historical project card and unverified fact label/timeline, Module02, pure map12registered markers/no default popup, report workspace. External requests blocked for this run; map offline fallback is intentional, not an online-tile claim. Source links/raw contents were independently verified by HTTP/reparse script. This round does not repeat Phase3's full zoom/drag/touch or all12-click interaction suite; original automated tests remain passing. Browser script: `python scripts/phase4_browser_uat.py` after starting app on8532 with acceptance DB.

[Machine receipt](evidence/phase4/browser.json), [desktop project](evidence/phase4/project-1440.png), [390 project](evidence/phase4/project-390.png), [desktop map](evidence/phase4/map-1440.png), [390 map](evidence/phase4/map-390.png), [earlier failed development iterations and fixes](evidence/phase4/ITERATIONS.json). Native checkbox/summary/marker locator errors and a stale-process ImportError were recorded and corrected; final checks use a new process, not hidden exceptions.

CLI Chinese-path/GBK-output subprocess simulation PASS: [encoding record](phase4/ENCODING_ACCEPTANCE.json). Native Windows remains NOT TESTED.
