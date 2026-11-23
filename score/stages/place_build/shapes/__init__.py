"""A place_build scene's made shapes that read wrong, each told for a remake (#149; the 2099 session's play-runs,
2026-11-20: "lumpy seats, sausage pipes"; the owner's rule of 2026-10-18 keeps a picture-made model's geometry, so a
geometry that does not read as its thing is remade, never kept). Judged from each object's model file, in its own
frame, never from a mark the agent sets.

    faults(stage, place) -> {object: [fault]}       every made object whose shape reads wrong
    measured(asset) -> Shape                         a model file's flat share and its section's swell
    shape_of(points, faces) -> Shape                 the same of triangles in hand

Only a made shape is judged: an entry whose shape a picture made (a take, Pixal3D, TRELLIS.2: finished.picture_made)
or that code built from its concept crop (CROP_WORDS in its provenance). A library kit or a scan is what it is. What a
thing is comes from its entry's id (the words below), so a desk is held to a desk's faces and a pipe to a pipe's run:

- `a sausage`: a pipe (PIPE_WORDS) long enough to have a run (LONG times its width or more) whose section swells
  along it: the spread of its section's width over the middle of its run (SWELL_SPAN) is over SWELL as a share of
  its mean. A library pipe (Poly Haven's modular pipes, Kenney's station pipe) and the hangar's code-built pipes
  measure 0.01 to 0.02, NVIDIA's adopted SimReady pipes 0.035 (pipe_plastic_black_b06) and 0.066
  (pipe_plastic_gray_b08, its sockets: the 0.05 bar called it a sausage, #163 calibration); the cockpit's
  crop-built red pipes, which the play-runs saw as sausages, 0.11.
- `a lump`: a hard made thing (HARD_WORDS: a console, a desk, a cabinet) whose surface holds too few flat faces: the
  share of its area facing one of its FULLEST fullest of DIRECTIONS directions is under FLAT. A made desk or
  console that reads as one measures 0.33 to 0.77; the cockpit's pilot console, its seats grown into lumps, 0.21.
  A seat is not held to it: upholstery is curved (a made office chair that reads as one measures 0.16).
"""
import dataclasses
import json
import pathlib

import numpy as np
from pxr import Usd, UsdGeom

from score.stages.place_build import finished

FAULT = "misread shape"
PIPE_WORDS = ("pipe", "duct", "conduit")
HARD_WORDS = ("console", "desk", "table", "cabinet", "locker", "rack", "shelf", "crate", "terminal",
              "workstation", "door")
CROP_WORDS = ("from its concept crop",)  # a shape built in code from the concept's crop (shapes_first)
LONG = 6.0  # a pipe's run over its width (twice its section's mean radius) before its swell is judged
SWELL = 0.08  # a pipe's section's width spread over its run, as a share of its mean
SWELL_SPAN = 0.8  # the middle of the run judged: a pipe's ends (a flange, a bend, a cap) are not its run
SLICES = 12  # the run cut in this many slices, each one width measured
WIDTH_PERCENTILE = 90  # a slice's width: this percentile of its points' distance from the run's axis
FLAT = 0.25  # a hard thing's least share of area facing one of its fullest directions
DIRECTIONS, FULLEST = 4000, 20  # Fibonacci directions a face's normal falls in; the fullest that count
SAMPLES, SEED = 4000, 7  # surface points drawn by area to measure a section
CHUNK = 20000  # faces matched to the directions at a time (20000 by 4000 floats, 640 MB)


@dataclasses.dataclass
class Shape:
    flat: float  # share of area facing one of the FULLEST fullest directions
    run: float  # the run's length over its width
    swell: float  # the spread of the section's width over the run's middle, as a share of its mean


def triangles(asset):
    """(points (N, 3), triangles (T, 3)) of every shown mesh of a model file, in the file's own frame."""
    stage = Usd.Stage.Open(str(asset))
    cache = UsdGeom.XformCache()
    points, faces, offset = [], [], 0
    for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        if not (prim.IsA(UsdGeom.Mesh) and finished.shown(prim)):
            continue
        mesh = UsdGeom.Mesh(prim)
        corners = np.asarray(mesh.GetPointsAttr().Get() or [], dtype=np.float64)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=np.int64)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=np.int64)
        if not len(corners) or not len(counts):
            continue
        frame = np.array(cache.GetLocalToWorldTransform(prim))
        points.append(corners @ frame[:3, :3] + frame[3, :3])
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        for corner in range(1, int(counts.max()) - 1):
            fanned = counts > corner + 1
            faces.append(np.stack([indices[starts[fanned]], indices[starts[fanned] + corner],
                                   indices[starts[fanned] + corner + 1]], 1) + offset)
        offset += len(corners)
    if not faces:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    return np.concatenate(points), np.concatenate(faces)


def fibonacci(count):
    """`count` directions spread evenly over the sphere."""
    middle = np.arange(count) + 0.5
    polar, around = np.arccos(1 - 2 * middle / count), np.pi * (1 + 5 ** 0.5) * middle
    return np.stack([np.cos(around) * np.sin(polar), np.sin(around) * np.sin(polar), np.cos(polar)], 1)


def flat_share(normals, areas):
    """The share of area whose faces face one of the FULLEST fullest of DIRECTIONS directions (the faces taken CHUNK
    at a time: a model of a million faces against every direction at once would hold 32 GB)."""
    directions = fibonacci(DIRECTIONS).T
    nearest = np.concatenate([(normals[start:start + CHUNK] @ directions).argmax(1)
                              for start in range(0, len(normals), CHUNK)])
    held = np.bincount(nearest, weights=areas, minlength=DIRECTIONS)
    return float(np.sort(held)[::-1][:FULLEST].sum() / areas.sum())


def surface_points(corners, areas):
    """SAMPLES points drawn on the triangles by area (corners (T, 3, 3))."""
    draw = np.random.default_rng(SEED)
    picked = draw.choice(len(areas), SAMPLES, p=areas / areas.sum())
    first, second = draw.random(SAMPLES), draw.random(SAMPLES)
    folded = first + second > 1
    first[folded], second[folded] = 1 - first[folded], 1 - second[folded]
    base = corners[picked, 0]
    return (base + first[:, None] * (corners[picked, 1] - base)
            + second[:, None] * (corners[picked, 2] - base))


def section(points):
    """(the run over its width, the swell): the widths of SLICES slices across the middle of the points' longest
    axis."""
    centre = points.mean(0)
    _, axes = np.linalg.eigh(np.cov((points - centre).T))
    axis = axes[:, -1]
    along = (points - centre) @ axis
    length = along.max() - along.min()
    trim = (1 - SWELL_SPAN) / 2 * length
    edges = np.linspace(along.min() + trim, along.max() - trim, SLICES + 1)
    widths = []
    for low, high in zip(edges[:-1], edges[1:]):
        inside = points[(along >= low) & (along < high)]
        if len(inside) < 10:
            continue
        across = inside - inside.mean(0)
        across = across - np.outer(across @ axis, axis)
        widths.append(np.percentile(np.linalg.norm(across, axis=1), WIDTH_PERCENTILE))
    widths = np.array(widths)
    if not len(widths) or widths.mean() <= 0:
        return 0.0, 0.0
    return float(length / (2 * widths.mean())), float(widths.std() / widths.mean())


MEASURED = {}  # {model file: its Shape}


def measured(asset):
    """The model file's Shape (cached by its path), or None when it shows no triangle."""
    asset = str(pathlib.Path(asset).resolve())
    if asset not in MEASURED:
        MEASURED[asset] = shape_of(*triangles(asset))
    return MEASURED[asset]


def shape_of(points, faces):
    """The Shape of triangles (points (N, 3), faces (T, 3)), or None when none has an area."""
    corners = points[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    doubled = np.linalg.norm(crossed, axis=1)
    kept = doubled > 0
    if not kept.any():
        return None
    areas = doubled[kept] / 2
    run, swell = section(surface_points(corners[kept], areas))
    return Shape(flat=flat_share(crossed[kept] / doubled[kept, None], areas), run=run, swell=swell)


def made(record):
    """Whether the entry's shape was made for its place: from a picture, or in code from its concept crop."""
    told = json.dumps((record or {}).get("provenance", {}).get("made_with", []))
    return finished.picture_made(record) or any(words in told for words in CROP_WORDS)


def entry_words(record):
    return str((record or {}).get("id", "")).lower()


def shape_faults(record, shape):
    """The faults of a made entry's Shape: a pipe that swells, a hard thing with too few flat faces."""
    words, found = entry_words(record), []
    if any(word in words for word in PIPE_WORDS) and shape.run >= LONG and shape.swell > SWELL:
        found.append({"fault": FAULT, "kind": "a sausage",
                      "why": (f"a pipe whose section swells along its run ({shape.swell:.2f} of its width, over "
                              f"{SWELL}): remake it from a library pipe or a straight one")})
    if any(word in words for word in HARD_WORDS) and shape.flat < FLAT:
        found.append({"fault": FAULT, "kind": "a lump",
                      "why": (f"a hard thing with too few flat faces ({shape.flat:.2f} of its area facing one of its "
                              f"{FULLEST} fullest directions, under {FLAT}): remake it")})
    return found


def faults(stage, place):
    """{object: [fault]} of every made object of /<place>/Objects whose shape reads wrong."""
    found = {}
    objects = stage.GetPrimAtPath(f"/{place}/Objects")
    for prim in objects.GetChildren() if objects else ():
        record = finished.record_of(prim)
        asset = finished.model_file(prim)
        if not made(record) or not asset or not asset.exists():
            continue
        shape = measured(asset)
        told = shape_faults(record, shape) if shape else []
        if told:
            found[prim.GetName()] = [dict(fault, model=finished.text(prim, "score:library")) for fault in told]
    return found
