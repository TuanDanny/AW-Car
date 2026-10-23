"""Check repository documentation, SystemVerilog sources and branch convention."""

import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


BRANCH_PATTERN = re.compile(
    r"(?:feat/f[0-9]{2,}-|(?:fix|docs|chore)/)[a-z0-9][a-z0-9._-]*"
)
HDL_SUFFIXES = {".v", ".vh", ".sv", ".svh", ".vhd", ".vhdl"}


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def check_repository(root, *, staged=False, branch=None):
    errors = []
    if branch is not None and not BRANCH_PATTERN.fullmatch(branch):
        errors.append("Use feat/fXX-name, fix/name, docs/name or chore/name; never commit on main.")

    args = ["ls-files", "-z", "--cached"]
    if not staged:
        args.extend(["--others", "--exclude-standard"])
    paths = {
        name for name in git(root, *args).decode("utf-8").split("\0") if name
    }
    if not staged:
        paths = {name for name in paths if (root / name).is_file()}

    required = {"README.md", "AGENTS.md"}
    for name in paths:
        parent = PurePosixPath(name).parent
        while parent != PurePosixPath("."):
            required.add(str(parent / "README.md"))
            parent = parent.parent
    for name in sorted(required - paths):
        errors.append(f"Missing {name}")

    for name in sorted(paths):
        suffix = PurePosixPath(name).suffix
        if suffix.lower() in HDL_SUFFIXES and suffix != ".sv":
            errors.append(f"HDL sources must use SystemVerilog .sv: {name}")

    for name in sorted(path for path in paths if path.endswith(".md")):
        try:
            data = git(root, "show", f":{name}") if staged else (root / name).read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeError, RuntimeError) as error:
            errors.append(f"Cannot read UTF-8 Markdown {name}: {error}")
            continue
        if not text.strip():
            errors.append(f"Empty Markdown: {name}")
        if not text.endswith("\n"):
            errors.append(f"Missing final newline: {name}")
        for number, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"Trailing whitespace: {name}:{number}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--feature-branch", nargs="?", const="", default=None)
    args = parser.parse_args()
    try:
        branch = args.feature_branch
        if branch == "":
            branch = git(args.root, "symbolic-ref", "--short", "HEAD").decode().strip()
        errors = check_repository(args.root, staged=args.staged, branch=branch)
    except (OSError, UnicodeError, RuntimeError) as error:
        errors = [str(error)]
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: repository structure, Markdown, SystemVerilog and requested branch checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
