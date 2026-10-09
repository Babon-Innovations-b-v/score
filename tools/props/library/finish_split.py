"""Split a generated model's parts in 3D along the finishes its close-up shows, so every finish is a part of its own
(job repaint, 2026-10-09, round five: painting by the close-up's 2D regions gave flat blobs, and the owner's rule is
paint by parts from the surface library). The close-up's regions only say which finish each seen face shows
(`finish`, a surface index, -1 unseen); the cut is made on the mesh.

In a part, a finish over SPLIT_LEAST of its seen area (and MODEL_LEAST of the model's) gets a part of its own. A smooth
region of the part (faces joined across folds under labels.REGION_DEGREES) that one finish clearly holds (no other
over MINOR of its seen area) goes to that finish whole, so a cut follows a panel line or a fold where there is one; where a smooth
surface carries finishes of several colour families (gold and silver foil on a round hull; one_per_family joins
those of one family) the finishes are diffused over it for DIFFUSION_ROUNDS
and each face takes the strongest, which leaves a smooth edge rather than the picture's ragged one. What no seen face
reaches takes the part's base finish: the plainest (least coloured) finish holding BASE_LEAST of the part's seen area,
a hull under its foil patches; a back the camera never saw is not given a patch's finish.
"""
import numpy as np
from scipy import sparse

SPLIT_LEAST = 0.08
MODEL_LEAST = 0.005
# A smooth region goes whole to its largest finish when it holds SMALL of the model's area and no other finish holds
# MINOR of its seen area; a smaller one, or one shared by finishes, is cut by diffusion (small creased regions deciding
# alone left the wreck's hull in specks).
SMALL = 0.003
MINOR = 0.12
BASE_LEAST = 0.2
DIFFUSION_ROUNDS = 120


def kept_finishes(finish, part_of, part, areas, total):
    """The finishes a part splits into: each over SPLIT_LEAST of its seen area and MODEL_LEAST of the model's; its
    largest when none is."""
    members = (part_of == part) & (finish >= 0)
    if not members.any():
        return []
    held = np.bincount(finish[members], weights=areas[members])
    share = held / held.sum()
    kept = [int(index) for index in np.nonzero((share >= SPLIT_LEAST) & (held >= MODEL_LEAST * total))[0]]
    return kept or [int(share.argmax())]


def base_finish(finish, part_of, part, kept, areas, colourfulness):
    """The part's base finish: the least coloured kept finish holding BASE_LEAST of its seen area, else the largest."""
    members = (part_of == part) & np.isin(finish, kept)
    if not kept or not members.any():
        return None
    held = {index: areas[members & (finish == index)].sum() for index in kept}
    total = sum(held.values())
    plain = [index for index in kept if held[index] >= BASE_LEAST * total]
    return min(plain, key=lambda index: colourfulness[index]) if plain else max(held, key=held.get)


def diffused(neighbours, seeds, rounds=DIFFUSION_ROUNDS):
    """Seed scores (faces x finishes) spread over the faces' neighbour graph; each face's strongest, -1 for none."""
    current = seeds.copy()
    for _ in range(rounds):
        spread = neighbours @ current
        reached = (spread.sum(1) > 0)[:, None]
        current = np.maximum(seeds, spread / np.maximum(spread.sum(1, keepdims=True), 1e-12) * reached)
    return np.where(current.sum(1) > 0, current.argmax(1), -1)


def one_per_family(votes, areas, family):
    """A smooth surface's votes (its faces' finishes, -1 unseen) with each colour family's finishes joined into the
    family's largest there: two finishes of one family across a smooth surface are its light and shade or its wear
    (the wreck's grey hull read as bare steel and white paint in specks), not two finishes; an edge across a smooth
    surface is a change of colour family."""
    seen = votes >= 0
    held = np.bincount(votes[seen], weights=areas[seen])
    joined = votes.copy()
    present = np.nonzero(held)[0]
    for name in {family[index] for index in present}:
        members = [index for index in present if family[index] == name]
        largest = max(members, key=lambda index: held[index])
        joined[seen & np.isin(votes, members)] = largest
    return joined


def split(mesh, part_of, finish, smooth, colourfulness, family):
    """Each face's new part and the (old part, finish) each new part is; `smooth` is each face's smooth region,
    `colourfulness` each finish's chroma and `family` each finish's colour family (surface_check.family)."""
    areas = mesh.area_faces
    total = float(areas.sum())
    pairs = mesh.face_adjacency
    result = np.full(len(mesh.faces), -1)
    for part in np.unique(part_of):
        members = part_of == part
        kept = kept_finishes(finish, part_of, part, areas, total)
        if not kept:
            continue
        base = base_finish(finish, part_of, part, kept, areas, colourfulness)
        result[members] = base
        votes = np.where(np.isin(finish, kept) & members, finish, -1)
        ambiguous = np.zeros(len(mesh.faces), dtype=bool)
        index = np.nonzero(members)[0]
        index = index[np.argsort(smooth[index], kind="stable")]
        bounds = np.flatnonzero(np.diff(smooth[index])) + 1
        for group in np.split(index, bounds):  # each smooth region of the part, as face indices
            if not (votes[group] >= 0).any():
                continue
            votes[group] = one_per_family(votes[group], areas[group], family)
            seen = group[votes[group] >= 0]
            held = np.bincount(votes[seen], weights=areas[seen])
            second = np.sort(held)[-2] if (held > 0).sum() > 1 else 0.0
            if areas[group].sum() >= SMALL * total and second < MINOR * held.sum():
                result[group] = int(held.argmax())
            else:
                ambiguous[group] = True
        if ambiguous.any():
            index = np.nonzero(ambiguous)[0]
            position = np.full(len(mesh.faces), -1)
            position[index] = np.arange(len(index))
            inner = (position[pairs[:, 0]] >= 0) & (position[pairs[:, 1]] >= 0)
            first, second = position[pairs[inner, 0]], position[pairs[inner, 1]]
            graph = sparse.coo_matrix((np.ones(2 * len(first)), (np.r_[first, second], np.r_[second, first])),
                                      shape=(len(index), len(index))).tocsr()
            columns = {value: number for number, value in enumerate(kept)}
            seeds = np.zeros((len(index), len(kept)))
            seeded = votes[index] >= 0
            seeds[np.nonzero(seeded)[0], [columns[value] for value in votes[index][seeded]]] = 1.0
            strongest = diffused(graph, seeds)
            result[index] = np.where(strongest >= 0, np.array(kept)[np.maximum(strongest, 0)], base)
    pair_of = sorted({(int(part), int(value)) for part, value in zip(part_of, result) if value >= 0})
    lookup = {pair: number for number, pair in enumerate(pair_of)}
    new_parts = np.array([lookup.get((int(part), int(value)), -1) for part, value in zip(part_of, result)])
    return new_parts, pair_of
