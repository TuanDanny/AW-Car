"""Build identity must change when compiler defaults change."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_esp', ROOT/'utils/build_esp.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BuildIdentity(unittest.TestCase):
    def test_defaults_and_generated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root/'esp/motion'
            project.mkdir(parents=True)
            defaults = project/'sdkconfig.defaults'
            defaults.write_text('CONFIG_OPTION=n\n')
            before = module.source_digest(root, 'motion')
            defaults.write_text('CONFIG_OPTION=y\n')
            after = module.source_digest(root, 'motion')
            self.assertNotEqual(before, after)
            (project/'sdkconfig').write_text('generated')
            (project/'build').mkdir()
            (project/'build/cache').write_text('generated')
            self.assertEqual(after, module.source_digest(root, 'motion'))
