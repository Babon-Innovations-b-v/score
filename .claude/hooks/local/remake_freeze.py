#!/usr/bin/env python3
"""The push freeze: while a freeze stands, a push to main that makes accepted rows again is refused unless a pushed
commit names each of them in a "Remakes: <row or node> ...: <reason>" trailer.

    printf '%s\n' "$push_lines" | remake_freeze.py <remakes.json>

.claude/hooks/local/pre-push-moved runs it after `score moved --pre-push`, which writes the accepted nodes the pushed
commit makes again, free ones too, to <remakes.json> ({"remade": [{"node", "paid", "euros"}]}). The freeze is a file
kept outside the repository, like the push cap: SCORE_PUSH_FREEZE names it, else ~/.config/score/push-freeze.json,
{"until": "YYYY-MM-DD", "reason": "..."}; it stands through its `until` day. No file, or a day past it: no freeze, the
push goes on. A file that cannot be read refuses the push (fix or remove it). A trailer names a node by its row
("light: why" covers every light node) or by the node itself ("light@hub: why"); a value with no reason after its
colon names nothing.

Why: on 2026-11-10 a few fixes re-keyed 655 accepted rows on this PC, most of them free, while env1's film ran; the
moved check counted only the paid ones. The root fix is #107 (a row's key moves only when its output would).
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys

TRAILER = "Remakes"
ZERO = "0" * 40
MAIN = "refs/heads/main"


def freeze_path():
    """Where the freeze file is looked for."""
    return pathlib.Path(os.environ.get("SCORE_PUSH_FREEZE") or pathlib.Path.home() / ".config/score/push-freeze.json")


def standing_freeze(path, today):
    """The freeze in force on `today` (an ISO date) as {until, reason}, or None. Raises ValueError on a file that
    cannot be read as one."""
    if not path.exists():
        return None
    try:
        freeze = json.loads(path.read_text())
        until = datetime.date.fromisoformat(str(freeze["until"])).isoformat()
    except (OSError, ValueError, KeyError, TypeError) as fault:
        raise ValueError(f"the freeze file {path} cannot be read ({fault})") from fault
    return {"until": until, "reason": freeze.get("reason", "")} if today <= until else None


def git_lines(*words):
    """The non-empty output lines of a git command run here."""
    found = subprocess.run(["git", *words], capture_output=True, text=True, check=True)
    return [line.strip() for line in found.stdout.splitlines() if line.strip()]


def pushed_reasons(push_lines):
    """Every Remakes trailer value of a commit the pushes to main send."""
    reasons = []
    for line in push_lines:
        words = line.split()
        if len(words) != 4 or words[2] != MAIN or words[1] == ZERO:
            continue
        local, remote = words[1], words[3]
        commits = git_lines("rev-list", *([local, "--not", "--remotes"] if remote == ZERO else [f"{remote}..{local}"]))
        for commit in commits:
            reasons += git_lines("log", "-1", f"--format=%(trailers:key={TRAILER},valueonly)", commit)
    return reasons


def named(node, reasons):
    """True when a trailer value lists the node, or its row, before a colon with a reason after it."""
    row = node.partition("@")[0]
    for reason in reasons:
        listed, colon, why = reason.partition(":")
        if colon and why.strip() and {node, row} & set(listed.replace(",", " ").split()):
            return True
    return False


def main(argv):
    """Exit 1 when a standing freeze meets a remade accepted node no Remakes trailer names; else 0."""
    try:
        freeze = standing_freeze(freeze_path(), datetime.date.today().isoformat())
    except ValueError as fault:
        print(f"refused: {fault}", file=sys.stderr)
        return 1
    if freeze is None:
        return 0
    remade = json.loads(pathlib.Path(argv[1]).read_text())["remade"]
    reasons = pushed_reasons(sys.stdin.read().splitlines())
    unnamed = sorted({row["node"] for row in remade if not named(row["node"], reasons)})
    if not unnamed:
        if remade:
            print(f"freeze: every remade accepted row is named ({TRAILER}: " + "; ".join(reasons) + ")")
        return 0
    rows = sorted({node.partition("@")[0] for node in unnamed})
    print(f"refused: a push freeze stands until {freeze['until']} ({freeze['reason']}), and this push makes "
          f"{len(unnamed)} accepted rows again that no '{TRAILER}:' trailer names: {' '.join(unnamed)}. "
          f"If they should be made again now, add to a pushed commit: '{TRAILER}: {' '.join(rows)}: <why>'.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
