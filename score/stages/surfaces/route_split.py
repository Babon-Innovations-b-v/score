"""The finish route's split row (free, on this PC's processor): each listed take's faces split by finish, the list's
labels voted across every view. In each view a face takes the region most of its pixels show (route_views) and that
region's label there (route_list); the views vote (squared_votes: each view's vote on a face weighed by how squarely
it sees it, the cosine between the face's normal and the way to the eye, the close-up's front counting FRONT_VOTE).
The close-up laid on the model (route_views.CLOSE_UP, where the views row laid it) votes as the front does, and a
finish only it labels, one no view of the texture shows, takes the faces it labels it on (close_up_only).

Every face gets exactly one finish, or its take is a gap, named (owner, 2026-10-20): a face some view sees whose
regions no view labelled is unassigned, a gap. Faces whose views disagree (no finish over half their votes) are a
split decision, never a gap (owner, 2026-10-28: the views disagreed on 1.2 to 5.8% of eleven takes, one colour region
over several finishes, and the old 1% limit was never measured): each takes the finish its views weigh most, a tie
the finish of the part round it (walked); their share is still recorded. A face no view can see (the inside of a raw
model's shell, out of every camera's reach, is no gap) takes its nearest seen face's finish along the surface (finish_parts.walked); the
finishes are then smoothed, each stray (an island under patchy.py's STRAY_ISLAND of a finish that has a larger one)
given the finish round it (finish_parts.without_strays) and crumbs joined (finish_parts.cleaned, merged_islands), each
island one part. A take whose paint is still patchy (patchy.score, each part its own region, as the paint measures,
each island of a detail finish a part of its own: finish_parts.patchiness) is a gap, named, before anything is baked.

The split decides by the labels alone (the paper, "Surfaces: the finish route": the views are split into colour
regions only so the list can label them). No colour is judged here: a finish's surface is held against its colour
in the close-up after the split, by the parts row's check and the bake check (route_parts, bake_check), never
against the raw model's texture, whose colours carry the picture's baked light (Batch 1 try 4, 2026-10-25: 134 takes
were gaps here for a surface dE 32 to 41 off a texture region; owner: "how is that possible with our finish lib and
segmentation method read paper").

Output per take: <take>/finish.npy (finish per face), <take>/parts.npy (part per face), <take>/finish-<view>.png (each
finish in its label colour, finish_ask.LABELS); split.json per take: its fault (None when split), the shares of its
area unassigned, disagreeing and unseen, its parts and each view's agreement with the vote.
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
    reaches, or no face any view sees (no finish to settle any face by)."""
    if found["unseen"] >= 1.0:
        return "no view sees any of its faces: no finish can be settled"
    if found["unassigned"] > 0:
        return f"faces no label reaches ({found['unassigned']:.2%} of its area): unassigned"
    return None


def squared_votes(mesh, per_map, angles, count):
    """Each face's votes per finish, each view's weighed by the cosine between the face's normal and the way to that
    view's eye (a raw take's normals may face in, so its size), the close-up's front and the laid close-up (seen from
    the front) by FRONT_VOTE too; a finish only the laid close-up labels takes the faces it labels (close_up_only)."""
    votes = np.zeros((len(mesh.faces), count))
    for view, label in per_map.items():
        seen = np.flatnonzero(label >= 0)
        turn = cast.BASE[cast.FRONT] if view == route_views.CLOSE_UP else angles[view]
        # a face seen edge on still votes, if faintly: a seen face with no vote would read as unassigned
        square = np.maximum(np.abs(mesh.face_normals[seen] @ cast.camera(turn)[0]), EDGE_ON)
        front = view in (cast.FRONT, route_views.CLOSE_UP)
        votes[seen, label[seen]] += square * (finish_parts.FRONT_VOTE if front else 1.0)
    return close_up_only(votes, per_map)


def close_up_only(votes, per_map):
    """`votes` with each face the laid close-up labels with a finish no view of the texture labels given that finish
    alone. The close-up is what the model is held to (likeness's close-up parts present), and a small part it shows
    (a red label, a blue decal, a screen's glow) the raw take's texture often lacks: greenhouse desk's views labelled
    every face of its screens and labels steel, so counted they voted the close-up's finishes away (2026-10-29)."""
    laid = per_map.get(route_views.CLOSE_UP)
    if laid is None:
        return votes
    textured = {int(finish) for view, label in per_map.items() if view != route_views.CLOSE_UP
                for finish in np.unique(label[label >= 0])}
    only = np.flatnonzero((laid >= 0) & ~np.isin(laid, list(textured)))
    found = votes.copy()
    found[only] = 0.0
    found[only, laid[only]] = 1.0
    return found


def voted_finishes(mesh, votes, count):
    """(part per face, finish per face): each face's most voted finish (a tie left to the walk, so it takes the
    finish round it), unseen faces walked, smoothed, strays joined to the finish round them and crumbs joined."""
    top = np.sort(votes, axis=1)
    tied = (top[:, -1] > 0) & np.isclose(top[:, -1], top[:, -2]) if count > 1 else np.zeros(len(votes), dtype=bool)
    own = np.where((votes.sum(1) > 0) & ~tied, votes.argmax(1), -1)
    smoothed = finish_parts.cleaned(mesh, finish_parts.walked(mesh, own), count)
    return finish_parts.merged_islands(mesh, finish_parts.without_strays(mesh, smoothed))


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


def split_take(folders, listed, record):
    """One take split into folders["out"] unless it is a gap; its split.json record. `record` is its views record."""
    mesh = model_of(folders["views"])
    count = len(listed["finishes"])
    labelled = per_view(folders["views"], listed["labels"], len(record["regions"]), len(mesh.faces))
    per_map = finishes_only(labelled)
    found = shares(mesh, labelled, finish_parts.voted(per_map, count))  # the views' own disagreement, unweighed
    votes = squared_votes(mesh, per_map, record["views"], count)
    fault = split_fault(found)
    if fault is not None:
        return {"fault": fault, **found}
    part_of, finish_of = voted_finishes(mesh, votes, count)
    found["patchy"] = finish_parts.patchiness(mesh, finish_of, part_of, listed["finishes"])
    if patchy_fault(found["patchy"]) is not None:
        return {"fault": patchy_fault(found["patchy"]), **found}
    split_saved(folders["out"], mesh, folders["views"], record["views"], (finish_of, part_of))
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
