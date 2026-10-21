"""The reviewer's skin-and-hard-through-cloth count (issue #5's check/bodycloth.py, kept outside the repo and left as it
is) run on a body whose garments carry corrective shapes each clip keys (the people route's correctives, route_build.py): its reader takes the
surfaces' points only, so here every frame's points get their morph targets at the frame's weights first, as the
engine draws them. Its own command line, its own record.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/bodycloth_shaped.py <bodycloth.py> BODY.glb \
        --outfit work --out OUT.json
"""
import importlib.util
import pathlib
import sys

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER.parent / "people"))

import joins  # noqa: E402
import numpy as np  # noqa: E402


class Shapes:
    """The frame the reviewer's count is posing, and each surface's morph targets by its points' array."""

    def __init__(self):
        self.document = self.blob = self.keyed = None
        self.frame = -1
        self.targets = {}


def patched(shapes):
    """joins' reader with the morph targets laid in: clip_frames names the clip, world_matrices steps its frame, and
    skinned adds the targets to the points it is given."""
    clip_frames, world_matrices, skinned, read_glb = (joins.clip_frames, joins.world_matrices, joins.skinned,
                                                      joins.read_glb)

    def read(path):
        shapes.document, shapes.blob = read_glb(path)
        for node, item in enumerate(shapes.document["nodes"]):
            if "mesh" not in item:
                continue
            for primitive in shapes.document["meshes"][item["mesh"]]["primitives"]:
                points = joins.accessor(shapes.document, shapes.blob, primitive["attributes"]["POSITION"])
                found = joins.morph_targets(shapes.document, shapes.blob, primitive, len(points))
                if found is not None:
                    shapes.targets[points.tobytes()[:4096] + bytes(str(len(points)), "ascii")] = (found, node)
        return shapes.document, shapes.blob

    def frames(document, blob, animation):
        shapes.keyed = {node: joins.morph_weights(document, blob, animation, node)
                        for _, node in shapes.targets.values()}
        shapes.frame = -1
        return clip_frames(document, blob, animation)

    def worlds(rotations, translations, scales, parent):
        shapes.frame += 1
        return world_matrices(rotations, translations, scales, parent)

    def skin(points, joints, weights, joint_worlds, inverse_bind):
        found = shapes.targets.get(points.tobytes()[:4096] + bytes(str(len(points)), "ascii"))
        if found is not None and shapes.keyed and shapes.keyed.get(found[1]) is not None:
            keyed = shapes.keyed[found[1]]
            points = points + np.tensordot(keyed[min(shapes.frame, len(keyed) - 1)], found[0], axes=1)
        return skinned(points, joints, weights, joint_worlds, inverse_bind)

    joins.read_glb, joins.clip_frames, joins.world_matrices, joins.skinned = read, frames, worlds, skin


def main():
    script = pathlib.Path(sys.argv[1])
    sys.argv = [str(script)] + sys.argv[2:]
    spec = importlib.util.spec_from_file_location("bodycloth", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.joins = joins
    patched(Shapes())
    module.main()


if __name__ == "__main__":
    main()
