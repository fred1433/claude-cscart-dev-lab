# Walkthrough: explain, plan, change one file, undo

One real Claude Code session (2.1.296, model `claude-sonnet-5-5`, manual mode,
on a subscription), four prompts, run by `sessions/run_sessions.py` on a
throwaway copy of the synthetic fixture. Raw records:
[`evidence/sessions/s01_walkthrough/`](../evidence/sessions/s01_walkthrough/)
(readable version: [transcript.md](../evidence/sessions/s01_walkthrough/transcript.md)).

![Before, after, restored](walkthrough/before-after-restored.png)

The screenshots are of a **preview page**: `tools/render_preview.py` turns the
fixture's Smarty template and LESS file into static HTML, because the lab has
no CS-Cart install. The widths were measured on that page in a headless browser.

## 1. "Explain this first ... Do not change anything."

Claude listed the add-on's five files in a table, said what each does, and
what it could not confirm from the folder (where `lab_queue_mail` is defined,
where the block is placed, where the language strings live). On dependencies (bold removed):

> The form template's own dependencies are the shared pieces. It uses theme
> classes (`ty-input-text`, `ty-control-group`, `ty-btn`) [...]

It did not go further and find that those classes are defined in
`css/tygh/forms.less`, which the checkout template uses too. (An earlier run
named that file, but at the time the fixture carried a comment pointing to it;
the comment was removed and the sessions re-run.) This is why the developer,
not the model, validates shared dependencies before approving a task's files,
and why the task tool decides which files may be edited.

One search command was refused by the guard on the way, because its text
mentioned `.claude/`; Claude switched to other commands.

## 2. "Show the intended files ... Do not edit yet."

> **One file:** `design/themes/custom_theme/css/addons/catalog_request/styles.less`
>
> No other file. The template, the JS and the controller stay as they are.

followed by the exact block it proposed to add, including one rule per
checkbox label so each option sits on its own line.

## 3. The human opens the task, then: "Go ahead: make only this change, in that one file."

```
$ bin/claude-task start catalog-form-mobile design/themes/custom_theme/css/addons/catalog_request/styles.less
Task 'catalog-form-mobile' open on branch claude/catalog-form-mobile.
Baseline: commit 21cc95a2d120
  may edit: design/themes/custom_theme/css/addons/catalog_request/styles.less (baseline blob 9aa150170389)
```

In this recorded run the edit was **pre-approved on the command line**
(`--allowedTools "Edit(design/.../styles.less)"`) in place of a human
answering yes to the permission question; in the owner's interactive session
that question is asked. Claude made one Edit call; the guard logged it as
`edit inside task 'catalog-form-mobile'`.

Review prompt after looking at the phone preview: *"Check the interest
checkboxes at 375 px: each checkbox must stay on the same line as its own
label, one option per line. Adjust the same file if needed, and only that
file."* Claude checked the markup and its own rule and changed nothing:
"by my reading the checkboxes already behave the way you want." The preview
agrees (figure, panel 2).

`bin/claude-task diff` then shows the change, with no WARNING line (no other
tracked or new non-ignored file moved):
[task.diff](../evidence/sessions/s01_walkthrough/task.diff), one
`@media (max-width: 767px)` block, 27 lines added, nothing removed.

On the preview page ([widths.txt](walkthrough/widths.txt)): page width on a
375 px phone 818 px before, 375 px after (the form itself is 351 px wide);
desktop rendering unchanged.

## 4. "Show me how to undo it."

> Undoing is done by you with the project's task tool. I don't run it.
> [...]
> ```
> bin/claude-task undo
> ```

The human runs it:

```
$ bin/claude-task undo
OK   design/themes/custom_theme/css/addons/catalog_request/styles.less: now 9aa150170389, baseline 9aa150170389
Task 'catalog-form-mobile' undone. Back on main at baseline 21cc95a2d120.
```

The proof of the restore is the file's git blob hash compared with the one
recorded at `start`, not a message. The preview page is back to 818 px.
