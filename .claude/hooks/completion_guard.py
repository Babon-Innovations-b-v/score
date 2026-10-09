#!/usr/bin/env python3
"""Stop guard: a session may not end on the claim that a place is done while the place's evidence says otherwise.

Reads the Stop or SubagentStop payload on stdin and, from the session's (or sub-agent's) transcript, finds the places
its tool calls worked on (a place's ``data/...`` file, its ``work/usd`` or ``work/review`` folder, or a stage tool run
on it) and whether its last message claims one of them is done (a sentence naming the place, or "every/all places",
with complete, done, finished or ready and no negation). For each claimed place it runs the completion gate
(tools/usd/complete.py) and blocks the stop when the gate does not pass, listing every requirement that failed or is
unknown. A session that makes no such claim ends as usual: the guard refuses a false "done", it does not force every
session to finish a place. (LEGO-Anything, arXiv 2609.36380, App. G.6: runtime hooks keep the agent from finishing
while validations are stale.)

FAILURE POLICY: the hook's own machinery fails open (an unreadable payload or transcript allows the stop), but a gate
verdict of unknown blocks like fail. Exit 2 + stderr is the only block path.
"""

import json
import pathlib
import re
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools/usd"))

_TOOL_RUNS = r"(?:export|page|settle|complete|resting|placeholders|made_only)\.py\s+(?:check\s+|done\s+)?"
_CLAIM = re.compile(r"\b(complete|completed|done|finished|ready)\b", re.IGNORECASE)
_NEGATION = re.compile(r"\b(not|incomplete|unfinished|blocked|fails?|failing)\b|n't\b", re.IGNORECASE)
_EVERY = re.compile(r"\b(every|all)\s+(the\s+)?places?\b", re.IGNORECASE)


def places():
    """Every place the framework knows: one with a kit or a scene record."""
    return sorted({path.stem for folder in ("data/kit", "data/scene") for path in (_REPO_ROOT / folder).glob("*.json")})


def transcript_entries(path):
    """The transcript's entries, in order (one JSON object a line); unreadable lines are skipped."""
    found = []
    for line in pathlib.Path(path).read_text().splitlines():
        try:
            found.append(json.loads(line))
        except ValueError:
            continue
    return found


def contents(entry):
    """An entry's message content as a list of blocks."""
    message = entry.get("message") or {}
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def touched(entries, known):
    """The places the session's tool calls worked on."""
    calls = " ".join(json.dumps(block.get("input", {})) for entry in entries if entry.get("type") == "assistant"
                     for block in contents(entry) if block.get("type") == "tool_use")
    names = "|".join(re.escape(place) for place in known)
    patterns = (rf"data/(?:inventory|kit|scene|characters)/({names})\.json", rf"work/(?:usd|review)/({names})\b",
                rf"{_TOOL_RUNS}({names})\b")
    return {match for pattern in patterns for match in re.findall(pattern, calls)}


def last_text(entries):
    """The text of the session's last assistant message."""
    for entry in reversed(entries):
        if entry.get("type") == "assistant":
            texts = [block.get("text", "") for block in contents(entry) if block.get("type") == "text"]
            if texts:
                return "\n".join(texts)
    return ""


def claimed(text, candidates):
    """The places among these that the text claims are done."""
    found = set()
    text = re.sub(r"`[^`]*`", "", text)  # a quoted command (`complete.py done wreck`) is not a claim
    for sentence in re.split(r"(?<=[.!?;])\s+|\n+", text):
        if not _CLAIM.search(sentence) or _NEGATION.search(sentence):
            continue
        if _EVERY.search(sentence):
            found |= set(candidates)
        found |= {place for place in candidates if re.search(rf"\b{re.escape(place)}\b", sentence, re.IGNORECASE)}
    return found


def refusals(claims):
    """For each claimed place the gate does not pass: its name and the requirements that did not pass."""
    import complete
    found = {}
    for place in sorted(claims):
        written = complete.manifest(place, complete.stage_path(place))
        if written["verdict"] != complete.PASS:
            found[place] = [requirement for requirement in written["requirements"]
                            if requirement["result"] != complete.PASS]
    return found


def message(refused):
    """The block reason fed back to the session."""
    lines = ["BLOCKED: the last message says a place is done, but the completion gate (tools/usd/complete.py) does "
             "not pass for it:"]
    for place, failing in refused.items():
        lines.append(f"  {place}:")
        lines += [f"    {requirement['name']}: {requirement['result']}: {requirement['why']}" for requirement in failing]
    lines.append("Make the gate pass (complete.py check <place>, then complete.py done <place>), or say plainly that "
                 "the place is not complete and what is left. Unknown blocks like fail.")
    return "\n".join(lines)


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        # SubagentStop names the sub-agent's own transcript; Stop has only the session's
        entries = transcript_entries(payload.get("agent_transcript_path") or payload["transcript_path"])
    except Exception:
        sys.exit(0)  # fail-open: no readable session to judge
    # the payload's copy: the transcript file may not hold the final message yet when the hook runs
    text = payload.get("last_assistant_message") or last_text(entries)
    claims = claimed(text, touched(entries, places()))
    if not claims:
        sys.exit(0)
    refused = refusals(claims)
    if refused:
        print(message(refused), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
