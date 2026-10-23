"""The finish route's scene palette row, `finish-route-palette` (paid: one Gemini 3.1 Pro answer a scene through the
Batch API at half price, route_ask.py; owner, 2026-10-21: every scene is made from its design alone). A scene's palette
tokens and wear (its scene palette, CONTEXT.md) are read from its design: its locked concept
({home}/design/concepts/<place>.png, drawn in the environment concept's style), never from a hand-kept entry in
data/definitions/place.json and never from the retired base theme's tokens (owner, 2026-10-21: every old material
retired, so the palette is read fresh, each token a name and a colour the concept shows).

No rule decides them: a concept's pixels name its lit shadows and the people in it (skin, hair) and miss the small
accents (hazard, alarm), glass and glow a scene is painted in (measured on the hub, wreck, greenhouse and engine room
concepts, 2026-10-21), and nothing in a picture's pixels says how worn a place is. So one recorded ask a scene decides
them, priced and cleared like every paid row, never by hand: Gemini sees the locked concept and answers the colours
the scene's surfaces are painted in (structure, objects and their accents, glass and glow; never its people), each a
short token name and its colour as it would be painted, unlit; its wear level of the method's levels
(data/library/materials.json `wear_levels`), its dirt from 0 to 1, the token its dirt is drawn in, and the cause it
sees for its wear. A line no scene owns (the people's, seen in every scene) has no concept of its own: it is asked
over every locked concept.

Output: palette.json ({tokens: {token: "#rrggbb"}, wear: {level, dirt, dirt_token, cause}, pictures}), or
unanswered.json with why. Gate "palette from the design": at least MIN_TOKENS tokens, each a #rrggbb colour, its level
one of the method's, its dirt within 0 to 1 and its dirt token one of its tokens; no usable answer fails by name. The
surface-library row (scene_library.py) makes the scene's surfaces in these tokens; the rows after it read both through
palette_library.py.
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import finish_ask  # noqa: E402
import route_ask  # noqa: E402
import surface_data as data  # noqa: E402
import surface_gates as gates  # noqa: E402

PALETTE_EUROS = 0.05  # a guess for the row's run (one ask on one to a few dozen pictures at half price); never a price
CALLER = "finish-route-palette"
MIN_TOKENS = 4  # fewer tokens than this cannot paint a scene's structure, objects and accents
OWN_LONGEST, SHARED_LONGEST = 1536, 768  # a concept's longer side sent: the scene's own, each of a shared line's
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TOKEN = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
QUESTION = """You choose the palette of a 3D scene whose every surface is painted from a library made for it, each
surface drawn in one palette token. {pictures}
First, the scene's palette: every colour its own surfaces are painted in, as the picture shows them: {surfaces}. Light
and shadow are not surfaces: give each colour as it would be painted, unlit. {left_out}Name each one with a short token
in lower case and hyphens (such as "hull-white" or "hazard-yellow") and give its colour as #rrggbb, and say in "what"
which surfaces wear it. Choose generously enough that every surface the scene shows has its token, at least {least}.
Then its wear, one of the levels {levels}: how worn its surfaces are, as the picture shows (chipped edges, scuffed
floors, faded paint, patches), and say the cause you see in "cause". Then its dirt, from 0 (clean) to 1 (caked), and
the token its dirt is drawn in: the colour of the dust or grime itself as the picture shows it, never a surface's
paint; if none of your tokens is that colour, add one for it to the palette."""
# What the palette covers: a scene's own surfaces, its people left out; a line no scene owns (the people's) the
# objects of that line, whatever scenes they stand in (astronaut-made, 2026-10-23: asked for the scenes with its
# people left out, the people's palette had no dark grey, so the boots took glass-grey 20 L* over their close-up, and
# with no grime colour its dirt was the hull's white, which lifted them to L* 65.5).
SCENE_SURFACES = ("its structure (walls, floor, ceiling, ground), its objects and machines, their accents (hazard "
                  "stripes, status lights, trim, labels), glass and glowing screens and lamps")
LINE_SURFACES = ("everything this line's objects wear, each garment, part, accent and trim, skin and hair, glass and "
                 "glowing parts, and not the scenes round them")


def method_read(path):
    """What the ask reads of the method's library (materials.json): its wear levels only."""
    return json.dumps({"wear_levels": json.loads(pathlib.Path(path).read_text())["wear_levels"]}, sort_keys=True)


def files(place):
    """The row's files: the place's surface data, its locked concept (or, for a line no scene owns, every locked
    concept) and the method's wear levels (method_read). A scene declares its own concept whether or not it is
    locked yet, so a scene without one blocks on it by name, never asked over every other scene's concept."""
    from score.stages.shapes_first import align  # here, not at the top: shapes_first imports this stage
    concept = ("concepts", "{home}/design/concepts") if place in align.NO_PLACE else \
        ("concept", "{home}/design/concepts/" + f"{place}.png")
    return {"surfaces": data.pattern(place), concept[0]: concept[1],
            "library": ("{data}/library/materials.json", method_read)}


def pictures_of(inputs):
    """The concept pictures the ask sees, with the longest side each is sent at."""
    from PIL import Image
    if "concept" in inputs:
        return [(Image.open(inputs["concept"]), OWN_LONGEST)]
    return [(Image.open(path), SHARED_LONGEST) for path in sorted(pathlib.Path(inputs["concepts"]).glob("*.png"))]


def schema(levels):
    token = {"type": "OBJECT", "properties": {"token": {"type": "STRING"}, "colour": {"type": "STRING"},
                                             "what": {"type": "STRING"}},
             "required": ["token", "colour", "what"], "propertyOrdering": ["token", "colour", "what"]}
    return {"type": "OBJECT",
            "properties": {"palette": {"type": "ARRAY", "items": token},
                           "wear": {"type": "STRING", "enum": list(levels)}, "cause": {"type": "STRING"},
                           "dirt": {"type": "NUMBER"}, "dirt_token": {"type": "STRING"}},
            "required": ["palette", "wear", "cause", "dirt", "dirt_token"],
            "propertyOrdering": ["palette", "wear", "cause", "dirt", "dirt_token"]}


def palette_body(pictures, levels):
    """The request: the concept pictures, the question and its schema."""
    own = len(pictures) == 1
    said = ("The picture is the scene's locked concept." if own else
            f"The {len(pictures)} pictures are the locked concepts of every scene this line's objects stand in; "
            "choose for the objects themselves.")
    text = QUESTION.format(pictures=said, surfaces=SCENE_SURFACES if own else LINE_SURFACES,
                           left_out="Leave out colours only the people in it wear. " if own else "",
                           least=MIN_TOKENS, levels=", ".join(levels))
    parts = [finish_ask.picture_part(picture, longest) for picture, longest in pictures]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema(levels)}}


def palette_of(answer, levels):
    """The scene palette from the answer's text: {token: "#rrggbb"} in the answer's order (a token named twice
    keeps its first colour), its dirt held to 0 to 1; a reply that does not parse, names a level outside the method's,
    a token or colour not well formed, or a dirt token not its own raises ValueError."""
    parsed = json.loads(answer)
    tokens = {}
    for entry in parsed["palette"]:
        if not (TOKEN.match(entry["token"]) and HEX.match(entry["colour"])):
            raise ValueError(f"a token not well formed: {entry}")
        tokens.setdefault(entry["token"], entry["colour"].lower())
    if parsed["wear"] not in levels or parsed["dirt_token"] not in tokens:
        raise ValueError(f"an answer off its own palette or the wear levels: {parsed}")
    return {"tokens": tokens, "said": {entry["token"]: entry["what"].strip() for entry in parsed["palette"]},
            "wear": {"level": parsed["wear"], "dirt": round(min(max(float(parsed["dirt"]), 0.0), 1.0), 3),
                     "dirt_token": parsed["dirt_token"], "cause": parsed["cause"].strip()}}


def ask(bodies):
    """The one batch of the row's ask: {place: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def make_palette(inputs, out, seed, params):
    """The scene palette from one ask on its locked concept: palette.json, or unanswered.json saying why there is
    none."""
    place = json.loads(pathlib.Path(inputs["surfaces"]).read_text())["place"]
    levels = json.loads(pathlib.Path(inputs["library"]).read_text())["wear_levels"]
    pictures = pictures_of(inputs)
    answer = ask({place: palette_body(pictures, levels)}).get(place, finish_ask.NoAnswer("the batch gave none"))
    try:
        if isinstance(answer, Exception):
            raise answer
        palette = palette_of(answer, levels)
    except route_ask.UNANSWERED as error:
        (out / "unanswered.json").write_text(json.dumps({"place": place, "why": f"{error!r}"[:300]}, indent=1))
        return
    (out / "palette.json").write_text(json.dumps({**palette, "pictures": len(pictures)}, indent=1))


def palette_faults(folder):
    return [] if (folder / "palette.json").exists() or (folder / "unanswered.json").exists() else \
        ["no palette.json or unanswered.json"]


def palette_findings(palette, levels):
    """What is off in a scene palette: a token or colour not well formed, too few tokens, its level, its dirt or a
    dirt token not its own."""
    wear, tokens = palette["wear"], palette["tokens"]
    failing = [f"palette token {token} {colour} is not a name and a #rrggbb colour" for token, colour in tokens.items()
               if not (TOKEN.match(token) and HEX.match(colour))]
    failing += [f"a palette of {len(tokens)} tokens, under {MIN_TOKENS}"] * (len(tokens) < MIN_TOKENS)
    failing += [f"wear level {wear['level']} is not one of {', '.join(levels)}"] * (wear["level"] not in levels)
    failing += [f"dirt {wear['dirt']} outside 0 to 1"] * (not 0 <= wear["dirt"] <= 1)
    return failing + [f"dirt token {wear['dirt_token']} is not one of its tokens"] * (wear["dirt_token"] not in tokens)


def judge_palette(output, inputs, evidence):
    """A scene palette read from the design (palette_findings finds nothing off); no usable answer fails by name."""
    if (output / "unanswered.json").exists():
        why = json.loads((output / "unanswered.json").read_text())["why"]
        return gates.verdict("palette from the design", [f"no usable answer: {why}"], 1, "scene palettes")
    palette = json.loads((output / "palette.json").read_text())
    levels = json.loads(pathlib.Path(inputs["library"]).read_text())["wear_levels"]
    failing = palette_findings(palette, levels)
    return gates.verdict("palette from the design", failing, 1, "scene palettes",
                         {"tokens": len(palette["tokens"]), "wear": float(levels.get(palette["wear"]["level"], -1)),
                          "dirt": palette["wear"]["dirt"]})
