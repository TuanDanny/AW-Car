"""Real C++ Brain core + independent Python BM-v1 Motion test peer."""

from __future__ import annotations
import binascii
import ctypes
import json
from pathlib import Path
import struct
import sys
import time
from collections import deque

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_brain_host import LIB


def frame(kind, session, seq, payload=b""):
    body = struct.pack("<BBB I H", 1, kind, len(payload), session, seq) + payload
    return b"\xa5\x5a" + body + struct.pack("<H", binascii.crc_hqx(body, 0xFFFF))


def decode(data):
    if len(data) < 13 or data[:3] != b"\xa5\x5a\x01":
        raise ValueError("header")
    version, kind, length, session, seq = struct.unpack_from("<BBB I H", data, 2)
    if (
        len(data) != 13 + length
        or binascii.crc_hqx(data[2:-2], 0xFFFF)
        != struct.unpack_from("<H", data, len(data) - 2)[0]
    ):
        raise ValueError("length/CRC")
    if {1: 0, 2: 0, 3: 7, 4: 0, 5: 0, 128: 17}.get(kind) != length:
        raise ValueError("type length")
    return kind, session, seq, data[11:-2]


class Brain:
    def __init__(self):
        self.lib = ctypes.CDLL(str(LIB))
        l = self.lib
        l.aw_new.restype = ctypes.c_void_p
        l.aw_delete.argtypes = [ctypes.c_void_p]
        l.aw_command.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64] + [
            ctypes.c_int64
        ] * 7
        l.aw_tx.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p]
        l.aw_tx.restype = ctypes.c_size_t
        l.aw_rx.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]
        l.aw_state.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        l.aw_state.restype = ctypes.c_char_p
        l.aw_indicator.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        l.aw_indicator.restype = ctypes.c_char_p
        l.aw_gate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint64,
            ctypes.c_int,
            ctypes.c_char_p,
        ]
        self.ptr = l.aw_new()

    def command(self, op, now, *args):
        return self.lib.aw_command(
            self.ptr, op, now, *(list(args) + [0] * (7 - len(args)))
        )

    def state(self, now):
        return json.loads(self.lib.aw_state(self.ptr, now))

    def indicator(self, now):
        return json.loads(self.lib.aw_indicator(self.ptr, now))

    def gate(self, op, now, identifier=1, session="session-A"):
        return self.lib.aw_gate(self.ptr, op, now, identifier, session.encode())

    def tx(self, now):
        buf = ctypes.create_string_buffer(32)
        n = self.lib.aw_tx(self.ptr, now, buf)
        return buf.raw[:n]

    def rx(self, now, data):
        self.lib.aw_rx(self.ptr, now, bytes(data), len(data))

    def close(self):
        if self.ptr:
            self.lib.aw_delete(self.ptr)
            self.ptr = None

    def __del__(self):
        self.close()


class Motion:
    """Contract peer only: no FPGA/PID/motor simulation, measured fields invalid."""

    def __init__(self):
        self.session = 0
        self.seq = 0
        self.last = 65535
        self.applied = 65535
        self.result = 255
        self.state = 0
        self.fault = 0
        self.v = 0
        self.w = 0
        self.lease = 0
        self.last_status = -50000
        self.last_accepted = None
        self.arm_context = False
        self.online = True
        self.frames = deque(maxlen=256)
        self.total_frames = 0

    def receive(self, data, now):
        kind, sess, seq, p = decode(data)
        self.frames.append((now, kind, sess, seq, p))
        self.total_frames += 1
        if kind == 4:
            self.state = 3 if self.fault else 0
            self.v = self.w = 0
            self.session = 0
            self.lease = 0
            self.result = 0
            self.last = seq
            self.last_accepted = None
            self.arm_context = False
        elif kind == 1 and self.state in (0, 3) and sess:
            self.session = sess
            self.last_accepted = seq
            self.last = seq
            self.result = 0
            self.arm_context = True
        else:
            self.last = seq
            fresh = (
                self.last_accepted is None
                or 0 < ((seq - self.last_accepted) & 65535) < 32768
            )
            self.result = (
                0
                if sess == self.session and sess and fresh
                else 2
                if sess != self.session
                else 3
            )
            if self.result:
                return
            if not self.arm_context:
                self.result = 2
                return
            if kind == 2:
                if self.state != 0 or self.fault:
                    self.result = 1
                    return
                self.state = 2
                self.lease = now + 120000
            elif kind == 3:
                v, w, source, ttl = struct.unpack("<hhBH", p)
                if self.state != 2:
                    self.result = 1
                    return
                if (
                    abs(v) > 200
                    or abs(w) > 1000
                    or source not in (1, 2)
                    or not 1 <= ttl <= 250
                ):
                    self.result = 4
                    return
                self.v = v
                self.w = w
                self.applied = seq
                self.lease = now + ttl * 1000
            elif kind == 5:
                if self.state != 3:
                    self.result = 1
                    return
                self.fault = 0
                self.state = 0
                self.arm_context = False
            self.last_accepted = seq

    def status(self, now, force=False):
        if self.state == 2 and now >= self.lease:
            self.state = 0
            self.v = self.w = 0
            self.result = 6
        if not self.online or (not force and now - self.last_status < 50000):
            return b""
        self.last_status = now
        self.seq = (self.seq + 1) & 65535
        p = struct.pack(
            "<HHBBHhhHHB",
            self.last,
            self.applied,
            self.result,
            self.state,
            self.fault,
            0,
            0,
            0,
            65535,
            0,
        )
        return frame(128, self.session, self.seq, p)


class Rig:
    def __init__(self):
        self.brain = Brain()
        self.motion = Motion()
        self.now = 0

    def pump(self, dt=0):
        self.now += dt
        self.brain.command(0, self.now)
        # Only a real decoded request earns a response; no direct fake core ARM.
        for _ in range(4):
            data = self.brain.tx(self.now)
            if not data:
                break
            if self.motion.online:
                self.motion.receive(data, self.now)
                reply = self.motion.status(self.now, True)
                if reply:
                    self.brain.rx(self.now, reply)
        reply = self.motion.status(self.now)
        if reply:
            self.brain.rx(self.now, reply)
        return self.brain.state(self.now)

    def advance(self, us):
        while us:
            n = min(5000, us)
            self.pump(n)
            us -= n
        return self.state

    @property
    def state(self):
        return self.brain.state(self.now)

    def connect(self):
        self.brain.command(1, self.now)
        return self.pump()

    def arm(self):
        result = self.brain.command(5, self.now, self.state["epoch"])
        self.pump()
        return result

    def mode(self, ai):
        self.brain.command(4, self.now, int(ai))
        return self.pump()

    def move(self, seq, v, w, deadman=True, ttl=120, epoch=None, challenge=None):
        s = self.state
        return self.brain.command(
            7,
            self.now,
            s["epoch"] if epoch is None else epoch,
            s["challenge"] if challenge is None else challenge,
            seq,
            v,
            w,
            ttl,
            deadman,
        )
