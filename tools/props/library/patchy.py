"""How patchy a generated piece's paint is (job paint, 2026-10-08: "a ton of models that have these black surfaces
mixed through the nice paint", the owner, on the greenhouse chair's seat split into blue vinyl and black blotches).

    ~/.farm-factory-props/env/bin/python tools/props/library/patchy.py labels <labels folder> [--place hub]
    ~/.farm-factory-props/env/bin/python tools/props/library/patchy.py baked <model.gltf> --place hub \
        --materials vinyl_seat,rubber

A piece is painted per face with library materials; patchy paint is material that changes where the shape does not.
Both ways measure the same thing on a mesh whose faces each name one material:

- `labels`: the labelled full model labels.py wrote (one .ply per material), the faces the bake paints from. This is
  the check before any bake: `route.py plan` refuses a generated kind whose labels fail it.
- `baked`: a baked game model, each face named by the material its baked colour lies nearest (every colour the
  material bakes to: its token, worn to bare metal and dirtied, as sweep.py's palette), sampled at four points a face.

The numbers, every share of the model's area:
- `stray`: area in islands of one material (faces of it joined across shared edges) each under STRAY_ISLAND of the
  model's area, unless the island is a whole piece of the shape by itself or, where the labels name their parts
  (labels.py's parts/), whole parts (a separate knob or a screw is a part, not a blotch).
- `mixed`: area of faces whose material differs from most of their neighbours' (speckle, a shade-split seam).
- `soft_seams`: how much material boundary runs over smooth surface (neighbours within SOFT_DEGREES of each other)
  rather than along a crease, as its length over the square root of the model's area: paint by picture colour splits
  a flat seat along its light and shade; paint by part follows the part's edges.
- `unbaked` (baked only): area left black by the bake (no ray reached it).
A model fails on stray > STRAY_LIMIT or mixed > MIXED_LIMIT or soft_seams > SOFT_LIMIT, or unbaked > UNBAKED_LIMIT.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Limits set from the whole game's pipeline models measured on 2026-10-08 (job paint), against renders of each.
STRAY_ISLAND = 0.01
STRAY_LIMIT = 0.03
MIXED_LIMIT = 0.02
SOFT_DEGREES = 20.0
SOFT_LIMIT = 6.0
# Baked: a face whose colour is under UNBAKED_LEVEL (0..255) in every channel was never reached by the bake (no library
# colour is that black); a model fails past UNBAKED_LIMIT of its area so (every generated piece's back, 2026-10-08).
UNBAKED_LEVEL = 12
UNBAKED_LIMIT = 0.01
# A labelled raw model is large (up to a million faces); its vertices are welded at this many decimals.
WELD_DIGITS = 6


def adjacency(mesh):
    """The face pairs sharing an edge and the angle between each pair's normals, in degrees."""
    return mesh.face_adjacency, np.degrees(mesh.face_adjacency_angles)


def components(count, pairs):
    """Each face's connected component over `pairs` (faces joined across shared edges)."""
    graph = sparse.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(count, count))
    return connected_components(graph, directed=False)[1]


def islands(labels, pairs):
    """Each face's island: its component over the pairs whose two faces share a material."""
    same = pairs[labels[pairs[:, 0]] == labels[pairs[:, 1]]]
    return components(len(labels), same)


def mixed_faces(labels, pairs):
    """Faces whose material differs from most of their edge neighbours'."""
    count = len(labels)
    both = np.r_[pairs[:, 0], pairs[:, 1]]
    other = np.r_[pairs[:, 1], pairs[:, 0]]
    differs = np.bincount(both, weights=(labels[both] != labels[other]).astype(float), minlength=count)
    neighbours = np.bincount(both, minlength=count)
    return differs * 2 > np.maximum(neighbours, 1)


def whole_parts(island, parts):
    """Per island, whether it is made of whole parts: every part it touches lies in it alone."""
    pairs = np.unique(np.stack([island, parts], 1), axis=0)
    islands_of_part = np.bincount(pairs[:, 1])
    alone = islands_of_part[pairs[:, 1]] == 1
    found = np.ones(island.max() + 1, dtype=bool)
    np.logical_and.at(found, pairs[:, 0], alone)
    return found


def score(mesh, labels, parts=None):
    """The patchiness numbers of a mesh whose faces each name a material (`labels`, ints), and pass or fail; `parts`,
    each face's part where the labels have them."""
    labels = np.asarray(labels)
    areas = mesh.area_faces
    total = float(areas.sum())
    pairs, angles = adjacency(mesh)
    island = islands(labels, pairs)
    piece = components(len(labels), pairs)
    island_area = np.bincount(island, weights=areas)
    # An island that is a whole piece of the shape (its faces exactly one piece's) is a part of its own, not a blotch.
    piece_of_island = np.zeros(island.max() + 1, dtype=int)
    piece_of_island[island] = piece
    piece_area = np.bincount(piece, weights=areas)
    whole_piece = np.isclose(island_area, piece_area[piece_of_island])
    if parts is not None:
        whole_piece |= whole_parts(island, np.asarray(parts))
    small = (island_area < STRAY_ISLAND * total) & ~whole_piece
    stray = float(island_area[small].sum() / total)
    mixed = float(areas[mixed_faces(labels, pairs)].sum() / total)
    seam = labels[pairs[:, 0]] != labels[pairs[:, 1]]
    edges = mesh.face_adjacency_edges
    lengths = np.linalg.norm(mesh.vertices[edges[:, 0]] - mesh.vertices[edges[:, 1]], axis=1)
    soft = float(lengths[seam & (angles < SOFT_DEGREES)].sum() / np.sqrt(total))
    shares = np.bincount(labels, weights=areas) / total
    faults = [text for text, failed in ((f"stray {stray:.3f} > {STRAY_LIMIT}", stray > STRAY_LIMIT),
                                         (f"mixed {mixed:.3f} > {MIXED_LIMIT}", mixed > MIXED_LIMIT),
                                         (f"soft seams {soft:.1f} > {SOFT_LIMIT}", soft > SOFT_LIMIT)) if failed]
    return {"faces": int(len(labels)), "materials": int((shares > 0).sum()), "islands": int(len(island_area)),
            "small_islands": int(small.sum()), "stray": round(stray, 4), "mixed": round(mixed, 4),
            "soft_seams": round(soft, 2), "pass": not faults, "faults": faults}


def labelled_model(folder):
    """A labels.py folder's full model as one welded mesh and each face's material index; the material names."""
    mesh, labels, names, _ = labelled_parts(folder)
    return mesh, labels, names


def labelled_parts(folder):
    """labelled_model, and each face's part where the folder has parts/part_XX.ply (else None)."""
    import trimesh
    from scipy.spatial import cKDTree
    names, meshes = [], []
    for path in sorted(pathlib.Path(folder).glob("*.ply")):
        meshes.append(trimesh.load(path, force="mesh", process=False))
        names.append(path.stem)
    if not meshes:
        raise SystemExit(f"{folder}: no labelled parts (.ply)")
    labels = np.concatenate([np.full(len(mesh.faces), index) for index, mesh in enumerate(meshes)])
    joined = trimesh.util.concatenate(meshes)
    welded = np.round(joined.vertices, WELD_DIGITS)
    _, first, inverse = np.unique(welded, axis=0, return_index=True, return_inverse=True)
    mesh = trimesh.Trimesh(joined.vertices[first], inverse.reshape(-1)[joined.faces], process=False)
    keep = mesh.nondegenerate_faces()
    mesh.update_faces(keep)
    parts = None
    part_files = sorted(pathlib.Path(folder).glob("parts/part_*.ply"))
    if part_files:
        part_meshes = [trimesh.load(path, force="mesh", process=False) for path in part_files]
        middles = np.vstack([part.triangles_center for part in part_meshes])
        owner = np.concatenate([np.full(len(part.faces), index) for index, part in enumerate(part_meshes)])
        parts = owner[cKDTree(middles).query(mesh.triangles_center)[1]]
    return mesh, labels[keep], names, parts


def material_colours(place, names):
    """Per material name, every colour (L*a*b*) it bakes to in `place`: its token, worn toward its bare metal and its
    second colour, dirtied with the place's dirt (sweep.py's mixes)."""
    import library
    import sweep
    specs = dict(library.by_library(place), **library.resolved(place))
    found = []
    for name in names:
        spec = specs[name]
        dirt = np.array(spec["dirt_colour"])
        colours = []
        for colour in [np.array(spec["colour"])] + [np.array(spec[key]) for key in ("bare", "second") if key in spec]:
            for share in sweep.MIXES[:3]:  # dirt never covers a surface over half: further mixes read as the dirt
                colours.append(colour * (1 - share) + dirt * share)
        if "bare" in spec:
            for share in sweep.MIXES:
                colours.append(np.array(spec["colour"]) * (1 - share) + np.array(spec["bare"]) * share)
        found.append(sweep.lab(np.array(colours)))
    return found


def baked_model(path, place, names):
    """A baked game model as one welded mesh, each face's material index among `names` (the material whose baked
    colours lie nearest the median of the face's colour at its middle and halfway to each corner) and whether the
    face is unbaked (black: no bake ray reached it)."""
    import trimesh
    import sweep
    scene = trimesh.load(path, force="scene")
    geometry = next(iter(scene.geometry.values()))
    picture = np.asarray(geometry.visual.material.baseColorTexture.convert("RGB"))
    uv = np.asarray(geometry.visual.uv)[geometry.faces]  # (faces, 3, 2)
    middle = uv.mean(1, keepdims=True)
    points = np.concatenate([middle, (uv + middle) / 2], axis=1)  # (faces, 4, 2)
    height, width = picture.shape[:2]
    column = np.clip((points[..., 0] % 1.0 * width).astype(int), 0, width - 1)
    row = np.clip(((1.0 - points[..., 1] % 1.0) * height).astype(int), 0, height - 1)
    sampled = picture[row, column]  # (faces, 4, 3)
    unbaked = np.median(sampled.max(2), axis=1) < UNBAKED_LEVEL
    colours = sweep.lab(sweep.linear_of(sampled.reshape(-1, 3))).reshape(len(uv), 4, 3)
    colours = np.median(colours, axis=1)
    palettes = material_colours(place, names)
    distances = np.stack([np.min(np.linalg.norm(colours[:, None, :] - palette[None], axis=2), axis=1)
                          for palette in palettes], axis=1)
    mesh = trimesh.Trimesh(geometry.vertices, geometry.faces, process=True)
    return mesh, distances.argmin(1), unbaked


def with_unbaked(found, mesh, unbaked):
    """A baked model's score with its unbaked share (black faces), failing past UNBAKED_LIMIT."""
    share = float(mesh.area_faces[unbaked].sum() / mesh.area)
    found["unbaked"] = round(share, 4)
    if share > UNBAKED_LIMIT:
        found["faults"].append(f"unbaked {share:.3f} > {UNBAKED_LIMIT}")
        found["pass"] = False
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("way", choices=("labels", "baked"))
    parser.add_argument("path", type=pathlib.Path)
    parser.add_argument("--place", default="hub")
    parser.add_argument("--materials", default="", help="baked: the materials the piece was labelled with, by comma")
    arguments = parser.parse_args()
    parts = None
    if arguments.way == "labels":
        mesh, labels, names, parts = labelled_parts(arguments.path)
    else:
        names = [name for name in arguments.materials.split(",") if name]
        mesh, labels, unbaked = baked_model(arguments.path, arguments.place, names)
    found = score(mesh, labels, parts)
    if arguments.way == "baked":
        found = with_unbaked(found, mesh, unbaked)
    found["names"] = names
    print(json.dumps(found))
    raise SystemExit(0 if found["pass"] else 1)


if __name__ == "__main__":
    main()
