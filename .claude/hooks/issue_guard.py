#!/usr/bin/env python3
"""PreToolUse guard: keep bare issues and destructive git off the main line.

Reads the Claude Code PreToolUse hook payload on stdin (``{tool_name, tool_input,
...}``) and blocks two things:

1. Destructive git (``git push --force`` / ``git reset --hard``) run via Bash. This
   repo works on ``main`` only (ADR-0001), so a force-push rewrites the one branch
   everybody and every clone is on.

2. A bare issue creation, via either ``gh issue create`` (Bash) or the
   ``mcp__github__create_issue`` tool. Every issue must carry an assignee and either
   ``PRD`` (epic) or a category (``bug``/``enhancement``); an issue with no assignee
   is invisible on the board, which is where the backlog actually lives. When
   ``.claude/project.json`` lists ``areas``, an ``area:<x>`` label is required too;
   with the list empty (the default) that check is off. The to-prd and triage skills
   already fill these in, so their creations pass; only hand-rolled bare creations get
   blocked, with a message that points at the skills.

   A new issue's *body* is checked for one kind of rot: a ``<file>.md line N`` /
   ``L N`` / ``:N`` citation. Prose line numbers rot within hours, so cite a section
   heading instead. Code references (``file.py:123``) stay allowed: they are the house
   citation format for code. Only creations are checked, never edits.

FAILURE POLICY: fail-open. Any parse error, unknown shape, or unrelated call exits 0
(allow). A guard that crashes must never wedge a legitimate tool call. Exit 2 + stderr
is the only block path (the harness feeds stderr back to the model as the block reason).
"""

import json
import pathlib
import re
import shlex
import sys

_CATEGORIES = ("PRD", "bug", "enhancement")
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CONFIG = _REPO_ROOT / ".claude" / "project.json"

# .md only: prose line numbers rot within hours. Code `file.py:123` references stay
# allowed, they are the house citation format for code.
_LINE_NUMBER_REF = re.compile(r"\.md`?\s*(?::\d+|\(?(?:L|line\s+)\d+)", re.IGNORECASE)

_ISSUE_HELP = (
    "BLOCKED: bare issue creation.\n"
    "Every issue needs an assignee and either PRD (epic) or a category "
    "(bug/enhancement).\n"
    "Missing: {missing}.\n"
    "Route through the skills instead of a raw create: /to-prd (a PRD or a sub-issue "
    "under one), or /triage. They fill labels and assignee for you.\n"
    "Or re-run adding: --assignee <login> --label <PRD|bug|enhancement>{area_hint}.\n"
    "(CLAUDE.md: every issue gets an assignee at creation; triage state lives in labels.)"
)


def _areas():
    """The area names from .claude/project.json, or [] when the project has none."""
    try:
        return [str(area) for area in json.loads(_CONFIG.read_text()).get("areas") or []]
    except Exception:
        return []


def _block(message):
    print(message, file=sys.stderr)
    sys.exit(2)


def _missing_from_labels(labels, has_assignee):
    """Return the human list of what a would-be issue is missing, or None if complete."""
    joined = " ".join(labels)
    missing = []
    if not has_assignee:
        missing.append("assignee")
    areas = _areas()
    if areas and not re.search(rf"area:({'|'.join(re.escape(a) for a in areas)})\b", joined):
        missing.append("an area:<x> label")
    if not any(re.search(rf"(^|[\s,]){re.escape(cat)}($|[\s,])", joined) for cat in _CATEGORIES):
        missing.append("a PRD or bug/enhancement label")
    return missing or None


def _help_text(missing):
    areas = _areas()
    hint = f" --label area:<{'|'.join(areas)}>" if areas else ""
    return _ISSUE_HELP.format(missing=", ".join(missing), area_hint=hint)


def _check_issue_body(body):
    """Block a new-issue body that cites prose line numbers."""
    if not body:
        return
    line_refs = _LINE_NUMBER_REF.findall(body)
    if line_refs:
        _block(
            "BLOCKED: issue body cites file line numbers ("
            + ", ".join(ref.strip() for ref in line_refs[:3])
            + "). Line numbers in prose rot within hours; cite a section heading or a "
            "quoted phrase instead."
        )


def _is_gh_issue_create(tokens):
    """True only for a real `gh issue create` invocation: a `gh` token followed
    somewhere by ADJACENT `issue` `create` tokens. Token-based on purpose: a regex
    matching "create" anywhere after `gh issue` blocks
    `gh issue close --comment "...create..."` as a creation. Words inside a quoted
    argument are one token, so they can never match."""
    if "gh" not in tokens:
        return False
    start = tokens.index("gh")
    return any(
        tokens[index] == "issue" and tokens[index + 1] == "create"
        for index in range(start + 1, len(tokens) - 1)
    )


def _check_gh_issue_create(command):
    """Guard a Bash `gh issue create`. Non-matching commands return without blocking."""
    if not re.search(r"\bgh\b", command):
        return
    tokens = shlex.split(command)  # may raise on odd quoting -> caller fails open
    if not _is_gh_issue_create(tokens):
        return
    labels = []
    has_assignee = False
    body = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        key, _, inline = token.partition("=")
        value = inline if inline else (tokens[index + 1] if index + 1 < len(tokens) else "")
        took_next = bool(value) and not inline
        if key in ("--label", "-l"):
            labels.extend(part.strip() for part in value.split(",") if part.strip())
            index += 2 if took_next else 1
            continue
        if key in ("--assignee", "-a"):
            has_assignee = has_assignee or bool(value.strip())
            index += 2 if took_next else 1
            continue
        if key in ("--body", "-b"):
            body = value
            index += 2 if took_next else 1
            continue
        if key in ("--body-file", "-F") and value and value != "-":
            try:
                body = pathlib.Path(value).read_text()
            except OSError:
                pass  # fail-open: an unreadable body file must not wedge the call
            index += 2 if took_next else 1
            continue
        index += 1
    missing = _missing_from_labels(labels, has_assignee)
    if missing:
        _block(_help_text(missing))
    _check_issue_body(body)


def _check_mcp_create_issue(tool_input):
    """Guard the mcp__github__create_issue tool call."""
    labels = tool_input.get("labels") or []
    if isinstance(labels, str):
        labels = [labels]
    assignees = tool_input.get("assignees") or tool_input.get("assignee") or []
    if isinstance(assignees, str):
        assignees = [assignees]
    missing = _missing_from_labels([str(label) for label in labels], bool(assignees))
    if missing:
        _block(_help_text(missing))
    _check_issue_body(str(tool_input.get("body") or ""))


def _is_destructive_git(command):
    """True if `command` runs a history-destroying git op.

    Covers the shorthands a single regex misses: ``-f`` for ``--force``,
    ``--force-with-lease``, and a leading-``+`` refspec (``git push origin
    +main:main``), which force-updates the remote ref just like ``--force``.

    Matches on *tokens*, not substrings, so a force pattern quoted inside a commit
    message (``git commit -m "... git push -f ..."``) does not trip the guard. shlex
    keeps a quoted message as one token, so ``push`` there is not a standalone token.
    Odd quoting that shlex cannot parse falls open (allow), matching the hook's global
    fail-open policy.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if "git" not in tokens:
        return False
    if "reset" in tokens and "--hard" in tokens:
        return True
    if "push" not in tokens:
        return False
    if any(tok in ("--force", "--force-with-lease", "-f") for tok in tokens):
        return True
    # A refspec whose source starts with '+' force-updates the remote,
    # e.g. `git push origin +main:main` or `git push origin +HEAD:main`.
    if any(re.match(r"\+[^\s:]+:", tok) for tok in tokens):
        return True
    return False


def _check_destructive_git(command):
    if _is_destructive_git(command):
        _block("BLOCKED: destructive git operation requires explicit user approval.")


def main():
    raw = sys.stdin.read()
    payload = json.loads(raw)
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool_name == "mcp__github__create_issue":
        _check_mcp_create_issue(tool_input)
        return

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        _check_destructive_git(command)
        _check_gh_issue_create(command)
        return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Fail-open: never wedge a tool call because the guard tripped over an input
        # shape it did not expect.
        sys.exit(0)
