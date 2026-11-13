"""The model adapter keys a node only on pinned images and models: an image by digest, each model by revision, hash
and licence, a model not for commercial use only in a tool-only kind, an API model by its id and settings; a step
asked through the claude-code adapter is asked of its pinned model once, on the subscription, written down.

Breaks (each applied once, seen red, reverted), in score/adapters/models/__init__.py:
- every built kind pinned: record carries `"digest": ""`.
- loose image or model refused: built_image's `if not image.get("digest"):` becomes `if False:`.
- commercial use: pinned_models' commercial check becomes `if False:`.
- API model: api_record's `if kind not in API:` becomes `if False:` (a KeyError, not NotPinned).
And in score/adapters/models/claude_code.py:
- asked once: ask's `if kept.exists():` becomes `if False:` (the kept ask calls Claude again).
- subscription only: the environment filter `if name != "ANTHROPIC_API_KEY"` becomes `if True` (the key reaches it).
- a failed answer kept: ask's `raise Unanswered(...)` becomes `answer, result = repr(error), {}` (cached, read back).
- a limit taken for an answer: result_of's `if refusal:` becomes `if False:` (the weekly limit is an Unanswered,
  a take's gap, and never asked again by the runner).
- a limit read from words only: unavailable's `kind = f"{info.get(...)} limit"` line becomes `pass` (the structured
  limit with no words is an Unanswered).
- a real refusal taken for a limit: REFUSAL_WORDS gains `|help` (the refusal "I can't help with that" is Unavailable).
- an overload not retried: Overloaded's `ConnectionError, ` base is dropped (not transient to the runner).
- runs on this PC: asked's `if shutil.which("claude") is None:` becomes `if False:` (no NotHere off the PC).
- the schema as Gemini wrote it: json_schema's `value.lower()` becomes `value` (OBJECT reaches --json-schema).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/adapters/models/
"""
import collections
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import graph  # noqa: E402
from score.adapters import models  # noqa: E402
from score.adapters.models import claude_code  # noqa: E402

MODEL = {"name": "m", "source": "hf:x/m", "revision": "abc", "sha256": "f" * 64, "licence": "Apache-2.0",
         "commercial_use": True}
PINNED_IMAGE = {"image": "x:1", "digest": "sha256:1"}

# A stand-in `claude` on PATH: writes one line a call of what it was given (argv, the message, the API key it saw),
# answers the colour it was asked, or an error result when the text says "fail"; "refuse" a refusal with no answer;
# "limit" the account's weekly limit in structured fields alone (a rejected rate_limit_event, an assistant `error`),
# "worded" in the result's words alone (checkout 70's conductor); "busy" an overload.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, pathlib, sys
line = json.loads(sys.stdin.readline())
with (pathlib.Path(__file__).parent / "sent.jsonl").open("a") as sent:  # one line a call, appended side by side
    sent.write(json.dumps({"argv": sys.argv[1:], "line": line, "key": os.environ.get("ANTHROPIC_API_KEY")}) + "\\n")
text = line["message"]["content"][-1]["text"]
refused = any(word in text for word in ("fail", "refuse", "limit", "worded", "busy"))
said = {"refuse": "I can't help with that.", "worded": "You've hit your weekly limit \\u00b7 resets Nov 12, 5am (UTC)",
        "busy": "API Error: Repeated 529 Overloaded errors"}
result = {"type": "result", "subtype": "success", "is_error": refused and "refuse" not in text,
          "result": next((words for word, words in said.items() if word in text), ""),
          "structured_output": None if refused else {"colour": "red"},
          "usage": {"input_tokens": 5, "output_tokens": 3}}
print(json.dumps({"type": "system", "subtype": "init"}))
if "limit" in text:
    print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": 1794459600,
                                                                      "rateLimitType": "seven_day"}}))
if "limit" in text or "busy" in text:
    print(json.dumps({"type": "assistant", "error": "rate_limit" if "limit" in text else "overloaded",
                      "message": {"role": "assistant", "content": [{"type": "text", "text": ""}]}}))
print(json.dumps(result, separators=(",", ":")))
"""

# A keying refused: its error's type, words its message holds, whether a later try may not meet it (transient), whether
# it is a take's gap (a ValueError), and whether it is raised or handed back as the body's answer.
Refusal = collections.namedtuple("Refusal", "kind words transient gap raised")


def images_folder(image, model):
    """A folder of one built kind "kind" (its image entry) listing one model (MODEL with `model`'s fields)."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "images.json").write_text(json.dumps({"kind": image}))
    (folder / "kind").mkdir()
    (folder / "kind" / "models.json").write_text(json.dumps([{**MODEL, **model}]))
    return folder


def a_body(text):
    return {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "image/png", "data": "AAAA"}},
                                                     {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": {"type": "OBJECT", "properties": {
                                     "colour": {"type": "STRING", "enum": ["red", "blue"]}},
                                     "required": ["colour"], "propertyOrdering": ["colour"]}}}


def outcome(call):
    """What a keying gave: its value, or (error, raised) when it refused, raised or handed back as the answer."""
    try:
        found = call()
    except Exception as error:  # noqa: BLE001 - every refusal is judged against its row
        return error, True
    return (found, False) if isinstance(found, Exception) else found


def test_a_node_is_keyed_only_on_pinned_models(monkeypatch):
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "claude").write_text(FAKE_CLAUDE)
    (folder / "claude").chmod(0o755)
    home = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setenv("PATH", f"{folder}:{os.environ['PATH']}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-not-to-be-used")
    monkeypatch.setattr(claude_code, "LEDGER", home / "claude-ledger.jsonl")
    monkeypatch.setattr(claude_code, "CACHE", home / "claude-cache")
    asks = {}  # each body's hash: (its text, the caller that asked it)

    def ask(*texts, caller="body-face"):
        asks.update({claude_code.body_hash(a_body(text)): (text, caller) for text in texts})
        return claude_code.asked({key: a_body(text) for key, text in zip("ab", texts)}, caller)

    def off_the_pc():
        with monkeypatch.context() as machine:
            machine.setenv("PATH", str(home))  # a machine with no `claude`: the conductor
            return ask("what colour, off the PC?", caller="finish-route-list")

    built = json.loads((models.IMAGES / "images.json").read_text())
    pinned = (True, True)
    cases = [  # (row, the keying, its value or its Refusal), in the order asked: the kept ask follows the first
        *[(f"built kind {kind}", lambda kind=kind: (lambda found: (found["digest"].startswith("sha256:"), all(
            model["revision"] and model["licence"] for model in found["models"])))(models.record(kind, tool_only=True)),
           pinned) for kind in built],
        ("image without a digest", lambda: models.record("kind", images=images_folder({"image": "x:1"}, {})),
         Refusal(models.NotPinned, ("digest",), False, False, True)),
        ("model without a revision", lambda: models.record("kind", images=images_folder(PINNED_IMAGE, {"revision": ""})),
         Refusal(models.NotPinned, ("revision",), False, False, True)),
        ("kind with no image", lambda: models.record("other", images=images_folder(PINNED_IMAGE, {})),
         Refusal(models.NotPinned, ("no image",), False, False, True)),
        ("not for commercial use in a shipped kind",
         lambda: models.record("kind", images=images_folder(PINNED_IMAGE, {"commercial_use": False})),
         Refusal(models.NotPinned, ("commercial",), False, False, True)),
        ("not for commercial use in a tool-only kind", lambda: models.record(
            "kind", tool_only=True, images=images_folder(PINNED_IMAGE, {"commercial_use": False}))["models"][0]["name"],
         "m"),
        ("API model by id and settings", lambda: (lambda found: (found["model"].startswith("gemini-"),
                                                                 found["temperature"], found["commercial_use"]))(
            models.api_record("gemini-judge")), (True, 0, True)),
        ("unknown API model", lambda: models.api_record("other"),
         Refusal(models.NotPinned, ("no API model",), False, False, True)),
        ("claude-code record", claude_code.record, {"kind": "claude-code", "provider": "claude-code-subscription",
                                                    "model": "claude-opus-5-5", "tools": "none", "euros": 0}),
        ("claude-code ask", lambda: json.loads(ask("what colour?")["a"]), {"colour": "red"}),
        ("claude-code ask kept", lambda: json.loads(ask("what colour?")["a"]), {"colour": "red"}),
        ("failed answer", lambda: ask("fail")["a"],
         Refusal(claude_code.Unanswered, ("no structured answer",), False, True, False)),
        ("failed answer asked again", lambda: ask("fail")["a"],
         Refusal(claude_code.Unanswered, ("no structured answer",), False, True, False)),
        ("a real refusal", lambda: ask("refuse")["a"],
         Refusal(claude_code.Unanswered, ("can't help with that",), False, True, False)),
        ("weekly limit in structured fields", lambda: ask("limit", "what colour is b?", caller="surface-library"),
         Refusal(claude_code.Unavailable, ("seven_day limit, resets 2026-11-12T05:00+00:00",), False, False, True)),
        ("weekly limit in words alone", lambda: ask("worded", "what colour is b?", caller="surface-library"),
         Refusal(claude_code.Unavailable, ("hit your weekly limit, resets Nov 12, 5am (UTC)",), False, False, True)),
        ("weekly limit asked again", lambda: ask("limit", "what colour is b?", caller="surface-library"),
         Refusal(claude_code.Unavailable, ("seven_day",), False, False, True)),
        ("overload", lambda: ask("busy", caller="surface-library"),
         Refusal(claude_code.Overloaded, ("overloaded",), True, False, True)),
        ("a machine with no claude code", off_the_pc,
         Refusal(claude_code.NotHere, ("runs on this PC", "finish-route-list"), False, False, True)),
    ]
    for row, call, expected in cases:
        found = outcome(call)
        if isinstance(expected, Refusal):
            assert isinstance(found, tuple) and isinstance(found[0], Exception), f"{row}: taken as {found!r}"
            error, raised = found
            assert (type(error), raised) == (expected.kind, expected.raised), f"{row}: {error!r} raised={raised}"
            assert all(words in str(error) for words in expected.words), f"{row}: {error}"
            assert (graph.transient(error), isinstance(error, ValueError)) == (expected.transient, expected.gap), row
        else:
            assert found == expected, f"{row}: {found!r}"

    sent = [json.loads(line) for line in (folder / "sent.jsonl").read_text().splitlines()]
    texts = collections.Counter(call["line"]["message"]["content"][-1]["text"] for call in sent)
    assert texts == {"what colour?": 1, "what colour is b?": 1, "fail": 2, "refuse": 1, "limit": 2, "worded": 1,
                     "busy": 1}  # each refusal asked again, each answer once, nothing off the PC
    schema = {"type": "object", "properties": {"colour": {"type": "string", "enum": ["red", "blue"]}},
              "required": ["colour"]}
    for call in sent:
        argv, content = call["argv"], call["line"]["message"]["content"]
        assert call["key"] is None, "the API key reached Claude Code"
        assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
        assert json.loads(argv[argv.index("--json-schema") + 1]) == schema
        assert content[0]["type"] == "image" and content[0]["source"]["data"] == "AAAA" and content[1]["type"] == "text"
    assert sorted(path.name for path in claude_code.CACHE.iterdir()) == sorted(
        f"{claude_code.body_hash(a_body(text))}.json" for text in ("what colour?", "what colour is b?"))
    lines = [json.loads(line) for line in claude_code.LEDGER.read_text().splitlines()]
    assert all(line["euros"] == 0 and line["model"] == "claude-opus-5-5" and line["caller"] == asks[line["prompt"]][1]
               for line in lines)
    ended = {"what colour?": "finished", "what colour is b?": "finished"}
    assert collections.Counter((asks[line["prompt"]][0], line["state"]) for line in lines) == collections.Counter(
        {(text, state): count for text, count in texts.items() for state in ("started", ended.get(text, "failed"))})


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
