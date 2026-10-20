"""The finish route's list row (paid: one Gemini 3.1 Pro ask a take, through finish_ask.generated and google_spend:
the key `gemini-api-key` by name, every call priced on the Google ledger, an ask asked before read back free).

Gemini sees the take's close-up (its own, or the stand-in, said so in the question), every view of the model's own
texture and the same views split into the split row's colour groups, and lists the take's finishes. Each finish is
matched FIRST to a surface of the library with its settings: the palette token of its colour (one the library's
variants or the places use), its shine (roughness, metal) and its seed (the node's, one a finish); its wear is the
place's one level (the room's wear rule, owner): a finish that looks more or less worn says so in `wear_wish`, an
owner question, never a setting. A new surface is proposed only when no surface fits with any settings (`fits`
false). Each group belongs to one finish; a group the answer leaves out takes the finish of the named group
nearest it in colour, recorded as such.

Output: <take>.json per take (its finishes, each with groups, surface, settings, fits, new_surface, wear_wish),
questions.json (the wear wishes, for the owner). Gate "library first": every split take is listed, every finish
names a library surface with settings inside the library's ranges, and one that does not fit proposes a surface.
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
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402

LIST_EUROS = 0.5  # a guess for the row's run (google_spend.ESTIMATES: EUR 0.05 an ask, a place's takes); never a price
QUESTION = """You help paint a 3D model with surfaces from a shared library. The object: {object}.
The first picture is {close_up}. The next {count} pictures show the model from every side ({views}) in its own
texture, shaded only by angle. The {count} after them show the same views with the model split into colour groups,
each group one flat colour:
{groups}
List the object's finishes: the distinct surface treatments a painter would give its parts. List a finish only when
it truly differs in material or paint from the others; dirt, wear, scratches, light and shadow are not finishes.
For each finish give its parts in words, the colour groups it covers (every group belongs to exactly one finish),
and FIRST the library surface it is, with its settings: the palette token nearest its colour, and its roughness
and metal from 0 to 1 (the surface's own unless the pictures clearly show otherwise). The library's surfaces, each
with its own token, roughness and metal:
{surfaces}
The palette tokens:
{tokens}
Choose by what the part is and how such a part is made, then by its colour. Only when no library surface fits with
any settings, set "fits" to false and propose a new library surface. Wear is the place's one level ({wear}); only if
a finish clearly looks more or less worn than that, say how in "wear_wish", else leave it empty."""


def library_tokens():
    """{token: linear RGB} of the palette tokens the library's variants and the places use."""
    import library
    every = library.token_colours()
    used = {variant["token"] for variant in library.variants(library.theme_library()).values()}
    places = json.loads(library.PLACES.read_text())
    used |= {entry["token"] for place in places.values() for entry in place.get("materials", {}).values()
             if isinstance(entry, dict) and "token" in entry}
    return {token: every[token] for token in sorted(used) if token in every}


def surface_lines(surfaces):
    """Each surface as a line: its code, part_judge's words for it, its token, roughness and metal."""
    import part_judge
    words = part_judge.material_lines(surfaces).splitlines()
    return "\n".join(f"{line}; token {spec.get('token')}, roughness {spec.get('roughness', 0.5):.2f}, metal "
                     f"{spec.get('metal', 0.0):.2f}" for line, spec in zip(words, surfaces.values()))


def token_lines(tokens):
    import part_judge
    return "\n".join(f"- {token}: {part_judge.colour_words(colour)}" for token, colour in tokens.items())


def group_lines(groups):
    return "\n".join(f"- group {entry['group'] + 1}: {finish_ask.LABEL_WORDS[entry['group']]}, "
                     f"{entry['share']:.0%} of the model, its texture there about RGB {entry['srgb']}"
                     for entry in groups)


def list_body(pictures, entry, groups, surfaces, tokens, wear, stand_in):
    """The request: the close-up, the views, the group views, the question and a schema whose surface is one of the
    surfaces' codes and whose token one of the tokens."""
    close_up = (f"a {route_data.STAND_IN}" if stand_in else "the object's close-up")
    text = QUESTION.format(object=entry["object"], close_up=close_up, count=len(pictures["views"]),
                           views=", ".join(pictures["views"]), groups=group_lines(groups),
                           surfaces=surface_lines(surfaces), tokens=token_lines(tokens), wear=wear)
    proposal = {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "description": {"type": "STRING"},
                                                 "why": {"type": "STRING"}}, "required": ["name", "description", "why"]}
    finish = {"type": "OBJECT",
              "properties": {"parts": {"type": "STRING"}, "finish": {"type": "STRING"},
                             "groups": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                             "surface": {"type": "STRING", "enum": finish_ask.surface_codes(surfaces)},
                             "token": {"type": "STRING", "enum": list(tokens)},
                             "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"},
                             "fits": {"type": "BOOLEAN"}, "new_surface": proposal, "wear_wish": {"type": "STRING"}},
              "required": ["parts", "finish", "groups", "surface", "token", "roughness", "metal", "fits"],
              "propertyOrdering": ["parts", "finish", "groups", "surface", "token", "roughness", "metal", "fits",
                                   "new_surface", "wear_wish"]}
    schema = {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": finish}}, "required": ["finishes"]}
    parts = [finish_ask.picture_part(pictures["close_up"], 1024)]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["shaded"]]
    parts += [finish_ask.picture_part(picture, 512) for picture in pictures["groups"]]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema}}


def finishes_of(answer, surfaces, seed):
    """The answer's finishes: each surface by its library name, its settings clipped to 0-1 with the node's seed
    (one a finish); their groups still to be given (grouped)."""
    names, codes = list(surfaces), finish_ask.surface_codes(surfaces)
    found = []
    for number, entry in enumerate(answer["finishes"]):
        settings = {"token": entry["token"], "roughness": round(float(np.clip(entry["roughness"], 0, 1)), 3),
                    "metal": round(float(np.clip(entry["metal"], 0, 1)), 3), "seed": int(seed) + number}
        found.append({"finish": entry["finish"], "parts": entry["parts"], "surface": names[codes.index(entry["surface"])],
                      "settings": settings, "fits": bool(entry["fits"]), "new_surface": entry.get("new_surface"),
                      "wear_wish": (entry.get("wear_wish") or "").strip() or None, "groups": [], "by": "the list"})
    if not found:
        raise ValueError("the finish list is empty")
    return found


def grouped(found, answer, groups):
    """`found` with each group (0-based) in the first finish the answer names it in; a group it leaves out goes to
    the finish of the named group nearest it in colour, said in that finish's `by`."""
    owner = {}
    for number, entry in enumerate(answer["finishes"]):
        for group in entry["groups"]:
            if 0 < int(group) <= len(groups):
                owner.setdefault(int(group) - 1, number)
    named = list(owner)
    for group in range(len(groups)):
        if group not in owner and named:
            nearest = min(named, key=lambda other: np.linalg.norm(np.subtract(groups[other]["lab"],
                                                                             groups[group]["lab"])))
            owner[group] = owner[nearest]
            found[owner[group]]["by"] = "the list, a group it left out joined by colour"
    for group, number in sorted(owner.items()):
        found[number]["groups"].append(group)
    return found


def pictures_of(views, split, take):
    from PIL import Image
    import route_cast as cast
    return {"views": list(cast.VIEWS), "close_up": Image.open(views / take / "close-up.png"),
            "shaded": [Image.open(views / take / f"{view}.png") for view in cast.VIEWS],
            "groups": [Image.open(split / take / f"groups-{view}.png") for view in cast.VIEWS]}


def ask(body):
    """One cleared, ledgered Gemini 3.1 Pro ask (finish_ask.generated: asked again on a dropped connection)."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish list (finish route)")
    response = finish_ask.generated(finish_ask.LIST_MODEL, body, finish_ask.secret_key(), finish_ask.TIMEOUT,
                                    caller="finish-route-list", cache=True)
    return finish_ask.reply_text(response)


def make_list(inputs, out, seed, params):
    """Every split take's finish list, and the owner's questions."""
    import library
    views, split = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-split"])
    place, _ = route_data.takes(inputs, params)
    takes = route_data.takes_written(out, inputs, params)
    grouped = json.loads((split / "groups.json").read_text())
    stand_ins = json.loads((views / "views.json").read_text())
    tokens = library_tokens()
    wear = json.loads(library.PLACES.read_text())[place]["wear"]["level"]
    questions = []
    for take, record in grouped.items():
        surfaces = finish_parts.take_surfaces(takes[take])
        stand_in = stand_ins[take].get("close_up") == route_data.STAND_IN
        body = list_body(pictures_of(views, split, take), takes[take], record["groups"], surfaces, tokens, wear,
                         stand_in)
        answer = json.loads(ask(body))
        finishes = grouped(finishes_of(answer, surfaces, seed), answer, record["groups"])
        (out / f"{take}.json").write_text(json.dumps({"take": take, "wear": wear, "finishes": finishes}, indent=1))
        questions += [f"{take}: {entry['finish']}: {entry['wear_wish']} (the place's wear is {wear})"
                      for entry in finishes if entry["wear_wish"]]
    (out / "questions.json").write_text(json.dumps({"wear_wishes": questions}, indent=1))


def list_faults(folder):
    return [] if (folder / "questions.json").exists() else ["no questions.json"]


def judge_list(output, inputs, evidence):
    """Every split take listed; every finish a library surface with a library token and settings 0-1, each group in
    one finish; a finish that does not fit proposes a surface. The owner's wear questions as a measure."""
    grouped = json.loads((pathlib.Path(inputs["finish-route-split"]) / "groups.json").read_text())
    tokens = library_tokens()
    failing = []
    for take, record in grouped.items():
        if not (output / f"{take}.json").exists():
            failing.append(f"{take}: no finish list")
            continue
        finishes = json.loads((output / f"{take}.json").read_text())["finishes"]
        covered = sorted(group for entry in finishes for group in entry["groups"])
        if covered != list(range(len(record["groups"]))):
            failing.append(f"{take}: groups not one finish each ({covered})")
        failing += [f"{take}: {entry['finish']}: token {entry['settings']['token']} is not the library's"
                    for entry in finishes if entry["settings"]["token"] not in tokens]
        failing += [f"{take}: {entry['finish']}: does not fit and proposes no surface"
                    for entry in finishes if not entry["fits"] and not entry.get("new_surface")]
    asked = json.loads((output / "questions.json").read_text())["wear_wishes"]
    return gates.verdict("library first", failing, len(grouped), "takes off the library",
                         {"wear_questions": len(asked)})
