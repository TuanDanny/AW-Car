"""Source scan must separate the main checkout from a nested Git worktree."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"utils"))
from check_repo import check

class RepoHygieneTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        for name in ("esp","fpga","schematic","docs","data","utils","test"):
            path=self.root/name
            path.mkdir()
            (path/"README.md").write_text("# Source\n")

    def test_nested_git_worktree_is_separate(self):
        nested=self.root/"simplev1"
        nested.mkdir()
        (nested/".git").write_text("gitdir: ../.git/worktrees/simplev1\n")
        (nested/"private.bin").write_bytes(b"not part of main source")
        self.assertEqual(check(self.root),[])

    def test_unmanaged_extra_directory_is_still_reported(self):
        (self.root/"old-source").mkdir()
        self.assertTrue(any("top-level directories" in error for error in check(self.root)))

    def test_source_artifacts_are_still_reported(self):
        (self.root/"esp"/"nvs-dump.bin").write_bytes(b"invalid tracked artifact")
        errors=check(self.root)
        self.assertTrue(any("forbidden" in error for error in errors))
        self.assertTrue(any("private artifact" in error for error in errors))
