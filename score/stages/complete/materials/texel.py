"""Texture detail near cameras against the room's kit: an object a camera sees from close by is drawn with fewer
texture pixels a metre than the walls and floor around it (the audit of 2026-10-18: 52 to 89 px/m on the big models
against 285 to 567 on the walls).

Measured: each laid model's texture pixels a metre of its surface (`density`: the square root of its texture area in
pixels over its surface area in square metres, the laid scale counted), and how near the nearest camera that has it in
sight comes (assets.nearest). Judged: the room's kit is the median of its code-built kit pieces' densities; an
object seen within NEAR metres with under SHARE of it is a finding. A place that lays no code-built kit piece (the
outdoor places, the streets) is held to the world's kit instead: the median over every place's code-built kit pieces.
"""
import functools
import statistics

import numpy as np
from PIL import Image

from score.stages.complete.materials import meshes

RULE = "soft texture near a camera"
# Seen this near (metres), an object is drawn large enough that its texture detail shows beside the walls'.
NEAR = 3.0
# Under this share of the kit's density, an object's texture reads blurred beside the walls around it.
SHARE = 0.5


@functools.cache
def picture_size(path):
    """(width, height) of a picture file."""
    with Image.open(path) as picture:
        return picture.size


def mesh_texels(mesh):
    """(texture pixels, square metres) of one drawn mesh's painted faces."""
    if mesh.corners_uv is None:
        return 0.0, 0.0
    sizes = np.zeros(len(mesh.triangles))
    whole = mesh.pictures.get("")
    if whole:
        sizes[:] = np.prod(picture_size(whole))
    for name, faces in mesh.finishes.items():
        if name in mesh.pictures:
            sizes[faces] = np.prod(picture_size(mesh.pictures[name]))
    painted = sizes > 0
    if not painted.any():
        return 0.0, 0.0
    flat = mesh.corners_uv[painted].reshape(-1, 2)
    order = np.arange(len(flat)).reshape(-1, 3)
    texels = float((meshes.triangle_areas(flat, order) * sizes[painted]).sum())
    surface = float(meshes.triangle_areas(mesh.points, mesh.triangles[painted]).sum())
    return texels, surface


def density(drawn, area_scale=1.0):
    """Texture pixels a metre of a model's surface, laid at a scale that multiplies its areas by `area_scale`; None
    for a model with no painted surface."""
    totals = np.array([mesh_texels(mesh) for mesh in drawn] or [(0.0, 0.0)])
    texels, surface = totals.sum(axis=0)
    return float(np.sqrt(texels / (surface * area_scale))) if surface > 0 else None


def is_kit(entry):
    """True for a code-built kit piece (a wall band, a floor plate): the reference the room's other objects meet."""
    return entry.get("kind") == "code" and entry.get("made") == "kit piece" and entry.get("px_per_m")


def kit_reference(objects):
    """The median density of the place's code-built kit pieces, or None when it lays none."""
    found = [entry["px_per_m"] for entry in objects if is_kit(entry)]
    return statistics.median(found) if found else None


def world_reference(evidences):
    """The median density of every code-built kit piece of the places measured, or None."""
    found = [entry["px_per_m"] for evidence in evidences for entry in evidence["objects"] if is_kit(entry)]
    return statistics.median(found) if found else None


def sentence(entry, reference, whose):
    """A finding in words."""
    return (f"{entry['model']} is drawn with {entry['px_per_m']:.0f} texture pixels a metre and a camera sees it from "
            f"{entry['near']:.1f} m; {whose} has {reference:.0f}, so it reads blurred beside it")


def findings(evidence, world=None):
    """One finding a model seen within NEAR metres with under SHARE of the room's kit density (the world's kit's,
    `world`, in a place with no kit), nearest first."""
    reference, whose = kit_reference(evidence["objects"]), "the room's kit"
    if reference is None:
        reference, whose = world, "the world's kit (this place lays no code-built kit piece)"
    if reference is None:
        return []
    soft = {}
    for entry in evidence["objects"]:
        if is_kit(entry) or entry.get("px_per_m") is None or entry.get("near") is None:
            continue
        if entry["near"] <= NEAR and entry["px_per_m"] < SHARE * reference:
            kept = soft.get(entry["model"])
            if kept is None or entry["near"] < kept["near"]:
                soft[entry["model"]] = entry
    return [{"rule": RULE, "prim": entry["prim"], "model": entry["model"], "px_per_m": round(entry["px_per_m"], 1),
             "kit_px_per_m": round(reference, 1), "near": round(entry["near"], 2),
             "sentence": sentence(entry, reference, whose)}
            for entry in sorted(soft.values(), key=lambda entry: entry["near"])]
