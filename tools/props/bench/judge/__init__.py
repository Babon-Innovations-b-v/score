"""The prop benchmark's picture judge (#184, PRD #159): the owner's own way of judging made a check. Each made model's
look (branch B's `look` step, #182: the finish as the bake paints it, from the close-up's camera) is held by eye to
NVIDIA's input render of the same object, and, when given, to the same object's look in the previous round.

    looked(words, made, given, previous=None, ask=None) -> the bench measure group "picture":
        {"drawn": 1 or 0, <each of KINDS>: 1 when a fault of that kind is seen else 0, "regressed": 1 or 0 (only with
         `previous`), "verdicts": {kind: clean | slight | fault}, "faults": [{kind, where, what}], "regression": text,
         "pictures": {name: sha256 of the picture as shown}}
    shown(path, crop) -> the picture's PNG bytes as the judge sees it
    framed(*paths)     -> the crop (shares of the frame) round every object drawn

`made` is the look (look.png, RGBA), `given` NVIDIA's render (the render step's rgba.png, true alpha), `previous` the
previous round's look (look.png, or any picture of it from the same camera). Each is laid on the close-up's light grey
backdrop (bench.BACKDROP), cut to the same frame round both objects and drawn at SHOWN px, so the three are seen alike.
A look with nothing drawn (no opaque pixel) is `drawn` 0 and asked nothing.

The ask is one Claude call on the subscription (score/adapters/models/claude_code, EUR 0), its answer a structured
JSON: every visible fault of the made model against NVIDIA's, its kind of KINDS, and a verdict per kind (clean;
slight: a difference a careful eye lets pass, such as the renderers' light, a library grain for NVIDIA's; fault),
and with a previous look whether the made one looks worse than it. An answer is kept by the hash of the model and the
body (claude_code.CACHE), whose pictures are these bytes, so the same pictures are never asked twice. The bars are in
measures.BARS: no kind at `fault`, no regression, a drawn look.
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
SHOWN = 768  # the longest side of each picture as the judge sees it
PAD = 0.04  # the share of the frame kept round the objects when they are cut to it
BACKDROP = (214, 214, 214)  # the close-up's backdrop (tools/props/bench/run/bench.py BACKDROP)
CALLER = "bench-picture"


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


def asking_body(words, made, given, previous=None):
    """The ask (a Gemini generateContent body, as claude_code reads one): NVIDIA's render, the made look and the
    previous round's look (PNG bytes), the object's words, answered as its faults and verdicts."""
    kinds = "; ".join(f"`{kind}`: {what}" for kind, what in KINDS.items())
    text = (f"You judge, by eye and strictly, a 3D model made again from a picture of an original model. The object: "
            f"{words}. Picture 1 is the ORIGINAL (NVIDIA's model, rendered). Picture 2 is the MADE model, drawn from "
            "the same camera on the same backdrop. The two are drawn by different renderers under different light, "
            "so a different brightness, shading, reflection or shadow alone is no fault; the made model's surfaces "
            "come from a library, so a different fine grain of the same material and colour is no fault either. "
            "Look at every part of the made model against the original and list every visible fault, each with its "
            f"kind, where it is and what is wrong. The kinds: {kinds}. Then give a verdict for every kind: `clean` "
            "(none seen), `slight` (a difference a careful person comparing the two would let pass) or `fault` "
            "(one he would point at). A part the original shows and the made model lacks is a fault, as is text "
            "that cannot be read as the original's.")
    schema_verdicts = {"type": "OBJECT", "properties": {kind: {"type": "STRING", "enum": list(VERDICTS)}
                                                        for kind in KINDS}, "required": list(KINDS)}
    properties = {
        "faults": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "kind": {"type": "STRING", "enum": list(KINDS)}, "where": {"type": "STRING"},
            "what": {"type": "STRING"}}, "required": ["kind", "where", "what"]}},
        "verdicts": schema_verdicts}
    required = ["faults", "verdicts"]
    parts = [{"text": "Picture 1, the ORIGINAL:"}, inline(given), {"text": "Picture 2, the MADE model:"}, inline(made)]
    if previous is not None:
        parts += [{"text": "Picture 3, the same object made in the PREVIOUS round, from the same camera:"},
                  inline(previous)]
        text += (" Last, compare picture 2 with picture 3, each against the original: `regressed` is true when the "
                 "made model (picture 2) looks worse against the original than the previous round's (picture 3) in "
                 "any way you would point at (a fault it did not have, a part or text it had right and lost, a colour "
                 "further off), even where it is better in others; `regression` says what got worse, or is empty.")
        properties.update(regressed={"type": "BOOLEAN"}, regression={"type": "STRING"})
        required += ["regressed", "regression"]
    schema = {"type": "OBJECT", "properties": properties, "required": required}
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def inline(picture):
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(picture).decode()}}


def claude_ask(body):
    """The ask sent to Claude on the subscription (EUR 0), its answer's JSON text."""
    from score.adapters.models import claude_code
    answer = claude_code.asked({"picture": body}, caller=CALLER)["picture"]
    if isinstance(answer, Exception):
        raise ValueError(f"no picture judgement: {answer}")
    return answer


def counted(answer, regression_asked):
    """The measure group of one answer: each kind 1 when its verdict is `fault` (the listed faults, slight ones too,
    are kept beside it); ValueError for an answer missing a kind's verdict."""
    verdicts = answer["verdicts"]
    missing = [kind for kind in KINDS if verdicts.get(kind) not in VERDICTS]
    if missing:
        raise ValueError(f"the picture judgement gave no verdict for {missing}: {verdicts}")
    found = {"drawn": 1, **{kind: int(verdicts[kind] == "fault") for kind in KINDS},
             "verdicts": {kind: verdicts[kind] for kind in KINDS},
             "faults": [{key: fault[key] for key in ("kind", "where", "what")} for fault in answer["faults"]]}
    if regression_asked:
        found.update(regressed=int(bool(answer["regressed"])), regression=answer.get("regression", ""))
    return found


def looked(words, made, given, previous=None, ask=None):
    """The bench measure group "picture" of one made look (module docstring); `ask` takes the body and gives the
    answer's JSON text (a test's), else Claude's."""
    paths = [pathlib.Path(made), pathlib.Path(given)] + ([pathlib.Path(previous)] if previous else [])
    crop = framed(*paths)
    pictures = {name: shown(path, crop) for name, path in zip(("made", "given", "previous"), paths)}
    hashes = {name: hashlib.sha256(picture).hexdigest() for name, picture in pictures.items()}
    if not drawn(made):
        return {"drawn": 0, "faults": [{"kind": "parts", "where": "the whole look", "what": "nothing is drawn"}],
                "pictures": hashes}
    body = asking_body(words, pictures["made"], pictures["given"], pictures.get("previous"))
    answer = json.loads((ask or claude_ask)(body))
    return {**counted(answer, previous is not None), "pictures": hashes}
