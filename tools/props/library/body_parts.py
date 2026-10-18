"""The parts a bodied prop's bake reads, written for a re-made take (free, on this PC, no model loaded): the take's
raw Pixal3D model laid on its finished model as labels.py lays it, each face given the library surface of the
nearest face of the prop's accepted labelled take, both laid in the kit frame at the prop's laid size, and written
as one .ply per surface beside a labels.json that names the body's take (bodies.BODIES), so make_chunky.make_bodied
builds the body and keeps the details bodies.kept names.

Why: a code body brings its own parts named from code, so the surface line's finish maps, SegviGen and paint are not
made again for a bodied prop (prop_batch's route, 2026-10-18); only its kept details need surfaces, and the accepted
take, made from the same close-up, already names them. A re-made take whose faces lie far from the accepted take's
(`GAP_MOST`) is refused rather than labelled by guess.

    props-env python body_parts.py <new take> <accepted labelled folder> <body take> <size json> <base json> <out>
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "inside"))
sys.path.insert(0, str(HERE))
import bodies  # noqa: E402

# A re-made take is labelled from the accepted one only when its faces' median distance to the accepted take's, both
# laid at the laid size, is at most this share of the laid size's diagonal (the two are the same close-up's model).
GAP_MOST = 0.02


def laid(vertices, turn, size):
    """Vertices (glTF frame) turned and fitted into the kit frame at `size`, standing on the middle of their foot, as
    make_chunky.into_kit_frame lays a take."""
    turned = np.asarray(vertices, dtype=float) @ np.asarray(turn, dtype=float).reshape(3, 3).T
    low, high = turned.min(0), turned.max(0)
    middle = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    return (turned - middle) * (np.asarray(size, dtype=float) / (high - low))


def accepted_faces(folder):
    """The accepted labelled take's faces: (middles in its own frame, surface names), one surface a .ply."""
    middles, names = [], []
    for path in sorted(pathlib.Path(folder).glob("*.ply")):
        mesh = trimesh.load(path, force="mesh", process=False)
        middles.append(mesh.triangles_center)
        names += [path.stem] * len(mesh.faces)
    if not names:
        raise SystemExit(f"{folder}: no labelled parts")
    return np.vstack(middles), np.array(names)


def surfaces_from(new_middles, old_middles, old_names, turn, size):
    """Each new face's surface, the nearest accepted face's in the kit frame, and the median gap as a share of the laid
    size's diagonal. Both takes are laid by their own box, so each is fitted on its own."""
    new_laid, old_laid = laid(new_middles, turn, size), laid(old_middles, turn, size)
    gaps, nearest = cKDTree(old_laid).query(new_laid)
    return old_names[nearest], float(np.median(gaps) / np.linalg.norm(size))


def raw_on_finished(take):
    """The re-made take's raw model, welded, laid on its finished model and cut to its box, as labels.py writes a
    take's parts."""
    import labels
    mesh = labels.welded(trimesh.load(labels.PIXAL / f"{take}.glb", force="mesh", process=False))
    final = trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh")
    matrix, _ = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                     labels.finish_turn(take))
    mesh.apply_transform(matrix)
    inside = np.all((mesh.triangles_center >= final.bounds[0] - 0.02)
                    & (mesh.triangles_center <= final.bounds[1] + 0.02), axis=1)
    return mesh.submesh([np.nonzero(inside)[0]], append=True)


def write_surfaces(mesh, names, out):
    """One .ply per surface into `out` (an old surface's file removed first, so none reaches the bake); the shares."""
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.ply"):
        old.unlink()
    shares = {}
    for name in sorted(set(names)):
        chosen = np.nonzero(names == name)[0]
        mesh.submesh([chosen], append=True).export(out / f"{name}.ply")
        shares[name] = round(float(mesh.area_faces[chosen].sum() / mesh.area), 3)
    return shares


def write(take, accepted, body_take, size, base, out):
    """The re-made take's parts for its body's bake, in `out`; its labels.json record. Refused (SystemExit) when the
    take names no body or lies too far from the accepted take."""
    if bodies.body_of(body_take) is None:
        raise SystemExit(f"{body_take}: no body in bodies.BODIES")
    turn = bodies.laid_turn(body_take, base)
    mesh = raw_on_finished(take)
    old_middles, old_names = accepted_faces(accepted)
    names, gap = surfaces_from(mesh.triangles_center, old_middles, old_names, turn, size)
    if gap > GAP_MOST:
        raise SystemExit(f"{take}: its faces lie {gap:.3f} of the laid diagonal from {body_take}'s accepted take, "
                         f"over {GAP_MOST}: not labelled from it")
    out = pathlib.Path(out)
    record = {"take": body_take, "made_from": take, "labels_from": str(accepted), "gap": round(gap, 4),
              "shares": write_surfaces(mesh, names, out)}
    (out / "labels.json").write_text(json.dumps(record, indent=1))
    return record


if __name__ == "__main__":
    new_take, accepted_folder, body_name, laid_size, laid_base, folder = sys.argv[1:7]
    print(json.dumps(write(new_take, accepted_folder, body_name, json.loads(laid_size), json.loads(laid_base), folder)))
