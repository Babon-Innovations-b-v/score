"""The finish route's recheck row (paid: one Gemini 3.1 Pro answer a take, all the place's takes in one batch at half
price, route_ask.py). One recheck, a batch (CONTEXT.md, owner 2026-10-20, #18 and #21): it only sorts each take into
passed or a named fault, with no tweak and no ask again.

First, free, the colour check: a take one of whose finishes the parts row's check left off its colour (no library
surface lies within finish_parts.COLOUR_DELTA_E of its texture's colour, or the close-up's lightness order cannot be
kept) is a gap with no ask. The rest are drawn from every view the views row cast, each part flat in its library
surface's colour (in the list's token where the part carries its settings), shaded by angle, and asked once: Gemini, shown the close-up (its own, or the stand-in, said so) and
the drawings, says per finish whether its library surface matches what the close-up shows for those parts. All
match: passed. Else the take fails the gate "library surface fits" by name, "no library surface fits", a gap of its
object (gate:finish-route-recheck/library surface fits:<take>); Gemini's token, roughness and metal for a failing
finish are kept as the gap's `suggested` and never applied: trying them is a new batch. A take the batch gives no
usable answer is a gap the same way.

Output per take: <take>/checked-<view>.png; recheck.json per take: the colour faults, `asked`, Gemini's answers,
`passed`, `fault`, `suggested`.
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
import route_ask  # noqa: E402
import route_cast as cast  # noqa: E402
import route_data  # noqa: E402
import route_list  # noqa: E402
import route_split  # noqa: E402
import surface_gates as gates  # noqa: E402

RECHECK_EUROS = 1.0  # a guess for the row's run (a place's takes at half of google_spend.ESTIMATES); never a price
CALLER = "finish-route-recheck"
QUESTION = """You check a painted 3D model of an object against its close-up. The object: {object}.
The first picture is {close_up}. The next {count} pictures show the model from every side ({views}), each part
drawn flat in its library surface's colour, shaded only by angle: no shine, wear or pattern is drawn, so judge
roughness and metal from the words below, colour from the pictures. Its finishes:
{finishes}
For each finish say whether its surface matches what the close-up shows for those parts. Where one does not, say
why, and give the palette token, roughness and metal that would match; the palette tokens:
{tokens}"""


def finish_lines(finishes, surfaces):
    """Each finish as a line: its number, words, parts, library surface and family, colour in words and shine."""
    import part_judge
    lines = []
    for number, entry in enumerate(finishes):
        spec = surfaces.get(entry["surface"], {})
        colour = part_judge.colour_words(spec["colour"]) if "colour" in spec else "its own colour"
        lines.append(f"- finish {number + 1}: {entry['finish']}, on {entry['parts']}; surface {entry['surface']} "
                     f"({spec.get('family')}), drawn {colour}, roughness {spec.get('roughness', 0.5):.2f}, metal "
                     f"{spec.get('metal', 0.0):.2f}")
    return "\n".join(lines)


def recheck_body(pictures, entry, finishes, context):
    """The request: the close-up, the drawn views, the question, and a schema of one answer a finish."""
    text = QUESTION.format(object=entry["object"], close_up=(f"a {route_data.STAND_IN}" if context["stand_in"]
                                                             else "the object's close-up"),
                           count=len(pictures["views"]), views=", ".join(pictures["views"]),
                           finishes=finish_lines(finishes, context["surfaces"]),
                           tokens=route_list.token_lines(context["tokens"]))
    answer = {"type": "OBJECT",
              "properties": {"finish": {"type": "INTEGER"}, "matches": {"type": "BOOLEAN"}, "why": {"type": "STRING"},
                             "token": {"type": "STRING", "enum": list(context["tokens"])},
                             "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"}},
              "required": ["finish", "matches", "why"]}
    schema = {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": answer}}, "required": ["finishes"]}
    parts = [finish_ask.picture_part(pictures["close_up"], 1024),
             *(finish_ask.picture_part(picture, 512) for picture in pictures["drawn"])]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema}}


def ask(bodies):
    """The one batch of the row's asks: {take: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def answers_of(text):
    """The answer's verdicts by finish (0-based); a reply that does not parse raises."""
    return {int(entry["finish"]) - 1: entry for entry in json.loads(text)["finishes"]}


def colour_faults(finishes):
    """The finishes the free colour check left off their colour, with why."""
    return [f"{entry['finish']}: dE {entry.get('delta_e')} from {entry['surface']}" for entry in finishes
            if entry.get("by") == "off its colour"]


def token_colour(token):
    """A palette token's colour, sRGB 0-255 (finish_parts.surface_colours' way)."""
    import labels
    import library
    return np.clip(labels.srgb(np.array(library.token_colours()[token], dtype=float)) * 255, 0, 255).astype(np.uint8)


def drawn(folders, entry, record):
    """Each view of the take drawn flat in its parts' library surface colours (a part with the list's settings in
    its token's: the colour the bake gives it, route_settings) into folders["out"]
    (checked-<view>.png); the pictures by view."""
    from PIL import Image
    mesh = route_split.model_of(folders["views"])
    part_of = np.load(folders["parts"] / "parts.npy").astype(int)
    colours = finish_parts.surface_colours(entry, {row["judge"] for row in record["parts"]})
    by_face = np.array([token_colour(row["settings"]["token"]) if row.get("settings") else colours[row["judge"]]
                        for row in record["parts"]], dtype=np.uint8)[part_of]
    angles = json.loads((folders["views"].parent / "views.json").read_text())[folders["views"].name]["views"]
    faces = np.load(folders["views"] / "faces.npz")
    folders["out"].mkdir(parents=True)
    for view in faces.files:
        cast.picture(cast.face_painted(by_face, faces[view]), faces[view],
                     cast.shading(mesh, faces[view], angles[view])).save(folders["out"] / f"checked-{view}.png")
    return {"views": list(faces.files), "close_up": Image.open(folders["views"] / "close-up.png"),
            "drawn": [Image.open(folders["out"] / f"checked-{view}.png") for view in faces.files]}


def failed(finishes, answers):
    """The finishes (0-based) Gemini did not say match."""
    return [number for number in range(len(finishes)) if not answers.get(number, {}).get("matches", False)]


def suggested(finishes, answers, wrong):
    """Gemini's settings for each failing finish, kept for a later batch, never applied: {finish words: settings}."""
    found = {}
    for index in wrong:
        answer = answers.get(index, {})
        settings = {name: answer[name] for name in ("token", "roughness", "metal") if answer.get(name) is not None}
        if settings:
            found[finishes[index]["finish"]] = settings
    return found


def sorted_answer(finishes, text):
    """The one ask's answer sorted: passed, or the fault naming each failing finish, with Gemini's suggestions; a reply
    that does not parse is a fault the same way."""
    try:
        answers = answers_of(text)
    except route_ask.UNANSWERED as error:
        return {"passed": False, "fault": f"no usable answer: {error!r}"[:300], "suggested": {}, "gemini": {}}
    wrong = failed(finishes, answers)
    gemini = {str(key + 1): value for key, value in answers.items()}
    if not wrong:
        return {"passed": True, "fault": None, "suggested": {}, "gemini": gemini}
    fault = "; ".join(f"{finishes[index]['finish']}: {answers.get(index, {}).get('why', 'no answer')}" for index in wrong)
    return {"passed": False, "fault": fault, "suggested": suggested(finishes, answers, wrong), "gemini": gemini}


def make_recheck(inputs, out, seed, params):
    """Every take of the parts checked free, the rest drawn and asked in one batch; recheck.json."""
    views, parts = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["surfaces-parts"])
    _, takes = route_data.takes_written(out, inputs, params)
    cast_takes = json.loads((views / "views.json").read_text())
    tokens = route_list.library_tokens()
    found, bodies = {}, {}
    records = json.loads((parts / "parts.json").read_text())["takes"]
    for take, record in records.items():
        faults = colour_faults(record["finishes"])
        if faults:
            found[take] = {"colour_faults": faults, "asked": False, "passed": False, "suggested": {}, "gemini": {},
                           "fault": "the free colour check, not asked: " + "; ".join(faults)}
            continue
        pictures = drawn({"views": views / take, "parts": parts / take, "out": out / take}, takes[take], record)
        context = {"surfaces": finish_parts.take_surfaces(takes[take]), "tokens": tokens,
                   "stand_in": cast_takes[take].get("close_up") == route_data.STAND_IN}
        bodies[take] = recheck_body(pictures, takes[take], record["finishes"], context)
    answers = ask(bodies) if bodies else {}
    for take in bodies:
        answer = answers.get(take, finish_ask.NoAnswer("the batch gave no answer"))
        sorted_found = ({"passed": False, "fault": f"no usable answer: {answer!r}"[:300], "suggested": {},
                         "gemini": {}} if isinstance(answer, Exception) else
                        sorted_answer(records[take]["finishes"], answer))
        found[take] = {"colour_faults": [], "asked": True, **sorted_found}
    (out / "recheck.json").write_text(json.dumps(found, indent=1))


def recheck_faults(folder):
    return [] if (folder / "recheck.json").exists() else ["no recheck.json"]


def judge_recheck(output, inputs, evidence):
    """Every take of the parts passed its one recheck; one that did not, or was not asked, is named: no library
    surface fits. Checked against a stand-in close-up, the pass says so."""
    found = json.loads((output / "recheck.json").read_text())
    failing = [f"{take}: no library surface fits ({record['fault']})" for take, record in found.items()
               if not record["passed"]]
    cast_takes = json.loads((pathlib.Path(inputs["finish-route-views"]) / "views.json").read_text())
    stand_ins = sum(cast_takes.get(take, {}).get("close_up") == route_data.STAND_IN for take in found)
    asked = sum(record["asked"] for record in found.values())
    return gates.verdict("library surface fits", failing, len(found), "takes with no library surface that fits",
                         {"stand_in_close_ups": stand_ins, "asked": asked})
