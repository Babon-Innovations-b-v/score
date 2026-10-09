#!/usr/bin/env python3
"""PreToolUse guard: keep bare issues and destructive git off the main line.

Reads the Claude Code PreToolUse payload on stdin and blocks:

1. Destructive git via Bash (``git push --force``, ``-f``, ``--force-with-lease``, a ``+`` refspec, ``git reset
   --hard``). This repo works on ``main`` only (ADR-0001), so a force-push rewrites the one branch every clone is on.
2. A bare issue creation (``gh issue create`` or ``mcp__github__create_issue``): every issue needs an assignee and
   ``PRD`` or a category (``bug``/``enhancement``), plus an ``area:<x>`` label when ``.claude/project.json`` lists
   ``areas``. An issue with no assignee is invisible on the board, where the backlog lives. The to-prd and triage
   skills fill these in, so only hand-rolled creations are blocked. A new issue's body may not cite a ``.md`` line
   number (``x.md line N``, ``L N``, ``:N``): prose line numbers rot within hours. Code refs (``file.py:123``) stay
   allowed, they are the house citation format for code.

FAILURE POLICY: fail-open. Any parse error, unknown shape, or unrelated call exits 0 (allow): a crashing guard must
never wedge a tool call. Exit 2 + stderr is the only block path (the harness feeds stderr back as the block reason).
"""

import json
import pathlib
import re
import shlex
import sys

_CATEGORIES = ("PRD", "bug", "enhancement")
_CONFIG = pathlib.Path(__file__).resolve().parents[2] / ".claude" / "project.json"
_LINE_NUMBER_REF = re.compile(r"\.md`?\s*(?::\d+|\(?(?:L|line\s+)\d+)", re.IGNORECASE)
_GH_FLAGS = {"--label": "label", "-l": "label", "--assignee": "assignee", "-a": "assignee",
             "--body": "body", "-b": "body", "--body-file": "body_file", "-F": "body_file"}

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


def _missing(labels, has_assignee, areas):
    """What a would-be issue is missing, as human phrases."""
    joined = " ".join(labels)
    missing = [] if has_assignee else ["assignee"]
    if areas and not re.search(rf"area:({'|'.join(re.escape(area) for area in areas)})\b", joined):
        missing.append("an area:<x> label")
    if not any(re.search(rf"(^|[\s,]){re.escape(category)}($|[\s,])", joined) for category in _CATEGORIES):
        missing.append("a PRD or bug/enhancement label")
    return missing


def _check_new_issue(labels, has_assignee, body):
    """Block a new issue that lacks an assignee or labels, or whose body cites prose line numbers."""
    areas = _areas()
    missing = _missing(labels, has_assignee, areas)
    if missing:
        hint = f" --label area:<{'|'.join(areas)}>" if areas else ""
        _block(_ISSUE_HELP.format(missing=", ".join(missing), area_hint=hint))
    line_refs = _LINE_NUMBER_REF.findall(body)
    if line_refs:
        _block("BLOCKED: issue body cites file line numbers (" + ", ".join(ref.strip() for ref in line_refs[:3])
               + "). Line numbers in prose rot within hours; cite a section heading or a quoted phrase instead.")


def _is_gh_issue_create(tokens):
    """True only for adjacent ``issue`` ``create`` tokens after ``gh``. Token-based on purpose: a regex would block
    ``gh issue close --comment "...create..."``; a quoted argument is one token, so it never matches."""
    if "gh" not in tokens:
        return False
    return any(tokens[index:index + 2] == ["issue", "create"] for index in range(tokens.index("gh") + 1, len(tokens)))


def _gh_issue_fields(tokens):
    """The labels, whether an assignee is given, and the body of a ``gh issue create`` command."""
    labels, has_assignee, body = [], False, ""
    index = 0
    while index < len(tokens):
        key, _, inline = tokens[index].partition("=")
        value = inline or (tokens[index + 1] if index + 1 < len(tokens) else "")
        field = _GH_FLAGS.get(key)
        if field == "body_file" and value in ("", "-"):
            field = None
        index += 2 if field and value and not inline else 1
        if field == "label":
            labels.extend(part.strip() for part in value.split(",") if part.strip())
        elif field == "assignee":
            has_assignee = has_assignee or bool(value.strip())
        elif field == "body":
            body = value
        elif field == "body_file":
            try:
                body = pathlib.Path(value).read_text()
            except OSError:
                pass  # fail-open: an unreadable body file must not wedge the call
    return labels, has_assignee, body


def _check_gh_issue_create(command):
    """Guard a Bash ``gh issue create``; any other command passes."""
    if not re.search(r"\bgh\b", command):
        return
    tokens = shlex.split(command)  # may raise on odd quoting -> fail open
    if _is_gh_issue_create(tokens):
        _check_new_issue(*_gh_issue_fields(tokens))


def _check_mcp_create_issue(tool_input):
    """Guard the mcp__github__create_issue tool call."""
    labels = tool_input.get("labels") or []
    assignees = tool_input.get("assignees") or tool_input.get("assignee") or []
    labels = [labels] if isinstance(labels, str) else labels
    _check_new_issue([str(label) for label in labels], bool(assignees), str(tool_input.get("body") or ""))


def _is_destructive_git(command):
    """True if ``command`` runs a history-destroying git op. Matches tokens, not substrings, so a force pattern
    quoted inside a commit message does not trip it; quoting shlex cannot parse falls open."""
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
    # a refspec whose source starts with '+' (git push origin +main:main) force-updates the remote
    return any(token in ("--force", "--force-with-lease", "-f") or re.match(r"\+[^\s:]+:", token) for token in tokens)


def main():
    payload = json.loads(sys.stdin.read())
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool_name == "mcp__github__create_issue":
        _check_mcp_create_issue(tool_input)
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if _is_destructive_git(command):
            _block("BLOCKED: destructive git operation requires explicit user approval.")
        _check_gh_issue_create(command)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open: never wedge a tool call on an input shape the guard did not expect
