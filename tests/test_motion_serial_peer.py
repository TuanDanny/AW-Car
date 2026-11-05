import sys
import struct
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from brain_simulator import frame, decode
from motion_serial_peer import WirePeer


class SerialPeerTests(unittest.TestCase):
    def test_fragment_noise_crc_and_recovery(self):
        p = WirePeer()
        hello = frame(1, 123, 1)
        self.assertEqual(p.receive(b"noise" + hello[:6], 0), [])
        replies = p.receive(hello[6:], 1000)
        self.assertEqual(len(replies), 1)
        self.assertEqual(decode(replies[0])[1], 123)
        bad = bytearray(frame(2, 123, 2))
        bad[-1] ^= 1
        replies = p.receive(bad + frame(2, 123, 2), 2000)
        self.assertEqual(len(replies), 1)
        self.assertEqual(p.motion.state, 2)
        self.assertGreater(p.errors, 0)

    def test_signed_twist_and_independent_lease(self):
        p = WirePeer()
        p.receive(frame(1, 123, 1) + frame(2, 123, 2), 0)
        p.receive(frame(3, 123, 3, struct.pack("<hhBH", -60, 300, 1, 120)), 1000)
        self.assertEqual((p.motion.v, p.motion.w), (-60, 300))
        p.motion.status(120999, True)
        self.assertEqual(p.motion.state, 2)
        p.motion.status(121000, True)
        self.assertEqual(p.motion.state, 0)

    def test_noise_buffer_is_bounded(self):
        p = WirePeer()
        for i in range(1000):
            p.receive(bytes(64), i * 1000)
            self.assertLessEqual(len(p.buffer), 1)


if __name__ == "__main__":
    unittest.main()
