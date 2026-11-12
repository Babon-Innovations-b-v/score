"""surfaces-paint's gate "feet in one plane" with a take refused on its resting face alone judged by the resting
check's own measure of its baked model.

The paint's last levelling (place_line.resting_base) reads the face of the model's convex hull straight under its
weight and refuses it as a fault of the model when that face, carried across the whole bottom band, rises more than a
set share of its size. The face's slope says nothing of how far the model is off standing: where the weight lies near
the face's low edge it rests on its low points as it is. Cockpit's pilot seat (2026-11-12): a seat on a pad under a
slightly rising base, its face rising 18.1% of its size across the band, failed "1 of 1 feet end 18.1% ... a missing
leg", while its baked model's weight lies inside what it touches within 3 cm; habitat's sink (46.2%), airlock's open
case (53.6%) and camp's kitchen counter (23.0%, 2.6 cm outside) the same.

So a take whose only refusal is its resting face's (its report's `rests`) passes when each baked model of it stands
by the resting check's measure (tools/usd/triage.py held_up_faults: at least CONTACTS points within TOLERANCE of its
lowest, its weight, the middle of its surface by area, within BALANCE of what they span); one that does not stand
fails, named with how far its weight falls outside. Every other refusal fails as place_line.judge_feet fails it.

Its own module, set on the row in the table (stages.feet_checked), so place_line.py, in the bake's and 84 paid rows'
code, does not move: the bake and its levelling stay as they are, only the gate's judging changes.
"""
import contextlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import place_line  # noqa: E402
import route_paint  # noqa: E402
import surface_gates as gates  # noqa: E402

# The resting check's measure (tools/usd/resting.py TOLERANCE and BALANCE, triage.py CONTACTS_NEEDED), in metres; not
# imported, as resting.py loads OpenUSD, which the prop environment has none of.
TOLERANCE, BALANCE, CONTACTS = 0.03, 0.05, 4
# Surface points sampled beside a model's vertices (triage.py OWN_SAMPLES): a big low-poly base touches over faces
# whose corners lie off the floor.
SAMPLES = 4000


def make_paint(inputs, out, seed, params):
    """route_paint.make_paint with its feet gate (place_line.judge_feet, read when the gates are named) held as this
    module's judge_feet, so the batch gaps it writes are this gate's."""
    with held():
        return route_paint.make_paint(inputs, out, seed, params)


@contextlib.contextmanager
def held():
    """place_line.judge_feet as this module's while the make runs."""
    kept = place_line.judge_feet
    place_line.judge_feet = judge_feet
    try:
        yield
    finally:
        place_line.judge_feet = kept


def judge_feet(output, inputs, evidence):
    """Every painted take's feet lie in one plane in its own frame, a take refused on its resting face alone passing
    when its baked models stand (off_balance)."""
    found = json.loads((pathlib.Path(output) / "painted.json").read_text())["takes"]
    failing, resting = [], 0
    for take, report in found.items():
        feet = report.get("feet", {})
        refused = feet.get("refused") or []
        if not refused:
            continue
        outside = off_balance(inputs.get("surfaces-bake"), take) if refused == [feet.get("rests")] else None
        if outside == 0.0:
            resting += 1
        elif outside is not None:
            off = (f"touches within {TOLERANCE * 100:.0f} cm at under {CONTACTS} points" if outside == float("inf")
                   else f"has its weight {outside:.2f} m outside what it touches within {TOLERANCE * 100:.0f} cm (over "
                        f"{BALANCE * 100:.0f} cm)")
            failing.append(f"{take}: its resting face rises {feet['rests']:.1%} of its size across its base and its "
                           f"baked model {off}: it does not stand")
        else:
            failing.append(f"{take}: {len(refused)} of {feet['feet']} feet end "
                           f"{', '.join(f'{gap:.1%}' for gap in refused)} of its size over its lowest "
                           f"(over {place_line.FOOT_MOST:.0%}: a missing leg, not a short one)")
    levelled = sum(bool(report.get("feet", {}).get("levelled")) for report in found.values())
    return gates.verdict("feet in one plane", failing, len(found), "models with a foot off the plane",
                         {"levelled": levelled, "standing on a refused resting face": resting})


def off_balance(bake, take):
    """How far (metres) the weight of the take's worst baked model falls outside what it stands on, 0.0 when every
    one stands by the resting check's measure (outside_by over BALANCE, or under CONTACTS points touching, counts as
    off); None when the bake or a model of it cannot be read."""
    if bake is None:
        return None
    folder = pathlib.Path(bake)
    entries = folder / "entries" / f"{take}.json"
    if not entries.is_file():
        return None
    worst = 0.0
    for model in json.loads(entries.read_text()):
        gltf = folder / "made" / f"{model}.gltf"
        if not gltf.is_file():
            return None
        outside = standing_gap(*baked_mesh(gltf))
        worst = max(worst, outside if outside > BALANCE else 0.0)
    return worst


def baked_mesh(gltf):
    """A baked .gltf's positions (+y up) and triangles over all its primitives (baked_gltf.read's buffers)."""
    import numpy as np
    import baked_gltf
    import glb_file
    document, views = baked_gltf.read(gltf)
    points, triangles, corners = [], [], 0
    for primitive in baked_gltf.primitives(document):
        found = glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"]).astype(np.float64)
        triangles.append(glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3) + corners)
        points.append(found)
        corners += len(found)
    return np.concatenate(points), np.concatenate(triangles).astype(np.int64)


def standing_gap(points, triangles):
    """How far (metres) a model's weight (its surface's middle by area, resting.weight_at) lies outside the span of
    its points within TOLERANCE of its lowest (resting.outside_by), its points its vertices and SAMPLES of its surface
    as triage.low_points reads them; inf under CONTACTS such points."""
    import numpy as np
    import trimesh
    mesh = trimesh.Trimesh(points, triangles, process=False)
    weight = (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0)[[0, 2]] / mesh.area
    points = np.vstack([points, mesh.sample(SAMPLES, seed=0)])
    footing = points[points[:, 1] <= points[:, 1].min() + TOLERANCE][:, [0, 2]]
    return np.inf if len(footing) < CONTACTS else outside_by(weight, footing)


def outside_by(point, footprint):
    """How far a point (x, z) lies outside the convex hull of the footprint's points (x, z); 0 inside (resting.py's
    outside_by, which this module cannot import)."""
    import numpy as np
    from scipy.spatial import ConvexHull, QhullError
    try:
        corners = footprint[ConvexHull(footprint).vertices]
    except QhullError:  # all on one line: the nearest of them
        return float(np.min(np.linalg.norm(footprint - point, axis=1)))
    edges = np.roll(corners, -1, axis=0) - corners
    across = edges[:, 0] * (point[1] - corners[:, 1]) - edges[:, 1] * (point[0] - corners[:, 0])
    if np.all(across >= 0) or np.all(across <= 0):
        return 0.0
    share = np.clip(np.einsum("ij,ij->i", point - corners, edges) / np.einsum("ij,ij->i", edges, edges), 0.0, 1.0)
    return float(np.min(np.linalg.norm(corners + edges * share[:, None] - point, axis=1)))
