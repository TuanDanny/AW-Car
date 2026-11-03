"""USB console checks for a driver-LOCKED Motion board. No ARM or motor commands."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time


def run(port_name, directory, reset=False, console_test=False):
    import serial
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "console-private.log"
    transcript = bytearray()
    serial_port = serial.Serial()
    serial_port.port = port_name
    serial_port.baudrate = 115200
    serial_port.timeout = .05
    serial_port.write_timeout = 1
    serial_port.dtr = serial_port.rts = False
    serial_port.open()
    def collect(seconds):
        start = len(transcript)
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            transcript.extend(serial_port.read(4096))
        return transcript[start:].decode("utf-8", errors="replace")
    def command(line, expected=None):
        serial_port.write((line + "\n").encode())
        data = collect(.4)
        if expected is not None and expected not in data:
            raise RuntimeError(f"command {line!r} did not yield {expected!r}: {data[-300:]!r}")
        return data
    def status():
        data = command("status")
        for line in data.splitlines():
            if line.startswith("STATUS "):
                return json.loads(line[7:])
        raise RuntimeError("missing JSON status")
    try:
        if reset:
            from esptool.reset import HardReset
            HardReset(serial_port, uses_usb=False)()
        boot = collect(6)
        if reset and "physical_driver_build=LOCKED" not in boot:
            raise RuntimeError("expected a driver-LOCKED firmware boot")
        cfg = command("config")
        if "driver_build=LOCKED" not in cfg:
            raise RuntimeError("This test refuses hardware-enabled builds")
        first = status()
        assert first["state"] == 0 and first["fault"] == 0, first
        assert not first["driver"] and not first["logical_permit"], first
        assert first["driver_gpio"] == first["logical_gpio"] == 0, first
        assert first["v_est"] is None and first["omega_est"] is None, first
        if first["latency_samples"] == 0:
            assert first["rx_to_uart_p95_us"] is None and first["rx_to_uart_p99_us"] is None, first
        print("Boot and default-off GPIO readback verified", flush=True)
        checks = ["boot_locked", "disarmed_gpio_readback", "invalid_measured_fields"]
        if console_test:
            command("help", "No USB ARM/MOVE/CLEAR")
            for line in ("set pulses_per_rev 0", "set duty_limit 1351", "set validated 1",
                         "set track_mm -1", "set track_mm 12.5"):
                command(line, "ERROR")
            command("set track_mm 130", "OK set track_mm")
            command("config", "track_mm=130")
            command("save", "OK save")
            command("set track_mm 140", "OK set track_mm")
            command("load", "OK load")
            command("config", "track_mm=130")
            command("defaults", "OK defaults")
            command("save", "OK save")
            command("stop", "OK STOP requested")
            checks += ["invalid_parameters_rejected", "configuration_roundtrip",
                       "nvs_save_load_crc", "restore_defaults", "local_stop_no_fpga_no_fault"]
            print("Console validation, NVS roundtrip and STOP verified", flush=True)
        samples = [status()]
        for _ in range(10):
            collect(1)
            samples.append(status())
        for sample in samples:
            assert sample["state"] == 0 and not sample["fault"], sample
            assert not sample["driver"] and not sample["logical_permit"], sample
            assert sample["driver_gpio"] == sample["logical_gpio"] == 0, sample
            assert sample["queue_drops"] == sample["tx_drops"] == 0, sample
        text = transcript.decode("utf-8", errors="replace")
        bad = re.search(r"(?i)guru meditation|panic'ed|backtrace:|stack overflow|assert failed|watchdog got triggered", text)
        if bad:
            raise RuntimeError(f"firmware fault signature: {bad.group(0)}")
        image = Path(__file__).resolve().parents[1] / "firmware/motion/build/merged-binary.bin"
        elf = image.with_name("aw_car_motion.elf")
        result = {"passed": True, "port": port_name, "checks": checks,
                  "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                  "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest(),
                  "samples": samples, "raw_log_private": raw_path.name,
                  "limits": "Board console/default-off only. No Brain/FPGA UART wiring, gate, current or motor test."}
        (directory / "board-check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "samples"}, indent=2))
        return result
    finally:
        raw_path.write_bytes(transcript)
        serial_port.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="COM7")
    parser.add_argument("--directory", default="build/board-motion-20261103-initial")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--console-test", action="store_true")
    args = parser.parse_args()
    run(args.port, args.directory, args.reset, args.console_test)
