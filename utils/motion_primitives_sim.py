"""Offline, dimensionless motion study. Does not import or write MCU firmware.

Kinematics assume equal wheel speeds within each side and no slip. Duty is only
treated as speed in explicitly ideal plots. Startup/friction parameters are toy
values, NOT TT-motor calibration. Core equations use only the Python stdlib.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import platform
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
Pose = tuple[float, float, float]
Wheels = tuple[float, float]

# Nominal 30% examples; left/right refer to positive body yaw (CCW).
PRIMITIVES: dict[str, Wheels] = {
    "stop": (0.0, 0.0),
    "forward": (0.3, 0.3), "backward": (-0.3, -0.3),
    "arc_forward_left": (0.15, 0.3), "arc_forward_right": (0.3, 0.15),
    "arc_reverse_yaw_left": (-0.3, -0.15),
    "arc_reverse_yaw_right": (-0.15, -0.3),
    "spin_left": (-0.3, 0.3), "spin_right": (0.3, -0.3),
    "pivot_left": (0.0, 0.3), "pivot_right": (0.3, 0.0),
}


def finite(*values: float) -> None:
    if not all(math.isfinite(value) for value in values):
        raise ValueError("parameters must be finite")


def mix(throttle: float, steer: float) -> Wheels:
    """Normalized effort mixer, +steer = CCW; common saturation keeps ratio."""
    finite(throttle, steer)
    if max(abs(throttle), abs(steer)) > 1:
        raise ValueError("normalized input outside [-1, 1]")
    left, right = throttle - steer, throttle + steer
    scale = max(1.0, abs(left), abs(right))
    return left / scale, right / scale


def body(wheels: Wheels, track: float = 1.0) -> tuple[float, float]:
    finite(*wheels, track)
    if track <= 0:
        raise ValueError("track must be positive")
    left, right = wheels
    return (left + right) / 2, (right - left) / track


def wheel_speeds(v: float, omega: float, track: float = 1.0) -> Wheels:
    finite(v, omega, track)
    if track <= 0:
        raise ValueError("track must be positive")
    return v - track * omega / 2, v + track * omega / 2


def exact_constant_step(pose: Pose, wheels: Wheels, dt: float,
                        track: float = 1.0) -> Pose:
    """Closed SE(2) integration for a constant wheel-speed interval."""
    finite(*pose, dt)
    if dt < 0:
        raise ValueError("time cannot run backward")
    v, omega = body(wheels, track)
    x, y, theta = pose
    angle = omega * dt
    # sinc midpoint form stays stable near omega=0.
    half = angle / 2
    sinc = math.sin(half) / half if abs(half) > 1e-10 else 1 - half * half / 6
    distance = v * dt * sinc
    return x + distance * math.cos(theta + half), y + distance * math.sin(theta + half), theta + angle


def integrate(command: Callable[[float], Wheels], duration: float, dt: float,
              initial: Pose = (0.0, 0.0, 0.0), track: float = 1.0,
              gains: Wheels = (1.0, 1.0), method: str = "rk4") -> list[tuple[float, Pose]]:
    """Independent numerical ODE integrator; RK4 does not call exact step."""
    finite(duration, dt, track, *initial, *gains)
    if duration <= 0 or dt <= 0 or track <= 0 or method not in {"rk4", "euler"}:
        raise ValueError("invalid integration settings")

    def derivative(t: float, state: Pose) -> Pose:
        l, r = command(t)
        v, omega = body((l * gains[0], r * gains[1]), track)
        return v * math.cos(state[2]), v * math.sin(state[2]), omega

    def add(state: Pose, delta: Pose, scale: float) -> Pose:
        return tuple(a + scale * b for a, b in zip(state, delta))

    count = math.ceil(duration / dt)
    h = duration / count
    state = initial
    samples = [(0.0, state)]
    for i in range(count):
        t = i * h
        k1 = derivative(t, state)
        if method == "euler":
            state = add(state, k1, h)
        else:
            k2 = derivative(t + h / 2, add(state, k1, h / 2))
            k3 = derivative(t + h / 2, add(state, k2, h / 2))
            k4 = derivative(t + h, add(state, k3, h))
            state = tuple(a + h * (b + 2*c + 2*d + e) / 6
                          for a, b, c, d, e in zip(state, k1, k2, k3, k4))
        samples.append(((i + 1) * h, state))
    return samples


def eight(t: float, rate: float = 0.2, amplitude: float = 2.0) -> tuple[Pose, Wheels]:
    """Analytic Gerono curve x=A sin(s), y=A/2 sin(2s), track=1.

    Heading is compared modulo 2*pi, because atan2 returns wrapped angles.
    Constant rate limits wheel speed below 1 for this illustrative setup.
    """
    s = rate * t
    dx, dy = amplitude * math.cos(s), amplitude * math.cos(2*s)
    ddx, ddy = -amplitude * math.sin(s), -2 * amplitude * math.sin(2*s)
    speed = rate * math.hypot(dx, dy)
    yaw_rate = rate * (dx * ddy - dy * ddx) / (dx * dx + dy * dy)
    return ((amplitude * math.sin(s), amplitude / 2 * math.sin(2*s), math.atan2(dy, dx)),
            wheel_speeds(speed, yaw_rate))


class KickEnvelope:
    """Effort-envelope experiment ONLY, not a vehicle controller.

    A command-space zero->nonzero starts a bounded common gain. Refreshes and
    magnitude changes do not reset its clock. Actual rest is NOT measured here.
    Caller must supply neutral/STOP before any sign reversal and apply existing
    hardware wake/reverse guards. Timeout/STOP ownership stays in Motion.
    """
    def __init__(self, tau: float = 0.1, gain: float = 5 / 3):
        finite(tau, gain)
        if tau <= 0 or gain < 1:
            raise ValueError("tau>0 and gain>=1 required")
        self.tau, self.gain = tau, gain
        self.target: Wheels = (0.0, 0.0)
        self.started: float | None = None

    def command(self, target: Wheels, now: float) -> None:
        finite(*target, now)
        if max(map(abs, target)) > 1 or now < 0:
            raise ValueError("invalid effort/time")
        if target == (0.0, 0.0):
            self.target, self.started = target, None
            return
        if any(a * b < 0 for a, b in zip(self.target, target)):
            raise ValueError("neutral and external reverse guard required")
        if self.started is None:
            self.started = now
        self.target = target

    def sample(self, now: float) -> Wheels:
        finite(now)
        if self.started is None:
            return 0.0, 0.0
        elapsed = now - self.started
        if elapsed < 0:
            raise ValueError("time cannot run backward")
        # Common cap, not a per-wheel floor; a pivot's zero wheel stays zero.
        peak = max(map(abs, self.target))
        g0 = min(self.gain, 1 / peak)
        g = 1.0 if elapsed >= 5*self.tau else 1 + (g0 - 1) * math.exp(-elapsed / self.tau)
        return self.target[0] * g, self.target[1] * g


def linear_motor(t: float, target: float = 0.3, boost: float = 0.2,
                 tau_input: float = 0.1, tau_motor: float = 0.15) -> float:
    """Exact response of tau_motor*dv/dt + v = target+boost*exp(-t/tau_input)."""
    base = target * (1 - math.exp(-t/tau_motor))
    if math.isclose(tau_input, tau_motor, rel_tol=1e-12):
        return base + boost * (t / tau_motor) * math.exp(-t / tau_motor)
    return base + boost*tau_input/(tau_input-tau_motor) * (
        math.exp(-t/tau_input) - math.exp(-t/tau_motor))


def linear_motor_numeric(duration: float = 1.0, dt: float = 0.005,
                         tau_motor: float = 0.15) -> list[tuple[float, float]]:
    # Separate RK4 evaluation of the scalar differential equation.
    def f(t: float, v: float) -> float:
        return (0.3 + 0.2*math.exp(-t/0.1) - v) / tau_motor
    count = math.ceil(duration/dt)
    h, v = duration/count, 0.0
    rows = [(0.0, v)]
    for i in range(count):
        t = i*h
        k1 = f(t, v)
        k2 = f(t+h/2, v+h*k1/2)
        k3 = f(t+h/2, v+h*k2/2)
        k4 = f(t+h, v+h*k3)
        v += h*(k1+2*k2+2*k3+k4)/6
        rows.append(((i+1)*h, v))
    return rows


def friction_trial(target: float, kick: bool, dt: float = 0.001) -> list[tuple[float, float, float]]:
    """Toy positive-direction stiction: breakaway=.40, running friction=.20.

    Not a TT motor, no current/battery/thermal model. A negative net effort
    decelerates until speed=0, where the breakaway threshold applies again.
    """
    velocity = 0.0
    rows = []
    for i in range(round(2/dt) + 1):
        t = i*dt
        u = target + (0.5-target)*math.exp(-t/0.1) if kick and t < .5 else target
        rows.append((t, u, velocity))
        if velocity == 0 and u < 0.4:
            continue
        velocity = max(0.0, velocity + dt * (u - 0.2 - velocity) / 0.15)
    return rows


def angle_error(a: float, b: float) -> float:
    return abs(math.atan2(math.sin(a-b), math.cos(a-b)))


def path_error(rows: list[tuple[float, Pose]], reference: Callable[[float], Pose]) -> dict:
    return {
        "max_position_units": max(math.hypot(p[0]-reference(t)[0], p[1]-reference(t)[1]) for t, p in rows),
        "max_heading_rad": max(angle_error(p[2], reference(t)[2]) for t, p in rows),
        "endpoint_position_units": math.hypot(rows[-1][1][0], rows[-1][1][1]),
    }


def generate(output: Path, plots: bool = True) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    duration = 2*math.pi/0.2
    reference_circle = lambda t: (2*math.sin(.2*t), 2*(1-math.cos(.2*t)), .2*t)
    circle = integrate(lambda t: (.3, .5), duration, .005)
    figure = integrate(lambda t: eight(t)[1], duration, .005, initial=eight(0)[0])
    figure_half = integrate(lambda t: eight(t)[1], duration, .0025, initial=eight(0)[0])
    figure_euler = integrate(lambda t: eight(t)[1], duration, .005, initial=eight(0)[0], method="euler")
    biased = integrate(lambda t: eight(t)[1], duration, .005, initial=eight(0)[0], gains=(.95, 1.05))
    numeric_motor = linear_motor_numeric()
    equal_tau_motor = linear_motor_numeric(tau_motor=.1)
    no_kick, with_kick, insufficient = (friction_trial(.3, False), friction_trial(.3, True), friction_trial(.15, True))
    max_mix_error, mix_cases = 0.0, 0
    for i in range(-40, 41):
        for j in range(-40, 41):
            t, s = i/40, j/40
            l, r = mix(t, s)
            factor = max(1.0, abs(t-s), abs(t+s))
            v, w = body((l, r))
            max_mix_error = max(max_mix_error, abs(v-t/factor), abs(w-2*s/factor))
            mix_cases += 1
    decay = 1.0
    recurrence_error = 0.0
    for i in range(1001):
        recurrence_error = max(recurrence_error, abs(decay-math.exp(-i*.005/.1)))
        decay *= math.exp(-.005/.1)
    summary = {
        "schema": 1, "scope": "offline ideal/toy models; NOT firmware or hardware acceptance",
        "source_baseline": "85a0094fcc0eb6dd07d9693b3a020455372657df",
        "units": "track b=1 abstract length unit; time in seconds; no AW-Car speed calibration",
        "python": platform.python_version(),
        "parameters": {"track_units": 1, "dt_s": .005, "figure8_amplitude_units": 2,
                       "path_phase_rate_rad_s": .2, "kick_target": .3, "kick_start": .5,
                       "kick_tau_s": .1, "toy_breakaway": .4, "toy_running_friction": .2},
        "mixer": {"cases": mix_cases, "max_error": max_mix_error},
        "circle_rk4_vs_analytic": path_error(circle, reference_circle),
        "eight_rk4_vs_analytic": path_error(figure, lambda t: eight(t)[0]),
        "eight_half_dt_vs_analytic": path_error(figure_half, lambda t: eight(t)[0]),
        "eight_euler_vs_analytic": path_error(figure_euler, lambda t: eight(t)[0]),
        "eight_peak_wheel_speed_units_s": max(max(map(abs, eight(t)[1])) for t, _ in figure),
        "linear_motor_rk4_max_error": max(abs(v-linear_motor(t)) for t, v in numeric_motor),
        "linear_motor_equal_tau_max_error": max(abs(v-linear_motor(t, tau_motor=.1)) for t, v in equal_tau_motor),
        "exponential_recurrence_max_error": recurrence_error,
        "illustrative_5pct_side_gain_bias": path_error(biased, lambda t: eight(t)[0]),
        "toy_friction_final_speed": {"target_30_no_kick": no_kick[-1][2], "target_30_kick": with_kick[-1][2],
                                     "target_15_kick": insufficient[-1][2]},
        "kick_untruncated_at_ms": {str(ms): .3+.2*math.exp(-ms/100) for ms in (0, 100, 200, 300, 500)},
        "kick_finite_profile_at_ms": {str(ms): .3+.2*math.exp(-ms/100) if ms < 500 else .3
                                      for ms in (0, 100, 200, 300, 500)},
        "primitive_effort": PRIMITIVES,
    }
    summary["checks"] = {
        "mixer_6561_cases_bounded_error": max_mix_error < 1e-12,
        "circle_vs_analytic_below_1e_8": summary["circle_rk4_vs_analytic"]["max_position_units"] < 1e-8,
        "eight_vs_analytic_below_1e_8": summary["eight_rk4_vs_analytic"]["max_position_units"] < 1e-8,
        "path_wheel_speed_below_one": summary["eight_peak_wheel_speed_units_s"] < 1,
        "linear_motor_below_1e_7": summary["linear_motor_rk4_max_error"] < 1e-7,
        "equal_tau_motor_below_1e_7": summary["linear_motor_equal_tau_max_error"] < 1e-7,
        "recurrence_below_1e_12": recurrence_error < 1e-12,
        "toy_kick_starts_and_sustains": no_kick[-1][2] == 0 and with_kick[-1][2] > .09,
        "toy_low_throttle_stalls_again": max(r[2] for r in insufficient) > .01 and insufficient[-1][2] == 0,
    }
    if not all(summary["checks"].values()):
        raise AssertionError(summary["checks"])
    with (output/"paths.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("time_s", "reference_x_units", "reference_y_units", "rk4_x_units", "rk4_y_units", "bias_x_units", "bias_y_units"))
        for (t, p), (_, q) in zip(figure, biased):
            ref = eight(t)[0]
            writer.writerow((t, ref[0], ref[1], p[0], p[1], q[0], q[1]))
    with (output/"startup.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("time_s", "target30_no_kick_speed", "target30_kick_effort", "target30_kick_speed", "target15_kick_speed"))
        for a, b, c in zip(no_kick, with_kick, insufficient):
            writer.writerow((a[0], a[2], b[1], b[2], c[2]))
    if plots:
        render(output, circle, figure, biased, no_kick, with_kick, insufficient)
        import matplotlib
        summary["matplotlib"] = matplotlib.__version__
        from importlib.metadata import version
        summary["plot_packages"] = {name: version(name) for name in (
            "matplotlib", "numpy", "contourpy", "cycler", "fonttools", "kiwisolver",
            "packaging", "pillow", "pyparsing", "python-dateutil", "tzdata")}
    (output/"results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return summary


def render(output: Path, circle, figure, biased, no_kick, with_kick, insufficient) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.facecolor": "#f8fafc", "axes.facecolor": "white"})
    fig, axes = plt.subplots(4, 3, figsize=(12, 13), layout="constrained")
    labels = {
        "forward": "Tiến", "backward": "Lùi", "stop": "Dừng",
        "arc_forward_left": "Tiến rẽ cong trái", "arc_forward_right": "Tiến rẽ cong phải",
        "pivot_left": "Quay quanh bên trái đứng yên",
        "arc_reverse_yaw_left": "Lùi: đầu xe xoay trái",
        "arc_reverse_yaw_right": "Lùi: đầu xe xoay phải",
        "pivot_right": "Quay quanh bên phải đứng yên",
        "spin_left": "Quay tại chỗ trái", "spin_right": "Quay tại chỗ phải",
    }
    names = list(labels)
    for ax, name in zip(axes.flat, names):
        wheels = PRIMITIVES[name]
        poses = [exact_constant_step((0, 0, 0), wheels, i*.02) for i in range(151)]
        ax.plot([p[0] for p in poses], [p[1] for p in poses], color="#2563eb", lw=2)
        end = poses[-1]
        ax.scatter([0], [0], color="#64748b", s=20)
        ax.arrow(end[0], end[1], .12*math.cos(end[2]), .12*math.sin(end[2]), width=.008, color="#ea580c")
        ax.set_title(f"{labels[name]}\nTrái/phải = {wheels[0]*100:+.0f}% / {wheels[1]*100:+.0f}%", fontsize=11)
        ax.set(xlim=(-1.1, 1.1), ylim=(-1.1, 1.1), aspect="equal", xlabel="x / b", ylabel="y / b")
        ax.grid(alpha=.15)
    axes.flat[-1].axis("off")
    axes.flat[-1].text(.05, .7, "Chấm: vị trí đầu.\nMũi tên: hướng đầu xe cuối lượt.\n\nBánh cố định không đi ngang\ntức thời như xe mecanum.\n\nĐường đi lý tưởng; chưa xét trượt.\nb = khoảng cách hai vệt bánh,\nđơn vị trừu tượng, chưa đo trên xe.", va="top", fontsize=11)
    fig.suptitle("Bộ động tác cơ bản — mô hình lý tưởng\nChỉ trong hình minh họa: duty tỷ lệ tốc độ bánh; chưa hiệu chuẩn xe thật", fontsize=14)
    fig.savefig(output/"primitives.png", dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for ax, rows, title in ((axes[0], circle, "Vòng tròn: bán kính R = 2 b"), (axes[1], figure, "Số 8 liên tục: giải tích so với RK4")):
        reference = [(2*math.sin(.2*t), 2*(1-math.cos(.2*t))) if ax is axes[0] else eight(t)[0][:2] for t, _ in rows]
        ax.plot([p[0] for p in reference], [p[1] for p in reference], color="#94a3b8", lw=4, label="Đường chuẩn giải tích")
        ax.plot([p[0] for _, p in rows], [p[1] for _, p in rows], color="#2563eb", lw=1.6, label="Tích phân RK4 (bước 5 ms)")
        if ax is axes[1]:
            ax.plot([p[0] for _, p in biased], [p[1] for _, p in biased], "--", color="#ea580c", label="Giả định gain trái 0,95 / phải 1,05")
        ax.set(title=title, aspect="equal", xlabel="x / b", ylabel="y / b")
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.17))
    fig.suptitle("Kiểm tra công thức quỹ đạo — chưa phải đường đi đã hiệu chuẩn của AW-Car", fontsize=13)
    fig.savefig(output/"paths.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    times = [i*.005 for i in range(201)]
    env = KickEnvelope()
    env.command((.3, .15), 0)
    outputs = []
    for t in times:
        if t >= .6:
            env.command((0, 0), t)
        outputs.append(env.sample(t))
    axes[0, 0].plot(times, [100*p[0] for p in outputs], label="Trái: đích 30%", color="#2563eb")
    axes[0, 0].plot(times, [100*p[1] for p in outputs], label="Phải: đích 15%", color="#16a34a")
    axes[0, 0].axvline(.6, color="#ef4444", ls="--", label="STOP: lệnh về 0 ngay")
    axes[0, 0].set(title="Đề-pa chung hệ số, giữ tỷ lệ ga hai bên", ylabel="Lệnh duty PWM (%)")
    axes[0, 0].legend(fontsize=8)
    for rows, label, color in ((no_kick, "30% không đề-pa: đứng yên", "#64748b"), (with_kick, "30% có đề-pa: duy trì quay", "#2563eb"), (insufficient, "15% có đề-pa: lại dừng", "#ea580c")):
        axes[0, 1].plot([r[0] for r in rows], [r[2] for r in rows], label=label, color=color)
    axes[0, 1].set(title="Ma sát minh họa — ngưỡng chưa đo trên xe", ylabel="Tốc độ mô hình (chuẩn hóa)")
    axes[0, 1].legend(fontsize=8)
    numerical = linear_motor_numeric()
    axes[1, 0].plot([t for t, v in numerical], [linear_motor(t) for t, v in numerical], lw=4, color="#94a3b8", label="Nghiệm giải tích phương trình vi phân")
    axes[1, 0].plot([t for t, v in numerical], [v for t, v in numerical], color="#2563eb", label="Tích phân RK4 độc lập")
    axes[1, 0].set(title="Đối chiếu độc lập: motor tuyến tính bậc nhất", ylabel="Tốc độ mô hình (chuẩn hóa)")
    axes[1, 0].legend(fontsize=8)
    # Per-wheel flooring changes desired 1:2 effort ratio to 1:1.
    common = KickEnvelope(); common.command((.15, .3), 0)
    axes[1, 1].plot(times, [(.15+.35*math.exp(-t/.1))/(.3+.2*math.exp(-t/.1)) for t in times], color="#ea580c", label="Ép mỗi bên khởi đầu 50%: lệch tỷ lệ")
    axes[1, 1].plot(times, [common.sample(t)[0]/common.sample(t)[1] for t in times], color="#2563eb", label="Hệ số chung: tỷ lệ đích trái/phải = 0,5")
    axes[1, 1].set(title="Tỷ lệ lệnh rẽ trong lúc đề-pa", ylabel="Duty trái / duty phải", ylim=(.4, 1.1))
    axes[1, 1].legend(fontsize=8)
    for ax in axes.flat:
        ax.set_xlabel("Thời gian (s)"); ax.grid(alpha=.2)
    fig.suptitle("Nghiên cứu đề-pa mũ — số minh họa, chưa phải cấu hình motor thật", fontsize=14)
    fig.savefig(output/"startup.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"data/motion-simulation")
    parser.add_argument("--no-plots", action="store_true", help="stdlib core only")
    args = parser.parse_args()
    summary = generate(args.output, not args.no_plots)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
