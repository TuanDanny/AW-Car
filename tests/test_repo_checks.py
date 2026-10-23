"""Integration tests of the repository guard using disposable Git repositories."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "repo_checks", Path(__file__).resolve().parents[1] / "tools" / "check_repo.py"
)
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class RepositoryChecksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "--quiet")
        self.write("README.md", "# Example\n\nRepository introduction.\n")
        self.write("AGENTS.md", "# Rules\n\nUse feature branches.\n")

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            check=True,
        )

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def test_complete_repository_passes(self):
        self.assertEqual(CHECKS.check_repository(self.root), [])

    def test_missing_nested_readme_fails(self):
        self.write("firmware/motion/main.c", "int main(void) { return 0; }\n")
        errors = CHECKS.check_repository(self.root)
        self.assertIn("Missing firmware/README.md", errors)
        self.assertIn("Missing firmware/motion/README.md", errors)

    def test_ignored_generated_directory_is_excluded(self):
        self.write(".gitignore", "build/\n")
        self.write("build/generated/output.txt", "generated\n")
        self.write("build/generated/netlist.v", "module generated; endmodule\n")
        self.assertEqual(CHECKS.check_repository(self.root), [])

    def test_hdl_requires_sv_for_rtl_and_testbenches(self):
        for directory in ("fpga/rtl", "fpga/tb"):
            self.write(f"{directory}/README.md", "# HDL\n")
        self.write("fpga/README.md", "# FPGA\n")
        for directory in ("fpga/rtl", "fpga/tb"):
            for suffix in (".v", ".vh", ".svh", ".vhd", ".vhdl", ".V", ".SV"):
                with self.subTest(directory=directory, suffix=suffix):
                    name = f"{directory}/source{suffix}"
                    self.write(name, "module example; endmodule\n")
                    self.assertIn(f"HDL sources must use SystemVerilog .sv: {name}",
                                  CHECKS.check_repository(self.root))
                    (self.root / name).unlink()
            self.write(f"{directory}/source.sv", "module example; endmodule\n")
        self.assertEqual(CHECKS.check_repository(self.root), [])

    def test_staged_old_hdl_extension_cannot_be_hidden_by_rename(self):
        self.write("example.v", "module example; endmodule\n")
        self.git("add", ".")
        (self.root / "example.v").rename(self.root / "example.sv")
        self.assertEqual(CHECKS.check_repository(self.root), [])
        self.assertIn("HDL sources must use SystemVerilog .sv: example.v",
                      CHECKS.check_repository(self.root, staged=True))
        self.git("add", "-A")
        self.assertEqual(CHECKS.check_repository(self.root, staged=True), [])

    def test_staged_snapshot_cannot_be_hidden_by_worktree_fix(self):
        self.write("module/code.py", "pass\n")
        self.git("add", ".")
        self.write("module/README.md", "# Module\n\nIntroduction.\n")
        self.assertEqual(CHECKS.check_repository(self.root), [])
        self.assertIn(
            "Missing module/README.md",
            CHECKS.check_repository(self.root, staged=True),
        )
        self.git("add", "module/README.md")
        self.assertEqual(CHECKS.check_repository(self.root, staged=True), [])

    def test_markdown_validation(self):
        self.write("README.md", "# Example \n\nMissing newline")
        errors = CHECKS.check_repository(self.root)
        self.assertIn("Trailing whitespace: README.md:1", errors)
        self.assertIn("Missing final newline: README.md", errors)

    def test_main_and_invalid_branch_names_fail(self):
        for branch in ("main", "master", "feature", "feat/", "feat/no-id", "feat/Bad Name"):
            with self.subTest(branch=branch):
                self.assertTrue(CHECKS.check_repository(self.root, branch=branch))
        for branch in ("feat/f01-drive", "fix/uart-timeout", "docs/plan", "chore/repo-setup"):
            with self.subTest(branch=branch):
                self.assertEqual(CHECKS.check_repository(self.root, branch=branch), [])

    def enable_hooks(self):
        source = Path(__file__).resolve().parents[1]
        for name in ("pre-commit", "pre-push"):
            self.write(f".githooks/{name}", (source / ".githooks" / name).read_text())
            (self.root / ".githooks" / name).chmod(0o755)
        self.write(".githooks/README.md", "# Hooks\n\nLocal Git hooks.\n")
        self.write("tools/README.md", "# Tools\n\nRepository checker.\n")
        self.write("tools/check_repo.py", (source / "tools/check_repo.py").read_text())
        self.git("config", "core.hooksPath", ".githooks")
        self.git("config", "user.name", "AW-Car Test")
        self.git("config", "user.email", "aw-car-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("add", ".")

    def test_pre_commit_blocks_main_and_accepts_feature_branch(self):
        self.enable_hooks()
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        with self.assertRaises(subprocess.CalledProcessError) as failure:
            self.git("commit", "-m", "must fail")
        self.assertIn(b"never commit on main", failure.exception.stderr)
        self.git("symbolic-ref", "HEAD", "refs/heads/feat/f01-drive")
        self.git("commit", "-m", "feature commit")

    def test_pre_push_blocks_main_and_accepts_feature_branch(self):
        self.enable_hooks()
        self.git("symbolic-ref", "HEAD", "refs/heads/chore/test")
        self.git("commit", "-m", "setup commit")
        remote = tempfile.TemporaryDirectory()
        self.addCleanup(remote.cleanup)
        subprocess.run(
            ["git", "init", "--bare", "--quiet", remote.name],
            capture_output=True,
            check=True,
        )
        self.git("remote", "add", "origin", remote.name)
        with self.assertRaises(subprocess.CalledProcessError) as failure:
            self.git("push", "origin", "HEAD:refs/heads/main")
        self.assertIn(b"Push to main is blocked", failure.exception.stderr)
        self.git("push", "origin", "HEAD:refs/heads/chore/test")


if __name__ == "__main__":
    unittest.main()
