"""Compile the real firmware WS adapter with the ESP-IDF I/O boundary stubbed."""

from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WebSocketTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = (
            os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
        )
        if not compiler:
            candidates = list(
                (ROOT / "build/toolchain").glob("llvm-mingw-*/bin/clang++.exe")
            )
            compiler = str(candidates[0]) if candidates else None
        if not compiler:
            raise RuntimeError("A host C++17 compiler is required")
        build = ROOT / "build/brain"
        build.mkdir(parents=True, exist_ok=True)
        cls.binary = build / (
            "websocket-transport-test.exe"
            if os.name == "nt"
            else "websocket-transport-test"
        )
        flags = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror"]
        if os.name == "nt":
            flags.append("-static")
        subprocess.run(
            [
                compiler,
                *flags,
                "-I" + str(ROOT / "tests/brain_http_stub"),
                "-I" + str(ROOT / "firmware/brain/main/aw_car"),
                str(ROOT / "firmware/brain/main/aw_car/websocket_transport.cc"),
                str(ROOT / "tests/brain_http_stub/websocket_transport_test.cc"),
                "-o",
                str(cls.binary),
            ],
            check=True,
        )

    def check_case(self, name):
        result = subprocess.run(
            [str(self.binary), name], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS " + name, result.stdout)

    def test_partial_socket_writes_complete_or_fail_closed(self):
        self.check_case("short_writes")

    def test_http_handshake_is_not_control_json(self):
        self.check_case("handshake")

    def test_1000_frames_work_after_sdk_clears_request_uri(self):
        self.check_case("empty_uri")

    def test_text_bounds_binary_and_fragment_rejection(self):
        self.check_case("boundaries")

    def test_pong_is_consumed_without_control_dispatch(self):
        self.check_case("pong")

    def test_peer_close_and_ping_are_observed_without_double_close(self):
        self.check_case("close_and_ping")

    def test_sdk_io_failures_propagate(self):
        self.check_case("io_errors")
