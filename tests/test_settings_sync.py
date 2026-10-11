"""settings.json must be exactly what build_settings.py derives from policy.json."""
import json
import os
import sys
import unittest

LAB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(LAB, "kit", "admin"))
import build_settings  # noqa: E402


class SyncTest(unittest.TestCase):
    def test_settings_match_policy(self):
        with open(os.path.join(LAB, "kit", ".claude", "guard", "policy.json")) as handle:
            policy = json.load(handle)
        with open(os.path.join(LAB, "kit", ".claude", "settings.json")) as handle:
            settings = json.load(handle)
        self.assertEqual(settings, build_settings.build(policy))

    def test_fail_closed_and_bypass_lock_present(self):
        with open(os.path.join(LAB, "kit", ".claude", "settings.json")) as handle:
            settings = json.load(handle)
        for entry in settings["hooks"]["PreToolUse"][0]["hooks"]:
            self.assertEqual(entry["onFailure"], "block")
        self.assertEqual(settings["permissions"]["disableBypassPermissionsMode"], "disable")
        self.assertTrue(settings["sandbox"]["failIfUnavailable"])
        self.assertFalse(settings["sandbox"]["allowUnsandboxedCommands"])
        self.assertFalse(settings["sandbox"]["autoAllowBashIfSandboxed"])


if __name__ == "__main__":
    unittest.main()
