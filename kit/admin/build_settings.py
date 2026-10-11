#!/usr/bin/env python3
"""Build Claude Code settings from the one policy file.

Project mode (default) writes kit/.claude/settings.json, used inside the dev copy.
Managed mode prints a managed-settings.json for /etc/claude-code/ with absolute
paths, for a shared server where the developer account must not be able to
change the rules (see docs/developer-guide.md, "Admin install").

    python3 kit/admin/build_settings.py
    python3 kit/admin/build_settings.py --managed /srv/dev/shop /opt/claude-cscart-guard
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
KIT = os.path.dirname(HERE)
POLICY = os.path.join(KIT, ".claude", "guard", "policy.json")


def rule(tool, pattern, root):
    if pattern.startswith("~/"):
        return "%s(%s)" % (tool, pattern)
    if pattern.startswith("**/"):
        return "%s(%s)" % (tool, pattern)
    if root:  # managed settings: absolute paths are written with a leading //
        return "%s(/%s/%s)" % (tool, root.rstrip("/"), pattern)
    return "%s(/%s)" % (tool, pattern)  # project settings: /path = relative to the project root


def build(policy, root=None, guard_dir=None):
    deny = [rule("Edit", p, root) for p in policy["protected_edit"]]
    deny += [rule("Read", p, root) for p in policy["secret_read"]]
    for program in policy["bash_denied_programs"]:
        deny += ["Bash(%s)" % program, "Bash(%s *)" % program]
    deny += ["Bash(git push *)", "Bash(git reset --hard *)", "Bash(git clean *)", "WebFetch", "WebSearch"]
    if guard_dir:
        guard = "python3 %s/guard.py" % guard_dir.rstrip("/")
    else:
        guard = 'python3 "$CLAUDE_PROJECT_DIR/.claude/guard/guard.py"'
    hook = {"type": "command", "command": guard, "timeout": 10, "onFailure": "block"}
    settings = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {
            "defaultMode": "default",
            "disableBypassPermissionsMode": "disable",
            "disableAutoMode": "disable",
            "deny": deny,
            "allow": ["Bash(git status)", "Bash(git diff)", "Bash(git diff *)", "Bash(git log *)",
                      "Bash(bin/claude-task status)", "Bash(bin/claude-task diff)"],
        },
        "hooks": {
            "SessionStart": [{"hooks": [dict(hook, command=guard + " --session-start")]}],
            "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit|Read|Grep|Bash", "hooks": [hook]}],
        },
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": False,
            "excludedCommands": [],
            "network": {"allowedDomains": []},
        },
    }
    if root:
        settings["sandbox"]["network"]["strictAllowlist"] = True
    return settings


def main(argv):
    with open(POLICY) as handle:
        policy = json.load(handle)
    if argv[:1] == ["--managed"] and len(argv) == 3:
        print(json.dumps(build(policy, argv[1], argv[2]), indent=2))
        return 0
    if argv:
        sys.stderr.write(__doc__)
        return 1
    target = os.path.join(KIT, ".claude", "settings.json")
    with open(target, "w") as handle:
        handle.write(json.dumps(build(policy), indent=2) + "\n")
    print("wrote", os.path.relpath(target, os.getcwd()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
