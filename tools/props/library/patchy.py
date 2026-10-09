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
  An island of faces the material round it explains (their colours within WORN_REACH of that material's colours,
  wear and dirt included) is that material: a worn edge is wear on one material, not a second one (worn_as_around).

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

One material cannot be patchy, so a model painted all one material passes all of that; `stripped` is the check
against it (the owner, 2026-10-08: the repaint left models "just stripped of paint", the lander without its gold foil
and yellow, "the rest just got one colour for the entire thing"). It holds the clean close-up's main colours (the
STRIPPED_COLOURS clusters of the seen faces' picture colours, each over MAIN_SHARE of them, lightness weighed down
as shade) against what the faces under each are painted with: a main colour is lost when its faces' material bakes
to no colour within LOST_REACH of it but does hold another main colour, two of the picture's colours collapsed into
one material (a main colour no allowed material reaches is the place's own palette, not a stripped model). A model
fails when its lost main colours cover over LOST_LIMIT of what the camera sees. labels.py runs it on every labelling
(labels.json `stripped`); a model must pass both checks.
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
# Baked: an island of one material whose faces' colours lie, WORN_SHARE of them, within WORN_REACH (Lab distance) of
# the colours of the material it borders most is that material, over WORN_ROUNDS rounds. Worn painted edges show the
# bare metal under them, which the nearest-colour reading called bare steel: the scorched tank dome, labelled one
# material, read 31% stray and the gas bottle 15% (job repaint, 2026-10-08).
WORN_REACH = 10.0
WORN_SHARE = 0.8
WORN_ROUNDS = 3
# Stripped: the close-up's main colours, and how far (Lab, lightness weighed by STRIPPED_WEIGHTS) a material's baked
# colours may lie from one before it is lost.
STRIPPED_COLOURS = 6
MAIN_SHARE = 0.06
STRIPPED_WEIGHTS = np.array([0.15, 1.0, 1.0])
LOST_REACH = 14.0
# A main colour darker than DARK_LIGHTNESS is mostly shade (a white hull's shadowed side): it is held by its hue and
# chroma alone.
DARK_LIGHTNESS = 30.0
LOST_LIMIT = 0.08
# Points of a labelled model's regions laid on a baked model, at most.
BAKED_REGION_POINTS = 400_000
# Stripped: a main colour is paint (not bare metal) past PAINT_CHROMA; two main colours are distinct past DISTINCT.
PAINT_CHROMA = 12.0
DISTINCT = 20.0
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


def score(mesh, labels, parts=None, regions=None):
    """The patchiness numbers of a mesh whose faces each name a material (`labels`, ints), and pass or fail; `parts`,
    each face's part where the labels have them; `regions`, each face's finish region of the close-up where the model
    was painted by them (labels.py --regions): a material edge along a region's edge is the paint the close-up shows
    (the power unit's tape patches), so only edges and faces within one region are judged."""
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
    within = np.ones(len(pairs), dtype=bool)
    if regions is not None:
        regions = np.asarray(regions)
        whole_piece |= whole_parts(island, regions)
        within = regions[pairs[:, 0]] == regions[pairs[:, 1]]
    small = (island_area < STRAY_ISLAND * total) & ~whole_piece
    stray = float(island_area[small].sum() / total)
    mixed = float(areas[mixed_faces(labels, pairs[within])].sum() / total)
    seam = (labels[pairs[:, 0]] != labels[pairs[:, 1]]) & within
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


def labelled_regions(folder, mesh):
    """Each face's finish region where a labels.py folder has regions/region_XX.ply (painted by the close-up's
    regions), else None."""
    import trimesh
    from scipy.spatial import cKDTree
    files = sorted(pathlib.Path(folder).glob("regions/region_*.ply"))
    if not files:
        return None
    meshes = [trimesh.load(path, force="mesh", process=False) for path in files]
    middles = np.vstack([found.triangles_center for found in meshes])
    owner = np.concatenate([np.full(len(found.faces), index) for index, found in enumerate(meshes)])
    return owner[cKDTree(middles).query(mesh.triangles_center)[1]]


def baked_regions(mesh, folder, turn, size):
    """Each face of a baked model's finish region: the labelled folder's regions laid in the kit frame the model
    stands in (stored_parts.kit_frame), each face the region of the nearest; None without regions."""
    import trimesh
    from scipy.spatial import cKDTree
    import stored_parts
    files = sorted(pathlib.Path(folder).glob("regions/region_*.ply"))
    if not files:
        return None
    meshes = [trimesh.load(path, force="mesh", process=False) for path in files]
    total = sum(len(found.faces) for found in meshes)
    stride = max(1, total // BAKED_REGION_POINTS)
    middles = [found.triangles_center[::stride] for found in meshes]
    points = np.vstack(middles)
    owner = np.concatenate([np.full(len(found), index) for index, found in enumerate(middles)])
    return owner[cKDTree(stored_parts.kit_frame(points, turn, size)).query(mesh.triangles_center)[1]]


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


def baked_model(path, place, names, shares=None):
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
    distances[:, twins_left_out(palettes, names, shares)] = np.inf
    mesh = trimesh.Trimesh(geometry.vertices, geometry.faces, process=True)
    # A black face one of the materials bakes to (a screen that is off is ink black) is that material, not unbaked:
    # the CRT television's screen read 15% unbaked (job repaint, 2026-10-08).
    unbaked &= distances.min(1) > WORN_REACH
    return mesh, worn_as_around(mesh, distances), unbaked


def worn_as_around(mesh, distances):
    """Each face's material: the nearest by colour, except that an island of one material (faces joined across
    edges) takes the material it borders most when that material explains WORN_SHARE of its faces' colours within
    WORN_REACH (WORN_ROUNDS rounds): a worn strip along an edge is the wear of the paint round it."""
    pairs = mesh.face_adjacency
    labels = distances.argmin(1)
    for _ in range(WORN_ROUNDS):
        island = islands(labels, pairs)
        across = island[pairs[:, 0]] != island[pairs[:, 1]]
        borders = np.zeros((island.max() + 1, distances.shape[1]))
        for this, that in ((pairs[across, 0], pairs[across, 1]), (pairs[across, 1], pairs[across, 0])):
            np.add.at(borders, (island[this], labels[that]), 1)
        around = borders.argmax(1)
        explained = distances[np.arange(len(labels)), around[island]] <= WORN_REACH
        share = np.bincount(island, weights=explained) / np.bincount(island)
        worn = (borders.sum(1) > 0) & (share >= WORN_SHARE)
        labels = np.where(worn[island], around[island], labels)
    return labels


def twins_left_out(palettes, names, shares):
    """The materials a baked colour cannot tell from another (some of their baked colours within WORN_REACH) that the
    labels use less (`shares`, name to share of the labelled model): a baked face is read as the one used more. The
    power unit's dark panel bakes to the colours of its galvanized steel and the lab desk's paint wears to its bare
    steel; with a crumb of each in the labels, half of each model read as the other (job repaint, 2026-10-09)."""
    if not shares:
        return []
    out = []
    for first in range(len(names)):
        for second in range(len(names)):
            near = np.min(np.linalg.norm(palettes[first][:, None] - palettes[second][None], axis=2)) <= WORN_REACH
            if first != second and near and shares.get(names[first], 0.0) < shares.get(names[second], 0.0):
                out.append(first)
                break
    return out


def with_unbaked(found, mesh, unbaked):
    """A baked model's score with its unbaked share (black faces), failing past UNBAKED_LIMIT."""
    share = float(mesh.area_faces[unbaked].sum() / mesh.area)
    found["unbaked"] = round(share, 4)
    if share > UNBAKED_LIMIT:
        found["faults"].append(f"unbaked {share:.3f} > {UNBAKED_LIMIT}")
        found["pass"] = False
    return found


def colour_clusters(colours):
    """The picture colours' STRIPPED_COLOURS clusters (k-means, seeded, on the weighed axes): each colour's cluster
    and the clusters' centres (Lab)."""
    from scipy.cluster.vq import kmeans2
    scale = np.sqrt(STRIPPED_WEIGHTS)
    centres, cluster = kmeans2(colours * scale, min(STRIPPED_COLOURS, len(colours)), seed=0, minit="++")
    return cluster, centres / scale


def stripped(colours, painted, palettes, names, judged=None, bare=()):
    """The stripped check (module docstring) on a labelled raw model: each face's picture colour (Lab, NaN where
    unseen), its material (an index into `palettes` and `names`), every colour each material bakes to (Lab, as a
    picture shows it), `judged` (each face's material named by the judge, where it was) and the `bare` metals.

    A main colour is lost when it is paint (chroma past PAINT_CHROMA) painted with a bare metal no colour of which
    reaches it; or when its material, not named by the judge for it, holds another main colour and not this one. A
    material the judge named keeps the place's own colour for it (the lab's vinyl is blue where a close-up shows
    grey). A model of one material where the close-up shows distinct main colours is flat and fails too."""
    seen = ~np.isnan(colours[:, 0])
    if seen.sum() < STRIPPED_COLOURS:
        return {"main_colours": 0, "materials_seen": 0, "lost": [], "lost_share": 0.0, "flat": False, "pass": True}
    judged = np.zeros(len(colours), dtype=bool) if judged is None else np.asarray(judged)
    cluster, centres = colour_clusters(colours[seen])
    shares = np.bincount(cluster, minlength=len(centres)) / len(cluster)
    main = np.nonzero(shares >= MAIN_SHARE)[0]
    material = {index: int(np.bincount(painted[seen][cluster == index]).argmax()) for index in main}
    reach = {index: colour_reach(palettes[material[index]], centres[index]) for index in main}
    named = {index: judged[seen][cluster == index].mean() >= 0.5 for index in main}
    lost = []
    for index in main:
        paint_bare = (np.hypot(*centres[index][1:]) > PAINT_CHROMA and names[material[index]] in bare
                      and reach[index] > LOST_REACH)
        held_elsewhere = any(material[other] == material[index] and reach[other] <= LOST_REACH
                             for other in main if other != index)
        collapsed = reach[index] > LOST_REACH and held_elsewhere and not named[index]
        if paint_bare or collapsed:
            lost.append({"share": round(float(shares[index]), 3), "colour": np.round(centres[index], 1).tolist(),
                         "painted": names[material[index]], "reach": round(reach[index], 1),
                         "why": "bare where the close-up shows paint" if paint_bare else "two colours in one material"})
    used = np.bincount(painted[seen], minlength=len(palettes)) / seen.sum()
    distinct = []
    for index in main:
        if all(colour_reach(centres[other][None], centres[index]) > DISTINCT for other in distinct):
            distinct.append(index)
    flat = int((used >= MAIN_SHARE).sum()) == 1 and len(distinct) >= 2
    lost_share = round(min(1.0, sum(entry["share"] for entry in lost)), 3)
    return {"main_colours": int(len(main)), "distinct_colours": len(distinct),
            "materials_seen": int((used >= MAIN_SHARE).sum()), "lost": lost, "lost_share": lost_share, "flat": flat,
            "pass": lost_share <= LOST_LIMIT and not flat}


def colour_reach(palette, colour):
    """How near a material's baked colours come to a picture colour (weighed; a dark colour by hue and chroma)."""
    weights = STRIPPED_WEIGHTS * ([0.0, 1.0, 1.0] if colour[0] < DARK_LIGHTNESS else 1.0)
    return float(np.sqrt((((palette - colour) ** 2) * weights).sum(1)).min())


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
        regions = labelled_regions(arguments.path, mesh)
    else:
        names = [name for name in arguments.materials.split(",") if name]
        mesh, labels, unbaked = baked_model(arguments.path, arguments.place, names)
    found = score(mesh, labels, parts, regions if arguments.way == "labels" else None)
    if arguments.way == "baked":
        found = with_unbaked(found, mesh, unbaked)
    found["names"] = names
    print(json.dumps(found))
    raise SystemExit(0 if found["pass"] else 1)


if __name__ == "__main__":
    main()
