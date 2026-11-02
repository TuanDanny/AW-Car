"""Independent wire-format reference and shared golden vectors (stdlib only)."""
import argparse
import binascii
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "firmware" / "shared" / "fpga-vectors.hex"
FIXTURE_V2 = FIXTURE.with_name("fpga-vectors-v2.hex")
LENGTHS = {1: 0, 2: 0, 3: 6, 4: 0, 5: 0, 0x80: 18}


def encode_frame(kind, session, sequence, payload=b"", *, version=1):
    if version not in (1, 2):
        raise ValueError("unsupported protocol version")
    expected_length = 34 if version == 2 and kind == 0x80 else LENGTHS.get(kind)
    if expected_length is None or len(payload) != expected_length:
        raise ValueError("unknown type or incorrect payload length")
    body = struct.pack("<BBBIH", version, kind, len(payload), session, sequence) + payload
    return b"\xa5\x5a" + body + struct.pack("<H", binascii.crc_hqx(body, 0xFFFF))


def vectors(version=1):
    session = 0x12345678
    frames = [
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
    if version == 1:
        return frames
    if version != 2:
        raise ValueError("unsupported protocol version")
    status_v2 = struct.pack("<IIIHBHBIIII", 0x11223344, 0x55667788,
                            0x99AABBCC, 0x4321, 2, 0x0123, 0x3F,
                            0x10203040, 0x50607080, 0x90A0B0C0, 0xD0E0F000)
    return [(name, encode_frame(frame[3], int.from_bytes(frame[5:9], "little"),
                               int.from_bytes(frame[9:11], "little"),
                               status_v2 if name == "status" else frame[11:-2], version=2))
            for name, frame in frames]


def fixture_text(version=1):
    lines = []
    width = 32 if version == 1 else 64
    for name, frame in vectors(version):
        word = (len(frame) << (8 * (width - 1))) | int.from_bytes(frame, "little")
        lines.append(f"{word:0{width*2}x} // {name}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-vectors", action="store_true")
    args = parser.parse_args()
    for version, fixture in ((1, FIXTURE), (2, FIXTURE_V2)):
        expected = fixture_text(version)
        if args.write_vectors:
            fixture.write_text(expected, encoding="ascii", newline="\n")
        elif fixture.read_text(encoding="ascii") != expected:
            parser.exit(1, f"FAIL: shared FPGA v{version} vectors differ from wire reference\n")
    print("PASS: shared FPGA vectors and CRC reference")


if __name__ == "__main__":
    main()
