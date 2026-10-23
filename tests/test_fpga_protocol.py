"""Check wire layout and shared golden vectors independently of RTL."""
import binascii
import unittest

from tools import fpga_protocol as protocol


class FpgaProtocolTests(unittest.TestCase):
    def test_crc_check_value(self):
        self.assertEqual(binascii.crc_hqx(b"123456789", 0xFFFF), 0x29B1)

    def test_wire_layout_and_crc(self):
        frame = protocol.vectors()[2][1]
        self.assertEqual(len(frame), 19)
        self.assertEqual(frame[:11].hex(), "a55a010306785634123412")
        self.assertEqual(frame[11:17].hex(), "0000a3024605")
        self.assertEqual(frame.hex(), "a55a0103067856341234120000a3024605e8fe")
        crc = binascii.crc_hqx(frame[2:-2], 0xFFFF)
        self.assertEqual(frame[-2:], crc.to_bytes(2, "little"))

    def test_shared_fixture_matches_reference(self):
        self.assertEqual(protocol.FIXTURE.read_text(encoding="ascii"), protocol.fixture_text())
        for _, frame in protocol.vectors():
            self.assertLessEqual(len(frame), 31)

    def test_unknown_type_and_wrong_length_fail(self):
        for kind, payload in ((0, b""), (3, b""), (1, b"\x00"), (0x80, bytes(17))):
            with self.subTest(kind=kind, payload=payload):
                with self.assertRaises(ValueError):
                    protocol.encode_frame(kind, 1, 1, payload)


if __name__ == "__main__":
    unittest.main()
