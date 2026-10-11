#!/usr/bin/env python3
"""Build Claude Code settings from a policy file, named explicitly.

Always pass the policy you actually use (the one installed in the dev copy, or
the admin-installed one), never rely on the lab's copy.

Project mode writes a settings.json for the dev copy:
    python3 build_settings.py --policy .claude/guard/policy.json --out .claude/settings.json

Managed mode prints a managed-settings.json for /etc/claude-code/ with absolute
paths, for a shared server where the developer account must not be able to
change the rules (see docs/developer-guide.md, "Shared server"):
    python3 build_settings.py --policy /opt/claude-cscart-guard/policy.json \
        --managed /srv/dev/shop /opt/claude-cscart-guard

Policy paths: "relative/path" is relative to the dev copy, "/absolute/path" is
absolute, "~/path" is in the home folder, "**/x" matches anywhere.
"""
import json
import sys



def rule(tool, pattern, root):
    if pattern.startswith("~/") or pattern.startswith("**/"):
        return "%s(%s)" % (tool, pattern)
    if pattern.startswith("/"):  # absolute in the policy: Claude Code writes absolute paths with a leading //
        return "%s(/%s)" % (tool, pattern)
    if root:  # managed settings: relative policy paths become absolute under the dev copy
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
    args = list(argv)
    policy_path = out = managed = None
    while args:
        flag = args.pop(0)
        if flag == "--policy" and args:
            policy_path = args.pop(0)
        elif flag == "--out" and args:
            out = args.pop(0)
        elif flag == "--managed" and len(args) >= 2:
            managed = (args.pop(0), args.pop(0))
        else:
            sys.stderr.write(__doc__)
            return 1
    if not policy_path or bool(out) == bool(managed):
        sys.stderr.write(__doc__)
        return 1
    with open(policy_path) as handle:
        policy = json.load(handle)
    if managed:
        print(json.dumps(build(policy, managed[0], managed[1]), indent=2))
        return 0
    with open(out, "w") as handle:
        handle.write(json.dumps(build(policy), indent=2) + "\n")
    print("wrote %s from %s" % (out, policy_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
