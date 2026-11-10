"""Structure/source hygiene checks for the independent simplev1 branch."""
from __future__ import annotations
from pathlib import Path
import os
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"build", "managed_components", "__pycache__", ".git", ".venv", "node_modules", ".pytest_cache"}

def nested_checkout(path: Path) -> bool:
    # The main checkout contains the separately registered simplev1 worktree.
    # Its source/build/private files belong to that checkout, not this scan.
    return (path / ".git").exists()

def check(root: Path) -> list[str]:
    errors = []
    expected = {"esp", "fpga", "schematic", "docs", "data", "utils", "test"}
    actual = {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
              and p.name not in SKIP and not nested_checkout(p)}
    if actual != expected:
        errors.append(f"top-level directories: expected={sorted(expected)}, got={sorted(actual)}")
    for current, directories, files in os.walk(root):
        parent = Path(current)
        directories[:] = [name for name in directories if name not in SKIP and not nested_checkout(parent/name)]
        for name in directories:
            path = parent/name
            if not (path/"README.md").exists():
                errors.append(f"missing README: {path.relative_to(root).as_posix()}")
        for name in files:
            path = parent/name
            rel = path.relative_to(root).as_posix()
            if path.suffix.lower() in {".v", ".vh", ".svh", ".vhd", ".vhdl", ".bin", ".elf", ".raw", ".log", ".fs"}:
                errors.append(f"forbidden tracked source/artifact: {rel}")
            if re.search(r"(nvs[-_.]?dump|flash[-_.]?backup|credentials\.json)", name, re.I):
                errors.append(f"private artifact: {rel}")
    return errors

if __name__ == "__main__":
    errors = check(ROOT)
    for error in errors:
        print(error)
    print(f"simplev1 structure: {'FAIL' if errors else 'PASS'}")
    sys.exit(bool(errors))
