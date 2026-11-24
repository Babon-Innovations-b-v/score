"""The prop benchmark's calibration pass (#163 step 3, design on #162): free, no model made. Every measure is run on
each NVIDIA truth against a remeshed copy of itself (the known-good ceiling) and against the other assets of its kind
laid at its size (the wrong-object floor); every route check (the model gate, straight.py, place_build shapes'
sausage and lump, patchy) is run on the truth itself; each NVIDIA mass is read against the density of its volume.
A check that fails a known-good asset judges wrongly and is fixed at its source; the bars in measures.BARS are set
from these numbers (the tune split's; the held-out split only confirms them).

    remeshed(truth)              -> the known-good copy: its surface cut again unmoved (each triangle in four), each
                                    finish wearing its matching surface's look (own_looks)
    own_looks(side)              -> {material: look}: each material's library surface's own look, else NVIDIA's own
    cut(truth)                   -> the truth decimated to CUT_SHARE of its triangles, as the route's cut
    route_checks(truth, kind)    -> {"gate", "straight", "shapes", "patchy"} each with its "pass"
    mass_check(truth)            -> {"mass", "volume", "volume_of", "density", "plausible"}
    calibrated(item, mates)      -> one object's record: "good" (the exact copy's measures), "cut", "wrong" (each
                                    other asset's laid at its size, its twins left out), "route" and "mass"
    known_good_rows(record)      -> the copy's judged rows, its cleanliness the truth's own
    spread(records, split)       -> {measure: {test, bar, good: {n, least, p5, median, passed}, wrong: {n, p95,
                                    most, failed}}} over one split: where the known-good and the wrong lie

    python3 -m tools.props.bench.calibrate run [--only <id> ...] [--workers N]   (SCORE_LIB_ROOT a scratch checkout)

A relative bar (times or plus the truth's own value) is read as the value over (or less) the truth's, so the
spread is comparable across assets.
"""
import contextlib
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

import score.stages.props.prop_data as prop_data
from score.stages.place_build import shapes
from tools.props.bench import truth as bench_truth

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "run"))
import finish  # noqa: E402  (the run's finish: a library surface's own look)
import measures  # noqa: E402
from measures import _mesh  # noqa: E402

SUBDIVIDE_MOST = 400000  # triangles a truth may have and be split in four for its known-good copy
CUT_SHARE = 0.5  # the share of its triangles the decimated copy keeps
SQUARE_KINDS = ("box", "crate", "cabinet / locker", "fridge / stove / sink", "monitor / keyboard", "toolbox / tool cart")
DENSITY_LEAST, DENSITY_MOST = 2.0, 8000.0  # kg/m3 of its volume a mass is plausible within (an empty carton, steel)
PERCENT = 95  # the wrong objects' percentile a bar must clear


def carried_over(truth, vertices, faces):
    """Each new face's material: the material of the old face whose middle is nearest its middle."""
    middles = np.asarray(truth["vertices"])[np.asarray(truth["faces"])].mean(1)
    _, nearest = cKDTree(middles).query(vertices[faces].mean(1))
    return np.asarray(truth["face_material"])[nearest]


def own_looks(side):
    """{material: look} for a truth (or another asset laid like one): each material's matching surface as the route
    would set it (#172): its library surface's own look (finish.surface_look) where the surface names a colour,
    else NVIDIA's own on its faces (a surface painted for one model has no recipe), area-weighted."""
    materials = side.get("materials") or []
    addresses = sorted({item["surface"] for item in materials
                        if isinstance(item.get("surface"), str) and item["surface"].startswith("surface/")})
    records = finish.records(addresses) if addresses else {}
    area = _mesh.areas(np.asarray(side["vertices"], dtype=float), np.asarray(side["faces"]))
    face_material = np.asarray(side["face_material"])
    found = {}
    for number, item in enumerate(materials):
        record = records.get(item.get("surface"))
        look = finish.surface_look(record) if record else None
        if look and look["colour"] is not None and look["roughness"] is not None:
            found[number] = look
            continue
        held = np.flatnonzero(face_material == number)
        if not len(held) or side.get("face_look") is None:
            continue
        albedo, metal, roughness, name = measures._finish.true_look(side["face_look"], held, area[held])
        through = measures._finish.true_through(side["face_look"], held, area[held])
        found[number] = {"colour": None if albedo is None else albedo.tolist(), "metal": metal,
                         "roughness": roughness, "class": name,
                         "opacity": None if through is None else 0.0 if through > 0.5 else 1.0}
    return found


def remeshed(truth):
    """The known-good copy: the truth's surface cut again without moving it, each triangle split in four at its edges'
    middles (one over SUBDIVIDE_MOST triangles keeps its own, their order turned round); mass, colliders, friction
    and materials its own. Any measure that fails it judges wrongly."""
    import trimesh
    vertices, faces = np.asarray(truth["vertices"], dtype=float), np.asarray(truth["faces"])
    if len(faces) <= SUBDIVIDE_MOST:
        vertices, faces = trimesh.remesh.subdivide(vertices, faces)
        material = np.repeat(np.asarray(truth["face_material"]), 4)
    else:
        faces, material = faces[::-1], np.asarray(truth["face_material"])[::-1]
    return {**sided(truth), "vertices": vertices, "faces": faces, "face_material": material,
            "box": [vertices.min(0), vertices.max(0)], "looks": own_looks(truth)}


def cut(truth):
    """The truth cut to CUT_SHARE of its triangles (fast_simplification), as the route's triangle cut: how a measure
    meets a sound shape decimated (reported beside the known-good copy, never a bar's ceiling)."""
    import fast_simplification
    vertices, faces = fast_simplification.simplify(np.asarray(truth["vertices"], dtype=np.float32),
                                                   np.asarray(truth["faces"], dtype=np.int32), 1 - CUT_SHARE)
    vertices, faces = vertices.astype(float), faces.astype(np.int64)
    return {**sided(truth), "vertices": vertices, "faces": faces,
            "face_material": carried_over(truth, vertices, faces), "box": [vertices.min(0), vertices.max(0)]}


def sided(truth):
    """The truth's physics as a made side carries it."""
    return {"mass": truth["mass"], "colliders": truth["colliders"], "friction": truth["friction"]}


def y_up(vertices):
    """Z-up points in the kit frame the gate and straight.py read: x across, y up, z depth (toward the viewer)."""
    return np.stack([vertices[:, 0], vertices[:, 2], -vertices[:, 1]], 1)


@contextlib.contextmanager
def tool(*folders):
    with prop_data.tools(*folders):
        yield


def route_checks(truth, kind):
    """The route's own checks on the truth as a made model would meet them: the model gate at its true size,
    straight.py (judged only for a square kind), shapes' sausage and lump by its id, patchy on NVIDIA's materials
    (parts: its meshes)."""
    import trimesh
    corners, welded = _mesh.welded(np.asarray(truth["vertices"], dtype=float), np.asarray(truth["faces"]))
    standing = trimesh.Trimesh(y_up(corners), welded, process=False)
    with tool("props/gates", "props/library", "props"):
        import model as gate
        import patchy
        import straight
    wide, deep, tall = truth["size"]
    found = {"gate": gate.check(truth["id"], standing, [wide, tall, deep]),
             "straight": {**straight.straightness(standing), "judged": kind in SQUARE_KINDS}}
    shape = shapes.shape_of(corners, welded)
    told = shapes.shape_faults({"id": truth["id"]}, shape)
    found["shapes"] = {"flat": round(shape.flat, 4), "run": round(shape.run, 3), "swell": round(shape.swell, 4),
                       "faults": [fault["kind"] for fault in told], "pass": not told}
    patched = patchy.score(trimesh.Trimesh(corners, welded, process=False), np.asarray(truth["face_material"]),
                           parts=np.asarray(truth["face_prim"]))
    found["patchy"] = patched
    found["straight"]["pass"] = found["straight"]["pass"] or not found["straight"]["judged"]
    return found


def mass_check(truth):
    """NVIDIA's mass against the density of its volume (the closed mesh's, else its colliders' joined hulls):
    plausible between DENSITY_LEAST and DENSITY_MOST; flagged, never used blind."""
    import trimesh
    closed = trimesh.Trimesh(*_mesh.welded(np.asarray(truth["vertices"], dtype=float), np.asarray(truth["faces"])),
                             process=False)
    if closed.is_watertight and abs(closed.volume) > 0:
        volume, volume_of = abs(float(closed.volume)), "mesh"
    else:
        volume, volume_of = measures._physics.joined_volume(measures._physics.hulls(truth["colliders"])), "colliders"
    density = truth["mass"] / volume if truth["mass"] and volume else None
    return {"mass": truth["mass"], "volume": round(volume, 6), "volume_of": volume_of,
            "density": round(density, 2) if density else None,
            "plausible": bool(density and DENSITY_LEAST <= density <= DENSITY_MOST)}


def plain(value):
    """A JSON-able copy (numpy arrays and scalars as lists and numbers)."""
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def calibrated(item, mates):
    """One object's calibration (the module docstring): `item` its set row, `mates` its kind's other set rows. Every
    measures result is kept whole, so the spread is judged again at whatever bars stand."""
    truth = measures.by_finish(bench_truth.read(item["address"]))
    others = [{**bench_truth.read(mate["address"]), "id": mate["address"]} for mate in mates]
    good = measures.measured(truth, remeshed(truth), others=others)
    decimated = measures.measured(truth, cut(truth))
    wrong = [{"other": other["id"], "found": plain(measures.measured(truth, {**measures.laid_like(other, truth),
                                                                             "looks": own_looks(other)}))}
             for other in others if not measures.twin(other, truth)]
    return plain({"address": item["address"], "kind": item["kind"], "split": item["split"],
                  "faces": int(len(truth["faces"])), "good": plain(good), "cut": plain(decimated), "wrong": wrong,
                  "twins": [other["id"] for other in others if measures.twin(other, truth)],
                  "route": route_checks(truth, item["kind"]), "mass": mass_check(truth)})


def known_good_rows(record):
    """The known-good rows: the exact copy's, its cleanliness the truth's own (the copy is the truth's surface)."""
    good = record["good"]
    itself = {"clean": good["truth_clean"], "truth_clean": good["truth_clean"], "truth_sides": good["truth_sides"]}
    return [row for row in measures.judged(good)["rows"] if not row["measure"].startswith("clean.")] \
        + measures.judged(itself)["rows"]


def compared(row, truth_clean, test):
    """A judged row's value read against the truth's own (over it for a times bar, less it for a plus bar)."""
    own = truth_clean.get(row["measure"].split(".", 1)[1])
    if test.startswith("times_truth") and own:
        return row["value"] / own
    if test == "plus_truth_most" and own is not None:
        return row["value"] - own
    return row["value"]


def stats(values, percentile):
    found = np.asarray(values, dtype=float)
    return {"n": int(len(found)), "least": round(float(found.min()), 4), "most": round(float(found.max()), 4),
            "p5": round(float(np.percentile(found, 5)), 4), "median": round(float(np.median(found)), 4),
            f"p{percentile}": round(float(np.percentile(found, percentile)), 4)}


def spread(records, split):
    """Per measure over one split, judged at measures.BARS as they stand: the known-good copies' values and share
    passing, the decimated copies' the same, the wrong objects' values and share failing (each read against the
    truth's own for a relative bar)."""
    sides = {"good": {}, "cut": {}, "wrong": {}}
    for record in records:
        if record["split"] != split:
            continue
        own = record["good"]["truth_clean"]
        judged = {"good": known_good_rows(record), "cut": measures.judged(record["cut"])["rows"],
                  "wrong": [row for pair in record["wrong"] for row in measures.judged(pair["found"])["rows"]]}
        for side, rows in judged.items():
            for row in rows:
                sides[side].setdefault(row["measure"], []).append((row, own))
    found = {}
    for group, measure, test, bound in measures.BARS:
        name = f"{group}.{measure}"
        entry = {"test": test, "bar": bound}
        for side, rows in ((side, sides[side].get(name)) for side in sides):
            if not rows:
                continue
            values = [float(compared(row, own, test)) for row, own in rows]
            held = float(np.mean([row["pass"] for row, _ in rows]))
            entry[side] = {**stats(values, PERCENT if side == "wrong" else 5),
                           **({"failed": round(1 - held, 3)} if side == "wrong" else {"passed": round(held, 3)})}
        found[name] = entry
    return found
