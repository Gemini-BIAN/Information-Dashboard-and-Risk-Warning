"""Actual Phase3 UI checks against real public fuel data; writes only synthetic Demo feedback."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.settings import utcnow


def main():
    out = Path("runtime/phase3/browser")
    out.mkdir(parents=True, exist_ok=True)
    result = {"checked_at": utcnow().isoformat(), "status": "RUNNING", "checks": [], "page_errors": []}

    def passed(name):
        result["checks"].append({"name": name, "status": "PASS"})
        (out / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        try:
            for w, h, name in [(1440, 1000, "desktop"), (390, 844, "mobile390")]:
                context = browser.new_context(viewport={"width": w, "height": h}, accept_downloads=True)
                context.route(
                    "**/*",
                    lambda r: (
                        r.continue_()
                        if urlsplit(r.request.url).hostname in ["localhost", "127.0.0.1"]
                        else r.abort()
                    ),
                )
                page = context.new_page()
                page.set_default_timeout(15000)
                expect.set_options(timeout=15000)
                page.on("pageerror", lambda e: result["page_errors"].append(str(e)))

                def select_nav(label):
                    expand = page.get_by_test_id("stExpandSidebarButton")
                    if expand.is_visible():
                        expand.click()
                    page.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
                    if w == 390:
                        close = page.get_by_test_id("stSidebarHeader").get_by_role("button")
                        if close.count() and close.first.is_visible():
                            close.first.click()

                page.goto("http://127.0.0.1:8530", wait_until="domcontentloaded")
                expect(
                    page.get_by_text("决策支持 · 事实 / 推断 / 业务声明 / 行动分开", exact=True)
                ).to_be_visible()
                card = page.locator("details").filter(
                    has=page.get_by_text(
                        re.compile(r"^决策 #\d+ · 柴油价格观测｜Germany｜2026-11-09 · pending$")
                    )
                )
                expect(card).to_have_count(1)
                card.locator("summary").click()
                expect(
                    card.get_by_text("严重度：unknown；业务相关度：unknown；影响程度：unknown", exact=True)
                ).to_be_visible()
                expect(
                    card.get_by_text("无已核实事实；未把采集成功当作业务核实。", exact=True)
                ).to_be_visible()
                expect(card.get_by_role("link", name="原文与证据", exact=True)).to_have_attribute(
                    "href", re.compile("energy.ec.europa.eu/document/download/")
                )
                page.screenshot(path=str(out / f"{name}-real-card.png"), full_page=True)
                passed(
                    name
                    + ": actual Germany fuel card, source workbook link and unknown company impact; no auto-verified facts"
                )
                select_nav("日报与周报")
                page.get_by_role("combobox", name="报告周期", exact=True).click()
                page.get_by_role("option", name="weekly", exact=True).click()
                page.get_by_role("button", name="生成本空间报告", exact=True).click()
                expect(page.get_by_text("报告已保存", exact=True)).to_be_visible()
                report = page.locator("details").filter(
                    has=page.get_by_text(re.compile("^LIVE · decision_weekly ·"))
                )
                report.locator("summary").click()
                with page.expect_download() as download:
                    report.get_by_role("button", name="下载HTML", exact=True).click()
                file = out / f"{name}-live-decision.html"
                download.value.save_as(str(file))
                text = file.read_text(encoding="utf-8")
                assert (
                    "Germany" in text and "2.253" in text and "DEMO" not in text and "无人工核实事实" in text
                )
                page.screenshot(path=str(out / f"{name}-real-report.png"), full_page=True)
                passed(
                    name
                    + ": actual Live weekly decision report rendered/downloaded with normalized price, sources and uncertainty"
                )
                select_nav("Sources 数据源")
                expect(
                    page.get_by_text(
                        "成功率仅为本库Live实际HTTP尝试样本；未请求为未知，DEMO不计入。", exact=True
                    )
                ).to_be_visible()
                passed(name + ": source health sample/quality disclosure accessible")
                select_nav("DEMO · 合成测试数据")
                expand = page.get_by_test_id("stExpandSidebarButton")
                if expand.is_visible():
                    expand.click()
                page.get_by_role("button", name="加载 DEMO 合成数据", exact=True).click()
                if w == 390:
                    close = page.get_by_test_id("stSidebarHeader").get_by_role("button")
                    if close.count() and close.first.is_visible():
                        close.first.click()
                select_nav("统一情报中心")
                demo = page.locator("details").filter(
                    has=page.get_by_text(re.compile(r"^决策 #\d+ · DEMO factory announced · "))
                )
                demo.locator("summary").click()
                expect(
                    demo.get_by_text(
                        "严重度：unknown；业务相关度：matched_user_context；影响程度：potential_unconfirmed",
                        exact=True,
                    )
                ).to_be_visible()
                demo.get_by_text("处理中", exact=True).click()
                demo.get_by_role("textbox", name="处理人", exact=True).fill("DEMO QA")
                demo.get_by_role("textbox", name="处理原因/反馈", exact=True).fill(
                    "DEMO only, no business attestation"
                )
                demo.get_by_role("button", name="保存处理与反馈", exact=True).click()
                expect(
                    demo.get_by_text("处理/核实声明已审计；新证据版本需重新审核。", exact=True)
                ).to_be_visible()
                page.screenshot(path=str(out / f"{name}-demo-feedback.png"), full_page=True)
                passed(
                    name
                    + ": Demo project linked to synthetic context and feedback persisted without attesting facts"
                )
                select_nav("MANUAL · 人工输入待核实")
                expect(
                    page.get_by_text(
                        "暂无合格决策事件；可关闭筛选查看背景/待核实记录，覆盖不足不代表无风险。", exact=True
                    )
                ).to_be_visible()
                select_nav("LIVE · 官方真实采集")
                expect(page.get_by_text(re.compile(r"^决策 #\d+ · 柴油价格观测｜Germany"))).to_be_visible()
                select_nav("01 港口与物流")
                frame = page.frame_locator('iframe[title="scm.ui.port_details.escim_interactive_world"]')
                expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
                expect(frame.locator(".leaflet-popup")).to_have_count(0)
                expect(page.get_by_role("heading")).to_have_count(0)
                expect(page.get_by_test_id("stMetric")).to_have_count(0)
                passed(
                    name
                    + ": Manual empty/Live isolated; pure map remains map-only with12 markers and no dashboard"
                )
                expect(page.get_by_test_id("stException")).to_have_count(0)
                context.close()
            assert not result["page_errors"]
            result["status"] = "PASS"
            (out / "browser.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            browser.close()
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:1800]
            (out / "browser.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            page.screenshot(path=str(out / "failure.png"), full_page=True)
            browser.close()
            raise


if __name__ == "__main__":
    main()
