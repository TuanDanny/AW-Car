"""Guard app-only USB updates against replacing deployed OTA credentials."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'utils'))
from flash_esp import verify_management_identity


class FlashIdentityTests(unittest.TestCase):
    def test_existing_identity_is_required_before_write(self):
        app=b'ESP image\x00eaa7df7e5511\x00other bytes'
        verify_management_identity(app,'eaa7df7e5511')
        for bad in ('781d10bfcb0e',None,'', 'eaa7df7e551', 'eaa7df7e551X'):
            with self.subTest(key_id=bad),self.assertRaises(ValueError):
                verify_management_identity(app,bad)

    def test_partial_or_unterminated_identity_does_not_match(self):
        for app in (b'eaa7df7e5511extra\0',b'eaa7df7e551',b''):
            with self.assertRaises(ValueError):
                verify_management_identity(app,'eaa7df7e5511')


if __name__=='__main__':
    unittest.main()
