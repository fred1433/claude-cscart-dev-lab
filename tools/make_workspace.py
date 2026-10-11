#!/usr/bin/env python3
"""Assemble a throwaway dev copy: the synthetic fixture + the kit, under git, baseline committed.

    python3 tools/make_workspace.py <empty-or-new-folder> [--with-prod]

--with-prod also creates <folder>/../prod as a synthetic production copy next to
it (the "same server" topology).
"""
import os
import shutil
import subprocess
import sys

LAB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make(dest, with_prod=False):
    if os.path.exists(dest) and os.listdir(dest):
        raise SystemExit("refusing: %s is not empty" % dest)
    shutil.copytree(os.path.join(LAB, "fixture", "shop"), dest, dirs_exist_ok=True)
    shutil.copytree(os.path.join(LAB, "kit", ".claude"), os.path.join(dest, ".claude"))
    shutil.copy2(os.path.join(LAB, "kit", "CLAUDE.md"), os.path.join(dest, "CLAUDE.md"))
    os.makedirs(os.path.join(dest, "bin"), exist_ok=True)
    shutil.copy2(os.path.join(LAB, "kit", "bin", "claude-task"), os.path.join(dest, "bin", "claude-task"))
    run(["git", "init", "-q", "-b", "main"], dest)
    run(["git", "-c", "user.name=lab", "-c", "user.email=lab@example.invalid", "add", "-A"], dest)
    run(["git", "-c", "user.name=lab", "-c", "user.email=lab@example.invalid", "commit", "-q", "-m",
         "baseline before Claude Code"], dest)
    with open(os.path.join(dest, ".git", "config"), "a") as handle:
        handle.write("[user]\n\tname = lab\n\temail = lab@example.invalid\n")
    if with_prod:
        prod = os.path.join(os.path.dirname(os.path.abspath(dest)), "prod")
        shutil.copytree(os.path.join(LAB, "fixture", "shop"), prod)
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    print(make(sys.argv[1], "--with-prod" in sys.argv[2:]))
