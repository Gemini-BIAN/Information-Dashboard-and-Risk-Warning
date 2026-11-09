# Repository collaboration

Read README.md, PROJECT_STATUS.md, DECISIONS.md, NEXT_TASKS.md, TEST_REPORT.md and KNOWN_LIMITATIONS.md before changing code. Check this repository's Issues and unresolved PR reviews when API access is available; record blocks and keep independent work moving. Use only Gemini-BIAN/Information-Dashboard-and-Risk-Warning for project collaboration.

Use Python 3.12, existing isolated checkout and a feature branch. Do not create a worktree unless explicitly requested. Do not merge main automatically. Validate with `pytest -q` and `ruff check src tests`; update status/docs and push the feature branch, then create/update a PR when authorized and available.

Never present fixtures as live data. Preserve source URLs, original evidence, timestamps, raw/analysis separation, review logs and namespace filters. Keep risk computation independent of the LLM. Unknown or failed data access is not a successful collection; maintain PASS/BLOCKED/NOT TESTED distinctions. Do not bypass robots, TLS, site restrictions or network policy. No company-sensitive data or keys in code, fixtures, logs or commits.

Routine engineering choices are autonomous. Obtain user approval for paid services, company sensitive data use, public deployment, material scope change or irreversible/high-risk actions.
