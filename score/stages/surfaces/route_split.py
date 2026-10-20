"""The finish route's split row (free, on this PC's processor): each take's faces split into colour groups by the
labels its views vote, the labels free: the model's own texture under each pixel (route_views), its CIELAB colours
split by k-means into at most GROUPS groups (finish_maps.colour_split's way: colours only split, they name nothing),
each view's label of a face its pixels' most; the views vote (finish_parts.voted, the close-up's view counting
FRONT_VOTE), a face no view sees takes its nearest voted face's along the surface (finish_parts.walked), then
smoothed and crumbs joined (finish_parts.cleaned, merged_islands). The list row names which groups are which
finish, so the parts by finish are these groups joined by it (route_fill). No paid map is drawn here: Nano Banana's
finish maps (about EUR 3 a model) stay the existing route's (finish_rows), for a model these free labels fail.

Output per take: <take>/groups.npy (group per face), <take>/parts.npy (part per face), <take>/groups-<view>.png
(each group in its label colour, finish_ask.LABELS, for the list row's question); groups.json per take: each
group's CIELAB colour, sRGB and share of the area, and per view the share of the faces it labels that kept its label.
Gate "parts voted": every cast take is split, every face in a group.
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
import route_data  # noqa: E402
import surface_gates as gates  # noqa: E402

GROUPS = len(finish_ask.LABELS)  # one label colour a group in the list row's pictures
SAMPLE = 60000  # the pixels k-means is fitted on, drawn with the node's seed


def model_of(folder):
    """The welded, normalised model the views row cast (its face ids)."""
    import trimesh
    found = np.load(folder / "model.npz")
    return trimesh.Trimesh(found["vertices"].astype(float), found["faces"], process=False)


def colour_groups(colours, faces, seed):
    """(the groups' CIELAB centres, each view's group per pixel, -1 off the model): every seen pixel's colour in
    k-means' groups, fitted on SAMPLE of them; groups no pixel falls in are dropped."""
    from scipy.cluster.vq import kmeans2, vq
    seen = {view: cast.lab_of(colours[view][faces[view] >= 0]) for view in faces}
    every = np.concatenate(list(seen.values()))
    draw = np.random.default_rng(seed).choice(len(every), min(SAMPLE, len(every)), replace=False)
    distinct = len(np.unique(every[draw].round(1), axis=0))  # fewer colours than GROUPS: one group each
    centres, _ = kmeans2(every[draw], min(GROUPS, distinct), seed=seed, minit="++")
    used = np.unique(vq(every, centres)[0])
    centres = centres[used]
    per_pixel = {}
    for view, lab in seen.items():
        label = np.full(faces[view].shape, -1)
        label[faces[view] >= 0] = vq(lab, centres)[0]
        per_pixel[view] = label
    return centres, per_pixel


def view_labels(faces, labels, count, face_count):
    """One view's group per face: the group most of its pixels in the view have, -1 for a face it does not see."""
    seen = faces >= 0
    tally = np.bincount(faces[seen] * count + labels[seen], minlength=face_count * count).reshape(face_count, count)
    return np.where(tally.sum(1) > 0, tally.argmax(1), -1)


def face_groups(mesh, faces, per_pixel, count):
    """Each face's group, the views' colour groups voted across views, walked, cleaned and merged into islands, and
    its part: (group_of, part_of, per_map)."""
    per_map = {view: view_labels(faces[view], per_pixel[view], count, len(mesh.faces)) for view in faces}
    votes = finish_parts.voted(per_map, count)  # the close-up's view is "front": finish_parts' FRONT_VOTE
    own = np.where(votes.sum(1) > 0, votes.argmax(1), -1)
    part_of, group_of = finish_parts.merged_islands(mesh, finish_parts.cleaned(mesh, finish_parts.walked(mesh, own),
                                                                              count))
    return group_of, part_of, per_map


def split_saved(out, mesh, faces, group_of, part_of):
    """groups.npy, parts.npy and each view's group picture into `out`."""
    out.mkdir(parents=True)
    np.save(out / "groups.npy", group_of.astype(np.int16))
    np.save(out / "parts.npy", part_of.astype(np.int32))
    palette = np.array(finish_ask.LABELS, dtype=np.uint8)
    for view in faces:
        cast.picture(cast.face_painted(palette[group_of], faces[view]), faces[view],
                     cast.shading(mesh, faces[view], view)).save(out / f"groups-{view}.png")


def split_record(mesh, centres, srgb, group_of, part_of, per_map):
    """A take's groups.json record: each group's colour and share, its part count and the views' agreement."""
    area = np.bincount(group_of, weights=mesh.area_faces, minlength=len(centres)) / mesh.area
    return {"groups": [{"group": group, "lab": [round(float(value), 1) for value in centre], "srgb": srgb[group],
                        "share": round(float(area[group]), 4)} for group, centre in enumerate(centres)],
            "parts": int(part_of.max()) + 1, "agreement": finish_parts.agreement(mesh, group_of, per_map)}


def split_take(folder, seed):
    """One take's groups and parts into its views folder's twin; its groups.json record."""
    mesh = model_of(folder["views"])
    faces = dict(np.load(folder["views"] / "faces.npz"))
    colours = dict(np.load(folder["views"] / "colours.npz"))
    centres, per_pixel = colour_groups(colours, faces, seed)
    group_of, part_of, per_map = face_groups(mesh, faces, per_pixel, len(centres))
    split_saved(folder["out"], mesh, faces, group_of, part_of)
    return split_record(mesh, centres, group_colours(colours, per_pixel, len(centres)), group_of, part_of, per_map)


def group_colours(colours, per_pixel, count):
    """Each group's median sRGB 0-255 over its pixels in every view."""
    found = []
    for group in range(count):
        pixels = np.concatenate([colours[view][per_pixel[view] == group] for view in colours])
        found.append(np.median(pixels, axis=0).round().astype(int).tolist() if len(pixels) else None)
    return found


def make_split(inputs, out, seed, params):
    """Every cast take's groups and parts; groups.json."""
    views = pathlib.Path(inputs["finish-route-views"])
    cast_takes = json.loads((views / "views.json").read_text())
    route_data.takes_written(out, inputs, params)  # the filter's takes, for the record; the cast ones are split
    found = {take: split_take({"views": views / take, "out": out / take}, seed)
             for take, record in cast_takes.items() if record.get("model")}
    (out / "groups.json").write_text(json.dumps(found, indent=1))


def split_faults(folder):
    return [] if (folder / "groups.json").exists() else ["no groups.json"]


def judge_split(output, inputs, evidence):
    """Every take the views cast is split and every face is in a group."""
    cast_takes = json.loads((pathlib.Path(inputs["finish-route-views"]) / "views.json").read_text())
    found = json.loads((output / "groups.json").read_text())
    failing = [f"{take}: not split" for take, record in cast_takes.items() if record.get("model") and take not in found]
    failing += [f"{take}: faces in no group" for take in found
                if (np.load(output / take / "groups.npy") < 0).any()]
    return gates.verdict("parts voted", failing, len(found), "takes not split")
