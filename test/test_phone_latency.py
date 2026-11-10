import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('phone_latency',Path(__file__).resolve().parents[1]/'utils/analyze_phone_latency.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PhoneLatency(unittest.TestCase):
    def test_incomplete_and_malformed_are_not_pass(self):
        result=module.summarize('latency_probe: action=forward dispatch_us=90 confirm_us=5')
        self.assertIsNone(result['pass']);self.assertFalse(result['enough_samples'])
    def test_known_samples_and_budgets(self):
        text='\n'.join(f'latency_probe: action={a} dispatch_us=1000 confirm_us={n*1000}' for a in module.ACTIONS for n in range(1,11))
        result=module.summarize(text);self.assertTrue(result['pass'])
        self.assertEqual(result['directions']['left']['setpoint_status']['p95_ms'],10)
        slow=text.replace('confirm_us=10000','confirm_us=400000')
        self.assertFalse(module.summarize(slow)['pass'])
