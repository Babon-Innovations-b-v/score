"""Runs in GarmentCode's own Python (inside/garment_env.sh, pinned; pygarment, MIT): each garment of an outfit as a
GarmentCode sewing pattern sized to one body's measurements, then its box mesh: the panels triangulated flat and laid
round the body, their seams sewn shut by sharing points. GarmentCode's simulation is never imported (its Warp fork is
non-commercial): `warp` is refused before GarmentCode loads.

    <env>/bin/python tools/characters/garments/inside/pattern.py <job.json>

job.json (written by tools/characters/garments): {"garmentcode": <GarmentCode's folder>, "out": <folder>,
"measured": {the body's own measurements, ../measure.py `measured`}, "mean": "mean_female" or "mean_male" (the
GarmentCode mean body whose measurement file carries the rest over, ../measure.py `sized`), "resolution": <cm
between mesh points>,
"garments": [{"name", "design": <a design file of GarmentCode's assets/design_params>, "set": {"<dotted design
path>": value}, "knee_ease_cm": <optional: a Pants leg taken in at the knee to the knee's girth and this, `slim_legs`>}]}.

Writes <out>/measurements.yaml and .json (the 26 measurements the patterns are sized to) and <out>/<name>/ for each
garment: GarmentCode's pattern (<name>_specification.json, design.yaml, the body's
measurements) and <name>.npz, the garment as the drape reads it (centimetres, GarmentCode's frame: y up, facing +z):
    points      the box mesh's points, each seam's point shared by the panels it joins
    copies      every panel's own points laid round the body (a seam's point once in each panel it joins)
    box         for each copy, the box mesh point it is
    panel       for each copy, its panel's number; panel_names names them
    flat        for each copy, its place on its flat panel (cm): the cloth's rest shape and its texture coordinates
    faces       the panels' triangles, as indices into copies (a triangle a seam folds to a line is dropped)
    label/<l>   the box mesh points GarmentCode labels <l> (its edges' labels: `lower_interface` a garment's top at
                the waist, `right_collar` and `left_collar` a neckline's sides)
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import measure  # noqa: E402  (numpy and scipy only, shared with the score side)


def arguments():
    given = sys.argv[1:]
    if len(given) != 1:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text())


def use_garmentcode(folder):
    """GarmentCode's folder on the import path and its non-commercial simulator's Warp refused."""
    sys.modules["warp"] = None
    sys.path.insert(0, str(folder))


def design_of(garmentcode, garment):
    """The garment's design: its design file's parameters with each `set` path given its value."""
    import yaml
    design = yaml.safe_load((pathlib.Path(garmentcode) / "assets/design_params" / garment["design"]).read_text())
    design = design["design"]
    for path, value in garment.get("set", {}).items():
        node = design
        for key in path.split("."):
            node = node[key]
        node["v"] = value
    return design


def height_share(edge, height):
    """The share (0 to 1) along an edge's curve where it reaches `height` (its y; the edge rises or falls throughout)."""
    curve = edge.as_curve()
    rising = curve.point(1.0).imag > curve.point(0.0).imag
    low, high = 0.0, 1.0
    for _ in range(50):
        middle = (low + high) / 2.0
        if (curve.point(middle).imag < height) == rising:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def across_at(edge, height):
    """The edge's x where it reaches `height`."""
    return float(edge.as_curve().point(height_share(edge, height)).real)


def across_on(edges, height):
    """The x where the one of `edges` that spans `height` reaches it."""
    spanning = [edge for edge in edges if min(edge.start[1], edge.end[1]) <= height <= max(edge.start[1], edge.end[1])]
    return across_at(spanning[0], height)


def split_at(panel, edge, height, shift):
    """The panel's edge split where it reaches `height`, that point moved `shift` along x, in the panel's outline and
    in every interface of the panel the edge is in, the half at the hem first: a stitch pairs its two interfaces'
    edges in order, and a back panel's leg seams run the other way round its outline from the front's (in outline
    order, the front's hem half was sewn to the back's upper half)."""
    import pygarment as pyg
    share = height_share(edge, height)
    pieces = edge.subdivide_param([share, 1.0 - share])
    pieces[0].end[0] += shift
    panel.edges.substitute(edge, pieces)
    low, high = sorted(pieces, key=lambda piece: min(piece.start[1], piece.end[1]))
    for interface in panel.interfaces.values():
        if any(own is edge for own in interface.edges):
            interface.substitute(edge, pyg.EdgeSequence(low, high), [panel, panel])


def stitches_matched(made):
    """Every stitch of the garment whose two sides no longer split alike matched again (GarmentCode's own
    StitchingRule.match_interfaces): a leg's seams split at the knee after its stitches were matched."""
    stack = [made]
    while stack:
        part = stack.pop()
        for rule in getattr(getattr(part, "stitching_rules", None), "rules", []):
            if not rule.isMatching():
                rule.match_interfaces()
        if hasattr(part, "_get_subcomponents"):
            stack.extend(part._get_subcomponents())


def slim_legs(made, body, design, legs, ease):
    """A Pants leg taken in at the knee (cm): GarmentCode cuts each leg panel straight from the thigh to the hem, so
    a slim leg cut to its thigh and a 37 cm hem stood 56 cm round her 37 cm knee and gathered in folds at the calf
    as she walked (#225 round 6). Each leg panel's outseam and inseam get a point at the knee's height as cut (the
    hem stands (1 - pants.length) of GarmentCode's leg length over the sole), moved in by a quarter of what the leg's
    two panels measure there past the knee's girth and `ease`. A leg left narrower than the calf's girth at the calf's
    height is refused."""
    import pygarment as pyg
    hem_at = (1.0 - design["pants"]["length"]["v"]) * body["_leg_length"]
    panels = {}
    stack = [made]
    while stack:
        part = stack.pop()
        if isinstance(part, pyg.Panel):
            panels[part.name] = part
        elif hasattr(part, "_get_subcomponents"):
            stack.extend(part._get_subcomponents())
    for tag in ("r", "l"):
        pair = [panels[f"pant_{side}_{tag}"] for side in ("f", "b")]
        seams = [(panel, panel.interfaces["outside"].edges[0], panel.interfaces["inside"].edges[0]) for panel in pair]
        hem = [min(vertex[1] for edge in panel.edges for vertex in (edge.start, edge.end)) for panel in pair]
        knee = [low + legs["knee_h"] - hem_at for low in hem]
        wide = sum(abs(across_at(inside, level) - across_at(outside, level))
                   for (_, outside, inside), level in zip(seams, knee))
        take = (wide - legs["knee_circ"] - ease) / 4.0
        if take <= 0.0:
            continue
        for (panel, outside, inside), level in zip(seams, knee):
            inward = np.sign(across_at(inside, level) - across_at(outside, level))
            split_at(panel, outside, level, inward * take)
            split_at(panel, inside, level, -inward * take)
        calf = [low + legs["calf_h"] - hem_at for low in hem]
        round_calf = sum(abs(across_on(panel.interfaces["inside"].edges, level)
                             - across_on(panel.interfaces["outside"].edges, level))
                         for panel, level in zip(pair, calf))
        if round_calf < legs["calf_circ"]:
            raise SystemExit(f"pants leg {tag}: {round_calf:.1f} cm round at the calf, under its "
                             f"{legs['calf_circ']:.1f} cm girth")
        print(f"pants leg {tag}: {wide:.1f} cm round at the knee taken in to {wide - 4.0 * take:.1f} "
              f"(knee {legs['knee_circ']:.1f} + {ease}); {round_calf:.1f} cm round at the calf "
              f"({legs['calf_circ']:.1f})", flush=True)


def pattern(garmentcode, measurements_file, garment, folder, legs):
    """The garment's sewing pattern on the body, serialised in `folder`; its specification file."""
    import yaml
    from assets.bodies.body_params import BodyParameters
    from assets.garment_programs.meta_garment import MetaGarment
    design = design_of(garmentcode, garment)
    body = BodyParameters(str(measurements_file))
    made = MetaGarment(garment["name"], body, design)
    if garment.get("knee_ease_cm") is not None:
        slim_legs(made, body, design, legs, float(garment["knee_ease_cm"]))
        stitches_matched(made)
    built = made.assembly()
    if made.is_self_intersecting():
        raise SystemExit(f"{garment['name']}: GarmentCode's pattern has panels crossing themselves")
    written = pathlib.Path(built.serialize(str(folder.parent), tag="", to_subfolder=True, with_3d=False,
                                           with_text=False, view_ids=False, with_printable=False))
    (written / "design.yaml").write_text(yaml.safe_dump({"design": design}))
    return written / f"{garment['name']}_specification.json"


def box_record(box):
    """The box mesh as the drape reads it (the module docstring's npz fields)."""
    copies, flat, box_index, panel_of, faces = [], [], [], [], []
    for number, name in enumerate(box.panelNames):
        panel = box.panels[name]
        start = len(copies)
        local = np.asarray(panel.panel_vertices, dtype=float)
        laid = panel.rot_trans_panel(local)
        for index in range(len(local)):
            if index < panel.n_stitches:
                box_index.append(box.verts_loc_glob[(name, index)])
            else:
                box_index.append(index + panel.glob_offset - panel.n_stitches)
        copies.extend(np.asarray(laid, dtype=float))
        flat.extend(local[:, :2])
        panel_of.extend([number] * len(local))
        for face in panel.panel_faces:
            corners = [box_index[start + int(corner)] for corner in face]
            if len(set(corners)) == 3:
                faces.append([start + int(corner) for corner in face])
    return {"points": np.asarray(box.vertices, dtype=float), "copies": np.asarray(copies),
            "box": np.asarray(box_index, dtype=np.int64), "panel": np.asarray(panel_of, dtype=np.int64),
            "panel_names": np.asarray(box.panelNames), "flat": np.asarray(flat),
            "faces": np.asarray(faces, dtype=np.int64),
            **{f"label/{name}": np.asarray(points, dtype=np.int64) for name, points in box.vertex_labels.items()}}


def made(job):
    """Every garment's pattern and box mesh in the job's folder."""
    import yaml
    from pygarment.meshgen import boxmeshgen
    # GarmentCode's warning for an edge meshed with two points names `self.name`, which an Edge never has.
    boxmeshgen.Edge.name = "edge"
    out = pathlib.Path(job["out"])
    mean = yaml.safe_load((pathlib.Path(job["garmentcode"]) / "assets/bodies" / f"{job['mean']}.yaml").read_text())
    measurements = out / "measurements.yaml"
    sized = measure.sized(mean["body"], job["measured"])
    measurements.write_text(yaml.safe_dump({"body": sized}))
    (out / "measurements.json").write_text(json.dumps(sized, indent=1))
    for garment in job["garments"]:
        folder = out / garment["name"]
        folder.mkdir(parents=True, exist_ok=True)
        spec = pattern(job["garmentcode"], measurements, garment, folder, job["measured"])
        box = boxmeshgen.BoxMesh(str(spec), float(job["resolution"]))
        # The box mesh's own look for panels crossing themselves only warns (a coat's SimpleLapel, 2026-11-24).
        if box.is_self_intersecting():
            raise SystemExit(f"{garment['name']}: GarmentCode's box mesh has panels crossing themselves")
        box.load()
        record = box_record(box)
        np.savez(folder / f"{garment['name']}.npz", **record)
        print(f"{garment['name']}: {len(record['points'])} points, {len(record['faces'])} triangles, "
              f"{len(record['panel_names'])} panels", flush=True)


if __name__ == "__main__":
    given = arguments()
    use_garmentcode(given["garmentcode"])
    made(given)
