"""The far crowd's one cheap body and its clips baked into textures (#112).

    MOTION_PERSON=kit_m_avg python crowd_vat.py <out dir> <clip> ...

Thousands of people in the square cannot each be a skinned body playing a clip: the engine would
skin every one of them on the processor every frame. So one low body (the body model's own
far level of detail, 1,220 triangles) has every frame of a few clips worked out here, once, the
way Godot would skin it, and written into a texture: a column for each point of the body and a
row for each frame. The crowd's shader reads its place from the texture by the point's number and
the frame its clip is at, so the card does the moving and the processor does nothing.

Written out:
- `vat_positions.bin`: float32 RGBA, rows = frames, columns = points: each point's place.
- `vat_normals.bin`: uint8 RGBA, the same layout: each point's normal as 0..255.
- `crowd_body.json`: the points at rest, the triangles, each point's colour zone and its height
  at rest, the texture's size, each clip's first row, frame count and rate, and the crowd's
  colours: a row a colour set (`PALETTES`) and how many of the crowd wear each.

The zones are what the few colours of the crowd are painted by: skin, hair, top, bottom, shoes.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import body  # noqa: E402
import clips  # noqa: E402
import numpy as np  # noqa: E402
import paint  # noqa: E402
import prologue  # noqa: E402
from paths import IDENTITY, MOTIONS  # noqa: E402

ZONES = {"skin": 0, "hair": 1, "top": 2, "bottom": 3, "shoes": 4}
HEAD_JOINTS = ("Neck1", "Neck2", "Head", "HeadEnd")
FEET = ("Foot", "ToeBase", "ToeEnd")
LEGS = ("Leg", "Shin")
# The hair: over the head above this far below the Head joint's height at the back, and above
# this far over it at the front (the forehead).
HAIR_BACK_BELOW = 0.02
HAIR_FRONT_ABOVE = 0.085
# Frames a second kept in the texture; the shader blends between rows.
RATE = 30.0
# The crowd's colour sets, one row each: skin, hair, top, bottom, shoes, and whether the top is a
# coat reaching below the knee. The kit's plain clothes (blue work jackets, grey coats, olive
# uniforms), the crew's navy work suit, and dark coats; the share of the crowd in each.
DARK_COAT = (66, 66, 70)
PALETTES = [
    (paint.SKIN, (28, 26, 26), prologue.PLAIN["jacket_blue"]["cloth"], prologue.PLAIN["jacket_blue"]["trousers"], prologue.SHOE, 0),
    (paint.SKIN, (28, 26, 26), prologue.PLAIN["coat_grey"]["cloth"], prologue.PLAIN["coat_grey"]["trousers"], prologue.SHOE, 1),
    (paint.SKIN, (28, 26, 26), paint.NAVY, paint.NAVY, paint.BOOT, 0),
    (paint.SKIN, (28, 26, 26), DARK_COAT, (44, 44, 48), prologue.SHOE, 1),
    (paint.SKIN, (28, 26, 26), prologue.PLAIN["uniform_olive"]["cloth"], prologue.PLAIN["uniform_olive"]["trousers"], (30, 28, 26), 0),
]
PALETTE_SHARES = [0.34, 0.26, 0.18, 0.16, 0.06]


def zones_of(points, weights, joint_names, joints):
    owner = np.array([joint_names[joint] for joint in weights.argmax(axis=1)])
    zone = np.full(len(points), ZONES["top"])
    head = np.isin(owner, HEAD_JOINTS)
    zone[head] = ZONES["skin"]
    head_joint = joints["Head"]
    behind = points[:, 2] < head_joint[2] + 0.02
    hair = head & (((points[:, 1] > head_joint[1] - HAIR_BACK_BELOW) & behind)
                   | (points[:, 1] > head_joint[1] + HAIR_FRONT_ABOVE))
    zone[hair] = ZONES["hair"]
    zone[np.char.endswith(owner.astype(str), "Hand")] = ZONES["skin"]
    legs = np.array([any(name.endswith(part) for part in LEGS) for name in owner])
    zone[legs] = ZONES["bottom"]
    feet = np.array([any(name.endswith(part) for part in FEET) for name in owner])
    zone[feet] = ZONES["shoes"]
    return zone


def world_of(local, parents):
    """Each frame's world transforms from its transforms against the parents."""
    world = np.empty_like(local)
    for joint in range(local.shape[1]):
        world[:, joint] = (local[:, joint] if parents[joint] < 0
                           else np.einsum("fab,fbc->fac", world[:, parents[joint]], local[:, joint]))
    return world


def smooth_normals(points, faces):
    corners = points[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)


def main():
    out, wanted = pathlib.Path(sys.argv[1]), sys.argv[2:]
    identity = str(IDENTITY)
    near = body.build_layer("low", identity)
    far = body.build_layer("xlo", identity)
    names = list(near.public_joint_names)
    parents_all = near.output_joint_parent_ids.detach().numpy().astype(int)
    kept, parents, carries = body.joints_worth_keeping(names, parents_all)
    joint_names = [names[old] for old in kept]
    bind_world, _ = body.bind_pose(near)
    bind_world = bind_world[kept]
    inverse_bind = np.linalg.inv(bind_world)
    _, points = body.bind_pose(far, body.floor_lift(near))
    faces = far.faces.detach().numpy().astype(np.int64)
    weights = body.as_the_engine_sees_them(body.kept_weights(far, carries, len(kept)))
    joints = {name: bind_world[index, :3, 3] for index, name in enumerate(joint_names)}
    zone = zones_of(points, weights, joint_names, joints)
    # The file is turned half a circle (the body model builds people facing +z, the game faces -z).
    turn = np.diag([-1.0, 1.0, -1.0])
    rows_positions, rows_normals, table = [], [], []
    for name in wanted:
        world, _ = body.posed_by_the_model(near, MOTIONS / f"{name}.npz")
        local, notes = body.prepare_clip(world[:, kept], np.array(parents), body.LEAST_FRAMES,
                                         name in clips.ONCE)
        moved_world = world_of(local, parents)
        start = len(rows_positions)
        for frame in moved_world:
            placed = body.engine_skinning(points, weights, frame, inverse_bind) @ turn.T
            rows_positions.append(placed)
            rows_normals.append(smooth_normals(placed, faces))
        table.append({"name": name, "start": start, "frames": len(moved_world), "rate": RATE})
        print(f"{name}: {len(moved_world)} frames, loop gap {notes['loopGapCut']}")
    positions = np.stack(rows_positions)
    normals = np.stack(rows_normals)
    out.mkdir(parents=True, exist_ok=True)
    packed = np.concatenate([positions, np.ones(positions.shape[:2] + (1,))], axis=2).astype(np.float32)
    packed.tofile(out / "vat_positions.bin")
    as_bytes = np.concatenate([(normals * 0.5 + 0.5) * 255, np.full(normals.shape[:2] + (1,), 255)], axis=2)
    np.round(as_bytes).astype(np.uint8).tofile(out / "vat_normals.bin")
    rest = points @ turn.T
    (out / "crowd_body.json").write_text(json.dumps({
        "points": np.round(rest, 5).ravel().tolist(), "faces": faces[:, ::-1].ravel().tolist(),
        "zones": zone.tolist(), "rest_height": np.round(points[:, 1], 4).tolist(),
        "knee": float(joints["LeftShin"][1]), "width": int(positions.shape[1]),
        "height": int(positions.shape[0]), "clips": table, "zone_names": list(ZONES),
        "palettes": [[list(colour) if isinstance(colour, tuple) else colour for colour in row] for row in PALETTES],
        "palette_shares": PALETTE_SHARES}))
    print(f"{len(points)} points, {len(faces)} triangles, texture {positions.shape[1]} x "
          f"{positions.shape[0]}, zones {np.bincount(zone).tolist()}")


if __name__ == "__main__":
    main()
