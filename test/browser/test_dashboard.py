"""Exercise the real Motion WebSocket server, never a JavaScript arbiter.

Run directly against the native C++ simulator. Standard discovery skips this
suite unless AW_CAR_BROWSER_URL is set. Browser traces retain only command
types/timing; Wi-Fi secrets are neither logged nor included in screenshots.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import unittest
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
OPTIONS = {
    "url": os.environ.get("AW_CAR_BROWSER_URL"),
    "output": Path(__file__).resolve().parent / "output",
}


def prepare_output():
    output = Path(OPTIONS["output"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "README.md").write_text(
        "# Browser output\n\n"
        "Ảnh sinh bởi test/browser/test_dashboard.py. layout-offline-* chỉ kiểm bố cục; "
        "dashboard-* chụp simulator native C++. Không phải nghiệm thu phần cứng.\n",
        encoding="utf-8",
    )
    return output

# Instrument browser timing only. All commands/replies still reach the native
# server. Do not retain payloads (especially Wi-Fi credentials) in the trace.
TRACE = """(() => {
  window.__inputTrace = [];
  window.addEventListener('pointerdown', e => {
    if (e.target.closest('[data-action]'))
      window.__inputTrace.push({ t: 'pointerdown', at: performance.now() });
  }, true);
  const original = WebSocket.prototype.send;
  WebSocket.prototype.send = function(payload) {
    try {
      const value = JSON.parse(payload);
      if (['drive', 'neutral', 'stop'].includes(value.t))
        window.__inputTrace.push({ t: value.t, at: performance.now() });
    } catch {}
    return original.call(this, payload);
  };
})();"""


class Probe:
    def __init__(self, page):
        self.page = page
        self.sent = []
        self.statuses = []
        self.socket_count = 0
        self.errors = []
        page.on("websocket", self._socket)
        page.on("pageerror", lambda error: self.errors.append(str(error)))

    def _socket(self, socket):
        self.socket_count += 1
        socket.on("framesent", self._sent)
        socket.on("framereceived", self._received)

    def _sent(self, payload):
        try:
            value = json.loads(payload)
        except (ValueError, TypeError):
            return
        # Record no password, including fake test passwords.
        if value.get("t") == "wifi":
            value = {"t": "wifi", "ssid": value.get("ssid"),
                     "password_present": bool(value.get("password"))}
        self.sent.append((time.monotonic(), value))

    def _received(self, payload):
        try:
            value = json.loads(payload)
        except (ValueError, TypeError):
            return
        if value.get("t") == "status":
            self.statuses.append(value)

    @property
    def latest(self):
        return self.statuses[-1] if self.statuses else {}

    def commands(self, kind, after=0):
        return [value for _, value in self.sent[after:] if value.get("t") == kind]


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not OPTIONS["url"]:
            raise unittest.SkipTest("Browser opt-in: run test/browser/test_dashboard.py against the native simulator")
        from playwright.sync_api import sync_playwright

        deadline = time.monotonic() + 10
        while True:
            try:
                with urlopen(OPTIONS["url"], timeout=1) as response:
                    if response.status != 200:
                        raise RuntimeError("Native simulator HTTP is not ready")
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Native simulator HTTP did not start within10s")
                time.sleep(.05)
        with urlopen(OPTIONS["url"].rstrip("/") + "/sim/state", timeout=5) as response:
            if json.load(response).get("simulator") is not True:
                raise RuntimeError("Refusing browser control tests outside the native simulator")
        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except Exception:
            cls.playwright.stop()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.context.add_init_script(TRACE)
        self.mute_status = False
        self.relays = []
        self.context.route_web_socket("**/ws", self.relay)
        self.sim_event({"event": "reset"})
        self.page, self.probe = self.new_page()
        self.wait(lambda: self.probe.latest.get("simulator") is True,
                  "Refusing drive tests unless STATUS marks simulator=true")
        generation = self.probe.latest.get("generation")
        self.page.locator("#stop").click()
        self.wait(lambda: self.probe.latest.get("generation") != generation,
                  "STOP must advance native Motion generation")
        self.wait_mode("manual")
        self.wait_zero()
        self.page.locator("h1").click()

    def tearDown(self):
        self.context.close()

    def sim_event(self, payload, accepted=True):
        response = self.context.request.post(OPTIONS["url"].rstrip("/") + "/sim/event", data=payload)
        self.assertTrue(response.ok, "Native simulator fixture endpoint failed")
        result = response.json()
        self.assertEqual(result.get("ok"), accepted, "Native core accepted/rejected fixture unexpectedly")
        return result.get("state", {})

    def sim_state(self):
        response = self.context.request.get(OPTIONS["url"].rstrip("/") + "/sim/state")
        self.assertTrue(response.ok)
        return response.json()

    def relay(self, route):
        server = route.connect_to_server()
        self.relays.append(route)

        def receive(payload):
            if self.mute_status:
                try:
                    if json.loads(payload).get("t") == "status":
                        return
                except (ValueError, TypeError):
                    pass
            route.send(payload)

        server.on_message(receive)

    def new_page(self):
        page = self.context.new_page()
        page.set_default_timeout(5000)
        probe = Probe(page)
        page.goto(OPTIONS["url"], wait_until="networkidle")
        page.wait_for_selector('#telemetry[data-fresh="true"]')
        return page, probe

    def wait(self, predicate, message="Expected browser/server condition", page=None, timeout=5):
        page = page or self.page
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            page.wait_for_timeout(15)
        self.assertTrue(predicate(), message)

    def wait_mode(self, mode, page=None, probe=None):
        page, probe = page or self.page, probe or self.probe
        self.wait(lambda: probe.latest.get("mode") == mode, "Native Motion did not enter " + mode, page)
        page.wait_for_function("mode => document.querySelector('#' + mode + '-mode').getAttribute('aria-pressed') === 'true'", arg=mode)

    def wait_zero(self, probe=None, page=None):
        probe, page = probe or self.probe, page or self.page
        self.wait(lambda: probe.latest.get("left") == 0 and probe.latest.get("right") == 0,
                  "Native Motion did not report zero command", page)

    def pointer_down(self, action="forward"):
        box = self.page.locator("#" + action).bounding_box()
        self.assertIsNotNone(box)
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.page.mouse.down()

    def assert_no_drive(self, marker, duration=230):
        self.page.wait_for_timeout(duration)
        self.assertEqual(len(self.probe.commands("drive", marker)), 0, "Unexpected MOVE replay")

    def after_command(self, kind, marker):
        indices = [index for index in range(marker, len(self.probe.sent))
                   if self.probe.sent[index][1].get("t") == kind]
        self.assertTrue(indices, "Missing terminal input command: " + kind)
        return indices[0] + 1

    def test_01_immediate_hold_release_pointer_capture(self):
        self.assertEqual(self.page.locator("#speed").input_value(), "30")
        marker = len(self.probe.sent)
        self.pointer_down()
        self.wait(lambda: len(self.probe.commands("drive", marker)) >= 1)
        trace = self.page.evaluate("window.__inputTrace")
        down = next(item["at"] for item in trace if item["t"] == "pointerdown")
        first = next(item["at"] for item in trace if item["t"] == "drive")
        self.assertLess(first - down, 25, "First MOVE must be sent during press, not the 50 ms repeat")
        self.page.wait_for_timeout(310)
        frames = [(stamp, value) for stamp, value in self.probe.sent[marker:] if value.get("t") == "drive"]
        self.assertGreaterEqual(len(frames), 5)
        self.assertLessEqual(len(frames), 10)
        intervals = [b[0] - a[0] for a, b in zip(frames, frames[1:])]
        self.assertTrue(all(.020 < interval < .130 for interval in intervals), "Held repeat must be near 20 Hz")
        self.assertTrue(all(value == {"t": "drive", "action": "forward", "speed": 30} for _, value in frames))
        self.page.mouse.move(2, 2)
        marker = len(self.probe.sent)
        self.page.mouse.up()
        self.wait(lambda: bool(self.probe.commands("neutral", marker)))
        marker = self.after_command("neutral", marker)
        self.wait_zero()
        self.assert_no_drive(marker)

    def test_02_latest_key_release_does_not_resume_previous(self):
        self.page.keyboard.down("w")
        self.wait(lambda: bool(self.probe.commands("drive")) and self.probe.commands("drive")[-1].get("action") == "forward")
        self.page.keyboard.down("d")
        self.wait(lambda: bool(self.probe.commands("drive")) and self.probe.commands("drive")[-1].get("action") == "right")
        marker = len(self.probe.sent)
        self.page.keyboard.up("d")
        self.wait(lambda: bool(self.probe.commands("neutral", marker)))
        marker = self.after_command("neutral", marker)
        self.wait_zero()
        self.assert_no_drive(marker)
        self.page.keyboard.down("w")  # Browser repeat cannot revive the older held key.
        self.assert_no_drive(marker)
        self.page.keyboard.up("w")

    def test_03_release_older_key_keeps_latest(self):
        self.page.keyboard.down("w")
        self.wait(lambda: bool(self.probe.commands("drive")) and self.probe.commands("drive")[-1].get("action") == "forward")
        self.page.keyboard.down("a")
        # Keyboard RPC completion does not drain Playwright's WebSocket observer.
        # Establish the LEFT frame boundary before marking; otherwise an earlier
        # FORWARD notification can arrive after marker on a busy CI runner.
        self.wait(lambda: bool(self.probe.commands("drive")) and self.probe.commands("drive")[-1].get("action") == "left")
        marker = len(self.probe.sent)
        self.page.keyboard.up("w")
        self.wait(lambda: len(self.probe.commands("drive", marker)) >= 2,
                  "Latest held key must continue repeating after the older key releases", timeout=1)
        self.assertFalse(self.probe.commands("neutral", marker))
        frames = self.probe.commands("drive", marker)
        self.assertTrue(frames and all(value["action"] == "left" for value in frames), frames)
        self.assertEqual(self.sim_state()["action"], "left")
        self.page.keyboard.up("a")
        self.wait_zero()

    def test_04_pointer_cancel_and_lost_capture_clear(self):
        for event in ["pointercancel", "lostpointercapture"]:
            with self.subTest(event=event):
                self.pointer_down()
                self.wait(lambda: self.probe.commands("drive"))
                marker = len(self.probe.sent)
                self.page.locator("#forward").dispatch_event(event, {"pointerId": 1, "bubbles": True})
                self.wait(lambda: bool(self.probe.commands("neutral", marker)))
                marker = self.after_command("neutral", marker)
                self.assert_no_drive(marker)
                self.page.mouse.up()

    def test_05_blur_and_hidden_clear_without_replay(self):
        for event in ["blur", "hidden"]:
            with self.subTest(event=event):
                self.page.keyboard.down("w")
                self.page.wait_for_timeout(80)
                marker = len(self.probe.sent)
                if event == "blur":
                    self.page.evaluate("window.dispatchEvent(new Event('blur'))")
                else:
                    self.page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true, value:true}); document.dispatchEvent(new Event('visibilitychange'))")
                self.wait(lambda: bool(self.probe.commands("neutral", marker)))
                marker = self.after_command("neutral", marker)
                self.assert_no_drive(marker)
                self.page.evaluate("delete document.hidden; document.dispatchEvent(new Event('visibilitychange'))")
                self.page.keyboard.up("w")
                self.assert_no_drive(marker)

    def test_06_input_focus_never_drives(self):
        for selector in ["#ssid", "#password", "#speed"]:
            self.page.locator(selector).focus()
            marker = len(self.probe.sent)
            self.page.keyboard.press("w")
            self.page.keyboard.press("a")
            self.page.keyboard.press("s")
            self.page.keyboard.press("d")
            self.page.keyboard.press("Space")
            self.assert_no_drive(marker, duration=80)
            self.assertFalse(self.probe.commands("stop", marker), "Space must remain text input while editing")

    def test_07_stop_space_and_held_repeat(self):
        self.page.keyboard.down("w")
        self.page.wait_for_timeout(80)
        marker = len(self.probe.sent)
        self.page.keyboard.press("Space")
        self.wait(lambda: bool(self.probe.commands("stop", marker)))
        marker = self.after_command("stop", marker)
        self.wait_zero()
        self.wait_mode("manual")
        self.assert_no_drive(marker)
        self.page.keyboard.down("w")
        self.assert_no_drive(marker)
        self.page.keyboard.up("w")
        self.page.keyboard.down("s")
        self.page.wait_for_timeout(75)
        marker = len(self.probe.sent)
        self.page.locator("#stop").click()
        self.wait(lambda: bool(self.probe.commands("stop", marker)))
        marker = self.after_command("stop", marker)
        self.wait_zero()
        self.assert_no_drive(marker)
        self.page.keyboard.up("s")

    def test_08_ai_disables_manual_but_stop_mode_listen_remain(self):
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        for action in ["forward", "backward", "left", "right"]:
            self.assertTrue(self.page.locator("#" + action).is_disabled())
        for selector in ["#stop", "#manual-mode", "#listen-start", "#listen-stop"]:
            self.assertTrue(self.page.locator(selector).is_enabled())
        marker = len(self.probe.sent)
        self.page.keyboard.press("w")
        self.assert_no_drive(marker)
        self.page.locator("#listen-start").click()
        self.page.locator("#listen-stop").click()
        self.wait(lambda: len(self.probe.commands("listen", marker)) == 2)
        self.assertEqual(self.probe.commands("listen", marker), [{"t": "listen", "enabled": True}, {"t": "listen", "enabled": False}])
        self.page.locator("#stop").click()
        self.wait_mode("manual")
        self.wait_zero()
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        self.page.locator("#manual-mode").click()
        self.wait_mode("manual")
        self.assert_no_drive(marker)

    def test_09_wifi_password_cleared_not_rendered(self):
        marker = len(self.probe.sent)
        self.page.locator("#ssid").fill("Browser-test-network")
        self.page.locator("#password").fill("test-only-not-a-real-secret")
        self.page.locator("#wifi-submit").click()
        self.wait(lambda: bool(self.probe.commands("wifi", marker)))
        self.assertEqual(self.page.locator("#password").input_value(), "")
        self.assertNotIn("test-only-not-a-real-secret", self.page.locator("body").inner_text())
        self.assert_no_drive(marker)

    def test_10_status_gap_one_neutral_no_stop_flood(self):
        self.mute_status = True
        self.page.keyboard.down("w")
        marker = len(self.probe.sent)
        self.page.wait_for_selector('#telemetry[data-fresh="false"]')
        self.page.wait_for_timeout(1050)
        self.assertEqual(len(self.probe.commands("neutral", marker)), 1)
        self.assertEqual(len(self.probe.commands("stop", marker)), 0)
        stale_marker = len(self.probe.sent)
        self.assert_no_drive(stale_marker)
        self.assertIn("Chưa có trạng thái mới", self.page.locator("#motion-state").inner_text())
        self.mute_status = False
        self.page.wait_for_selector('#telemetry[data-fresh="true"]')
        self.wait_zero()
        self.assert_no_drive(stale_marker)
        self.page.keyboard.up("w")

    def test_11_ai_status_gap_sends_no_neutral(self):
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        marker = len(self.probe.sent)
        self.mute_status = True
        self.page.wait_for_selector('#telemetry[data-fresh="false"]')
        self.page.wait_for_timeout(600)
        self.assertFalse(self.probe.commands("neutral", marker))
        self.assertFalse(self.probe.commands("stop", marker))
        self.assert_no_drive(marker)
        self.mute_status = False

    def test_12_tab_takeover_close_code_and_explicit_reconnect(self):
        self.page.keyboard.down("w")
        self.page.wait_for_timeout(100)
        second, second_probe = self.new_page()
        self.page.wait_for_selector("#reconnect:not([hidden])")
        marker = len(self.probe.sent)
        note = self.page.locator("#connection-note").inner_text()
        self.assertIn("1001", note)
        self.assertIn("controller_replaced", note)
        self.wait_mode("manual", second, second_probe)
        self.wait_zero(second_probe, second)
        self.page.wait_for_timeout(650)
        self.assertEqual(self.probe.socket_count, 1, "No automatic reconnect after takeover")
        self.assert_no_drive(marker)
        self.page.keyboard.up("w")
        self.page.bring_to_front()
        self.page.locator("#reconnect").click()
        self.page.wait_for_selector('#telemetry[data-fresh="true"]')
        self.assertEqual(self.probe.socket_count, 2)
        self.wait_zero()
        self.assert_no_drive(marker)
        second.close()

    def test_13_refresh_takes_over_zero_no_move_replay(self):
        self.page.keyboard.down("w")
        self.page.wait_for_timeout(120)
        marker = len(self.probe.sent)
        self.page.reload(wait_until="networkidle")
        self.page.wait_for_selector('#telemetry[data-fresh="true"]')
        self.wait_mode("manual")
        self.wait_zero()
        self.page.keyboard.up("w")
        self.assert_no_drive(marker)
        self.assertEqual(self.probe.socket_count, 2)

    def test_14_speed_and_all_four_directions(self):
        self.page.locator("#speed").evaluate("el => { el.value = '47'; el.dispatchEvent(new Event('input', { bubbles: true })); }")
        self.page.locator("h1").click()
        signs = {"forward": (1, 1), "backward": (-1, -1), "left": (-1, 1), "right": (1, -1)}
        for action, (left_sign, right_sign) in signs.items():
            with self.subTest(action=action):
                marker = len(self.probe.sent)
                self.pointer_down(action)
                self.wait(lambda: bool(self.probe.commands("drive", marker)))
                self.assertEqual(self.probe.commands("drive", marker)[0], {"t": "drive", "action": action, "speed": 47})
                self.wait(lambda: self.probe.latest.get("left", 0) * left_sign > 0 and self.probe.latest.get("right", 0) * right_sign > 0,
                          "Native C++ core reported wrong spin/drive polarity")
                self.page.mouse.up()
                self.wait_zero()

    def test_15_layout_status_and_screenshots(self):
        output = prepare_output()
        self.assertTrue(self.page.locator("#simulator").is_visible())
        self.assertIn("Lệnh PWM", self.page.locator("#telemetry").inner_text())
        self.assertEqual(self.page.locator("[data-action]").count(), 4)
        self.assertEqual(self.probe.errors, [])
        for label, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.evaluate("window.scrollTo(0, 0)")
            self.page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
            # Capture the viewport before full_page changes Chromium's capture
            # surface, so the fixed STOP dock is faithfully present in the PNG.
            self.page.screenshot(path=str(output / ("dashboard-" + label + "-viewport.png")))
            self.page.screenshot(path=str(output / ("dashboard-" + label + ".png")), full_page=True)
            self.assertLessEqual(self.page.evaluate("document.documentElement.scrollWidth"), width)
            for scroll in [0, 800, 3000]:
                self.page.evaluate("y => window.scrollTo(0, y)", scroll)
                box = self.page.locator("#stop").bounding_box()
                self.assertIsNotNone(box)
                self.assertGreaterEqual(box["y"], 0)
                self.assertLessEqual(box["y"] + box["height"], height)
                self.assertGreaterEqual(box["height"], 54)
        self.assertEqual(self.probe.errors, [])

    def test_16_ai_native_duration_stop_and_old_generation(self):
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        old_generation = self.probe.latest["generation"]
        self.sim_event({"event": "ai", "action": "forward", "speed": 36,
                        "duration_ms": 350, "generation": old_generation})
        self.wait(lambda: self.probe.latest.get("left", 0) > 0)
        self.assertIn("AI", self.page.locator("#motion-state").inner_text())
        self.wait_zero()
        self.wait(lambda: self.probe.latest.get("reason") == "ai_complete")
        self.sim_event({"event": "ai", "action": "left", "speed": 30,
                        "duration_ms": 2500, "generation": old_generation})
        self.wait(lambda: self.probe.latest.get("left", 0) < 0 and self.probe.latest.get("right", 0) > 0)
        self.page.locator("#stop").click()
        self.wait_mode("manual")
        self.wait_zero()
        self.assertNotEqual(self.probe.latest["generation"], old_generation)
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        self.sim_event({"event": "ai", "action": "forward", "speed": 60,
                        "duration_ms": 1000, "generation": old_generation}, accepted=False)
        self.page.wait_for_timeout(150)
        self.assertEqual(self.sim_state()["left"], 0)
        self.assertEqual(self.sim_state()["right"], 0)
        self.assertFalse(self.probe.commands("drive"), "The browser must not synthesize AI MOVE commands")

    def test_18_maintenance_clears_held_and_never_replays(self):
        self.page.locator('#forward').hover()
        self.page.mouse.down()
        self.wait(lambda:self.probe.latest.get('left',0)>0)
        self.sim_event({'event':'maintenance','enabled':True})
        self.wait(lambda:self.probe.latest.get('maintenance') is True)
        self.wait_zero()
        self.assertTrue(self.page.locator('#forward').is_disabled())
        self.assertTrue(self.page.locator('#ai-mode').is_disabled())
        self.assertIn('bảo trì',self.page.locator('#mode-hint').inner_text())
        self.assertFalse(self.sim_state()['driver'])
        self.page.mouse.up()
        self.sim_event({'event':'maintenance','enabled':False})
        self.wait(lambda:self.probe.latest.get('maintenance') is False)
        self.page.wait_for_timeout(650)
        self.wait_zero()
        self.assertFalse(self.sim_state()['driver'])

    def test_17_ai_continues_when_web_disconnects(self):
        self.page.locator("#ai-mode").click()
        self.wait_mode("ai")
        self.sim_event({"event": "ai", "action": "forward", "speed": 30,
                        "duration_ms": 1600, "generation": self.probe.latest["generation"]})
        self.wait(lambda: self.probe.latest.get("left", 0) > 0)
        marker = len(self.probe.sent)
        monitor = self.context.new_page()  # No WebSocket; inspect native state only.
        self.page.close()
        monitor.wait_for_timeout(100)
        state = self.sim_state()
        self.assertEqual(state["mode"], "ai")
        self.assertGreater(state["left"], 0)
        self.assertFalse(self.probe.commands("neutral", marker))
        self.assertFalse(self.probe.commands("stop", marker))
        self.wait(lambda: self.sim_state().get("reason") == "ai_complete", page=monitor)
        self.assertEqual(self.sim_state()["left"], 0)
        self.assertEqual(self.sim_state()["right"], 0)


def capture_static_layout():
    """Offline layout only; never manufacture status or simulate the arbiter."""
    from playwright.sync_api import sync_playwright

    output = prepare_output()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto((ROOT / "esp/motion/web/index.html").as_uri(), wait_until="networkidle")
            for name, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844), ("narrow", 320, 700)]:
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("window.scrollTo(0, 0)")
                if page.evaluate("document.documentElement.scrollWidth") > width:
                    raise AssertionError("Layout overflows at " + str(width))
                page.screenshot(path=str(output / ("layout-offline-" + name + ".png")), full_page=True)
                for scroll in [0, 3000]:
                    page.evaluate("y => window.scrollTo(0, y)", scroll)
                    box = page.locator("#stop").bounding_box()
                    if not box or box["y"] < 0 or box["y"] + box["height"] > height:
                        raise AssertionError("STOP is not fully in the viewport")
            print("Offline layout checked at 1440, 390, 320 px. No motion/hardware claims.")
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8783)
    parser.add_argument("--url", help="Native simulator URL (default http://127.0.0.1:<port>)")
    parser.add_argument("--output", type=Path, default=OPTIONS["output"])
    parser.add_argument("--only", help="Run tests whose names contain this text")
    parser.add_argument("--layout-only", action="store_true", help="Offline static layout only; no control behavior claims")
    args = parser.parse_args()
    OPTIONS.update(url=args.url or f"http://127.0.0.1:{args.port}", output=args.output)
    if args.layout_only:
        capture_static_layout()
        return 0
    loader = unittest.TestLoader()
    if args.only:
        loader.testNamePatterns = ["*" + args.only + "*"]
    result = unittest.TextTestRunner(verbosity=2).run(loader.loadTestsFromTestCase(DashboardTests))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
