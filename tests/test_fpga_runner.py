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

    def test_compiler_receives_all_sv_sources_in_systemverilog_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rtl = root / "fpga" / "rtl"
            rtl.mkdir(parents=True)
            sources = [rtl / "encoder.sv", rtl / "pwm.sv"]
            for source in sources:
                source.write_text("module example; endmodule\n")
            with (patch.object(runner, "ROOT", root),
                  patch.object(runner.shutil, "which", side_effect=lambda name: name),
                  patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                      ["iverilog"], 0, "test compiler\n", "")),
                  patch.object(runner, "execute") as execute,
                  patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_encoder_units"]),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(runner.main(), 0)
                command = execute.call_args_list[0].args[0]
                self.assertIn("-g2012", command)
                for source in sources:
                    self.assertIn(str(source), command)
                self.assertIn(str(root / "fpga" / "tb" / "tb_encoder_units.sv"), command)

    def test_full_timing_runs_integrated_scenario_at_nominal_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            with (patch.object(runner, "ROOT", Path(directory)),
                  patch.object(runner.shutil, "which", side_effect=lambda name: name),
                  patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                      ["iverilog"], 0, "test compiler\n", "")),
                  patch.object(runner, "execute") as execute,
                  patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_drive_core", "--full-timing"]),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(runner.main(), 0)
                command = execute.call_args_list[0].args[0]
                self.assertIn("-Ptb_drive_core.SCALE=1", command)
                self.assertIn("tb_drive_core", command)
                self.assertEqual(execute.call_args_list[1].args[0][1],
                                 str(Path(directory) / "fpga" / "build" / "tb_drive_core.vvp"))


if __name__ == "__main__":
    unittest.main()
