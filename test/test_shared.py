"""Native core and independent Python/C++ wire-vector cross-checks."""
from __future__ import annotations
import binascii
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "utils"))
from build_host import build, compiler

class SharedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = build()
        cls.dll_dir = os.add_dll_directory(str(compiler().parent)) if os.name == "nt" else None
        cls.library = ctypes.CDLL(cls.output["library"])
        cls.library.codec_spi_encode.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        cls.library.codec_spi_status.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    def test_spi_vectors_independent_python(self):
        vectors = json.loads((ROOT / "data/protocol-vectors.json").read_text())
        for item in vectors["commands"]:
            seq, left, right = item["seq"], item["left"], item["right"]
            prefix = b"S1\x01\x00" + struct.pack("<Hhh", seq, left, right) + bytes(20)
            wire = prefix + struct.pack("<H", binascii.crc_hqx(prefix, 0xffff))
            self.assertEqual(wire.hex(), item["hex"])
            output = ctypes.create_string_buffer(32)
            self.library.codec_spi_encode(seq, left, right, output)
            self.assertEqual(output.raw, wire)

    def test_spi_reply_vector_and_corruption(self):
        prefix = b"SR\x01\x06" + struct.pack("<H6I", 65535, 1, 2, 1350, 2700, 81, 82)
        wire = prefix + struct.pack("<H", binascii.crc_hqx(prefix, 0xffff))
        out = (ctypes.c_uint32 * 8)()
        self.assertEqual(self.library.codec_spi_status(ctypes.create_string_buffer(wire), out), 1)
        self.assertEqual(list(out), [6, 65535, 1, 2, 1350, 2700, 81, 82])
        for i in range(32):
            corrupt = bytearray(wire)
            corrupt[i] ^= 1
            self.assertEqual(self.library.codec_spi_status(ctypes.create_string_buffer(bytes(corrupt)), out), 0)

    def test_no_old_control_contract_on_motion(self):
        source = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "esp/motion/main").glob("*.cpp"))
        for term in ["CLEAR_FAULT", "ARM_REQUEST", "validated=", "WIFI_MODE_APSTA"]:
            self.assertNotIn(term, source)
        self.assertIn("SPI_DMA_DISABLED", source)
        self.assertIn("WIFI_MODE_AP", source)

    def test_structure(self):
        subprocess.run([sys.executable, str(ROOT / "utils/check_repo.py")], check=True)

if __name__ == "__main__":
    unittest.main()
