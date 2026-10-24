"""Ensure simulation failures cannot be reported as success by the runner."""
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import run_fpga_tests as runner


class FpgaRunnerTests(unittest.TestCase):
    def test_every_top_testbench_is_registered(self):
        available = {path.stem for path in (runner.ROOT / "fpga" / "tb").glob("tb_*.sv")}
        self.assertEqual(set(runner.TESTS), available)

    def test_inventory_ignores_comments_and_rejects_duplicate_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "example.sv"
            source.write_text("// module fake;\n/* module also_fake; */\nmodule actual; endmodule\n")
            self.assertEqual(runner.declared_modules([source]), {"actual": str(source)})
            duplicate = Path(directory) / "duplicate.sv"
            duplicate.write_text("module actual; endmodule\n")
            with self.assertRaisesRegex(RuntimeError, "duplicate RTL module"):
                runner.declared_modules([source, duplicate])

    def test_module_evidence_uses_elaborated_types_not_instance_names(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "test.vvp"
            executable.write_text('S_1 .scope package, "$unit" "$unit";\n'
                                  'S_2 .scope module, "dut" "drive_core" 3 2;\n'
                                  'S_3 .scope module, "rx" "uart_rx" 4 2;\n'
                                  'S_4 .scope module, "rx2" "uart_rx" 4 2;\n')
            self.assertEqual(runner.elaborated_modules(executable), ["drive_core", "uart_rx"])

    def test_failed_or_uninstantiated_modules_are_not_credited(self):
        evidence = runner.module_evidence({"core": "core.sv", "rx": "rx.sv", "unused": "unused.sv"}, {
            "good": {"status": "passed", "modules": ["core", "test_helper"]},
            "bad": {"status": "failed", "modules": ["rx"]}})
        self.assertEqual(evidence["covered"], 1)
        self.assertEqual(evidence["missing"], ["rx", "unused"])
        self.assertEqual(evidence["modules"]["core"], ["good"])
        self.assertEqual(evidence["line_branch_toggle_coverage"], "not_measured")
        self.assertEqual(evidence["physical_timing"], "not_measured")

    def test_zero_exit_requires_the_correct_pass_marker_in_reports(self):
        for stdout in ("", "PASS tb_uart: wrong test\n", "not PASS tb_encoder_units: prefixed\n"):
            with self.subTest(stdout=stdout), self.assertRaises(RuntimeError):
                runner.require_pass_marker("tb_encoder_units", stdout)
        runner.require_pass_marker("tb_encoder_units", "noise\nPASS tb_encoder_units: checked\n")
        runner.require_pass_marker("tb_drive_defaults", "PASS tb_drive_core: default parameters\n")

    def test_report_contains_only_successfully_completed_evidence(self):
        for marker in (False, True):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / "fpga" / "rtl" / "core.sv"
                source.parent.mkdir(parents=True)
                source.write_text("module core; endmodule\n")

                def fake_execute(command, *args):
                    if "-g2012" in command:
                        Path(command[command.index("-o")+1]).write_text(
                            'S_1 .scope module, "dut" "core" 1 1;\n')
                        return ""
                    return "PASS tb_encoder_units: checks\nCOVER bin.hit 9\n" if marker else ""

                with (patch.object(runner, "ROOT", root),
                      patch.object(runner.shutil, "which", side_effect=lambda name: name),
                      patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                          ["iverilog"], 0, "test compiler\n", "")),
                      patch.object(runner, "execute", side_effect=fake_execute),
                      patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_encoder_units",
                                         "--report", "report.json", "--require-module-coverage"]),
                      redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                    self.assertEqual(runner.main(), 0 if marker else 1)
                report = json.loads((root / "report.json").read_text())
                self.assertEqual(report["status"], "passed" if marker else "failed")
                self.assertEqual(report["coverage"]["covered"], int(marker))
                self.assertIn("fpga/rtl/core.sv", report["source_sha256"])
                if marker:
                    self.assertEqual(report["tests"]["tb_encoder_units"]["functional_counts"], {"bin.hit": 9})

    def test_require_module_coverage_rejects_missing_report_option(self):
        with (patch("sys.argv", ["run_fpga_tests.py", "--require-module-coverage"]),
              redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error):
            runner.main()
        self.assertEqual(error.exception.code, 2)

    def test_require_module_coverage_fails_when_a_new_module_has_no_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fpga" / "rtl" / "core.sv"
            source.parent.mkdir(parents=True)
            source.write_text("module core; endmodule\nmodule untested; endmodule\n")

            def fake_execute(command, *args):
                if "-g2012" in command:
                    Path(command[command.index("-o")+1]).write_text(
                        'S_1 .scope module, "dut" "core" 1 1;\n')
                    return ""
                return "PASS tb_encoder_units: checks\n"

            with (patch.object(runner, "ROOT", root),
                  patch.object(runner.shutil, "which", side_effect=lambda name: name),
                  patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess(
                      ["iverilog"], 0, "test compiler\n", "")),
                  patch.object(runner, "execute", side_effect=fake_execute),
                  patch("sys.argv", ["run_fpga_tests.py", "--test", "tb_encoder_units",
                                     "--report", "report.json", "--require-module-coverage"]),
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                self.assertEqual(runner.main(), 1)
            report = json.loads((root / "report.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["tests"]["tb_encoder_units"]["status"], "passed")
            self.assertEqual(report["coverage"]["missing"], ["untested"])
            self.assertIn("untested", report["error"])

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
            sources = [rtl / "drive_core.sv", rtl / "encoder" / "encoder.sv",
                       rtl / "link" / "uart" / "rx.sv"]
            for source in sources:
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("module example; endmodule\n")
            unrelated = root / "fpga" / "tb" / "helper.sv"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("module test_helper; endmodule\n")
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
                self.assertNotIn(str(unrelated), command)
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
