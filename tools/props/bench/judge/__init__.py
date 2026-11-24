"""The prop benchmark's picture judge (#184, PRD #159): the owner's own way of judging made a check. Each made model's
look (branch B's `look` step, #182: the finish as the bake paints it, from the close-up's camera) is held by eye to
NVIDIA's model of the same object drawn by the same look (#159), and, when given, to the same object's look in the previous round.

    looked(words, made, given, previous=None, ask=None, pictured=False) -> the bench measure group "picture":
        {"drawn": 1 or 0, <each of KINDS>: 1 when a fault of that kind is seen else 0, "regressed": 1 or 0 (only with
         `previous`, with "closer": {made_first, previous_first} its two answers), "verdicts": {kind: clean | slight |
         fault}, "faults": [{kind, where, what}], "regression": text,
         "pictures": {name: sha256 of the picture as shown}; with `pictured`, "cutout": 1 when the close-up's own cut-out
         is at fault, "cutout_faults": [{where, what}]}
    shown(path, crop) -> the picture's PNG bytes as the judge sees it
    framed(*paths)     -> the crop (shares of the frame) round every object drawn

`made` is the look (look.png, RGBA), `given` NVIDIA's model drawn by the same look (bench.nvidia_look_step's
look.png, the model the only difference, #159; with `pictured`,
a pictured case's close-up, #159: the ask names it so, ORIGINALS), `previous` the
previous round's look (look.png: its made model drawn by today's look, from the same camera, bench.redrawn_look). Each is laid on the close-up's light grey
backdrop (bench.BACKDROP), cut to the same frame round both objects and drawn at SHOWN px, so the three are seen alike.
A look with nothing drawn (no opaque pixel) is `drawn` 0 and asked nothing.

The faults ask is one Claude call on the subscription (score/adapters/models/claude_code, EUR 0), its answer a
structured JSON: every visible fault of the made model against NVIDIA's, its kind of KINDS, and a verdict per kind
(clean; slight: a difference a careful eye lets pass, such as a library grain for NVIDIA's;
fault). With a previous look the regression is asked apart (COMPARE, #205), beside it: the original and the two looks
as A and B, which is closer to the original as a whole, asked in both orders; regressed only when both answers choose
the previous look (regression_of). An answer is kept by the hash of the model and the
body (claude_code.CACHE), whose pictures are these bytes, so the same pictures are never asked twice. The bars are in
measures.BARS: no kind at `fault`, no regression, a drawn look.
A pictured case's close-up is cut out of a larger picture (#159: tc5r's attitude panel, flight screen and pilot
console were torn cut-outs, and the judge booked the ragged outlines their looks copied as the make's faults): the
ask names the cut-out's own faults apart (CUTOUT), `cutout` holds them, and a made model that only follows them is
not at fault for it.
"""
import base64
import hashlib
import io
import json
import pathlib

# The kinds of fault the owner names when he looks (#159: tc4r's look lines), each with what it covers.
KINDS = {
    "edges": "messy, ragged, torn or jagged edges where two finishes meet or along the outline",
    "specks": "dots, blotches, smears or marks of another colour scattered over a surface",
    "holes": "places where the surface is missing: you see through it, or black voids punched into it",
    "lumps": "bulges, blobs, dents or warps on a surface the original has flat or smooth",
    "colour": "a part in a clearly different colour or material (white drawn grey or steel, glass drawn as metal, "
              "a pale colour drawn saturated, a ribbed or patterned surface drawn plain)",
    "text": "lettering, numbers, logos or printed marks garbled into glyphs, misspelled, smeared or missing",
    "shape": "a part whose shape or proportions clearly differ from the original's",
    "parts": "a part, piece or detail of the original that is missing (a shelf, a glass pane, a light strip, a vent "
             "pattern, trim, bolt heads)",
}
VERDICTS = ("clean", "slight", "fault")
# A mirror finish drawn dull is a material fault, not the light's (#159: tc5r's chrome chuck, nozzle, hand drill and
# rods drawn flat matte grey; the judge let all but the nozzle pass as a difference of reflection).
CHROME = ("But a part the original shows as polished chrome or mirror metal (crisp bright highlights and dark "
          "reflections across it) that the made model draws as flat, dull or matte grey is a `colour` fault: that is "
          "its material lost, not the light. ")
# The regression ask (#159 round 10: in one ask with the faults, "worse in any way you would point at, even where
# better in others" marked 26 of 30 tc6 looks regressed where the eye found 4 worse, 12 better): its own ask, both looks
# against the original as a whole, the way the owner chooses which to keep, asked once in each order.
COMPARE = ("You compare two 3D models made again from the same original, to tell which made model is closer to it. The "
           "object: {words}. Pictures A and B are the two made models, drawn alike: the same camera, backdrop and "
           "light, so every difference between A and B is the models' own. Look at both against the original as a "
           "careful person does when choosing which one to keep: the shape, every part and detail, each part's colour "
           "and material, any text, and surface faults (torn or ragged edges, specks and blotches, holes, lumps and "
           "warps). A part, detail or text one has right and the other lost, or a new tear, blotch or warp, counts as "
           "much as a colour. In `a_better` say what A has closer to the original than B, in `b_better` what B has "
           "closer than A (empty when nothing). Then `closer`: `A` or `B` when that one is closer to the original "
           "overall, its gains clearly outweighing its losses; `same` when neither is clearly closer (their "
           "differences small, or their gains and losses even).")
CLOSER = ("A", "B", "same")
SHOWN = 768  # the longest side of each picture as the judge sees it
PAD = 0.04  # the share of the frame kept round the objects when they are cut to it
BACKDROP = (214, 214, 214)  # the close-up's backdrop (tools/props/bench/run/bench.py BACKDROP)
CALLER = "bench-picture"
# Colour strength and value are the part's, not the light's (#198: tc5r's hospital chair seat drawn royal blue for the
# original's muted teal, drill b01's red and the heat gun's navy, the vending cabinet near-black for mid grey, the air
# ratchet glossy jet black for satin grey; the judge forgave them as the other renderer's brightness).
STRENGTH = (" Judge each part's colour strength and value as well as its hue: a whole part drawn clearly more "
            "saturated than the original shows the same part (royal blue for a muted teal, a pure red for a coral, an "
            "orange wood for a brown one), or clearly darker or lighter as a whole (near-black for a mid grey, a satin "
            "grey drawn glossy jet black, a white plastic part drawn grey), is a `colour` fault even where its hue is "
            "right; only a shade that follows the light across a face (a shaded side, a highlight) is the light's.")
# What picture 1 is: NVIDIA's model drawn by the same look as the made model (bench.nvidia_look_step, #159: beside
# NVIDIA's own close-up, another renderer and light, the owner could not tell the drawing from the pipeline, and the
# ask forgave a brightness or shading the model drew as the renderers'), or a pictured case's close-up (#159: the 2099
# cockpit cases, no NVIDIA model; its look is drawn from the camera fitted on that close-up's outline), whose words are
# the ask's as calibrated, kept byte for byte so its kept answers hold.
ORIGINALS = {
    "render": ("You judge, by eye and strictly, a 3D model made again from a picture of an original model. The "
               "object: {words}. Picture 1 is the ORIGINAL (NVIDIA's model). Picture 2 is the MADE model. The two are "
               "drawn by the same renderer from the same camera under the same light on the same backdrop, so the "
               "model is the only difference between them: a part drawn lighter, darker, duller, shinier or shaded "
               "otherwise than the original's is the made model's, never the light's;"),
    "closeup": ("You judge, by eye and strictly, a 3D model made from a picture of an object. The object: {words}. "
                "Picture 1 is the ORIGINAL: the close-up picture the model was made from (an image of the object, not "
                "a render of this model). Picture 2 is the MADE model, drawn on the same backdrop from a camera "
                "fitted to the close-up's outline, so its view may differ by a few degrees and its framing a little. "
                "The two are drawn under different light, so a different brightness, shading, reflection or shadow "
                "alone is no fault;"),
}
# A pictured case's close-up judged as a cut-out of its own (#159), asked after ORIGINALS["closeup"]'s words.
CUTOUT = ("Picture 1 is cut out of a larger picture, and the cut-out itself can be at fault: a torn, ragged, frayed or "
          "soft outline, flaps or fringes of background, shadow or another object left on, a part of the object cut "
          "off. First look at picture 1 alone: list each such fault of the cut-out in `cutout_faults` and give the "
          "cut-out its own verdict in `cutout`: `clean` (none), `slight` (a careful person would let it pass) or "
          "`fault` (one he would point at, such as a torn outline or a flap left on). Then judge the made model on "
          "what it makes of the object: for each ragged, torn or flapping place of its outline, look at the same "
          "place in picture 1; where picture 1's outline is ragged, torn or flapping there too, or the cut-out cut "
          "that part off, the made model only follows the cut-out, which is no fault of the made model (no `edges`, "
          "`shape` or `parts` fault of it). A ragged or torn place picture 1 does not have is the made model's. ")


def opened(path):
    """The picture as RGBA (a picture with no alpha is opaque everywhere)."""
    from PIL import Image
    with Image.open(path) as picture:
        return picture.convert("RGBA")


def framed(*paths):
    """(left, top, right, bottom) as shares of the frame: the box round every object drawn in the pictures (their
    alpha; a picture with none, or filled whole, gives none), PAD added, square (the close-up's frames are) and inside
    the frame; the whole frame when none is drawn."""
    boxes = []
    for path in paths:
        picture = opened(path)
        box = picture.getchannel("A").getbbox()
        if box and box != (0, 0, *picture.size):
            width, height = picture.size
            boxes.append((box[0] / width, box[1] / height, box[2] / width, box[3] / height))
    if not boxes:
        return (0.0, 0.0, 1.0, 1.0)
    left, top = min(box[0] for box in boxes), min(box[1] for box in boxes)
    right, bottom = max(box[2] for box in boxes), max(box[3] for box in boxes)
    half = max(right - left, bottom - top) / 2 + PAD
    middle = ((left + right) / 2, (top + bottom) / 2)
    half = min(half, 0.5)
    across = [min(max(centre, half), 1 - half) for centre in middle]
    return (across[0] - half, across[1] - half, across[0] + half, across[1] + half)


def shown(path, crop):
    """The picture laid on BACKDROP, cut to `crop` (shares of its frame) and drawn SHOWN px on its longest side:
    its PNG bytes."""
    from PIL import Image
    picture = opened(path)
    laid = Image.new("RGBA", picture.size, (*BACKDROP, 255))
    laid.alpha_composite(picture)
    width, height = picture.size
    cut = laid.convert("RGB").crop((round(crop[0] * width), round(crop[1] * height), round(crop[2] * width),
                                    round(crop[3] * height)))
    scale = SHOWN / max(cut.size)
    cut = cut.resize((max(1, round(cut.width * scale)), max(1, round(cut.height * scale))), Image.LANCZOS)
    out = io.BytesIO()
    cut.save(out, format="PNG")
    return out.getvalue()


def drawn(path):
    """Whether anything is drawn in the picture (an opaque pixel)."""
    return opened(path).getchannel("A").getextrema()[1] > 0


def asking_body(words, made, given, pictured=False):
    """The faults ask (a Gemini generateContent body, as claude_code reads one): NVIDIA's render (with `pictured`, the
    close-up the model was made from: ORIGINALS) and the made look (PNG bytes), the object's words, answered as its
    faults and verdicts."""
    kinds = "; ".join(f"`{kind}`: {what}" for kind, what in KINDS.items())
    text = (ORIGINALS["closeup" if pictured else "render"].format(words=words) +
            " the made model's surfaces "
            "come from a library, so a different fine grain of the same material and colour is no fault either. " +
            CHROME +
            (CUTOUT if pictured else "") +
            "Look at every part of the made model against the original and list every visible fault, each with its "
            f"kind, where it is and what is wrong. The kinds: {kinds}. Then give a verdict for every kind: `clean` "
            "(none seen), `slight` (a difference a careful person comparing the two would let pass) or `fault` "
            "(one he would point at). A part the original shows and the made model lacks is a fault, as is text "
            "that cannot be read as the original's." + STRENGTH)
    schema_verdicts = {"type": "OBJECT", "properties": {kind: {"type": "STRING", "enum": list(VERDICTS)}
                                                        for kind in KINDS}, "required": list(KINDS)}
    properties = {} if not pictured else {
        "cutout_faults": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "where": {"type": "STRING"}, "what": {"type": "STRING"}}, "required": ["where", "what"]}},
        "cutout": {"type": "STRING", "enum": list(VERDICTS)}}
    properties.update({
        "faults": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "kind": {"type": "STRING", "enum": list(KINDS)}, "where": {"type": "STRING"},
            "what": {"type": "STRING"}}, "required": ["kind", "where", "what"]}},
        "verdicts": schema_verdicts})
    required = (["cutout_faults", "cutout"] if pictured else []) + ["faults", "verdicts"]
    parts = [{"text": "Picture 1, the ORIGINAL:"}, inline(given), {"text": "Picture 2, the MADE model:"}, inline(made)]
    schema = {"type": "OBJECT", "properties": properties, "required": required}
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def inline(picture):
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(picture).decode()}}


def claude_asks(bodies):
    """{key: the answer's JSON text} of {key: body}, asked of Claude on the subscription (EUR 0) side by side."""
    from score.adapters.models import claude_code
    answers = claude_code.asked(bodies, caller=CALLER)
    for answer in answers.values():
        if isinstance(answer, Exception):
            raise ValueError(f"no picture judgement: {answer}")
    return answers


def compared_body(words, first, second, given, pictured=False):
    """The regression ask (COMPARE): the original (NVIDIA's render, or with `pictured` the close-up) and two made looks
    (PNG bytes) shown as A (`first`) and B (`second`), answered as which is closer to the original."""
    original = "the close-up picture the models were made from" if pictured else \
        "NVIDIA's model, drawn by the same renderer and light as the two"
    parts = [{"text": f"Picture 1, the ORIGINAL ({original}):"}, inline(given), {"text": "Picture A:"}, inline(first),
             {"text": "Picture B:"}, inline(second), {"text": COMPARE.format(words=words)}]
    schema = {"type": "OBJECT", "properties": {
        "a_better": {"type": "STRING"}, "b_better": {"type": "STRING"},
        "closer": {"type": "STRING", "enum": list(CLOSER)}}, "required": ["a_better", "b_better", "closer"]}
    return {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def regression_of(made_first, previous_first):
    """`regressed` and `regression` of the two compare answers (made as A, then the previous as A): regressed when
    both choose the previous look as the closer, so neither the order shown nor one answer's whim decides it; the
    regression says what the previous look had better, in both answers' words."""
    chose = (made_first["closer"], previous_first["closer"])
    if any(choice not in CLOSER for choice in chose):
        raise ValueError(f"the regression judgement chose no look: {chose}")
    regressed = chose == ("B", "A")
    return {"regressed": int(regressed), "closer": {"made_first": chose[0], "previous_first": chose[1]},
            "regression": " | ".join((made_first["b_better"], previous_first["a_better"])) if regressed else ""}


def counted(answer, pictured=False):
    """The measure group of one answer: each kind 1 when its verdict is `fault` (the listed faults, slight ones too,
    are kept beside it), and with `pictured` the close-up's own cut-out (`cutout`) alike; ValueError for an answer
    missing a verdict."""
    verdicts = answer["verdicts"]
    missing = [kind for kind in KINDS if verdicts.get(kind) not in VERDICTS]
    if pictured and answer.get("cutout") not in VERDICTS:
        missing.append("cutout")
    if missing:
        raise ValueError(f"the picture judgement gave no verdict for {missing}: {verdicts}")
    found = {"drawn": 1, **{kind: int(verdicts[kind] == "fault") for kind in KINDS},
             "verdicts": {kind: verdicts[kind] for kind in KINDS},
             "faults": [{key: fault[key] for key in ("kind", "where", "what")} for fault in answer["faults"]]}
    if pictured:
        found.update(cutout=int(answer["cutout"] == "fault"),
                     cutout_faults=[{key: fault[key] for key in ("where", "what")} for fault in answer["cutout_faults"]])
    return found


def looked(words, made, given, previous=None, ask=None, pictured=False):
    """The bench measure group "picture" of one made look (module docstring); `pictured`: `given` is a pictured case's
    close-up, not NVIDIA's render (ORIGINALS); `ask` takes the body and gives the answer's JSON text (a test's), else
    Claude's."""
    paths = [pathlib.Path(made), pathlib.Path(given)] + ([pathlib.Path(previous)] if previous else [])
    crop = framed(*paths)
    pictures = {name: shown(path, crop) for name, path in zip(("made", "given", "previous"), paths)}
    hashes = {name: hashlib.sha256(picture).hexdigest() for name, picture in pictures.items()}
    if not drawn(made):
        return {"drawn": 0, "faults": [{"kind": "parts", "where": "the whole look", "what": "nothing is drawn"}],
                "pictures": hashes}
    bodies = {"faults": asking_body(words, pictures["made"], pictures["given"], pictured)}
    if previous:
        bodies.update(made_first=compared_body(words, pictures["made"], pictures["previous"], pictures["given"],
                                               pictured),
                      previous_first=compared_body(words, pictures["previous"], pictures["made"], pictures["given"],
                                                   pictured))
    answers = {key: json.loads(text) for key, text in
               ({key: ask(body) for key, body in bodies.items()} if ask else claude_asks(bodies)).items()}
    found = counted(answers["faults"], pictured)
    if previous:
        found.update(regression_of(answers["made_first"], answers["previous_first"]))
    return {**found, "pictures": hashes}
