"""Structure/source hygiene checks for the independent simplev1 branch."""
from __future__ import annotations
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"build", "managed_components", "__pycache__", ".git", ".venv", "node_modules", ".pytest_cache"}
errors = []
expected = {"esp", "fpga", "schematic", "docs", "data", "utils", "test"}
actual = {p.name for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in SKIP}
if actual != expected:
    errors.append(f"top-level directories: expected={sorted(expected)}, got={sorted(actual)}")
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT)
    if any(p in SKIP for p in rel.parts):
        continue
    if path.is_dir():
        if not (path / "README.md").exists():
            errors.append(f"missing README: {rel.as_posix()}")
        continue
    if path.suffix.lower() in {".v", ".vh", ".svh", ".vhd", ".vhdl", ".bin", ".elf", ".raw", ".log", ".fs"}:
        errors.append(f"forbidden tracked source/artifact: {rel.as_posix()}")
    if re.search(r"(nvs[-_.]?dump|flash[-_.]?backup|credentials\.json)", path.name, re.I):
        errors.append(f"private artifact: {rel.as_posix()}")
for error in errors:
    print(error)
print(f"simplev1 structure: {'FAIL' if errors else 'PASS'}")
sys.exit(bool(errors))
