# Owner guide: one small change, start to finish

For the store owner. No programming needed. Your developer sets things up once
(see the [developer guide](developer-guide.md)); after that, every task looks
like this.

## 1. Open a task (one command)

Name the task and the file(s) Claude may change. Your developer can tell you
which file holds what you want to change.

```
bin/claude-task start mobile-catalog-form design/themes/<theme>/css/addons/catalog_request/styles.less
```

The tool records a starting point (the "baseline") and refuses files that
touch checkout, cart, orders, prices, payments, the database or the rules.

## 2. Start Claude Code and check the mode

```
claude
```

Look at the bottom of the screen. It should say **manual mode on**. If it
says anything else, press `Shift+Tab` until it does (the kit removes auto mode
from that cycle). In manual mode Claude asks before every change and every
command, and you answer yes or no.

## 3. Four sentences, in this order

1. **"Explain this first: what does the catalog request form do, which files
   make it up, and what else uses them? Don't change anything."**
2. **"Show me the intended files and the smallest change you would make. Don't
   edit yet."** If the answer mentions a file you did not put in the task, or
   anything about checkout, stop here and ask your developer.
3. **"Make only this change."** Claude shows each edit and asks permission.
   Read the file name in the question before you say yes, and do the same
   when it asks to run a command: a command can change a file too (for example
   `sed -i ... forms.less`). The task's file list binds Claude's edit tools,
   not commands; if a command names a file outside your task, answer no.
4. **"Show me how to undo it."**

If Claude says something was **blocked by the guard**, that is the safety
system doing its job. Do not ask Claude to find another way; ask your developer.

## 4. Look at the result

```
bin/claude-task diff
```

shows what changed in the task's files, line by line (red removed, green
added), and prints a **WARNING** line for any other file that changed or
appeared in the folder since the task started. A WARNING means something
outside the task moved: stop and show it to your developer. Then look
at the dev site. After a template or style change, the dev site may still show
the old version until its cache is cleared; your developer will tell you how
that is done on your setup.

## 5. Keep it or undo it

- **Undo:** `bin/claude-task undo`. It puts the task's files back exactly as
  they were and prints `OK` with the same fingerprint as the starting point.
  It does not touch anything else. If something outside the task changed
  meanwhile, undo says **NOT UNDONE** with the file names and keeps the task
  open: your developer decides what to do with those files.
- **Keep:** `bin/claude-task finish "Catalog form fits on phones"`. It saves
  the change on its own branch, and your developer reviews it before it goes
  anywhere near the live shop.

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
