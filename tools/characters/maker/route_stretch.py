"""How far a built person's triangles stretch in its clips (score #10, the people route's stretch measure): per clip,
over every frame as the engine plays it (joins.py's skinning, each clip's own morph targets keyed), each drawn
triangle's longest edge against its longest edge at the bind. Tuck bands (a material's `tuck_from` on) are left
out: they are hidden under a garment. Plain numpy on the PC.

    ~/.farm-factory-props/env/bin/python route_stretch.py <body.glb> --out <stretch.json> [--node work]

Per clip: `most` (the worst triangle's growth in the worst frame), `p999` (the 99.9th percentile triangle in the
worst frame, so one sliver does not decide), and `over_1_5` (how many triangles grow past 1.5 times in the worst
frame), and `metres` (the most any triangle's longest edge grew, in metres, in any frame, and `where`: its surface's
material and its bind height): the stretch check, held to MOST_METRES. Only one clip's own morph targets are read at a time, so a settled body's thousands of targets fit in memory.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(MAKER), str(MAKER.parent / "people")]
import joins  # noqa: E402

LONG = 1.5
# The stretch check: no triangle's longest edge grows more than this in any frame of a clip. The pre-route astronaut
# grew 0.21 m between its legs walking and 0.29 m under its arm sitting (2026-10-27); the route's own grew 0.12 m, at
# the trouser cuff over its rigid boot sitting (the boot's shaft swings with the pointed foot).
MOST_METRES = 0.15
# A rest edge shorter than a millimetre (a sliver Pixal3D left) is read as a millimetre, so its growth is not noise.
FLOOR = 0.001


class Drawn:
    """One drawn surface of the node: its rest points, joints, weights, drawn triangles and primitive."""

    def __init__(self, document, blob, primitive):
        attributes = primitive["attributes"]
        extras = document["materials"][primitive["material"]].get("extras", {})
        self.primitive = primitive
        self.points = joins.accessor(document, blob, attributes["POSITION"])
        self.joints = joins.accessor(document, blob, attributes["JOINTS_0"]).astype(int)
        self.weights = joins.accessor(document, blob, attributes["WEIGHTS_0"])
        faces = joins.accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3)
        own = extras.get("tuck_from") or len(self.points)
        self.faces = faces[(faces < own).all(1)]


def surfaces_of(document, blob, node_name):
    """The node's drawn surfaces and the node's number."""
    node = next(number for number, node in enumerate(document["nodes"]) if node.get("name") == node_name)
    mesh = document["meshes"][document["nodes"][node]["mesh"]]
    return [Drawn(document, blob, primitive) for primitive in mesh["primitives"]], node


def clip_targets(document, node, clip):
    """The numbers of the node's morph targets a clip keys: those named `<clip>.<n>` (a settled body's), or every
    target when none is named after the clip (the route's corrective shapes, which every clip keys)."""
    mesh = document["meshes"][document["nodes"][node]["mesh"]]
    names = mesh.get("extras", {}).get("targetNames")
    everything = list(range(len(mesh.get("weights", []))))
    own = [number for number, name in enumerate(names or []) if name.split(".")[0] == clip]
    return own or everything


def longest_edges(points, faces):
    """Each triangle's longest edge."""
    corners = points[faces]
    return np.stack([np.linalg.norm(corners[:, first] - corners[:, second], axis=1)
                     for first, second in ((0, 1), (1, 2), (2, 0))], 1).max(1)


def grown(posed, rest, faces):
    """(the most a triangle's longest edge grew from its bind length `rest`, in metres; that triangle's number)."""
    growth = longest_edges(posed, faces) - rest
    return float(growth.max()), int(growth.argmax())


def frame_points(surface, offsets, joint_worlds, inverse_bind):
    """One surface posed in one frame, its morph offsets added first."""
    return joins.skinned(surface.points + offsets, surface.joints, surface.weights, joint_worlds, inverse_bind)


def clip_offsets(document, blob, surface, numbers, keyed):
    """A surface's offsets per frame from a clip's keyed targets (frames, points, 3), or None."""
    if keyed is None or not numbers or "targets" not in surface.primitive:
        return None
    targets = np.stack([joins.target_values(document, blob, surface.primitive["targets"][number]["POSITION"],
                                            len(surface.points)) for number in numbers])
    return np.tensordot(keyed[:, numbers], targets, axes=1)


def clip_growth(document, blob, surfaces, node, animation, rest, metres_rest):
    """The growth record of one clip: worst frame's most, 99.9th percentile and count over LONG; the most any
    triangle grew in metres in any frame and where (`metres_rest`: each surface's bind longest edges, unfloored)."""
    skin = document["skins"][0]
    inverse_bind = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = joins.parents_of(document)
    _, _, scales = joins.node_rest(document)
    rotations, translations = joins.clip_frames(document, blob, animation)
    keyed = joins.morph_weights(document, blob, animation, node)
    numbers = clip_targets(document, node, animation["name"])
    offsets = [clip_offsets(document, blob, surface, numbers, keyed) for surface in surfaces]
    worst = {"most": 1.0, "p999": 1.0, "over_1_5": 0, "frame": 0}
    metres = {"metres": 0.0, "where": None}
    for frame in range(len(rotations)):
        world = joins.world_matrices(rotations[frame], translations[frame], scales, parent)[skin["joints"]]
        posed = [frame_points(surface, 0 if moved is None else moved[min(frame, len(moved) - 1)], world, inverse_bind)
                 for surface, moved in zip(surfaces, offsets)]
        growth = np.concatenate([longest_edges(points, surface.faces) / bind
                                 for surface, points, bind in zip(surfaces, posed, rest)])
        for surface, points, bind in zip(surfaces, posed, metres_rest):
            most, triangle = grown(points, bind, surface.faces)
            if most > metres["metres"]:
                metres = {"metres": round(most, 3), "where": {
                    "material": document["materials"][surface.primitive["material"]].get("name"),
                    "height": round(float(surface.points[surface.faces[triangle], 1].mean()), 3), "frame": frame}}
        if growth.max() > worst["most"]:
            worst = {"most": round(float(growth.max()), 3), "p999": round(float(np.quantile(growth, 0.999)), 3),
                     "over_1_5": int((growth > LONG).sum()), "frame": frame}
    return {**worst, **metres}


def measure(path, node_name):
    """Every clip's growth record, and the triangles measured."""
    document, blob = joins.read_glb(path)
    surfaces, node = surfaces_of(document, blob, node_name)
    metres_rest = [longest_edges(surface.points, surface.faces) for surface in surfaces]
    rest = [np.maximum(bind, FLOOR) for bind in metres_rest]
    clips = {animation["name"]: clip_growth(document, blob, surfaces, node, animation, rest, metres_rest)
             for animation in document.get("animations", [])}
    return {"body": str(path), "triangles": int(sum(len(surface.faces) for surface in surfaces)), "clips": clips}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--node", default="work")
    options = parser.parse_args()
    record = measure(options.body, options.node)
    options.out.write_text(json.dumps(record, indent=1))
    worst = max(clip["most"] for clip in record["clips"].values())
    over = {name: clip["metres"] for name, clip in record["clips"].items() if clip["metres"] > MOST_METRES}
    print(f"route stretch: worst growth {worst} over {len(record['clips'])} clips, "
          f"{'over ' + str(MOST_METRES) + ' m: ' + str(over) if over else 'within ' + str(MOST_METRES) + ' m'}; "
          f"{options.out}")
    if over:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
