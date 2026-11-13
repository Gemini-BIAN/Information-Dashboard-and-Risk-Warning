"""Actual Leaflet input tests: tiles, wheel, drag, clicks, popup close, route and viewport restoration."""

import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from scm.ports.registry import registry
from scm.settings import utcnow


def main():
    os.environ["PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK"] = "1"
    output = Path("runtime/world-map/browser")
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "checked_at": utcnow().isoformat(),
        "status": "RUNNING",
        "checks": [],
        "page_errors": [],
        "tiles": [],
        "viewports": [],
    }

    def save():
        (output / "browser.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def passed(name):
        result["checks"].append({"name": name, "status": "PASS"})
        save()

    with sync_playwright() as p:
        options = dict(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        if os.environ.get("HTTPS_PROXY"):
            options["proxy"] = {"server": os.environ["HTTPS_PROXY"], "bypass": "127.0.0.1,localhost"}
        browser = p.chromium.launch(**options)
        result["browser"] = browser.version
        try:
            for width, height, name in [(1440, 1000, "desktop"), (390, 844, "mobile390")]:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    is_mobile=width == 390,
                    has_touch=width == 390,
                )
                page = context.new_page()
                page.set_default_timeout(15000)
                expect.set_options(timeout=15000)
                page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
                page.on(
                    "response",
                    lambda r: (
                        result["tiles"].append({"url": r.url, "status": r.status})
                        if "tile.openstreetmap.org" in r.url
                        else None
                    ),
                )
                page.goto("http://127.0.0.1:8530/?port_view=map", wait_until="domcontentloaded")
                frame = page.frame_locator('iframe[title="scm.ui.port_details.escim_interactive_world"]')
                root = frame.locator("#map")
                expect(root).to_have_attribute("data-marker-count", "12")
                expect(root).to_have_attribute("data-basemap", "online")
                expect(root).to_have_attribute("data-tiles-ready", "true")
                expect(frame.locator(".leaflet-popup")).to_have_count(0)
                expect(page.get_by_role("heading")).to_have_count(0)
                expect(page.get_by_role("combobox")).to_have_count(0)
                expect(page.get_by_test_id("stMetric")).to_have_count(0)
                assert int(root.get_attribute("data-loaded-tiles")) > 0
                page.screenshot(path=str(output / f"{name}-default-world.png"), full_page=True)
                passed(
                    name
                    + ": pure full-area online colour world map,12 markers,no selection/title/dropdown/metrics/popup"
                )
                old_zoom = float(root.get_attribute("data-zoom"))
                # Wheel zoom at actual Hamburg marker coordinates; no map.setZoom/setView shortcuts.
                marker = frame.locator('[data-port-id="hamburg"].leaflet-marker-icon')
                box = marker.bounding_box()
                page.mouse.move(box["x"] + 9, box["y"] + 9)
                page.mouse.wheel(0, -900)
                page.wait_for_function(
                    '(z)=>Number(document.querySelector("iframe").contentDocument.querySelector("#map").dataset.zoom)>z',
                    arg=old_zoom,
                )
                zoom = float(root.get_attribute("data-zoom"))
                assert zoom > old_zoom
                mapbox = root.bounding_box()
                x = mapbox["x"] + mapbox["width"] * 0.45
                y = mapbox["y"] + mapbox["height"] * 0.65
                before = root.get_attribute("data-center")
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + 75, y + 45, steps=12)
                page.mouse.up()
                page.wait_for_function(
                    '(before)=>document.querySelector("iframe").contentDocument.querySelector("#map").dataset.center!==before',
                    arg=before,
                )
                page.screenshot(path=str(output / f"{name}-zoomed-panned.png"), full_page=True)
                passed(name + ": actual mouse wheel changes zoom; actual drag changes geographic centre")
                # Keyboard focus is Leaflet's native accessible auto-pan, followed by actual mouse click.
                marker.focus()
                marker.click()
                popup = frame.locator(".leaflet-popup")
                expect(popup).to_be_visible()
                expect(popup.get_by_text("Hamburg · 汉堡", exact=True)).to_be_visible()
                expect(popup.get_by_text("当前运营状态：未知", exact=True)).to_be_visible()
                expect(popup).to_have_css("opacity", "1")
                page.screenshot(path=str(output / f"{name}-hamburg-popup.png"), full_page=True)
                point = marker.bounding_box()
                card = popup.bounding_box()
                assert abs((card["x"] + card["width"] / 2) - (point["x"] + 9)) < 180
                frame.locator("#map").click(position={"x": 30, "y": mapbox["height"] * 0.72})
                expect(popup).to_have_count(0)
                marker.click()
                expect(popup).to_be_visible()
                popup.locator(".leaflet-popup-close-button").click()
                expect(popup).to_have_count(0)
                passed(
                    name
                    + ": Hamburg anchored popup has unknown state; blank-map click and close button both dismiss it"
                )
                # Zoom controls are actual UI buttons, enough separation for the two River Tees markers.
                while float(root.get_attribute("data-zoom")) < 11:
                    prior = float(root.get_attribute("data-zoom"))
                    frame.get_by_role("button", name="放大", exact=True).click()
                    page.wait_for_function(
                        '(z)=>Number(document.querySelector("iframe").contentDocument.querySelector("#map").dataset.zoom)>z',
                        arg=prior,
                    )
                for port in registry().ports:
                    m = frame.locator('[data-port-id="' + port.id + '"].leaflet-marker-icon')
                    m.focus()
                    m.click()
                    expect(popup).to_have_count(1)
                    expect(popup.locator("section")).to_have_attribute("data-port-id", port.id)
                    popup.locator(".leaflet-popup-close-button").click()
                    expect(popup).to_have_count(0)
                passed(
                    name
                    + ": all12 exact-coordinate markers actually clicked and matching anchored cards opened"
                )
                marker.focus()
                marker.click()
                expect(popup).to_be_visible()
                # Stop any accessibility auto-pan by waiting for the centre to settle, not injecting a view.
                page.wait_for_timeout(350)
                saved = {
                    "center": json.loads(root.get_attribute("data-center")),
                    "zoom": float(root.get_attribute("data-zoom")),
                }
                popup.get_by_role("button", name="查看详情", exact=True).click()
                expect(page.get_by_role("tab")).to_have_count(4)
                page.get_by_role("button", name="← 返回地图", exact=True).click()
                expect(root).to_have_attribute("data-marker-count", "12")
                expect(popup).to_have_count(0)
                restored = {
                    "center": json.loads(root.get_attribute("data-center")),
                    "zoom": float(root.get_attribute("data-zoom")),
                }
                assert restored["zoom"] == saved["zoom"] and all(
                    abs(a - b) < 0.01 for a, b in zip(restored["center"], saved["center"])
                ), (saved, restored)
                passed(
                    name + ": four existing detail tabs preserved; back restores centre/zoom and closes popup"
                )
                if width == 390:
                    session = context.new_cdp_session(page)
                    box = root.bounding_box()
                    cx = box["x"] + box["width"] / 2
                    cy = box["y"] + box["height"] / 2
                    start = float(root.get_attribute("data-zoom"))
                    session.send(
                        "Input.dispatchTouchEvent",
                        {
                            "type": "touchStart",
                            "touchPoints": [{"x": cx - 35, "y": cy}, {"x": cx + 35, "y": cy}],
                        },
                    )
                    for distance in [50, 70, 95]:
                        session.send(
                            "Input.dispatchTouchEvent",
                            {
                                "type": "touchMove",
                                "touchPoints": [{"x": cx - distance, "y": cy}, {"x": cx + distance, "y": cy}],
                            },
                        )
                    session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                    page.wait_for_function(
                        '(z)=>Number(document.querySelector("iframe").contentDocument.querySelector("#map").dataset.zoom)>z',
                        arg=start,
                    )
                    passed("mobile390: actual two-finger CDP touch gesture changes map zoom")
                frame.get_by_role("button", name="恢复世界视图", exact=True).click()
                page.wait_for_function(
                    '(z)=>Number(document.querySelector("iframe").contentDocument.querySelector("#map").dataset.zoom)<z',
                    arg=11,
                )
                expect(popup).to_have_count(0)
                passed(
                    name
                    + ": small world-reset control returns to whole-world viewport without selecting port"
                )
                result["viewports"].append(
                    {
                        "width": width,
                        "height": height,
                        "saved": saved,
                        "restored": restored,
                        "loaded_tiles": int(root.get_attribute("data-loaded-tiles")),
                    }
                )
                context.close()
            context = browser.new_context(viewport={"width": 390, "height": 844})
            context.route("https://tile.openstreetmap.org/**", lambda r: r.abort())
            page = context.new_page()
            page.goto("http://127.0.0.1:8530/?port_view=map")
            frame = page.frame_locator('iframe[title="scm.ui.port_details.escim_interactive_world"]')
            expect(frame.locator("#map")).to_have_attribute("data-basemap", "offline")
            expect(frame.get_by_role("status")).to_contain_text("在线底图不可用")
            assert frame.locator(".leaflet-overlay-pane path").count() > 100
            page.screenshot(path=str(output / "mobile390-explicit-offline-fallback.png"), full_page=True)
            passed(
                "Blocked tiles: explicit warning and real Leaflet vector fallback with country geometry, not a blank success"
            )
            assert not result["page_errors"]
            result["status"] = "PASS"
            save()
            browser.close()
        except Exception as e:
            result["status"] = "FAIL"
            result["error"] = type(e).__name__ + ": " + str(e)[:1600]
            save()
            page.screenshot(path=str(output / "failure.png"), full_page=True)
            browser.close()
            raise


if __name__ == "__main__":
    main()
