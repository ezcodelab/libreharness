# SPDX-License-Identifier: MIT
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
import scan_private  # noqa: E402


class ScanPrivatePatternTests(unittest.TestCase):
    def matches(self, text):
        return any(
            re.compile(pattern).search(text)
            for pattern in scan_private.DEFAULT_PATTERNS
        )

    def test_semver_is_not_a_private_ip(self):
        self.assertFalse(self.matches('"node": "^8.16.0 || ^10.6.0"'))

    def test_rfc1918_addresses_are_detected(self):
        self.assertTrue(self.matches("host=" + "10." + "1.2.3"))
        self.assertTrue(self.matches("host=" + "172." + "16.0.1"))
        self.assertTrue(self.matches("host=" + "192." + "168.1.1"))

    def test_private_path_is_detected(self):
        self.assertTrue(
            self.matches("/home/" + "someone/Documents/" + "homelab/file")
        )


if __name__ == "__main__":
    unittest.main()
