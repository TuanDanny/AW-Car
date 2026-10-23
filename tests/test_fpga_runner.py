"""Ensure simulation failures cannot be reported as success by the runner."""
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import io
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import run_fpga_tests as runner


class FpgaRunnerTests(unittest.TestCase):
    def test_nonzero_tool_exit_fails(self):
        with patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                ["vvp"], 1, "", "")):
            with self.assertRaises(RuntimeError):
                runner.execute(["vvp"], 1, Path.cwd())

    def test_timeout_is_not_success(self):
        with patch.object(runner.subprocess, "run", side_effect=subprocess.TimeoutExpired("vvp", 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.execute(["vvp"], 1, Path.cwd())

    def test_compile_failure_never_runs_simulator(self):
        with tempfile.TemporaryDirectory() as directory:
            with (patch.object(runner, "ROOT", Path(directory)),
                  patch.object(runner.shutil, "which", side_effect=lambda name: name),
                  patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                      ["iverilog"], 0, "test compiler\n", "")),
                  patch.object(runner, "execute", side_effect=RuntimeError("compile failed")) as execute,
                  patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_encoder_units"]),
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                self.assertEqual(runner.main(), 1)
                self.assertEqual(execute.call_count, 1)
                self.assertEqual(Path(execute.call_args.args[0][0]).name, "iverilog")

    def test_relative_tool_paths_and_child_environment(self):
        original_path = os.environ.get("PATH")
        with tempfile.TemporaryDirectory(prefix="aw car ") as directory:
            with (patch.object(runner, "ROOT", Path(directory)),
                  patch.object(runner.shutil, "which", side_effect=lambda name: "relative/bin/" + name),
                  patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                      ["iverilog"], 0, "test compiler\n", "")),
                  patch.object(runner, "execute") as execute,
                  patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_encoder_units"]),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(runner.main(), 0)
                self.assertEqual(execute.call_count, 2)
                runtime_args = execute.call_args.args
                self.assertTrue(Path(runtime_args[0][0]).is_absolute())
                self.assertEqual(runtime_args[2], Path(directory) / "fpga" / "build")
                self.assertIn(str(Path(runtime_args[0][0]).parent),
                              runtime_args[3]["PATH"].split(os.pathsep))
                self.assertEqual(os.environ.get("PATH"), original_path)


if __name__ == "__main__":
    unittest.main()
