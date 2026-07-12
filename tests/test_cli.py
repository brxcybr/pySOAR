#!/usr/bin/env python3

import subprocess
import sys
import unittest


class TestCLISmoke(unittest.TestCase):
    def test_list_playbooks(self):
        result = subprocess.run(
            [sys.executable, "pysoar.py", "--list-playbooks"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("test", result.stdout)


if __name__ == "__main__":
    unittest.main()
