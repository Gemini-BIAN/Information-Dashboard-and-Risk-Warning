"""Optional real Chromium UAT against an isolated localhost QA database.

Requires playwright==1.56.0 and a Chromium executable (or `playwright install chromium`).
Do NOT point at an owner's working DB: this script reviews Demo evidence, adjusts a Demo
port, imports fictional CSV, and generates a Demo report. It never collects source news.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

from scm.settings import ROOT, TIMEZONE, utcnow


def run(args):
    assert urlsplit(args.url).hostname in ["127.0.0.1", "localhost"], "Only localhost UAT is supported"
    assert args.isolated_qa, "Pass --isolated-qa only for a disposable QA DB/server"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "RUNNING",
        "verified_at": utcnow().astimezone(TIMEZONE).isoformat(),
        "dataset": "isolated copy: 15 retained public EU Live articles + clearly fictional Demo data; not new live ingestion",
        "checks": [],
        "screenshots": [],
        "page_errors": [],
    }

    def passed(name):
        result["checks"].append({"check": name, "status": "PASS"})

    with sync_playwright() as p:
        launch = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if args.chromium:
            launch["executable_path"] = args.chromium
        browser = p.chromium.launch(**launch)
        result["browser"] = "Chromium " + browser.version
        page = browser.new_page(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
        # This is a localhost-only browser run. Block outbound assets/requests rather
        # than sending loopback WebSocket traffic to the external HTTPS proxy.
        page.route(
            "**/*",
            lambda route: (
                route.continue_()
                if urlsplit(route.request.url).hostname in ["127.0.0.1", "localhost"]
                else route.abort()
            ),
        )
        page.set_default_timeout(30000)
        expect.set_options(timeout=15000)
        page.on("pageerror", lambda error: result["page_errors"].append(str(error)))

        def ready():
            expect(page.get_by_role("heading", name="供应链例外与风险指挥台", exact=True)).to_be_visible()
            expect(page.get_by_test_id("stException")).to_have_count(0)

        def navigate(label, heading):
            page.get_by_role("radio", name=label, exact=True).check()
            expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
            ready()

        def expand(label):
            details = page.locator("details").filter(has=page.get_by_text(label, exact=True)).first
            if details.get_attribute("open") is None:
                details.locator("summary").click()
            return details

        def shot(name):
            ready()
            page.evaluate("() => document.fonts.ready.then(() => true)")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                "Viewport horizontal overflow"
            )
            path = args.output_dir / (name + ".png")
            page.screenshot(path=str(path))
            result["screenshots"].append(
                {
                    "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                    "viewport": page.viewport_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "unaltered": True,
                }
            )

        page.goto(args.url, wait_until="networkidle")
        ready()
        expect(page.get_by_text("LIVE · 真实来源", exact=True)).to_be_visible()
        expect(page.get_by_test_id("stMetricValue").first).to_have_text("0")
        expect(page.get_by_text("今日采集覆盖不足", exact=False).first).to_be_visible()
        assert "非实时告警" in page.locator(".scm-card-head").first.inner_text()
        first_title = page.locator(".scm-event-title").first
        assert "PET Spunbond" in first_title.inner_text(), (
            "Grounded trade topic should precede generic aviation capacity"
        )
        assert abs(page.get_by_test_id("stSidebar").bounding_box()["width"] - 240) < 3
        first_source = page.get_by_role("link", name="查看原始来源", exact=True).first
        assert first_source.bounding_box()["y"] < 768, (
            "First queue source link must be in 1366x768 first viewport"
        )
        shot("after-live-1366")
        passed(
            "Live first viewport: four distinct KPIs, coverage/freshness, relevant queue, 240px sidebar, source link visible"
        )
        page.get_by_role("radio", name="演示数据 Demo", exact=True).check()
        expect(page.get_by_text("DEMO · 虚构数据", exact=True)).to_be_visible()
        expect(page.get_by_test_id("stMetricValue").first).to_have_text("0")
        shot("after-demo-1366")
        passed("Demo clearly fictional; unreviewed high content not counted as confirmed current disruption")
        navigate("情报研判", "情报研判与审核")
        search = page.get_by_role("textbox", name="搜索情报", exact=True)
        search.fill("CATL")
        search.press("Enter")
        expect(page.locator(".scm-event-title")).to_have_count(1)
        page.get_by_role("combobox", name="内容严重度", exact=True).click()
        page.get_by_role("option", name="高", exact=True).click()
        expect(page.locator(".scm-event-title")).to_have_count(0)
        page.get_by_role("combobox", name="内容严重度", exact=True).click()
        page.get_by_role("option", name="全部", exact=True).click()
        expect(page.locator(".scm-event-title")).to_have_count(1)
        with page.expect_download() as info:
            page.get_by_role("button", name="导出筛选结果 CSV", exact=True).click()
        data = Path(info.value.path()).read_text(encoding="utf-8-sig")
        assert (
            "CATL" in data
            and "data_mode" in data
            and "demo" in data
            and "confirmed_current_operational" in data
        )
        passed("Search + severity filter + filtered CSV export preserve source and risk taxonomy")
        summary = page.locator("summary").filter(has_text="查看事实、依据与审核").first
        summary.click()
        page.get_by_role("textbox", name="审核人", exact=True).fill("UI QA · isolated Demo")
        page.get_by_role("textbox", name="原因/备注（必填）", exact=True).fill(
            "仅用于隔离UAT：需核实原文、负责人和下一步，不代表真实运营。"
        )
        page.get_by_role("button", name="保存审核记录", exact=True).click()
        expect(page.get_by_text("审核/行动记录已保存", exact=True)).to_be_visible()
        # Reopen after rerun if necessary. No raw evidence or lifecycle changes are permitted.
        details = (
            page.locator("details").filter(has=page.get_by_text("核心事实 · 原文依据", exact=True)).first
        )
        if details.get_attribute("open") is None:
            details.locator("summary").click()
        expect(
            page.get_by_text("仅用于隔离UAT：需核实原文、负责人和下一步，不代表真实运营。", exact=True)
        ).to_be_visible()
        shot("after-review-demo-1366")
        passed("Review writes self-reported actor/reason and timeline; unknown lifecycle not promoted")
        navigate("态势总览", "例外与待核实队列")
        expect(page.get_by_test_id("stMetricValue").first).to_have_text("0")
        navigate("港口监测", "港口监测")
        page.get_by_role("combobox", name="选择港口", exact=True).click()
        page.get_by_role("option", name="Hamburg", exact=True).click()
        expect(
            page.get_by_text("等待时间 / 拥堵趋势：数据暂不可用。未接入可靠真实时间序列。", exact=True)
        ).to_be_visible()
        expand("人工调整风险 · 保留审计")
        page.get_by_role("combobox", name="调整等级", exact=True).click()
        page.get_by_role("option", name="高", exact=True).click()
        page.get_by_role("textbox", name="调整人", exact=True).fill("UI QA")
        page.get_by_role("textbox", name="调整原因（必填）", exact=True).fill(
            "仅隔离Demo测试，非真实港口状态"
        )
        page.get_by_role("button", name="保存人工状态", exact=True).click()
        expect(page.get_by_test_id("stMetricValue").first).to_have_text("高")
        expect(page.get_by_test_id("stMetricValue").nth(1)).to_have_text("0")
        shot("after-port-demo-1366")
        passed(
            "Port manual rule override remains separate from confirmed operations; no invented waiting-time chart"
        )
        navigate("航次与 ETA", "航次与 ETA 风险")
        expand("CSV导入 · 最大5MB / 1万行")
        expect(page.get_by_test_id("stFileUploaderDropzone")).to_contain_text("5MB")
        assert "200MB" not in page.get_by_test_id("stFileUploaderDropzone").inner_text()
        page.locator("input[type=file]").set_input_files(str(ROOT / "fixtures/demo_shipments.csv"))
        page.get_by_role("button", name="校验并导入当前数据空间", exact=True).click()
        expect(page.get_by_text("CSV导入完成：新增 0，重复跳过 3（demo）", exact=True)).to_be_visible()
        passed("Native upload advertises 5MB; valid Demo CSV import is idempotent")
        expand("CSV导入 · 最大5MB / 1万行")
        page.locator("input[type=file]").set_input_files(
            {"name": "too-large.csv", "mimeType": "text/csv", "buffer": b"x" * 5_000_001}
        )
        page.get_by_role("button", name="校验并导入当前数据空间", exact=True).click()
        expect(
            page.get_by_text("文件超过应用5MB上限（5,000,000字节），请拆分后导入。", exact=True)
        ).to_be_visible()
        passed("Application rejects 5,000,001-byte CSV without a write")
        page.locator("input[type=file]").set_input_files(
            {"name": "native-too-large.csv", "mimeType": "text/csv", "buffer": b"x" * (5 * 1024 * 1024 + 1)}
        )
        expect(page.get_by_text("File must be 5.0MB or smaller.", exact=False)).to_be_visible()
        passed("Browser/server uploader rejects over-5MiB file")
        page.locator("input[type=file]").set_input_files(
            {"name": "invalid.csv", "mimeType": "text/csv", "buffer": b"wrong,headers\n1,2\n"}
        )
        page.get_by_role("button", name="校验并导入当前数据空间", exact=True).click()
        expect(
            page.get_by_text("CSV headers must match provided template exactly", exact=False)
        ).to_be_visible()
        passed("Invalid CSV shows error; existing snapshots preserved")
        # Clear the file so the shipment screenshot only contains intended demonstration data.
        page.locator("input[type=file]").set_input_files([])
        page.locator("summary").filter(has_text="DEMO-0001").first.click()
        shot("after-shipment-demo-1366")
        page.get_by_role("radio", name="真实数据 Live", exact=True).check()
        expect(page.get_by_text("LIVE · 真实来源", exact=True)).to_be_visible()
        expand("CSV导入 · 最大5MB / 1万行")
        page.locator("input[type=file]").set_input_files(str(ROOT / "fixtures/demo_shipments.csv"))
        page.get_by_role("button", name="校验并导入当前数据空间", exact=True).click()
        expect(page.get_by_text("Demo identifiers cannot be imported as live", exact=False)).to_be_visible()
        passed("Live rejects Demo identifiers; data space cannot silently change shipment provenance")
        navigate("情报报告", "情报报告")
        expect(page.get_by_role("combobox", name="历史报告", exact=True)).to_be_visible()
        expect(page.locator("iframe")).to_have_count(1)
        shot("after-reports-live-1366")
        passed("Live report history + isolated HTML preview and download render")
        navigate("来源与系统", "来源与系统")
        expect(page.get_by_text("今日有效日覆盖", exact=True)).to_be_visible()
        shot("after-sources-live-1366")
        page.get_by_role("radio", name="演示数据 Demo", exact=True).check()
        expand("手动采集与调度")
        expect(page.get_by_role("button", name="执行真实公开来源采集", exact=True)).to_be_disabled()
        passed("Source status/failures/freshness visible; Demo cannot trigger real collection")
        page.get_by_role("radio", name="真实数据 Live", exact=True).check()
        navigate("态势总览", "例外与待核实队列")
        page.set_viewport_size({"width": 390, "height": 844})
        collapse = page.get_by_test_id("stSidebarCollapseButton")
        if collapse.is_visible():
            collapse.locator("button").click()
        expect(page.get_by_role("heading", name="供应链例外与风险指挥台", exact=True)).to_be_visible()
        shot("after-live-mobile-390")
        passed("390px mobile viewport has no horizontal page overflow")
        assert not result["page_errors"], result["page_errors"]
        passed("No browser pageerror or Streamlit exception across interactions")
        browser.close()
    result["status"] = "PASS"
    result["baseline_revision"] = args.baseline_revision
    before = args.output_dir / "before-live-1366.png"
    if before.exists():
        result["baseline_screenshot_sha256"] = hashlib.sha256(before.read_bytes()).hexdigest()
    files = list((ROOT / "src/scm/ui").glob("*.py")) + [ROOT / ".streamlit/config.toml"]
    result["tested_ui_sha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files
    }
    result["git_head_at_run"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    result["limitations"] = [
        "QA interactions write only the disposable DB; not a production incident or human business sign-off.",
        "Screenshots are direct local app viewports, unaltered; no external enterprise overlay was changed or removed.",
        "Source collection, waiting-time, external LLM, Windows-native and comprehensive WCAG audit are outside this browser run.",
    ]
    (args.output_dir / "browser-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": len(result["checks"]),
                "screenshots": len(result["screenshots"]),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8503")
    parser.add_argument("--chromium", default=None)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/ui_uat")
    parser.add_argument("--baseline-revision", default=None)
    parser.add_argument("--isolated-qa", action="store_true")
    run(parser.parse_args())
