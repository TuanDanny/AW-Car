"""Compile and run the actual portable Brain session policy; no board/serial access."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]

class BrainContextTests(unittest.TestCase):
    def test_value_captured_context_cannot_revive(self):
        fixed = Path("C:/Users/tuand/.codex/worktrees/xiaozhi-ai/AW-Car/build/toolchain/llvm-mingw-20261020-ucrt-x86_64/bin/clang++.exe")
        compiler = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("g++") or (str(fixed) if fixed.is_file() else None)
        if not compiler:
            self.skipTest("C++17 compiler unavailable")
        output = ROOT / "esp/brain/build/host"
        output.mkdir(parents=True, exist_ok=True)
        exe = output / ("brain_context.exe" if os.name == "nt" else "brain_context")
        env = os.environ.copy()
        env["PATH"] = str(Path(compiler).parent) + os.pathsep + env.get("PATH", "")
        subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2",
            "-I", str(ROOT / "esp/brain/main"), "-I", str(ROOT / "esp/shared/include"),
            str(Path(__file__).with_name("context_test.cpp")), "-o", str(exe)], check=True, env=env)
        result = subprocess.run([str(exe)], check=True, env=env, text=True, capture_output=True)
        self.assertIn("PASS", result.stdout)
        print(result.stdout.strip())

if __name__ == "__main__":
    unittest.main()
