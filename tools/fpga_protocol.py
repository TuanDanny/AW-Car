"""Independent wire-format reference and shared golden vectors (stdlib only)."""
import argparse
import binascii
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "firmware" / "shared" / "fpga-vectors.hex"
LENGTHS = {1: 0, 2: 0, 3: 6, 4: 0, 5: 0, 0x80: 18}


def encode_frame(kind, session, sequence, payload=b""):
    if kind not in LENGTHS or len(payload) != LENGTHS[kind]:
        raise ValueError("unknown type or incorrect payload length")
    body = struct.pack("<BBBIH", 1, kind, len(payload), session, sequence) + payload
    return b"\xa5\x5a" + body + struct.pack("<H", binascii.crc_hqx(body, 0xFFFF))


def vectors():
    session = 0x12345678
    return [
        ("hello", encode_frame(1, session, 0x1233)),
        ("arm_zero", encode_frame(2, session, 0x1233)),
        ("cmd", encode_frame(3, session, 0x1234, struct.pack("<BBHH", 0, 0, 675, 1350))),
        ("cmd_preamble", encode_frame(3, 0x5AA55AA5, 0xA55A, bytes(6))),
        ("disable", encode_frame(4, 0, 0)),
        ("clear_fault", encode_frame(5, session, 0x1235)),
        ("status", encode_frame(0x80, session, 0x4321,
                               struct.pack("<IIIHBHB", 0x10203040, 0xFFEEDDCC,
                                           0x56789ABC, 0x4321, 2, 0x100, 0x0C))),
    ]


def fixture_text():
    lines = []
    for name, frame in vectors():
        word = (len(frame) << 248) | int.from_bytes(frame, "little")
        lines.append(f"{word:064x} // {name}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-vectors", action="store_true")
    args = parser.parse_args()
    expected = fixture_text()
    if args.write_vectors:
        FIXTURE.write_text(expected, encoding="ascii", newline="\n")
    elif FIXTURE.read_text(encoding="ascii") != expected:
        parser.exit(1, "FAIL: shared FPGA vectors differ from wire reference\n")
    print("PASS: shared FPGA vectors and CRC reference")


if __name__ == "__main__":
    main()
