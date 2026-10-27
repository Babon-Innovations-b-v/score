"""The per-row parameters of a scene's effects that neither its design nor a rule gives (each kind's `asked` in
data/checks/effects.json: how wide a drilling rig's bore is and how much rock it has brought up), read off the scene's
locked concept by one recorded model call per scene inside the batch, never typed by hand: the claude-code adapter
(score/adapters/models/claude_code.py: claude-opus-5-5 on the owner's subscription, EUR 0, cached by its body and
written to its ledger), so a rerun reads the same answer back. The answers and their reasons go into the scene's
effects record (each emitter's `asked`).

    values(place, concept, rows, effects)   {(row id, effect): {"values": {parameter: number}, "why": {...}}}
"""
import base64
import json
import pathlib

from score.adapters.models import claude_code

CALLER = "effects-layer"
SCHEMA = {"type": "OBJECT", "properties": {"answers": {"type": "ARRAY", "items": {
    "type": "OBJECT", "properties": {"row": {"type": "STRING"}, "effect": {"type": "STRING"},
                                     "parameter": {"type": "STRING"}, "value": {"type": "NUMBER"},
                                     "why": {"type": "STRING"}},
    "required": ["row", "effect", "parameter", "value", "why"]}}}, "required": ["answers"]}


def wanted(rows, effects):
    """What the scene's rows need asked: one line per row, effect and parameter (the row's name and size in metres
    from the design, what the parameter means from the effect's kind)."""
    return [{"row": row["id"], "name": row.get("name"), "size_metres": row.get("size"), "effect": effect,
             "parameter": parameter, "means": means}
            for row, effect in rows for parameter, means in effects["kinds"][effect].get("asked", {}).items()]


def body(place, concept, wants):
    """The scene's one ask, as a Gemini generateContent body: its locked concept and what is wanted."""
    text = (f"This is the locked concept picture of the scene '{place}'. Each line below is a thing in it (its row "
            "in the scene's inventory, its size in metres) carrying an effect, and one parameter of that effect. "
            "For every line give one number in the unit it names: read off the picture where it shows it, else the "
            "likeliest for the thing as the picture and its size show it. Say why in one sentence.\n"
            + json.dumps(wants, indent=1))
    picture = base64.b64encode(pathlib.Path(concept).read_bytes()).decode()
    return {"contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "image/png", "data": picture}},
                                                     {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA}}


def read(answer, wants):
    """The answer's values by (row, effect); a line wanted and not answered with a number above 0 stops the row."""
    found = {(line["row"], line["effect"], line["parameter"]): line for line in json.loads(answer)["answers"]}
    values = {}
    for want in wants:
        line = found.get((want["row"], want["effect"], want["parameter"]))
        if line is None or not float(line["value"]) > 0:
            raise ValueError(f"{CALLER}: no number above 0 for {want['row']} {want['effect']} {want['parameter']}: "
                             f"{line}")
        held = values.setdefault((want["row"], want["effect"]), {"values": {}, "why": {}})
        held["values"][want["parameter"]] = float(line["value"])
        held["why"][want["parameter"]] = line["why"]
    return values


def values(place, concept, rows, effects):
    """{(row id, effect): {"values", "why"}} for the scene's (row, effect) pairs whose kind asks: one call, none
    when nothing is asked."""
    wants = wanted(rows, effects)
    if not wants:
        return {}
    answer = claude_code.asked({place: body(place, concept, wants)}, CALLER)[place]
    if isinstance(answer, Exception):
        raise answer
    return read(answer, wants)
