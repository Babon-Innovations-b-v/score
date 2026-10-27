#!/usr/bin/env python3
"""PreToolUse guard: only the owner rejects, accepts, waives or overrides; only the runner accepts automatically and
clears a paid run.

Reads the Claude Code PreToolUse payload on stdin and blocks an agent from:

1. Running the owner's commands: a command part that runs Python on ``score.review`` (or ``score/review``, or its
   ``__main__.py``) with accept, reject, spend, waive or stop (his money yes, which writes an environment's stop line)
   as its subcommand, quoted or not.
2. Calling them from Python, or writing a script that does: a shell command that runs Python, or writes a file
   outside the framework package, and holds a call to ``accept(``, ``reject(``, ``spend(``, ``waive(``,
   ``write_once(``, ``write_accept(``, ``write_reject(``, ``write_spend_yes(``, ``write_waiver(``,
   ``write_clearance(`` or ``set_line(``; a Write or Edit of a code file outside the framework package (``score/``)
   with such a call.
3. Taking Claude Code's mark off a process (``unset CLAUDECODE``, ``env -u``, ``env -i``, ``CLAUDECODE=``), or
   faking a terminal (``script -c``, ``unbuffer``) for a ``score`` command: the store refuses an agent's process the
   owner's areas by that mark (score/store ``running_under_agent``), and the review commands want a terminal.
4. Writing the store's accepts, rejects, waivers, spend yeses, clearances, stop lines or benchmark grants
   (``accepts/``, ``rejects/``, ``waivers/``, ``spend-yes/``, ``clearances/``, ``stops/``, ``grants/``) by hand: by Write, Edit or NotebookEdit
   on such a path, or a shell command one of whose parts redirects into such a path or runs a writing command
   (``tee``, ``cp``, ``mv``, ``ln``, ``rm``, ``touch``, ``install``, ``rsync``, ``dd``, ``chmod``, ``sed -i``, ``find -delete``, Python) that names one.
5. Writing an artifact database collection or document of those names (``Artifact`` with ``write_db``, a batch's
   writes included).
6. His concept and film locks and the chat route's own steps by any other route (owner, 2026-10-27: "i hate the rule
   that i cant make discisions in chat aswell"): a shell command that runs Python, or writes a script outside the
   framework, holding a call to ``concept_pick(``, ``film_locked(``, ``concepts.pick(``, ``script.lock(``,
   ``chat_decisions.apply(``, ``applying.apply(``, ``as_owner_deciding(``, ``as_owner_under(``, ``markers_lifted(``,
   ``decision_yes_spent(`` or ``buy_yes_spent(`` (a code file outside the framework and ``score/dashboard/`` too); a
   hand write into the store's concept ``picks/`` or the cockpit's ``films/locked/`` (rule 4); and the apply command
   (``python -m score.dashboard decide``, ``this_pc.py decide``, the agents' door's ``decide``) without the id of his
   yes. That command with its yes id is the one route an agent applies his decision by: decide-yes records his
   quoted answer and the question, and the apply refuses a yes used already or a target changed since the question
   (score/dashboard/sync/chat_decisions.py). Like the Buy's yes, the id is checked by the code, not here.

Running the stages stays allowed, and with it the runner's own automatic accept and clearance (score/graph,
score.adapters.compute), which this guard does not see: they are written by the framework's code, only when every
gate passed and nothing got worse, or the inputs passed and the stop has room. Reading stays allowed:
``grep``, ``ls`` and ``cat`` of those folders, a redirect to an unrelated file, a review page, the tests. So do code
edits and text that only mention the owner's words (owner, 2026-10-27, his "yes" to narrowing this guard to the
commands that actually run his accept, reject, waive or spend): a test run under a path or ``-k`` holding "accept", a
commit message, a heredoc into the framework, a doc that quotes ``accept(``.

A benchmark grant (the owner's standing rule of 2026-10-20, root CLAUDE.md) passes: the session that asked him writes
his yes with ``score.adapters.compute.grant_benchmark(answer, question, euros)`` (benchmark only, at most EUR 20,
24 h, a balance each run draws its real spend from), and runs a batch as ``SCORE_BENCHMARK_GRANT=<grant id> .venv/bin/python -m score run ...``; the
runner checks the grant at clearance. The grant's records are written by that code only, never by hand (rule 4).

Why (the layered framework's design, 2026-10-11, amended the same day): agent verdicts stood in for the owner's (a
place declared complete that he had not seen), and the newest take replaced the accepted one by itself. Now the
framework's gates decide, the runner accepts and clears by their answer, and the owner's reject, waiver and override
stay his alone. On one machine under YOLO this guard and the store's refusal are a barrier, not a lock: an agent set
on getting round them can (by editing the framework's own code, say), and every accept in the store names who gave
it and when.

FAILURE POLICY: fail-open. Any parse error, unknown shape or unrelated call exits 0 (allow). Exit 2 + stderr is the
only block path (the harness feeds stderr back to the model as the block reason).
"""

import json
import re
import sys

_PYTHON = re.compile(r"\b(python3?(\.\d+)?|uv\s+run)\b|/python\b")
_REVIEW_RUN = re.compile(r"^\s*(\S+=\S*\s+)*(sudo\s+)?((ba)?sh\s+-\S*c\s+['\"]?|eval\s+['\"]?)?(uv\s+run\s+)?\S*python3?(\.\d+)?\s+(-\S+\s+)*"
                         r"(-m\s+)?\S*(score[./]review(/__main__\.py)?|__main__\.py)\s+['\"]?"
                         r"(accept|reject|spend|waive|stop)\b")
_OWNER_CALL = re.compile(r"\b(accept|reject|spend|waive|write_once|write_accept|write_reject|write_spend_yes|"
                         r"write_waiver|write_clearance|set_line)\s*\(")
# His concept and film locks and the chat route's own steps (owner, 2026-10-27): his decision made in chat is applied
# only as `decide <yes id>`, never by calling what that command calls.
_LOCK_CALL = re.compile(r"\b(concept_pick|film_locked|as_owner_deciding|as_owner_under|markers_lifted|"
                        r"decision_yes_spent|buy_yes_spent)\s*\(|\b(concepts\.pick|script\.lock|chat_decisions\.apply|"
                        r"applying\.apply)\s*\(")
_DASHBOARD = re.compile(r"(^|/)score/dashboard/")
# The apply command of a decision he made in chat, by the cockpit's command, this PC's or the agents' door; its id.
_DECIDE_RUN = re.compile(r"^\s*(\S+=\S*\s+)*(sudo\s+)?((uv\s+run\s+)?\S*python3?(\.\d+)?\s+(-\S+\s+)*"
                         r"(-m\s+score\.dashboard|\S*score/dashboard(/__main__\.py)?|\S*this_pc\.py)|ssh\s.*?score@\S+)"
                         r"\s+['\"]?decide['\"]?(?=\s|$)(\s+['\"]?(?P<id>[^\s'\"]+))?")
_YES_ID = re.compile(r"^\d{8}T\d{6}\d*Z$")
_AGENT_MARK = re.compile(r"\b(CLAUDECODE|CLAUDE_CODE_ENTRYPOINT|AI_AGENT)\b")
_UNMARK = re.compile(r"\bunset\b|\benv\s+(-\S+\s+)*(-u|--unset|-i|--ignore-environment)\b|\b(CLAUDECODE|"
                     r"CLAUDE_CODE_ENTRYPOINT|AI_AGENT)=|environ|\bpop\b|\bdel\b")
_CLEARED_ENV = re.compile(r"\benv\s+(-\S+\s+)*(-i|--ignore-environment|-)\s")
_FAKE_TERMINAL = re.compile(r"(^|[\s;&|(])(script\s+-\S*c|unbuffer\s)")
_OWNER_PATH = re.compile(r"(^|[/\s'\"=])(accepts|rejects|waivers|spend-yes|clearances|stops|grants|picks|"
                         r"films/locked)/")
_OWNER_NAME = re.compile(r"(^|/)(accepts|rejects|waivers|spend-yes|clearances|stops|grants|picks|films/locked)(/|$)")
_SEGMENTS = re.compile(r"\|\||&&|[;|\n]")
_REDIRECT_INTO_OWNER = re.compile(r"(^|[^<>&0-9])>>?\s*['\"]?[^\s'\"]*(accepts|rejects|waivers|spend-yes|clearances|"
                                  r"stops|grants|picks|films/locked)/")
_WRITER = re.compile(r"^\s*(\S+=\S*\s+)*(sudo\s+)?(\S*/)?(tee|cp|mv|ln|rm|touch|install|rsync|dd|chmod|chown|"
                     r"truncate|python3?(\.\d+)?|uv)\b|\bsed\s+(-\S+\s+)*-i|\bfind\b.*\s-(delete|exec)\b")
_WRITE_TARGET = re.compile(r"(?:(?:^|[^<>&0-9])>>?|\btee\s+(?:-\S+\s+)*)\s*['\"]?([^\s'\";|&<>]+)")
_QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
_TEXT_FILE = re.compile(r"\.(md|txt|rst|tex|bib)$")
_FRAMEWORK = re.compile(r"(^|/)score/(checks|contracts|store|graph|review|adapters|stages)/|(^|/)\.claude/hooks/")

_MESSAGE = (
    "Blocked: only the owner accepts or rejects by hand, waives a gate or overrides a spend; the runner accepts and\n"
    "clears by the gates.\n"
    "  {what}\n"
    "Run the stages (.venv/bin/python -m score.stages run <place>): the runner accepts a passing output that got no\n"
    "worse and clears a paid run whose inputs passed. An agent's verdict never stands in for the gates or the owner\n"
    "(docs/bible.md, the layered framework). A decision he made in chat is recorded by decide-yes and applied only\n"
    "as `decide <yes id>` (the agents' door, or tools/cloud/this_pc.py for a run on his PC)."
)


def _owner_command(command):
    """Why a shell command runs or calls the owner's accept, reject, spend, waive or lock, or None."""
    segments = _SEGMENTS.split(_QUOTED.sub(_blank_separators, command))
    if any(_REVIEW_RUN.search(segment) for segment in segments):
        return "runs the owner's accept, reject, spend or waive command"
    if any(not _YES_ID.match(found.group("id") or "") for found in map(_DECIDE_RUN.search, segments) if found):
        return "applies a decision without the id of his yes recorded by decide-yes"
    if _OWNER_CALL.search(command) and (_PYTHON.search(command) or _script_write(command)):
        return "calls the owner's accept, reject, spend or waive from Python, or writes a script that does"
    if _LOCK_CALL.search(command) and (_PYTHON.search(command) or _script_write(command)):
        return "calls the owner's lock or the chat route's own steps from Python, or writes a script that does"
    return None


def _blank_separators(quoted):
    """A quoted string with its command separators blanked, so a commit message's ``; python ...`` is not a command."""
    return re.sub(r"[;&|\n]", " ", quoted.group(0))


def _script_write(command):
    """Whether a shell command writes a file outside the framework package."""
    return any(not _FRAMEWORK.search(target) for target in _WRITE_TARGET.findall(command))


def _unmarking(command):
    """Why a shell command takes Claude Code's mark off a process or fakes a terminal, or None."""
    if (_AGENT_MARK.search(command) and _UNMARK.search(command)) or _CLEARED_ENV.search(command):
        return "takes Claude Code's mark off a process"
    if _FAKE_TERMINAL.search(command) and "score" in command:
        return "fakes a terminal for a score command"
    return None


def _owner_area_write(command):
    """Why a shell command writes the store's accepts, rejects, waivers, spend yeses or clearances, or None."""
    for segment in _SEGMENTS.split(command):
        if _REDIRECT_INTO_OWNER.search(segment):
            return "redirects into the store's accepts, rejects, waivers, spend yeses or clearances"
        if _OWNER_PATH.search(segment) and _WRITER.search(segment):
            return "writes the store's accepts, rejects, waivers, spend yeses or clearances"
    return None


def _bash_offence(command):
    """Why a shell command is the owner's alone, or None."""
    return _owner_command(command) or _unmarking(command) or _owner_area_write(command)


def _file_offence(path, content):
    """Why a file write is the owner's alone, or None."""
    if _OWNER_PATH.search(path):
        return f"writes {path}"
    if _FRAMEWORK.search(path):
        return None
    if _OWNER_CALL.search(content) and not _TEXT_FILE.search(path):
        return f"writes a call to the owner's accept, reject, spend or waive into {path}"
    if _LOCK_CALL.search(content) and not _TEXT_FILE.search(path) and not _DASHBOARD.search(path):
        return f"writes a call to the owner's lock or the chat route's own steps into {path}"
    if _AGENT_MARK.search(content):
        return f"writes code that touches Claude Code's mark into {path}"
    return None


def _artifact_offence(tool_input):
    """Why an artifact database write is the owner's alone, or None."""
    if tool_input.get("action") != "write_db":
        return None
    writes = [tool_input, *(tool_input.get("writes") or [])]
    names = [str(write.get(part) or "") for write in writes if isinstance(write, dict)
             for part in ("collection", "doc_id")]
    if any(_OWNER_NAME.search(name) for name in names):
        return "writes accepts, rejects, waivers, spend yeses or clearances into an artifact's database"
    return None


def _offence(payload):
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool == "Bash":
        return _bash_offence(str(tool_input.get("command", "")))
    if tool in ("Write", "Edit", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        content = str(tool_input.get("content") or tool_input.get("new_string") or tool_input.get("new_source") or "")
        return _file_offence(path, content)
    if tool == "Artifact":
        return _artifact_offence(tool_input)
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        offence = _offence(payload)
    except Exception:
        return 0
    if offence:
        print(_MESSAGE.format(what=offence), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
