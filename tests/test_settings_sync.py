"""Settings are generated from the policy file that is passed explicitly."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

LAB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
BUILD = os.path.join(LAB, "kit", "admin", "build_settings.py")
KIT_POLICY = os.path.join(LAB, "kit", ".claude", "guard", "policy.json")
FORMS = "design/themes/custom_theme/css/tygh/forms.less"
SECRET = "/srv/secrets/database.key"


def build(*args):
    result = subprocess.run([sys.executable, BUILD] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


class SyncTest(unittest.TestCase):
    def test_kit_settings_match_kit_policy(self):
        out = os.path.join(tempfile.mkdtemp(), "settings.json")
        build("--policy", KIT_POLICY, "--out", out)
        with open(out) as a, open(os.path.join(LAB, "kit", ".claude", "settings.json")) as b:
            self.assertEqual(json.load(a), json.load(b))

    def test_fail_closed_and_mode_locks_present(self):
        with open(os.path.join(LAB, "kit", ".claude", "settings.json")) as handle:
            settings = json.load(handle)
        for entry in settings["hooks"]["PreToolUse"][0]["hooks"]:
            self.assertEqual(entry["onFailure"], "block")
        self.assertEqual(settings["permissions"]["disableBypassPermissionsMode"], "disable")
        self.assertEqual(settings["permissions"]["disableAutoMode"], "disable")
        self.assertTrue(settings["sandbox"]["failIfUnavailable"])
        self.assertFalse(settings["sandbox"]["allowUnsandboxedCommands"])
        self.assertFalse(settings["sandbox"]["autoAllowBashIfSandboxed"])

    def test_required_explicit_policy(self):
        result = subprocess.run([sys.executable, BUILD, "--out", "/dev/null"], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)


class AdaptedPolicyTest(unittest.TestCase):
    """An installed policy with a shared file added and an absolute secret, in both modes."""

    def setUp(self):
        with open(KIT_POLICY) as handle:
            policy = json.load(handle)
        policy["protected_edit"].append(FORMS)
        policy["secret_read"].append(SECRET)
        self.dir = tempfile.mkdtemp()
        self.policy = os.path.join(self.dir, "policy.json")
        with open(self.policy, "w") as handle:
            json.dump(policy, handle)

    def test_project_mode(self):
        out = os.path.join(self.dir, "settings.json")
        build("--policy", self.policy, "--out", out)
        deny = json.load(open(out))["permissions"]["deny"]
        self.assertIn("Edit(/%s)" % FORMS, deny)
        self.assertIn("Read(//srv/secrets/database.key)", deny)

    def test_managed_mode(self):
        deny = json.loads(build("--policy", self.policy, "--managed", "/srv/dev/shop",
                                "/opt/claude-cscart-guard"))["permissions"]["deny"]
        self.assertIn("Edit(//srv/dev/shop/%s)" % FORMS, deny)
        self.assertIn("Read(//srv/secrets/database.key)", deny)
        self.assertFalse([r for r in deny if "shop//" in r])


if __name__ == "__main__":
    unittest.main()
