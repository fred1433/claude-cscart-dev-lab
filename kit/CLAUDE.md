# Working rules for Claude Code on this CS-Cart dev copy

This folder is a development copy of a customised CS-Cart 4.x store. It is not
the live shop. The person you work with is the store owner, who is not a
developer; a CS-Cart developer works on the same code.

## How every task goes
1. **Explain first.** Read the files involved and explain, in plain words, what
   they do and what else uses them. Do not change anything at this step.
2. **Show the intended files.** List the exact files you would change and the
   smallest change that does the job. Wait for a go.
3. **Make only that change.** Only files listed in the open task
   (`.claude/task.json`) can be edited with the file tools; a guard blocks the
   rest. Do not change any other file through shell commands either.
4. **Show the diff and how to undo it**: `bin/claude-task diff`, then
   `bin/claude-task undo` (the human runs it).

If a "visual" request needs a file shared with checkout, cart, orders or
payment (for example a global stylesheet or a common script), stop and say so.
Do not look for another way in.

## Never, in this workflow
- Prices, discounts, taxes, cart, checkout, orders, payments, promotions.
- The database: no SQL, no `mysql` client, no schema or data scripts. You have
  no database credentials and must not look for them (`config.local.php` is
  off limits).
- Servers: no `ssh`, `scp`, `rsync`, FTP, `git push`, deploys.
- The rules themselves: `.claude/`, this file, `bin/claude-task`.
- Git history: no commit, reset, clean, stash, restore. The human uses
  `bin/claude-task`.

When something is blocked, report it with the exact message. Do not retry the
same goal through another command, interpreter or path.

## CS-Cart 4.x layout (generic, check it against this install)
- `app/controllers/frontend/` and `app/controllers/backend/`: storefront and
  admin controllers, one file per area, branched on `$mode`.
- `app/functions/fn.*.php`: core functions (`fn.cart.php` holds cart, totals
  and orders).
- `app/payments/`: payment processor scripts.
- `app/addons/<addon>/`: add-ons (`addon.xml`, `func.php`, `init.php`,
  controllers). PHP hooks: core code calls `fn_set_hook('name', ...)` and an
  add-on registers its functions for that hook in `init.php`.
- `design/themes/<theme>/templates/`: Smarty `.tpl` templates. Template hooks
  are `{hook name="section:name"}...{/hook}` blocks; add-ons extend them with
  files under `templates/addons/<addon>/hooks/`.
- `design/themes/<theme>/css/`: LESS styles (`.less`), compiled by CS-Cart.
- `js/tygh/` core scripts, `js/addons/<addon>/` add-on scripts.
- `var/cache/`: compiled templates and styles. After a `.tpl` or `.less`
  change, the cache must be cleared before the dev site shows it: tell the
  human, do not do it yourself.
- "Hooks" above means CS-Cart hooks. The Claude Code checks that block tool
  calls are called **guards** in this project.

## This install (UNVERIFIED until the developer fills it in)
- CS-Cart version: UNVERIFIED
- PHP version on the dev server: UNVERIFIED. Ask the human to run `php -v`
  before you write any PHP, and use no syntax newer than that version.
- Active theme folder: UNVERIFIED
- Customised add-ons and core overrides: UNVERIFIED
- Files shared between the storefront and checkout (stylesheets, scripts):
  UNVERIFIED. Until the developer lists them, check who includes a file
  before proposing to change it.
- How a change reaches the dev site (same folder, deploy step, cache): UNVERIFIED
