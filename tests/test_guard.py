"""Deterministic tests of the guard script alone (no model, no Claude Code).

They prove what guard.py decides for a given tool call. They do NOT prove that
Claude Code loads it; the recorded sessions in evidence/sessions/ do that.
"""
import os
import shutil
import unittest

from helpers import guard, new_workspace, task

STYLES = "design/themes/custom_theme/css/addons/catalog_request/styles.less"


class GuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = new_workspace()
        out = task(cls.ws, "start", "unit", STYLES)
        assert out.returncode == 0, out.stdout

    def assertBlocked(self, tool, tool_input, reason_part):
        code, err = guard(self.ws, tool, tool_input)
        self.assertEqual(code, 2, err)
        self.assertIn(reason_part, err)

    def assertAllowed(self, tool, tool_input):
        code, err = guard(self.ws, tool, tool_input)
        self.assertEqual(code, 0, err)

    # permitted component edit
    def test_edit_inside_task(self):
        self.assertAllowed("Edit", {"file_path": os.path.join(self.ws, STYLES)})

    # direct sensitive edit
    def test_edit_cart_functions(self):
        self.assertBlocked("Edit", {"file_path": "app/functions/fn.cart.php"}, "protected by policy rule")

    def test_write_payment_script(self):
        self.assertBlocked("Write", {"file_path": "app/payments/new_gateway.php"}, "app/payments/**")

    def test_edit_checkout_template(self):
        self.assertBlocked("Edit", {"file_path": "design/themes/custom_theme/templates/views/checkout/components/customer_info.tpl"},
                           "views/checkout")

    def test_edit_sql_anywhere(self):
        self.assertBlocked("Write", {"file_path": "var/fix_prices.sql"}, "**/*.sql")

    # scope: a visual request that reaches a shared dependency
    def test_shared_stylesheet_outside_task(self):
        self.assertBlocked("Edit", {"file_path": "design/themes/custom_theme/css/tygh/forms.less"},
                           "not in the file list of task")

    # path aliases
    def test_dotdot_alias(self):
        self.assertBlocked("Edit", {"file_path": "design/../app/payments/example_gateway.php"}, "protected")

    def test_symlink_alias(self):
        link = os.path.join(self.ws, "design", "harmless.less")
        os.symlink(os.path.join(self.ws, "app", "functions", "fn.cart.php"), link)
        try:
            self.assertBlocked("Edit", {"file_path": link}, "protected")
        finally:
            os.remove(link)

    def test_edit_in_production_copy(self):
        self.assertBlocked("Edit", {"file_path": "../prod/" + STYLES}, "production copy")

    # secrets
    def test_read_config_local(self):
        self.assertBlocked("Read", {"file_path": "config.local.php"}, "holds secrets")

    def test_grep_config_local(self):
        self.assertBlocked("Grep", {"pattern": "db_password", "path": "config.local.php"}, "holds secrets")

    def test_bash_cat_secret(self):
        self.assertBlocked("Bash", {"command": "cat config.local.php"}, "config.local.php")

    # policy tampering
    def test_edit_policy(self):
        self.assertBlocked("Edit", {"file_path": ".claude/guard/policy.json"}, ".claude/**")

    def test_edit_settings(self):
        self.assertBlocked("Write", {"file_path": ".claude/settings.json"}, ".claude/**")

    def test_edit_task_scope(self):
        self.assertBlocked("Write", {"file_path": ".claude/task.json"}, ".claude/**")

    def test_bash_touch_policy(self):
        self.assertBlocked("Bash", {"command": "sed -i 's/x/y/' .claude/guard/policy.json"}, ".claude/")

    # database, production, network
    def test_bash_mysql(self):
        self.assertBlocked("Bash", {"command": "mysql -u shop_dev_app -e 'DELETE FROM lab_orders'"}, "'mysql'")

    def test_bash_mysql_in_chain(self):
        self.assertBlocked("Bash", {"command": "cd /tmp && /usr/bin/mysql shop_dev < x"}, "'mysql'")

    def test_bash_rsync(self):
        self.assertBlocked("Bash", {"command": "rsync -a design/ shop@prod.example.test:/var/www/"}, "'rsync'")

    def test_bash_git_push(self):
        self.assertBlocked("Bash", {"command": "git push origin main"}, "git")

    def test_bash_curl(self):
        self.assertBlocked("Bash", {"command": "curl -X POST http://receiver.example.test/"}, "'curl'")

    def test_bash_prod_relative(self):
        self.assertBlocked("Bash", {"command": "echo x >> ../prod/js/addons/catalog_request/func.js"}, "'..'")

    def test_bash_git_history_and_task_commands(self):
        for cmd in ("git commit -am wip", "git switch main", "git checkout main -- design",
                    "bin/claude-task start x design/themes/custom_theme/css/tygh/forms.less",
                    "python3 bin/claude-task undo", "bin/claude-task finish done", "git add -A", "git stash"):
            self.assertBlocked("Bash", {"command": cmd}, "reserved to the human")

    def test_bash_task_diff_and_status_allowed(self):
        for cmd in ("bin/claude-task diff", "bin/claude-task status", "git diff", "git status", "git log -3"):
            self.assertAllowed("Bash", {"command": cmd})

    def test_known_gap_shell_write_to_unprotected_file_passes_guard(self):
        # the task scope binds Claude's file tools only; this is reported by claude-task diff/undo instead
        self.assertAllowed("Bash", {"command": "sed -i 's/4px/8px/' design/themes/custom_theme/css/tygh/forms.less"})

    def test_bash_reset_hard(self):
        self.assertBlocked("Bash", {"command": "git reset --hard HEAD"}, "reserved to the human")

    # the documented limit: the guard is not a shell parser
    def test_known_gap_obfuscated_python_passes_guard(self):
        cmd = "python3 -c \"p='app/pay'+'ments/example_gateway.php'; open(p,'a').write('//x')\""
        self.assertAllowed("Bash", {"command": cmd})

    def test_known_gap_variable_program_name_passes_guard(self):
        self.assertAllowed("Bash", {"command": "c=my; c=${c}sql; $c -e 'DELETE FROM lab_orders'"})

    # no open task
    def test_no_task_blocks_every_edit(self):
        ws = new_workspace(with_prod=False)
        code, err = guard(ws, "Edit", {"file_path": STYLES})
        self.assertEqual(code, 2)
        self.assertIn("no task is open", err)


class FailClosedTest(unittest.TestCase):
    """The guard's own failure paths. Claude Code's onFailure: "block" is tested in real sessions."""

    def setUp(self):
        self.ws = new_workspace(with_prod=False)
        self.policy = os.path.join(self.ws, ".claude", "guard", "policy.json")

    def test_malformed_policy_blocks(self):
        with open(self.policy, "w") as handle:
            handle.write("{ not json")
        code, err = guard(self.ws, "Read", {"file_path": "README.md"})
        self.assertEqual(code, 2)
        self.assertIn("internal error", err)

    def test_wrong_policy_shape_blocks(self):
        with open(self.policy, "w") as handle:
            handle.write('{"version": 1, "protected_edit": "app/payments/**"}')
        code, err = guard(self.ws, "Read", {"file_path": "README.md"})
        self.assertEqual(code, 2)

    def test_missing_policy_blocks(self):
        os.remove(self.policy)
        code, err = guard(self.ws, "Read", {"file_path": "README.md"})
        self.assertEqual(code, 2)

    def test_garbage_stdin_blocks(self):
        import subprocess
        import sys
        script = os.path.join(self.ws, ".claude", "guard", "guard.py")
        result = subprocess.run([sys.executable, script], input="{{{", stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
