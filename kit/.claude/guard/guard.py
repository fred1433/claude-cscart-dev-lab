#!/usr/bin/env python3
"""Guard for Claude Code on a CS-Cart dev copy.

Runs as a Claude Code PreToolUse hook (and once at SessionStart). It reads the
tool call as JSON on stdin and either lets it through (exit 0) or blocks it
(exit 2, reason on stderr, which Claude Code shows to the model).

What it is for: early, readable rejection of edits outside the current task,
edits to protected files, reads of secrets, and obvious database, network and
production commands. What it is NOT: a shell parser. A command can be written
in a way this guard does not recognise; the Claude Code sandbox and Unix
permissions are the layers that stop those. See docs/developer-guide.md.

Self-contained on purpose: Python 3.6+ standard library only, no import from
the project, data read from policy.json next to this file. Any internal error
blocks (exit 2), and settings.json also sets onFailure: "block" so a guard
that cannot start, crashes or times out blocks too.
"""
import hashlib
import json
import os
import re
import shlex
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
POLICY_FILE = os.path.join(HERE, "policy.json")
LIST_KEYS = ("protected_edit", "secret_read", "production_roots",
             "bash_denied_programs", "bash_denied_patterns", "bash_denied_fragments")
EDIT_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
              "NotebookEdit": "notebook_path"}


class Block(Exception):
    pass


def load_policy():
    with open(POLICY_FILE, "rb") as handle:
        raw = handle.read()
    policy = json.loads(raw.decode("utf-8"))
    if not isinstance(policy, dict) or policy.get("version") != 1:
        raise ValueError("policy.json: missing or unknown version")
    for key in LIST_KEYS:
        value = policy.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise ValueError("policy.json: %s must be a list of non-empty strings" % key)
    for pattern in policy["bash_denied_patterns"]:
        re.compile(pattern)
    root = policy.get("project_root")
    if root is not None and not (isinstance(root, str) and os.path.isabs(root)):
        raise ValueError("policy.json: project_root must be an absolute path")
    return policy, hashlib.sha256(raw).hexdigest()[:16]


def glob_regex(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile("^" + out + "$")


def resolve(path, base):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    # realpath follows symlinks and folds "..", so an alias cannot hide a target.
    return os.path.realpath(path)


def inside(path, root):
    return path == root or path.startswith(root.rstrip("/") + "/")


def matches(abs_path, patterns, root):
    rel = os.path.relpath(abs_path, root) if inside(abs_path, root) else None
    for pattern in patterns:
        if pattern.startswith("~/") or pattern.startswith("/"):
            candidate, pat = abs_path, os.path.expanduser(pattern)
        elif rel is not None:
            candidate, pat = rel, pattern
        else:
            continue
        regex = glob_regex(pat)
        if regex.match(candidate) or (pat.endswith("/**") and regex.match(candidate + "/x")):
            return pattern
    return None


def production_roots(policy, root):
    return [resolve(p, root) for p in policy["production_roots"]]


def load_task(root):
    task_file = os.path.join(root, ".claude", "task.json")
    if not os.path.exists(task_file):
        return None
    with open(task_file) as handle:
        task = json.load(handle)
    files = task.get("files")
    if not isinstance(task.get("name"), str) or not isinstance(files, list):
        raise ValueError(".claude/task.json is malformed")
    return task


def check_edit(path, policy, root, cwd):
    target = resolve(path, cwd)
    for prod in production_roots(policy, root):
        if inside(target, prod):
            raise Block("%s is inside the production copy. This workflow never writes there." % path)
    if not inside(target, root):
        raise Block("%s resolves outside the dev copy (%s)." % (path, target))
    hit = matches(target, policy["protected_edit"], root)
    if hit:
        raise Block("%s is protected by policy rule '%s' (checkout, payment, orders, prices, database, "
                    "secrets or the guard itself). Ask the developer." % (path, hit))
    task = load_task(root)
    if task is None:
        raise Block("no task is open. The human starts one with: bin/claude-task start <name> <file>...")
    allowed = [resolve(f, root) for f in task["files"]]
    if target not in allowed:
        raise Block("%s is not in the file list of task '%s' (%s). If the change really needs this file, "
                    "stop and explain why; the human decides whether to widen the task."
                    % (path, task["name"], ", ".join(task["files"])))
    return "edit inside task '%s'" % task["name"]


def check_read(path, policy, root, cwd):
    target = resolve(path, cwd)
    for prod in production_roots(policy, root):
        if inside(target, prod):
            raise Block("%s is inside the production copy." % path)
    hit = matches(target, policy["secret_read"], root)
    if hit:
        raise Block("%s holds secrets (policy rule '%s'). Ask the developer for the value you need." % (path, hit))
    return "read"


def check_bash(command, policy, root):
    try:
        words = shlex.split(command, comments=False, posix=True)
    except ValueError:
        words = command.split()
    for word in words:
        for part in re.split(r"[;&|()`$<>]+", word):
            name = os.path.basename(part)
            if name in policy["bash_denied_programs"]:
                raise Block("'%s' is not allowed here: no database, server, network or permission commands "
                            "in this workflow." % name)
    for pattern in policy["bash_denied_patterns"]:
        if re.search(pattern, command):
            raise Block("this command is reserved to the human (git history, branches, staging, or bin/claude-task start/undo/finish).")
    for fragment in policy["bash_denied_fragments"]:
        if fragment in command:
            raise Block("the command mentions '%s', a protected area." % fragment)
    if re.search(r"(^|[\s/'\"=:])\.\.(/|\s|$|['\"])", command):
        raise Block("the command leaves the dev copy with '..'.")
    for prod in production_roots(policy, root):
        if prod in command:
            raise Block("the command names the production copy.")
    return "bash passed the guard (the sandbox still applies)"


def audit(entry):
    log = os.environ.get("CSCART_GUARD_LOG")
    if not log:
        return
    entry["time"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        with open(log, "a") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def project_root(policy, payload):
    root = policy.get("project_root") or os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    return os.path.realpath(root)


def decide(payload, policy):
    root = project_root(policy, payload)
    cwd = os.path.realpath(payload.get("cwd") or root)
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        target = data.get(EDIT_TOOLS[tool])
        if not isinstance(target, str) or not target:
            raise Block("%s call without a file path." % tool)
        return target, check_edit(target, policy, root, cwd)
    if tool == "Read":
        return data.get("file_path", ""), check_read(data.get("file_path", ""), policy, root, cwd)
    if tool == "Grep" and data.get("path"):
        return data["path"], check_read(data["path"], policy, root, cwd)
    if tool == "Bash":
        return data.get("command", ""), check_bash(data.get("command", ""), policy, root)
    return "", "tool not covered by the guard"


def check_scope(files):
    policy, _ = load_policy()
    root = policy.get("project_root") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = os.path.realpath(root)
    bad = 0
    for path in files:
        target = resolve(path, root)
        hit = matches(target, policy["protected_edit"], root)
        if not inside(target, root) or hit:
            sys.stderr.write("refused: %s (%s)\n" % (path, hit or "outside the dev copy"))
            bad += 1
    return 1 if bad else 0


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--check-scope":
        return check_scope(sys.argv[2:])
    raw = sys.stdin.read()
    payload = json.loads(raw) if raw.strip() else {}
    policy, digest = load_policy()
    if sys.argv[1:] == ["--session-start"] or payload.get("hook_event_name") == "SessionStart":
        audit({"event": "SessionStart", "policy_sha256_16": digest, "session": payload.get("session_id")})
        print("CS-Cart guard active (policy %s). Edits are limited to the open task's files." % digest)
        return 0
    target, why = None, None
    try:
        target, why = decide(payload, policy)
    except Block as block:
        audit({"event": "PreToolUse", "tool": payload.get("tool_name"), "target": str(target or ""),
               "input": payload.get("tool_input"), "decision": "block", "reason": str(block),
               "policy_sha256_16": digest, "session": payload.get("session_id")})
        sys.stderr.write("[guard] Blocked: %s\n" % block)
        return 2
    audit({"event": "PreToolUse", "tool": payload.get("tool_name"), "input": payload.get("tool_input"),
           "decision": "allow", "reason": why, "policy_sha256_16": digest, "session": payload.get("session_id")})
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as error:  # fail closed on anything unexpected
        sys.stderr.write("[guard] Blocked: the guard hit an internal error (%s: %s). Nothing was run.\n"
                         % (type(error).__name__, error))
        sys.exit(2)
