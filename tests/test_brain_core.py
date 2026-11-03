"""Behavior tests execute the firmware's compiled C++ core, with an independent peer."""

import binascii
from pathlib import Path
import struct
import sys
import unittest
import random

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_brain_host import LIB, SOURCES, HEADERS, build
from brain_simulator import Rig, Brain, Motion, frame, decode


class BrainCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = SOURCES + HEADERS
        if not LIB.exists() or LIB.stat().st_mtime < max(
            p.stat().st_mtime for p in files
        ):
            build()

    def setUp(self):
        self.r = Rig()
        self.r.connect()

    def tearDown(self):
        self.r.brain.close()

    def arm(self, ai=False):
        if ai:
            self.r.brain.command(3, self.r.now, 1)
            self.r.mode(True)
        self.assertEqual(self.r.arm(), 0)
        self.assertTrue(self.r.state["authorized"])

    def test_boot_is_manual_disarmed(self):
        s = self.r.state
        self.assertEqual(s["mode"], "Manual")
        self.assertFalse(s["authorized"])
        self.assertEqual((s["v"], s["omega"]), (0, 0))

    def test_motion_reset_recovers_only_with_explicit_new_arm(self):
        self.arm(True)
        self.r.advance(1500000)
        self.r.motion = Motion()
        self.r.advance(160000)
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(self.r.state["motion_state"], 0)
        self.assertEqual(self.r.arm(), 0)
        self.assertTrue(self.r.state["authorized"])

    def test_arm_requires_motion_response(self):
        self.r.motion.online = False
        self.assertEqual(self.r.brain.command(5, self.r.now, self.r.state["epoch"]), 0)
        self.r.pump()
        self.assertFalse(self.r.state["authorized"])
        self.r.advance(150000)
        self.assertEqual(self.r.state["reason"], "motion_stale")

    def test_explicit_arm_rejection_is_reported_without_timeout(self):
        original = self.r.motion.receive

        def receive(data, now):
            kind, _, seq, _ = decode(data)
            if kind == 2:
                self.r.motion.last = seq
                self.r.motion.result = 5
            else:
                original(data, now)

        self.r.motion.receive = receive
        self.r.brain.command(5, self.r.now, self.r.state["epoch"])
        self.r.pump(50000)
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(self.r.state["reason"], "arm_rejected")

    def test_manual_directions_and_full_scale(self):
        self.arm()
        seq = 0
        for p in (0, 30, 100):
            for v, w in (
                (2 * p, 0),
                (-2 * p, 0),
                (2 * p, 10 * p),
                (2 * p, -10 * p),
                (0, 10 * p),
                (0, -10 * p),
            ):
                seq += 1
                self.assertEqual(self.r.move(seq, v, w), 0)
                self.r.pump()
                self.assertEqual((self.r.motion.v, self.r.motion.w), (v, w))

    def test_neutral_keeps_arm_stop_revokes(self):
        self.arm()
        self.r.move(1, 60, 0)
        self.r.pump()
        self.assertEqual(self.r.move(2, 0, 0, False), 0)
        self.r.pump()
        self.assertTrue(self.r.state["authorized"])
        self.assertEqual(self.r.motion.v, 0)
        old = self.r.state["epoch"]
        self.r.brain.command(6, self.r.now)
        self.r.pump()
        self.assertFalse(self.r.state["authorized"])
        self.assertNotEqual(old, self.r.state["epoch"])

    def test_manual_ttl_then_deadman_exact_boundary(self):
        self.arm()
        self.r.move(1, 60, 0)
        self.r.pump()
        self.r.advance(119999)
        self.assertEqual(self.r.state["v"], 60)
        self.r.advance(1)
        self.assertEqual(self.r.state["v"], 0)
        self.r.advance(29999)
        self.assertTrue(self.r.state["authorized"])
        self.r.advance(1)
        self.assertFalse(self.r.state["authorized"])

    def test_disconnect_manual_stops_ai_survives(self):
        self.arm()
        self.r.brain.command(2, self.r.now)
        self.r.pump()
        self.assertFalse(self.r.state["authorized"])
        self.r.connect()
        self.arm(True)
        self.r.brain.command(2, self.r.now)
        self.r.advance(200000)
        self.assertTrue(self.r.state["authorized"])
        self.assertEqual(self.r.state["mode"], "AI")

    def test_switch_requires_stop_ack_and_explicit_arm(self):
        self.arm()
        self.r.move(1, 60, 0)
        self.r.pump()
        old = self.r.state["epoch"]
        self.r.mode(True)
        self.assertFalse(self.r.state["authorized"])
        self.assertFalse(self.r.state["switching"])
        self.assertEqual(self.r.brain.command(8, self.r.now, old, 0, 30, 1000), 5)
        self.assertEqual(
            self.r.brain.command(7, self.r.now, old, 1, 2, 60, 0, 120, 1), 5
        )

    def test_switch_not_confirmed_by_unrelated_disarmed_status(self):
        self.r.brain.command(4, self.r.now, 1)
        data = self.r.brain.tx(self.r.now)
        self.assertEqual(decode(data)[0], 4)
        p = struct.pack("<HHBBHhhHHB", 65530, 65535, 0, 0, 0, 0, 0, 0, 65535, 0)
        self.r.brain.rx(self.r.now, frame(128, 0, 99, p))
        self.assertTrue(self.r.state["switching"])

    def test_stale_challenge_and_sequence_wrap(self):
        self.arm()
        epoch = self.r.state["epoch"]
        challenge = self.r.state["challenge"]
        self.assertEqual(self.r.move(0xFFFFFFFF, 1, 0), 0)
        self.r.pump()
        self.assertEqual(self.r.move(0, 2, 0), 0)
        self.assertEqual(self.r.move(0, 3, 0), 4)
        self.assertEqual(self.r.move(0x80000000, 3, 0), 4)
        self.r.advance(120000)
        self.assertEqual(self.r.move(1, 1, 0, epoch=epoch, challenge=challenge), 5)

    def test_invalid_commands_do_not_renew(self):
        self.arm()
        self.r.move(1, 60, 0)
        self.r.pump()
        for args in [
            (2, 201, 0, True, 120),
            (2, 0, 1001, True, 120),
            (2, 1, 0, False, 120),
            (2, 0, 0, True, 0),
            (2, 0, 0, True, 251),
        ]:
            self.assertNotEqual(self.r.move(*args), 0)
        self.r.advance(150000)
        self.assertFalse(self.r.state["authorized"])

    def test_voice_defaults_limits_and_exact_end(self):
        self.arm(True)
        e = self.r.state["epoch"]
        self.assertEqual(self.r.brain.command(8, self.r.now, e, 0, 30, 1000), 0)
        self.r.pump()
        self.r.advance(999999)
        self.assertEqual(self.r.state["v"], 60)
        self.r.advance(1)
        self.assertEqual(self.r.state["v"], 0)
        self.assertTrue(self.r.state["authorized"])
        for action, pct, duration in [
            (6, 30, 1000),
            (0, 101, 1000),
            (0, 30, 99),
            (0, 30, 3001),
        ]:
            self.assertEqual(
                self.r.brain.command(8, self.r.now, e, action, pct, duration), 3
            )

    def test_voice_new_target_replaces_old_duration(self):
        self.arm(True)
        e = self.r.state["epoch"]
        self.r.brain.command(8, self.r.now, e, 0, 100, 3000)
        self.r.advance(500000)
        self.r.brain.command(8, self.r.now, e, 1, 30, 1000)
        self.r.pump()
        self.assertEqual(self.r.state["v"], -60)
        self.r.advance(1000000)
        self.assertEqual(self.r.state["v"], 0)

    def test_voice_denied_in_manual(self):
        self.arm()
        self.assertEqual(
            self.r.brain.command(8, self.r.now, self.r.state["epoch"], 0, 30, 1000), 6
        )

    def test_grant_five_minutes_not_renewed(self):
        self.arm(True)
        start = self.r.now
        e = self.r.state["epoch"]
        self.r.advance(299000000)
        self.r.brain.command(8, self.r.now, e, 0, 30, 3000)
        self.r.advance(999999)
        self.assertTrue(self.r.state["authorized"])
        self.r.advance(1)
        self.assertEqual(self.r.now - start, 300000000)
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(self.r.state["v"], 0)

    def test_internet_loss_only_revokes_ai(self):
        self.arm()
        self.r.brain.command(3, self.r.now, 0)
        self.assertTrue(self.r.state["authorized"])
        self.r.brain.command(6, self.r.now)
        self.r.pump()
        self.arm(True)
        self.r.brain.command(3, self.r.now, 0)
        self.r.pump()
        self.assertFalse(self.r.state["authorized"])
        self.r.brain.command(3, self.r.now, 1)
        self.r.advance(50000)
        self.assertFalse(self.r.state["authorized"])

    def test_same_status_cannot_renew_link(self):
        self.arm()
        saved = self.r.motion.status(self.r.now, True)
        self.r.brain.rx(self.r.now, saved)
        self.r.motion.online = False
        for _ in range(29):
            self.r.pump(5000)
            self.r.brain.rx(self.r.now, saved)
        self.assertTrue(self.r.state["authorized"])
        self.r.pump(5000)
        self.assertFalse(self.r.state["authorized"])

    def test_fresh_status_at_timeout_boundary_cannot_revive_authority(self):
        self.arm(True)
        self.r.motion.online = False
        self.r.now += 150000
        self.r.motion.online = True
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual((self.r.state["v"], self.r.state["omega"]), (0, 0))

    def test_invalid_status_fields_do_not_renew_link(self):
        self.arm(True)
        self.r.motion.online = False
        session = self.r.motion.session
        for i in range(30):
            self.r.now += 5000
            result, state, flags = [(8, 2, 0), (0, 4, 0), (0, 2, 0x80)][i % 3]
            payload = struct.pack(
                "<HHBBHhhHHB", 0, 0, result, state, 0, 0, 0, 0, 65535, flags
            )
            self.r.brain.rx(self.r.now, frame(128, session, 100 + i, payload))
            self.r.brain.command(0, self.r.now)
        self.assertFalse(self.r.state["authorized"])

    def test_motion_reject_is_not_an_applied_command(self):
        self.arm(True)
        self.r.brain.command(8, self.r.now, self.r.state["epoch"], 0, 30, 1000)
        self.r.pump()
        p = struct.pack(
            "<HHBBHhhHHB", self.r.motion.last, 65535, 4, 2, 0, 0, 0, 0, 65535, 0
        )
        self.r.brain.rx(
            self.r.now, frame(128, self.r.motion.session, self.r.motion.seq + 1, p)
        )
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(self.r.state["applied_seq"], 65535)
        self.assertEqual(decode(self.r.brain.tx(self.r.now))[0], 4)

    def test_stop_wins_over_delayed_arm_ack(self):
        e = self.r.state["epoch"]
        self.assertEqual(self.r.brain.command(5, self.r.now, e), 0)
        hello = self.r.brain.tx(self.r.now)
        self.r.motion.receive(hello, self.r.now)
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        arm = self.r.brain.tx(self.r.now)
        self.assertEqual(decode(arm)[0], 2)
        self.r.brain.command(6, self.r.now)
        self.r.motion.receive(arm, self.r.now)
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(decode(self.r.brain.tx(self.r.now))[0], 4)
        self.assertEqual(self.r.brain.command(5, self.r.now, e), 5)

    def test_wrong_session_and_corrupt_crc_do_not_renew(self):
        self.arm()
        self.r.motion.online = False
        data = bytearray(
            self.r.motion.status(self.r.now, True) or frame(128, 42, 100, bytes(17))
        )
        for offset in range(len(data)):
            bad = bytearray(data)
            bad[offset] ^= 1
            self.r.brain.rx(self.r.now, bad)
        self.r.advance(150000)
        self.assertFalse(self.r.state["authorized"])

    def test_stop_wins_and_old_epoch_never_rearms(self):
        self.arm()
        e = self.r.state["epoch"]
        self.r.move(1, 60, 0)
        self.r.brain.command(6, self.r.now)
        self.assertEqual(decode(self.r.brain.tx(self.r.now))[0], 4)
        self.assertEqual(self.r.brain.command(5, self.r.now, e), 5)
        self.assertEqual(self.r.move(2, 60, 0, epoch=e), 5)

    def test_protocol_golden_and_corruption(self):
        expected = bytes.fromhex(
            "A5 5A 01 03 07 78 56 34 12 02 00 FA 00 90 01 02 78 00 76 9B"
        )
        self.assertEqual(
            frame(3, 0x12345678, 2, struct.pack("<hhBH", 250, 400, 2, 120)), expected
        )
        self.assertEqual(binascii.crc_hqx(b"123456789", 0xFFFF), 0x29B1)

    def test_parser_timeout_and_recovery(self):
        good = self.r.motion.status(self.r.now, True)
        before = self.r.state["rx_errors"]
        self.r.brain.rx(1, good[:7])
        self.r.brain.rx(10001, good[7:])
        self.assertGreater(self.r.brain.state(10001)["rx_errors"], before)
        self.r.brain.rx(10002, good)
        self.assertEqual(self.r.brain.state(10002)["telemetry_age_ms"], 0)

    def test_voice_gate_missing_wrong_and_valid_session(self):
        self.arm(True)
        b = self.r.brain
        n = self.r.now
        self.assertTrue(b.gate(0, n))
        b.gate(1, n)
        self.assertFalse(b.gate(2, n, 1, ""))
        self.assertFalse(b.gate(2, n, 1, "wrong"))
        self.assertTrue(b.gate(2, n, 1))
        self.assertTrue(b.gate(3, n, 1))
        self.assertFalse(b.gate(3, n, 1))

    def test_voice_gate_callback_deadline_and_stt_expiry(self):
        self.arm(True)
        b = self.r.brain
        b.gate(0, self.r.now)
        b.gate(1, self.r.now)
        self.assertTrue(b.gate(2, self.r.now))
        self.r.advance(119999)
        self.assertTrue(b.gate(3, self.r.now))
        b.gate(1, self.r.now)
        self.assertTrue(b.gate(2, self.r.now, 2))
        self.r.advance(120000)
        self.assertFalse(b.gate(3, self.r.now, 2))
        b.gate(1, self.r.now)
        self.r.advance(5000000)
        self.assertFalse(b.gate(2, self.r.now, 3))

    def test_voice_gate_stop_epoch_and_old_session_cannot_revive(self):
        self.arm(True)
        b = self.r.brain
        b.gate(0, self.r.now)
        b.gate(1, self.r.now)
        b.gate(2, self.r.now, 9)
        b.command(6, self.r.now)
        self.r.pump()
        self.assertFalse(b.gate(3, self.r.now, 9))
        self.assertFalse(b.gate(0, self.r.now, 1, "session-A"))
        self.assertTrue(b.gate(0, self.r.now, 1, "session-B"))
        b.gate(1, self.r.now, 1, "session-B")
        self.assertTrue(b.gate(2, self.r.now, 9, "session-B"))

    def test_voice_gate_duplicate_id_across_turns(self):
        self.arm(True)
        b = self.r.brain
        b.gate(0, self.r.now)
        b.gate(1, self.r.now)
        self.assertTrue(b.gate(2, self.r.now, 13))
        self.assertTrue(b.gate(3, self.r.now))
        b.gate(1, self.r.now)
        self.assertFalse(b.gate(2, self.r.now, 13))
        self.assertTrue(b.gate(2, self.r.now, 14))

    def test_voice_gate_old_stt_cannot_authorize_new_session(self):
        self.arm(True)
        b = self.r.brain
        b.gate(0, self.r.now)
        b.gate(1, self.r.now, 1, "wrong")
        self.assertFalse(b.gate(2, self.r.now))
        b.gate(1, self.r.now)
        b.gate(2, self.r.now)
        b.gate(0, self.r.now, 1, "session-B")
        self.assertFalse(b.gate(3, self.r.now))

    def test_web_clear_fault_opens_fresh_context_and_never_arms(self):
        self.arm()
        self.r.motion.fault = 4
        self.r.motion.state = 3
        self.r.pump(50000)
        epoch = self.r.state["epoch"]
        self.assertEqual(self.r.brain.command(9, self.r.now, epoch), 0)
        self.assertTrue(self.r.state["clearing"])
        self.r.pump()
        self.assertFalse(self.r.state["clearing"])
        self.assertFalse(self.r.state["authorized"])
        self.assertEqual(self.r.state["fault_flags"], 0)
        self.assertEqual(self.r.state["motion_state"], 0)
        self.assertEqual(self.r.state["reason"], "fault_cleared")
        self.assertNotEqual(self.r.state["epoch"], epoch)
        self.assertNotEqual(self.r.brain.command(9, self.r.now, epoch), 0)
        self.assertEqual(self.r.arm(), 0)
        self.assertTrue(self.r.state["authorized"])

    def test_clear_healthy_peer_is_rejected(self):
        self.assertNotEqual(self.r.brain.command(9, self.r.now, self.r.state["epoch"]), 0)
        self.assertFalse(self.r.state["clearing"])

    def test_clear_waits_for_exact_stop_ack_before_recovery_hello(self):
        self.r.motion.fault = 4
        self.r.motion.state = 3
        self.r.pump(50000)
        self.assertEqual(self.r.brain.command(9, self.r.now, self.r.state["epoch"]), 0)
        stop = self.r.brain.tx(self.r.now)
        self.assertEqual(decode(stop)[0], 4)
        self.assertFalse(self.r.brain.tx(self.r.now))
        self.r.motion.receive(stop, self.r.now)
        seq = self.r.motion.last
        self.r.motion.last = (seq - 1) & 65535
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        self.assertFalse(self.r.brain.tx(self.r.now))
        self.r.now += 50000
        self.r.brain.command(0, self.r.now)
        self.assertFalse(self.r.brain.tx(self.r.now))
        self.r.motion.last = seq
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        hello = self.r.brain.tx(self.r.now)
        self.assertEqual(decode(hello)[0], 1)
        self.r.motion.receive(hello, self.r.now)
        self.r.brain.rx(self.r.now, self.r.motion.status(self.r.now, True))
        self.r.pump()
        self.assertEqual(self.r.state["reason"], "fault_cleared")
        self.assertFalse(self.r.state["authorized"])

    def test_stop_cancels_clear_before_callback_can_progress(self):
        self.r.motion.fault = 4
        self.r.motion.state = 3
        self.r.pump(50000)
        self.assertEqual(self.r.brain.command(9, self.r.now, self.r.state["epoch"]), 0)
        self.r.brain.command(6, self.r.now)
        self.r.pump()
        self.assertFalse(self.r.state["clearing"])
        self.assertEqual(self.r.state["fault_flags"], 4)
        self.assertFalse(self.r.state["authorized"])

    def test_clear_stale_motion_fails_closed(self):
        self.r.motion.fault = 4
        self.r.motion.state = 3
        self.r.pump(50000)
        self.assertEqual(self.r.brain.command(9, self.r.now, self.r.state["epoch"]), 0)
        self.r.motion.online = False
        self.r.advance(150000)
        self.assertFalse(self.r.state["clearing"])
        self.assertFalse(self.r.state["authorized"])

    def test_clear_rejected_by_motion_does_not_clear_ui_fault(self):
        self.r.motion.fault = 4
        self.r.motion.state = 3
        self.r.pump(50000)
        original = self.r.motion.receive
        def receive(data, now):
            kind, _, seq, _ = decode(data)
            if kind == 5:
                self.r.motion.last = seq
                self.r.motion.result = 5
            else:
                original(data, now)
        self.r.motion.receive = receive
        self.r.brain.command(9, self.r.now, self.r.state["epoch"])
        self.r.pump()
        self.assertFalse(self.r.state["clearing"])
        self.assertEqual(self.r.state["reason"], "clear_rejected")
        self.assertEqual(self.r.state["fault_flags"], 4)

    def test_randomized_safety_invariants(self):
        rng = random.Random(0xAC419)
        seq = 0
        for _ in range(10000):
            choice = rng.randrange(8)
            if choice == 0:
                self.r.brain.command(6, self.r.now)
            elif choice == 1:
                self.r.mode(bool(rng.randrange(2)))
            elif choice == 2:
                self.r.brain.command(3, self.r.now, rng.randrange(2))
            elif choice == 3:
                self.r.arm()
            elif choice == 4:
                seq += 1
                self.r.move(seq, rng.randint(-230, 230), rng.randint(-1100, 1100))
            elif choice == 5:
                self.r.brain.command(
                    8, self.r.now, self.r.state["epoch"], rng.randrange(6), 30, 1000
                )
            elif choice == 6:
                self.r.brain.command(2, self.r.now)
            else:
                self.r.connect()
            self.r.pump(rng.randrange(5000))
            s = self.r.state
            if not s["authorized"]:
                self.assertEqual((s["v"], s["omega"]), (0, 0))
            self.assertLessEqual(abs(s["v"]), 200)
            self.assertLessEqual(abs(s["omega"]), 1000)


if __name__ == "__main__":
    unittest.main()
