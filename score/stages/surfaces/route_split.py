"""The finish route's split row (free, on this PC's processor): each listed take's faces split by finish, the list's
labels voted across every view. In each view a face takes the region most of its pixels show (route_views) and that
region's label there (route_list); the views vote (finish_parts.voted, the close-up's front counting FRONT_VOTE).

Every face gets exactly one finish, or its take is a hole, named (owner, 2026-10-20): a face some view sees whose
regions no view labelled is unassigned, and faces whose views disagree (no finish holds over half their votes) over
DISAGREE_MOST of the area are views that disagree. A face no view can see takes its nearest seen face's finish along
the surface (finish_parts.walked); the finishes are then smoothed and crumbs joined (finish_parts.cleaned,
merged_islands), each island one part.

Output per take: <take>/finish.npy (finish per face), <take>/parts.npy (part per face), <take>/finish-<view>.png (each
finish in its label colour, finish_ask.LABELS); split.json per take: its fault (None when split), the shares of its
area unassigned, disagreeing and unseen, its parts and each view's agreement with the vote.
Gate "one finish a face": every listed take is split with no fault.
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
import surface_gates as gates  # noqa: E402

DISAGREE_MOST = 0.01  # a take whose disagreeing faces hold over this share of its area is a hole (set, not measured)


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
    """{view: finish per face} (view_finishes) of every view the take was cast from."""
    faces = np.load(folder / "faces.npz")
    regions = np.load(folder / "regions.npz")
    return {view: view_finishes(view_regions(faces[view], regions[view], region_count, face_count),
                                labels.get(view, {}), region_count) for view in faces.files}


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
    """The hole a take's shares make (None when every face has one finish): unassigned faces, or views that
    disagree."""
    if found["unassigned"] > 0:
        return f"faces no label reaches ({found['unassigned']:.2%} of its area): unassigned"
    if found["disagree"] > DISAGREE_MOST:
        return f"the views disagree on {found['disagree']:.2%} of its area (over {DISAGREE_MOST:.0%})"
    return None


def voted_finishes(mesh, votes, count):
    """(part per face, finish per face): each face's most voted finish, unseen faces walked, smoothed and crumbs
    joined."""
    own = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
    return finish_parts.merged_islands(mesh, finish_parts.cleaned(mesh, finish_parts.walked(mesh, own), count))


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
    """One take split into folders["out"] unless it is a hole; its split.json record. `record` is its views record."""
    mesh = model_of(folders["views"])
    count = len(listed["finishes"])
    labelled = per_view(folders["views"], listed["labels"], len(record["regions"]), len(mesh.faces))
    per_map = finishes_only(labelled)
    votes = finish_parts.voted(per_map, count)
    found = shares(mesh, labelled, votes)
    fault = split_fault(found)
    if fault is not None:
        return {"fault": fault, **found}
    part_of, finish_of = voted_finishes(mesh, votes, count)
    split_saved(folders["out"], mesh, folders["views"], record["views"], (finish_of, part_of))
    return {"fault": None, **found, "parts": int(part_of.max()) + 1,
            "agreement": finish_parts.agreement(mesh, finish_of, per_map)}


def make_split(inputs, out, seed, params):
    """Every listed take split by finish, or named a hole; split.json."""
    views, listed = pathlib.Path(inputs["finish-route-views"]), pathlib.Path(inputs["finish-route-list"])
    found = {take: split_take({"views": views / take, "out": out / take},
                              json.loads((listed / f"{take}.json").read_text()), record)
             for take, record in json.loads((views / "views.json").read_text()).items()
             if (listed / f"{take}.json").exists()}
    (out / "split.json").write_text(json.dumps(found, indent=1))


def split_faults(folder):
    return [] if (folder / "split.json").exists() else ["no split.json"]


def judge_split(output, inputs, evidence):
    """Every listed take split, every face one finish: an unassigned face or views that disagree is a hole, named."""
    found = json.loads((output / "split.json").read_text())
    failing = [f"{take}: {record['fault']}" for take, record in found.items() if record["fault"]]
    return gates.verdict("one finish a face", failing, len(found), "takes not split by finish",
                         {"unseen_share_most": max((record["unseen"] for record in found.values()), default=0.0)})
