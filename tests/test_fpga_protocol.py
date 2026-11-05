"""Check wire layout and shared golden vectors independently of RTL."""
import binascii
import struct
import unittest

from tools import fpga_protocol as protocol


class FpgaProtocolTests(unittest.TestCase):
    def status_with_fault(self, fault, state=3):
        payload = struct.pack("<IIIHBHBIIII", 1, 2, 3, 4, state, fault, 0x1C, 0, 0, 1, 2)
        return protocol.encode_frame(0x80, 7, 4, payload, version=2)

    def test_diagnostic_warning_does_not_mean_fatal(self):
        decoded = protocol.decode_status_v2(self.status_with_fault(0x3700))
        self.assertFalse(decoded["fatal"])
        self.assertFalse(decoded["requires_fpga_reset"])
        self.assertIn("RX_FRAME_ERROR", decoded["fault_names"])
        self.assertIn("RIGHT_ENCODER_NO_EDGE", decoded["fault_names"])
        self.assertEqual(decoded["session"], 7)

    def test_diagnostic_critical_and_safety_faults(self):
        for fault in (1, 0x80, 0x800, 0x8000, 0xFFFF):
            decoded = protocol.decode_status_v2(self.status_with_fault(fault))
            self.assertTrue(decoded["fatal"])
            self.assertEqual(decoded["requires_fpga_reset"], bool(fault & 0x8800))

    def test_diagnostic_decoder_rejects_corrupt_or_mixed_frames(self):
        frame = self.status_with_fault(0)
        variants = [frame[:-1], frame+b"x", bytes(47), dict(protocol.vectors())["status"]]
        for index in range(len(frame)):
            bad = bytearray(frame); bad[index] ^= 1; variants.append(bytes(bad))
        mismatch = bytearray(frame[11:-2]); mismatch[12] ^= 1
        variants.append(protocol.encode_frame(0x80, 7, 4, mismatch, version=2))
        for bad in variants:
            with self.assertRaises(ValueError): protocol.decode_status_v2(bad)

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

    def test_v2_status_layout_and_crc(self):
        frame = dict(protocol.vectors(2))["status"]
        self.assertEqual(len(frame), 47)
        self.assertEqual(frame[:5], bytes.fromhex("a55a028022"))
        fields = struct.unpack("<IIIHBHBIIII", frame[11:-2])
        self.assertEqual(fields, (0x11223344, 0x55667788, 0x99AABBCC,
                                 0x4321, 2, 0x123, 0x3F, 0x10203040,
                                 0x50607080, 0x90A0B0C0, 0xD0E0F000))
        self.assertEqual(int.from_bytes(frame[-2:], "little"),
                         binascii.crc_hqx(frame[2:-2], 0xFFFF))
        self.assertEqual(protocol.FIXTURE_V2.read_text(encoding="ascii"),
                         protocol.fixture_text(2))
        for name, command in protocol.vectors(2):
            self.assertEqual(command[2], 2, name)
            self.assertEqual(len(command), 13 + command[4], name)

    def test_protocol_versions_do_not_share_status_lengths(self):
        for version, payload in ((1, bytes(34)), (2, bytes(18)), (3, bytes(18))):
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    protocol.encode_frame(0x80, 1, 1, payload, version=version)


if __name__ == "__main__":
    unittest.main()
