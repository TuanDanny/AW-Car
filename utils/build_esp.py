"""Build (never flash) either ESP-IDF6.1 project with an isolated build directory."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from management_keys import prepare

ROOT = Path(__file__).resolve().parents[1]

def source_digest(root: Path, board: str) -> str:
    """Include defaults/lockfiles; exclude generated sdkconfig and build output."""
    digest = hashlib.sha256()
    for directory in [root / 'esp' / board, root / 'esp/shared', root / 'esp/management']:
        for file in sorted(directory.rglob('*')):
            if not file.is_file() or any(p in {'build', 'managed_components', '__pycache__'} for p in file.parts):
                continue
            if file.name in {'sdkconfig', 'sdkconfig.old'}:
                continue
            digest.update(file.relative_to(root).as_posix().encode())
            digest.update(file.read_bytes())
    return digest.hexdigest()

def environment() -> tuple[dict[str, str], Path, Path]:
    env = os.environ.copy()
    sdk = Path(env.get("IDF_PATH", "C:/Espressif/frameworks/esp-idf-v6.1"))
    tools = Path(env.get("IDF_TOOLS_PATH", "C:/Espressif"))
    python = Path(env.get("IDF_PYTHON_ENV_PATH", "C:/Espressif/python_env/idf6.1_py3.13_env")) / "Scripts/python.exe"
    if os.name != "nt":
        python = Path(sys.executable)
    if not (sdk / "tools/idf.py").is_file() or not python.is_file():
        raise SystemExit("ESP-IDF6.1/Python environment missing; set IDF_PATH and IDF_PYTHON_ENV_PATH")
    paths = [str(p) for p in (tools / "tools").glob("*/*/bin")]
    paths += [str(p) for p in (tools / "tools").glob("*/*/*/bin")]
    paths += [str(p) for p in (tools / "tools").glob("*/*") if p.is_dir()]
    env.update(IDF_PATH=str(sdk), IDF_TOOLS_PATH=str(tools), IDF_PYTHON_ENV_PATH=str(python.parent.parent), ESP_IDF_VERSION="6.1.0", PYTHONUTF8="1")
    rom = sorted((tools / "tools/esp-rom-elfs").glob("*"))
    if rom:
        env["ESP_ROM_ELF_DIR"] = str(rom[-1])
    env["PATH"] = os.pathsep.join([str(python.parent), *paths, env.get("PATH", "")])
    return env, sdk, python

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", choices=["motion", "brain"])
    parser.add_argument("--clean", action="store_true", help="IDF fullclean only inside generated board build")
    parser.add_argument("--test-rollback", action="store_true", help="Build an OTA-only trial image that deliberately fails local health")
    args = parser.parse_args()
    env, sdk, python = environment()
    project = ROOT / "esp" / args.board
    build = ROOT / "build" / args.board
    build.mkdir(parents=True, exist_ok=True)
    key_directory, key_id = prepare(ROOT, args.board, python)
    build_id = "simplev1-" + hashlib.sha256((source_digest(ROOT, args.board) + key_id + str(args.test_rollback)).encode()).hexdigest()[:12]
    command = [str(python), str(sdk / "tools/idf.py"), "-C", str(project), "-B", str(build), "-D", "IDF_TARGET=esp32s3", "-D", f"SIMPLE_BUILD_ID={build_id}", "-D", f"SIMPLE_MGMT_KEY_DIR={key_directory}"]
    command += ['-D', 'SIMPLE_OTA_TEST_FAIL_HEALTH=' + ('1' if args.test_rollback else '0')]
    if args.clean:
        subprocess.run(command + ["fullclean"], env=env, check=True)
    with (build / "build.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command + ["build"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        assert process.stdout
        for line in process.stdout:
            log.write(line)
            if any(token in line for token in ["error:", "Error", "FAILED", "Project build complete", "warning:", "Resolving dependencies"]):
                print(line.rstrip(), flush=True)
        code = process.wait()
    if code:
        raise SystemExit(f"Build failed ({code}); read {build / 'build.log'}")
    images = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in build.glob("*.bin")}
    for name in ('bootloader/bootloader.bin', 'partition_table/partition-table.bin'):
        file=build/name
        images[name]={'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    report = {"board": args.board, "build_id": build_id, "images": images, "flashed": False}
    report['sdkconfig_sha256'] = hashlib.sha256((project/'sdkconfig').read_bytes()).hexdigest()
    report['management_key_id'] = key_id
    report['test_rollback'] = args.test_rollback
    (build / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
