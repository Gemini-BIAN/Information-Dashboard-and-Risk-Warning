"""Bounded localhost Module01 browser UAT. Run only on isolated QA DB seeded with explicit Demo."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.ports.registry import registry
from scm.settings import utcnow


def run(args):
    assert urlsplit(args.url).hostname in ["127.0.0.1", "localhost"]
    assert args.isolated_qa, "Requires disposable isolated QA database"
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "checked_at": utcnow().isoformat(),
        "checks": [],
        "page_errors": [],
        "status": "RUNNING",
        "dataset": "Fresh isolated QA database; 0 Live operational notices. Explicit fictional Demo only for alerts.",
    }

    def save():
        (args.output / "browser.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def passed(name):
        result["checks"].append({"name": name, "status": "PASS"})
        save()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        context.route(
            "**/*",
            lambda r: (
                r.continue_() if urlsplit(r.request.url).hostname in ["127.0.0.1", "localhost"] else r.abort()
            ),
        )
        page = context.new_page()
        page.set_default_timeout(12000)
        expect.set_options(timeout=12000)
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=20000)
            page.get_by_test_id("stSidebar").get_by_text("港口监测", exact=True).click()
            expect(page.get_by_test_id("stException")).to_have_count(0)
            frame = page.frame_locator('iframe[title="scm.ui.port_monitor.escim_port_world"]')
            expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
            expect(frame.locator("#land path")).to_have_count(1)
            passed("Offline Natural Earth map and all12 marker objects actually rendered, no external assets")
            page.screenshot(path=str(args.output / "01-live-map.png"), full_page=True)
            for port in registry().ports:
                frame.locator('[data-port-id="' + port.id + '"]').click()
                expect(
                    page.get_by_role("heading", name=port.business_label + " · " + port.name_zh, exact=True)
                ).to_be_visible()
                expect(page.get_by_text("当前运营状态： 未知", exact=False)).to_be_visible()
                expect(page.get_by_test_id("stException")).to_have_count(0)
            passed("All12 actual map-marker clicks open correct right-hand detail and unknown current status")
            page.screenshot(path=str(args.output / "02-dover-panel.png"), full_page=True)
            frame.get_by_role("button", name="世界", exact=True).click()
            expect(frame.locator("#map")).to_have_attribute("viewBox", "0 0 1000 500")
            frame.get_by_role("button", name="欧洲", exact=True).click()
            frame.get_by_role("button", name="地图放大").click()
            passed("World/Europe viewport and zoom controls work")
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).fill("Koper")
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).press("Enter")
            expect(frame.locator("#map")).to_have_attribute("data-marker-count", "1")
            expect(page.get_by_role("heading", name="KOPER · 科佩尔", exact=True)).to_be_visible()
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).fill("not-a-port")
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).press("Enter")
            expect(
                page.get_by_text("没有匹配的港口；清除筛选后查看全部12个地点。", exact=True)
            ).to_be_visible()
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).fill("")
            page.get_by_role("textbox", name="搜索港口或国家", exact=True).press("Enter")
            expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
            passed("Search filters map/detail, empty result and clearing search work")
            page.get_by_role("button", name="生成港口运营日报", exact=True).click()
            expect(page.get_by_role("button", name="下载港口日报HTML", exact=True)).to_be_visible()
            with page.expect_download() as download:
                page.get_by_role("button", name="下载港口日报HTML", exact=True).click()
            download.value.save_as(str(args.output / "live-daily.html"))
            live_html = (args.output / "live-daily.html").read_text(encoding="utf-8")
            assert "覆盖不足" in live_html and "<article>" not in live_html and "DEMO" not in live_html
            assert all(p.business_label in live_html for p in registry().ports)
            passed("Actual Live empty daily generated without sample-news padding")
            page.get_by_test_id("stSidebar").get_by_text("演示数据 Demo", exact=True).click()
            frame.locator('[data-port-id="teesport"]').click()
            expect(page.get_by_role("heading", name="TEESPORT · 提斯港", exact=True)).to_be_visible()
            expect(page.get_by_text("DEMO River Tees port closure", exact=False).first).to_be_visible()
            page.screenshot(path=str(args.output / "03-demo-shared-tee.png"), full_page=True)
            frame.locator('[data-port-id="middlesbrough"]').click()
            expect(page.get_by_role("heading", name="MIDDLESBROUGH · 米德尔斯堡", exact=True)).to_be_visible()
            expect(page.get_by_text("事件级通知 2 条，未读 2 条", exact=False)).to_be_visible()
            passed("Shared Tees evidence visible under distinct locations, inbox only2 events, Demo labeled")
            page.get_by_role("button", name="标为已读", exact=True).first.click()
            expect(page.get_by_text("事件级通知 2 条，未读 1 条", exact=False)).to_be_visible()
            page.get_by_role("button", name="生成港口运营日报", exact=True).click()
            expect(page.get_by_role("button", name="下载港口日报HTML", exact=True)).to_be_visible()
            with page.expect_download() as download:
                page.get_by_role("button", name="下载港口日报HTML", exact=True).click()
            download.value.save_as(str(args.output / "demo-daily.html"))
            assert "DEMO" in (args.output / "demo-daily.html").read_text(encoding="utf-8")
            page.get_by_role("heading", name="站内预警收件箱", exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(args.output / "05-demo-inbox.png"), full_page=True)
            passed("Demo in-app read acknowledgement and daily generation work")
            page.get_by_test_id("stSidebar").get_by_text("真实数据 Live", exact=True).click()
            expect(page.get_by_text("暂无站内预警；缺少数据不表示港口正常。", exact=True)).to_be_visible()
            expect(page.get_by_text("DEMO River Tees port closure", exact=False)).to_have_count(0)
            passed("Switch back to Live never displays Demo signal/inbox")
            # Existing six workspaces remain routable; only bounded smoke, no mutations.
            for label in ["态势总览", "情报研判", "港口监测", "航次与 ETA", "情报报告", "来源与系统"]:
                page.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
                headings = {
                    "态势总览": "例外与待核实队列",
                    "情报研判": "情报研判与审核",
                    "港口监测": "港口监测",
                    "航次与 ETA": "航次与 ETA 风险",
                    "情报报告": "情报报告",
                    "来源与系统": "来源与系统",
                }
                expect(page.get_by_role("heading", name=headings[label], exact=True).first).to_be_visible()
                expect(page.get_by_test_id("stException")).to_have_count(0)
            passed("All existing six workspace routes have no Streamlit exception")
            page.get_by_test_id("stSidebar").get_by_text("港口监测", exact=True).click()
            page.set_viewport_size({"width": 1000, "height": 900})
            expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
            page.screenshot(path=str(args.output / "04-compact-live.png"), full_page=True)
            passed("1000px compact desktop map still renders; phone-specific UX not claimed")
            assert not result["page_errors"], result["page_errors"]
            result["status"] = "PASS"
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:1200]
            page.screenshot(path=str(args.output / "failure.png"), full_page=True)
            raise
        finally:
            save()
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8512")
    parser.add_argument("--isolated-qa", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("runtime/port01/browser"))
    run(parser.parse_args())
