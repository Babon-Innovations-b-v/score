"""The finish route's split row (free, on this PC's processor): each listed take's faces split by finish, the list's
labels voted across every view. In each view a face takes the region most of its pixels show (route_views) and that
region's label there (route_list); the views vote (squared_votes: each view's vote on a face weighed by how squarely
it sees it, the cosine between the face's normal and the way to the eye, the close-up's front counting FRONT_VOTE).
The close-up laid on the model (route_views.CLOSE_UP, where the views row laid it) votes as the front does, and a
finish only it labels, one no view of the texture shows, or a lit one (finish_parts.LIT_FAMILIES: a texture cannot
show light), takes the faces it labels it on (close_up_only).

Every face gets exactly one finish, or its take is a gap, named (owner, 2026-10-20): a face some view sees whose
regions no view labelled is unassigned, a gap once its share of the area passes UNASSIGNED_MOST; under it each takes
its nearest labelled face's finish, as an unseen face does (walked), its share still recorded. Faces whose views disagree (no finish over half their votes) are a
split decision, never a gap (owner, 2026-10-28: the views disagreed on 1.2 to 5.8% of eleven takes, one colour region
over several finishes, and the old 1% limit was never measured): each takes the finish its views weigh most, a tie
the finish of the part round it (walked); their share is still recorded. A face no view can see (the inside of a raw
model's shell, out of every camera's reach, is no gap) takes the finish of the voted face nearest it in space, the
outer side a wall's thickness behind it (behind; walked along the surface it took the rim's finish, #173), and a part
the views hardly vote on joins its finish's nearest voted part (hidden_joined); the
finishes are then smoothed, each stray (an island under patchy.py's STRAY_ISLAND of a finish that has a larger one, or
of one whose islands cover that much only together) given the finish round it (finish_parts.without_strays) and
crumbs joined (finish_parts.cleaned, merged_islands), each island one part. A take whose paint is still patchy (patchy.score, each part its own region, as the paint measures,
each island of a detail finish a part of its own: finish_parts.patchiness) is a gap, named, before anything is baked.

The split decides by the labels alone (the paper, "Surfaces: the finish route": the views are split into colour
regions only so the list can label them). No colour is judged here: a finish's surface is held against its colour
in the close-up after the split, by the parts row's check and the bake check (route_parts, bake_check), never
against the raw model's texture, whose colours carry the picture's baked light (Batch 1 try 4, 2026-10-25: 134 takes
were gaps here for a surface dE 32 to 41 off a texture region; owner: "how is that possible with our finish lib and
segmentation method read paper").

Output per take: <take>/finish.npy (finish per face), <take>/parts.npy (part per face), <take>/finish-<view>.png (each
finish in its label colour, finish_ask.LABELS); <take>/texels.npz where the views measured the
model's pictures (route_texels: one part per texel, so the look's borders follow the texture's colour edges; the faces
keep theirs); split.json per take: its fault (None when split), the shares of its area unassigned, disagreeing and
unseen, its parts, each view's agreement with the vote and its texels' record (`moved`, `specks`: area shares).
Gate "one finish a face": every listed take is split with no fault (patchy paint's gaps included). Each faulted
take, and each the rows before named, is a batch gap (batch-gaps.json, score/stages/batch_gaps.py): left out here and
after, its fault moved to complete by the table.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import numpy as np  # noqa: E402

import finish_ask  # noqa: E402
import finish_parts  # noqa: E402
import route_cast as cast  # noqa: E402
import route_views  # noqa: E402
import surface_gates as gates  # noqa: E402
import score.stages.batch_gaps as batch_gaps  # noqa: E402

EDGE_ON = 1e-3  # the least weight of a view's vote on a face it sees (squared_votes)
# The most of a take's area (as split.json records it, to four places) left unassigned that walks to its nearest
# label, not a gap: of 779 takes split in the store (2026-11-08) 778 recorded 0 and one 0.0001, quarters box (48 of
# its 969,698 faces, which only the laid close-up sees, in a small region the list left unlabelled there). Measured,
# never loosened past what a real take showed.
UNASSIGNED_MOST = 0.0001
# A small island the views agree on is a part of its own, never a crumb or a stray (held_islands, #202): every face of
# it seen by a view, at least HELD_AGREE of the weighed votes on it its finish's, and at least HELD_LEAST of the area.
# tc6's surgical chair's ten white wheel hubs (each 0.13 to 0.15% of its area, 15 to 47 faces, their votes 0.95 to
# 1.0 their finish's) were joined into the black tyres round them as crumbs (finish_parts.cleaned at ISLAND_LEAST,
# 0.2%) and drawn black. On tc6's stove, desk, heat gun, fridge and chair the floor keeps no one- or two-face crumb
# (the desk's 200 islands the views agree on under it are 0.03% of its area together).
HELD_AGREE = 0.9
HELD_LEAST = 0.0005


def model_of(folder):
    """The welded, normalised model the views row cast (its face ids)."""
    import trimesh
    found = np.load(folder / "model.npz")
    return trimesh.Trimesh(found["vertices"].astype(float), found["faces"], process=False)


def view_regions(faces, regions, count, face_count):
    """One view's region per face: the region most of its pixels in the view show, -1 for a face it does not see."""
    seen = faces >= 0
    tally = np.bincount(faces[seen] * count + regions[seen], minlength=face_count * count).reshape(face_count, count)
    return np.where(tally.sum(1) > 0, tally.argmax(1), -1)


def view_finishes(region_of, labels, region_count):
    """One view's finish per face from its region and the view's labels ({region: finish}); -1 unseen, -2 seen in a
    region the view's labels leave out."""
    lookup = np.full(region_count, -2)
    for region, finish in labels.items():
        lookup[int(region)] = finish
    return np.where(region_of >= 0, lookup[np.maximum(region_of, 0)], -1)


def per_view(folder, labels, region_count, face_count):
    """{view: finish per face} (view_finishes) of every view the take was cast from, and of the laid close-up
    (close-up.npz) where the views row laid it."""
    faces = dict(np.load(folder / "faces.npz"))
    if (folder / "close-up.npz").exists():
        faces[route_views.CLOSE_UP] = np.load(folder / "close-up.npz")["faces"]
    regions = np.load(folder / "regions.npz")
    return {view: view_finishes(view_regions(faces[view], regions[view], region_count, face_count),
                                labels.get(view, {}), region_count) for view in faces}


def finishes_only(per_map):
    """{view: finish per face, -1 where the view gives none}: a face seen in an unlabelled region votes nothing."""
    return {view: np.where(label >= 0, label, -1) for view, label in per_map.items()}


def shares(mesh, per_map, votes):
    """{unassigned, disagree, unseen}: the shares of the area seen with no label, without a finish over half its
    votes, and seen by no view."""
    area = mesh.area_faces
    seen = np.any([label != -1 for label in per_map.values()], axis=0)
    labelled = votes.sum(1) > 0
    disagree = labelled & (votes.max(1) <= votes.sum(1) / 2)
    return {name: round(float(area[chosen].sum() / area.sum()), 4)
            for name, chosen in (("unassigned", seen & ~labelled), ("disagree", disagree), ("unseen", ~seen))}


def split_fault(found):
    """The gap a take's shares make (None when every face has one finish): faces some view sees that no label
    reaches over UNASSIGNED_MOST of its area (under it they walk to their nearest label), or no face any view sees
    (no finish to settle any face by)."""
    if found["unseen"] >= 1.0:
        return "no view sees any of its faces: no finish can be settled"
    if found["unassigned"] > UNASSIGNED_MOST:
        return (f"faces no label reaches ({found['unassigned']:.2%} of its area, over {UNASSIGNED_MOST:.2%}): "
                "unassigned")
    return None


def squared_votes(mesh, per_map, angles, count, lit=()):
    """Each face's votes per finish, each view's weighed by the cosine between the face's normal and the way to that
    view's eye (a raw take's normals may face in, so its size), the close-up's front and the laid close-up (seen from
    the front) by FRONT_VOTE too; a finish only the laid close-up labels, or one of `lit`, takes the faces it labels
    (close_up_only)."""
    votes = np.zeros((len(mesh.faces), count))
    for view, label in per_map.items():
        seen = np.flatnonzero(label >= 0)
        turn = cast.BASE[cast.FRONT] if view == route_views.CLOSE_UP else angles[view]
        # a face seen edge on still votes, if faintly: a seen face with no vote would read as unassigned
        square = np.maximum(np.abs(mesh.face_normals[seen] @ cast.camera(turn)[0]), EDGE_ON)
        front = view in (cast.FRONT, route_views.CLOSE_UP)
        votes[seen, label[seen]] += square * (finish_parts.FRONT_VOTE if front else 1.0)
    return close_up_only(votes, per_map, lit)


def close_up_only(votes, per_map, lit=()):
    """`votes` with each face the laid close-up labels with a finish no view of the texture labels, or with one of
    `lit` (the finishes that give off light), given that finish alone. The close-up is what the model is held to
    (likeness's close-up parts present), and a small part it shows (a red label, a blue decal, a screen's glow) the raw
    take's texture often lacks: greenhouse desk's views labelled every face of its screens and labels steel, so
    counted they voted the close-up's finishes away (2026-10-29). A lit part no texture shows lit: the readout
    window's texture drew its lit digits as dark relief and voted them the frame's paint (#159 round 8)."""
    laid = per_map.get(route_views.CLOSE_UP)
    if laid is None:
        return votes
    textured = {int(finish) for view, label in per_map.items() if view != route_views.CLOSE_UP
                for finish in np.unique(label[label >= 0])}
    only = np.flatnonzero((laid >= 0) & (~np.isin(laid, list(textured)) | np.isin(laid, list(lit))))
    found = votes.copy()
    found[only] = 0.0
    found[only, laid[only]] = 1.0
    return found


def behind(mesh, own, voted):
    """`own` with each face no view votes on given the finish of the voted face nearest it in space. Such a face is
    mostly a shell's inner side, a wall's thickness behind the outer side that shows its finish (TRELLIS.2's models,
    tc2: 55 to 77% of the area unseen, 74 to 79% of it facing the seen face nearest it); walked along the surface it
    took whatever finish crossed the rim first (the rack's beams the deck's grey: held_mean 0.57 against NVIDIA's face
    groups, 0.87 so; the fridge's glass pane's back its door frame's), and the parts mixed NVIDIA's finishes (#173)."""
    from scipy.spatial import cKDTree
    found = own.copy()
    sources = np.flatnonzero(own >= 0)
    unseen = np.flatnonzero(~voted)
    if len(sources) and len(unseen):
        middles = mesh.triangles_center
        found[unseen] = own[sources[cKDTree(middles[sources]).query(middles[unseen])[1]]]
    return found


def voted_finishes(mesh, votes, count):
    """(part per face, finish per face): each face's most voted finish (a tie left to the walk, so it takes the
    finish round it), unseen faces the finish behind them (behind), smoothed, strays joined to the finish round them
    and crumbs joined; a held island (held_islands) keeps its own finish through the smoothing."""
    top = np.sort(votes, axis=1)
    tied = (top[:, -1] > 0) & np.isclose(top[:, -1], top[:, -2]) if count > 1 else np.zeros(len(votes), dtype=bool)
    voted = votes.sum(1) > 0
    own = np.where(voted & ~tied, votes.argmax(1), -1)
    smoothed = finish_parts.cleaned(mesh, finish_parts.walked(mesh, behind(mesh, own, voted)), count)
    joined = finish_parts.without_strays(mesh, smoothed)
    held = held_islands(mesh, own, votes)
    joined[held] = own[held]
    return hidden_joined(mesh, finish_parts.merged_islands(mesh, joined), voted)


def held_islands(mesh, own, votes):
    """Whether each face lies in a held island of `own` (each face's voted finish, -1 none): one under patchy's
    STRAY_ISLAND of the area and at least HELD_LEAST of it, whose every face a view votes on, HELD_AGREE of the votes
    on it its finish's: a part the views agree on, however small (a wheel's hub), which the crumb and stray joins
    would give the finish round it. A larger island is never joined away, so its smoothed border stands."""
    import patchy
    island = np.unique(patchy.islands(own, mesh.face_adjacency), return_inverse=True)[1]
    areas = mesh.area_faces
    agree = np.bincount(island, weights=votes[np.arange(len(own)), np.maximum(own, 0)]) \
        / np.maximum(np.bincount(island, weights=votes.sum(1)), 1e-12)
    voted = np.bincount(island, weights=(own < 0).astype(float)) == 0
    area = np.bincount(island, weights=areas) / areas.sum()
    held = voted & (agree >= HELD_AGREE) & (area >= HELD_LEAST) & (area < patchy.STRAY_ISLAND)
    return held[island]


def hidden_joined(mesh, found, voted):
    """(part per face, finish per face) `found` with each part the views hardly vote on (its voted faces under
    finish_parts.ISLAND_LEAST of the area, a crumb's: a shell's inner side cut off from its outer side by a rim of
    another finish, a loose piece inside glimpsed through a gap) joined to the part of the voted face of its own
    finish nearest it; a part whose finish no voted face has stays its own, and so does one under patchy's
    STRAY_ISLAND of the area: joined, it would read as a blotch of the part it joined (the sign's six, stray 0.031).
    Left apart, the printer box's one cardboard came out as five parts and its tape as four (tc2, #173)."""
    import patchy
    from scipy.spatial import cKDTree
    part_of, finish_of = found
    joined = part_of.copy()
    middles = mesh.triangles_center
    shown = np.bincount(part_of, weights=np.where(voted, mesh.area_faces, 0.0)) >= finish_parts.ISLAND_LEAST * mesh.area
    large = np.bincount(part_of, weights=mesh.area_faces) >= patchy.STRAY_ISLAND * mesh.area
    for part in np.flatnonzero(~shown & large):
        faces = np.flatnonzero(part_of == part)
        host = np.flatnonzero(voted & (finish_of == finish_of[faces[0]]))
        if len(host):
            joined[faces] = part_of[host[cKDTree(middles[host]).query(middles[faces])[1]]]
    return np.unique(joined, return_inverse=True)[1], finish_of


def patchy_fault(found):
    """The gap patchy paint makes (finish_parts.patchiness failing), None when it passes."""
    return None if found["pass"] else f"patchy paint: {'; '.join(found['faults'])}"


def split_saved(out, mesh, folder, angles, found):
    """finish.npy, parts.npy and each view's finish picture into `out`; `found` is (finish per face, part per
    face)."""
    finish_of, part_of = found
    out.mkdir(parents=True)
    np.save(out / "finish.npy", finish_of.astype(np.int16))
    np.save(out / "parts.npy", part_of.astype(np.int32))
    palette = np.array(finish_ask.LABELS, dtype=np.uint8)
    faces = np.load(folder / "faces.npz")
    for view in faces.files:
        cast.picture(cast.face_painted(palette[finish_of % len(palette)], faces[view]), faces[view],
                     cast.shading(mesh, faces[view], angles[view])).save(out / f"finish-{view}.png")


def texels_saved(folders, mesh, listed, counts, split, lit=()):
    """<take>/texels.npz (route_texels: each texel of the model's pictures its part, so the look's borders follow the
    texture's colour edges; a lit finish's where the close-up shows it, route_texels.texel_parts); its record.
    `counts` is (regions, finishes), `split` (part per face, finish per face)."""
    import route_texels
    weights = route_texels.region_weights(listed["labels"], counts[0], counts[1], finish_parts.FRONT_VOTE,
                                          (cast.FRONT, route_views.CLOSE_UP))
    told = {int(region): int(finish) for region, finish in listed["labels"].get(route_views.CLOSE_UP, {}).items()}
    parts, found = route_texels.take_texels(mesh, dict(np.load(folders["views"] / "texels.npz")), weights, split,
                                            (lit, told))
    np.savez_compressed(folders["out"] / "texels.npz", **{f"piece{piece}": part for piece, part in parts.items()})
    return found


def lit_laid(mesh, found, laid, lit):
    """(part per face, finish per face) `found` with each face the laid close-up (`laid`, finish per face, -1 none)
    labels with one of the `lit` finishes given it again after the smoothing, each island of it holding one a part of
    its own: a lit part is the close-up's (close_up_only), and its small islands are no stray of paint (the readout
    window's lit digits, islands of 0.01 to 0.1% of its area, were folded into the frame's paint because its texture's
    back held a larger lit island, #159 round 8)."""
    import patchy
    part_of, finish_of = found
    chosen = np.isin(laid, list(lit)) if laid is not None else np.zeros(len(finish_of), dtype=bool)
    if not chosen.any():
        return found
    finish_of = finish_of.copy()
    finish_of[chosen] = laid[chosen]
    island = patchy.islands(finish_of, mesh.face_adjacency)
    own = np.isin(island, island[chosen])
    return np.unique(np.where(own, part_of.max() + 1 + island, part_of), return_inverse=True)[1], finish_of


def lit_finishes(finishes):
    """The numbers of the listed finishes that give off light (their family one of finish_parts.LIT_FAMILIES)."""
    return [number for number, finish in enumerate(finishes) if finish.get("family") in finish_parts.LIT_FAMILIES]


def split_take(folders, listed, record):
    """One take split into folders["out"] unless it is a gap; its split.json record. `record` is its views record."""
    mesh = model_of(folders["views"])
    count = len(listed["finishes"])
    labelled = per_view(folders["views"], listed["labels"], len(record["regions"]), len(mesh.faces))
    per_map = finishes_only(labelled)
    found = shares(mesh, labelled, finish_parts.voted(per_map, count))  # the views' own disagreement, unweighed
    lit = lit_finishes(listed["finishes"])
    votes = squared_votes(mesh, per_map, record["views"], count, lit)
    fault = split_fault(found)
    if fault is not None:
        return {"fault": fault, **found}
    part_of, finish_of = lit_laid(mesh, voted_finishes(mesh, votes, count), per_map.get(route_views.CLOSE_UP), lit)
    found["patchy"] = finish_parts.patchiness(mesh, finish_of, part_of, listed["finishes"])
    if patchy_fault(found["patchy"]) is not None:
        return {"fault": patchy_fault(found["patchy"]), **found}
    split_saved(folders["out"], mesh, folders["views"], record["views"], (finish_of, part_of))
    if (folders["views"] / "texels.npz").exists():
        found["texels"] = texels_saved(folders, mesh, listed, (len(record["regions"]), count), (part_of, finish_of),
                                       lit)
    return {"fault": None, **found, "parts": int(part_of.max()) + 1,
            "agreement": finish_parts.agreement(mesh, finish_of, per_map)}


def make_split(inputs, out, seed, params):
    """Every listed take split by finish, or named a gap; split.json."""
    views, listed = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-list"])
    carried = batch_gaps.of(inputs)
    found = {take: split_take({"views": views / take, "out": out / take},
                              json.loads((listed / f"{take}.json").read_text()), record)
             for take, record in json.loads((views / "views.json").read_text()).items()
             if (listed / f"{take}.json").exists() and take not in batch_gaps.objects(carried)}
    (out / "split.json").write_text(json.dumps(found, indent=1))
    batch_gaps.write(out, [*carried, *(batch_gaps.gap(f"{take}: not one finish a face", "finish-route-split",
                                                      "one finish a face", (take,), [f"{take}: {record['fault']}"],
                                                      "the one list answer did not give every face one finish")
                                       for take, record in found.items() if record["fault"])])


def split_faults(folder):
    return [] if (folder / "split.json").exists() else ["no split.json"]


def judge_split(output, inputs, evidence):
    """Every listed take split, every face one finish: an unassigned face, views that disagree or patchy paint is a
    gap, named."""
    found = json.loads((output / "split.json").read_text())
    failing = [f"{take}: {record['fault']}" for take, record in found.items() if record["fault"]]
    return gates.verdict("one finish a face", failing, len(found), "takes not split by finish",
                         {"unseen_share_most": max((record["unseen"] for record in found.values()), default=0.0)})
