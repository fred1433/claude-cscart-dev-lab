"""Recovery tests: a task is undone, nothing else moves, and nothing done outside the task is hidden.

Replays the cases found in review: a shell write (sed -i) to the stylesheet
shared with checkout during a task must show up in `diff` as a WARNING and
make `undo` fail loudly while leaving it in place; a file the developer
creates during the task must not be moved; pre-existing uncommitted work must
not be touched or reported.
"""
import os
import subprocess
import unittest

from helpers import new_workspace, task

STYLES = "design/themes/custom_theme/css/addons/catalog_request/styles.less"
FORMS = "design/themes/custom_theme/css/tygh/forms.less"
OTHER = "js/addons/catalog_request/func.js"


def blob(ws, path):
    return subprocess.run(["git", "hash-object", path], cwd=ws, stdout=subprocess.PIPE,
                          universal_newlines=True, check=True).stdout.strip()


def git(ws, *args):
    return subprocess.run(["git"] + list(args), cwd=ws, stdout=subprocess.PIPE, universal_newlines=True,
                          check=True).stdout


def write(ws, path, text, mode="a"):
    with open(os.path.join(ws, path), mode) as handle:
        handle.write(text)


class UndoTest(unittest.TestCase):
    def setUp(self):
        self.ws = new_workspace(with_prod=False)
        self.baseline_styles = blob(self.ws, STYLES)
        # the developer's work in progress, before the task starts
        write(self.ws, OTHER, "// developer's unfinished change\n")
        self.dev_other = blob(self.ws, OTHER)
        write(self.ws, "dev-notes.txt", "developer notes, untracked\n", "w")

    def start(self):
        out = task(self.ws, "start", "mobile-form", STYLES)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_clean_task_undo(self):
        self.start()
        write(self.ws, STYLES, "@media (max-width: 600px) { .ty-catalog-request { width: auto; } }\n")
        diff = task(self.ws, "diff").stdout
        self.assertIn("+@media", diff)
        self.assertNotIn("WARNING", diff)  # pre-existing work is not reported as task damage
        out = task(self.ws, "undo")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("OK   %s" % STYLES, out.stdout)
        self.assertEqual(blob(self.ws, STYLES), self.baseline_styles)
        self.assertEqual(blob(self.ws, OTHER), self.dev_other)
        self.assertTrue(os.path.exists(os.path.join(self.ws, "dev-notes.txt")))
        self.assertEqual(git(self.ws, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")

    def test_shell_write_outside_scope_is_reported_and_not_hidden(self):
        self.start()
        write(self.ws, STYLES, "/* task edit */\n")
        # what a sed -i through the shell does: the guard and the sandbox do not stop it,
        # because forms.less is neither protected nor outside the dev copy
        subprocess.run(["sed", "-i.bak", "s/margin-bottom: 4px/margin-bottom: 8px/", FORMS], cwd=self.ws, check=True)
        os.remove(os.path.join(self.ws, FORMS + ".bak"))
        forms_after_shell = blob(self.ws, FORMS)
        diff = task(self.ws, "diff").stdout
        self.assertIn("WARNING", diff)
        self.assertIn(FORMS, diff)
        out = task(self.ws, "undo")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("NOT UNDONE", out.stdout)
        self.assertIn(FORMS, out.stdout)
        self.assertEqual(blob(self.ws, STYLES), self.baseline_styles)  # task file restored
        self.assertEqual(blob(self.ws, FORMS), forms_after_shell)     # left in place, reported
        self.assertTrue(os.path.exists(os.path.join(self.ws, ".claude", "task.json")))  # task stays open
        # once the developer resolves it, undo completes
        git(self.ws, "checkout", "--", FORMS)
        out = task(self.ws, "undo")
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertEqual(blob(self.ws, OTHER), self.dev_other)

    def test_file_created_during_task_is_never_moved(self):
        self.start()
        write(self.ws, "dev-second-note.txt", "created by the developer during the task\n", "w")
        write(self.ws, "design/themes/custom_theme/css/new-file.less", "/* created during the task */\n", "w")
        diff = task(self.ws, "diff").stdout
        self.assertIn("dev-second-note.txt", diff)
        self.assertIn("new-file.less", diff)
        out = task(self.ws, "undo")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("dev-second-note.txt", out.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.ws, "dev-second-note.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.ws, "design/themes/custom_theme/css/new-file.less")))
        self.assertFalse(os.path.exists(os.path.join(self.ws, ".claude-task-trash")))

    def test_refuses_task_on_file_with_uncommitted_changes(self):
        write(self.ws, STYLES, "/* someone else's edit */\n")
        out = task(self.ws, "start", "x", STYLES)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("uncommitted changes", out.stdout)

    def test_refuses_protected_file_in_scope(self):
        out = task(self.ws, "start", "x", "app/functions/fn.cart.php")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("refused", out.stdout)


if __name__ == "__main__":
    unittest.main()
