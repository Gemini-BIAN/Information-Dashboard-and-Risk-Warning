"""Actual local UI verification over the downloaded official law. No fixtures/seeding."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

from scm.settings import utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8522")
    parser.add_argument("--output", type=Path, default=Path("runtime/regulatory/live/browser-first"))
    args = parser.parse_args()
    assert urlsplit(args.url).hostname in ["127.0.0.1", "localhost"]
    args.output.mkdir(parents=True, exist_ok=True)
    expected = "e9745513fabe68c8c15cc9f487c4d13da81d40394712f3e0b4c2588b3238d09a"
    result = {
        "verified_at": utcnow().isoformat(),
        "status": "RUNNING",
        "checks": [],
        "page_errors": [],
        "dataset": "Actual EUR-Lex CELEX32023R1542 OJ original PDF; no mock corpus",
    }

    def passed(name):
        result["checks"].append({"name": name, "status": "PASS"})
        (args.output / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(15000)
        page.route(
            "**/*",
            lambda r: (
                r.continue_() if urlsplit(r.request.url).hostname in ["127.0.0.1", "localhost"] else r.abort()
            ),
        )
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
        try:
            page.goto(args.url, wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="ESCIM Module02｜法规资料库与原文检索")).to_be_visible()
            expect(
                page.get_by_text(
                    "下载：downloaded；解析：needs_review；法律效力/适用日期：待核实", exact=True
                )
            ).to_be_visible()
            expect(page.get_by_text("SHA256：" + expected, exact=False)).to_be_visible()
            passed("Actual battery original downloaded status/SHA displayed with legal status pending")
            with page.expect_download() as d:
                page.get_by_role("button", name="打开/下载已校验原文", exact=True).click()
            pdf = args.output / "opened-official-original.pdf"
            d.value.save_as(str(pdf))
            assert hashlib.sha256(pdf.read_bytes()).hexdigest() == expected
            reader = PdfReader(pdf)
            assert len(reader.pages) == 117
            assert "REGULATION (EU) 2023/1542" in reader.pages[0].extract_text()
            assert "Carbon footprint of electric vehicle batteries" in reader.pages[30].extract_text()
            assert "RESTRICTION ON SUBSTANCES" in reader.pages[83].extract_text()
            passed(
                "Browser-downloaded actual source re-opened: hash,117 pages,regulation identity,Article7 p31 andAnnexI p84 match"
            )
            page.get_by_role("textbox", name="中文问题", exact=True).fill(
                "Regulation (EU) 2023/1542 Article 7 对碳足迹有什么要求？"
            )
            page.get_by_role("button", name="检索原文证据", exact=True).click()
            expect(page.get_by_test_id("stCode").first).to_contain_text("Article 7")
            expect(page.get_by_test_id("stCode").first).to_contain_text(
                "carbon footprint declaration shall be drawn up"
            )
            expect(page.get_by_role("link", name="打开引用原文页", exact=True).first).to_have_attribute(
                "href", __import__("re").compile(r"^https://eur-lex.europa.eu/.*#page=31$")
            )
            page.screenshot(path=str(args.output / "article7-query.png"), full_page=True)
            passed("Chinese Article7 query gives actual English clause and official PDF page31 citation")
            page.get_by_role("textbox", name="中文问题", exact=True).fill("Annex I 附件 I 限制物质有哪些？")
            page.get_by_role("button", name="检索原文证据", exact=True).click()
            expect(page.get_by_test_id("stCode").first).to_contain_text("RESTRICTION ON SUBSTANCES")
            expect(page.get_by_test_id("stCode").first).to_contain_text("Mercury")
            expect(page.get_by_role("link", name="打开引用原文页", exact=True).first).to_have_attribute(
                "href", __import__("re").compile("#page=84$")
            )
            page.screenshot(path=str(args.output / "annex1-query.png"), full_page=True)
            passed("AnnexI actual restriction text/correct PDF page84; table flagged review")
            # Same law, explicitly declared but not downloaded consolidated version.
            selector = page.get_by_role("combobox", name="选择法规与精确版本", exact=True)
            selector.click()
            page.get_by_role(
                "option", name="Regulation (EU) 2023/1542 | consolidated | 2026-08-13 | pdf", exact=True
            ).click()
            expect(page.get_by_text("下载：not_downloaded", exact=False)).to_be_visible()
            page.get_by_role("textbox", name="中文问题", exact=True).fill("Article 7 碳足迹")
            page.get_by_role("button", name="检索原文证据", exact=True).click()
            expect(page.get_by_text("证据不足：知识库未覆盖", exact=False)).to_be_visible()
            expect(page.get_by_test_id("stCode")).to_have_count(0)
            passed("Consolidated candidate never borrows original-version chunks or download status")
            selector.click()
            page.get_by_role(
                "option", name="Regulation (EU) 2023/1542 | official | 2023-07-28 | pdf", exact=True
            ).click()
            for q in [
                "REACH 与 CLP 分别有什么要求？",
                "ISO Tank 在欧洲运输需要什么危险品规则？",
                "目前 Article 7 碳足迹适用要求？",
            ]:
                page.get_by_role("textbox", name="中文问题", exact=True).fill(q)
                page.get_by_role("button", name="检索原文证据", exact=True).click()
                expect(page.get_by_text("证据不足", exact=False).last).to_be_visible()
                expect(page.get_by_test_id("stCode")).to_have_count(0)
            passed(
                "Uncovered other-law/ISO tank/current-applicability questions refuse unsupported conclusions"
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)
            assert not result["page_errors"]
            result["status"] = "PASS"
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:1200]
            page.screenshot(path=str(args.output / "failure.png"), full_page=True)
            raise
        finally:
            (args.output / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
            browser.close()


if __name__ == "__main__":
    main()
