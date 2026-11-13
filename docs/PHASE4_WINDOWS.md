# Phase 4 Windows local acceptance

Native Windows: **NOT TESTED**. Linux/UTF-8 and existing GBK simulation tests do not establish Windows PASS. No task has been registered.

From PowerShell in the repository (stop old Streamlit/PyCharm process first):

```powershell
git switch feature/escim-intelligence-platform
git pull --ff-only origin feature/escim-intelligence-platform
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m scm.platform.cli init
.\.venv\Scripts\python.exe -m scm.platform.cli collect --source govuk-aesc-finance --source govuk-aesc-capacity --source govuk-aesc-opening --source hapag-ports-rss
.\.venv\Scripts\python.exe -m scm.platform.cli collect --source govuk-aesc-finance --source govuk-aesc-capacity --source govuk-aesc-opening --source hapag-ports-rss
.\.venv\Scripts\python.exe -m scm.platform.cli decisions --mode live
.\.venv\Scripts\python.exe -m scm.platform.cli decision-report --mode live --kind weekly --output runtime/phase4/weekly.html
.\.venv\Scripts\python.exe -m streamlit run src/scm/platform/app.py --server.address 127.0.0.1 --server.port 8503 --browser.gatherUsageStats false
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

Check Live project timeline: 2025-05 financing support → 2025-06 planned15.8GWh/year → 2025-12 opened; not three factories, not today's news. Actual start/date and actual output remain unknown. Unified center uncheck high-value filter for historical/stale claims. Module01 pure map remains12 ports; Rotterdam detail has no confirmed current risk. Check CSV/HTML Chinese text under a Chinese directory and GBK console, both widths, original evidence links and Manual isolation.

Task Scheduler may call existing `scripts/run_decision_update.ps1` using an absolute `-Python` executable. Set **Start in** to repository root and use the current Windows user's context. Example action (manual setup only):

```text
powershell.exe -NoProfile -File C:\path\repo\scripts\run_decision_update.ps1 -Python C:\path\repo\.venv\Scripts\python.exe
```

Do not change execution policy automatically. Run script interactively first; exit2 means partial source failure, read runtime/platform/updates/update.json. No external messages. Only one scheduler instance; overlapping task invocation is not yet coordinated across processes. Rights expire after30 days and then fail closed until reviewed. Background task installation, cross-day endurance, native Windows and real user diesel script integration remain NOT TESTED.
