import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class StatusIndicatorTests(unittest.TestCase):
    def test_production_policy_and_output_cache(self):
        compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
        self.assertIsNotNone(compiler, "Set CXX to a native C++17 compiler")
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / ("indicator.exe" if os.name == "nt" else "indicator")
            subprocess.run([compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                "-I" + str(ROOT / "firmware/shared"), str(ROOT / "tests/status_indicator_test.cc"),
                "-o", str(executable), *(["-static"] if os.name == "nt" else [])], check=True, capture_output=True)
            result = subprocess.run([str(executable)], check=True, capture_output=True, text=True)
            self.assertIn("PASS status", result.stdout)

    def test_retired_rgb_controls_and_tools_are_removed(self):
        if not (ROOT / "dashboard/app.mjs").exists():
            self.skipTest("Brain UI is maintained on the AI branch")
        for relative in ("dashboard/app.mjs", "dashboard/index.html"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("rgb-power", text)
            self.assertNotIn("data-rgb", text)
        board = ROOT / "firmware/brain/main/boards/aw-car-ai-rgb"
        if board.exists():
            text = "\n".join(p.read_text(encoding="utf-8") for p in board.glob("*.cc"))
            self.assertNotIn("self.rgb_light", text)
            self.assertFalse((board / "rgb_light.cc").exists())
