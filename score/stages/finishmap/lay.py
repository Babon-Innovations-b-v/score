"""EXPERIMENTAL (the finish-map test of 2026-10-11): a finish map laid onto the raw Pixal3D model (its geometry kept),
every face one label, the labels smoothed and their islands under CRUMB merged into their neighbours, each label's
faces painted with its finish's library surface, the painted parts the labels' connected patches. Runs in the prop
environment (trimesh); no model runs here.

    python score/stages/finishmap/lay.py <maps folder> <segvigen run folder> <out folder> <take> [<take> ...]

Three arms, each written as <out>/<arm>/<take>/faces.npz and labels.json in the surface test's format (paint.py's:
`names`, `surface`, `painted_part` per welded face; `named_on` "close-up", since the finish list was named on the
close-up alone):
- fm-project: the cheap route. Faces the close-up's camera sees take their pixel's label; every other face takes the
  label of the nearest labelled face along the surface (a walk over face neighbours), a piece no walk reaches the
  nearest labelled face in space.
- fm-segvigen: SegviGen (MIT, on TRELLIS.2) guided by the finish map in SegviGen's part colours splits the whole
  model, unseen sides included; each of its parts takes the label most of its seen faces carry, a part with too few
  seen faces the label most of its faces got from fm-project's walk.
- fm-hybrid: fm-project's labels where the camera sees, fm-segvigen's elsewhere.
"""
import json
import pathlib
import sys

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in (REPO / "tools/props", REPO / "tools/props/library"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))
import labels  # noqa: E402
import patchy  # noqa: E402
import split_compare  # noqa: E402

ARMS = ("fm-project", "fm-segvigen", "fm-hybrid")
# An island of one label under CRUMB of the model's area joins the label it borders most (split_compare's crumb).
CRUMB = split_compare.CRUMB
# A SegviGen part names itself from its seen faces when they hold SEEN_LEAST of its area.
SEEN_LEAST = 0.05


def projected(mesh, take, per_pixel):
    """Each face's label where the close-up's camera sees it (its pixel's), -1 elsewhere or on no label."""
    _, seen, row, column = labels.picture_view(mesh, take)
    found = np.full(len(mesh.faces), -1)
    found[seen] = per_pixel[row[seen], column[seen]]
    return found


def walked(mesh, face_label):
    """Every unlabelled face given the label of the nearest labelled face along the surface (face middles joined
    across shared edges, weighed by their distance); faces no walk reaches take the nearest labelled face in space."""
    pairs = mesh.face_adjacency
    middles = mesh.triangles_center
    length = np.linalg.norm(middles[pairs[:, 0]] - middles[pairs[:, 1]], axis=1) + 1e-9
    count = len(mesh.faces)
    graph = sparse.coo_matrix((np.r_[length, length], (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                              shape=(count, count)).tocsr()
    sources = np.flatnonzero(face_label >= 0)
    distance, _, source = dijkstra(graph, directed=False, indices=sources, min_only=True, return_predecessors=True)
    found = face_label.copy()
    reached = np.isfinite(distance) & (source >= 0)
    found[reached] = face_label[source[reached]]
    lost = found < 0
    if lost.any():
        found[lost] = face_label[sources[cKDTree(middles[sources]).query(middles[lost])[1]]]
    return found


def cleaned(mesh, face_label, count):
    """The labels smoothed over the surface (labels.smoothed_parts, hardly across a crease) and every island under
    CRUMB of the area joined to the label it borders most."""
    votes = np.zeros((len(face_label), count))
    votes[np.arange(len(face_label)), face_label] = 1.0
    smoothed = labels.smoothed_parts(votes, labels.neighbour_matrix(mesh))
    saved = labels.PART_CRUMB
    labels.PART_CRUMB = CRUMB
    try:
        return labels.without_crumbs(mesh, smoothed)
    finally:
        labels.PART_CRUMB = saved


def part_labels(mesh, part_of, seen_label, walked_label, count):
    """Each SegviGen part's label: the most area among its seen labelled faces when they hold SEEN_LEAST of its
    area, else the most area of the walked labels over it; per face."""
    areas = mesh.area_faces
    parts = int(part_of.max()) + 1
    seen = seen_label >= 0
    by_seen = np.zeros((parts, count))
    np.add.at(by_seen, (part_of[seen], seen_label[seen]), areas[seen])
    by_walk = np.zeros((parts, count))
    np.add.at(by_walk, (part_of, walked_label), areas)
    size = np.bincount(part_of, weights=areas, minlength=parts)
    chosen = np.where(by_seen.sum(1) >= SEEN_LEAST * size, by_seen.argmax(1), by_walk.argmax(1))
    return chosen[part_of]


def turned(mesh):
    """The raw model turned half round about up (labels.VIEW_TURN), as it goes to SegviGen: SegviGen's camera looks
    at the raw model's back (its own conditioning render showed the lander's back, 2026-10-11), so unturned the
    close-up's finish map was painted onto the back."""
    import trimesh
    return trimesh.Trimesh(mesh.vertices @ labels.VIEW_TURN.T, mesh.faces, process=False)


def segvigen_split(mesh, take_folder):
    """SegviGen's guided split on the faces (its voxels laid on the turned model it was given), cleaned as the parts
    test cleaned it (split_compare)."""
    return split_compare.cleaned(mesh, split_compare.segvigen_parts(turned(mesh), take_folder, "guided"))


def arm_labels(mesh, take, per_pixel, count, segvigen_folder):
    """{arm: label per face} for every arm whose inputs exist."""
    seen_label = projected(mesh, take, per_pixel)
    walked_label = walked(mesh, seen_label)
    found = {"fm-project": cleaned(mesh, walked_label, count)}
    if (segvigen_folder / "down" / "segvigen_guided.npz").exists():
        from_parts = part_labels(mesh, segvigen_split(mesh, segvigen_folder), seen_label, walked_label, count)
        found["fm-segvigen"] = cleaned(mesh, from_parts, count)
        found["fm-hybrid"] = cleaned(mesh, np.where(seen_label >= 0, seen_label, from_parts), count)
    return found, float(mesh.area_faces[seen_label >= 0].sum() / mesh.area)


def written(out, take, arm, mesh, face_label, finishes, seen_share):
    """faces.npz and labels.json of one arm on one take; the report."""
    out.mkdir(parents=True, exist_ok=True)
    names = sorted({entry["surface"] for entry in finishes})
    surface = np.array([names.index(finishes[label]["surface"]) for label in range(len(finishes))])[face_label]
    painted_part = patchy.islands(face_label, mesh.face_adjacency)
    np.savez_compressed(out / "faces.npz", surface=surface.astype(np.int16), part=face_label.astype(np.int32),
                        painted_part=np.unique(painted_part, return_inverse=True)[1].astype(np.int32),
                        names=np.array(names))
    areas = mesh.area_faces
    report = {"take": take, "arm": arm, "named_on": "close-up", "seen_share": round(seen_share, 3),
              "finishes": [dict(entry, share=round(float(areas[face_label == label].sum() / areas.sum()), 3))
                           for label, entry in enumerate(finishes)],
              "painted_parts": int(len(np.unique(painted_part)))}
    (out / "labels.json").write_text(json.dumps(report, indent=1))
    return report


def lay(maps, segvigen_run, out, take):
    """Every arm of one take laid and written; {arm: report}."""
    record = json.loads((maps / take / "map.json").read_text())
    per_pixel = np.load(maps / take / "labels.npy")
    mesh = split_compare.raw_model(take)
    found, seen_share = arm_labels(mesh, take, per_pixel, len(record["finishes"]), segvigen_run / take)
    return {arm: written(out / arm / take, take, arm, mesh, face_label, record["finishes"], seen_share)
            for arm, face_label in found.items()}


def main():
    maps, segvigen_run, out = (pathlib.Path(argument) for argument in sys.argv[1:4])
    for take in sys.argv[4:]:
        reports = lay(maps, segvigen_run, out, take)
        print(take, {arm: report["painted_parts"] for arm, report in reports.items()}, flush=True)


if __name__ == "__main__":
    main()
