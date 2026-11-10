"""Build the real shared C++ core/tests and simulator DLL; no ESP or serial ports."""
from __future__ import annotations
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/host"
SOURCES = [ROOT / "esp/shared/src/protocol.cpp", ROOT / "esp/shared/src/control.cpp"]

def compiler() -> Path:
    candidate = os.environ.get("CXX") or shutil.which("clang++") or shutil.which("g++")
    if candidate:
        return Path(candidate)
    fixed = Path("C:/Users/tuand/.codex/worktrees/xiaozhi-ai/AW-Car/build/toolchain/llvm-mingw-20261020-ucrt-x86_64/bin/clang++.exe")
    if fixed.is_file():
        return fixed
    raise RuntimeError("Set CXX to a C++17 compiler")

def build(run: bool = True) -> dict:
    BUILD.mkdir(parents=True, exist_ok=True)
    cxx = compiler()
    env = os.environ.copy()
    env["PATH"] = str(cxx.parent) + os.pathsep + env.get("PATH", "")
    base = [str(cxx), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "esp/shared/include")]
    exe = BUILD / ("host_tests.exe" if os.name == "nt" else "host_tests")
    subprocess.run(base + [*map(str, SOURCES), str(ROOT / "test/host_tests.cpp"), "-o", str(exe)], check=True, env=env)
    # Windows cannot overwrite a loaded DLL. Content-addressed builds also identify
    # exactly which native implementation a running browser/soak is exercising.
    digest = hashlib.sha256()
    for source in [*SOURCES, ROOT / "test/sim_api.cpp", *sorted((ROOT / "esp/shared/include/simple").glob("*.hpp"))]:
        digest.update(source.read_bytes())
    suffix = digest.hexdigest()[:12]
    library = BUILD / (f"simple_sim_{suffix}.dll" if os.name == "nt" else f"libsimple_sim_{suffix}.so")
    subprocess.run(base + ["-shared", *([] if os.name == "nt" else ["-fPIC"]), *map(str, SOURCES), str(ROOT / "test/sim_api.cpp"), "-o", str(library)], check=True, env=env)
    if run:
        subprocess.run([str(exe)], check=True, env=env)
    result = {"compiler": str(cxx), "exe": str(exe), "library": str(library), "source_sha256": digest.hexdigest()}
    (BUILD / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
