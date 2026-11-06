"""Captured Programmer failures must not become passes through exit0 or progress."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from tools import gowin_programmer_result as programmer


READOUT = "User Code is: 0x00009EF7\nStatus Code is: 0x0003F020\n"
DEVICE = "Target Device: GW1NR-9C(0x1100481B)\n"
CODES = "ID Code is: 0x1100481B\n" + READOUT + "Finished.\n"
# Short excerpt of flash-link-20261106/flash-program.log; no private UART data.
REAL_VERIFY_FAILURE = (
    DEVICE + 'Operation "embFlash Erase,Program,Verify" for device#1...\n'
    "\rErasing embFlash ...: [ ] 0% Status Code is: 0x00039020\r"
    "Programing...: [#########################] 100%\r"
    "Verifying...: [ ] 0%\nError: Verify Failed at 0\r"
    "Verifying...: [#########################] 100%\nError: Verify Failed\n"
    "Status Code is: 0x0003F020\nUser Code: 0x00009EF7\n"
    "Program Finished!\nFinished.\nCost 7.91 second(s)\n"
)


class ProgrammerResultTests(unittest.TestCase):
    def analyze(self, stdout=DEVICE + READOUT + "Finished.\n", **kwargs):
        options = dict(returncode=0, operation_index=5, expected_usercode=0x9EF7)
        options.update(kwargs)
        return programmer.analyze_programmer_result(stdout, **options)

    def test_real_verify_failure_wins_over_exit_zero_and_good_configuration(self):
        result = self.analyze(REAL_VERIFY_FAILURE, operation_index=6)
        self.assertEqual(result["result"], "FAIL_VERIFY")
        self.assertFalse(result["passed"])
        self.assertEqual(result["readback_verify"], "FAILED")
        self.assertEqual(result["configuration_status"], "VALID")
        self.assertEqual(result["operation_status"], "FAILED")
        self.assertTrue(result["status_bits"]["security"])
        self.assertNotIn("expected", " ".join(result["reasons"]))

    def test_semantic_error_in_either_stream_wins_even_after_finished(self):
        for error in ("Error: cable lost", "Programming Failed", "Fatal: stopped"):
            for stream in ("stdout", "stderr"):
                with self.subTest(error=error, stream=stream):
                    log = DEVICE + READOUT + "Program Finished!\nFinished.\n"
                    result = self.analyze(log + "\r" + error if stream == "stdout" else log,
                                          stderr=error if stream == "stderr" else "")
                    self.assertEqual(result["result"], "FAIL_SEMANTIC")
                    self.assertFalse(result["passed"])

    def test_native_nonzero_or_unknown_cannot_pass(self):
        for code in (1, -1, 23, None):
            with self.subTest(code=code):
                result = self.analyze(returncode=code)
                self.assertFalse(result["passed"])
                self.assertEqual(result["configuration_status"], "VALID")

    def test_progress_or_program_finished_is_not_terminal_completion(self):
        for tail in ("", "Program Finished!\n", "100%\n", "Finishe"):
            with self.subTest(tail=tail):
                result = self.analyze(READOUT + tail)
                self.assertEqual(result["result"], "INCOMPLETE")
                self.assertEqual(result["operation_status"], "INCOMPLETE")

    def test_timeout_and_known_truncation_override_complete_success(self):
        for kwargs in ({"timed_out": True}, {"output_truncated": True},
                       {"stderr": "Process timed out"}, {"stderr": "Timeout"}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(self.analyze(**kwargs)["passed"])

    def test_all_required_and_error_status_bits(self):
        for bit in (12, 13, 14, 15, 16, 0, 1, 2, 3, 4, 7, 18):
            with self.subTest(bit=bit):
                status = 0x3F020 ^ (1 << bit)
                log = READOUT.replace("0x0003F020", f"0x{status:08X}") + "Finished.\n"
                result = self.analyze(log)
                self.assertEqual(result["result"], "FAIL_CONFIGURATION")
                self.assertEqual(result["configuration_status"], "INVALID")

    def test_wrong_usercode_is_not_a_configuration_bit_failure(self):
        result = self.analyze(READOUT.replace("9EF7", "1234") + "Finished.\n")
        self.assertEqual(result["result"], "FAIL_USERCODE")
        self.assertEqual(result["configuration_status"], "VALID")
        self.assertFalse(result["passed"])

    def test_usercode_can_be_checked_for_presence_without_expected_value(self):
        self.assertTrue(self.analyze(expected_usercode=None)["passed"])

    def test_missing_or_malformed_readouts_never_pass(self):
        for log in ("", "Finished.\n", READOUT.splitlines()[0] + "\nFinished.\n",
                    READOUT.splitlines()[1] + "\nFinished.\n",
                    READOUT + "Status Code is: 0x\nFinished.\n",
                    READOUT + "User Code is: 0x9EF7garbage\nFinished.\n"):
            with self.subTest(log=log):
                self.assertFalse(self.analyze(log)["passed"])

    def test_conflicting_stream_readouts_are_unknown(self):
        result = self.analyze(stderr="Status Code is: 0x00039020")
        self.assertEqual(result["configuration_status"], "UNKNOWN")
        self.assertFalse(result["passed"])

    def test_protected_program_success_never_claims_byte_verify(self):
        for op in (2, 5):
            with self.subTest(op=op):
                result = self.analyze(operation_index=op)
                self.assertTrue(result["passed"])
                self.assertEqual(result["configuration_status"], "VALID")
                self.assertEqual(result["operation_status"], "COMPLETED")
                self.assertEqual(result["readback_verify"], "NOT_REQUESTED")

    def test_read_device_codes_requires_actual_matching_id(self):
        self.assertTrue(self.analyze(CODES, operation_index=0)["passed"])
        for log in (CODES.replace("1100481B", "1100481C"),
                    DEVICE + READOUT + "Finished.\n",
                    CODES + "ID Code is: 0x\n"):
            with self.subTest(log=log):
                self.assertFalse(self.analyze(log, operation_index=0)["passed"])
        self.assertEqual(self.analyze(CODES, operation_index=0)["readback_verify"],
                         "NOT_REQUESTED")

    def test_wrong_target_id_is_rejected(self):
        log = (DEVICE + READOUT + "Finished.\n").replace("1100481B", "1100481C")
        self.assertEqual(self.analyze(log)["result"], "FAIL_ID")

    def test_reprogram_completion_requires_separate_codes_read(self):
        for log in (DEVICE + "Finished.\n", DEVICE + READOUT + "Finished.\n"):
            with self.subTest(log=log):
                result = self.analyze(log, operation_index=1)
                self.assertEqual(result["operation_status"], "COMPLETED")
                self.assertEqual(result["configuration_status"], "UNKNOWN")
                self.assertEqual(result["readback_verify"], "NOT_REQUESTED")
                self.assertFalse(result["passed"])

    def test_verification_requires_explicit_success_not_progress(self):
        log = READOUT + "Verifying...: [####] 100%\nFinished.\n"
        result = self.analyze(log, operation_index=6)
        self.assertFalse(result["passed"])
        self.assertEqual(result["readback_verify"], "UNKNOWN")
        result = self.analyze("Verify Success\n" + log, operation_index=6)
        self.assertTrue(result["passed"])
        self.assertEqual(result["readback_verify"], "PASSED")
        result = self.analyze("Verify Success\nError: Verify Failed at 0\n" + log,
                              operation_index=6)
        self.assertEqual(result["result"], "FAIL_VERIFY")

    def test_joined_runs_cannot_supply_completion_to_a_truncated_attempt(self):
        first = 'Operation "embFlash Erase,Program" for device#1...\n'
        log = first + DEVICE + READOUT + "Finished.\n" + first + "Programing... 1%\n"
        result = self.analyze(log)
        self.assertFalse(result["passed"])
        self.assertEqual(result["operation_status"], "INCOMPLETE")
        self.assertIn("multiple_operation_headers", result["reasons"])

    def test_operation_header_cannot_be_relabelled_as_another_operation(self):
        log = 'Operation "Reprogram" for device#1...\n' + READOUT + "Finished.\n"
        self.assertEqual(self.analyze(log)["result"], "FAIL_OPERATION")

    def test_verifyfailed_without_space_is_still_a_failed_operation(self):
        result = self.analyze(READOUT + "VerifyFailed at 0\nFinished.\n", operation_index=6)
        self.assertEqual(result["result"], "FAIL_VERIFY")
        self.assertEqual(result["operation_status"], "FAILED")

    def test_api_rejects_unsupported_operations_and_invalid_usercode(self):
        for kwargs in ({"operation_index": 3}, {"operation_index": True},
                       {"expected_usercode": -1}, {"expected_usercode": 2**32},
                       {"returncode": "0"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.analyze(**kwargs)

    def test_cli_json_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "programmer.log"
            stderr = Path(temporary) / "stderr.log"
            for text, op, options, expected_exit, expected_result in (
                (REAL_VERIFY_FAILURE, 6, [], 1, "FAIL_VERIFY"),
                (CODES, 0, [], 0, "PASS"),
                (CODES, 0, ["--expected-usercode", "0x1234"], 1, "FAIL_USERCODE"),
                (CODES, 0, ["--timed-out"], 1, "TIMEOUT"),
                (CODES, 0, ["--truncated"], 1, "INCOMPLETE"),
                ("Finished.\n", 1, [], 1, "CONFIGURATION_UNKNOWN"),
            ):
                with self.subTest(op=op, options=options):
                    log.write_text(text, encoding="utf-8")
                    output = io.StringIO()
                    with redirect_stdout(output):
                        code = programmer.main(["--log", str(log), "--returncode", "0",
                                                "--operation-index", str(op), *options])
                    self.assertEqual(code, expected_exit)
                    self.assertEqual(json.loads(output.getvalue())["result"], expected_result)
            log.write_text(CODES, encoding="utf-8")
            stderr.write_text("Error: disconnected", encoding="utf-8")
            with redirect_stdout(io.StringIO()) as output:
                code = programmer.main(["--log", str(log), "--stderr-log", str(stderr),
                                        "--returncode", "0", "--operation-index", "0"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["result"], "FAIL_SEMANTIC")

    def test_cli_unreadable_log_is_json_nonpass(self):
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()) as output:
            code = programmer.main(["--log", str(Path(temporary) / "missing.log"),
                                    "--returncode", "0", "--operation-index", "5"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["result"], "INPUT_ERROR")


if __name__ == "__main__":
    unittest.main()
