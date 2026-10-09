"""A garment for one body, up to the cloth Blender drapes: the design sized to the body by GarmentCode's own
measurements, the sewing pattern, GarmentCode's box mesh, and the box mesh cut back into its panels for sewing.

GarmentCode (MIT, https://github.com/maria-korosteleva/GarmentCode at commit d449629) makes the pattern and the box
mesh; both are plain geometry, no model. Its simulation is not used: it ran on a fork of NVIDIA Warp whose licence
allows non-commercial research only (2026-10-09), so the cloth is draped by Blender instead (`cloth_drape.py`). This
file runs in a GarmentCode environment: Python 3.10 with GarmentCode's requirements (pygarment, its CGAL bindings,
igl, trimesh, scipy, yaml) and GarmentCode's folder named by GARMENTCODE (default
~/.farm-factory-motion/rnd/garmentcode/GarmentCode). Nothing here imports warp; a run fails if it is imported.

    python garment.py measure <body.npz> <work folder> [mean_male|mean_female]
    python garment.py pattern <design folder> <work folder> <name> [key=value ...]
    python garment.py box <work folder> <name> <resolution scale> [<tag>]

`measure` writes <work>/bodies/ours.yaml (GarmentCode's measurements of the body, in centimetres),
ours.obj (the body in metres, GarmentCode's body file) and ggg_body_segmentation.json; `pattern` writes
<work>/patterns/<name>/ (<name>_specification.json, design.yaml); `box` writes <work>/box/<tag or name>/ with
GarmentCode's box mesh files (<tag>_boxmesh.obj, <tag>_sim_segmentation.txt, <tag>_vertex_labels.yaml,
<name>_specification.json) and <tag>_sewing.npz, the box mesh's panels apart again for Blender (`sewing.py` says
what is in it).

The body file (<body.npz>) holds points (metres, y up, feet at 0), faces, joint_names and weights: the people tools'
bind-pose body, as 2099's rnd/people/nev_mars/scripts/measure.py read it (ported here unchanged in what it measures).
"""
import json
import os
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sewing  # noqa: E402

GARMENTCODE = pathlib.Path(os.environ.get(
    "GARMENTCODE", pathlib.Path.home() / ".farm-factory-motion/rnd/garmentcode/GarmentCode"))
GARMENTCODE_COMMIT = "d449629"
# Body parts a point belongs to, by the joint that holds it most: GarmentCode's names for them.
LIMB_JOINTS = {"arm": ("Arm", "ForeArm", "Hand"), "leg": ("Leg", "Shin", "Foot", "Toe")}


def use_garmentcode():
    """GarmentCode's folder on the import path, warp refused, and its 'system.json' looked for in the working folder
    (GarmentCode reads it from there)."""
    sys.modules["warp"] = None
    sys.path.insert(0, str(GARMENTCODE))


# ---- measuring the body (2099's measure.py) ---------------------------------------------------------------------

def reference_body(reference):
    """GarmentCode's own body (mean_male or mean_female) and each point's part."""
    import trimesh
    bodies = GARMENTCODE / "assets" / "bodies"
    mesh = trimesh.load(bodies / f"{reference}.obj", process=False)
    labels = np.full(len(mesh.vertices), "body", dtype=object)
    for name, ids in json.loads((bodies / "ggg_body_segmentation.json").read_text()).items():
        labels[np.array(ids, dtype=int)] = name
    return mesh, labels


def part_of(joint):
    """The part a joint's points belong to: left_arm, right_arm, left_leg, right_leg or body."""
    for side in ("Left", "Right"):
        for limb, words in LIMB_JOINTS.items():
            if joint.startswith(side) and any(word in joint for word in words):
                return f"{side.lower()}_{limb}"
    return "body"


def our_body(body_file):
    """The body to dress and each point's part, by the joint that holds it most."""
    import trimesh
    data = np.load(body_file)
    mesh = trimesh.Trimesh(data["points"], data["faces"], process=False)
    names = [str(name) for name in data["joint_names"]]
    labels = np.array([part_of(names[joint]) for joint in data["weights"].argmax(axis=1)], dtype=object)
    return mesh, labels


def submesh(mesh, labels, keep):
    """The faces whose corners all belong to the kept parts."""
    import trimesh
    mask = np.isin(labels, keep)
    return trimesh.Trimesh(mesh.vertices, mesh.faces[mask[mesh.faces].all(axis=1)], process=False)


def girth(mesh, origin, normal):
    """A tape measure's girth: the perimeter of the convex hull of the cross-section."""
    from scipy.spatial import ConvexHull
    section = mesh.section(plane_origin=origin, plane_normal=normal)
    if section is None:
        return 0.0
    normal = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    helper = np.array([1.0, 0, 0]) if abs(normal[0]) < 0.9 else np.array([0, 0, 1.0])
    first = np.cross(normal, helper)
    first /= np.linalg.norm(first)
    second = np.cross(normal, first)
    raw = np.asarray(section.vertices) - origin
    flat = np.stack([raw @ first, raw @ second], axis=1)
    if len(flat) < 3:
        return 0.0
    return float(ConvexHull(flat).area)  # in two dimensions the hull's 'area' is its perimeter


def torso_girths(mesh, labels):
    """Height, and the bust, waist and hips as (girth, level as a share of the height)."""
    torso = submesh(mesh, labels, ["body"])
    floor = mesh.vertices[:, 1].min()
    height = mesh.vertices[:, 1].max() - floor

    def scan(low, high):
        return [(girth(torso, [0, floor + level * height, 0], [0, 1, 0]), level)
                for level in np.linspace(low, high, 25)]

    return height, max(scan(0.70, 0.76)), min(scan(0.58, 0.66)), max(scan(0.47, 0.55))


def thigh(mesh, labels):
    """The left thigh's largest girth."""
    leg = submesh(mesh, labels, ["left_leg"])
    floor = mesh.vertices[:, 1].min()
    height = mesh.vertices[:, 1].max() - floor
    return max(girth(leg, [0, floor + level * height, 0], [0, 1, 0]) for level in np.linspace(0.36, 0.44, 17))


def arm_numbers(mesh, labels):
    """The left arm's angle below the horizontal (degrees), its length and its wrist's girth."""
    points = mesh.vertices[labels == "left_arm"]
    centre = points.mean(axis=0)
    axis = np.linalg.svd(points - centre)[2][0]
    if axis[1] > 0:
        axis = -axis
    along = (points - centre) @ axis
    length = along.max() - along.min()
    arm = submesh(mesh, labels, ["left_arm"])
    wrists = [girth(arm, centre + axis * (along.min() + share * length), axis) for share in np.linspace(0.62, 0.8, 19)]
    return float(np.degrees(np.arcsin(-axis[1]))), length, min(value for value in wrists if value > 0)


def shoulder_width(mesh, labels):
    """The gap between the tops of the two arms."""
    left = mesh.vertices[labels == "left_arm"]
    right = mesh.vertices[labels == "right_arm"]
    top_left = left[left[:, 1] > left[:, 1].max() - 0.03]
    top_right = right[right[:, 1] > right[:, 1].max() - 0.03]
    return float(top_left[:, 0].min() - top_right[:, 0].max())


def measure(mesh, labels):
    """The numbers both bodies are measured by, the same way, so their ratios size GarmentCode's measurements."""
    height, bust, waist, hips = torso_girths(mesh, labels)
    angle, arm_length, wrist = arm_numbers(mesh, labels)
    return {"height": height, "bust": bust[0], "waist": waist[0], "hips": hips[0], "leg_circ": thigh(mesh, labels),
            "arm_pose_angle": angle, "arm_length": arm_length, "wrist": wrist,
            "shoulder_w": shoulder_width(mesh, labels)}


def write_body(body_file, work, reference):
    """GarmentCode's body files for the body: bodies/ours.yaml, ours.obj and ggg_body_segmentation.json."""
    import yaml
    theirs_mesh, theirs_labels = reference_body(reference)
    ours_mesh, ours_labels = our_body(body_file)
    theirs, ours = measure(theirs_mesh, theirs_labels), measure(ours_mesh, ours_labels)
    base = yaml.safe_load((GARMENTCODE / "assets" / "bodies" / f"{reference}.yaml").read_text())["body"]
    folder = pathlib.Path(work) / "bodies"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "ours.yaml").write_text(yaml.safe_dump({"body": sewing.sized_measurements(base, theirs, ours)}))
    parts = {name: np.where(ours_labels == name)[0].tolist()
             for name in ("body", "left_arm", "right_arm", "left_leg", "right_leg")}
    parts["face_internal"] = []
    (folder / "ggg_body_segmentation.json").write_text(json.dumps(parts))
    ours_mesh.export(folder / "ours.obj")
    (folder / "measured.json").write_text(json.dumps({"reference": reference, "theirs": theirs, "ours": ours},
                                                     indent=1, default=float))


# ---- the pattern and the box mesh --------------------------------------------------------------------------------

def write_system(work):
    """GarmentCode's system.json in the work folder (it reads the body's folder from it)."""
    work = pathlib.Path(work).resolve()
    (work / "system.json").write_text(json.dumps({
        "output": str(work / "box"), "datasets_path": "", "datasets_sim": "", "sim_configs_path": "",
        "bodies_default_path": str(work / "bodies"), "body_samples_path": ""}, indent=1))


def sized_design(design_folder, overrides):
    """The design's parameters with each override (dotted path=value) put in."""
    import yaml
    design = yaml.safe_load((pathlib.Path(design_folder) / "design.yaml").read_text())["design"]
    for path, value in overrides.items():
        node = design
        for key in path.split("."):
            node = node[key]
        node["v"] = value
    return design


def write_pattern(design_folder, work, name, overrides):
    """The sewing pattern of the design on the measured body, in <work>/patterns/<name>/."""
    import yaml
    use_garmentcode()
    from assets.bodies.body_params import BodyParameters
    from assets.garment_programs.meta_garment import MetaGarment
    work = pathlib.Path(work).resolve()
    design = sized_design(design_folder, overrides)
    body = BodyParameters(str(work / "bodies" / "ours.yaml"))
    garment = MetaGarment(name, body, design)
    built = garment.assembly()
    if garment.is_self_intersecting():
        print(f"the pattern {name} has panels crossing themselves; its drape may fail")
    (work / "patterns").mkdir(exist_ok=True)
    folder = pathlib.Path(built.serialize(str(work / "patterns"), tag="", to_subfolder=True, with_3d=False,
                                          with_text=False, view_ids=False, with_printable=True))
    body.save(str(folder))
    (folder / "design.yaml").write_text(yaml.safe_dump({"design": design}))
    print("pattern in", folder)
    return folder


def write_box_mesh(work, name, resolution, tag=None):
    """GarmentCode's box mesh of the pattern <name> at a spacing of `resolution` centimetres and its sewing record, in
    <work>/box/<tag>/ (its files named <tag>_..., `tag` the pattern's name unless given)."""
    tag = tag or name
    use_garmentcode()
    from pygarment.meshgen import boxmeshgen
    from pygarment.meshgen.sim_config import PathCofig
    # GarmentCode's warning for an edge meshed with only two points names `self.name`, which an Edge never has; a
    # small body's short edges reached it and it crashed the mesher (2099's gc.py).
    boxmeshgen.Edge.name = "edge"
    work = pathlib.Path(work).resolve()
    write_system(work)
    os.chdir(work)
    paths = PathCofig(in_element_path=work / "patterns" / name, out_path=str(work / "box"), in_name=name,
                      out_name=tag, body_name="ours", smpl_body=False, add_timestamp=False)
    box = boxmeshgen.BoxMesh(paths.in_g_spec, float(resolution))
    box.load()
    box.serialize(paths, store_panels=False, uv_config={"seam_width": 0.5, "dpi": 300})
    np.savez(paths.out_el / f"{tag}_sewing.npz", **panels_apart(box), **waist_of(box, work / "bodies" / "ours.yaml"))
    print("box mesh in", paths.out_el)
    return paths.out_el


def waist_of(box, measurements):
    """Where GarmentCode holds a garment's waist while it drapes (its Warp run's 'lower_interface' attachment): the
    box mesh points so labelled, the body's waist level and its height (centimetres)."""
    import yaml
    body = yaml.safe_load(pathlib.Path(measurements).read_text())["body"]
    level = body.get("_waist_level", body["height"] - body["head_l"] - body["waist_line"])
    return {"waist_points": np.array(box.vertex_labels.get("lower_interface", []), dtype=np.int64),
            "waist_level": float(level), "height": float(body["height"])}


def panels_apart(box):
    """The box mesh with every panel its own piece again: each panel's points where GarmentCode laid the panel
    round the body, its triangles, and for each point the box mesh point it is (the seams' points are shared there).

    GarmentCode's box mesh shares a seam's points between its two panels, halfway across the gap, and leaves the
    true lengths in a side file for Warp; Blender keeps the rest lengths its mesh starts with, so it sews panels
    that are flat and true instead and pulls the seams shut (`sewing.seams`)."""
    points, faces, box_index, panel_of = [], [], [], []
    for number, panel_name in enumerate(box.panelNames):
        panel = box.panels[panel_name]
        start = len(points)
        placed = panel.rot_trans_panel(panel.panel_vertices)
        for local in range(len(placed)):
            if local < panel.n_stitches:
                box_index.append(box.verts_loc_glob[(panel_name, local)])
            else:
                box_index.append(local + panel.glob_offset - panel.n_stitches)
        points.extend(np.asarray(placed, dtype=float))
        panel_of.extend([number] * len(placed))
        for face in panel.panel_faces:
            corners = [box_index[start + int(local)] for local in face]
            if len(set(corners)) == 3:  # GarmentCode drops a triangle its seams fold to a line; so does this
                faces.append([start + int(local) for local in face])
    return {"points": np.array(points), "faces": np.array(faces, dtype=np.int64),
            "box_index": np.array(box_index, dtype=np.int64), "panel": np.array(panel_of, dtype=np.int64),
            "panel_names": np.array(box.panelNames)}


def overrides_of(arguments):
    """key=value arguments as a design's overrides, each value read as YAML."""
    import yaml
    return {key: yaml.safe_load(value) for key, value in (argument.split("=", 1) for argument in arguments)}


def main():
    command, *arguments = sys.argv[1:]
    if command == "measure":
        write_body(arguments[0], arguments[1], arguments[2] if len(arguments) > 2 else "mean_male")
    elif command == "pattern":
        write_pattern(arguments[0], arguments[1], arguments[2], overrides_of(arguments[3:]))
    elif command == "box":
        write_box_mesh(*arguments[:4])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
