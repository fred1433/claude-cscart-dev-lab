# Owner guide: one small change, start to finish

For the store owner, on tasks your developer has framed: which files the task
may change, and which commands you may approve. Within that frame no
programming is needed. A new kind of task, new files or new commands go back
to your developer first (see the [developer guide](developer-guide.md)).
Every framed task looks like this.

## 1. Open a task (one command)

Name the task and the file(s) Claude may change. In this lab, the exercise is:

```
bin/claude-task start mobile-catalog-form design/themes/custom_theme/css/addons/catalog_request/styles.less
```

For your real store, your developer gives you the complete command for each
task. The tool records a starting point (the "baseline"). It refuses paths
your developer has marked as protected; it does not know by itself which files
are shared with checkout. Your developer checks shared dependencies before
approving the task's files.

## 2. Start Claude Code and check the mode

```
claude
```

Look at the bottom of the screen. It should say **manual mode on**. If it
says anything else, press `Shift+Tab` until it does (the kit removes auto mode
from that cycle). In manual mode Claude asks before editing a file and before
running a command that is not pre-approved; reading files and a few read-only
commands (such as `git status`, `git diff`) run without asking.

## 3. Four sentences, in this order

1. **"Explain this first: what does the catalog request form do, which files
   make it up, and what else uses them? Don't change anything."**
2. **"Show me the intended files and the smallest change you would make. Don't
   edit yet."** If the answer mentions a file you did not put in the task, or
   anything about checkout, stop here and ask your developer.
3. **"Make only this change."** Claude asks permission before each step.
   The rule for answering:
   - **an edit**: approve it only when its file is one of the task's files;
   - **a command**: approve it only if it is on the checklist your developer
     gave you (a command can change files that are not in the task, and its
     targets are not always visible in its text);
   - **anything else, including any request to open network access**: choose
     **No** and ask your developer;
   - never select "don't ask again".
4. **"Show me how to undo it."**

If Claude says something was **blocked by the guard**, that is the safety
system doing its job. Do not ask Claude to find another way; ask your developer.

## 4. Look at the result

```
bin/claude-task diff
```

shows what changed in the task's files, line by line (red removed, green
added, including the content of new task files), and prints a **WARNING**
line for any other tracked file that changed, or any new file that git does
not ignore, since the task started. A WARNING means something outside the
task moved: stop and show it to your developer. The database and ignored
folders (such as `var/` and `images/`) are not watched. Then look
at the dev site. After a template or style change, the dev site may still show
the old version until its cache is cleared; your developer will tell you how
that is done on your setup.

## 5. Keep it or undo it

- **Undo:** `bin/claude-task undo`. It puts the task's files back exactly as
  they were and prints `OK` with the same fingerprint as the starting point.
  It does not touch anything else. If something outside the task changed
  meanwhile, undo says **NOT UNDONE** with the file names and keeps the task
  open: your developer decides what to do with those files. Undo does not
  cover the database or ignored folders.
- **Keep:** `bin/claude-task finish "Catalog form fits on phones"`. It saves
  exactly the task's files (changes, new files and deletions) in one commit
  on the task's own branch, and nothing else; if that fails the task stays
  open. Your developer reviews it before it goes anywhere near the live shop.

## How to stop Claude

- `Esc`: stops what Claude is doing right now. On a permission question,
  `Esc` means **no**.
- `Ctrl+C` twice, or type `/exit`: closes Claude Code.

## What this setup is built to prevent

It is set up so that Claude does not touch the live shop, the database,
payments, prices or checkout, and is given no passwords. Several independent
layers do this, each one tested on dummy files; the
[results page](../evidence/RESULTS.md) shows the tests, including what got
through when a layer was switched off, and the
[developer guide](developer-guide.md#2-the-layers-and-what-each-one-does-not-do)
lists what each layer does not stop. One example: PHP code that Claude writes
runs on your dev site with the dev site's own access, so your developer checks
that this access is limited (developer guide, section 3).
