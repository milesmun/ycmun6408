#!/usr/bin/env python3
"""Record which skills get used, so unused ones can be cleaned up later.

  skill_usage.py log     <- PreToolUse(Skill) / UserPromptSubmit hook; reads hook JSON on stdin
  skill_usage.py commit  <- Stop hook; commits the log file if it changed

Never fails loudly: a broken log must not block the session.
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
REL = ".claude/skill-usage.log"
LOG = os.path.join(ROOT, REL)


def log():
    data = json.load(sys.stdin)
    name = None
    if data.get("tool_name") == "Skill":
        name = (data.get("tool_input") or {}).get("skill")
    else:
        prompt = (data.get("prompt") or "").strip()
        if prompt.startswith("/") and len(prompt) > 1:
            name = prompt[1:].split()[0]
    if not name:
        return
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{name}\n")


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def commit():
    if not git("status", "--porcelain", "--", REL).stdout.strip():
        return
    gitdir = git("rev-parse", "--git-dir").stdout.strip()
    gitdir = os.path.join(ROOT, gitdir) if gitdir and not os.path.isabs(gitdir) else gitdir
    busy = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD")
    if not gitdir or any(os.path.exists(os.path.join(gitdir, b)) for b in busy):
        return
    if git("symbolic-ref", "-q", "HEAD").returncode != 0:  # detached HEAD
        return
    git("add", "--", REL)
    git("commit", "-q", "-m", "chore: record skill usage", "--", REL)


if __name__ == "__main__":
    try:
        {"log": log, "commit": commit}[sys.argv[1]]()
    except Exception:
        pass
    sys.exit(0)
