"""The sim body stage's ground: the solids the cast is measured on, a character's own frame and the triangles its body
may touch in it."""
import pathlib

import numpy as np

from score.stages import cast as cast_stage
from score.stages import layer_base
from score.stages.cast import measure

REACH = 1.0  # metres round a body's clip path (its segments, across the ground) whose solids it may touch
# A dressed body's Turned, degrees about up: the people build's root node (tools/characters/maker/prop_build.py build,
# "Person", rotation [0, 1, 0, 0]: the rig faces +z, a laid character -z). The skeleton plays the sim in that frame.
TURNED = 180.0


def solids_of(inputs, place):
    """{solid: its triangles in the place's frame} of the stage the cast is measured on: the seed's base layer with its
    scene record written in, on the place's made ground (the cast's own reading, cast/measure.solids); no water."""
    with layer_base.built(inputs) as folder:
        found = measure.solids(pathlib.Path(folder) / "layers/base.usda", place, cast_stage.made_ground(inputs, place))
    return {name: tris for name, tris in found.items() if not name.startswith(measure.WATER)}


def own_frame(at, turn):
    """The frame a character's sim body runs in, in the place's: its spot, then its turn about up (tools/characters/
    cast.py placed), then its dressed body's Turned (TURNED about up), the rig's frame its skeleton plays in."""
    from scipy.spatial.transform import Rotation
    frame = np.eye(4)
    frame[:3, :3], frame[:3, 3] = Rotation.from_euler("y", turn + TURNED, degrees=True).as_matrix(), at
    return frame


def ground_of(solids, worlds, frame):
    """The triangles a body may touch, in its own frame (n x 3 x 3), and the solids they are of: those whose span
    across the ground meets its clip's segments' span (`worlds`, its own frame) grown by REACH."""
    path = np.asarray(worlds)[:, :, [0, 2], 3].reshape(-1, 2)
    low, high = path.min(axis=0) - REACH, path.max(axis=0) + REACH
    back = np.linalg.inv(frame)
    found, names = [], []
    for name, tris in solids.items():
        mine = tris @ back[:3, :3].T + back[:3, 3]
        near = mine[((mine[:, :, [0, 2]].max(axis=1) >= low) & (mine[:, :, [0, 2]].min(axis=1) <= high)).all(axis=1)]
        if len(near):
            found.append(near)
            names.append(name)
    return (np.concatenate(found) if found else np.zeros((0, 3, 3))), names
