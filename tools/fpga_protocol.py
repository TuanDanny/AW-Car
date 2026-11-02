"""Independent wire-format reference and shared golden vectors (stdlib only)."""
import argparse
import binascii
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "firmware" / "shared" / "fpga-vectors.hex"
FIXTURE_V2 = FIXTURE.with_name("fpga-vectors-v2.hex")
LENGTHS = {1: 0, 2: 0, 3: 6, 4: 0, 5: 0, 0x80: 18}
FAULT_NAMES = {
    0x0001: "COMMAND_WATCHDOG", 0x0002: "SAFETY_HEALTH_OR_GATE",
    0x0004: "MOTION_PERMIT_LOST", 0x0008: "RECOVERY_ORDER",
    0x0010: "PWM_REJECTED", 0x0020: "CLEAR_TIMEOUT",
    0x0040: "HANDSHAKE_TIMEOUT", 0x0080: "SAFETY_STATE_INVALID",
    0x0100: "RX_FRAME_ERROR", 0x0200: "COMMAND_REJECTED",
    0x0400: "SNAPSHOT_DROPPED", 0x0800: "SNAPSHOT_STALL",
    0x1000: "LEFT_ENCODER_NO_EDGE", 0x2000: "RIGHT_ENCODER_NO_EDGE",
    0x4000: "PWM_REJECT_HISTORY", 0x8000: "INTERNAL_INVARIANT",
}


def decode_status_v2(frame):
    """Decode one complete CRC-checked STATUS; does not grant Motion permission."""
    if len(frame) != 47 or frame[:5] != bytes.fromhex("a55a028022"):
        raise ValueError("expected a complete 47-byte STATUS v2")
    if binascii.crc_hqx(frame[2:-2], 0xFFFF) != int.from_bytes(frame[-2:], "little"):
        raise ValueError("STATUS CRC mismatch")
    keys = ("left_count", "right_count", "timestamp", "snapshot_seq", "safety_state",
            "fault", "encoder_status", "left_period_ticks", "right_period_ticks",
            "left_age_ticks", "right_age_ticks")
    status = dict(zip(keys, struct.unpack("<IIIHBHBIIII", frame[11:-2])))
    status["session"] = int.from_bytes(frame[5:9], "little")
    if status["snapshot_seq"] != int.from_bytes(frame[9:11], "little"):
        raise ValueError("STATUS header/snapshot sequence mismatch")
    fault = status["fault"]
    status["fault_names"] = [name for mask, name in FAULT_NAMES.items() if fault & mask]
    status["requires_fpga_reset"] = bool(fault & 0x8800)
    status["fatal"] = bool(fault & 0x00FF or fault & 0x8800 or status["safety_state"] >= 4)
    return status


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
    parser.add_argument("--decode-status", metavar="HEX", help="decode a captured STATUS v2 to JSON")
    args = parser.parse_args()
    if args.decode_status is not None:
        try:
            print(json.dumps(decode_status_v2(bytes.fromhex(args.decode_status)), indent=2))
        except ValueError as error:
            parser.exit(1, f"FAIL: {error}\n")
        return
    for version, fixture in ((1, FIXTURE), (2, FIXTURE_V2)):
        expected = fixture_text(version)
        if args.write_vectors:
            fixture.write_text(expected, encoding="ascii", newline="\n")
        elif fixture.read_text(encoding="ascii") != expected:
            parser.exit(1, f"FAIL: shared FPGA v{version} vectors differ from wire reference\n")
    print("PASS: shared FPGA vectors and CRC reference")


if __name__ == "__main__":
    main()
