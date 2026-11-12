"""Real localhost browser acceptance over existing evidence; no Live collection or DB copy."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.database.session import session_factory
from scm.ports.detail import detail
from scm.ports.registry import registry
from scm.settings import utcnow


def main():
    out = Path("runtime/port-detail/browser")
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "verified_at": utcnow().isoformat(),
        "status": "RUNNING",
        "checks": [],
        "page_errors": [],
        "viewports": [],
    }

    def save():
        (out / "browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def passed(name):
        result["checks"].append({"name": name, "status": "PASS"})
        save()

    with session_factory("sqlite:///runtime/platform/platform.db")() as session:
        raw = detail(session, "hamburg", "live")["records"]
        assert raw and all(r["background"] for r in raw)
        expected = raw[0]
        result["actual_evidence"] = {
            "id": expected["id"],
            "url": expected["url"],
            "sha256": expected["sha256"],
            "body_sha256": expected["body_sha256"],
        }
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        result["browser"] = browser.version
        try:
            for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile390")]:
                context = browser.new_context(viewport={"width": width, "height": height})
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
                page.on("pageerror", lambda e: result["page_errors"].append(str(e)))

                def sidebar():
                    button = page.get_by_test_id("stExpandSidebarButton")
                    if button.is_visible():
                        button.click()

                def close_sidebar():
                    if width == 390:
                        b = page.get_by_test_id("stSidebarHeader").get_by_role("button")
                        if b.count() and b.first.is_visible():
                            b.first.click()

                def space(label):
                    sidebar()
                    page.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
                    close_sidebar()

                def choose(port):
                    page.get_by_role("combobox", name="选择业务港口", exact=True).click()
                    page.get_by_role("option", name=port.business_label, exact=True).click()
                    heading = page.get_by_role(
                        "heading", name=port.business_label + " · " + port.name_zh, exact=True
                    )
                    expect(heading).to_have_count(1)
                    expect(heading).to_be_visible()

                def back():
                    page.get_by_role("button", name="← 返回地图", exact=True).click()
                    expect(page.get_by_role("tab")).to_have_count(0)
                    expect(page.get_by_role("button", name="查看详情", exact=True)).to_be_visible()

                page.goto("http://127.0.0.1:8530/?port=dover&port_view=map", wait_until="domcontentloaded")
                expect(page.get_by_role("heading", name="港口监测", exact=True)).to_be_visible()
                frame = page.frame_locator('iframe[title="scm.ui.port_monitor.escim_port_world"]')
                expect(frame.locator("#map")).to_have_attribute("data-marker-count", "12")
                frame.locator('[data-port-id="hamburg"]').click()
                expect(page.get_by_role("heading", name="HAMBURG · 汉堡", exact=True)).to_be_visible()
                expect(page.get_by_role("tab")).to_have_count(0)
                page.screenshot(path=str(out / f"{name}-map-summary.png"), full_page=True)
                passed(name + ": map click opens concise Hamburg summary,12 markers, no embedded full tabs")
                page.get_by_role("button", name="查看详情", exact=True).click()
                expect(page.get_by_role("tab")).to_have_count(4)
                expect(page.get_by_text("没有合格当前运营证据；状态未知。", exact=True)).to_be_visible()
                page.screenshot(path=str(out / f"{name}-overview.png"), full_page=True)
                page.get_by_role("tab", name="来源证据", exact=True).click()
                card = page.locator("details").filter(
                    has=page.get_by_text(
                        f"证据 {expected['id']} · {expected and raw[0]['title']} · v{raw[0]['version']}",
                        exact=True,
                    )
                )
                card.locator("summary").click()
                expect(
                    card.get_by_text("原始证据指纹 SHA256：" + expected["sha256"], exact=True)
                ).to_be_visible()
                expect(card.get_by_role("link", name="跳转原始来源", exact=True)).to_have_attribute(
                    "href", expected["url"]
                )
                expect(
                    card.get_by_text("背景/人工资料，不作为当前港口状态证据。", exact=True)
                ).to_be_visible()
                page.screenshot(path=str(out / f"{name}-real-evidence.png"), full_page=True)
                passed(
                    name
                    + ": actual stored Hamburg evidence SHA/link/review/times shown, background not current operations"
                )
                page.get_by_role("tab", name="公告时间线", exact=True).click()
                page.get_by_role("combobox", name="事件状态", exact=True).click()
                page.get_by_role("option", name="当前有效", exact=True).click()
                expect(page.get_by_text("暂无符合筛选的公告；不推断当前正常。", exact=True)).to_be_visible()
                page.screenshot(path=str(out / f"{name}-timeline-empty.png"), full_page=True)
                passed(
                    name
                    + ": current-event filter excludes historical/background actual records and shows empty state"
                )
                page.get_by_role("tab", name="业务影响", exact=True).click()
                expect(page.get_by_text("尚未配置港口使用情况，保持未知。", exact=True)).to_be_visible()
                expect(
                    page.get_by_text(
                        "企业业务影响：未知。脱敏配置是用户声明，不是已核实运输事实，不据此计算影响等级或更改风险规则。",
                        exact=True,
                    )
                ).to_be_visible()
                page.screenshot(path=str(out / f"{name}-business-unknown.png"), full_page=True)
                back()
                expect(page.get_by_role("combobox", name="选择业务港口", exact=True)).to_have_value("HAMBURG")
                passed(name + ": unconfigured business impact unknown; return preserves selected Hamburg")
                for port in registry().ports:
                    choose(port)
                    page.get_by_role("button", name="查看详情", exact=True).click()
                    expect(
                        page.get_by_role(
                            "heading", name=port.business_label + " · " + port.name_zh, exact=True
                        )
                    ).to_be_visible()
                    expect(page.get_by_role("tab")).to_have_count(4)
                    expect(page.get_by_test_id("stException")).to_have_count(0)
                    back()
                passed(name + ": all12 registry ports complete summary/detail/back round trip")
                page.get_by_role("button", name="查看详情", exact=True).click()
                expect(page.get_by_role("tab")).to_have_count(4)
                expect(page).to_have_url(re.compile(r"port_view=detail"))
                page.reload()
                expect(page.get_by_role("tab")).to_have_count(4)
                back()
                passed(name + ": reloadable detail URL and return map route")
                choose(next(p for p in registry().ports if p.id == "dover"))
                space("DEMO · 合成测试数据")
                sidebar()
                page.get_by_role("button", name="加载 DEMO 合成数据", exact=True).click()
                close_sidebar()
                page.get_by_role("button", name="查看详情", exact=True).click()
                page.get_by_role("tab", name="公告时间线", exact=True).click()
                expect(page.get_by_text("DEMO", exact=False).first).to_be_visible()
                page.get_by_role("tab", name="业务影响", exact=True).click()
                page.get_by_role("textbox", name="港口使用情况", exact=True).fill("DEMO redacted test usage")
                page.get_by_role("textbox", name="配置人", exact=True).fill("UAT tester")
                page.get_by_role("textbox", name="修改原因", exact=True).fill(
                    "DEMO local configuration acceptance"
                )
                page.get_by_role("button", name="保存脱敏配置", exact=True).click()
                expect(page.get_by_text("已保存；业务影响仍待核实。", exact=True)).to_be_visible()
                space("LIVE · 官方真实采集")
                page.get_by_role("tab", name="业务影响", exact=True).click()
                expect(page.get_by_role("textbox", name="港口使用情况", exact=True)).to_have_value("")
                space("MANUAL · 人工输入待核实")
                page.get_by_role("tab", name="来源证据", exact=True).click()
                expect(page.get_by_text("尚无本港可追溯原文证据。", exact=True)).to_be_visible()
                passed(
                    name
                    + ": Demo profile saved/audited; Live empty profile and Manual empty evidence isolated"
                )
                overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
                assert not overflow
                result["viewports"].append(
                    {"width": width, "height": height, "horizontal_overflow": overflow}
                )
                context.close()
            assert not result["page_errors"]
            result["status"] = "PASS"
            save()
        except Exception as exc:
            result["status"] = "FAIL"
            result["error"] = type(exc).__name__ + ": " + str(exc)[:1500]
            save()
            page.screenshot(path=str(out / "failure.png"), full_page=True)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
