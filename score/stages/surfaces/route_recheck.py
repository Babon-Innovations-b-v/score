"""The finish route's recheck row (paid: up to TRIES Gemini 3.1 Pro asks a take, cleared and priced on the Google
ledger as the list row's, an ask asked before read back free).

Each try checks the filled model two ways: the free colour check (route_fill: each finish's token against its seen
colour) and Gemini, shown the close-up (its own, or the stand-in, said so) and the filled views, saying per finish
whether its library surface and settings match what the close-up shows (the drawings are flat colour: shine is
judged from the words). Both pass: done. Else the settings of each finish that failed are tweaked (Gemini's token,
roughness and metal where it gave them, else the library token nearest the finish's seen colour), the model is
filled and drawn again and checked again, at most TRIES tries; a tweak is this row's output, never a library edit.
A take still failing after its last try, or whose tweak changes nothing, fails the gate "library surface fits" by
name: "no library surface fits", a hole of its object (gate:finish-route-recheck/library surface fits:<take>).

Output per take: <take>/try-<n>-<view>.png; recheck.json per take: each try's colour faults and Gemini's answers,
`passed`, and the finishes with their final settings.
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
import route_data  # noqa: E402
import route_fill  # noqa: E402
import route_list  # noqa: E402
import surface_gates as gates  # noqa: E402

TRIES = 3
RECHECK_EUROS = 1.0  # a guess for the row's run (up to TRIES asks a take at google_spend's EUR 0.05); never a price
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
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema}}


def ask(body):
    """One cleared, ledgered Gemini 3.1 Pro ask; its answers by finish (0-based)."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish recheck (finish route)")
    response = finish_ask.generated(finish_ask.LIST_MODEL, body, finish_ask.secret_key(), finish_ask.TIMEOUT,
                                    caller="finish-route-recheck", cache=True)
    return {int(entry["finish"]) - 1: entry for entry in json.loads(finish_ask.reply_text(response))["finishes"]}


def nearest_token(seen_lab, tokens):
    """The library token whose colour lies nearest a seen CIELAB colour (CIE76)."""
    import labels
    return min(tokens, key=lambda token: float(np.linalg.norm(
        labels.lab(labels.srgb(np.asarray(tokens[token], dtype=float))[None])[0] - np.asarray(seen_lab))))


def failed(finishes, answers):
    """The finishes (0-based) the colour check or Gemini failed."""
    return [number for number, entry in enumerate(finishes)
            if not entry["colour_fits"] or not answers.get(number, {}).get("matches", False)]


def tweaked(entry, answer, tokens):
    """One failing finish's next settings: Gemini's token, roughness and metal where it gave them (a token in the
    library's), else the token nearest its seen colour."""
    settings = dict(entry["settings"])
    if answer.get("token") in tokens:
        settings["token"] = answer["token"]
    elif entry.get("seen_lab") is not None:
        settings["token"] = nearest_token(entry["seen_lab"], tokens)
    for name in ("roughness", "metal"):
        if answer.get(name) is not None:
            settings[name] = round(float(np.clip(answer[name], 0, 1)), 3)
    return {key: value for key, value in entry.items() if key not in ("srgb", "filled_lab", "seen_lab", "delta_e",
                                                                       "own_colour", "colour_fits")} | {
        "settings": settings}


def try_record(number, finishes, answers):
    return {"try": number, "settings": [entry["settings"] for entry in finishes],
            "colour_faults": [f"{entry['finish']}: dE {entry['delta_e']}" for entry in finishes
                              if not entry["colour_fits"]],
            "gemini": {str(key + 1): value for key, value in answers.items()}}


def recheck_take(folders, entry, finishes, context):
    """One take checked and tweaked up to TRIES times: its record (tries, passed, finishes, fault)."""
    from PIL import Image
    finish_of = np.load(folders["fill"] / "finish.npy").astype(int)
    close_up = Image.open(folders["views"] / "close-up.png")
    tries = []
    for number in range(1, TRIES + 1):
        route_fill.drawn(folders["views"], finish_of, finishes, folders["out"], f"try-{number}")
        pictures = [Image.open(folders["out"] / f"try-{number}-{view}.png") for view in cast.VIEWS]
        answers = ask(recheck_body(close_up, pictures, entry, finishes, context["surfaces"], context["tokens"],
                                   context["stand_in"]))
        tries.append(try_record(number, finishes, answers))
        wrong = failed(finishes, answers)
        if not wrong:
            return {"tries": tries, "passed": True, "finishes": finishes, "fault": None}
        fault = "; ".join(f"{finishes[index]['finish']}: dE {finishes[index]['delta_e']}, Gemini: "
                          f"{answers.get(index, {}).get('why', 'no answer')}" for index in wrong)
        nudged = [tweaked(found, answers.get(index, {}), context["tokens"]) if index in wrong else found
                  for index, found in enumerate(finishes)]
        if [found["settings"] for found in nudged] == [found["settings"] for found in finishes]:
            return {"tries": tries, "passed": False, "finishes": finishes, "fault": f"{fault} (no tweak left)"}
        finishes = route_fill.filled(folders["views"], finish_of, nudged, context["families"])
    return {"tries": tries, "passed": False, "finishes": finishes, "fault": fault}


def make_recheck(inputs, out, seed, params):
    """Every filled take rechecked; recheck.json."""
    views, fill = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-fill"])
    takes = route_data.takes_written(out, inputs, params)
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
    """Every filled take passed its recheck within TRIES tries; one that did not is named: no library surface fits.
    Checked against a stand-in close-up, the pass says so."""
    found = json.loads((output / "recheck.json").read_text())
    failing = [f"{take}: no library surface fits ({record['fault']})" for take, record in found.items()
               if not record["passed"]]
    cast_takes = json.loads((pathlib.Path(inputs["finish-route-views"]) / "views.json").read_text())
    stand_ins = sum(cast_takes.get(take, {}).get("close_up") == route_data.STAND_IN for take in found)
    tries = sum(len(record["tries"]) for record in found.values())
    return gates.verdict("library surface fits", failing, len(found), "takes with no library surface that fits",
                         {"stand_in_close_ups": stand_ins, "tries": tries})
