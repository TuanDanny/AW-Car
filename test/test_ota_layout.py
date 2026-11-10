"""Check the proposed Motion OTA layout without accessing a board."""
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_layout(path):
    rows = (line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#"))
    return {row[0].strip(): (row[1].strip(), row[2].strip(),
                             int(row[3].strip(), 0), int(row[4].strip(), 0))
            for row in csv.reader(rows)}


class OtaLayoutTest(unittest.TestCase):
    def test_candidate_preserves_existing_partitions(self):
        motion = ROOT / "esp" / "motion"
        old = read_layout(motion / "partitions.csv")
        new = read_layout(motion / "partitions_ota_candidate.csv")
        for name, entry in old.items():
            self.assertEqual(new[name], entry, name)
        self.assertEqual(new["otadata"][:2], ("data", "ota"))
        self.assertEqual(new["otadata"][3], 0x2000)
        for name in ("ota_0", "ota_1"):
            self.assertEqual(new[name][:2], ("app", name))
            self.assertEqual(new[name][2] % 0x10000, 0)
            self.assertGreaterEqual(new[name][3], old["factory"][3])
        regions = sorted((offset, offset + size, name)
                         for name, (_, _, offset, size) in new.items())
        for first, second in zip(regions, regions[1:]):
            self.assertLessEqual(first[1], second[0], (first, second))
        self.assertLessEqual(regions[-1][1], 16 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
