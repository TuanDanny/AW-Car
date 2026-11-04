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
