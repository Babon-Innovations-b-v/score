"""The surface stage's two paid Google asks (the finish-map method), both through google_spend.generate
(tools/props/cloud; priced on the Google ledger, each request cached by its input's hash).

- finish_list: Gemini 3.1 Pro (temperature 0, structured output) looks at a model's close-up and lists its finishes
  (few, only finishes that truly differ), each mapped to one of the take's allowed library surfaces; where none fits
  it gives the closest and proposes a new library surface (name, description, why), which the paint records in the
  finish registry as proposed, never in the library.
- draw_map: Nano Banana Pro redraws the close-up as a finish map, each finish one flat label colour (LABELS) on plain
  white, with a seed so a failed map can be drawn again; the last draw is asked more strictly (STRICT).
- draw_view_map: the same for a turntable view of the raw model (its own texture, unlit), given the close-up and its
  finish map as the reference, so each finish keeps its label colour on the sides the close-up does not show.

Refused outside a cleared run or the owner's override (score.adapters.compute.require_cleared), as every paid call.
"""
import base64
import io
import json
import pathlib
import sys

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in (REPO / "tools/props", REPO / "tools/props/cloud", REPO / "tools/props/library"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the prop tools must not shadow the framework's

LIST_MODEL = "gemini-3.1-pro-preview"
MAP_MODEL = "gemini-3-pro-image"
KEY_SECRET = "gemini-api-key"
TIMEOUT = 300
ASKS = 3
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
list fits the finish, still give the closest code, set "fits" to false and propose a new library surface for it."""
MAP_WORDING = """Redraw this picture as a flat-colour finish map for a 3D painter.
Keep exactly the same object, the same outline, pose, size and position in the frame; do not move, crop, add or
remove anything. Paint every visible part of the object one solid flat colour by its finish:
{finishes}
Use only these colours, fully saturated and flat: no shading, no light, no texture, no gradients, no outlines, no
lines, no text. Every pixel of the object takes one of these colours. The background is plain pure white."""
STRICT = """
Not one pixel of the photograph may remain: doors, handles, grilles, louvres, vents, panels and their edges are all
painted flat in their finish's colour too, with nothing photographic left anywhere on the object."""
VIEW_WORDING = """The first picture is a photograph of an object. The second is its finish map: the same picture with
every finish painted one flat colour:
{finishes}
The third picture shows the same object from another side. Redraw the third picture as a finish map in exactly the
same way: keep its outline, pose, size and position in the frame; paint every visible part one solid flat colour by
its finish, the same colour that finish has in the second picture. Use only these colours, fully saturated and flat:
no shading, no light, no texture, no gradients, no outlines, no lines, no text. Every pixel of the object takes one of
these colours; not one pixel of the photograph may remain. The background is plain pure white."""


def generated(model, body, key, timeout, caller, cache):
    """google_spend.generate, asked again up to ASKS times when the connection times out or drops (a request the API
    lost answered nothing and cost nothing; the greenhouse's naming lost one, 2026-10-12)."""
    import urllib.error
    import google_spend
    for attempt in range(ASKS):
        try:
            return google_spend.generate(model, body, key, timeout, caller=caller, cache=cache)
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if attempt == ASKS - 1:
                raise


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


def list_body(picture, object_words, surfaces):
    """The finish-list request: the close-up, the question with the take's surfaces in part_judge's words (the same
    words the round-4 judge read), and a schema whose surface is one of their codes."""
    import part_judge
    text = LIST_QUESTION.format(object=object_words, most=len(LABELS), surfaces=part_judge.material_lines(surfaces))
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
                                 "responseSchema": schema}}


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


def finish_list(picture, object_words, surfaces):
    """The take's finish list (parsed_list); the call is priced on the Google ledger, a cached ask is free."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish list")
    response = generated(LIST_MODEL, list_body(picture, object_words, surfaces), secret_key(), TIMEOUT,
                         caller="finishmap-list", cache=True)
    return parsed_list(reply_text(response), surfaces)


NAME_QUESTION = """You help paint a 3D model of an object made from the first picture. The object: {object}.
The second picture is its finish map: each finish painted one flat colour. Look at the finish painted {label}: {finish},
on {parts}. Which one of these library surfaces is it?
{surfaces}
Choose by what the part is made of and how such a part is made, then by its colour in the first picture."""


def name_body(picture, front_map, object_words, number, finish, surfaces):
    """The second naming of one finish: the close-up, its finish map and the take's surfaces, the answer one code."""
    import part_judge
    text = NAME_QUESTION.format(object=object_words, label=LABEL_WORDS[number], finish=finish["finish"],
                                parts=finish["parts"], surfaces=part_judge.material_lines(surfaces))
    schema = {"type": "OBJECT", "properties": {"surface": {"type": "STRING", "enum": surface_codes(surfaces)}},
              "required": ["surface"]}
    return {"contents": [{"role": "user", "parts": [picture_part(picture, 1600), picture_part(front_map, 1600),
                                                    {"text": text}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                 "responseSchema": schema}}


def name_finish(picture, front_map, object_words, number, finish, surfaces):
    """The library surface Gemini 3.1 Pro names for one finish when asked again with its finish map."""
    from score.adapters import compute
    compute.require_cleared("a Gemini finish naming")
    response = generated(LIST_MODEL, name_body(picture, front_map, object_words, number, finish,
                                    surfaces), secret_key(), TIMEOUT,
                         caller="finishmap-name", cache=True)
    code = json.loads(reply_text(response))["surface"]
    return list(surfaces)[surface_codes(surfaces).index(code)]


def finish_lines(finishes):
    """Each finish's label colour in words and its parts, one line each."""
    return "\n".join(f"- {LABEL_WORDS[number]} (RGB {LABELS[number][0]}, {LABELS[number][1]}, {LABELS[number][2]}): "
                     f"{entry['finish']}, on {entry['parts']}" for number, entry in enumerate(finishes))


def image_body(parts, seed):
    """A Nano Banana Pro request: its parts, one square 2K picture back."""
    return {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "seed": seed,
                                 "imageConfig": {"imageSize": "2K", "aspectRatio": "1:1"}}}


def map_body(picture, finishes, seed, strict=False):
    """The finish-map request: each finish's label colour in words (STRICT added on the last draw), the close-up."""
    text = MAP_WORDING.format(finishes=finish_lines(finishes)) + (STRICT if strict else "")
    return image_body([{"text": text}, picture_part(picture, 1600)], seed)


def view_body(picture, front_map, view, finishes, seed):
    """The view-map request: the words, the close-up, its finish map and a turntable view of the raw model."""
    return image_body([{"text": VIEW_WORDING.format(finishes=finish_lines(finishes))}, picture_part(picture, 1024),
                       picture_part(front_map, 1024), picture_part(view, 1024)], seed)


def drawn(body, what):
    """One finish map (RGB) from Nano Banana Pro, or None when the answer held no picture."""
    from score.adapters import compute
    compute.require_cleared(what)
    response = generated(MAP_MODEL, body, secret_key(), TIMEOUT, caller="finishmap-map", cache=True)
    found = [piece["inlineData"]["data"] for candidate in response.get("candidates", [])
             for piece in candidate.get("content", {}).get("parts", []) if "inlineData" in piece]
    return Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB") if found else None


def draw_map(picture, finishes, seed, strict=False):
    """The close-up's finish map, or None."""
    return drawn(map_body(picture, finishes, seed, strict), "a Nano Banana Pro finish map")


def draw_view_map(picture, front_map, view, finishes, seed):
    """A turntable view's finish map, or None."""
    return drawn(view_body(picture, front_map, view, finishes, seed), "a Nano Banana Pro view finish map")
