import json
import os
import subprocess
import sys
import tempfile

LAB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(LAB, "tools"))
from make_workspace import make  # noqa: E402


def new_workspace(with_prod=True):
    parent = tempfile.mkdtemp(prefix="cscart-lab-")
    return make(os.path.join(parent, "dev"), with_prod=with_prod)


def guard(workspace, tool, tool_input, guard_path=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
               "cwd": workspace, "session_id": "unit-test"}
    script = guard_path or os.path.join(workspace, ".claude", "guard", "guard.py")
    result = subprocess.run([sys.executable, script], input=json.dumps(payload), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True,
                            env=dict(os.environ, CLAUDE_PROJECT_DIR=workspace))
    return result.returncode, result.stderr.strip()


def task(workspace, *args):
    return subprocess.run([sys.executable, os.path.join(workspace, "bin", "claude-task")] + list(args),
                          cwd=workspace, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
