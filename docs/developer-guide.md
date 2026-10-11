# Developer guide: install, adapt, verify

Audience: the CS-Cart developer who maintains the store. Everything here was
written against Claude Code 2.1.296 and the documentation pages under
`code.claude.com/docs/en/` (permissions, hooks, sandboxing, settings,
managed-settings, permission-modes, checkpointing) read on 2026-10-11. Re-run
the tests after every Claude Code update (section 9).

## 1. Threat model

Contained: mistakes and actions of the agent running under the **dev
identity** (the Unix account Claude Code runs as), including the owner
approving a change without fully reading it.

Not contained: someone acting as the server administrator. An admin can
change any policy file; that is by design.

Two separate requirements, tested separately:

1. **No authority over production**: the dev identity cannot write the
   production files and its database account cannot touch the production
   schema. This is enforced by Unix permissions and MySQL grants, not by Claude.
2. **No database operation in the owner's front-end workflow**: Claude gets
   no database credential and no SQL tool at all. A credential limited to the
   dev database can still damage the dev database. The dev application keeps
   its own restricted account in `config.local.php`, which Claude cannot read.

## 2. The layers, and what each one does not do

| Layer | Stops | Does not stop |
|---|---|---|
| `CLAUDE.md` | Nothing. It is guidance; the model usually follows it (see the "operating config" sessions). | Anything, if the model ignores or misreads it. |
| Permission deny rules (`settings.json`) | Claude Code's file tools on listed paths, in every mode. Recognised shell file commands (`cat`, `sed`, redirects) on those paths. | A Python or Node script that opens the file itself (documented). |
| Guard (`.claude/guard/guard.py`, a PreToolUse hook) | Edits with Claude's file tools outside the open task, edits to protected files, reads of secrets, shell commands naming DB clients, servers, network tools, protected paths, git history/branch commands or `bin/claude-task start/undo/finish`, `..` escapes. Readable messages. | Anything written so its text does not match (`'app/pay'+'ments'`, `c=my; ${c}sql`). It is a text filter, not a shell parser. **The task's file list binds the file tools only**: a shell command such as `sed -i` on an unprotected file outside the task passes the guard and the sandbox. `bin/claude-task diff` and `undo` report it (WARNING / NOT UNDONE); they do not prevent it. |
| Sandbox (`sandbox.*`) | Bash and every child process: writes outside the dev copy and to protected paths, reads of `config.local.php` and `~/.ssh`, all network. | Claude Code's own file tools and hooks (they run outside it; the deny rules and guard cover them). |
| Unix permissions and MySQL grants | The dev identity, whatever program it runs, Claude or not. | Nothing below the admin. This is the real boundary. |

The recorded runs show each layer separately, including cases where an
earlier layer let the attempt through (for example the Python write that the
guard misses and the sandbox stops).

## 3. Before you install: adoption checklist

Check these on the real dev copy. None of them can be checked from this lab.

- **PHP identity**: which Unix user runs the dev site's PHP (php-fpm pool
  `user =`, or the web server user)? Code that Claude writes runs as that user
  when the page loads. It must not have write access to production files.
- **Copied production credentials**: is `config.local.php` on the dev copy
  pointing at the dev database? Does the dev copy still hold live keys for
  payment processors, mail or shipping APIs (in CS-Cart many of these live in
  the database settings, not in files)? Switch them to test mode or blank them.
- **Outbound integrations**: payment callbacks, order emails, feeds, ERP or
  marketplace syncs. A dev copy that can still send real emails or real API
  calls is a risk even if Claude never touches the database.
- **Database rights**: the dev application's MySQL account should have grants
  on the dev schema only. Check with `SHOW GRANTS FOR 'user'@'host';` and try
  one forbidden statement on the production schema: you want an *access
  denied* error (1142 or 1044), not a *can't connect* error.

## 4. Two topologies

**Dev copy on another machine than production.** Check that the dev machine
holds no production credential: no SSH key or config entry for the production
host, no production database password, no deploy tool configured. The kit's
guard and deny rules also refuse `ssh`, `scp`, `rsync`, FTP and `git push`.

**Dev copy on the same server (and MySQL) as production.** Then the
boundary must be Unix and MySQL, because a name filter does not cover
`../public_html` or `localhost`:

- run Claude Code as a dedicated dev account, not as the account that owns
  the production web root;
- production files owned by another account, not writable by the dev account
  (the lab checks append, delete, rename, copy-over, symlink-over and new
  file; all must fail with *Permission denied*);
- the dev MySQL account granted on the dev schema only (checked over the Unix
  socket and over TCP separately: a TCP failure says nothing about the socket);
- set `production_roots` in `policy.json` to the real production path, so the
  guard also names it in its messages.

## 5. Install

### Try it (project mode)

From the root of the dev copy, in this order:

```
# 1. keep secrets and generated files out of git, before anything is added
printf 'config.local.php\nvar/\nimages/\n.claude/task.json\n.claude-task-trash/\n' >> .gitignore
# 2. copy the kit
cp -R /path/to/lab/kit/.claude /path/to/lab/kit/CLAUDE.md .
mkdir -p bin && cp /path/to/lab/kit/bin/claude-task bin/
# 3. check that config.local.php is ignored, then commit the code and the rules together
git init                      # only if the copy is not under git yet
git status --ignored | grep config.local.php
git add -A && git commit -m "baseline before Claude Code, with the Claude Code rules"
```

The rules are now versioned with the code, so you and the owner work with the
same ones.

Then adapt the one policy file, `.claude/guard/policy.json` (protected paths,
secret files, production path), and regenerate the settings from it:

```
python3 /path/to/lab/kit/admin/build_settings.py   # in the lab, then copy settings.json again
```

Two behaviours seen in our own runs:

- In a folder Claude Code has never been trusted in, it ignores the
  `permissions.allow` entries of the project settings until someone accepts
  the trust dialog interactively once (the deny rules, hooks and sandbox
  still apply). Open `claude` interactively in the dev copy once.
- The guard refuses any shell command that *names* a protected file, even a
  harmless `grep`. Claude then uses its Read tool, which is allowed.

### Shared server (admin mode, recommended)

Project files can be changed by whoever owns the dev copy. On a server, put
the policy where the dev account can read but not write it:

```
sudo mkdir -p /opt/claude-cscart-guard /etc/claude-code
sudo cp kit/.claude/guard/guard.py /opt/claude-cscart-guard/
# policy.json with "project_root": "/abs/path/to/dev", "production_roots": ["/abs/path/to/prod"]
sudo cp policy.json /opt/claude-cscart-guard/
python3 kit/admin/build_settings.py --managed /abs/path/to/dev /opt/claude-cscart-guard \
  | sudo tee /etc/claude-code/managed-settings.json
sudo chmod 755 /opt/claude-cscart-guard /etc/claude-code
sudo chmod 644 /opt/claude-cscart-guard/* /etc/claude-code/managed-settings.json
```

Managed settings are not one of the sources `--setting-sources` chooses from (user, project, local), and they are
where `sandbox.network.strictAllowlist` is honoured (project settings cannot
set it). Also keep the Claude Code binary and Python owned by root. The Linux
proofs check that the dev account cannot modify, move or replace any of these,
nor add a `managed-settings.d/` drop-in.

### Linux sandbox prerequisites

`sudo apt-get install bubblewrap socat`. For Unix-socket blocking (keeps the
sandbox away from the local MySQL socket), also
`npm install -g @anthropic-ai/sandbox-runtime`. On Ubuntu 24.04 and later,
check `sysctl kernel.apparmor_restrict_unprivileged_userns`: if it is `1`,
bubblewrap cannot start until an AppArmor profile allows it (Anthropic's
sandboxing page gives the profile). Our first Linux run failed exactly there;
the failure is kept in `evidence/attempts/`. The kit sets
`sandbox.failIfUnavailable: true`, so Claude Code refuses to start instead of
running unsandboxed (proof F08b). Inside the sandbox, MySQL on `127.0.0.1` and
on its socket is unreachable, on purpose.

## 6. Check what is really loaded

- `/status` in a session: the `Setting sources` line lists every settings
  file loaded. `claude doctor` lists entries Claude Code rejected.
- The guard writes a line at every session start when `CSCART_GUARD_LOG` is
  set: `CSCART_GUARD_LOG=/tmp/guard.log claude`, then look for
  `"event": "SessionStart"` with the policy fingerprint. No line means the
  guard is not registered. Every recorded session in `evidence/sessions/`
  shows this hook firing.
- Compare with your colleague: user settings, local settings, CLI flags and
  plugins differ per person, so identical project files do not guarantee
  identical behaviour.

## 7. Permission modes

| Mode | What it means | For this project |
|---|---|---|
| `default` (shown as **manual**) | Asks before edits and commands; reads are free. | The owner's mode. Set in `settings.json`. |
| `acceptEdits` | Edits and some file commands without asking. | Developer, on a task branch. |
| `plan` | Reads and plans; edits wait for an approved plan. | Useful for step 2 of the owner guide. |
| `auto` | A classifier approves or refuses. Not an isolation layer. | Removed by the kit (`disableAutoMode: "disable"`), so it is not in the `Shift+Tab` cycle. Since v2.1.283 it is otherwise the default starting mode of interactive sessions. |
| `dontAsk` | Pre-approved tools only; anything that would ask is refused. Not a synonym of bypass. | Scripts and tests. |
| `bypassPermissions` | Almost no questions; deny rules still apply. | Disabled by the kit (`disableBypassPermissionsMode`). |

`sandbox.autoAllowBashIfSandboxed` is `false` in the kit, so sandboxed shell
commands still ask in manual mode. Deny rules beat allow rules, so the kit
never writes a broad deny with a narrow allow exception: the task's file list
(an allow list, enforced by the guard) does that job.

## 8. Rollback and working together

- **One clone or worktree per person.** A git worktree gives each person
  their own folder, but it shares the repository's history and refs: it is a
  convenience, not a security boundary.
- **One branch per task**, created by `bin/claude-task start`, with the same
  rules versioned in the repository for both of you.
- **Undo is task-scoped and does not hide anything**: `bin/claude-task undo`
  restores only the task's files to the baseline blob hashes and never runs
  `git reset --hard` or `git clean`. It compares the whole `git status` with
  the snapshot taken at `start`: any other file changed or created since then
  (by a shell command, by you, by anything) is left in place, untracked files
  included, and named in a NOT UNDONE error; the task stays open. Pre-existing
  uncommitted work is neither touched nor reported. Tested by replaying a
  `sed -i` on the shared stylesheet during a task and a file created by the
  developer during a task (`tests/test_task_undo.py`). Ignored files
  (`var/`, `images/`) are not seen by git and so not reported.
- **Git does not bring back**: the database, `var/cache`, ignored files
  (`images/`, `config.local.php`), anything outside the repository.
- **`/rewind`** (Esc Esc) restores Claude's own file edits, but not files
  changed by Bash commands, by subagents, or outside Claude Code. Use the task
  tool for anything that matters.

## 9. Understanding a customised install (code map method)

`CLAUDE.md` ships with an "UNVERIFIED" section. Fill it in from observation,
not memory:

1. Versions: `php -v` on the dev server, CS-Cart version from the admin
   panel or the code.
2. Active theme folder and which templates it overrides.
3. Customisations: compare against a clean copy of the same CS-Cart version
   if you have one, list core files that were edited and custom add-ons.
4. Shared dependencies: stylesheets and scripts loaded on checkout and
   elsewhere (start from the checkout templates and follow includes).
5. The route from a saved file to the dev site: same folder, sync step, cache.

Each entry you confirm loses its UNVERIFIED tag. Shared dependencies found in
step 4 belong in `policy.json` or in the stop list of `CLAUDE.md`.

## 10. Re-running the evidence

```
python3 -m unittest discover -s tests -v      # guard, undo, settings sync: no model, seconds
tests/linux/run_linux.sh                       # Linux container proofs: Docker, no model, about 1 minute
python3 sessions/run_sessions.py               # real Claude Code sessions: needs a Claude subscription
python3 tools/summarize_sessions.py && python3 tools/build_results.py
```
