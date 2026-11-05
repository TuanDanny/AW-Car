"""Compile the firmware reconnect policy; test outages using a virtual clock."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ReconnectTests(unittest.TestCase):
    def test_bounded_scan_auth_dhcp_flap_and_cloud_independence(self):
        compiler=os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
        if not compiler: raise RuntimeError("Native C++17 compiler required")
        out=ROOT/"build/brain"/("reconnect-test.exe" if os.name=="nt" else "reconnect-test")
        out.parent.mkdir(parents=True,exist_ok=True)
        flags=["-std=c++17","-Wall","-Wextra","-Werror"]+(["-static"] if os.name=="nt" else [])
        subprocess.run([compiler,*flags,"-I"+str(ROOT/"firmware/brain/main/aw_car"),str(ROOT/"tests/brain_http_stub/reconnect_policy_test.cc"),"-o",str(out)],check=True)
        r=subprocess.run([str(out)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        self.assertIn("PASS",r.stdout)
