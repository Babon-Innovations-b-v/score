"""The models an output names by content hash (a `<name>.glb: <sha256>` entry), found where the store's machine keeps
them and checked against that hash, each drawn three-quarter from above in its own colours, lit from one side: one
cell per model, its final take when the output names one."""
import hashlib
import pathlib
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from score.dashboard.previews import paint

SHA = re.compile(r"^[0-9a-f]{64}$")
CELL = 200
COLUMNS = 3
MOST_MODELS = 9
MOST_FACES = 40000
BACKGROUND = (238, 236, 230)
INK = (29, 32, 38)
LIGHT = np.array([-0.4, 0.75, 0.55]) / np.linalg.norm([-0.4, 0.75, 0.55])


def named_meshes(document):
    """[(model, file name, sha)] of every record whose entries name a .glb by its hash, its final take first."""
    found = []
    for model, record in (document.items() if isinstance(document, dict) else ()):
        if not isinstance(record, dict):
            continue
        meshes = sorted(((name, sha) for name, sha in record.items()
                         if name.endswith(".glb") and isinstance(sha, str) and SHA.match(sha)),
                        key=lambda entry: not entry[0].endswith("-final.glb"))
        if meshes:
            found.append((model, *meshes[0]))
    return found


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def located(name, sha, roots):
    """The file of that name under a folder of the roots (one level down) whose content is that hash; None."""
    for root in roots:
        for candidate in sorted(pathlib.Path(root).glob(f"*/{name}")):
            if candidate.is_file() and file_hash(candidate) == sha:
                return candidate
    return None


def faces_of(path):
    """(centres, normals, colours 0-255) of a model's faces, at most MOST_FACES of them."""
    import trimesh
    loaded = trimesh.load(str(path), process=False)
    mesh = loaded.to_geometry() if hasattr(loaded, "to_geometry") else loaded
    picked = np.arange(len(mesh.faces))
    if len(picked) > MOST_FACES:
        picked = picked[np.linspace(0, len(picked) - 1, MOST_FACES).astype(int)]
    coloured = mesh.visual.to_color() if hasattr(mesh.visual, "to_color") else mesh.visual
    colours = np.asarray(coloured.vertex_colors, dtype=float)[:, :3]
    corners = mesh.faces[picked]
    return mesh.triangles_center[picked], mesh.face_normals[picked], colours[corners].mean(axis=1)


def cell(path):
    """One model drawn: its faces' centres projected, each shaded by how it faces the light, nearest last."""
    picture = Image.new("RGB", (CELL, CELL), BACKGROUND)
    centres, normals, colours = faces_of(path)
    if not len(centres):
        return picture
    turn = paint.view()
    turned, facing = centres @ turn.T, normals @ turn.T
    shade = 0.35 + 0.65 * np.clip(np.abs(facing @ (turn @ LIGHT)), 0, 1)
    shaded = np.clip(colours * shade[:, None], 0, 255)
    low, high = turned.min(axis=0), turned.max(axis=0)
    scale = (CELL - 24) / max(high[0] - low[0], high[1] - low[1], 1e-6)
    pixels = np.array(picture)
    for at in np.argsort(turned[:, 2]):
        column = int(12 + (turned[at, 0] - low[0]) * scale)
        row = int(CELL - 12 - (turned[at, 1] - low[1]) * scale)
        pixels[max(row - 1, 0):row + 1, max(column - 1, 0):column + 1] = shaded[at]
    return Image.fromarray(pixels)


def picture(document, roots, destination):
    """The sheet of the models a document names that were found; the path, or None when none was found."""
    found = [(model, located(name, sha, roots)) for model, name, sha in named_meshes(document)[:MOST_MODELS]]
    found = [(model, path) for model, path in found if path]
    if not found:
        return None
    rows = -(-len(found) // COLUMNS)
    sheet = Image.new("RGB", (COLUMNS * CELL, rows * CELL), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=11)
    for number, (model, path) in enumerate(found):
        left, top = (number % COLUMNS) * CELL, (number // COLUMNS) * CELL
        sheet.paste(cell(path), (left, top))
        pen.text((left + 4, top + 3), str(model)[:28], fill=INK, font=small)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
