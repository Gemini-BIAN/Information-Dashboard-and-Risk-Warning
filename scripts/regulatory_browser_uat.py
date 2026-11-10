"""Local empty-library foundation UAT; NOT a real regulatory RAG acceptance."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.settings import utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8522")
    parser.add_argument("--output", type=Path, default=Path("runtime/regulatory/browser"))
    args = parser.parse_args()
    if urlsplit(args.url).hostname not in ["127.0.0.1", "localhost"]:
        raise ValueError("Localhost only")
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "RUNNING",
        "verified_at": utcnow().isoformat(),
        "scope": "Empty-library/input-blocker fallback ONLY",
        "real_downloads": 0,
        "checks": [],
        "page_errors": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        page = browser.new_page(viewport={"width": 1366, "height": 1000})
        page.set_default_timeout(12000)
        page.route(
            "**/*",
            lambda r: (
                r.continue_() if urlsplit(r.request.url).hostname in ["127.0.0.1", "localhost"] else r.abort()
            ),
        )
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
        try:
            page.goto(args.url, wait_until="domcontentloaded")
            expect(
                page.get_by_role("heading", name="ESCIM Module02｜法规资料库与检索基础设施")
            ).to_be_visible()
            expect(page.get_by_text("BLOCKED · 未找到", exact=False)).to_have_count(5)
            expect(page.get_by_test_id("stException")).to_have_count(0)
            result["checks"].append("Five missing inputs and empty real library displayed")
            for q in [
                "Regulation (EU) 2023/1542 Article 7 对碳足迹有什么要求？",
                "REACH 与 CLP 对化学品供应商分别有什么要求？",
                "电解液使用 ISO Tank 在欧洲运输时需要核查哪些危险品规则？",
            ]:
                page.get_by_role("textbox", name="中文问题（知识库为空时只返回证据不足）", exact=True).fill(q)
                page.get_by_role("button", name="检索原文证据", exact=True).click()
                expect(page.get_by_text("证据不足：尚无已下载并解析的法规原文。", exact=True)).to_be_visible()
                expect(page.get_by_test_id("stCode")).to_have_count(0)
                expect(page.get_by_test_id("stException")).to_have_count(0)
            result["checks"].append(
                "All three user questions return insufficient evidence; no fabricated citations or legal conclusions"
            )
            page.screenshot(path=str(args.output / "missing-inputs-empty-library.png"), full_page=True)
            assert not result["page_errors"]
            result["status"] = "PASS"
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:600]
            page.screenshot(path=str(args.output / "failure.png"), full_page=True)
            raise
        finally:
            (args.output / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            browser.close()


if __name__ == "__main__":
    main()
