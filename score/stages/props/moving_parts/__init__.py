"""Objects with moving parts built in code, its parts apart and each pivot where it turns (#19, decided 2026-11-05: one
Pixal3D model cannot open or turn; organic one-piece objects stay on Pixal3D): a double door's two leaves on their
outer edges in a still frame, a hatch's lid on the hinge along one edge of its still frame, a wheeled vehicle's body
and its wheels on their axles. Every part names the library recipe it is finished with (data/library/materials.json
`recipes`, the scene library's variant of it chosen by the finish route), never a colour of its own.

    parted(row, kinds)     the parted rule a scene inventory row takes ("double door", "hatch", "wheeled"), else None
    build(row, kinds)      (trimesh.Scene, record): its parts at the row's size, in a final take's frame (y up, the
                           longer ground side along z, centred on the origin over its floor), each part a node of its
                           own whose origin is its pivot
    write(row, kinds, folder)   its model (`model.glb`) and its record (`parts.json`) in the folder

A part's node is named `<part>__<joint>_<axis>[n]` (joint `hinge` or `spin`, axis x, y or z in the object's own frame,
`n` for the negative way round), a still part by its name alone: the motion layer reads joints off those names
(score/stages/motion/from_design.parts_of), so the name is the pivot's whole interface.
"""
import json
import pathlib

import numpy as np

from score.stages import row_kinds

# Share of a door's width each jamb takes, and of its height the head; of a hatch's side its frame rim.
JAMB_SHARE, HEAD_SHARE, RIM_SHARE = 0.06, 0.05, 0.1
# Share of the frame's depth a leaf or lid takes (it sits inside its frame's depth).
LEAF_SHARE = 0.6
# A wheel's diameter as a share of the vehicle's height, its width as a share of the vehicle's width, and its axle's
# place along the vehicle's length from each end, as a share of the length.
WHEEL_TALL, WHEEL_WIDE, AXLE_IN = 0.45, 0.14, 0.2
# How round a wheel is drawn (faces round its tread).
WHEEL_FACES = 32
# Words of a vehicle that runs on tracks, not on wheels that turn alone (a tracked rover is one piece).
TRACKED = ("tracked", "track", "tracks", "crawler")
VEHICLES = ("vehicle",)
RECIPES = "data/library/materials.json"


def parted(row, kinds):
    """The parted rule a row takes: "double door" (a door kind whose words say double), "hatch" (a door kind whose
    noun is a hatch, or which lies lower than it is wide both ways), "wheeled" (a vehicle not on tracks, its noun
    not a drone), else None (a single hinged, sliding or rising door moves whole; an organic thing is one piece)."""
    kind = row_kinds.kind_of(row, kinds)
    said = set(row_kinds.words(row.get("name") or row.get("id")).split())
    if kind == "door":
        wide, deep, tall = (float(value) for value in row.get("size") or (1.0, 1.0, 1.0))
        if said & {"hatch", "hatches"} or tall < min(wide, deep):
            return "hatch"
        return "double door" if "double" in said else None
    if kind in VEHICLES and not said & set(TRACKED) and "drone" not in said:
        return "wheeled"
    return None


def joint_name(part, joint=None, axis=None, sign=1):
    """A part's node name: `<part>__<joint>_<axis>[n]`, or the part alone when it is still."""
    return part if joint is None else f"{part}__{joint}_{axis}{'n' if sign < 0 else ''}"


def frame_size(row):
    """(x, y, z) of the row's size in a final take's frame: y its height, z its longer ground side."""
    wide, deep, tall = (float(value) for value in row["size"])
    return np.array([min(wide, deep), tall, max(wide, deep)])


def slab(low, high):
    """A box mesh from `low` to `high`."""
    import trimesh
    low, high = np.asarray(low, dtype=float), np.asarray(high, dtype=float)
    return trimesh.creation.box(extents=high - low).apply_translation((low + high) / 2)


def part(name, mesh, finish, pivot=(0.0, 0.0, 0.0), joint=None, axis=None, sign=1):
    """One part: its mesh in the object's frame, laid in its own node at its pivot."""
    return {"name": joint_name(name, joint, axis, sign), "mesh": mesh, "pivot": np.asarray(pivot, dtype=float),
            "finish": finish, "joint": joint, "axis": axis, "sign": sign}


def door_parts(size):
    """A double door standing in the y-z plane: a still frame (two jambs and a head) and two leaves, each hinged
    about the upright at its outer edge, the left one turning the positive way and the right one the negative, so
    both open to the same side."""
    thick, tall, wide = size
    jamb, head = wide * JAMB_SHARE, tall * HEAD_SHARE
    leaf = thick * LEAF_SHARE / 2
    frame = [slab((-thick / 2, 0, -wide / 2), (thick / 2, tall, -wide / 2 + jamb)),
             slab((-thick / 2, 0, wide / 2 - jamb), (thick / 2, tall, wide / 2)),
             slab((-thick / 2, tall - head, -wide / 2 + jamb), (thick / 2, tall, wide / 2 - jamb))]
    inner = wide / 2 - jamb
    return [part("frame", frame, "painted_metal"),
            part("leaf_left", [slab((-leaf, 0, -inner), (leaf, tall - head, 0.0))], "painted_metal",
                 (0.0, 0.0, -inner), "hinge", "y", 1),
            part("leaf_right", [slab((-leaf, 0, 0.0), (leaf, tall - head, inner))], "painted_metal",
                 (0.0, 0.0, inner), "hinge", "y", -1)]


def hatch_parts(size):
    """A hatch lying level: a still rim round its opening and a lid filling it, hinged about the level line along
    its edge at -z (axis x), turning up and over away from its hinge."""
    across, thick, along = size
    rim = min(across, along) * RIM_SHARE
    top = thick / 2
    frame = [slab((-across / 2, -top, -along / 2), (across / 2, top, -along / 2 + rim)),
             slab((-across / 2, -top, along / 2 - rim), (across / 2, top, along / 2)),
             slab((-across / 2, -top, -along / 2 + rim), (-across / 2 + rim, top, along / 2 - rim)),
             slab((across / 2 - rim, -top, -along / 2 + rim), (across / 2, top, along / 2 - rim))]
    lid = thick * LEAF_SHARE / 2
    return [part("frame", frame, "chequer_plate"),
            part("lid", [slab((-across / 2 + rim, top - 2 * lid, -along / 2 + rim),
                              (across / 2 - rim, top, along / 2 - rim))], "chequer_plate",
                 (0.0, top, -along / 2 + rim), "hinge", "x", -1)]


def wheel(radius, width, middle):
    """A wheel round the x axis (its axle) at `middle`."""
    import trimesh
    mesh = trimesh.creation.cylinder(radius=radius, height=width, sections=WHEEL_FACES)
    mesh.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], [1, 0, 0]))
    return mesh.apply_translation(middle)


def vehicle_parts(size):
    """A wheeled vehicle along z: its body over four wheels, each spinning about its axle (x) at its own middle."""
    across, tall, along = size
    radius, width = tall * WHEEL_TALL / 2, across * WHEEL_WIDE
    axles = (-along / 2 + along * AXLE_IN, along / 2 - along * AXLE_IN)
    body = slab((-across / 2 + width, radius * 0.6, -along / 2), (across / 2 - width, tall, along / 2))
    wheels = [part(f"wheel_{number}", [wheel(radius, width, (side * (across - width) / 2, radius, axle))], "rubber",
                   (side * (across - width) / 2, radius, axle), "spin", "x", 1)
              for number, (side, axle) in enumerate(((side, axle) for axle in axles for side in (-1, 1)), 1)]
    return [part("body", [body], "painted_metal"), *wheels]


BUILDERS = {"double door": door_parts, "hatch": hatch_parts, "wheeled": vehicle_parts}


def scene_of(parts, centre):
    """A trimesh scene of the parts, each part a node at its pivot holding its meshes laid from it, all moved by
    `centre` so the object is centred on the origin over its floor."""
    import trimesh
    scene = trimesh.Scene()
    for entry in parts:
        pivot = entry["pivot"] + centre
        joined = trimesh.util.concatenate([mesh.copy().apply_translation(centre - pivot) for mesh in entry["mesh"]])
        scene.add_geometry(joined, node_name=entry["name"], geom_name=entry["name"],
                           transform=trimesh.transformations.translation_matrix(pivot))
    return scene


def build(row, kinds):
    """(the scene, its record) of a parted row, or ValueError for a row no parted rule takes."""
    rule = parted(row, kinds)
    if rule is None:
        raise ValueError(f"{row.get('id')}: no parted rule takes it (parted)")
    parts = BUILDERS[rule](frame_size(row))
    low = np.min([mesh.bounds[0] for entry in parts for mesh in entry["mesh"]], axis=0)
    high = np.max([mesh.bounds[1] for entry in parts for mesh in entry["mesh"]], axis=0)
    centre = -np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    record = {"row": row.get("id"), "rule": rule, "size": [round(float(value), 4) for value in frame_size(row)],
              "parts": [{"name": entry["name"], "finish": entry["finish"], "joint": entry["joint"],
                         "axis": entry["axis"], "sign": entry["sign"],
                         "pivot": [round(float(value), 5) for value in entry["pivot"] + centre]}
                        for entry in parts],
              "from": "score/stages/props/moving_parts: built in code with its parts apart, each pivot at its "
                      "node's origin (#19, 2026-11-05)"}
    return scene_of(parts, centre), record


def write(row, kinds, folder):
    """The row's parted model (`model.glb`) and record (`parts.json`) in `folder`; the record."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scene, record = build(row, kinds)
    scene.export(folder / "model.glb")
    (folder / "parts.json").write_text(json.dumps(record, indent=1))
    return record
