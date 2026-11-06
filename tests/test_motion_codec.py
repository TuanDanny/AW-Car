import ctypes
from pathlib import Path
import random
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_motion_host import LIB, build
from motion_simulator import frame, Motion, Fpga
from fpga_protocol import vectors


class CodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.lib = ctypes.CDLL(str(LIB))
        cls.lib.motion_codec_echo.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
        cls.lib.motion_codec_echo.restype = ctypes.c_size_t
        cls.lib.motion_codec_command.argtypes = [ctypes.c_uint32, ctypes.c_uint16, ctypes.c_uint8,
                                                ctypes.c_uint16, ctypes.c_uint16, ctypes.c_void_p]
        cls.lib.motion_codec_command.restype = ctypes.c_size_t
        cls.lib.motion_fpga_parse_timed.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint64), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_uint32)]
        cls.lib.motion_fpga_parse_timed.restype = ctypes.c_uint

    def parse_timed(self, data, times):
        clock = (ctypes.c_uint64 * len(times))(*times)
        diagnostics = (ctypes.c_uint32 * 8)()
        count = self.lib.motion_fpga_parse_timed(data, clock, len(data), diagnostics)
        return count, list(diagnostics)

    def test_parser_distinguishes_timeout_header_and_crc_without_weakening_limits(self):
        data = vectors(2)[-1][1]
        times = [10000 + i * 87 for i in range(len(data))]
        self.assertEqual(self.parse_timed(data, times), (1, [0] * 8))
        delayed = [10000 if i < 8 else 12000 + (i-8)*87 for i in range(len(data))]
        accepted, d = self.parse_timed(data, delayed)
        self.assertEqual(accepted, 0)
        self.assertEqual(d[:5], [1, 1, 0, 0, 1])
        self.assertEqual(d[5:], [2000, 2000, 8])
        bad = bytearray(data)
        bad[-1] ^= 1
        accepted, d = self.parse_timed(bytes(bad), times)
        self.assertEqual(accepted, 0)
        self.assertEqual(d[:5], [1, 0, 0, 1, 3])
        bad[2] = 1
        accepted, d = self.parse_timed(bytes(bad[:3]), times[:3])
        self.assertEqual(accepted, 0)
        self.assertEqual(d[:5], [1, 0, 1, 0, 2])

    def test_valid_frame_recovers_after_timed_out_partial_and_errors_remain_visible(self):
        data = vectors(2)[-1][1]
        joined = data[:8] + data
        times = [10000+i*87 for i in range(8)] + [20000+i*87 for i in range(len(data))]
        accepted, d = self.parse_timed(joined, times)
        self.assertEqual(accepted, 1)
        self.assertEqual(d[:5], [1, 1, 0, 0, 1])

    def test_full_frame_deadline_stays_six_ms_even_when_each_gap_is_short(self):
        data = vectors(2)[-1][1]
        # Each inter-batch gap is <2ms, but the last batch reaches 6ms.
        at_deadline = [10000 + min(i//8, 4)*1500 for i in range(len(data))]
        accepted, d = self.parse_timed(data, at_deadline)
        self.assertEqual(accepted, 0)
        self.assertGreaterEqual(d[1], 1)
        before_deadline = [10000 + min(i//8, 4)*1499 for i in range(len(data))]
        self.assertEqual(self.parse_timed(data, before_deadline), (1, [0]*8))

    def echo(self, version, data):
        buf = ctypes.create_string_buffer(64)
        n = self.lib.motion_codec_echo(version, data, len(data), buf)
        return buf.raw[:n]

    def test_exact_fpga_v2_golden_vectors(self):
        for name, data in vectors(2):
            with self.subTest(name=name):
                self.assertEqual(self.echo(2, data), data)
                self.assertEqual(self.echo(1, data), b"")

    def test_bm_v1_all_messages_and_crc_vector(self):
        for kind in (1, 2, 3, 4, 5, 128):
            payload = struct.pack("<hhBH", -200, 1000, 1, 120) if kind == 3 else bytes(17) if kind == 128 else b""
            data = frame(1, kind, 0x12345678, 65535, payload)
            self.assertEqual(self.echo(1, data), data)
            self.assertEqual(self.echo(2, data), b"")

    def test_random_direction_duty_serialization_independent_crc(self):
        rng = random.Random(0x8833)
        for _ in range(1000):
            session = rng.randint(1, 0xffffffff)
            seq, direction = rng.randrange(65536), rng.randrange(4)
            left, right = rng.randrange(1351), rng.randrange(1351)
            expected = frame(2, 3, session, seq, struct.pack("<BBHH", 0, direction, left, right))
            buf = ctypes.create_string_buffer(64)
            n = self.lib.motion_codec_command(session, seq, direction, left, right, buf)
            self.assertEqual(buf.raw[:n], expected)

    def test_crc_and_length_corruption_rejected(self):
        data = vectors(2)[-1][1]
        for index in range(2, len(data)):
            bad = bytearray(data)
            bad[index] ^= 1
            self.assertEqual(self.echo(2, bytes(bad)), b"")

    def test_status_semantics_mode_direction_and_snapshot_header(self):
        for offset, value in ((12, 0xff), (14, 6), (17, 0), (17, 0x9c), (17, 0x1d)):
            m = Motion()
            try:
                p = bytearray(Fpga().status(10000)[11:-2])
                p[offset] = value
                m.receive(2, frame(2, 128, 0, 0, bytes(p)), 10000)
                self.assertFalse(m.view(10000)["fresh"])
            finally:
                m.close()
