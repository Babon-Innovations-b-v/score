"""The claude-code adapter: a step's Gemini ask answered by Claude through a headless Claude Code call on this PC,
against the owner's subscription (owner, 2026-10-27: "keep those calls minimal aswell, as ur a perf good llm urself
aswell").

    answers = claude_code.asked({key: generateContent body}, caller="body-face")
    # {key: the answer's JSON text, or an Unanswered saying why there is none}: route_ask.asked's shape

Each body is the one the step builds for Gemini, read as it is: its pictures (inline PNG parts) and text, in order,
become one user message, its responseSchema the answer's JSON Schema (`--json-schema`), the pinned model
`PINNED` (`claude -p --model claude-opus-5-5`, no tools, no settings, no session kept, the
API key left out of its environment so it bills the subscription and never the API). Claude Code exposes no
temperature: an answer is asked once and kept (`CACHE`, by the hash of the model and the body), so a rerun reads it
back rather than drawing again. Every call is written down before it starts and when it ends (`LEDGER`: model,
caller, the body's hash, minutes, tokens, EUR 0 against the subscription, the run's id as `tag`). An ask with no
usable answer (a time-out, an error result, no structured answer) is Unanswered and never kept, so the next try asks
it fresh. Asks of one call run side by side, at most PARALLEL at once. With no `claude` on the machine `asked` raises
NotHere before anything is asked, saying the step runs on this PC: a set-up fault that stops the row, never a gap a
take and never a fall-back to Gemini.

The finish route's palette, library, list and recheck ask here (their `ask`, owner via the coordinator, 2026-10-27,
after the side-by-side on the backlog PRD #36): environment 1 runs on the owner's PC (tools/cloud/this_pc.py), where
Claude Code is installed; the conductor has none, so those rows stop there with NotHere. body-face stays on Gemini.
This module is in those rows' code version, so a change of the pinned model re-keys them.
"""
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import uuid

KIND = "claude-code"
# The pinned model and how it is reached (`record`: what a step asking here is disclosed as). Kept here, not in
# models.API: models/__init__.py is in the sound rows' code version.
PINNED = {"provider": "claude-code-subscription", "model": "claude-opus-5-5", "tools": "none", "euros": 0}
HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
LEDGER = HOME / "cloud" / "claude-ledger.jsonl"
CACHE = HOME / "cloud" / "claude-cache"
PARALLEL = 8
TIMEOUT = 900  # seconds an ask may take: the side-by-side's nine asks took 0.06 to 0.8 min (2026-10-27)


class Unanswered(ValueError):
    """An ask Claude gave no usable answer to: a time-out, an error result or no structured answer. A ValueError, so
    the finish route's UNANSWERED (finish_ask.py) makes it its take's gap, as a Gemini ask with no answer."""


class NotHere(RuntimeError):
    """This machine has no Claude Code: a step that asks through it runs on the owner's PC only. Not an Unanswered:
    a set-up fault that stops the row, never a gap a take and never a Gemini ask in its place."""


def record():
    """What a step's `model` param carries for this adapter: its kind and pinned model."""
    return {"kind": KIND, **PINNED}


def json_schema(gemini):
    """A Gemini responseSchema (OpenAPI types in capitals, propertyOrdering) as the JSON Schema Claude Code takes."""
    if isinstance(gemini, list):
        return [json_schema(item) for item in gemini]
    if not isinstance(gemini, dict):
        return gemini
    schema = {}
    for name, value in gemini.items():
        if name == "propertyOrdering":
            continue
        if name == "type":
            schema["type"] = value.lower()
        elif name == "properties":
            schema["properties"] = {key: json_schema(item) for key, item in value.items()}
        elif name == "nullable":
            continue
        else:
            schema[name] = json_schema(value)
    if gemini.get("nullable"):
        schema["type"] = [schema["type"], "null"]
    return schema


def message(body):
    """The body's one user turn as a Claude Code stream-json line: its pictures and text, in order."""
    content = []
    for part in body["contents"][0]["parts"]:
        if "inline_data" in part:
            content.append({"type": "image", "source": {"type": "base64", "media_type": part["inline_data"]["mime_type"],
                                                        "data": part["inline_data"]["data"]}})
        else:
            content.append({"type": "text", "text": part["text"]})
    return json.dumps({"type": "user", "message": {"role": "user", "content": content}})


def body_hash(body):
    """The hash an ask is cached and ledgered by: of the pinned model and the body."""
    return hashlib.sha256(json.dumps([PINNED["model"], body], sort_keys=True).encode()).hexdigest()


def write(entry):
    """Append one line to the ledger, stamped with the time."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:
        ledger.write(json.dumps({"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                 **entry}) + "\n")


def command(body):
    """The headless Claude Code call for one body."""
    schema = json_schema(body["generationConfig"]["responseSchema"])
    return ["claude", "-p", "--model", PINNED["model"], "--input-format", "stream-json",
            "--output-format", "stream-json", "--verbose", "--json-schema", json.dumps(schema), "--tools", "",
            "--setting-sources", "", "--no-session-persistence"]


def result_of(stdout):
    """The answer's JSON text from the call's result line; Unanswered when it has none."""
    results = [found for found in map(json.loads, filter(str.strip, stdout.splitlines()))
               if found.get("type") == "result"]
    if not results:
        raise Unanswered(f"no result line: {stdout[-200:]!r}")
    result = results[-1]
    if result.get("is_error") or result.get("structured_output") is None:
        raise Unanswered(f"no structured answer: {result.get('subtype')} {str(result.get('result'))[:200]}")
    return json.dumps(result["structured_output"]), result


def ask(body, caller):
    """One body asked once: its answer read back when kept, else asked, written down and kept."""
    digest = body_hash(body)
    kept = CACHE / f"{digest}.json"
    if kept.exists():
        return kept.read_text()
    call = uuid.uuid4().hex
    line = {"call": call, "model": PINNED["model"], "caller": caller, "prompt": digest,
            "tag": os.environ.get("SCORE_RUN_ID")}
    write({**line, "state": "started", "euros": 0})
    environment = {name: value for name, value in os.environ.items() if name != "ANTHROPIC_API_KEY"}
    start = time.monotonic()
    try:
        with tempfile.TemporaryDirectory() as folder:  # no project's CLAUDE.md or settings reach the call
            done = subprocess.run(command(body), input=message(body) + "\n", capture_output=True, text=True,
                                  timeout=TIMEOUT, cwd=folder, env=environment)
        answer, result = result_of(done.stdout)
    except (subprocess.TimeoutExpired, Unanswered, ValueError) as error:
        write({**line, "state": "failed", "minutes": round((time.monotonic() - start) / 60, 2), "euros": 0,
               "error": repr(error)[:300]})
        raise Unanswered(repr(error)[:300]) from error
    usage = result.get("usage", {})
    write({**line, "state": "finished", "minutes": round((time.monotonic() - start) / 60, 2), "euros": 0,
           "input": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
           + usage.get("cache_read_input_tokens", 0), "output": usage.get("output_tokens", 0)})
    CACHE.mkdir(parents=True, exist_ok=True)
    part = kept.with_name(f"{kept.name}.{os.getpid()}")
    part.write_text(answer)
    part.replace(kept)
    return answer


def asked(bodies, caller):
    """{key: the answer's JSON text, or the Unanswered saying why there is none} of {key: generateContent body},
    asked side by side; NotHere on a machine with no Claude Code."""
    if shutil.which("claude") is None:
        raise NotHere(f"{caller}: runs on this PC (tools/cloud/this_pc.py): this machine has no Claude Code "
                      f"(`claude`), and the step never asks Gemini in its place")

    def answered(key):
        try:
            return ask(bodies[key], caller)
        except Unanswered as error:
            return error
    with concurrent.futures.ThreadPoolExecutor(PARALLEL) as pool:
        return dict(zip(bodies, pool.map(answered, bodies)))
