"""Bounded desktop/mobile acceptance over actual local Live data plus explicit Demo/Manual."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.settings import utcnow


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8530")
    parser.add_argument("--output", type=Path, default=Path("runtime/platform/browser"))
    args = parser.parse_args()
    assert urlsplit(args.url).hostname in ["127.0.0.1", "localhost"]
    args.output.mkdir(parents=True, exist_ok=True)
    result = {
        "verified_at": utcnow().isoformat(),
        "status": "RUNNING",
        "checks": [],
        "page_errors": [],
        "viewports": [],
    }

    def save():
        (args.output / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

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
        try:
            for width, height, label in [(1440, 1000, "desktop"), (390, 844, "mobile390")]:
                context = browser.new_context(
                    viewport={"width": width, "height": height}, accept_downloads=True
                )
                context.route(
                    "**/*",
                    lambda r: (
                        r.continue_()
                        if urlsplit(r.request.url).hostname in ["localhost", "127.0.0.1"]
                        else r.abort()
                    ),
                )
                page = context.new_page()
                page.set_default_timeout(12000)
                expect.set_options(timeout=12000)
                page.on("pageerror", lambda error: result["page_errors"].append(str(error)))

                def sidebar():
                    expand = page.get_by_test_id("stExpandSidebarButton")
                    if expand.is_visible():
                        expand.click()

                def close_sidebar():
                    if width == 390:
                        buttons = page.get_by_test_id("stSidebarHeader").get_by_role("button")
                        if buttons.count() and buttons.first.is_visible():
                            buttons.first.click()

                def navigate(name):
                    sidebar()
                    page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                    expect(page.get_by_role("radio", name=name, exact=True)).to_be_checked()
                    close_sidebar()
                    expect(page.get_by_test_id("stException")).to_have_count(0)

                def space(name):
                    sidebar()
                    page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                    expect(page.get_by_role("radio", name=name, exact=True)).to_be_checked()
                    close_sidebar()

                page.goto(args.url, wait_until="domcontentloaded", timeout=20000)
                expect(
                    page.get_by_role("heading", name="ESCIM 海外供应链情报平台", exact=True)
                ).to_be_visible()
                expect(page.get_by_text("匹配情报 4 条", exact=True)).to_be_visible()
                expect(
                    page.get_by_text(
                        "11th chainPORT Annual Meeting at Tanger Med Focuses on Scaling AI in Ports",
                        exact=False,
                    )
                ).to_be_visible()
                with page.expect_download() as downloaded:
                    page.get_by_role("button", name="导出筛选结果 CSV", exact=True).click()
                dest = args.output / f"{label}-live.csv"
                downloaded.value.save_as(str(dest))
                assert "DEMO project" not in dest.read_text(encoding="utf-8-sig")
                passed(label + ": actual four Live records and source-only CSV, no Demo mixing")
                navigate("01 港口与物流")
                frame = page.frame_locator('iframe[title="scm.ui.port_monitor.escim_port_world"]')
                expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
                frame.locator('[data-port-id="dover"]').click()
                expect(page.get_by_role("heading", name="DOVER · 多佛", exact=True)).to_be_visible()
                expect(page.get_by_text("当前运营状态： 未知", exact=False)).to_be_visible()
                page.screenshot(path=str(args.output / f"{label}-ports-live.png"), full_page=True)
                passed(label + ": existing12-port map and real click/detail unknown state retained")
                for name in [
                    "02 海外产能与竞争",
                    "03 物流市场与成本",
                    "日报与周报",
                    "预警收件箱",
                    "Sources 数据源",
                ]:
                    navigate(name)
                    expect(
                        page.get_by_role(
                            "heading",
                            name="Sources 数据源"
                            if name == "Sources 数据源"
                            else "站内预警收件箱"
                            if name == "预警收件箱"
                            else name,
                            exact=True,
                        )
                    ).to_be_visible()
                passed(label + ": all seven workspaces navigable, no application exceptions")
                space("DEMO · 合成测试数据")
                sidebar()
                page.get_by_role("button", name="加载 DEMO 合成数据", exact=True).click()
                close_sidebar()
                navigate("02 海外产能与竞争")
                details = page.locator("details").filter(
                    has=page.get_by_text("DEMO factory announced · unknown · pending", exact=True)
                )
                details.locator("summary").click()
                expect(details.get_by_text("项目时间线（明确项目编号关联）", exact=True)).to_be_visible()
                expect(details.get_by_text("证据版本历史", exact=True)).to_be_visible()
                page.screenshot(path=str(args.output / f"{label}-capacity-demo.png"), full_page=True)
                passed(
                    label
                    + ": synthetic project status/timeline/evidence visible; planned capacity not operating capacity"
                )
                navigate("03 物流市场与成本")
                expect(page.get_by_text("DEMO synthetic fuel observation", exact=False)).to_be_visible()
                market_card = page.locator("details").filter(
                    has=page.get_by_text("DEMO synthetic fuel observation · unknown · pending", exact=True)
                )
                market_card.locator("summary").click()
                expect(
                    market_card.get_by_text(
                        "价格、指数、公告、人工输入和模型估计分别标识；未接入实时价格API。", exact=True
                    )
                ).to_be_visible()
                page.screenshot(path=str(args.output / f"{label}-market-demo.png"), full_page=True)
                passed(label + ": market announcement and fictional manual measurement separated with units")
                navigate("日报与周报")
                page.get_by_role("button", name="生成本空间报告", exact=True).click()
                expect(page.get_by_text("报告已保存", exact=True)).to_be_visible()
                daily = page.locator("details").filter(has=page.get_by_text(re.compile(r"^DEMO · daily ·")))
                daily.locator("summary").click()
                with page.expect_download() as downloaded:
                    daily.get_by_role("button", name="下载HTML", exact=True).click()
                dest = args.output / f"{label}-demo-report.html"
                downloaded.value.save_as(str(dest))
                assert (
                    "DEMO" in dest.read_text()
                    and "DEMO project delayed" in dest.read_text()
                    and "2条关联记录" in dest.read_text()
                )
                passed(label + ": actual Demo report generated/displayed/downloaded as HTML")
                navigate("预警收件箱")
                select = page.get_by_role("combobox", name="处理状态", exact=True).first
                select.click()
                page.get_by_role("option", name="read", exact=True).click()
                page.get_by_role("button", name="更新状态", exact=True).first.click()
                expect(page.get_by_text("read", exact=False).first).to_be_visible()
                passed(label + ": local alert updated to read; no external notification")
                space("MANUAL · 人工输入待核实")
                navigate("统一情报中心")
                expect(page.get_by_text("匹配情报 0 条", exact=True)).to_be_visible()
                space("LIVE · 官方真实采集")
                expect(page.get_by_text("匹配情报 4 条", exact=True)).to_be_visible()
                search = page.get_by_role("textbox", name="搜索标题、原文或企业", exact=True)
                search.fill("no-such-event-UAT")
                search.press("Enter")
                expect(page.get_by_text("匹配情报 0 条", exact=True)).to_be_visible()
                search.fill("")
                search.press("Enter")
                expect(page.get_by_text("匹配情报 4 条", exact=True)).to_be_visible()
                page.screenshot(path=str(args.output / f"{label}-live-center.png"), full_page=True)
                passed(label + ": Manual empty/Live4/Demo isolation, empty search fallback and reset")
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
                assert not overflow, "Page horizontal overflow"
                result["viewports"].append(
                    {"width": width, "height": height, "page_horizontal_overflow": overflow}
                )
                context.close()
            assert not result["page_errors"]
            result["status"] = "PASS"
            save()
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:1000]
            page.screenshot(path=str(args.output / "failure.png"), full_page=True)
            save()
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
