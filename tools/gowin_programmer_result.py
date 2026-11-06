"""Classify one captured Gowin Programmer run; never invoke tools or hardware.

Profile: GW1NR-9C, Security Final ON. UG290-2.8.1E Table 7-13,
pp. 79-81 defines the status bits; SUG502-2.2.1E pp. 47-48 defines
operation indices. A valid configuration readout is not byte verification,
nor proof that CRC was enabled in the input image. No failure cause is inferred.
"""

import argparse
import json
from pathlib import Path
import re
import sys


OPERATIONS = {
    0: "Read Device Codes",
    1: "Reprogram",
    2: "SRAM Program",
    5: "embFlash Erase,Program",
    6: "embFlash Erase,Program,Verify",
}
EXPECTED_DEVICE_ID = 0x1100481B
STATUS_BITS = {
    "crc_error": 0,
    "bad_command": 1,
    "id_error": 2,
    "timeout_error": 3,
    "edit_mode": 7,
    "vld": 12,
    "done": 13,
    "security": 14,
    "ready": 15,
    "por": 16,
    "flash_lock": 17,
}
REQUIRED_BITS = ("vld", "done", "security", "ready", "por")
ERROR_BITS = ("crc_error", "bad_command", "id_error", "timeout_error", "edit_mode")
_ERROR = re.compile(r"\b(?:error|fatal|failed|failure)\b", re.IGNORECASE)
_VERIFY_FAILED = re.compile(r"\bverif(?:y|ication)\s*[:=-]?\s*fail(?:ed|ure)\b", re.IGNORECASE)
_TIMEOUT = re.compile(r"\b(?:timed[ -]*out|timeout)\b", re.IGNORECASE)
_FINISHED = re.compile(r"\s*(?:Info:\s*)?Finished\.\s*", re.IGNORECASE)
_VERIFY_PASSED = re.compile(
    r"\s*(?:Info:\s*)?(?:Verify|Verification)\s+"
    r"(?:Success(?:ful(?:ly)?)?|Passed)[.!]?\s*", re.IGNORECASE
)


def _hex(value):
    return None if value is None else f"0x{value:08X}"


def _read_code(streams, label):
    """Use the last readout per stream; malformed/conflicting tails stay unknown."""
    marker = re.compile(rf"\b{label}\s+Code\b", re.IGNORECASE)
    value = re.compile(
        rf"\b{label}\s+Code(?:\s+is)?\s*:\s*(0x[0-9a-f]{{1,8}})\s*$",
        re.IGNORECASE,
    )
    tails = []
    for lines in streams:
        matches = [line for line in lines if marker.search(line)]
        if matches:
            match = value.search(matches[-1])
            tails.append(int(match[1], 16) if match else None)
    if not tails:
        return None, False
    ambiguous = None in tails or len(set(tails)) != 1
    return (None if ambiguous else tails[0]), ambiguous


def analyze_programmer_result(
    stdout, stderr="", *, returncode, operation_index, expected_usercode=None,
    timed_out=False, output_truncated=False,
):
    """Return a JSON-ready classification of one run's captured text.

    stdout/stderr are strings. Callers must flag known capture truncation or
    subprocess timeout; missing output/terminal Finished. also prevents PASS.
    Reprogram requires a subsequent, separately analyzed op0 for configuration
    acceptance, even if its own output happens to contain register readouts.
    Only op6 can report readback PASSED, and only with an explicit success line.
    """
    if type(operation_index) is not int or operation_index not in OPERATIONS:
        raise ValueError("operation_index must be one of 0, 1, 2, 5, 6")
    if returncode is not None and type(returncode) is not int:
        raise ValueError("returncode must be an integer or None")
    if expected_usercode is not None and (
        type(expected_usercode) is not int or not 0 <= expected_usercode <= 0xFFFFFFFF
    ):
        raise ValueError("expected_usercode must be an unsigned 32-bit integer")

    streams = [stdout.splitlines(), stderr.splitlines()]
    lines = [line for stream in streams for line in stream]
    errors = [line.strip() for line in lines if _ERROR.search(line)]
    verify_failed = any(_VERIFY_FAILED.search(line) for line in lines)
    operation_headers = re.findall(r'^\s*(?:Info:\s*)?Operation\s+"([^"]+)"',
                                   "\n".join(lines), re.IGNORECASE | re.MULTILINE)
    ambiguous_run = len(operation_headers) > 1
    wrong_operation = any(name.casefold() != OPERATIONS[operation_index].casefold()
                          for name in operation_headers)
    timeout = timed_out or any(_TIMEOUT.search(line) for line in lines)
    completed = any(_FINISHED.fullmatch(line) for line in lines)
    verify_passed = any(_VERIFY_PASSED.fullmatch(line) for line in lines)
    status, bad_status = _read_code(streams, "Status")
    usercode, bad_usercode = _read_code(streams, "User")
    device_id, bad_id = _read_code(streams, "ID")
    # Target identity is diagnostic input too, but does not replace op0's ID read.
    targets = re.findall(r"Target Device:\s*[^\n]*(0x[0-9a-f]{8})\)",
                         "\n".join(lines), re.IGNORECASE)
    wrong_target = any(int(value, 16) != EXPECTED_DEVICE_ID for value in targets)
    bits = None if status is None else {
        name: bool(status & (1 << bit)) for name, bit in STATUS_BITS.items()
    }
    configuration = "UNKNOWN"
    if bits is not None and operation_index != 1:
        configuration = "VALID" if (
            all(bits[name] for name in REQUIRED_BITS)
            and not any(bits[name] for name in ERROR_BITS)
            and status & 0xFFFC0010 == 0  # Reserved bits 31:18 and 4 must be zero.
        ) else "INVALID"
    readback = "NOT_REQUESTED"
    if operation_index == 6:
        readback = "FAILED" if verify_failed else (
            "PASSED" if verify_passed else "UNKNOWN"
        )

    if timeout:
        operation_status = "TIMEOUT"
    elif verify_failed or errors or returncode not in (0, None):
        operation_status = "FAILED"
    elif output_truncated or ambiguous_run or wrong_operation or not completed or returncode is None:
        operation_status = "INCOMPLETE"
    else:
        operation_status = "COMPLETED"

    reasons = []
    if verify_failed:
        reasons.append("verify_failed")
    if errors:
        reasons.append("semantic_error")
    if timeout:
        reasons.append("timeout")
    if returncode is None:
        reasons.append("missing_native_returncode")
    elif returncode != 0:
        reasons.append("native_exit_nonzero")
    if output_truncated:
        reasons.append("output_truncated")
    if ambiguous_run:
        reasons.append("multiple_operation_headers")
    if wrong_operation:
        reasons.append("operation_index_mismatch")
    if not completed:
        reasons.append("missing_completion")
    if operation_index == 1:
        reasons.append("configuration_requires_subsequent_op0")
    else:
        if status is None:
            reasons.append("invalid_status_readout" if bad_status else "missing_status")
        elif configuration == "INVALID":
            reasons.append("invalid_configuration_status")
        if usercode is None:
            reasons.append("invalid_usercode_readout" if bad_usercode else "missing_usercode")
        elif expected_usercode is not None and usercode != expected_usercode:
            reasons.append("usercode_mismatch")
        if operation_index == 0 and device_id is None:
            reasons.append("invalid_id_readout" if bad_id else "missing_id")
    if wrong_target or (device_id is not None and device_id != EXPECTED_DEVICE_ID):
        reasons.append("device_id_mismatch")
    if bad_id and operation_index != 0:
        reasons.append("invalid_id_readout")
    if operation_index == 6 and readback == "UNKNOWN":
        reasons.append("missing_verify_success")

    if verify_failed:
        result = "FAIL_VERIFY"
    elif errors:
        result = "FAIL_SEMANTIC"
    elif timeout:
        result = "TIMEOUT"
    elif returncode not in (0, None):
        result = "FAIL_NATIVE"
    elif wrong_operation:
        result = "FAIL_OPERATION"
    elif "device_id_mismatch" in reasons:
        result = "FAIL_ID"
    elif "usercode_mismatch" in reasons:
        result = "FAIL_USERCODE"
    elif configuration == "INVALID":
        result = "FAIL_CONFIGURATION"
    elif reasons:
        result = "CONFIGURATION_UNKNOWN" if (
            operation_index == 1 and operation_status == "COMPLETED"
        ) else "INCOMPLETE"
    else:
        result = "PASS"
    return {
        "schema": 1,
        "operation_index": operation_index,
        "operation": OPERATIONS[operation_index],
        "native_returncode": returncode,
        "timed_out": bool(timeout),
        "output_truncated": bool(output_truncated),
        "completion_seen": completed,
        "result": result,
        "passed": result == "PASS",
        "operation_status": operation_status,
        "configuration_status": configuration,
        "status_code": _hex(status),
        "status_bits": bits,
        "device_id": _hex(device_id),
        "usercode": _hex(usercode),
        "expected_usercode": _hex(expected_usercode),
        "readback_verify": readback,
        "reasons": reasons,
        "semantic_errors": errors,
    }


def _usercode_arg(value):
    try:
        number = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use decimal or 0x-prefixed UserCode") from error
    if not 0 <= number <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("UserCode must be an unsigned 32-bit integer")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="captured stdout or merged log")
    parser.add_argument("--stderr-log", type=Path, help="optional separate captured stderr")
    parser.add_argument("--returncode", type=int, required=True)
    parser.add_argument("--operation-index", type=int, choices=OPERATIONS, required=True)
    parser.add_argument("--expected-usercode", type=_usercode_arg)
    parser.add_argument("--timed-out", action="store_true")
    parser.add_argument("--truncated", action="store_true", help="capture is known to be incomplete")
    args = parser.parse_args(argv)
    try:
        stdout = args.log.read_text(encoding="utf-8-sig", errors="strict")
        stderr = args.stderr_log.read_text(encoding="utf-8-sig", errors="strict") if args.stderr_log else ""
    except (OSError, UnicodeError) as error:
        print(json.dumps({"result": "INPUT_ERROR", "passed": False, "error": str(error)}))
        return 2
    result = analyze_programmer_result(
        stdout, stderr, returncode=args.returncode, operation_index=args.operation_index,
        expected_usercode=args.expected_usercode, timed_out=args.timed_out,
        output_truncated=args.truncated,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
