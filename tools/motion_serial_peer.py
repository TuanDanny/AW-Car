"""BM-v1 PC test peer for real Brain UART. Never a motor/FPGA controller."""

from __future__ import annotations
import argparse
import time
from brain_simulator import Motion, decode


class WirePeer:
    def __init__(self):
        self.motion = Motion()
        self.buffer = bytearray()
        self.errors = 0

    def receive(self, data, now):
        self.buffer.extend(data)
        replies = []
        while len(self.buffer) >= 2:
            index = self.buffer.find(b"\xa5\x5a")
            if index < 0:
                self.buffer[:] = self.buffer[-1:] if self.buffer[-1] == 0xA5 else b""
                break
            if index:
                del self.buffer[:index]
            if len(self.buffer) < 5:
                break
            kind, length = self.buffer[3], self.buffer[4]
            if (
                self.buffer[2] != 1
                or {1: 0, 2: 0, 3: 7, 4: 0, 5: 0}.get(kind) != length
            ):
                del self.buffer[0]
                self.errors += 1
                continue
            size = 13 + length
            if len(self.buffer) < size:
                break
            frame = bytes(self.buffer[:size])
            try:
                decode(frame)
            except ValueError:
                del self.buffer[0]
                self.errors += 1
                continue
            del self.buffer[:size]
            self.motion.receive(frame, now)
            reply = self.motion.status(now, True)
            if reply:
                replies.append(reply)
        return replies


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--baud", type=int, default=115200)
    args = p.parse_args()
    import serial

    peer = WirePeer()
    start = time.monotonic_ns()
    last_print = 0
    print("MOTION SIMULATOR ONLY. No GPIO/PWM/PID/physical sensor data.", flush=True)
    with serial.Serial(
        args.port, args.baud, timeout=0.005, write_timeout=0.1
    ) as stream:
        while True:
            now = (time.monotonic_ns() - start) // 1000
            data = stream.read(64)
            for reply in peer.receive(data, now):
                stream.write(reply)
            reply = peer.motion.status(now)
            if reply:
                stream.write(reply)
            if now - last_print >= 1000000:
                last_print = now
                print(
                    f"state={peer.motion.state} target=({peer.motion.v},{peer.motion.w}) frames={peer.motion.total_frames} crc/parser_errors={peer.errors}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
