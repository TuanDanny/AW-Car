"""Compiled C++ Motion core and an independent Python FPGA/UART peer.

This peer models the contract, not current, traction, mechanical stopping or STA.
"""
from __future__ import annotations
import binascii
import ctypes
import json
import struct
from collections import deque
from build_motion_host import LIB, build


def frame(version, kind, session, seq, payload=b""):
    data = struct.pack("<BBBIH", version, kind, len(payload), session, seq) + payload
    return b"\xa5\x5a" + data + struct.pack("<H", binascii.crc_hqx(data, 0xffff))


def decode(data):
    if len(data) < 13 or data[:2] != b"\xa5\x5a" or len(data) != data[4] + 13:
        raise ValueError("frame")
    if binascii.crc_hqx(data[2:-2], 0xffff) != int.from_bytes(data[-2:], "little"):
        raise ValueError("CRC")
    version, kind, length, session, seq = struct.unpack_from("<BBBIH", data, 2)
    return version, kind, session, seq, data[11:-2]


class Motion:
    def __init__(self, validated=True):
        if not LIB.exists():
            build()
        self.lib = ctypes.CDLL(str(LIB))
        lib = self.lib
        lib.motion_new.argtypes = [ctypes.c_int]
        lib.motion_new.restype = ctypes.c_void_p
        lib.motion_delete.argtypes = [ctypes.c_void_p]
        lib.motion_tick.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint]
        lib.motion_receive.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
                                      ctypes.c_size_t, ctypes.c_uint64]
        lib.motion_transmit.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p]
        lib.motion_transmit.restype = ctypes.c_size_t
        lib.motion_view.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        lib.motion_view.restype = ctypes.c_char_p
        lib.motion_stop.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        lib.motion_fault.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint64]
        lib.motion_config.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_uint64]
        lib.motion_config.restype = ctypes.c_int
        self.ptr = lib.motion_new(validated)

    def close(self):
        if self.ptr:
            self.lib.motion_delete(self.ptr)
            self.ptr = None

    def __del__(self):
        self.close()

    def tick(self, now, inputs=12):
        self.lib.motion_tick(self.ptr, now, inputs)

    def receive(self, port, data, now):
        self.lib.motion_receive(self.ptr, port, data, len(data), now)

    def tx(self, port, now):
        out = ctypes.create_string_buffer(64)
        n = self.lib.motion_transmit(self.ptr, port, now, out)
        return out.raw[:n]

    def view(self, now):
        return json.loads(self.lib.motion_view(self.ptr, now))

    def configure(self, key, value, now):
        return self.lib.motion_config(self.ptr, key.encode(), value, now)


class Fpga:
    def __init__(self):
        self.state = self.session = self.fault = self.seq = self.last_cmd = 0
        self.ack = self.req = self.permit = False
        self.online = self.progress = True
        self.edges = False
        self.rolling = False
        self.count = [0, 0]
        self.last_edge = [None, None]
        self.period = [0, 0]
        self.duties = [0, 0]
        self.direction = 0
        self.last_tx = -10000
        self.pending = []
        self.history = deque(maxlen=256)
        self.freeze = False

    def status(self, now):
        encoder = 0x1c
        for i in range(2):
            if self.last_edge[i] is not None:
                encoder |= 1 << (5 + i)
            if self.period[i]:
                encoder |= 1 << i
        age = [0xffffffff if t is None else min(0xffffffff, (now - t) * 27)
               for t in self.last_edge]
        payload = struct.pack("<IIIHBHBIIII", *self.count, (now * 27) & 0xffffffff,
                              self.seq, self.state, self.fault, encoder, *self.period, *age)
        return frame(2, 0x80, self.session, self.seq, payload)

    def pins(self, motion, now):
        if motion["req"] and not self.req and not motion["permit"]:
            self.ack = True
            self.session = 0
            self.state = 4 if self.fault else 0
        if not motion["req"] and self.req:
            self.ack = False
        if motion["permit"] and not self.permit:
            if self.state == 2 and self.ack:
                self.state = 3
            else:
                self.fault |= 8
                self.state = 4
        if not motion["permit"] and self.permit and self.state == 3:
            self.fault |= 4
            self.state = 4
        self.req, self.permit = motion["req"], motion["permit"]
        return (1 if self.ack else 0) | (2 if self.state == 3 and self.permit else 0) | 12

    def receive(self, data, now):
        version, kind, session, seq, payload = decode(data)
        assert version == 2
        self.history.append((now, kind, session, seq, payload))
        if kind == 4:
            self.session = 0
            self.ack = False
            self.state = 4 if self.fault else 0
            self.duties = [0, 0]
        elif kind == 1:
            self.session = session
            self.state = 4 if self.fault else 1
            self.last_cmd = seq
        elif session == self.session and 0 < ((seq - self.last_cmd) & 65535) < 32768:
            self.last_cmd = seq
            if kind == 2 and self.state == 1:
                self.state = 2
            elif kind == 5 and self.state == 4:
                self.fault = 0
                self.session = 0
                self.state = 0
                self.ack = False
            elif kind == 3 and self.state == 3:
                flags, self.direction, *self.duties = struct.unpack("<BBHH", payload)
                assert flags == 0 and self.direction < 4 and max(self.duties) <= 1350

    def step(self, now):
        if self.online and now - self.last_tx >= 10000:
            self.last_tx = now
            if self.progress:
                self.seq = (self.seq + 1) & 65535
            if self.edges and self.state == 3:
                for i in range(2):
                    if (self.duties[i] or self.rolling) and (
                            self.last_edge[i] is None or now - self.last_edge[i] >= 20000):
                        self.count[i] = (self.count[i] + 1) & 0xffffffff
                        if self.last_edge[i] is not None:
                            self.period[i] = (now - self.last_edge[i]) * 27
                        self.last_edge[i] = now
            self.pending.append((now + 4100, self.status(now)))
        ready = []
        while self.pending and self.pending[0][0] <= now:
            _, data = self.pending.pop(0)
            ready.append(data)
            if self.state == 2 and data[25] == 2:
                self.ack = True
        return ready


class Rig:
    def __init__(self, validated=True):
        self.motion = Motion(validated)
        self.fpga = Fpga()
        self.now = 0
        self.session = 0x12345678
        self.seq = 0
        self.inputs_override = None
        self.statuses = deque(maxlen=256)
        self.advance(30)

    @property
    def view(self):
        return self.motion.view(self.now)

    def advance(self, ms):
        for _ in range(ms):
            self.now += 1000
            inputs = self.fpga.pins(self.view, self.now)
            self.motion.tick(self.now, inputs if self.inputs_override is None else self.inputs_override)
            for data in self.fpga.step(self.now):
                self.motion.receive(2, data, self.now)
            out = self.motion.tx(2, self.now)
            if out:
                self.fpga.receive(out, self.now)
            out = self.motion.tx(1, self.now)
            if out:
                self.statuses.append(decode(out))

    def send(self, kind, v=0, omega=0, ttl=120, source=2, session=None, seq=None):
        self.seq = (self.seq + 1) & 65535
        payload = struct.pack("<hhBH", v, omega, source, ttl) if kind == 3 else b""
        self.motion.receive(1, frame(1, kind, self.session if session is None else session,
                                    self.seq if seq is None else seq, payload), self.now)
        return self.view

    def arm(self):
        self.session += 1
        self.send(1)
        self.send(2)
        self.advance(70)
        return self.view

    def drive(self, ms, v=60, omega=0):
        for i in range(ms):
            if i % 50 == 0:
                self.send(3, v, omega)
            self.advance(1)

    def close(self):
        self.motion.close()
