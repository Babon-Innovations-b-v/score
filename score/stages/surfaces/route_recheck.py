"""The finish route's recheck row (paid: one Gemini 3.1 Pro ask a take on the flex tier, cleared and priced on the
Google ledger as the list row's, an ask asked before read back free). A batch (CONTEXT.md, owner 2026-10-20, #21):
each take is asked once; the check only sorts its answer into pass or a named fault.

Before the ask, free, the prediction (`predicted`): each finish the fill's colour check fails (route_fill: its token
against its seen colour, CIE76 within finish_parts.COLOUR_DELTA_E) takes the library token nearest its seen colour,
and the model is filled again. A take one of whose finishes still fails the colour check is a hole with no ask: the
gate fails it whatever Gemini would say. The rest are drawn once and asked once: Gemini, shown the close-up (its own,
or the stand-in, said so) and the filled views, says per finish whether its library surface and settings match what
the close-up shows (the drawings are flat colour: shine is judged from the words). All match: passed. Else the take
fails the gate "library surface fits" by name, "no library surface fits", a hole of its object
(gate:finish-route-recheck/library surface fits:<take>); Gemini's token, roughness and metal for a failing finish
are kept as the hole's `suggested` settings and never applied: trying them is a new batch and a new ask. An ask
with no usable answer (a timeout, a dropped connection, a reply that does not parse) is a hole the same way, never
asked again. Settings are this row's output, never a library edit.

Output per take: <take>/checked-<view>.png; recheck.json per take: the tokens the prediction changed, the colour
faults, `asked`, Gemini's answers, `passed`, `fault`, `suggested`, and the finishes with their checked settings.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_ask  # noqa: E402
import finish_parts  # noqa: E402
import route_cast as cast  # noqa: E402
import route_cap  # noqa: E402
import route_data  # noqa: E402
import route_fill  # noqa: E402
import route_list  # noqa: E402
import surface_gates as gates  # noqa: E402

RECHECK_EUROS = 1.0  # a guess for the row's run (one ask a take at google_spend's EUR 0.05); never a price
UNANSWERED = (OSError, ValueError, KeyError)  # a timeout, a dropped connection, a reply that does not parse
QUESTION = """You check a painted 3D model of an object against its close-up. The object: {object}.
The first picture is {close_up}. The next {count} pictures show the model from every side ({views}), each part
drawn flat in its library surface's colour, shaded only by angle: no shine, wear or pattern is drawn, so judge
roughness and metal from the words below, colour from the pictures. Its finishes:
{finishes}
For each finish say whether its surface and settings match what the close-up shows for those parts. Where one does
not, say why, and give the palette token, roughness and metal that would match; the palette tokens:
{tokens}"""


def finish_lines(finishes, surfaces, tokens):
    """Each finish as a line: its number, words, parts, surface and family, drawn colour in words and shine."""
    import part_judge
    return "\n".join(f"- finish {number + 1}: {entry['finish']}, on {entry['parts']}; surface "
                     f"{entry['surface']} ({surfaces.get(entry['surface'], {}).get('family')}), drawn "
                     f"{part_judge.colour_words(tokens[entry['settings']['token']])}, "
                     f"roughness {entry['settings']['roughness']:.2f}, metal {entry['settings']['metal']:.2f}"
                     for number, entry in enumerate(finishes))


def recheck_body(close_up, pictures, entry, finishes, surfaces, tokens, stand_in):
    """The request: the close-up, the filled views, the question, and a schema of one answer a finish."""
    text = QUESTION.format(object=entry["object"], close_up=(f"a {route_data.STAND_IN}" if stand_in
                                                             else "the object's close-up"),
                           count=len(pictures), views=", ".join(cast.VIEWS),
                           finishes=finish_lines(finishes, surfaces, tokens), tokens=route_list.token_lines(tokens))
    answer = {"type": "OBJECT",
              "properties": {"finish": {"type": "INTEGER"}, "matches": {"type": "BOOLEAN"}, "why": {"type": "STRING"},
                             "token": {"type": "STRING", "enum": list(tokens)}, "roughness": {"type": "NUMBER"},
                             "metal": {"type": "NUMBER"}},
              "required": ["finish", "matches", "why"]}
    schema = {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": answer}}, "required": ["finishes"]}
    parts = [finish_ask.picture_part(close_up, 1024), *(finish_ask.picture_part(picture, 512) for picture in pictures)]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema},
            "serviceTier": finish_ask.LIST_TIER}


def ask(body):
    """One cleared, ledgered Gemini 3.1 Pro ask; its answers by finish (0-based)."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish recheck (finish route)")
    route_cap.require_room(finish_ask.LIST_MODEL, body)
    response = finish_ask.generated(finish_ask.LIST_MODEL, body, finish_ask.secret_key(), finish_ask.FLEX_TIMEOUT,
                                    caller="finish-route-recheck", cache=True)
    return {int(entry["finish"]) - 1: entry for entry in json.loads(finish_ask.reply_text(response))["finishes"]}


def nearest_token(seen_lab, tokens):
    """The library token whose colour, as the fill draws it (route_fill.token_srgb), lies nearest a seen CIELAB
    colour (CIE76)."""
    return min(tokens, key=lambda token: float(np.linalg.norm(
        cast.lab_of(route_fill.token_srgb(token)[None])[0] - np.asarray(seen_lab))))


def failed(finishes, answers):
    """The finishes (0-based) the colour check or Gemini failed."""
    return [number for number, entry in enumerate(finishes)
            if not entry["colour_fits"] or not answers.get(number, {}).get("matches", False)]


def colour_faults(finishes):
    return [f"{entry['finish']}: dE {entry['delta_e']}" for entry in finishes if not entry["colour_fits"]]


def unchecked(entry):
    """A finish without its colour check's fields, ready to be filled again."""
    return {key: value for key, value in entry.items()
            if key not in ("srgb", "filled_lab", "seen_lab", "delta_e", "own_colour", "colour_fits")}


def predicted(views, finish_of, finishes, context):
    """The free prediction before the ask: each finish the colour check fails takes the library token nearest its
    seen colour, and the model is filled again. The finishes with their new colour check, and the tokens it changed
    ({finish words: [old, new]})."""
    changed, settled = {}, []
    for entry in finishes:
        settings = dict(entry["settings"])
        if not entry["colour_fits"] and entry.get("seen_lab") is not None:
            settings["token"] = nearest_token(entry["seen_lab"], context["tokens"])
        if settings["token"] != entry["settings"]["token"]:
            changed[entry["finish"]] = [entry["settings"]["token"], settings["token"]]
        settled.append(unchecked(entry) | {"settings": settings})
    return route_fill.filled(views, finish_of, settled, context["families"]), changed


def suggested(finishes, answers, wrong):
    """Gemini's settings for each failing finish, kept for a later batch, never applied: {finish words: settings}."""
    found = {}
    for index in wrong:
        answer = answers.get(index, {})
        settings = {name: answer[name] for name in ("token", "roughness", "metal") if answer.get(name) is not None}
        if settings:
            found[finishes[index]["finish"]] = settings
    return found


def sorted_answer(finishes, answers):
    """The one ask's answer sorted: passed, or the fault naming each failing finish, with Gemini's suggestions."""
    wrong = failed(finishes, answers)
    if not wrong:
        return {"passed": True, "fault": None, "suggested": {}}
    fault = "; ".join(f"{finishes[index]['finish']}: dE {finishes[index]['delta_e']}, Gemini: "
                      f"{answers.get(index, {}).get('why', 'no answer')}" for index in wrong)
    return {"passed": False, "fault": fault, "suggested": suggested(finishes, answers, wrong)}


def recheck_take(folders, entry, finishes, context):
    """One take predicted free, then drawn and asked once: its record (changed, colour_faults, asked, gemini,
    passed, fault, suggested, finishes)."""
    from PIL import Image
    finish_of = np.load(folders["fill"] / "finish.npy").astype(int)
    finishes, changed = predicted(folders["views"], finish_of, finishes, context)
    record = {"changed": changed, "colour_faults": colour_faults(finishes), "finishes": finishes, "gemini": {},
              "suggested": {}, "passed": False}
    if record["colour_faults"]:
        return record | {"asked": False, "fault": "predicted, not asked: no library token within the colour check: "
                                                  + "; ".join(record["colour_faults"])}
    route_fill.drawn(folders["views"], finish_of, finishes, folders["out"], "checked")
    pictures = [Image.open(folders["out"] / f"checked-{view}.png") for view in cast.VIEWS]
    close_up = Image.open(folders["views"] / "close-up.png")
    try:
        answers = ask(recheck_body(close_up, pictures, entry, finishes, context["surfaces"], context["tokens"],
                                   context["stand_in"]))
    except UNANSWERED as error:
        return record | {"asked": True, "fault": f"no usable answer: {error!r}"[:300]}
    return record | {"asked": True, "gemini": {str(key + 1): value for key, value in answers.items()},
                     **sorted_answer(finishes, answers)}


def make_recheck(inputs, out, seed, params):
    """Every filled take rechecked; recheck.json."""
    route_cap.require_filtered(params, "finish-route-recheck")
    views, fill = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-fill"])
    _, takes = route_data.takes_written(out, inputs, params)
    cast_takes = json.loads((views / "views.json").read_text())
    tokens = route_list.library_tokens()
    found = {}
    for take, finishes in json.loads((fill / "fill.json").read_text()).items():
        surfaces = finish_parts.take_surfaces(takes[take])
        context = {"surfaces": surfaces, "tokens": tokens,
                   "families": {name: spec.get("family") for name, spec in surfaces.items()},
                   "stand_in": cast_takes[take].get("close_up") == route_data.STAND_IN}
        (out / take).mkdir(parents=True)
        found[take] = recheck_take({"views": views / take, "fill": fill / take, "out": out / take}, takes[take],
                                   finishes, context)
    (out / "recheck.json").write_text(json.dumps(found, indent=1))


def recheck_faults(folder):
    return [] if (folder / "recheck.json").exists() else ["no recheck.json"]


def judge_recheck(output, inputs, evidence):
    """Every filled take passed its one recheck; one that did not, or was not asked, is named: no library surface
    fits. Checked against a stand-in close-up, the pass says so."""
    found = json.loads((output / "recheck.json").read_text())
    failing = [f"{take}: no library surface fits ({record['fault']})" for take, record in found.items()
               if not record["passed"]]
    cast_takes = json.loads((pathlib.Path(inputs["finish-route-views"]) / "views.json").read_text())
    stand_ins = sum(cast_takes.get(take, {}).get("close_up") == route_data.STAND_IN for take in found)
    asked = sum(record["asked"] for record in found.values())
    return gates.verdict("library surface fits", failing, len(found), "takes with no library surface that fits",
                         {"stand_in_close_ups": stand_ins, "asked": asked})
