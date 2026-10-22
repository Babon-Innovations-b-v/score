"""The bodies' faces, one paid row a body, `body-face-<body>` (an environment node each: one Gemini 3.1 Pro answer
through the Batch API, route_ask.py). score_lib withdrew every old surface on 2026-10-21, so nothing made the face a
planet or moon shows in a sky or a film any more (surface-library makes a scene's own surfaces only). Each body of
the environment concept's setting that does not shine (a shining one is drawn by its light) gets its face made here,
fresh, by the material method the scene surfaces are made with (scene_library.py: one ProcFunc recipe variant in
palette tokens, data/library/materials.json), from the environment concept alone: its style line and the body's own
physics (a real body's values from the cited reference table, data/physics/bodies.json, through setting.checked).

The body list and each row's inputs are the locked environment concept's (`concept`: the version in force, else
today's data while none is kept), so a body added to the setting is a row of its own and a changed style line or body
re-asks only its rows (`params`, worked out from the runner's store when the node is keyed).

Output: face.json {body, surface (`<body>_face`), family, recipe, token, hex, colour (linear RGB), roughness, metal,
palette}, what the sky (score/stages/light/sky.py, the light layer reading each accepted face) and the films (the
cockpit state's `body_faces`, score/dashboard/films/preview/scenes.py) draw, never a library name; and
materials.json, the face as a surface library in the loader's form (tools/props/library/library.py). Or
unanswered.json with why. Gate "face from the design": a face named `<body>_face`, its recipe the method's, every
token its palette's, every setting 0 to 1, every colour setting its recipe needs given.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

from score import contracts, graph  # noqa: E402
from score.review import environment_concept, setting as settings  # noqa: E402

import finish_ask  # noqa: E402
import route_ask  # noqa: E402
import scene_library  # noqa: E402
import scene_palette  # noqa: E402
import surface_gates as gates  # noqa: E402

PREFIX = "body-face-"
CALLER = "body-face"
# A guess for one body's ask, never a price: surface-library's one measured run (google ledger call
# 507bf0dfcea54d6b9723bcfe9d29a167, surface-library, 2026-10-22, standard tier: EUR 0.08087), the same method's ask
# with no picture, so at most that.
FACE_EUROS = 0.081
QUESTION = """You make the face of one body of a 3D environment's setting: the one surface its whole ball is painted
with where it hangs in a sky or turns in a film, drawn by the environment's own material method, in the environment's
style: {style}
The body: {name}, {facts}.
First its palette: the colours its face shows from afar, as the body truly looks in that style, each a short token in
lower case and hyphens with its colour as #rrggbb. Then its face: one surface, a variant of one recipe below, in one
token of its palette, its family (one word for what the face is made of), its roughness and metal from 0 to 1, and a
token of the palette for each colour setting its recipe needs.
The recipes (name: default settings; colour settings it needs):
{recipes}"""
FACTS = (("radius_km", "radius {:,.0f} km"), ("gravity", "surface gravity {:.2f} m/s2"),
         ("surface_pressure_kpa", "surface pressure {:.3g} kPa"), ("around", "orbiting {}"),
         ("distance_km", "{:,.0f} km from it"), ("day_hours", "a day of {:.1f} hours"), ("locked_to", "facing {}"))


def concept(store):
    """{style, setting} of the environment concept in force: the locked version, else today's data."""
    return environment_concept.in_force(store) or {"style": environment_concept.style_now(),
                                                   "setting": settings.now()}


def faced(store):
    """The bodies of the concept's setting that need a face (every one that does not shine), each filled from the
    reference table."""
    return [body for body in settings.checked(concept(store)["setting"])["bodies"] if body.get("kelvin") is None]


def body_param(key):
    """The `body` param of a row: the body as the runner's store's concept holds it now."""
    def worked_out(runner):
        return next((body for body in faced(runner.store) if body["body"] == key), None)
    return worked_out


def style_param(runner):
    return concept(runner.store)["style"]


def facts_of(body):
    """The body's physics in words, the facts it has."""
    return ", ".join(said.format(body[key]) for key, said in FACTS if body.get(key) is not None) or "no facts known"


def face_body(body, style, method):
    """The request: the question and its schema (the face is scene_library's surface schema, one of it)."""
    text = QUESTION.format(style=style or "(no style line)", name=body["name"], facts=facts_of(body),
                           recipes=scene_library.recipe_lines(method))
    colour = {"type": "OBJECT", "properties": {"setting": {"type": "STRING"}, "token": {"type": "STRING"}},
              "required": ["setting", "token"]}
    token = {"type": "OBJECT", "properties": {"token": {"type": "STRING"}, "colour": {"type": "STRING"}},
             "required": ["token", "colour"], "propertyOrdering": ["token", "colour"]}
    face = {"type": "OBJECT",
            "properties": {"family": {"type": "STRING"}, "recipe": {"type": "STRING", "enum": list(method["recipes"])},
                           "token": {"type": "STRING"}, "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"},
                           "colours": {"type": "ARRAY", "items": colour}},
            "required": ["family", "recipe", "token", "roughness", "metal"],
            "propertyOrdering": ["family", "recipe", "token", "roughness", "metal", "colours"]}
    schema = {"type": "OBJECT", "properties": {"palette": {"type": "ARRAY", "items": token}, "face": face},
              "required": ["palette", "face"], "propertyOrdering": ["palette", "face"]}
    return {"contents": [{"role": "user", "parts": [{"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema}}


def library_of(key, answer, method):
    """The face as a surface library in the loader's form from the answer's text; a reply that does not parse or
    names a token not well formed raises ValueError."""
    parsed = json.loads(answer)
    tokens = {}
    for entry in parsed["palette"]:
        if not (scene_palette.TOKEN.match(entry["token"]) and scene_palette.HEX.match(entry["colour"])):
            raise ValueError(f"a token not well formed: {entry}")
        tokens.setdefault(entry["token"], entry["colour"].lower())
    face = parsed["face"]
    variant = scene_library.variant_of(key, {**face, "name": f"{key}_face", "sound": None}, method)
    variant.pop("surface")
    return {"is": f"the face of {key}, made fresh from the environment concept by {PREFIX}{key} (body_faces.py)",
            "wear_levels": method["wear_levels"], "recipes": method["recipes"],
            "colour_settings": method.get("colour_settings", {}), "tokens": tokens, "dirt": variant["token"],
            "families": {face["family"].strip().lower(): {"variants": {f"{key}_face": variant}}}, "kinds": {},
            "pictures": {}}


def face_of(key, library):
    """face.json's content: the face's variant with its token's colour, as #rrggbb and linear RGB."""
    family, entry = next(iter(library["families"].items()))
    variant = entry["variants"][f"{key}_face"]
    hex_colour = library["tokens"][variant["token"]]
    channels = [int(hex_colour[at:at + 2], 16) / 255 for at in (1, 3, 5)]
    return {"body": key, "surface": f"{key}_face", "family": family, "recipe": variant["recipe"],
            "token": variant["token"], "hex": hex_colour,
            "colour": [round(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4, 5)
                       for value in channels],
            "roughness": variant["roughness"], "metal": variant["metal"], "palette": library["tokens"]}


def make_face(inputs, out, seed, params):
    """The body's face from one ask: face.json and materials.json, or unanswered.json saying why there is none."""
    body = params["body"]
    if body is None:
        raise ValueError("the environment concept's setting no longer holds this body")
    method = json.loads(pathlib.Path(inputs["library"]).read_text())
    key = body["body"]
    answer = route_ask.asked({key: face_body(body, params["style"], method)}, CALLER).get(
        key, finish_ask.NoAnswer("the batch gave none"))
    try:
        if isinstance(answer, Exception):
            raise answer
        library = library_of(key, answer, method)
    except route_ask.UNANSWERED as error:
        (out / "unanswered.json").write_text(json.dumps({"body": key, "why": f"{error!r}"[:300]}, indent=1))
        return
    (out / "materials.json").write_text(json.dumps(library, indent=1))
    (out / "face.json").write_text(json.dumps(face_of(key, library), indent=1))


def face_faults(folder):
    return [] if (folder / "face.json").exists() or (folder / "unanswered.json").exists() else \
        ["no face.json or unanswered.json"]


def face_findings(key, library):
    """What is off in a body's face: not one variant named `<key>_face`, a recipe not the method's, a token or colour
    setting off its palette, a colour setting its recipe needs left out, a setting outside 0 to 1."""
    variants = {name: variant for family in library["families"].values() for name, variant in family["variants"].items()}
    if list(variants) != [f"{key}_face"]:
        return [f"faces {sorted(variants)}, not one {key}_face"]
    variant, needs = variants[f"{key}_face"], library.get("colour_settings", {}).get(variants[f"{key}_face"]["recipe"], [])
    failing = [f"recipe {variant['recipe']} is not the method's"] * (variant["recipe"] not in library["recipes"])
    failing += [f"{setting} not given" for setting in needs if setting not in variant]
    failing += [f"token {variant.get(setting)} ({setting}) is not its palette's" for setting in ("token", *needs)
                if setting in variant and variant[setting] not in library["tokens"]]
    return failing + [f"{setting} {variant[setting]} outside 0 to 1" for setting in scene_library.SETTINGS
                      if not 0 <= variant[setting] <= 1]


def judge_face(output, inputs, evidence):
    """A body's face made from the design (face_findings finds nothing off); no usable answer fails by name."""
    if (output / "unanswered.json").exists():
        why = json.loads((output / "unanswered.json").read_text())["why"]
        return gates.verdict("face from the design", [f"no usable answer: {why}"], 1, "faces")
    face = json.loads((output / "face.json").read_text())
    failing = face_findings(face["body"], json.loads((output / "materials.json").read_text()))
    return gates.verdict("face from the design", failing, 1, "faces", {"tokens": len(face["palette"])})


FACE = contracts.Contract("body-face", 1, face_faults)


def rows(store):
    """One environment row a body that needs a face, by the concept in force in `store`."""
    return tuple(graph.Stage(f"{PREFIX}{body['body']}", "world", make_face, FACE,
                             (gates.guarded("face from the design", judge_face),),
                             files={"library": "{data}/library/materials.json"},
                             params={"body": body_param(body["body"]), "style": style_param}, paid=True,
                             euros=FACE_EUROS)
                 for body in faced(store))
