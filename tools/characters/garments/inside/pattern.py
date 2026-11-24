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
path>": value}}]}.

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


def pattern(garmentcode, measurements_file, garment, folder):
    """The garment's sewing pattern on the body, serialised in `folder`; its specification file."""
    import yaml
    from assets.bodies.body_params import BodyParameters
    from assets.garment_programs.meta_garment import MetaGarment
    design = design_of(garmentcode, garment)
    body = BodyParameters(str(measurements_file))
    made = MetaGarment(garment["name"], body, design)
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
        spec = pattern(job["garmentcode"], measurements, garment, folder)
        box = boxmeshgen.BoxMesh(str(spec), float(job["resolution"]))
        box.load()
        record = box_record(box)
        np.savez(folder / f"{garment['name']}.npz", **record)
        print(f"{garment['name']}: {len(record['points'])} points, {len(record['faces'])} triangles, "
              f"{len(record['panel_names'])} panels", flush=True)


if __name__ == "__main__":
    given = arguments()
    use_garmentcode(given["garmentcode"])
    made(given)
