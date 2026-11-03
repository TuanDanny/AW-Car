"""Build the actual portable Brain core as a host library (not a behavior clone)."""

from pathlib import Path
import os
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "brain"
SOURCES = [
    ROOT / "tools/brain_host.cc",
    ROOT / "firmware/brain/main/aw_car/control_core.cc",
    ROOT / "firmware/shared/brain_motion_codec.cc",
]
HEADERS = [
    ROOT / "firmware/brain/main/aw_car/control_core.h",
    ROOT / "firmware/brain/main/aw_car/voice_gate.h",
    ROOT / "firmware/shared/brain_motion_codec.h",
]
DIGEST = hashlib.sha256(
    b"".join(p.read_bytes() for p in SOURCES + HEADERS)
).hexdigest()[:12]
LIB = BUILD / (f"brain-{DIGEST}.dll" if os.name == "nt" else f"libbrain-{DIGEST}.so")


def build():
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        candidates = list(
            (ROOT / "build/toolchain").glob("llvm-mingw-*/bin/clang++.exe")
        )
        if candidates:
            compiler = str(candidates[0])
    if not compiler:
        raise RuntimeError(
            "Install a host C++17 compiler or set CXX; ESP cross-compiler cannot run host tests"
        )
    BUILD.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-shared"]
    flags += ["-static"] if os.name == "nt" else ["-fPIC"]
    # Content-addressed binaries can already be loaded by a running simulator.
    # Never overwrite them on Windows; a source change selects a new filename.
    if not LIB.exists():
        subprocess.run(
            [
                compiler,
                *flags,
                "-I" + str(ROOT / "firmware/shared"),
                "-I" + str(ROOT / "firmware/brain/main/aw_car"),
                *map(str, SOURCES),
                "-o",
                str(LIB),
            ],
            check=True,
        )
    manifest = {
        "source_digest": DIGEST,
        "binary": LIB.name,
        "binary_sha256": hashlib.sha256(LIB.read_bytes()).hexdigest(),
        "compiler": subprocess.check_output(
            [compiler, "--version"], text=True
        ).splitlines()[0],
        "flags": flags,
        "sources": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SOURCES + HEADERS
        },
    }
    LIB.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(LIB)
    return LIB


if __name__ == "__main__":
    build()
