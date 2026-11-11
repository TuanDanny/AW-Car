"""Analytic references and counterexamples, not hardware acceptance tests."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "utils"))
from motion_primitives_sim import (KickEnvelope, PRIMITIVES, angle_error, body,
    eight, exact_constant_step, friction_trial, integrate, linear_motor,
    linear_motor_numeric, mix, path_error, wheel_speeds)


class MotionPrimitiveStudyTests(unittest.TestCase):
    def test_named_directions_and_heading_convention(self):
        # Expectations describe geometry, rather than reuse a production map.
        for name in ("arc_forward_left", "arc_reverse_yaw_left", "spin_left", "pivot_left"):
            with self.subTest(name=name):
                self.assertGreater(body(PRIMITIVES[name])[1], 0)
        for name in ("arc_forward_right", "arc_reverse_yaw_right", "spin_right", "pivot_right"):
            self.assertLess(body(PRIMITIVES[name])[1], 0)
        self.assertGreater(body(PRIMITIVES["forward"])[0], 0)
        self.assertLess(body(PRIMITIVES["backward"])[0], 0)

    def test_mixer_grid_bounds_ratio_and_inverse(self):
        for i in range(-40, 41):
            for j in range(-40, 41):
                throttle, steer = i/40, j/40
                l, r = mix(throttle, steer)
                scale = max(1, abs(throttle-steer), abs(throttle+steer))
                self.assertLessEqual(max(abs(l), abs(r)), 1)
                self.assertAlmostEqual((l+r)/2, throttle/scale, places=14)
                self.assertAlmostEqual((r-l)/2, steer/scale, places=14)
                self.assertAlmostEqual(l*(throttle+steer), r*(throttle-steer), places=14)

    def test_kinematic_round_trip_distinct_track_widths(self):
        for track in (.1, .5, 1, 2):
            for v in (-1, 0, .4):
                for omega in (-2, 0, .7):
                    got_v, got_w = body(wheel_speeds(v, omega, track), track)
                    self.assertAlmostEqual(got_v, v)
                    self.assertAlmostEqual(got_w, omega)

    def test_straight_and_no_instantaneous_lateral_motion(self):
        self.assertEqual(exact_constant_step((0, 0, 0), (.3, .3), 2), (.6, 0, 0))
        # At heading zero, body lateral velocity remains zero for any wheel pair.
        for wheels in PRIMITIVES.values():
            _, y, _ = exact_constant_step((0, 0, 0), wheels, 1e-6)
            self.assertLess(abs(y / 1e-6), 1e-6)

    def test_spin_changes_heading_without_translation(self):
        for name in ("spin_left", "spin_right"):
            p = exact_constant_step((2, 3, .5), PRIMITIVES[name], 2)
            self.assertEqual(p[:2], (2, 3))
            self.assertNotEqual(p[2], .5)

    def test_pivot_circle_and_full_turn(self):
        # Left wheel stopped: center describes radius b/2 around stationary side.
        p = exact_constant_step((0, 0, 0), (0, .3), math.pi/.3)
        self.assertAlmostEqual(p[0], 0, places=13)
        self.assertAlmostEqual(p[1], 1, places=13)
        self.assertAlmostEqual(p[2], math.pi, places=13)
        p = exact_constant_step((0, 0, 0), (.3, .5), 2*math.pi/.2)
        self.assertLess(math.hypot(*p[:2]), 1e-12)

    def test_rk4_circle_against_geometry(self):
        reference = lambda t: (2*math.sin(.2*t), 2*(1-math.cos(.2*t)), .2*t)
        rows = integrate(lambda t: (.3, .5), 2*math.pi/.2, .005)
        error = path_error(rows, reference)
        self.assertLess(error["max_position_units"], 1e-9)
        self.assertLess(error["max_heading_rad"], 1e-10)

    def test_figure_eight_matches_parametric_curve(self):
        # Reference x/y from analytic sin curve; numerical engine integrates
        # wheel commands -> body derivatives, so the two paths are independent.
        period = 2*math.pi/.2
        rows = integrate(lambda t: eight(t)[1], period, .005, initial=eight(0)[0])
        error = path_error(rows, lambda t: eight(t)[0])
        self.assertLess(error["max_position_units"], 1e-8)
        self.assertLess(error["max_heading_rad"], 1e-8)
        self.assertLess(max(max(map(abs, eight(t)[1])) for t, _ in rows), 1)

    def test_figure_eight_step_halving_reduces_error(self):
        # Coarse steps expose truncation error above floating-point noise.
        def error(dt):
            rows = integrate(lambda t: eight(t)[1], 2*math.pi/.2, dt, initial=eight(0)[0])
            return path_error(rows, lambda t: eight(t)[0])["max_position_units"]
        self.assertLess(error(.05), error(.1)/10)

    def test_unknown_wheel_gain_breaks_open_loop_path(self):
        rows = integrate(lambda t: eight(t)[1], 2*math.pi/.2, .01,
                         initial=eight(0)[0], gains=(.95, 1.05))
        self.assertGreater(path_error(rows, lambda t: eight(t)[0])["max_position_units"], .1)

    def test_exponential_gain_preserves_ratio_zero_side_and_bounds(self):
        for wheels in PRIMITIVES.values():
            env = KickEnvelope(); env.command(wheels, 0)
            for i in range(101):
                l, r = env.sample(i*.005)
                self.assertLessEqual(max(abs(l), abs(r)), 1)
                self.assertAlmostEqual(l*wheels[1], r*wheels[0], places=14)
                for a, b in zip((l, r), wheels):
                    if b == 0: self.assertEqual(a, 0)
                    else: self.assertGreater(a*b, 0)
            self.assertEqual(env.sample(.5), wheels)

    def test_high_target_has_common_saturation(self):
        env = KickEnvelope(); env.command((.8, .4), 0)
        self.assertEqual(env.sample(0), (1, .5))
        env.command((1, .5), .01)
        self.assertEqual(env.sample(.01), (1, .5))

    def test_repeated_20hz_messages_do_not_rekick(self):
        env = KickEnvelope(); env.command((.3, .3), 0)
        previous = math.inf
        for i in range(21):
            t = i*.05
            env.command((.3, .3), t)
            current = env.sample(t)[0]
            self.assertLessEqual(current, previous)
            previous = current
        self.assertEqual(env.sample(1), (.3, .3))

    def test_speed_update_does_not_restart_envelope(self):
        env = KickEnvelope(); env.command((.3, .3), 0)
        env.command((.4, .4), .3)
        self.assertLess(env.sample(.3)[0], .42)

    def test_stop_has_no_exponential_tail_and_new_start_is_distinct(self):
        env = KickEnvelope(); env.command((.3, .3), 0)
        self.assertGreater(env.sample(.04)[0], .3)
        env.command((0, 0), .04)
        self.assertEqual(env.sample(.04), (0, 0))
        self.assertEqual(env.sample(3), (0, 0))
        env.command((-.3, -.3), 3)
        self.assertAlmostEqual(env.sample(3)[0], -.5)

    def test_direct_sign_reversal_not_hidden_by_profile(self):
        env = KickEnvelope(); env.command((.3, .3), 0)
        with self.assertRaises(ValueError): env.command((-.3, -.3), .02)

    def test_separate_kick_floors_distort_arc(self):
        desired_ratio = .15/.3
        naive_ratio = max(.15, .5)/max(.3, .5)
        self.assertNotEqual(naive_ratio, desired_ratio)
        env = KickEnvelope(); env.command((.15, .3), 0)
        l, r = env.sample(0)
        self.assertEqual(l/r, desired_ratio)

    def test_motor_numeric_matches_closed_form_including_equal_tau(self):
        for tau in (.15, .1):
            rows = linear_motor_numeric(tau_motor=tau)
            self.assertLess(max(abs(v-linear_motor(t, tau_motor=tau)) for t, v in rows), 1e-7)
        # The cheap fixed-step recurrence proposed for Motion matches exp(t).
        z, coefficient = 1.0, math.exp(-.005/.1)
        for i in range(1001):
            self.assertLess(abs(z-math.exp(-i*.005/.1)), 1e-12)
            z *= coefficient

    def test_kick_starts_toy_motor_but_cannot_fix_low_final_throttle(self):
        without, kick, too_low = friction_trial(.3, False), friction_trial(.3, True), friction_trial(.15, True)
        self.assertTrue(all(r[2] == 0 for r in without))
        self.assertGreater(kick[-1][2], .09)
        self.assertGreater(max(r[2] for r in too_low), .01)
        self.assertEqual(too_low[-1][2], 0)
        # Not an accident of the toy Euler solver's time step.
        self.assertAlmostEqual(friction_trial(.3, True, .0005)[-1][2], kick[-1][2], places=6)

    def test_invalid_parameters_do_not_silently_produce_outputs(self):
        for bad in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValueError): mix(bad, 0)
            with self.assertRaises(ValueError): KickEnvelope(tau=bad)
        with self.assertRaises(ValueError): mix(1.1, 0)
        with self.assertRaises(ValueError): body((.3, .3), 0)
        with self.assertRaises(ValueError): KickEnvelope(tau=0)
        with self.assertRaises(ValueError): integrate(lambda t: (0, 0), 1, 0)


if __name__ == "__main__":
    unittest.main()
