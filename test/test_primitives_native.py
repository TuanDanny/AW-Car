"""Execute firmware C++ and compare with independent Python model/geometry.

Never opens COM/OTA/JTAG. Fraction arithmetic keeps half-tick rounding explicit.
"""
import ctypes
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "utils"))
from build_host import build, compiler
from motion_primitives_sim import KickEnvelope, PRIMITIVES

NAMES = ("neutral", "forward", "backward", "left", "right", "forward_left",
         "forward_right", "backward_left", "backward_right", "pivot_left", "pivot_right")
MODEL_NAMES = ("stop", "forward", "backward", "spin_left", "spin_right",
               "arc_forward_left", "arc_forward_right", "arc_reverse_yaw_left",
               "arc_reverse_yaw_right", "pivot_left", "pivot_right")


class NativePrimitives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest = build(run=False)
        cls.dll_directory = os.add_dll_directory(str(compiler().parent)) if os.name == "nt" else None
        cls.dll = ctypes.CDLL(manifest["library"])
        cls.dll.car_create.argtypes = [ctypes.c_uint]
        cls.dll.car_create.restype = ctypes.c_void_p
        cls.dll.car_create_startup.argtypes = [ctypes.c_uint] * 3
        cls.dll.car_create_startup.restype = ctypes.c_void_p
        cls.dll.car_destroy.argtypes = [ctypes.c_void_p]
        cls.dll.car_event.argtypes = [ctypes.c_void_p] + [ctypes.c_uint]*5 + [ctypes.c_ulonglong]
        cls.dll.car_state.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_ulonglong]
        for name in ("primitive_left", "primitive_right"):
            getattr(cls.dll, name).argtypes = [ctypes.c_uint]*2
            getattr(cls.dll, name).restype = ctypes.c_int
        cls.dll.envelope_create.argtypes = [ctypes.c_uint]*2
        cls.dll.envelope_create.restype = ctypes.c_void_p
        cls.dll.envelope_destroy.argtypes = [ctypes.c_void_p]
        cls.dll.envelope_reset.argtypes = [ctypes.c_void_p]
        cls.dll.envelope_sample.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                           ctypes.c_ulonglong, ctypes.POINTER(ctypes.c_int)]

    def car(self, startup=False):
        p = self.dll.car_create_startup(500, 167, 100) if startup else self.dll.car_create(500)
        self.addCleanup(self.dll.car_destroy, p)
        return p

    def event(self, p, kind, now, a=0, b=0, duration=0, generation=0):
        return self.dll.car_event(p, kind, a, b, duration, generation, now)

    def links(self, p, now):
        self.event(p, 6, now)
        self.event(p, 5, now, a=3)

    def state(self, p, now):
        out = ctypes.create_string_buffer(2048)
        size = self.dll.car_state(p, out, len(out), now)
        self.assertLess(size, len(out))
        return json.loads(out.value)

    def test_all_1111_action_speed_pairs_against_fraction_reference(self):
        for action, model_name in enumerate(MODEL_NAMES):
            for speed in range(101):
                expected = []
                for fraction in PRIMITIVES[model_name]:
                    exact = Fraction(str(fraction))/Fraction("0.3") * speed*1350/100
                    magnitude = abs(exact)
                    rounded = (2*magnitude.numerator + magnitude.denominator)//(2*magnitude.denominator)
                    expected.append(rounded if exact >= 0 else -rounded)
                got = [self.dll.primitive_left(action, speed), self.dll.primitive_right(action, speed)]
                self.assertEqual(got, expected, (NAMES[action], speed))
        self.assertEqual(self.dll.primitive_left(11, 100), 0)
        self.assertEqual(self.dll.primitive_right(1, 101), 0)

    def test_all_actions_manual_and_ai_preserve_deadlines(self):
        for action in range(1, 11):
            for ai in (False, True):
                with self.subTest(action=NAMES[action], ai=ai):
                    p = self.car(); self.links(p, 100)
                    if ai: self.event(p, 2, 100, a=1)
                    generation = self.state(p, 100)["generation"]
                    accepted = self.event(p, 7 if ai else 1, 100, a=action, b=30, duration=3000, generation=generation)
                    self.assertEqual(accepted, 1)
                    self.event(p, 0, 100); self.event(p, 0, 101)
                    s = self.state(p, 101)
                    self.assertEqual((s["left"], s["right"]),
                                     (self.dll.primitive_left(action, 30), self.dll.primitive_right(action, 30)))
                    self.assertEqual(s["action"], NAMES[action])
                    self.assertFalse(s["startup"]["enabled"])
                    deadline = 3100 if ai else 600
                    for now in range(200, deadline, 100):
                        self.links(p, now); self.event(p, 0, now)
                    self.links(p, deadline); self.event(p, 0, deadline)
                    s = self.state(p, deadline)
                    self.assertEqual((s["left"], s["right"]), (0, 0))
                    self.assertEqual(s["reason"], "ai_complete" if ai else "manual_timeout")

    def test_cpp_envelope_vs_python_time_and_ratio(self):
        max_error = 0
        for target in ((405, 203), (-405, -203), (-405, 405), (0, 405), (1350, 675)):
            p = self.dll.envelope_create(167, 100)
            self.addCleanup(self.dll.envelope_destroy, p)
            reference = KickEnvelope(tau=.1, gain=1.67)
            reference.command(tuple(v/1350 for v in target), 0)
            out = (ctypes.c_int * 2)()
            for ms in (0, 1, 5, 50, 100, 137, 200, 300, 499, 500, 999):
                self.dll.envelope_sample(p, *target, ms, out)
                expected = reference.sample(ms/1000)
                max_error = max(max_error, *(abs(out[i]-1350*expected[i]) for i in range(2)))
                self.assertTrue(all(abs(v)<=1350 for v in out))
                self.assertLessEqual(abs(out[0]*target[1]-out[1]*target[0]), abs(target[0])+abs(target[1]))
                if ms >= 500: self.assertEqual(tuple(out), target)
            self.dll.envelope_sample(p, 0, 0, 1000, out)
            self.assertEqual(tuple(out), (0, 0))
        self.assertLessEqual(max_error, .501)
        print(f"C++ envelope vs Python: max_error={max_error:.6f} PWM ticks")

    def test_refresh_does_not_restart_kick_and_stop_cancels_it(self):
        p = self.car(startup=True); self.links(p, 100)
        self.event(p, 1, 100, a=5, b=30); self.event(p, 0, 100); self.event(p, 0, 101)
        self.assertEqual(self.state(p, 101)["left"], 339) # 203 * 1.67, half away from zero
        previous = math.inf
        for now in range(151, 652, 50):
            self.links(p, now); self.event(p, 1, now, a=5, b=30); self.event(p, 0, now)
            s = self.state(p, now)
            self.assertLessEqual(s["right"], previous); previous = s["right"]
        self.assertEqual(self.state(p, 651)["right"], 405)
        self.event(p, 3, 652, a=2); self.event(p, 0, 652)
        self.assertEqual(self.state(p, 652)["left"], 0)
        self.assertFalse(self.state(p, 652)["driver"])

    def test_reversal_then_wake_precedes_new_kick(self):
        p = self.car(startup=True); self.links(p, 100)
        self.event(p, 1, 100, a=1, b=30); self.event(p, 0, 100); self.event(p, 0, 101)
        self.event(p, 1, 102, a=2, b=30); self.event(p, 0, 102)
        self.assertEqual(self.state(p, 102)["reason"], "reversing")
        self.event(p, 0, 140); self.assertEqual(self.state(p, 140)["left"], 0)
        self.event(p, 0, 141); self.assertEqual(self.state(p, 141)["reason"], "waking")
        self.event(p, 0, 142); self.assertEqual(self.state(p, 142)["left"], -676)

    def test_kick_cannot_outlive_stop_release_mode_maintenance_or_links(self):
        for cause in ("stop", "release", "mode", "maintenance", "fpga", "brain", "cloud", "deadline"):
            p = self.car(startup=True); self.links(p, 100)
            if cause == "release":
                self.event(p, 1, 100, a=7, b=30)
            else:
                self.event(p, 2, 100, a=1)
                generation = self.state(p, 100)["generation"]
                self.event(p, 7, 100, a=7, b=30, duration=100, generation=generation)
            self.event(p, 0, 100); self.event(p, 0, 101)
            now = 110
            if cause == "stop": self.event(p, 3, now, a=2)
            elif cause == "release": self.event(p, 1, now, a=0)
            elif cause == "mode": self.event(p, 2, now, a=0)
            elif cause == "maintenance": self.event(p, 8, now, a=1)
            elif cause == "fpga": now=602; self.event(p, 5, now, a=3)
            elif cause == "brain": now=602; self.event(p, 6, now)
            elif cause == "cloud": self.event(p, 5, now, a=1)
            elif cause == "deadline": now=200; self.links(p, now)
            self.event(p, 0, now)
            s = self.state(p, now)
            self.assertEqual((s["left"], s["right"]), (0, 0), cause)
            self.assertFalse(s["driver"], cause)
            self.links(p, now+1); self.event(p, 0, now+1)
            self.assertEqual(self.state(p, now+1)["left"], 0, cause)


if __name__ == "__main__":
    unittest.main()
