#!/usr/bin/env python3
"""PreToolUse guard on Bash: no waiting in the foreground (owner, 2026-10-09, WAITING).

An agent's turn that comes more than 5 minutes after its previous one re-writes its whole context to the prompt cache;
on 2026-10-09 that was about half of all agent spend, most of it after foreground sleep and poll loops and foreground
cloud runs. Claude Code blocks a command that *starts* with ``sleep`` in some sessions but not in others (in the
2026-10-09 bench's background sessions ``sleep 300; tail log`` ran), so this guard blocks, for a Bash call not run
with ``run_in_background``:

1. a ``sleep`` longer than ``LONGEST_SLEEP`` seconds anywhere in the command (``sleep 300; tail log``);
2. a poll loop: ``while`` or ``until`` with a ``sleep`` in it, or a ``for`` loop sleeping more than
   ``LONGEST_LOOP_SLEEP`` seconds a round;
3. a cloud Blender run: Python running ``blender_cloud.py`` (not ``--dry-run``), ``settle.py --cloud`` or
   ``page.py --cloud`` (not ``--no-render``), which blocks for many minutes. Reading those files is not a run.

The block message names the way out: run_in_background (the completion notice wakes the agent), the tools'
``--detach`` mode or ``tools/props/cloud/detached.py`` (one result line, progress in a log), or the Monitor tool.

FAILURE POLICY: fail-open. Any parse error or unknown shape exits 0 (allow). Exit 2 + stderr is the only block path.
"""

import json
import re
import sys

LONGEST_SLEEP = 60
LONGEST_LOOP_SLEEP = 5
_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
# A shell sleep (not time.sleep): a word boundary, then a number with an optional unit.
_SLEEP = re.compile(r"(?<![\w.])sleep\s+(\d+(?:\.\d+)?)([smhd]?)\b")
_MESSAGE = re.compile(r"""(?<![\w-])-m\s+(["'])[\s\S]*?(?<!\\)\1""")  # a commit message is words, not a wait
_UNBOUNDED_LOOP = re.compile(r"(?<![\w.-])(while|until)\s[\s\S]*?(?<![\w.-])do\b([\s\S]*?)(?<![\w.-])done\b")
_FOR_LOOP = re.compile(r"(?<![\w.-])for\s[\s\S]*?(?<![\w.-])do\b([\s\S]*?)(?<![\w.-])done\b")
_SEGMENT = re.compile(r"&&|\|\||[;|\n]")
_PYTHON_RUN = r"(?:^|\s)\S*python[\w.]*\s+(?:-\S+\s+)*\S*"
_CLOUD_RUNS = (
    (re.compile(_PYTHON_RUN + r"blender_cloud\.py\b"), re.compile(r"--dry-run\b")),
    (re.compile(_PYTHON_RUN + r"settle\.py\b.*--cloud\b"), None),
    (re.compile(_PYTHON_RUN + r"review/page\.py\b.*--cloud\b"), re.compile(r"--no-render\b")),
)
_WAY_OUT = (
    "Never wait in the foreground (CLAUDE.md, Agent tools): start the command with run_in_background: true and go on "
    "with other work or end your turn; the completion notice wakes you. Cloud runs and test gates: add --detach "
    "(blender_cloud.py, tools/usd/settle.py, tools/review/page.py) or wrap them in tools/props/cloud/detached.py, "
    "which prints one result line at the end. To wait for a condition, use the Monitor tool."
)


def seconds_of(match):
    return float(match.group(1)) * _UNITS[match.group(2)]


def sleeps(text):
    return [seconds_of(match) for match in _SLEEP.finditer(text)]


def long_sleep(command):
    """A sleep over LONGEST_SLEEP anywhere in the command, or None."""
    longest = max(sleeps(command), default=0)
    return f"a sleep of {longest:g} s" if longest > LONGEST_SLEEP else None


def poll_loop(command):
    """A while/until loop that sleeps, or a for loop sleeping more than LONGEST_LOOP_SLEEP a round, or None."""
    for match in _UNBOUNDED_LOOP.finditer(command):
        if sleeps(match.group(2)):
            return f"a {match.group(1)} loop that sleeps"
    for match in _FOR_LOOP.finditer(command):
        if any(seconds > LONGEST_LOOP_SLEEP for seconds in sleeps(match.group(1))):
            return "a for loop that sleeps between rounds"
    return None


def cloud_run(command):
    """A command segment that runs a cloud Blender tool in the foreground, or None."""
    for segment in _SEGMENT.split(command):
        for runs, exempt in _CLOUD_RUNS:
            if runs.search(segment) and not (exempt and exempt.search(segment)):
                return "a cloud Blender run in the foreground"
    return None


def blocked(tool_input):
    """Why this Bash call waits in the foreground, or None."""
    if tool_input.get("run_in_background"):
        return None
    command = _MESSAGE.sub("-m ''", tool_input.get("command") or "")
    return long_sleep(command) or poll_loop(command) or cloud_run(command)


def main():
    try:
        payload = json.load(sys.stdin)
        reason = blocked(payload.get("tool_input") or {}) if payload.get("tool_name") == "Bash" else None
    except Exception:  # fail-open: a broken guard must never wedge a tool call
        sys.exit(0)
    if reason:
        print(f"Blocked: {reason}. {_WAY_OUT}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
