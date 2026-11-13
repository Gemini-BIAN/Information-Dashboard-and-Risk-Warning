"""Real local Chromium checks; no external requests, no fixture claims as Live."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.settings import utcnow


def main():
    out = Path("runtime/phase4/browser")
    out.mkdir(parents=True, exist_ok=True)
    result = {"at": utcnow().isoformat(), "checks": [], "page_errors": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        try:
            for width, height in [(1440, 1000), (390, 844)]:
                context = browser.new_context(viewport={"width": width, "height": height})
                context.route(
                    "**/*",
                    lambda r: (
                        r.continue_()
                        if urlsplit(r.request.url).hostname in ["127.0.0.1", "localhost"]
                        else r.abort()
                    ),
                )
                page = context.new_page()
                page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
                page.set_default_timeout(25000)
                page.goto("http://127.0.0.1:8532")
                expect(
                    page.get_by_text("决策支持 · 事实 / 推断 / 业务声明 / 行动分开", exact=True)
                ).to_be_visible()
                page.get_by_text("仅高价值事件", exact=True).click()
                expect(page.get_by_label("仅高价值事件", exact=True)).not_to_be_checked()
                page.wait_for_timeout(1500)  # Wait for Streamlit checkbox rerun before opening card.
                project = page.locator("details").filter(
                    has=page.locator("summary").filter(has_text=re.compile(r"决策 #\d+ · Nissan launches"))
                )
                expect(project).to_have_count(1)
                project.locator(":scope > summary").click()
                expect(project).to_have_attribute("open", "")
                expect(project.get_by_text("同一事件/项目时间线与来源差异", exact=True)).to_be_visible()
                expect(
                    project.get_by_text("无已核实事实；未把采集成功当作业务核实。", exact=True)
                ).to_be_visible()
                project.scroll_into_view_if_needed()
                page.screenshot(path=str(out / f"project-{width}.png"), full_page=True)
                result["checks"].append(f"{width}: real historical project card, timeline, pending review")

                def nav(label):
                    button = page.get_by_test_id("stExpandSidebarButton")
                    if button.is_visible():
                        button.click()
                    page.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
                    if width == 390:
                        close = page.get_by_test_id("stSidebarHeader").get_by_role("button")
                        if close.count() and close.first.is_visible():
                            close.first.click()

                nav("02 海外产能与竞争")
                expect(page.get_by_text("ESCIM 海外供应链情报平台", exact=True)).to_be_visible()
                expect(page.locator('[data-testid="stException"]')).to_have_count(0)
                result["checks"].append(f"{width}: capacity page no exception")
                nav("01 港口与物流")
                # Component title can differ between Streamlit versions; inspect actual frame.
                page.wait_for_timeout(1500)
                frames = [f for f in page.frames if f != page.main_frame]
                world = next(f for f in frames if f.locator("#map").count())
                expect(world.locator("[data-port-id].leaflet-marker-icon")).to_have_count(12)
                expect(world.locator(".leaflet-popup")).to_have_count(0)
                page.screenshot(path=str(out / f"map-{width}.png"), full_page=True)
                result["checks"].append(f"{width}: pure map 12 markers no initial popup")
                nav("日报与周报")
                expect(page.locator('[data-testid="stException"]')).to_have_count(0)
                result["checks"].append(f"{width}: report workspace no exception")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
                result["checks"].append(f"{width}: no page-wide overflow")
                context.close()
            assert not result["page_errors"]
            result["status"] = "PASS"
        finally:
            (out / "browser.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            browser.close()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
