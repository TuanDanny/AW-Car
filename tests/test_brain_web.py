"""HTTP/WebSocket contract tests against actual host C++ core (optional dev deps)."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import unittest

HAVE_WEB = importlib.util.find_spec("aiohttp") is not None
if HAVE_WEB:
    import aiohttp
    from aiohttp.test_utils import TestServer, TestClient

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
    from simulator import Simulator


@unittest.skipUnless(
    HAVE_WEB, "Install dashboard/requirements-dev.txt to run Web integration tests"
)
class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.received = []
        # Functional HTTP cases control time explicitly. The separate soak uses
        # a real monotonic clock and measures scheduling delays under load.
        self.sim = Simulator("123456", realtime=False)
        self.client = TestClient(TestServer(self.sim.app()))
        await self.client.start_server()
        self.origin = str(self.client.make_url("/")).rstrip("/")

    async def asyncTearDown(self):
        await self.client.close()
        self.sim.rig.brain.close()

    async def login(self):
        r = await self.client.post("/api/login", json={"pin": "123456"})
        self.assertEqual(r.status, 200)

    async def connect(self):
        await self.login()
        return await self.client.ws_connect("/ws", origin=self.origin)

    async def receive(self, ws, kind):
        for _ in range(30):
            m = await ws.receive_json(timeout=1)
            self.received.append(m)
            if m.get("type") == kind:
                return m
        self.fail("missing " + kind)

    async def arm(self, ws, ai=False):
        s = await self.receive(ws, "STATUS")
        if ai:
            await ws.send_json(
                {"type": "SET_MODE", "mode": "AI", "epoch": s["epoch"], "seq": 1}
            )
            s = await self.receive(ws, "STATUS")
            while s["mode"] != "AI" or s["switching"]:
                s = await self.receive(ws, "STATUS")
        await ws.send_json({"type": "ARM", "epoch": s["epoch"], "seq": 2})
        for _ in range(10):
            s = await self.receive(ws, "STATUS")
            if s["authorized"]:
                return s
        self.fail("Motion did not confirm ARM: " + str(s))

    async def test_session_preflight_reports_auth_and_busy(self):
        r = await self.client.post("/api/session", headers={"Origin": self.origin})
        self.assertEqual(r.status, 401)
        await self.login()
        r = await self.client.post("/api/session", headers={"Origin": self.origin})
        self.assertEqual(r.status, 200)
        ws = await self.client.ws_connect("/ws", origin=self.origin)
        r = await self.client.post("/api/session", headers={"Origin": self.origin})
        self.assertEqual(r.status, 409)
        await ws.close()

    async def test_motion_deadman_150ms_is_independent_of_socket_2s(self):
        ws = await self.connect()
        await self.arm(ws)
        await self.client.post("/api/lab", json={"op":"advance", "ms":600})
        self.assertFalse(self.sim.rig.state["authorized"])
        self.assertFalse(ws.closed)
        await ws.send_json({"type":"HEARTBEAT"})
        self.assertEqual((await self.receive(ws,"ACK"))["result"],"OK")
        self.assertFalse(self.sim.rig.state["authorized"])

    async def test_socket_watchdog_produces_reason_without_auto_arm(self):
        ws = await self.connect()
        await self.receive(ws,"STATUS")
        await self.client.post("/api/lab", json={"op":"advance", "ms":2000})
        for _ in range(30):
            msg = await ws.receive(timeout=1)
            if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                break
        self.assertEqual(ws.close_code,1001)
        self.assertFalse(self.sim.rig.state["authorized"])

    async def test_assets_and_unknown_measurements(self):
        for path in ("/", "/app.mjs", "/control.mjs", "/connection.mjs", "/style.css"):
            r = await self.client.get(path)
            self.assertEqual(r.status, 200)
        ws = await self.connect()
        s = await self.receive(ws, "STATUS")
        self.assertEqual(s["mode"], "Manual")
        self.assertIsNone(s["v_est_mm_s"])
        self.assertIsNone(s["battery_mv"])
        self.assertEqual(s["data_source"], "mock")

    async def test_os_memory_sampler_does_not_report_a_false_zero(self):
        await self.login()
        await self.client.post("/api/lab", json={"op": "advance", "ms": 5000})
        for _ in range(20):
            if self.sim.memory_samples:
                break
            await asyncio.sleep(0.005)
        self.assertTrue(self.sim.memory_samples)
        self.assertGreater(self.sim.memory_samples[-1][1], 0)

    async def test_auth_origin_and_exclusive_websocket(self):
        r = await self.client.post("/api/login", json={"pin": "wrong"})
        self.assertEqual(r.status, 403)
        await self.login()
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.client.ws_connect("/ws", origin="https://other.invalid")
        ws = await self.client.ws_connect("/ws", origin=self.origin)
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.client.ws_connect("/ws", origin=self.origin)
        r = await self.client.post("/api/login", json={"pin": "123456"})
        self.assertEqual(r.status, 409)
        await ws.close()

    async def test_move_neutral_stop_and_epoch(self):
        ws = await self.connect()
        s = await self.arm(ws)
        move = {
            "type": "MOVE",
            "seq": 3,
            "epoch": s["epoch"],
            "challenge": s["challenge"],
            "v_mm_s": 60,
            "omega_mrad_s": 0,
            "ttl_ms": 120,
            "deadman": True,
        }
        await ws.send_json(move)
        a = await self.receive(ws, "ACK")
        self.assertEqual(a["result"], "OK")
        self.assertEqual(self.sim.rig.motion.v, 60)
        await ws.send_json({**move, "seq": 4, "v_mm_s": 0, "deadman": False})
        a = await self.receive(ws, "ACK")
        self.assertEqual(a["result"], "OK")
        self.assertTrue(self.sim.rig.state["authorized"])
        self.assertEqual(self.sim.rig.motion.v, 0)
        await ws.send_json({"type": "STOP"})
        await self.receive(ws, "ACK")
        self.assertFalse(self.sim.rig.state["authorized"])
        await ws.send_json({**move, "seq": 5})
        self.assertEqual((await self.receive(ws, "ACK"))["result"], "STALE")

    async def test_wrong_json_types_and_range(self):
        ws = await self.connect()
        s = await self.arm(ws)
        base = {
            "type": "MOVE",
            "seq": 3,
            "epoch": s["epoch"],
            "challenge": s["challenge"],
            "v_mm_s": 60,
            "omega_mrad_s": 0,
            "ttl_ms": 120,
            "deadman": True,
        }
        for update in (
            {"seq": True},
            {"v_mm_s": 1.5},
            {"deadman": 1},
            {"ttl_ms": 251},
            {"v_mm_s": 201},
        ):
            await ws.send_json({**base, **update})
            self.assertNotEqual((await self.receive(ws, "ACK"))["result"], "OK")

    async def test_web_disconnect_manual_vs_ai(self):
        ws = await self.connect()
        await self.arm(ws)
        await ws.close()
        await asyncio.sleep(0.02)
        self.assertFalse(self.sim.rig.state["authorized"])
        ws = await self.connect()
        await self.arm(ws, True)
        await ws.close()
        await asyncio.sleep(0.2)
        self.assertTrue(self.sim.rig.state["authorized"])

    async def test_ai_tool_motion_loss_and_no_auto_rearm(self):
        ws = await self.connect()
        await self.arm(ws, True)
        r = await self.client.post(
            "/api/lab", json={"op": "voice", "action": "backward"}
        )
        self.assertEqual((await r.json())["result"], "OK")
        self.assertEqual(self.sim.rig.state["v"], -60)
        await self.client.post(
            "/api/lab", json={"op": "motion_online", "online": False}
        )
        await self.client.post("/api/lab", json={"op": "advance", "ms": 180})
        self.assertFalse(self.sim.rig.state["authorized"])
        await self.client.post("/api/lab", json={"op": "motion_online", "online": True})
        await asyncio.sleep(0.06)
        self.assertFalse(self.sim.rig.state["authorized"])

    async def test_rgb_and_chat_work_in_manual(self):
        ws = await self.connect()
        await self.receive(ws, "STATUS")
        await ws.send_json({"type": "RGB", "r": 255, "g": 0, "b": 0})
        self.assertEqual((await self.receive(ws, "ACK"))["result"], "OK")
        self.assertEqual(self.sim.rgb, {"power": True, "r": 255, "g": 0, "b": 0})
        await ws.send_json({"type": "CHAT_TOGGLE"})
        self.assertEqual((await self.receive(ws, "ACK"))["result"], "OK")
        await self.receive(ws, "EVENT")
        self.assertTrue(any(m.get("kind") == "rgb" for m in self.received))

    async def test_bad_payload_does_not_crash_server(self):
        ws = await self.connect()
        await self.receive(ws, "STATUS")
        for text in ("[]", "null", "{", '"MOVE"'):
            await ws.send_str(text)
            self.assertEqual((await self.receive(ws, "ACK"))["result"], "BAD_RANGE")

    async def test_wifi_only_disarmed(self):
        ws = await self.connect()
        await self.arm(ws)
        r = await self.client.post(
            "/api/wifi", json={"ssid": "test-only", "password": "not-a-real-secret"}
        )
        self.assertEqual(r.status, 409)


if __name__ == "__main__":
    unittest.main()
