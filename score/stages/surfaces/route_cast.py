"""The finish route's light local views (no Blender, no picture model): a model ray cast on the processor with
trimesh and Embree, orthographic, from several sides and the close-up's direction, at SIDE pixels square. Each view
gives the face under every pixel (-1 off the model) and, from the model's own texture, its colour there; pictures are
flat colour, shaded only by the angle to the view so the form reads (no light, wear, bump or pattern).

The model is welded by position (its UV seams joined, its faces kept in the file's order), centred on its box and
scaled to a largest side of 1, Y up (glTF). The close-up's direction is the model's front, +Z (glTF's forward).
"""
import pathlib
import sys

import numpy as np

LIBRARY_TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools/props/library"
if str(LIBRARY_TOOLS.parent) not in sys.path:
    sys.path.append(str(LIBRARY_TOOLS.parent))  # appended: the prop tools must not shadow the framework's
if str(LIBRARY_TOOLS) not in sys.path:
    sys.path.append(str(LIBRARY_TOOLS))

SIDE = 384
ELEVATION = 15.0
# The views, name: (turn round Y in degrees from the front, elevation in degrees). "front" is the close-up's.
VIEWS = {"front": (0.0, ELEVATION), "front_left": (60.0, ELEVATION), "back_left": (120.0, ELEVATION),
         "back": (180.0, ELEVATION), "back_right": (240.0, ELEVATION), "front_right": (300.0, ELEVATION),
         "top": (0.0, 75.0)}
FRONT = "front"
MARGIN = 1.05
SHADE_LEAST = 0.35  # the share of a face's colour it keeps seen edge-on (the pictures' shading only)


class Model:
    """A model's welded faces with what its texture needs: each face's three corners' UVs (NaN without), its piece
    and each piece's colour picture (sRGB 0-255, or None) and colour factor (0-1 RGBA)."""

    def __init__(self, mesh, corner_uv, piece_of, pictures, factors):
        self.mesh, self.corner_uv, self.piece_of = mesh, corner_uv, piece_of
        self.pictures, self.factors = pictures, factors


def piece_colouring(geometry):
    """(colour picture or None, colour factor 0-1, UVs or None) of one loaded piece."""
    visual = geometry.visual
    material = getattr(visual, "material", None)
    picture = getattr(material, "baseColorTexture", None) or getattr(material, "image", None)
    factor = getattr(material, "baseColorFactor", None)
    factor = np.ones(4) if factor is None else np.asarray(factor, dtype=float) / (255.0 if np.max(factor) > 1 else 1)
    if picture is None and getattr(visual, "kind", None) == "face":
        factor = np.asarray(visual.face_colors, dtype=float).mean(0) / 255.0
    uv = getattr(visual, "uv", None)
    pixels = None if picture is None else np.asarray(picture.convert("RGB"), dtype=np.uint8)
    return pixels, factor, (None if uv is None or pixels is None else np.asarray(uv, dtype=float))


def loaded(path):
    """The model at `path` (any file trimesh reads as a scene) as a Model, normalised."""
    import trimesh
    scene = trimesh.load(str(path), force="scene", process=False)
    vertices, faces, corners, pieces, pictures, factors = [], [], [], [], [], []
    offset = 0
    for index, node in enumerate(scene.graph.nodes_geometry):
        transform, name = scene.graph[node]
        geometry = scene.geometry[name]
        picture, factor, uv = piece_colouring(geometry)
        vertices.append(trimesh.transform_points(np.asarray(geometry.vertices, dtype=float), transform))
        faces.append(np.asarray(geometry.faces) + offset)
        corners.append(uv[geometry.faces] if uv is not None else np.full((len(geometry.faces), 3, 2), np.nan))
        pieces.append(np.full(len(geometry.faces), index))
        pictures.append(picture)
        factors.append(factor)
        offset += len(geometry.vertices)
    every = np.concatenate(vertices)
    low, high = every.min(0), every.max(0)
    every = (every - (low + high) / 2) / max(float((high - low).max()), 1e-9)
    mesh = trimesh.Trimesh(every, np.concatenate(faces), process=False)
    mesh.merge_vertices()
    return Model(mesh, np.concatenate(corners), np.concatenate(pieces), pictures, factors)


def camera(view):
    """(eye way, right, up) unit vectors of a view: the eye lies along `eye way` from the model's middle."""
    turn, elevation = (np.radians(angle) for angle in VIEWS[view])
    eye = np.array([np.sin(turn) * np.cos(elevation), np.sin(elevation), np.cos(turn) * np.cos(elevation)])
    right = np.cross([0.0, 1.0, 0.0], eye)
    right /= np.linalg.norm(right)
    return eye, right, np.cross(eye, right)


def rays(mesh, view, side=SIDE):
    """The view's ray origins (one a pixel, row 0 at the top) and their one way, framing the model's bounding
    sphere."""
    eye, right, up = camera(view)
    reach = float(np.linalg.norm(mesh.vertices, axis=1).max()) * MARGIN
    steps = (np.arange(side) + 0.5) / side * 2 - 1
    across, down = np.meshgrid(steps, -steps)
    origins = (eye * reach * 2)[None, None] + across[..., None] * right * reach + down[..., None] * up * reach
    return origins.reshape(-1, 3), np.repeat(-eye[None], side * side, axis=0)


def cast(mesh, view, side=SIDE):
    """(the face under each pixel, -1 off the model; the point each pixel's ray meets, NaN off it)."""
    origins, ways = rays(mesh, view, side)
    hit_faces, hit_rays, points = mesh.ray.intersects_id(origins, ways, multiple_hits=False, return_locations=True)
    faces = np.full(side * side, -1, dtype=np.int64)
    met = np.full((side * side, 3), np.nan)
    faces[hit_rays], met[hit_rays] = hit_faces, points
    return faces.reshape(side, side), met.reshape(side, side, 3)


def texture_colours(model, faces, points):
    """Each pixel's colour from the model's own texture (sRGB 0-255; 0 off the model): its face's UV at the point
    its ray met, sampled from its piece's picture, times its colour factor."""
    import trimesh
    found = np.zeros((*faces.shape, 3))
    seen = faces >= 0
    hit = faces[seen]
    triangles = model.mesh.triangles[hit]
    weights = trimesh.triangles.points_to_barycentric(triangles, points[seen])
    uv = np.einsum("nk,nkd->nd", weights, model.corner_uv[hit])
    colours = np.zeros((len(hit), 3))
    for piece, picture in enumerate(model.pictures):
        mine = model.piece_of[hit] == piece
        factor = model.factors[piece][:3]
        if picture is None or np.isnan(uv[mine]).any():
            colours[mine] = factor * 255.0
            continue
        height, width = picture.shape[:2]
        column = np.clip(((uv[mine, 0] % 1.0) * width).astype(int), 0, width - 1)
        row = np.clip(((1.0 - uv[mine, 1] % 1.0) * height).astype(int), 0, height - 1)
        colours[mine] = picture[row, column] * factor
    found[seen] = colours
    return np.clip(found, 0, 255).astype(np.uint8)


def shading(mesh, faces, view):
    """Each pixel's shade from its face's angle to the view (SHADE_LEAST edge-on, 1 face-on); 0 off the model."""
    eye, _, _ = camera(view)
    shade = np.zeros(faces.shape)
    seen = faces >= 0
    shade[seen] = SHADE_LEAST + (1 - SHADE_LEAST) * np.abs(mesh.face_normals[faces[seen]] @ eye)
    return shade


def picture(colours, faces, shade=None):
    """An RGBA picture of per-pixel colours (sRGB 0-255), clear off the model, shaded when `shade` is given."""
    from PIL import Image
    painted = colours.astype(float) * (shade[..., None] if shade is not None else 1.0)
    found = np.zeros((*faces.shape, 4), dtype=np.uint8)
    found[..., :3] = np.clip(painted, 0, 255).astype(np.uint8)
    found[..., 3] = np.where(faces >= 0, 255, 0)
    return Image.fromarray(found)


def face_painted(face_colours, faces):
    """Per-pixel colours of a painting by face (face_colours: one sRGB 0-255 colour a face); 0 off the model."""
    found = np.zeros((*faces.shape, 3), dtype=np.uint8)
    seen = faces >= 0
    found[seen] = face_colours[faces[seen]]
    return found


def lab_of(colours):
    """sRGB 0-255 colours to CIELAB (labels.lab)."""
    import labels
    return labels.lab(np.asarray(colours, dtype=float) / 255.0)
