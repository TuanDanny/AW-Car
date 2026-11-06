"""Safety and movement regressions run the production C++ Motion code."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_motion_host import build
from motion_simulator import Rig, Motion, Fpga, frame, decode


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setUp(self):
        self.r = Rig()

    def tearDown(self):
        self.r.close()

    def armed(self):
        self.assertEqual(self.r.arm()["state"], 2, self.r.view)

    def rest(self):
        self.r.drive(600, 0)

    def test_boot_no_fake_measurements(self):
        self.assertFalse(self.r.view["driver"])
        self.assertEqual(self.r.view["state"], 0)
        payload = self.r.statuses[-1][4]
        self.assertEqual(payload[8:14], bytes(6))
        self.assertEqual(payload[16] & 7, 0)

    def test_unvalidated_configuration_cannot_arm(self):
        self.assertTrue(self.r.motion.configure("validated", 0, self.r.now))
        self.assertEqual(self.r.arm()["state"], 0)
        self.assertEqual(self.r.view["result"], 5)

    def test_arm_requires_real_pending_status_and_gpio_sequence(self):
        self.armed()
        kinds = [h[1] for h in self.r.fpga.history]
        self.assertLess(kinds.index(1), kinds.index(2))
        self.assertTrue(self.r.view["driver"])
        self.assertEqual(self.r.view["applied"], 65535)
        self.assertFalse(self.r.view["lease"])

    def test_first_twist_required_after_arm(self):
        self.armed()
        self.r.advance(150)
        self.assertFalse(self.r.view["driver"])
        self.assertEqual(self.r.view["state"], 0)

    def test_six_directions_signed_and_bounded(self):
        for v, omega, direction in ((60, 0, 0), (-60, 0, 3), (60, 300, 0),
                                     (60, -300, 0), (0, 300, 1), (0, -300, 2)):
            with self.subTest(v=v, omega=omega):
                rig = Rig()
                try:
                    self.assertEqual(rig.arm()["state"], 2)
                    rig.send(3, v, omega)
                    rig.advance(2)
                    s = rig.view
                    self.assertEqual(s["dir"], direction)
                    self.assertGreater(max(s["left"], s["right"]), 0)
                    self.assertLessEqual(max(s["left"], s["right"]), 1350)
                    if omega > 0 and v > 0:
                        self.assertLess(s["left"], s["right"])
                    if omega < 0 and v > 0:
                        self.assertGreater(s["left"], s["right"])
                finally:
                    rig.close()

    def test_wheel_saturation_preserves_ratio(self):
        self.armed()
        self.r.send(3, 200, 1000)
        self.r.advance(1)
        s = self.r.view
        self.assertEqual(s["right"], 1350)
        self.assertAlmostEqual(s["left"] / s["right"], 140 / 260, delta=.01)

    def test_neutral_holds_arm_stop_revokes_and_does_not_fault(self):
        self.armed()
        self.r.drive(100, 60)
        self.r.send(3, 0)
        self.r.advance(1)
        self.assertEqual(self.r.view["state"], 2)
        self.assertEqual(self.r.view["left"], 0)
        self.r.send(4)
        self.assertFalse(self.r.view["driver"])
        self.assertTrue(self.r.view["permit"])
        self.r.advance(25)
        self.assertEqual(self.r.view["state"], 0)
        self.assertEqual(self.r.view["fault"], 0)
        self.assertEqual(self.r.fpga.fault, 0)
        self.assertFalse(self.r.view["permit"])
        self.assertEqual(self.r.view["result"], 0)

    def test_stop_accepted_with_foreign_session_old_sequence(self):
        self.armed()
        self.r.send(3, 60)
        epoch = self.r.view["epoch"]
        self.r.send(4, session=0xdeadbeef, seq=0)
        self.assertGreater(self.r.view["epoch"], epoch)
        self.assertFalse(self.r.view["driver"])
        self.r.advance(25)
        self.assertEqual(self.r.view["fault"], 0)

    def test_move_and_arm_after_stop_do_not_revive_context(self):
        self.armed()
        self.r.send(4)
        self.r.send(3, 200)
        self.r.send(2)
        self.r.advance(30)
        self.assertFalse(self.r.view["driver"])
        self.assertEqual(self.r.view["left"], 0)
        self.assertEqual(self.r.arm()["state"], 2)

    def test_repeated_stop_does_not_extend_disable_deadline(self):
        self.armed()
        self.r.fpga.online = False
        self.r.fpga.pending.clear()
        self.r.send(4)
        for _ in range(4):
            self.r.advance(10)
            self.r.send(4)
        self.assertEqual(self.r.view["state"], 3)
        self.assertFalse(self.r.view["permit"])

    def test_kick_decays_without_restart_from_20hz_messages(self):
        self.armed()
        self.rest()
        self.r.send(3, 60)
        self.r.advance(1)
        a = self.r.view["left"]
        self.r.drive(99, 60)
        b = self.r.view["left"]
        self.r.drive(100, 60)
        c = self.r.view["left"]
        self.assertGreater(a, 1300)
        self.assertTrue(800 < b < 950, b)
        self.assertEqual(c, 405)

    def test_low_speed_has_reduced_kick(self):
        self.armed()
        self.rest()
        self.r.send(3, 10)
        self.r.advance(1)
        self.assertTrue(150 < self.r.view["left"] < 250)

    def test_kick_keeps_turn_ratio_and_zero_side_zero(self):
        self.armed()
        self.rest()
        self.r.send(3, 60, 1000)
        self.r.advance(1)
        self.assertEqual(self.r.view["left"], 0)
        self.assertGreater(self.r.view["right"], 1300)

    def test_release_and_stop_cancel_kick_immediately(self):
        self.armed()
        self.rest()
        self.r.send(3, 60)
        self.r.advance(1)
        self.r.send(3, 0)
        self.r.advance(1)
        self.assertEqual(self.r.view["left"], 0)
        self.r.send(3, 60)
        self.r.advance(1)
        self.assertEqual(self.r.view["phase"], 2)  # No rested retrigger.
        self.r.send(4)
        self.assertFalse(self.r.view["driver"])

    def test_reverse_wait_latest_target_then_changes_direction(self):
        self.armed()
        self.r.fpga.edges = True
        self.r.drive(100, 60)
        self.r.fpga.edges = False
        self.r.send(3, -60)
        self.r.advance(1)
        self.assertEqual(self.r.view["phase"], 3)
        self.assertEqual(self.r.view["left"], 0)
        self.r.drive(600, -60)
        self.assertEqual(self.r.view["dir"], 3)
        self.assertGreater(self.r.view["left"], 0)

    def test_reverse_wait_cancelled_by_short_ai_expiry(self):
        self.armed()
        self.r.fpga.edges = True
        self.r.drive(100, 60)
        self.r.send(3, -60, source=1)
        self.r.advance(100)
        self.r.send(3, 0, source=1)
        self.r.drive(700, 0)
        self.assertEqual(self.r.view["left"], 0)
        self.assertEqual(self.r.view["state"], 2)

    def test_reverse_timeout_latches_fault_and_never_forces_direction(self):
        self.armed()
        self.r.fpga.edges = self.r.fpga.rolling = True
        self.r.drive(100, 60)
        self.assertGreater(self.r.fpga.count[0], 0)
        self.assertTrue(self.r.view["speeds_valid"])
        self.r.drive(1550, -60)
        self.assertEqual(self.r.view["state"], 3)
        self.assertTrue(self.r.view["fault"] & 256)
        self.assertFalse(self.r.view["driver"])

    def test_no_edges_stops_both_sides_no_automatic_retry(self):
        self.armed()
        self.r.drive(1000, 60)
        self.assertTrue(self.r.view["fault"] & 4)
        self.assertFalse(self.r.view["driver"])
        self.assertEqual(self.r.view["left"], 0)

    def test_fpga_stale_or_duplicate_status_stops_independently(self):
        for duplicate in (False, True):
            rig = Rig()
            try:
                rig.arm()
                rig.send(3, 60)
                if duplicate:
                    rig.fpga.progress = False
                else:
                    rig.fpga.online = False
                    rig.fpga.pending.clear()
                rig.advance(45)
                self.assertTrue(rig.view["fault"] & 2, rig.view)
                self.assertFalse(rig.view["driver"])
            finally:
                rig.close()

    def test_expiry_wins_frame_at_exact_ttl_boundary(self):
        self.armed()
        self.r.send(3, 60, ttl=50)
        self.r.advance(49)
        self.assertEqual(self.r.view["state"], 2)
        self.r.advance(1)
        self.r.send(3, 60)
        self.assertFalse(self.r.view["driver"])

    def test_bad_range_source_ttl_session_and_duplicate_do_not_apply(self):
        self.armed()
        self.r.send(3, 60)
        applied = self.r.view["applied"]
        for kwargs in ({"v": 201}, {"omega": 1001}, {"ttl": 0}, {"ttl": 251},
                       {"source": 0}, {"session": 0xeeee}, {"seq": applied}):
            self.r.send(3, **kwargs)
            self.assertEqual(self.r.view["applied"], applied)
            self.assertNotEqual(self.r.view["result"], 0)

    def test_crc_error_does_not_trip_or_renew_lease(self):
        self.armed()
        self.r.send(3, 60, ttl=80)
        data = bytearray(frame(1, 3, self.r.session, 100, struct.pack("<hhBH", 200, 0, 2, 250)))
        data[-1] ^= 1
        self.r.advance(40)
        self.r.motion.receive(1, bytes(data), self.r.now)
        self.assertEqual(self.r.view["state"], 2)
        self.assertGreater(self.r.view["brain_errors"], 0)
        self.r.advance(40)
        self.assertFalse(self.r.view["driver"])

    def test_local_boot_stop_and_gate_fault(self):
        self.armed()
        self.r.motion.lib.motion_stop(self.r.motion.ptr, self.r.now)
        self.assertFalse(self.r.view["driver"])
        self.r.advance(25)
        self.assertEqual(self.r.view["fault"], 0)
        self.r.arm()
        self.r.inputs_override = 0
        self.r.advance(1)
        self.assertTrue(self.r.view["fault"] & 1)

    def test_clear_fault_returns_disarmed_requires_new_hello_arm(self):
        self.armed()
        self.r.motion.lib.motion_fault(self.r.motion.ptr, 4, self.r.now)
        self.r.advance(30)
        self.r.session += 1
        self.r.send(1)
        self.r.advance(5)
        self.assertEqual(self.r.view["result"], 0)
        self.r.send(5)
        self.r.advance(90)
        self.assertEqual(self.r.view["fault"], 0, self.r.view)
        self.assertEqual(self.r.view["state"], 0)
        self.assertFalse(self.r.view["driver"])
        self.r.send(2)
        self.assertNotEqual(self.r.view["result"], 0)
        self.assertEqual(self.r.arm()["state"], 2)

    def test_diagnostics_warnings_are_not_motion_faults_reset_bits_are(self):
        self.armed()
        self.r.fpga.fault = 0x1700
        self.r.advance(20)
        self.assertEqual(self.r.view["fault"], 0)
        self.r.fpga.fault |= 0x0800
        self.r.advance(20)
        self.assertTrue(self.r.view["fault"] & 128)
        self.r.session += 1
        self.r.send(1)
        self.r.send(5)
        self.assertEqual(self.r.view["result"], 5)

    def test_tuning_rejected_armed_and_invalid_parameters(self):
        self.assertFalse(self.r.motion.configure("pulses_per_rev", 0, self.r.now))
        self.assertFalse(self.r.motion.configure("duty_limit", 1351, self.r.now))
        self.assertTrue(self.r.motion.configure("track_mm", 130, self.r.now))
        self.armed()
        self.assertFalse(self.r.motion.configure("track_mm", 140, self.r.now))

    def test_sequence_wrap(self):
        self.r.seq = 65534
        self.armed()
        self.r.send(3, -60)
        self.assertEqual(self.r.view["result"], 0)
        self.assertEqual(self.r.view["applied"], 1)

    def test_parser_version_length_fragment_timeout_noise_recovery(self):
        m = self.r.motion
        for data in (bytes(1000), frame(2, 1, 12, 1), b"\xa5\x5a\x01\x03\xff"):
            m.receive(1, data, self.r.now)
        hello = frame(1, 1, 12345, 1)
        m.receive(1, hello[:7], self.r.now)
        self.r.advance(11)
        m.receive(1, hello[7:], self.r.now)
        m.receive(1, hello, self.r.now)
        self.assertEqual(self.r.view["last_req"], 1)
        self.assertEqual(self.r.view["result"], 0)
        self.assertFalse(self.r.view["driver"])

    def test_snapshot_sequence_and_timestamp_wrap(self):
        m = Motion()
        try:
            for now, seq, ticks in ((0, 65535, 0xfffff000), (1000, 0, 0x00005978)):
                m.tick(now)
                payload = struct.pack("<IIIHBHBIIII", 0xffffffff, 0, ticks,
                                      seq, 0, 0, 0x1c, 0, 0, 0xffffffff, 0xffffffff)
                m.receive(2, frame(2, 128, 0, seq, payload), now)
                self.assertTrue(m.view(now)["fresh"])
        finally:
            m.close()

    def test_idle_fpga_reboot_rebaselines_counter_phases_after_progressing_samples(self):
        for old_seq, old_ticks in ((1000, 0x10000000), (1000, 0x90000000),
                                   (35000, 0x90000000), (65000, 0xf0000000)):
            with self.subTest(old_seq=old_seq, old_ticks=old_ticks):
                m = Motion(False)
                def send(now, seq, ticks):
                    m.tick(now, 0)
                    p = struct.pack("<IIIHBHBIIII", 0, 0, ticks, seq, 0, 0,
                                    0x1c, 0, 0, 0xffffffff, 0xffffffff)
                    m.receive(2, frame(2, 128, 0, seq, p), now)
                try:
                    send(10000, old_seq, old_ticks)
                    self.assertTrue(m.view(10000)["fresh"])
                    m.tick(50000, 0)
                    self.assertFalse(m.view(50000)["fresh"])
                    send(60000, 1, 270000)
                    if old_seq == 1000:
                        self.assertFalse(m.view(60000)["fresh"])
                    send(70000, 2, 540000)
                    self.assertTrue(m.view(70000)["fresh"])
                    self.assertEqual(m.view(70000)["state"], 0)
                    self.assertFalse(m.view(70000)["driver"])
                finally:
                    m.close()

    def test_reboot_discovery_does_not_refresh_from_duplicate_or_sparse_candidates(self):
        m = Motion(False)
        def send(now, seq, ticks):
            m.tick(now, 0)
            p = struct.pack("<IIIHBHBIIII", 0, 0, ticks, seq, 0, 0,
                            0x1c, 0, 0, 0xffffffff, 0xffffffff)
            m.receive(2, frame(2, 128, 0, seq, p), now)
        try:
            send(10000, 1000, 0x90000000)
            for now in (60000, 70000, 80000):
                send(now, 1, 270000)
                self.assertFalse(m.view(now)["fresh"])
            send(120000, 2, 540000)
            self.assertFalse(m.view(120000)["fresh"])
            send(130000, 3, 810000)
            self.assertTrue(m.view(130000)["fresh"])
            self.assertFalse(m.view(130000)["driver"])
        finally:
            m.close()

    def test_reboot_discovery_keeps_existing_motion_fault_latched(self):
        m = Motion(False)
        def send(now, seq, ticks, state, fault):
            m.tick(now, 0)
            p = struct.pack("<IIIHBHBIIII", 0, 0, ticks, seq, state, fault,
                            0x1c, 0, 0, 0xffffffff, 0xffffffff)
            m.receive(2, frame(2, 128, 0, seq, p), now)
        try:
            send(10000, 1000, 0x90000000, 4, 2)
            self.assertEqual(m.view(10000)["state"], 3)
            send(60000, 1, 270000, 0, 0)
            send(70000, 2, 540000, 0, 0)
            v = m.view(70000)
            self.assertTrue(v["fresh"])
            self.assertEqual(v["state"], 3)
            self.assertTrue(v["fault"] & 1)
            self.assertFalse(v["driver"])
        finally:
            m.close()

    def test_reboot_discovery_candidate_deadline_is_strict(self):
        for gap, accepted in ((29999, True), (30000, False)):
            with self.subTest(gap=gap):
                m = Motion(False)
                def send(now, seq, ticks):
                    m.tick(now, 0)
                    p = struct.pack("<IIIHBHBIIII", 0, 0, ticks, seq, 0, 0,
                                    0x1c, 0, 0, 0xffffffff, 0xffffffff)
                    m.receive(2, frame(2, 128, 0, seq, p), now)
                try:
                    send(10000, 1000, 0x90000000)
                    send(60000, 1, 270000)
                    self.assertFalse(m.view(60000)["fresh"])
                    send(60000 + gap, 2, 540000)
                    self.assertEqual(m.view(60000 + gap)["fresh"], accepted)
                    self.assertFalse(m.view(60000 + gap)["driver"])
                finally:
                    m.close()

    def test_armed_link_does_not_use_session_zero_discovery_to_extend_freshness(self):
        self.armed()
        m, start = self.r.motion, self.r.now
        for delta, seq in ((1000, 1), (11000, 2)):
            p = struct.pack("<IIIHBHBIIII", 0, 0, seq*270000, seq, 3, 0,
                            0x1c, 0, 0, 0xffffffff, 0xffffffff)
            m.receive(2, frame(2, 128, 0, seq, p), start+delta)
        for delta in range(12000, 40001, 1000):
            m.tick(start+delta, 15)
        v = m.view(start+40000)
        self.assertFalse(v["driver"])
        self.assertTrue(v["fault"] & 2)

    def test_control_stall_cannot_be_hidden_by_uart_task(self):
        self.armed()
        self.r.send(3, 60)
        self.r.advance(1)
        self.r.motion.tx(2, self.r.now + 20000)
        self.assertTrue(self.r.view["fault"] & 128)
        self.assertFalse(self.r.view["driver"])

    def test_idle_stop_without_fpga_is_idempotent_and_does_not_invent_fault(self):
        m = Motion(False)
        try:
            m.tick(0, 0)
            m.receive(1, frame(1, 4, 0, 1), 0)
            for i in range(1, 80):
                m.tick(i * 1000, 0)
            self.assertEqual(m.view(79000)["state"], 0)
            self.assertEqual(m.view(79000)["fault"], 0)
        finally:
            m.close()

    def test_idle_duplicate_snapshots_do_not_refresh_freshness(self):
        self.r.fpga.progress = False
        self.r.advance(60)
        self.assertFalse(self.r.view["fresh"])

    def test_encoder_count_wrap_does_not_create_fault(self):
        self.armed()
        self.r.fpga.edges = True
        self.r.fpga.count = [0xfffffff8, 0xfffffff8]
        self.r.drive(500, 60)
        self.assertLess(self.r.fpga.count[0], 100)
        self.assertEqual(self.r.view["fault"], 0)


if __name__ == "__main__":
    unittest.main()
