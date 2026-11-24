"""A made model's front decided from its close-up's content (#192, PRD #159): fit.headed turns a model by its outline
from the close-up's camera, and a box-like object's outline cannot tell front from back (tc4r's desk: its 90 and 270
degree outlines 0.551 and 0.538, laid a half turn off with its cable hole in the wrong corner; its fridge: four turns
within 0.007, its glass door on its side). Each turn the outline leaves open is drawn with the model's own texture
(TRELLIS.2 paints what the picture showed) from the close-up style's camera, framed on the close-up's opaque box, and
one ask (Claude on the subscription, EUR 0, kept by its body's hash, claude_code.CACHE) picks the drawing whose
content (a hole, a door, a handle, a panel, a colour) sits where the close-up shows it. Drawn flat-colour numbers were
tried first and could not: over the desk's pixels its legs' shading outweighs a cable hole, so the plain colour
agreement picked the wrong half turn (0.62 against 0.59).

    picked(words, raw, picture, cut, turn, down, matrices, ask=None) -> (index into matrices, the answer's reason)
    drawn(mesh, texels, matrix, crop, size, turn, down)              -> RGB uint8 picture (SHOWN on its longer side)
"""
import base64
import io
import json

import numpy as np

from . import fit

FIELD = 30.0  # vertical degrees of the close-up's camera: the close-up style's (tools/props/bench/run FOV)
SHOWN = 512  # pixels across each picture's longer side as asked
MARGIN = 0.06  # the share of the object's box kept round it in each picture asked
BACKDROP = np.array([214, 214, 214], dtype=float)  # the close-up style's light grey (bench BACKDROP)
FRAMING_STEPS = 12
AMBIENT = 0.45  # a drawing's light: this much everywhere, the rest by the face's turn to a light over the camera
CALLER = "make-front"


def textured(path):
    """(the model's mesh, its base colour picture as RGB 0-1 or None, its base colour factor RGB 0-1)."""
    import trimesh
    mesh = trimesh.load(str(path), force="mesh")
    material = getattr(mesh.visual, "material", None)
    picture = getattr(material, "baseColorTexture", None)
    factor = getattr(material, "baseColorFactor", None)
    factor = np.ones(3) if factor is None else np.asarray(factor, dtype=float)[:3]
    factor = factor / 255.0 if factor.max() > 1.0 else factor
    texels = None if picture is None else np.asarray(picture.convert("RGB"), dtype=float) / 255.0
    return mesh, texels, factor


def eye_framing(points, right, up, back, focal, box, size):
    """The eye from which `points` seen along -`back` (`focal` pixels a unit away) span the opaque `box` (left, top,
    right, bottom pixels) of a picture `size` (width, height): moved along the view to match the box's larger side and
    across it to match its middle (surfaces/close_up_fit.framed's way)."""
    target, distance = points.mean(0), 3.0 * np.ptp(points, 0).max()
    for _ in range(FRAMING_STEPS):
        eye = target + back * distance
        relative = points - eye
        depth = np.maximum(-(relative @ back), 1e-9)
        seen = np.c_[relative @ right / depth * focal + size[0] / 2, size[1] / 2 - relative @ up / depth * focal]
        low, high = seen.min(0), seen.max(0)
        spans = (high - low) / np.maximum(np.array([box[2] - box[0], box[3] - box[1]], dtype=float), 1.0)
        middle = (low + high) / 2 - [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]
        distance *= float(spans.max())
        target = target + (middle[0] * right - middle[1] * up) * distance / focal
    return target + back * distance


def crop_of(cut):
    """(left, top, right, bottom) pixels round the cut-out's opaque box, MARGIN of its larger side kept round it,
    square-free; and the opaque box itself."""
    rows, columns = np.nonzero(cut)
    box = (int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1)
    grow = MARGIN * max(box[2] - box[0], box[3] - box[1])
    return (box[0] - grow, box[1] - grow, box[2] + grow, box[3] + grow), box


def pixel_grid(crop):
    """The picture places ([column, row], pixel middles) of a SHOWN-across grid over `crop`, and its shape."""
    width, height = crop[2] - crop[0], crop[3] - crop[1]
    step = max(width, height) / SHOWN
    columns, rows = np.meshgrid(crop[0] + (np.arange(round(width / step)) + 0.5) * step,
                                crop[1] + (np.arange(round(height / step)) + 0.5) * step)
    return columns, rows


def drawn(mesh, texels, factor, matrix, crop, box, size, turn, down):
    """The model laid by `matrix` (4x4, Y up) as the close-up's camera (turned `turn`, looking down `down`, FIELD
    high, framed on its opaque `box` in a picture `size` wide and high) sees it over `crop`: its own base colour,
    lit by AMBIENT and a light over the camera, on BACKDROP; RGB uint8."""
    import trimesh
    vertices = fit.applied(matrix, np.asarray(mesh.vertices, dtype=float))
    laid = trimesh.Trimesh(vertices, mesh.faces, process=False)
    right, up = fit.view_axes(turn, down)
    back = np.cross(right, up)
    focal = size[1] / 2 / np.tan(np.radians(FIELD) / 2)
    eye = eye_framing(np.asarray(laid.convex_hull.vertices), right, up, back, focal, box, size)
    columns, rows = pixel_grid(crop)
    ways = ((columns.ravel() - size[0] / 2) / focal)[:, None] * right \
        + ((size[1] / 2 - rows.ravel()) / focal)[:, None] * up - back
    ways /= np.linalg.norm(ways, axis=1, keepdims=True)
    faces, rays, met = laid.ray.intersects_id(np.repeat(eye[None], len(ways), 0), ways, multiple_hits=False,
                                              return_locations=True)
    colour = np.tile(BACKDROP / 255.0, (len(ways), 1))
    paint = np.tile(factor, (len(faces), 1))
    uv = getattr(mesh.visual, "uv", None)
    if texels is not None and uv is not None and len(faces):
        weights = trimesh.triangles.points_to_barycentric(laid.triangles[faces], met)
        where = np.einsum("ij,ijk->ik", weights, np.asarray(uv)[mesh.faces[faces]])
        height, width = texels.shape[:2]
        paint = paint * texels[np.clip(np.round((1 - where[:, 1] % 1.0) * (height - 1)), 0, height - 1).astype(int),
                               np.clip(np.round((where[:, 0] % 1.0) * (width - 1)), 0, width - 1).astype(int)]
    light = up + back
    light /= np.linalg.norm(light)
    facing = np.abs(laid.face_normals[faces] @ light)
    colour[rays] = paint * (AMBIENT + (1 - AMBIENT) * facing)[:, None]
    return np.round(np.clip(colour, 0, 1).reshape(*columns.shape, 3) * 255).astype(np.uint8)


def close_up_shown(rgba, crop):
    """The close-up (RGBA 0-255) laid on BACKDROP over `crop`, sampled on the drawings' grid; RGB uint8."""
    columns, rows = pixel_grid(crop)
    height, width = rgba.shape[:2]
    inside = (columns >= 0) & (columns < width) & (rows >= 0) & (rows < height)
    taken = rgba[np.clip(rows.astype(int), 0, height - 1), np.clip(columns.astype(int), 0, width - 1)].astype(float)
    alpha = np.where(inside, taken[..., 3] / 255.0, 0.0)[..., None]
    return np.round(taken[..., :3] * alpha + BACKDROP * (1 - alpha)).astype(np.uint8)


def png(picture):
    from PIL import Image
    encoded = io.BytesIO()
    Image.fromarray(picture).save(encoded, "PNG")
    return encoded.getvalue()


def inline(picture):
    return {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(picture).decode()}}


def asking_body(words, close_up, drawings):
    """The ask (a Gemini generateContent body, as claude_code reads one): the close-up and each drawing (PNG bytes),
    answered as the number of the drawing turned as the close-up shows the object."""
    parts = [{"text": "The PICTURE the model was made from:"}, inline(close_up)]
    for number, drawing in enumerate(drawings, 1):
        parts += [{"text": f"Drawing {number}:"}, inline(drawing)]
    text = (f"A 3D model of an object was made from the picture, and it lies turned some way about its upright axis. "
            f"The object: {words}. Each drawing shows the same model from the picture's camera, turned another way "
            "about its upright axis, in its own paint (flat light, so its brightness and shading differ from the "
            "picture's). Its outline alone cannot tell these turns apart. Pick the drawing in which the model faces "
            "the camera as the object in the picture does: the same features on the same sides and corners (a hole "
            "or grommet, a door or glass panel, a handle, a hinge side, a screen, a label, a coloured panel, a "
            "brace), not the one whose outline or shading looks most alike. `pick` is its number; `reason` names "
            "the features you matched.")
    schema = {"type": "OBJECT", "properties": {"reason": {"type": "STRING"}, "pick": {"type": "INTEGER"}},
              "required": ["reason", "pick"]}
    return {"contents": [{"role": "user", "parts": [*parts, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def claude_ask(body):
    """The ask sent to Claude on the subscription (EUR 0), its answer's JSON text."""
    from score.adapters.models import claude_code
    answer = claude_code.asked({"front": body}, caller=CALLER)["front"]
    if isinstance(answer, Exception):
        raise ValueError(f"no front answer: {answer}")
    return answer


def picked(words, raw, picture, cut, turn, down, matrices, ask=None):
    """(the index of the one of `matrices` (4x4, each laying the raw model `raw` a turn the outline leaves open) the
    close-up `picture` (RGBA path; `cut` its opaque pixels) shows, its reason): each drawn (`drawn`) and asked;
    `ask` takes the body and gives the answer's JSON text (a test's), else Claude's. An answer naming no drawing is
    a ValueError."""
    from PIL import Image
    rgba = np.asarray(Image.open(picture).convert("RGBA"))
    crop, box = crop_of(cut)
    mesh, texels, factor = textured(raw)
    size = (cut.shape[1], cut.shape[0])
    drawings = [png(drawn(mesh, texels, factor, matrix, crop, box, size, turn, down)) for matrix in matrices]
    answer = json.loads((ask or claude_ask)(asking_body(words, png(close_up_shown(rgba, crop)), drawings)))
    number = int(answer["pick"])
    if not 1 <= number <= len(matrices):
        raise ValueError(f"the front answer picks drawing {number} of {len(matrices)}: {answer}")
    return number - 1, str(answer.get("reason", ""))
