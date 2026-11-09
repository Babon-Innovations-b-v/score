"""The finish route's material step, `surface-library` (paid: one Gemini 3.1 Pro answer a scene through the Batch API
at half price, route_ask.py). The owner retired every old material on 2026-10-21 ("we did a lot of work to how
materials get made, so a chance of contaminating with old is not worth it"): the library starts empty, and each
scene's surfaces are made fresh here, from its design alone, before anything of it is listed, baked or finished.

Gemini sees the scene's locked concept (a line no scene owns, the people's: every locked concept), its scene palette
(finish-route-palette: its tokens and colours, wear and dirt), every object kind its takes are (its surface data,
written from its scene inventory) with the words for it, the parts of the shell its locked plan lays (the floor,
walls, roof, raised levels and stairs, `shell_kinds`: the plan lays an enclosed place's shell, so no take is it), and
today's method: the ProcFunc recipes
(tools/props/library/recipes.py, their default settings and the colour settings each names, data/library/
materials.json). It answers the scene's surfaces, each a variant of one recipe: a name, its family, its token, its
roughness and metal, the token of each colour setting its recipe names, the surface it sounds like (one of
data/sound/surfaces.json's: what the sound layer plays on it and its absorption) and the kinds it is for. No rule
could: which recipe a surface is made with is what the part is, which the concept shows.

Output: materials.json, a surface library in the loader's form (tools/props/library/library.py: the method's wear
levels, recipes and colour settings; the scene's families of variants, its palette tokens, its dirt token, `kinds`
{kind: [variant]}), every variant with its own seed and sound surface (`surface`, the family's its first
variant's); or unanswered.json with why. Gate "surfaces from the design": at least one surface, every kind of the
scene covered (the shell's
parts too), every recipe the method's, every token the palette's, every sound surface known, every setting 0 to
1. The rows after it (finish-route-list, surfaces-parts, surfaces-bake, finish-route-recheck,
surfaces-check) take this library through palette_library.py. Handing the accepted library to score_lib as surface
drafts is the library handover's (score/stages/library), not this row's.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

from score.stages import natural_grounds  # noqa: E402

import finish_ask  # noqa: E402
import palette_library  # noqa: E402
import prop_env  # noqa: E402
import route_ask  # noqa: E402
import scene_palette  # noqa: E402
import surface_gates as gates  # noqa: E402

ROW = palette_library.ROW
CALLER = ROW
LIBRARY_EUROS = 0.05  # a guess for the row's run (one ask on a scene's concept at half price); never a price
SETTINGS = ("roughness", "metal")
# The recipes that paint a picture (tools/props/library/recipes.py, `picture_on`): a scene library makes no picture
# (its `pictures` are empty), so none is offered or kept (surface-library@people, 2026-10-22: suit_patches as `printed`
# with no picture stopped the bake, recipes.arguments wanting its `image`).
PICTURED = ("screen", "printed")
QUESTION = """You make the surface library of one 3D scene: every surface its objects and structure are painted
with, each a variant of one procedural recipe, in the scene's own palette tokens. {pictures}
The scene's palette (token: colour, what wears it):
{tokens}
Its wear is {wear} ({cause}); its dirt {dirt} in {dirt_token}.
The kinds of object in it, each with what it is:
{kinds}
{grounds}The recipes (name: default settings; colour settings it needs in a token of the palette):
{recipes}
The surfaces a thing can sound like (a boot on it, a thing dropped on it): {sounds}.
Answer every surface the scene needs, enough that each kind above is made of surfaces you list (a kind made of
several materials names each of them). For each give a short name in lower case and underscores, its family (one
word for what it is made of: steel, paint, rubber, glass, wood, fabric, plastic, concrete...), its recipe, its token
from the palette, its roughness and metal from 0 to 1, a token of the palette for each colour setting its recipe
needs, the surface it sounds like, and the kinds it is for. Choose each recipe by what the surface is and how it is
made, its token by its colour in the picture. A recipe that draws a pattern of its own (a quilt, tiles, a grid,
boards, a mottled pile, rows of writing) is only for a surface the picture shows with that pattern; a plain surface
takes a plain recipe. A flat sheet (a kind marked so) shows nothing but its face: where the picture shows a pile or a
mottle on it, or writing or print, give it the recipe that draws that (pile; written, its ink the second colour). A
thing that shows a picture (a kind marked so: a photo, a print, a painting) is painted with its picture, never its
glass or one plain colour: give the picture the recipe that draws print (written), its token the picture's main colour
and its ink the second; its frame, if any, takes its own surface."""
# A kind's words in the question when a take of it is laid as a flat sheet (sheet_kinds).
SHEET_WORDS = " (a flat sheet: its face is what shows)"
# A kind's words in the question when its take's words name a picture (shows_picture), and the recipes that draw one in
# the palette's colours: flat's framed family photo, a flat sheet, took plain `glass` in photo-grey and baked one grey
# sheet, so its likeness failed, while its poster and calendar, `written`, passed (checkout 62, 2026-11-08).
PICTURE_WORDS = " (shows a picture: draw it, never its glass)"
PICTURES = ("photo", "photograph", "picture", "painting", "poster", "print", "portrait", "artwork", "canvas")
DRAWN = ("written",)
# flat_sheet.SHEET_SHARE (thin_straight.FLAT_SHARE) and tools/props/closeup/check.SLENDER_SHARE, held equal by the test.
SHEET_FLAT, SHEET_MIDDLE = 0.05, 0.25


def files(place):
    """The row's files: the scene palette row's (its surface data, its locked concept or every locked concept), the
    whole method's library (recipes, their colour settings, wear levels) and what its ground rows' recipes are ruled
    from (ground_files), and its locked plan where it has one (the shell's parts, shell_kinds)."""
    return {**scene_palette.files(place), "library": "{data}/library/materials.json",
            "sounds": "{data}/sound/surfaces.json", **ground_files(place), **plan_files(place)}


def plan_files(place):
    """The scene's locked plan where it has one ({home}/design/plans/<place>.json, where score/review/plans.KEPT keeps
    it); none for a line no scene owns. The path is spelled here, not read off plans: importing plans put the whole
    review behind it (concepts, reading, plan_writing, people_rows, people_bodies, the conductor and the store) into
    the row's code version, so their edits re-asked this paid row (7f68af46, 6456c223, cd5d01c8, 2026-11-03)."""
    return {"plan": f"{{home}}/design/plans/{place}.json"} if \
        (prop_env.PROPS_HOME / "design" / "plans" / f"{place}.json").is_file() else {}


# The words the question gives each shell part's library kind (palette_library.SHELL_KINDS, its first).
SHELL_WORDS = {"deck": "the floor the place stands on", "level": "a raised deck or level of the place",
               "wall": "the room's walls", "roof": "the roof or ceiling over the room", "stair": "the stairs"}


def shell_kinds(plan):
    """{library kind: the words for it} of each part of the shell the locked plan lays (design_shell: an enclosed
    place's deck, walls and roof, whoever lays them, else an open place's raised levels; `stair` for its flights),
    each its part's first library kind (palette_library.SHELL_KINDS), the one the shell finds its surface by."""
    from score.stages import shell_parts
    parts = shell_parts.parts(plan)
    if any(len(entry.get("points") or []) >= 3 for entry in plan.get("stairs") or []):
        parts.add("stair")
    return {palette_library.SHELL_KINDS[part][0]: f"{SHELL_WORDS[part]} (the shell its locked plan lays)"
            for part in sorted(parts)}


def ground_files(place):
    """The scene's kept inventory and kept sky where it has them, with the physics' reference table: what its ground
    rows' natural ground recipes are ruled from (grounds_of); none for a line no scene owns. The design folder is
    spelled here (plan_files says why), not read off score/review/scene_sky.KEPT."""
    found = {name: f"{{home}}/design/{folder}/{place}.json" for name, folder in (("inventory", "inventory"),
                                                                                 ("sky", "sky"))
             if (prop_env.PROPS_HOME / "design" / folder / f"{place}.json").is_file()}
    return {**found, "reference": "{data}/physics/bodies.json"} if "inventory" in found else {}


def grounds_of(inputs):
    """{a ground row's kind (its noun): {"words", "recipe", "why"}} of the scene inventory's terrain rows, each the
    natural ground its words name, else its body's physics at the scene's kept site (natural_grounds.of_row); a row
    neither gives a recipe is left to the ask. {} with no inventory."""
    if "inventory" not in inputs:
        return {}
    rows = [row for row in json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"] if row.get("terrain")]
    sky = json.loads(pathlib.Path(inputs["sky"]).read_text()) if "sky" in inputs else None
    bodies = (sky["setting"].get("bodies") or []) if sky else []
    body = next((body for body in bodies if body["body"] == sky["site"]["on"]), None) if sky else None
    table = json.loads(pathlib.Path(inputs["reference"]).read_text())
    found = {}
    for row in rows:
        recipe, why = natural_grounds.of_row(row, body, bodies, table)
        if recipe and row.get("noun"):
            found.setdefault(row["noun"], {"words": row.get("name") or row["noun"], "recipe": recipe, "why": why})
    return found


def ground_lines(grounds):
    """The question's lines naming each ground kind's recipe, or none."""
    if not grounds:
        return ""
    return ("The ground kinds, each made with the natural ground recipe its row's words or its body's physics call "
            "for (a surface for it uses that recipe):\n"
            + "\n".join(f"- {kind}: {ground['recipe']} ({ground['why']})" for kind, ground in grounds.items()) + "\n")


def sound_surfaces(inputs):
    """The names of the surfaces a thing can sound like (data/sound/surfaces.json), sorted."""
    return sorted(json.loads(pathlib.Path(inputs["sounds"]).read_text())["surfaces"])


def kinds_of(inputs):
    """{kind: the words for it} of every take in the scene's surface data, every ground row (grounds_of) of its
    inventory and every part of the shell its locked plan lays (shell_kinds; first words kept)."""
    found = {kind: ground["words"] for kind, ground in grounds_of(inputs).items()}
    data = json.loads(pathlib.Path(inputs["surfaces"]).read_text())
    sheets = sheet_kinds(data)
    for take in data.get("takes", {}).values():
        if take.get("kind"):
            words = take.get("object") or take["kind"]
            found.setdefault(take["kind"], words + (SHEET_WORDS if take["kind"] in sheets else "")
                             + (PICTURE_WORDS if shows_picture(f"{take['kind']} {words}") else ""))
    if "plan" in inputs:
        for kind, words in shell_kinds(json.loads(pathlib.Path(inputs["plan"]).read_text())).items():
            found.setdefault(kind, words)
    return dict(sorted(found.items()))


def shows_picture(words):
    """Whether a take's words name a thing that shows a picture (PICTURES, a word of them whole, its plural too)."""
    return any(word in PICTURES or word.removesuffix("s") in PICTURES for word in re.split(r"[^a-z]+", words.lower()))


def sheet_kinds(data):
    """The kinds of the surface data's takes a model of which its bake lays as a flat sheet: a rug, a mat, a note,
    whose face is all that shows. The bake entry's size by `sheet_sized`."""
    takes, bake = data.get("takes", {}), data.get("bake", {})
    return {takes[take].get("kind") for model, take in bake.get("models", {}).items()
            if take in takes and sheet_sized((bake.get("entries", {}).get(model) or {}).get("size"))}


def sheet_sized(size):
    """Whether a size is a flat sheet's by score/stages/props/flat_sheet.py's size rule: its thinnest side under
    SHEET_FLAT of its longest, its middle one at least SHEET_MIDDLE of it. The rule is read here, not imported: that
    module's file imports the prop route's scene tools (thin_straight's lamps), which put the review pages and the
    store in this paid row's key (main red on 1d330dcf, 2026-11-08); the surfaces test holds the two rules equal."""
    if not size:
        return False
    smallest, middle, largest = sorted(float(value) for value in size)
    return smallest < SHEET_FLAT * largest and middle >= SHEET_MIDDLE * largest


def schema(recipes, tokens, kinds, sounds):
    colour = {"type": "OBJECT", "properties": {"setting": {"type": "STRING"},
                                              "token": {"type": "STRING", "enum": list(tokens)}},
              "required": ["setting", "token"]}
    surface = {"type": "OBJECT",
               "properties": {"name": {"type": "STRING"}, "family": {"type": "STRING"},
                              "recipe": {"type": "STRING", "enum": list(recipes)},
                              "token": {"type": "STRING", "enum": list(tokens)},
                              "roughness": {"type": "NUMBER"}, "metal": {"type": "NUMBER"},
                              "colours": {"type": "ARRAY", "items": colour},
                              "sound": {"type": "STRING", "enum": list(sounds)},
                              "kinds": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(kinds) or [""]}}},
               "required": ["name", "family", "recipe", "token", "roughness", "metal", "sound", "kinds"],
               "propertyOrdering": ["name", "family", "recipe", "token", "roughness", "metal", "colours", "sound",
                                    "kinds"]}
    return {"type": "OBJECT", "properties": {"surfaces": {"type": "ARRAY", "items": surface}},
            "required": ["surfaces"]}


def offered(method):
    """{recipe: default settings} of the method's recipes a scene library may use: all but the PICTURED."""
    return {name: defaults for name, defaults in method["recipes"].items() if name not in PICTURED}


def recipe_lines(method):
    """Each offered recipe as a line: its default settings and the colour settings it needs."""
    needs = method.get("colour_settings", {})
    return "\n".join(f"- {name}: {json.dumps(defaults, sort_keys=True)}"
                     + (f"; colours: {', '.join(needs[name])}" if needs.get(name) else "")
                     for name, defaults in offered(method).items())


def library_body(pictures, palette, kinds, method, sounds, grounds=None):
    """The request: the concept pictures, the question and its schema (`sounds`: the sound surfaces' names; `grounds`:
    the ground kinds' ruled recipes, grounds_of)."""
    said = ("The picture is the scene's locked concept." if len(pictures) == 1 else
            f"The {len(pictures)} pictures are the locked concepts of every scene this line's objects stand in.")
    wear, said_of = palette["wear"], palette.get("said", {})
    text = QUESTION.format(
        pictures=said, wear=wear["level"], cause=wear.get("cause", ""), dirt=wear["dirt"],
        dirt_token=wear["dirt_token"], recipes=recipe_lines(method), sounds=", ".join(sounds),
        grounds=ground_lines(grounds),
        tokens="\n".join(f"- {token}: {colour}, {said_of.get(token, '')}"
                         for token, colour in palette["tokens"].items()),
        kinds="\n".join(f"- {kind}: {words}" for kind, words in kinds.items()) or "- (none listed)")
    parts = [finish_ask.picture_part(picture, longest) for picture, longest in pictures]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema(offered(method), palette["tokens"], kinds, sounds)}}


def seed_of(place, name):
    """A variant's own seed, fixed by its scene and name."""
    return int(hashlib.sha256(f"{place}/{name}".encode()).hexdigest()[:8], 16) % 100000


def variant_of(place, surface, method):
    """One answered surface as a library variant: its recipe, token, roughness, metal, colour settings and seed."""
    needs = method.get("colour_settings", {}).get(surface["recipe"], [])
    variant = {"recipe": surface["recipe"], "token": surface["token"], "seed": seed_of(place, surface["name"]),
               "surface": surface.get("sound"),
               **{setting: round(min(max(float(surface[setting]), 0.0), 1.0), 3) for setting in SETTINGS}}
    variant.update({colour["setting"]: colour["token"] for colour in surface.get("colours") or []
                    if colour["setting"] in needs})
    return variant


def library_of(place, answer, palette, method):
    """The scene's surface library from the answer's text, in the loader's form; a reply that does not parse
    raises ValueError."""
    families, kinds = {}, {}
    for surface in json.loads(answer)["surfaces"]:
        name = surface["name"].strip().lower().replace(" ", "_")
        variant = variant_of(place, {**surface, "name": name}, method)
        family = families.setdefault(surface["family"].strip().lower(), {"surface": variant["surface"], "variants": {}})
        family["variants"].setdefault(name, variant)
        for kind in filter(None, surface.get("kinds") or []):
            kinds.setdefault(kind, []).append(name)
    return {"is": f"the surface library of {place}, made fresh from its design by {ROW} (scene_library.py)",
            "wear_levels": method["wear_levels"], "recipes": method["recipes"],
            "colour_settings": method.get("colour_settings", {}), "tokens": palette["tokens"],
            "dirt": palette["wear"]["dirt_token"], "families": families, "kinds": kinds, "pictures": {}}


def ask(bodies):
    """The one batch of the row's ask: {place: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def make_library(inputs, out, seed, params):
    """The scene's surface library from one ask: materials.json, or unanswered.json saying why there is none."""
    place = json.loads(pathlib.Path(inputs["surfaces"]).read_text())["place"]
    palette = palette_library.read(inputs)
    method = json.loads(pathlib.Path(inputs["library"]).read_text())
    kinds, sounds = kinds_of(inputs), sound_surfaces(inputs)
    pictures = scene_palette.pictures_of(inputs)
    answer = ask({place: library_body(pictures, palette, kinds, method, sounds, grounds_of(inputs))}).get(
        place, finish_ask.NoAnswer("the batch gave none"))
    try:
        if isinstance(answer, Exception):
            raise answer
        found = library_of(place, answer, palette, method)
        # The kinds this ask marked as pictures (PICTURE_WORDS): the picture rule judges only a library asked with it,
        # so a library accepted before the marking existed is not failed by a rule its question never stated.
        found["picture_kinds"] = sorted(kind for kind, words in kinds.items() if PICTURE_WORDS in words)
    except route_ask.UNANSWERED as error:
        (out / "unanswered.json").write_text(json.dumps({"place": place, "why": f"{error!r}"[:300]}, indent=1))
        return
    (out / "materials.json").write_text(json.dumps(found, indent=1))


def library_faults(folder):
    return [] if (folder / "materials.json").exists() or (folder / "unanswered.json").exists() else \
        ["no materials.json or unanswered.json"]


def library_findings(found, kinds, sounds, grounds=None):
    """What is off in a scene library: no surface, a kind no surface is for, a kind its ask marked as showing a picture
    (`picture_kinds`, written by make_library; none in a library asked before the marking) no surface of which draws
    one (DRAWN), a ground kind no surface of its ruled
    recipe is for (`grounds`, grounds_of), a recipe not the method's, a token or colour setting off the palette, a
    setting outside 0 to 1, a colour setting its recipe needs left out, a sound surface not known."""
    variants = {name: variant for family in found["families"].values() for name, variant in family["variants"].items()}
    tokens, needs = set(found["tokens"]), found.get("colour_settings", {})
    failing = ["no surface"] * (not variants)
    failing += [f"kind {kind} has no surface" for kind in kinds if not found.get("kinds", {}).get(kind)]
    failing += [f"kind {kind} shows a picture and no surface of it draws one ({', '.join(DRAWN)})"
                for kind in found.get("picture_kinds", []) if found.get("kinds", {}).get(kind)
                and not any(variants.get(name, {}).get("recipe") in DRAWN for name in found["kinds"][kind])]
    failing += [f"ground {kind} has no surface of its recipe {ground['recipe']}"
                for kind, ground in (grounds or {}).items()
                if not any(variants.get(name, {}).get("recipe") == ground["recipe"]
                           for name in found.get("kinds", {}).get(kind, []))]
    for name, variant in variants.items():
        failing += [f"{name}: recipe {variant['recipe']} is not the method's"] * (
            variant["recipe"] not in found["recipes"])
        failing += [f"{name}: recipe {variant['recipe']} paints a picture, and the library has none"] * (
            variant["recipe"] in PICTURED)
        failing += [f"{name}: token {variant.get(key)} ({key}) is not the palette's"
                    for key in ("token", *needs.get(variant["recipe"], [])) if variant.get(key) not in tokens]
        failing += [f"{name}: {key} {variant[key]} outside 0 to 1" for key in SETTINGS if not 0 <= variant[key] <= 1]
        failing += [f"{name}: sound surface {variant.get('surface')} is not known"] * (
            variant.get("surface") not in sounds)
    return failing


def judge_library(output, inputs, evidence):
    """A scene library made from the design (library_findings finds nothing off); no usable answer fails by name."""
    if (output / "unanswered.json").exists():
        why = json.loads((output / "unanswered.json").read_text())["why"]
        return gates.verdict("surfaces from the design", [f"no usable answer: {why}"], 1, "scene libraries")
    found = json.loads((output / "materials.json").read_text())
    kinds = kinds_of(inputs)
    failing = library_findings(found, kinds, sound_surfaces(inputs), grounds_of(inputs))
    return gates.verdict("surfaces from the design", failing, max(len(kinds), 1), "kinds and surfaces",
                         {"surfaces": sum(len(family["variants"]) for family in found["families"].values()),
                          "kinds": len(kinds)})
