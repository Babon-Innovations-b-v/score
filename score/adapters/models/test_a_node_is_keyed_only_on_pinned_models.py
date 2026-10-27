"""The model adapter keys a node only on pinned images and models: an image by digest, each model by revision, hash
and licence, a model not for commercial use only in a tool-only kind, an API model by its id and settings; a step
asked through the claude-code adapter is asked of its pinned model once, on the subscription, written down.

Breaks (each applied once, seen red, reverted), in score/adapters/models/__init__.py:
- every built kind pinned: record carries `"digest": ""`.
- loose image or model refused: built_image's `if not image.get("digest"):` becomes `if False:`.
- commercial use: pinned_models' commercial check becomes `if False:`.
- API model: api_record's `if kind not in API:` becomes `if False:` (a KeyError, not NotPinned).
And in score/adapters/models/claude_code.py:
- asked once: ask's `if kept.exists():` becomes `if False:` (the second ask calls Claude again).
- subscription only: the environment filter `if name != "ANTHROPIC_API_KEY"` becomes `if True` (the key reaches it).
- a failed answer kept: ask's `raise Unanswered(...)` becomes `answer, result = repr(error), {}` (cached, read back).
- the schema as Gemini wrote it: json_schema's `value.lower()` becomes `value` (OBJECT reaches --json-schema).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/adapters/models/
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.adapters import models  # noqa: E402
from score.adapters.models import claude_code  # noqa: E402

MODEL = {"name": "m", "source": "hf:x/m", "revision": "abc", "sha256": "f" * 64, "licence": "Apache-2.0",
         "commercial_use": True}


def images_folder(built, listed):
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "images.json").write_text(json.dumps(built))
    (folder / "kind").mkdir()
    (folder / "kind" / "models.json").write_text(json.dumps(listed))
    return folder


def refused(call):
    try:
        call()
    except models.NotPinned as refusal:
        return str(refusal)
    raise AssertionError("taken")


def test_every_built_kind_in_the_repo_gives_a_pinned_record():
    built = json.loads((models.IMAGES / "images.json").read_text())
    for kind in built:
        found = models.record(kind, tool_only=True)
        assert found["digest"].startswith("sha256:"), kind
        assert all(model["revision"] and model["licence"] for model in found["models"]), kind


def test_an_image_without_a_digest_or_a_model_without_a_pin_is_refused():
    loose_image = images_folder({"kind": {"image": "x:1"}}, [MODEL])
    assert "digest" in refused(lambda: models.record("kind", images=loose_image))
    loose_model = images_folder({"kind": {"image": "x:1", "digest": "sha256:1"}}, [{**MODEL, "revision": ""}])
    assert "revision" in refused(lambda: models.record("kind", images=loose_model))
    assert "no image" in refused(lambda: models.record("other", images=loose_model))


def test_a_model_not_for_commercial_use_needs_a_tool_only_kind():
    folder = images_folder({"kind": {"image": "x:1", "digest": "sha256:1"}}, [{**MODEL, "commercial_use": False}])
    assert "commercial" in refused(lambda: models.record("kind", images=folder))
    assert models.record("kind", tool_only=True, images=folder)["models"][0]["name"] == "m"


def test_an_api_model_is_keyed_on_its_id_and_settings():
    found = models.api_record("gemini-judge")
    assert found["model"].startswith("gemini-") and found["temperature"] == 0 and found["commercial_use"]
    assert "no API model" in refused(lambda: models.api_record("other"))


# A stand-in `claude` on PATH: counts its calls, keeps what it was given, answers the colour it was asked, or an error
# result when the text says "fail".
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, pathlib, sys
here = pathlib.Path(__file__).parent
calls = here / "calls"
calls.write_text(str(int(calls.read_text() or 0) + 1) if calls.exists() else "1")
line = json.loads(sys.stdin.readline())
(here / "last.json").write_text(json.dumps({"argv": sys.argv[1:], "line": line,
                                            "key": os.environ.get("ANTHROPIC_API_KEY")}))
text = line["message"]["content"][-1]["text"]
result = {"type": "result", "subtype": "success", "is_error": "fail" in text, "result": "",
          "structured_output": None if "fail" in text else {"colour": "red"},
          "usage": {"input_tokens": 5, "output_tokens": 3}}
print(json.dumps({"type": "system", "subtype": "init"}))
print(json.dumps(result, separators=(",", ":")))
"""


def fake_claude(monkeypatch):
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "claude").write_text(FAKE_CLAUDE)
    (folder / "claude").chmod(0o755)
    home = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setenv("PATH", f"{folder}:{os.environ['PATH']}")
    monkeypatch.setattr(claude_code, "LEDGER", home / "claude-ledger.jsonl")
    monkeypatch.setattr(claude_code, "CACHE", home / "claude-cache")
    return folder


def a_body(text):
    return {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "image/png", "data": "AAAA"}},
                                                     {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": {"type": "OBJECT", "properties": {
                                     "colour": {"type": "STRING", "enum": ["red", "blue"]}},
                                     "required": ["colour"], "propertyOrdering": ["colour"]}}}


def test_a_claude_code_ask_is_asked_of_its_pinned_model_once_on_the_subscription(monkeypatch):
    folder = fake_claude(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-not-to-be-used")
    assert claude_code.record() == {"kind": "claude-code", "provider": "claude-code-subscription",
                                    "model": "claude-opus-5-5", "tools": "none", "euros": 0}
    first = claude_code.asked({"a": a_body("what colour?")}, "body-face")
    again = claude_code.asked({"a": a_body("what colour?")}, "body-face")
    assert json.loads(first["a"]) == {"colour": "red"} and again == first
    assert (folder / "calls").read_text() == "1"
    sent = json.loads((folder / "last.json").read_text())
    assert sent["key"] is None
    assert sent["argv"][sent["argv"].index("--model") + 1] == "claude-opus-5-5"
    schema = json.loads(sent["argv"][sent["argv"].index("--json-schema") + 1])
    assert schema == {"type": "object", "properties": {"colour": {"type": "string", "enum": ["red", "blue"]}},
                      "required": ["colour"]}
    content = sent["line"]["message"]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["data"] == "AAAA" and content[1]["type"] == "text"
    lines = [json.loads(line) for line in claude_code.LEDGER.read_text().splitlines()]
    assert [line["state"] for line in lines] == ["started", "finished"]
    assert all(line["euros"] == 0 and line["caller"] == "body-face" and line["model"] == "claude-opus-5-5"
               and line["prompt"] == claude_code.body_hash(a_body("what colour?")) for line in lines)


def test_a_claude_code_ask_with_no_answer_is_unanswered_and_asked_fresh_next_time(monkeypatch):
    folder = fake_claude(monkeypatch)
    first = claude_code.asked({"a": a_body("fail")}, "body-face")["a"]
    second = claude_code.asked({"a": a_body("fail")}, "body-face")["a"]
    assert isinstance(first, claude_code.Unanswered) and isinstance(second, claude_code.Unanswered)
    assert (folder / "calls").read_text() == "2"
    assert [json.loads(line)["state"] for line in claude_code.LEDGER.read_text().splitlines()] == \
        ["started", "failed", "started", "failed"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
