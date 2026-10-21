"""The finish route's scene palette row, `finish-route-palette` (paid: one Gemini 3.1 Pro answer a scene through the
Batch API at half price, route_ask.py; owner, 2026-10-21: every scene is made from its design alone). A scene's palette
tokens and wear (its scene palette, CONTEXT.md) are read from its design: its locked concept
({home}/design/concepts/<place>.png, drawn in the environment concept's style), never from a hand-kept entry in
data/definitions/place.json, so a new scene needs nothing written for it.

No rule decides them: measured against the palette tokens, a concept's pixels name its lit shadows and the people in
it (skin, hair) and miss the small accents (hazard, alarm), glass and glow a scene is painted in (measured on the hub,
wreck, greenhouse and engine room concepts, 2026-10-21), and nothing in a picture's pixels says how worn a place is.
So one recorded ask a scene decides both, priced and cleared like every paid row, never by hand: Gemini sees the
locked concept and the library's palette tokens in words, and answers the tokens the scene's surfaces are painted in
(structure, objects and their accents, glass and glow; never its people), its wear level of the library's levels,
its dirt from 0 to 1, the token its dirt is drawn in, and the cause it sees for its wear. A line no scene owns (the
people's, seen in every scene) has no concept of its own: it is asked over every locked concept.

Output: palette.json ({tokens, wear: {level, dirt, dirt_token, cause}, pictures}), or unanswered.json with why. Gate
"palette from the design": its tokens the library's (at least MIN_TOKENS), its level one of the library's, its dirt
within 0 to 1 and its dirt token the library's; no usable answer fails by name. The rows after it read the scene
palette through palette_library.py (the list's tokens and wear, every take's surfaces, the bake's and the check's
wear and dirt).
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import finish_ask  # noqa: E402
import palette_library  # noqa: E402
import prop_env  # noqa: E402
import route_ask  # noqa: E402
import surface_data as data  # noqa: E402
import surface_gates as gates  # noqa: E402

PALETTE_EUROS = 0.05  # a guess for the row's run (one ask on one to a few dozen pictures at half price); never a price
CALLER = "finish-route-palette"
MIN_TOKENS = 4  # fewer tokens than this cannot paint a scene's structure, objects and accents
OWN_LONGEST, SHARED_LONGEST = 1536, 768  # a concept's longer side sent: the scene's own, each of a shared line's
QUESTION = """You choose the palette of a 3D scene that is painted only from a shared library of surfaces, each drawn
in one palette token. {pictures}
First, the scene's palette: every token below that the scene's own surfaces are painted in, as the picture shows
them: its structure (walls, floor, ceiling, ground), its objects and machines, their accents (hazard stripes, status
lights, trim, labels), glass and glowing screens and lamps. Light and shadow are not surfaces; leave out tokens only
the people in it wear. Choose generously enough that every surface the scene shows has its token, at least
{least}. The palette tokens:
{tokens}
Then its wear, one of the library's levels ({levels}): how worn its surfaces are, as the picture shows (chipped edges,
scuffed floors, faded paint, patches), and say the cause you see in "cause". Then its dirt, from 0 (clean) to 1
(caked), and the token its dirt is drawn in, the dust or grime the picture shows."""


def concept_path(place):
    """The scene's own locked concept, here or not."""
    return prop_env.PROPS_HOME / "design/concepts" / f"{place}.png"


def library_read(path):
    """What the ask reads of the library (materials.json): the tokens its variants are drawn in and its wear levels,
    so a surface added in a token the library already has asks no scene again."""
    library = json.loads(pathlib.Path(path).read_text())
    tokens = sorted({variant["token"] for family in library["families"].values()
                     for variant in family["variants"].values()})
    return json.dumps({"tokens": tokens, "wear_levels": library["wear_levels"]}, sort_keys=True)


def files(place):
    """The row's files: the place's surface data, its locked concept (or, for a line no scene owns, every locked
    concept), the library's tokens and wear levels (library_read) and the tokens' colours."""
    concept = ("concept", "{home}/design/concepts/" + f"{place}.png") if concept_path(place).exists() else \
        ("concepts", "{home}/design/concepts")
    return {"surfaces": data.pattern(place), concept[0]: concept[1],
            "library": ("{data}/library/materials.json", library_read), "tokens": "{repo}/design/tokens/tokens.json"}


def pictures_of(inputs):
    """The concept pictures the ask sees, with the longest side each is sent at."""
    from PIL import Image
    if "concept" in inputs:
        return [(Image.open(inputs["concept"]), OWN_LONGEST)]
    return [(Image.open(path), SHARED_LONGEST) for path in sorted(pathlib.Path(inputs["concepts"]).glob("*.png"))]


def schema(tokens, levels):
    return {"type": "OBJECT",
            "properties": {"palette": {"type": "ARRAY", "items": {"type": "STRING", "enum": list(tokens)}},
                           "wear": {"type": "STRING", "enum": list(levels)}, "cause": {"type": "STRING"},
                           "dirt": {"type": "NUMBER"}, "dirt_token": {"type": "STRING", "enum": list(tokens)}},
            "required": ["palette", "wear", "cause", "dirt", "dirt_token"],
            "propertyOrdering": ["palette", "wear", "cause", "dirt", "dirt_token"]}


def palette_body(pictures, tokens, levels):
    """The request: the concept pictures, the question and its schema."""
    import part_judge
    said = ("The picture is the scene's locked concept." if len(pictures) == 1 else
            f"The {len(pictures)} pictures are the locked concepts of every scene this line's objects stand in; "
            "choose for the objects themselves.")
    text = QUESTION.format(pictures=said, least=MIN_TOKENS, levels=", ".join(levels),
                           tokens="\n".join(f"- {token}: {part_judge.colour_words(colour)}"
                                            for token, colour in tokens.items()))
    parts = [finish_ask.picture_part(picture, longest) for picture, longest in pictures]
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema(tokens, levels)}}


def palette_of(answer, tokens, levels):
    """The scene palette from the answer's text: its tokens in the library's order, duplicates dropped, its dirt held
    to 0 to 1; a reply that does not parse or names a level or token outside the library raises ValueError."""
    parsed = json.loads(answer)
    if parsed["wear"] not in levels or parsed["dirt_token"] not in tokens or set(parsed["palette"]) - set(tokens):
        raise ValueError(f"an answer off the library: {parsed}")
    return {"tokens": [token for token in tokens if token in set(parsed["palette"])],
            "wear": {"level": parsed["wear"], "dirt": round(min(max(float(parsed["dirt"]), 0.0), 1.0), 3),
                     "dirt_token": parsed["dirt_token"], "cause": parsed["cause"].strip()}}


def ask(bodies):
    """The one batch of the row's ask: {place: answer text, or why there is none}."""
    return route_ask.asked(bodies, CALLER)


def make_palette(inputs, out, seed, params):
    """The scene palette from one ask on its locked concept: palette.json, or unanswered.json saying why there is
    none."""
    import library
    place = json.loads(pathlib.Path(inputs["surfaces"]).read_text())["place"]
    tokens, levels = palette_library.library_tokens(), library.theme_library()["wear_levels"]
    pictures = pictures_of(inputs)
    answer = ask({place: palette_body(pictures, tokens, levels)}).get(place, finish_ask.NoAnswer("the batch gave none"))
    try:
        if isinstance(answer, Exception):
            raise answer
        palette = palette_of(answer, tokens, levels)
    except route_ask.UNANSWERED as error:
        (out / "unanswered.json").write_text(json.dumps({"place": place, "why": f"{error!r}"[:300]}, indent=1))
        return
    (out / "palette.json").write_text(json.dumps({**palette, "pictures": len(pictures)}, indent=1))


def palette_faults(folder):
    return [] if (folder / "palette.json").exists() or (folder / "unanswered.json").exists() else \
        ["no palette.json or unanswered.json"]


def palette_findings(palette, tokens, levels):
    """What is off the library in a scene palette: a token, too few tokens, its level, its dirt or its dirt token."""
    wear = palette["wear"]
    failing = [f"palette token {token} is not the library's" for token in palette["tokens"] if token not in tokens]
    failing += [f"a palette of {len(palette['tokens'])} tokens, under {MIN_TOKENS}"] * (
        len(palette["tokens"]) < MIN_TOKENS)
    failing += [f"wear level {wear['level']} is not the library's"] * (wear["level"] not in levels)
    failing += [f"dirt {wear['dirt']} outside 0 to 1"] * (not 0 <= wear["dirt"] <= 1)
    return failing + [f"dirt token {wear['dirt_token']} is not the library's"] * (wear["dirt_token"] not in tokens)


def judge_palette(output, inputs, evidence):
    """A scene palette read from the design (palette_findings finds nothing off the library); no usable answer fails
    by name."""
    import library
    if (output / "unanswered.json").exists():
        why = json.loads((output / "unanswered.json").read_text())["why"]
        return gates.verdict("palette from the design", [f"no usable answer: {why}"], 1, "scene palettes")
    palette = json.loads((output / "palette.json").read_text())
    levels = library.theme_library()["wear_levels"]
    failing = palette_findings(palette, palette_library.library_tokens(), levels)
    return gates.verdict("palette from the design", failing, 1, "scene palettes",
                         {"tokens": len(palette["tokens"]), "wear": float(levels.get(palette["wear"]["level"], -1)),
                          "dirt": palette["wear"]["dirt"]})
