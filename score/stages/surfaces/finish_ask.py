"""The surface stage's paid Google ask and what the finish route shares of it (route_ask.py, route_list.py,
route_split.py, route_views.py, route_recheck.py: the labels, the reply, the key), through google_spend.generate
(tools/cloud; priced on the Google ledger, each request cached by its input's hash).

Each is asked once (the batch rule, #21): no second draw, no second naming, no ask again after a timeout. A call cut
off mid-way is not free: google_spend counts it at its estimate. Only a refusal (HTTP 429, 500, 503 or 504: the
rate or quota, a failing or overloaded service, the flex tier full) is asked again, at most REFUSED_ASKS times, the
wait doubling each time. An ask with no usable answer (UNANSWERED: a
timeout, a lost connection, refused every time, a reply that does not parse) makes its take a gap; any other HTTP
status (400 a body the API rejects, 401 or 403 a bad key, 404 a wrong model) is a set-up fault, not an output's, and
stops the row once instead of making every take a gap. A refused send is written to the Google ledger as started
then failed, and google_spend.month_euros and route_cap.route_euros count it at its estimate though Google billed
nothing for it: the books lean high until Google's billing export (#13) reads the month.

- finish_list: Gemini 3.1 Pro (temperature 0, structured output, thinking held low, on the flex tier at half price)
  looks at a model's close-up and lists its finishes (few, only finishes that truly differ), each mapped to one of the
  take's allowed library surfaces, given the close-up's measured colours (CIELAB) and the library surfaces within
  COLOUR_DELTA_E of each, measured free before the ask. Where none fits it gives the closest and proposes a new
  library surface (name, description, why), which the paint records in the finish registry as proposed, never in the
  library. The prop batch's finish pick asks it (tools/cloud/prop_makers.py).
- LABELS: the flat label colours a finish is drawn in on the route's views (the finish-map method's maps, which first
  used them, were deleted on 2026-10-20, #26).

Refused outside a cleared run or the owner's override (score.adapters.compute.require_cleared), as every paid call.
"""
import base64
import io
import json
import pathlib
import sys

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in (REPO / "tools/props", REPO / "tools/cloud", REPO / "tools/props/library"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the prop tools must not shadow the framework's

LIST_MODEL = "gemini-3.1-pro-preview"
KEY_SECRET = "gemini-api-key"
# The list asks on Google's flex tier, half price: the request's own `serviceTier` (google_spend.TIER_PRICE prices the
# tier the answer's usageMetadata names; one that names none is priced at standard, high, never low). Set here, not in
# google_spend, which is in many rows' code versions (closeup, crops, boxes). The flex tier answers slower: Google's
# flex page asks for client timeouts of 10 minutes or more (read 2026-10-20).
LIST_TIER, FLEX_TIMEOUT = "flex", 900
# A refused call (429: rate or quota, 500: an internal fault, 503: no room, the flex tier full, 504: the service's own
# deadline passed) did no work; it is asked again after REFUSED_WAIT seconds, doubling, at most REFUSED_ASKS times in
# all (audit, 2026-10-22: a 500 or 504 was a set-up fault that stopped the row).
REFUSED, REFUSED_ASKS, REFUSED_WAIT = (429, 500, 503, 504), 3, 30
# The label colours a finish map paints with, in order (finish 1 the first): saturated, far apart, none near the
# white background or black.
LABELS = ((230, 25, 25), (20, 170, 40), (30, 70, 235), (245, 215, 0), (215, 0, 215), (0, 200, 215), (255, 125, 0),
          (120, 0, 190))
LABEL_WORDS = ("pure red", "pure green", "pure blue", "pure yellow", "pure magenta", "pure cyan", "pure orange",
               "pure purple")
BACKGROUND = (255, 255, 255)
LIST_QUESTION = """You help paint a 3D model of an object made from this picture.
The object: {object}.
List the object's finishes: the distinct surface treatments a painter would give its parts (for example gold foil,
bare steel, black rubber, brown vinyl). Keep the list short: list a finish only when it truly differs in material or
paint from the others. Dirt, wear, rust spots, scratches, light, shadow and reflections are not finishes of their own.
At most {most} finishes; most objects have two to four.
For each finish say which parts of the object in this picture have it, the finish in a few words, and which one of
these library surfaces it is:
{surfaces}
Choose by what the part is and how such a part is made, not only by its colour in the picture. If no surface on the
list fits the finish, still give the closest code, set "fits" to false and propose a new library surface for it.{regions}"""
# Added to the list question when the close-up's colours were measured.
REGIONS = """
The object's main colours in this picture, measured (CIELAB, as lit), each with the library surfaces whose colour lies
within {delta:.0f} (CIE76) of it, nearest first. A finish whose colour is one of these should take a surface near it;
glass, lamp light, screens and print are judged by what they are, not by this colour:
{lines}"""


# Added to the route's list question (route_list.py, score #164, #171): the printed marks a part carries, each placed
# later by free code (route_parts.decal_placements): words, numbers and plain lines drawn as text decals in a library
# face (text_decals.py: a route's texture garbles them), any other mark printed from a library decal, never cut from the
# close-up.
MARKS = """
Last, list the printed marks you see on the object in the first picture: words, numbers, plain printed lines or bars,
labels, logos, warning signs, button and key legends, stickers. For each give its box in that picture as
[ymin, xmin, ymax, xmax] from 0 to 1000, tight round its ink, what it is in a few words, and its shape: "text" for words
or numbers (each line of text its own mark, its exact words in "text" as printed, and the look of its typeface, the
nearest of: {looks}), "rule" for a plain straight printed line or bar, "picture" for anything else (a logo, an icon, a
label with a picture of its own). Say whether it is printed in one ink or many (a one-ink mark: the palette token
nearest its ink), the finish (its number in your list, from 1) it is printed on, and "print_finish": the number of the
finish in your list that is this print itself, when you listed the print as a finish of its own, else 0. Leave out marks
you cannot see clearly.{decals}"""
DECALS_TEXT = """
For a picture mark, FIRST say which of these library decals it is (its code), with "fits" false when none of them is
that mark (then give the closest code). The library's decals:
{decals}"""
# Added to MARKS when the library holds patterns (#210, pattern_decals.py): a vent or perforation pattern is a mark of
# its own, drawn from a library pattern at the pitch read here, never TRELLIS.2's bumps.
PATTERNS = """
Also list each regular pattern of openings cut, punched or moulded into a surface (vent holes, perforations, cooling
slots, grille slots, ribs or grooves) as a mark of shape "pattern", one mark for each separate patch of openings, its
box tight round the openings' outer edges. Give its "opening", the nearest of: {openings}; "rows" (how many rows of
openings from top to bottom in the picture) and "columns" (the most openings in one row; for ribs or long slots that
run top to bottom, rows is 1 and columns their count); "staggered" (true when every second row is moved half a spacing
across, as in a diamond or honeycomb grid); "outline", the shape the openings fill together: one of {outlines};
"opening_share", one opening's width across its narrow side as a share of the distance between neighbouring
openings' middles (0.1 to 0.9); "along" for slots and ribs, "up" when they run top to bottom in the picture, else
"across"; "ink": "one", with "ink_token" the palette token nearest the colour seen inside the openings; "on_finish"
the finish they are cut into, and "print_finish" the finish in your list that is the openings themselves, when you
listed them as a finish of their own, else 0. Count the openings in the picture; do not guess."""
BOX_SCALE = 1000.0  # a mark's box in thousandths of the close-up's height and width
SHAPES = ("text", "rule", "picture")
PATTERN = "pattern"  # a mark of openings (#210), offered when the library holds patterns
OPENING_SHARE = (0.05, 0.95)  # an opening's width as a share of its spacing, held inside these


def decal_codes(decals):
    """The codes the question lists the library's decals by (D1, D2, ...)."""
    return [f"D{index + 1}" for index in range(len(decals))]


def decal_lines(decals):
    """One line a decal: its code, words, material class, ink and size."""
    lines = []
    for code, decal in zip(decal_codes(decals), decals):
        size = "x".join(f"{side:.3f}" for side in decal["size_m"]) + " m" if decal.get("size_m") else "size unknown"
        lines.append(f"- {code}: {decal['title'] or ' '.join(decal['words'])} ({decal['class']}, {decal['ink']} ink, "
                     f"{size})")
    return "\n".join(lines) or "- (the library holds no decal)"


def marks_text(decals, looks, patterns=()):
    """The MARKS paragraph: text marks read in one of `looks` (text_decals.FONTS), the library's `decals` offered
    for a picture mark when it holds any, and pattern marks asked when it holds `patterns` (decal_library.patterns)."""
    import pattern_decals
    text = MARKS.format(looks=", ".join(looks), decals=DECALS_TEXT.format(decals=decal_lines(decals)) if decals else "")
    return text + (PATTERNS.format(openings=", ".join(pattern["opening"] for pattern in patterns),
                                   outlines=", ".join(pattern_decals.OUTLINES)) if patterns else "")


def mark_schema(decals, tokens, looks, patterns=()):
    """The schema of the answer's `marks`: a box, what, its shape, its words and typeface look, ink (a one-ink mark's
    palette token), the finish it is on and the finish it is itself, with decals offered a decal code and fits, and
    with `patterns` a pattern mark's opening, rows, columns, stagger, outline, opening share and the way it runs."""
    import pattern_decals
    shapes = [*SHAPES, PATTERN] if patterns else list(SHAPES)
    properties = {"box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}}, "what": {"type": "STRING"},
                  "shape": {"type": "STRING", "enum": shapes}, "text": {"type": "STRING"},
                  "look": {"type": "STRING", "enum": list(looks)},
                  "ink": {"type": "STRING", "enum": ["one", "many"]},
                  "ink_token": {"type": "STRING", "enum": list(tokens)}, "on_finish": {"type": "INTEGER"},
                  "print_finish": {"type": "INTEGER"}}
    if decals:
        properties.update(decal={"type": "STRING", "enum": decal_codes(decals)}, fits={"type": "BOOLEAN"})
    if patterns:
        properties.update(opening={"type": "STRING", "enum": [pattern["opening"] for pattern in patterns]},
                          rows={"type": "INTEGER"}, columns={"type": "INTEGER"}, staggered={"type": "BOOLEAN"},
                          outline={"type": "STRING", "enum": list(pattern_decals.OUTLINES)},
                          opening_share={"type": "NUMBER"},
                          along={"type": "STRING", "enum": list(pattern_decals.ALONG)})
    return {"type": "ARRAY", "items": {"type": "OBJECT", "properties": properties,
                                       "required": ["box_2d", "what", "shape", "ink", "on_finish"],
                                       "propertyOrdering": list(properties)}}


def drawn_gap(mark, looks):
    """Why a text or rule mark cannot be drawn (no words, a look the library has no face for, more than one ink, no
    palette token for its ink), or None."""
    if mark.get("shape") == "text" and not str(mark.get("text") or "").strip():
        return "a text mark names no words"
    if mark.get("shape") == "text" and mark.get("look") not in looks:
        return f"its typeface look {mark.get('look')!r} is none the library has a face for"
    if mark.get("ink") != "one":
        return "a text or line mark printed in many inks"
    if not mark.get("ink_token"):
        return "a one-ink mark names no palette token for its ink"
    return None


def decal_gap(mark, decal):
    """Why a picture mark has no library decal (none fits, its ink is not the mark's, no token for its ink), or None."""
    if decal is None or not mark.get("fits"):
        return "no library decal is this mark"
    if decal["ink"] != mark.get("ink"):
        return f"its decal {decal['address']} is {decal['ink']} ink, the mark {mark.get('ink')}"
    if decal["ink"] == "one" and not mark.get("ink_token"):
        return "a one-ink mark names no palette token for its ink"
    return None


def pattern_gap(mark, pattern):
    """Why a pattern mark cannot be drawn (no library pattern of its opening, no openings counted, no palette token
    for what is seen inside them), or None."""
    if pattern is None:
        return f"no library pattern is its opening {mark.get('opening')!r}"
    if int(mark.get("rows") or 0) < 1 or int(mark.get("columns") or 0) < 1:
        return "a pattern mark counts no rows or columns of openings"
    if not mark.get("ink_token"):
        return "a pattern mark names no palette token for inside its openings"
    return None


def pattern_row(mark, patterns):
    """A pattern mark's own fields (#210): its library pattern's address as its `decal`, its opening's shape, length
    share, relief and roughness, and the mark's rows, columns, stagger, outline, opening share (held inside
    OPENING_SHARE) and the way it runs; with `gap` naming why it cannot be drawn (pattern_gap)."""
    import pattern_decals
    pattern = next((each for each in patterns if each["opening"] == mark.get("opening")), None)
    gap = pattern_gap(mark, pattern)
    share = min(max(float(mark.get("opening_share") or 0.5), OPENING_SHARE[0]), OPENING_SHARE[1])
    return {"decal": None if gap else pattern["address"], "gap": gap, "opening": mark.get("opening"),
            "opening_shape": pattern and pattern["shape"], "length_share": pattern and pattern["length_share"],
            "relief": pattern and pattern["relief"], "roughness": pattern and pattern["roughness"],
            "rows": int(mark.get("rows") or 0), "columns": int(mark.get("columns") or 0),
            "staggered": bool(mark.get("staggered")),
            "outline": mark.get("outline") if mark.get("outline") in pattern_decals.OUTLINES else "rectangle",
            "opening_share": share,
            "along": mark.get("along") if mark.get("along") in pattern_decals.ALONG else "up"}


def marks_of(answer, decals, finishes, close_up_size, looks=(), patterns=()):
    """The answer's marks: each box in the close-up's pixels ([x, y, width, height]), what, shape, ink (a one-ink
    mark's palette token), the finish it is on and the finish that is its print (0-based, None: not listed), and a text
    mark's words and look, a picture mark's decal's address, or a pattern mark's library pattern and counts
    (pattern_row, `patterns` decal_library.patterns); None with `gap` naming why one cannot be printed (drawn_gap,
    decal_gap, pattern_gap). A mark on no finish of the list, or with no area, is left out; one with no shape is a
    picture."""
    names, codes = [decal["address"] for decal in decals], decal_codes(decals)
    wide, tall = close_up_size
    found = []
    for mark in answer.get("marks") or []:
        box, finish = mark.get("box_2d") or [], int(mark.get("on_finish", 0)) - 1
        if len(box) != 4 or not 0 <= finish < finishes:
            continue
        top, left, bottom, right = (min(max(float(value), 0.0), BOX_SCALE) / BOX_SCALE for value in box)
        if bottom <= top or right <= left:
            continue
        shape = mark.get("shape") if mark.get("shape") in (*SHAPES, PATTERN) else "picture"
        printed = int(mark.get("print_finish") or 0) - 1
        row = {"box": [round(left * wide), round(top * tall), round((right - left) * wide),
                       round((bottom - top) * tall)], "what": mark.get("what", ""), "shape": shape,
               "ink": mark.get("ink"), "ink_token": mark.get("ink_token") if mark.get("ink") == "one" else None,
               "on_finish": finish, "print_finish": printed if 0 <= printed < finishes and printed != finish else None}
        if shape == PATTERN:
            row.update(text=None, look=None, **pattern_row(mark, patterns))
        elif shape in ("text", "rule"):
            gap = drawn_gap(mark, looks)
            row.update(text=str(mark.get("text") or "").strip() if shape == "text" else None,
                       look=mark.get("look") if shape == "text" else None, decal=None, gap=gap)
        else:
            decal = decals[codes.index(mark["decal"])] if mark.get("decal") in codes else None
            gap = decal_gap(mark, decal)
            row.update(decal=None if gap else names[codes.index(mark["decal"])], gap=gap)
        found.append(row)
    return found


class NoAnswer(Exception):
    """An ask that got no answer: refused REFUSED_ASKS times, or its connection lost before an HTTP status."""


# What an ask that got no usable answer raises; each makes its take or draw a gap, never an ask again. An HTTPError
# that is not a refusal is left out on purpose: a set-up fault stops the row (module docstring).
UNANSWERED = (NoAnswer, TimeoutError, ConnectionError, ValueError, KeyError)


def generated(model, body, key, timeout, caller, cache, room=None):
    """google_spend.generate, asked once. A refusal (HTTP REFUSED: rate, quota, a failing or full service) did no work and is
    asked again after a wait, at most REFUSED_ASKS times in all, `room` (a cap's check, when given) called before
    every send; refused every time, or a connection lost before any status, raises NoAnswer. A timeout reaches the
    caller as it is (the row makes its take a gap): Google may bill a call cut off mid-way, and google_spend counts
    it at its estimate. Any other HTTP status reaches the caller unchanged."""
    import time
    import urllib.error
    import google_spend
    for attempt in range(REFUSED_ASKS):
        if room is not None:
            room()
        try:
            return google_spend.generate(model, body, key, timeout, caller=caller, cache=cache)
        except urllib.error.HTTPError as error:
            if error.code not in REFUSED:
                raise
            if attempt == REFUSED_ASKS - 1:
                raise NoAnswer(f"refused {REFUSED_ASKS} times, last HTTP {error.code}") from error
            time.sleep(REFUSED_WAIT * 2 ** attempt)
        except urllib.error.URLError as error:
            raise NoAnswer(f"no connection: {error.reason!r}") from error


def secret_key():
    from secret_store import secret
    return secret(KEY_SECRET)


def picture_part(picture, longest):
    """A picture as an inline PNG part, composited on white, its longer side at most `longest` pixels."""
    picture = picture.convert("RGBA")
    flat = Image.new("RGBA", picture.size, BACKGROUND + (255,))
    flat.alpha_composite(picture)
    flat = flat.convert("RGB")
    flat.thumbnail((longest, longest))
    buffer = io.BytesIO()
    flat.save(buffer, "PNG")
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(buffer.getvalue()).decode()}}


def surface_codes(surfaces):
    """The codes the question lists the take's surfaces by (part_judge's M1, M2, ...)."""
    import part_judge
    return [part_judge.code(index) for index in range(len(surfaces))]


def region_lines(regions, surfaces):
    """The REGIONS text: `regions` is {"within": the CIE76 distance a near surface lies within, "regions": [[share of
    the object, L*a*b*, the names of the surfaces near it], ...]}; per region its share, colour and near surfaces by
    their codes. Empty with no region."""
    if not regions or not regions["regions"]:
        return ""
    codes = dict(zip(surfaces, surface_codes(surfaces)))
    lines = [f"- {round(share * 100)}% of the object: L*a*b* ({', '.join(str(round(value)) for value in lab)}); near "
             + (", ".join(codes[name] for name in near if name in codes) or "no surface")
             for share, lab, near in regions["regions"]]
    return REGIONS.format(delta=regions["within"], lines="\n".join(lines))


def list_body(picture, object_words, surfaces, regions=None):
    """The finish-list request: the close-up, the question with the take's surfaces in part_judge's words (the same
    words the round-4 judge read) and its measured colours' regions (region_lines), a schema whose surface is one of
    their codes, thinking held low from the start (flat's, hangar's and lab's namings timed out at 300 s on high,
    2026-10-12)."""
    import part_judge
    text = LIST_QUESTION.format(object=object_words, most=len(LABELS), surfaces=part_judge.material_lines(surfaces),
                                regions=region_lines(regions, surfaces))
    proposal = {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "description": {"type": "STRING"},
                                                 "why": {"type": "STRING"}},
                "required": ["name", "description", "why"]}
    finish = {"type": "OBJECT",
              "properties": {"parts": {"type": "STRING"}, "finish": {"type": "STRING"},
                             "surface": {"type": "STRING", "enum": surface_codes(surfaces)},
                             "fits": {"type": "BOOLEAN"}, "new_surface": proposal},
              "required": ["parts", "finish", "surface", "fits"],
              "propertyOrdering": ["parts", "finish", "surface", "fits", "new_surface"]}
    schema = {"type": "OBJECT", "properties": {"finishes": {"type": "ARRAY", "items": finish}},
              "required": ["finishes"]}
    return {"contents": [{"role": "user", "parts": [picture_part(picture, 1600), {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema, "thinkingConfig": {"thinkingLevel": "low"}},
            "serviceTier": LIST_TIER}


def reply_text(response):
    """The answer's text (thought parts left out)."""
    candidate = (response.get("candidates") or [{}])[0]
    return "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                   if not part.get("thought"))


def parsed_list(text, surfaces):
    """The finish list from the reply: each finish with its surface's library name; at most len(LABELS) kept."""
    names = list(surfaces)
    codes = surface_codes(surfaces)
    found = []
    for entry in json.loads(text)["finishes"][:len(LABELS)]:
        entry = dict(entry, surface=names[codes.index(entry["surface"])])
        found.append(entry)
    if not found:
        raise ValueError("the finish list is empty")
    return found


def finish_list(picture, object_words, surfaces, regions=None):
    """The take's finish list (parsed_list), asked once on the flex tier; the call is priced on the Google ledger, a
    cached ask is free."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish list")
    response = generated(LIST_MODEL, list_body(picture, object_words, surfaces, regions), secret_key(), FLEX_TIMEOUT,
                         caller="finishmap-list", cache=True)
    return parsed_list(reply_text(response), surfaces)
