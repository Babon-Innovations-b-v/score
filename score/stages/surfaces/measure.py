"""The g-texture method's measures, never a judgement by eye: the texture's finish per face (texture_reference: the
raw texture's measured colour, metalness and roughness decide where the judge's regions disagree), each part's
mixing of two finishes (part_measures), and the unlit close-up's regions and questions (region_pixels,
materials_of). The surface test of 2026-10-11 (rounds 1 to 4) measured its arms with this module; only what the
chosen arm, g-texture, uses is kept.
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PROPS = HERE.parents[2] / "tools/props"  # the prop tool chain this stage reads (labels, the judge, the cloud)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROPS))
sys.path.insert(0, str(PROPS / "library"))
import labels  # noqa: E402
import regions  # noqa: E402
import split_compare  # noqa: E402

# A painted part mixes two finishes when its second finish holds this share of its seen area; parts under
# PART_LEAST of the seen area are not counted.
MIX_SHARE = 0.2
PART_LEAST = 0.01
# The texture decides (owner, 2026-10-11, round 4): the whole-model reference follows the raw texture's own measured
# finish where the judge's regions say otherwise. Each surface the reference names gets an exemplar of the texture's
# colour, metalness and roughness (multiview.exemplar over multiview.exemplar_faces: its core, middle lightness, main
# hue). Two surfaces whose exemplars lie under SEPARABLE apart (the root of the summed squared differences, each over
# the root of the two spreads squared) are one finish to the texture, named by the larger: the power unit's
# dark_panel and galvanized_dull lie 1.06 apart (L* 46 and 44, metal 0.11 and 0.04, roughness 0.90 and 0.92) and the
# views name its body one or the other at random (t15-240 97% dark_panel, t15-180 68% galvanized_dull), the lander's
# bare_steel and galvanized_dull 0.4; its hull_white_old lies 2.4 to 2.7 from both. Then each seen face takes the
# finish its texture says where its texture lies FAR (squared, in spreads, over the five features: chi-square's 0.999
# point) from its own finish's exemplar and NEAR (its 0.95 point) another's, and half its smoothed neighbourhood says
# so: chair-b's back shell and seat skirt (roughness 0.56, metal 0.14) read as its frame's steel (0.59, 0.14), not its
# cushion's vinyl (0.78, 0.21), which the judge's "backrest" region named them. A likeliest-finish rule moved 11% of
# the lander to glass and lamp lens (independent Gaussians make nearly every face sure of something); a finish under
# TARGET_LEAST of the seen area takes no face this way (the lander's glass, 1%, drew 8.5% of its gold foil: a small
# exemplar's tight spreads say little about what else the texture holds).
TEXTURE_FEATURES = 5  # multiview.FEATURES' L*, a*, b*, metal, rough: the texture's, not the solid's thickness
SEPARABLE = 2.0
FAR, NEAR = 20.5, 11.07
TARGET_LEAST = 0.05


def materials_of(entry):
    return labels.allowed_materials(entry["library_places"][0], entry["kind"], [])


def picture_path(work, name, take):
    """A reference picture's file (RGBA): the unlit copy, or the raw model's own texture from the close-up's camera
    (multiview.py's view c, unlit)."""
    return work / f"seg-{name}" / f"{take}.png"


def region_pixels(work, name, take):
    """Each pixel's region on a reference picture (-1 off the object)."""
    inside = np.asarray(split_compare.picture(take))[..., 3] > 127
    return regions.region_map(regions.masks_of(work / f"seg-{name}" / "masks" / f"{take}.npz"), inside)


def separation(first, second):
    """How far apart two exemplars ((centre, spread) per feature) lie: the root of the summed squared centre
    differences, each over the root of the two spreads squared, over the features both know."""
    known = ~np.isnan(first[0]) & ~np.isnan(second[0])
    apart = (first[0][known] - second[0][known]) / np.hypot(first[1][known], second[1][known])
    return float(np.sqrt((apart ** 2).sum()))


def distinct_faces(mesh, colour, members, elsewhere):
    """A finish's exemplar faces (multiview.exemplar_faces), its hue group the one farther from the hue (a*, b*) of
    the faces `elsewhere`, not the larger: the power unit's gold-named faces are 61% grey and 30% gold (chroma 40 to
    80), and the larger group gave its exemplar the body's grey."""
    import multiview
    kept = multiview.exemplar_faces(mesh, colour, members)
    chosen = np.nonzero(kept)[0]
    larger = multiview.main_hue(colour[chosen])
    if larger.all() or not elsewhere.any():
        return kept
    around = np.nanmedian(colour[elsewhere, 1:], axis=0)
    groups = [chosen[larger], chosen[~larger]]
    hues = [np.nanmedian(colour[group, 1:], axis=0) for group in groups]
    wider = int(np.argmax([np.linalg.norm(hue - around) for hue in hues]))
    found = np.zeros(len(members), dtype=bool)
    found[groups[wider]] = True
    return found


def texture_finishes(mesh, surface, features):
    """The reference's surfaces grouped as the texture tells them apart: {surface: the surface naming its group},
    each group's exemplar, and each pair's separation."""
    import multiview
    seen = surface != None  # noqa: E711 (an object array's None)
    areas = mesh.area_faces
    names = sorted(set(surface[seen].tolist()), key=lambda name: -areas[surface == name].sum())
    chosen = {name: distinct_faces(mesh, features[:, :3], surface == name, seen & (surface != name))
              for name in names}
    exemplars = {name: multiview.exemplar(features, chosen[name]) for name in names}
    apart = {(first, second): separation(exemplars[first], exemplars[second])
             for number, first in enumerate(names) for second in names[number + 1:]}
    group = {name: name for name in names}
    for (first, second), distance in sorted(apart.items(), key=lambda item: item[1]):
        if distance < SEPARABLE:
            larger, smaller = sorted((group[first], group[second]), key=names.index)
            group = {name: larger if head == smaller else head for name, head in group.items()}
    heads = sorted(set(group.values()), key=names.index)
    joined = {head: multiview.exemplar(features, np.any([chosen[name] for name in names if group[name] == head],
                                                        axis=0)) for head in heads}
    return group, joined, apart


def distances(features, exemplar):
    """Each face's squared distance from an exemplar: the summed squared differences over the features it knows, each
    over the exemplar's spread (NaN where the face knows none)."""
    centre, spread = exemplar
    usable = ~np.isnan(centre)
    terms = ((features[:, usable] - centre[usable]) / spread[usable]) ** 2
    known = (~np.isnan(terms)).any(1)
    return np.where(known, np.nansum(terms, axis=1), np.nan)


def texture_reference(mesh, surface, features):
    """The whole-model reference following the texture (TEXTURE_FEATURES of multiview.face_features): surfaces the
    texture cannot tell apart become the larger one; a seen face whose texture lies FAR from its own finish's exemplar
    and NEAR another's takes that other, where most of its neighbourhood says the same (smoothed); unseen faces stay
    None. The surface per face, and a record (groups, separations, the seen area regrouped and moved)."""
    features = features[:, :TEXTURE_FEATURES]
    seen = surface != None  # noqa: E711
    group, exemplars, apart = texture_finishes(mesh, surface, features)
    heads = list(exemplars)
    found = surface.copy()
    found[seen] = [group[name] for name in surface[seen]]
    regrouped = found.copy()
    far = np.stack([distances(features, exemplars[head]) for head in heads], axis=1)
    own = np.full(len(surface), -1)
    own[seen] = [heads.index(name) for name in found[seen]]
    wants = np.zeros((len(surface), len(heads)))
    areas = mesh.area_faces
    small = np.array([areas[found == head].sum() < TARGET_LEAST * areas[seen].sum() for head in heads])
    for number in range(len(heads)):
        others = np.where((np.arange(len(heads)) == number) | small, np.inf, far)
        nearest = np.nanargmin(np.nan_to_num(others, nan=np.inf), axis=1)
        moving = (own == number) & (far[:, number] > FAR) & (others[np.arange(len(surface)), nearest] < NEAR)
        wants[np.nonzero(moving)[0], nearest[moving]] = 1.0
    current = wants
    neighbours = labels.neighbour_matrix(mesh)
    for _ in range(labels.SMOOTH_ROUNDS):
        current = 0.5 * wants + 0.5 * (neighbours @ current) / np.maximum(neighbours.sum(1).A1, 1e-12)[:, None]
    moved = seen & (current.max(1) >= 0.5)
    found[moved] = np.array(heads, dtype=object)[current[moved].argmax(1)]
    record = {"groups": group, "separations": {f"{first} | {second}": round(distance, 2)
                                               for (first, second), distance in apart.items()},
              "regrouped_share": round(float(areas[seen & (regrouped != surface)].sum() / areas[seen].sum()), 3),
              "moved_share": round(float(areas[seen & (found != regrouped)].sum() / areas[seen].sum()), 3)}
    return found, record


def whole_finishes(surface_names):
    """Each face's finish index on the whole-model reference (a finish being one surface name), -1 unseen."""
    seen = surface_names != None  # noqa: E711 (an object array's None)
    names = sorted(set(surface_names[seen].tolist()))
    found = np.full(len(surface_names), -1)
    found[seen] = [names.index(name) for name in surface_names[seen]]
    return found


def finish_table(areas, finish, part_of):
    """Seen area per (painted part, finish)."""
    seen = finish >= 0
    table = np.zeros((int(part_of.max()) + 1, int(finish.max()) + 1))
    np.add.at(table, (part_of[seen], finish[seen]), areas[seen])
    return table


def part_measures(areas, finish, part_of):
    """Against one reference's finishes per face (-1 unseen): the finishes that get parts of their own
    (split_compare.finishes_owned), the seen area in pure parts, and the parts mixing two finishes (of those
    counted)."""
    owned, missed = split_compare.finishes_owned(areas, finish, part_of)
    table = finish_table(areas, finish, part_of)
    sizes = table.sum(1)
    counted = sizes >= PART_LEAST * sizes.sum()
    ordered = np.sort(table, axis=1)[:, ::-1]
    purity = ordered[:, 0] / np.maximum(sizes, 1e-12)
    second = (ordered[:, 1] if table.shape[1] > 1 else np.zeros(len(sizes))) / np.maximum(sizes, 1e-12)
    return {"owned": len(owned), "finishes": len(owned) + len(missed),
            "pure": round(float(sizes[purity >= split_compare.OWN_PURITY].sum() / sizes.sum()), 3),
            "mixing": int((counted & (second >= MIX_SHARE)).sum()), "parts": int(counted.sum())}
