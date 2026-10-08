"""The model gate (G5 of the robust route, job robust-exp 2026-10-06): every kind's real mesh checked before it is
placed, the same way for a generated model and a code-built one.

    ~/.farm-factory-props/env/bin/python tools/props/gates/model.py <layout.json> [--models <folder>] \
        [--kinds k1,k2] [--report <out.json>]

    watertight   whether the mesh is closed
    pieces       how many separate pieces it is in, and the biggest one's share of its area (floaters)
    spread       how far its proportions are from the size it is laid at, on the sides its shape class can be
                 judged on (sorter.py: a flat piece on its face, a slender one not at all, the rest on all three):
                 the largest ratio between model and laid proportion, minus one (the hub kit's 20% rule)
    thinnest     the thinnest wall, in metres once fitted to its laid size: inward rays from 300 surface points,
                 the 5th percentile of how far each goes before leaving the mesh

A kind fails at a spread over 0.2 or a thinnest wall under 3 mm; a failing kind is remade or routed to code, never
stretched and never placed while flagged. A kind of leaves (data/library/details.json `leaves`: a palm's fronds, world
1's square, 2026-10-07) is held to its spread only: a frond is thinner than any wall, and nothing is walked into there.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "library"))
import room  # noqa: E402
import sorter  # noqa: E402

DETAILS = HERE.parents[2] / "data/library/details.json"
SPREAD_LIMIT = 0.2
THINNEST_LIMIT = 0.003
SAMPLES = 300


def raw_model(name, about, folder):
    """A made model's (or a kind's own) mesh as made, turned by its `base` but not fitted, or None."""
    path = ((room.model_file(folder, name) if folder else None) or room.model_file(room.KIT_MODELS, name)
            or room.model_file(room.GAME_MODELS / name, name))
    if path is None:
        return None
    mesh = trimesh.load(path, force="mesh", skip_materials=True)
    mesh.merge_vertices(merge_tex=True, merge_norm=True)  # a .glb splits its vertices at every UV seam
    matrix = np.eye(4)
    matrix[:3, :3] = room.basis(about["base"]) if "base" in about else np.eye(3)
    mesh.apply_transform(matrix)
    return mesh


def spread(extents, laid):
    """The largest model-to-laid proportion error on the sides the laid shape can be judged on: a flat one's face,
    a slender one's none, the rest all three (by the sorter's size rules, whatever the kind is named)."""
    order = np.argsort(laid)
    smallest, middle, largest = np.sort(laid)
    if middle / largest < sorter.SLENDER_SHARE:
        return 0.0
    judged = order[1:] if smallest / largest < sorter.FLAT_SHARE else order
    model = np.array(extents)[judged]
    target = np.array(laid)[judged]
    ratios = (model / model.max()) / (target / target.max())
    return float(max(ratios.max(), 1 / ratios.min()) - 1)


def thinnest(mesh, laid):
    """The 5th-percentile wall thickness once the mesh is fitted to `laid` (inward rays from surface points)."""
    fitted = mesh.copy()
    fitted.vertices = (fitted.vertices - fitted.bounds[0]) / np.maximum(fitted.extents, 1e-6) * np.array(laid)
    points, faces = trimesh.sample.sample_surface(fitted, SAMPLES, seed=0)
    inward = -fitted.face_normals[faces]
    starts = points + inward * 1e-4
    where, index, _ = fitted.ray.intersects_location(starts, inward, multiple_hits=False)
    if len(index) == 0:
        return 0.0
    return float(np.percentile(np.linalg.norm(where - starts[index], axis=1), 5))


def check(kind, mesh, laid):
    shape = sorter.shape_class(kind, laid)
    parts = mesh.split(only_watertight=False) if len(mesh.faces) <= 60000 else [mesh]
    areas = sorted((part.area for part in parts), reverse=True)
    found = {"class": shape, "faces": int(len(mesh.faces)), "watertight": bool(mesh.is_watertight),
             "pieces": len(parts), "biggest_share": round(float(areas[0] / sum(areas)), 3),
             "spread": round(spread(mesh.extents, laid), 3), "thinnest": round(thinnest(mesh, laid), 4)}
    found["pass"] = found["spread"] <= SPREAD_LIMIT and (found["thinnest"] >= THINNEST_LIMIT or leaves(kind))
    return found


def leaves(kind):
    """Whether a kind is leaves (details.json `leaves`), held to its spread alone."""
    return bool(json.loads(DETAILS.read_text()).get(kind, {}).get("leaves", False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("layout", type=pathlib.Path)
    parser.add_argument("--models", type=pathlib.Path)
    parser.add_argument("--kinds")
    parser.add_argument("--prefix", help="only the kinds whose name starts so (a route's new kinds)")
    parser.add_argument("--report", type=pathlib.Path)
    arguments = parser.parse_args()
    layout = json.loads(arguments.layout.read_text())
    wanted = set(arguments.kinds.split(",")) if arguments.kinds else None
    sizes = {}
    for laid in layout["pieces"]:
        name = laid.get("model", laid["kind"])
        about = layout.get("models", {}).get(name, {}) if "model" in laid else layout["kinds"].get(laid["kind"], {})
        sizes.setdefault(name, (laid["kind"], laid["size"], about))
    report = {}
    for name, (kind, laid, about) in sorted(sizes.items()):
        if (wanted and name not in wanted) or (arguments.prefix and not name.startswith(arguments.prefix)):
            continue
        mesh = raw_model(name, about, arguments.models)
        report[name] = check(kind, mesh, laid) if mesh is not None else {"missing": True, "pass": None}
        print(name, report[name], flush=True)
    if arguments.report:
        arguments.report.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
