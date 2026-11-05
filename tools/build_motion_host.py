"""Compile production Motion algorithms for native tests; no ESP32 behavior clone."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / path for path in (
    "tools/motion_host.cc", "firmware/motion/main/motion_core.cc",
    "firmware/motion/main/fpga_link.cc", "firmware/motion/main/drive_model.cc",
    "firmware/shared/fpga_codec.cc", "firmware/shared/brain_motion_codec.cc")]
HEADERS = [ROOT / "firmware/motion/main" / name for name in
           ("motion_core.h", "fpga_link.h", "drive_model.h")] + [
    ROOT / "firmware/shared/fpga_codec.h", ROOT / "firmware/shared/brain_motion_codec.h"]
DIGEST = hashlib.sha256(b"".join(p.read_bytes() for p in SOURCES + HEADERS)).hexdigest()[:16]
BUILD = ROOT / "build/motion"
LIB = BUILD / (f"motion-{DIGEST}.dll" if os.name == "nt" else f"motion-{DIGEST}.so")


def build():
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        candidates = list((ROOT / "build/toolchain").glob("llvm-mingw-*/bin/clang++.exe"))
        if candidates:
            compiler = str(candidates[0])
    if not compiler:
        raise RuntimeError("Native C++17 compiler required. Set CXX; do not use the Xtensa compiler for host tests.")
    BUILD.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-shared"]
    flags += ["-static"] if os.name == "nt" else ["-fPIC"]
    if not LIB.exists():
        subprocess.run([compiler, *flags,
                        "-I" + str(ROOT / "firmware/shared"),
                        "-I" + str(ROOT / "firmware/motion/main"),
                        *map(str, SOURCES), "-o", str(LIB)], check=True)
    LIB.with_suffix(".manifest.json").write_text(json.dumps({
        "digest": DIGEST, "compiler": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
        "flags": flags, "sha256": hashlib.sha256(LIB.read_bytes()).hexdigest(),
        "sources": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in SOURCES + HEADERS}}, indent=2) + "\n", encoding="utf-8")
    return LIB


if __name__ == "__main__":
    print(build())
