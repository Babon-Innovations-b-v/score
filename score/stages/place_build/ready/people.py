"""A laid person (a character's SkelRoot, held in its pose) read as the physics check reads any object: its drawn
skin posed as the renderer poses it (UsdSkel skinning, the clip's correctives applied first), each point's joint, and
the measures that say the body is whole.

    posed_body(prim) -> Body | None
    copies_posed(prim) -> {copy name: Body | None}
    shape_faults(body) -> [fault]

A crowd (a PointInstancer of laid people, crowd.py) is read copy by copy as the package names them (`<crowd>_<n>`,
skinned.copies_of): each copy its prototype's posed skin moved to where the copy stands, never the prototype itself
where it lies under the crowd (at the origin: the square's crowd read 39.8 cm inside its stage, 2099 #161).

A body is broken when a triangle's longest edge grows past route_stretch.MOST_METRES from its bind, or over TORN of
one garment's triangles more than double (bad skinning: a garment torn where a joint bends), when a head, a hand or a foot has no skin of its own (a missing part), or when
its bind height or its head's or legs' share of it lies outside a person's (HEIGHT, HEAD, LEGS).
"""
import pathlib
import sys

import numpy as np
import trimesh
from pxr import Usd, UsdGeom, UsdSkel, Vt

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/characters/maker"))
import route_stretch  # noqa: E402

STRETCH = route_stretch.MOST_METRES  # metres a triangle's longest edge may grow from its bind
HEIGHT = (0.9, 2.2)  # metres, a person's bind height (a child to a tall adult)
HEAD = (0.09, 0.2)  # the head's share of the bind height (a toddler's a fifth, an adult's an eighth)
LEGS = (0.4, 0.6)  # the hips' height over the feet as a share of the bind height
TEAR, TEAR_METRES = 2.0, 0.01  # a triangle torn: its longest edge more than doubles and grows over a centimetre
# The share of one drawn mesh's triangles that may tear (hidden tuck bands and closed webs stretch by design): the
# crew's astronaut suit tears 1.4% at most standing, the stairwell woman's tee 2.8% across her shoulders (2026-11-16).
TORN = 0.02
PARTS = {"head": ("head",), "hands": ("hand",), "feet": ("foot", "toe", "ankle")}
LEFT, RIGHT = ("left", "l_", "_l"), ("right", "r_", "_r")


class Body:
    """A person's posed skin in the scene's frame: one mesh, each point's joint (by path), the bind points and faces
    per drawn mesh, and the joints' bind places in the skeleton's frame."""

    def __init__(self, mesh, joint_of, drawn, bind_joints):
        self.mesh, self.joint_of, self.drawn, self.bind_joints = mesh, joint_of, drawn, bind_joints

    def points_of(self, *words, side=None):
        """The posed points whose joint's own name holds one of `words` (and, with `side`, a side word)."""
        names = np.array([path.split("/")[-1].lower() for path in self.joint_of])
        keep = np.array([any(word in name for word in words) for name in names], dtype=bool)
        if side is not None:
            keep &= np.array([any(name.startswith(mark) or name.endswith(mark) or mark in name for mark in side)
                              for name in names], dtype=bool)
        return np.asarray(self.mesh.vertices)[keep]

    def seat_joints(self):
        """The joints a seated person sits on: each foot's chain's hip and thigh (two and three above the foot)."""
        seat = set()
        for path in set(self.joint_of):
            parts = path.split("/")
            if "foot" in parts[-1].lower() and len(parts) >= 4:
                seat.update(("/".join(parts[:-2]), "/".join(parts[:-3])))
        return seat


def skeleton_root(prim):
    return next((UsdSkel.Root(inside) for inside in Usd.PrimRange(prim) if inside.IsA(UsdSkel.Root)), None)


def deformed(target, anim_query, time, points):
    """A mesh's points with the clip's blend shapes (its correctives) added, as the renderer adds them first."""
    if not anim_query or not target.HasBlendShapes() or target.GetBlendShapeMapper() is None:
        return points
    weights = anim_query.ComputeBlendShapeWeights(time)
    if not weights:
        return points
    weights = target.GetBlendShapeMapper().Remap(weights)
    query = UsdSkel.BlendShapeQuery(UsdSkel.BindingAPI(target.GetPrim()))
    sub_weights, shapes, subs = query.ComputeSubShapeWeights(weights)
    query.ComputeDeformedPoints(sub_weights, shapes, subs, query.ComputeBlendShapePointIndices(),
                                query.ComputeSubShapePointOffsets(), points)
    return points


def posed_body(prim, time=Usd.TimeCode.Default()):
    """The person's drawn skin posed (Body), or None when the prim holds no skinned mesh."""
    root = skeleton_root(prim)
    if root is None:
        return None
    cache = UsdSkel.Cache()
    cache.Populate(root, Usd.TraverseInstanceProxies())
    from score.stages.place_build.ready import fans  # ready imports this module
    pieces, joint_of, drawn, bind_joints = [], [], [], {}
    for binding in cache.ComputeSkelBindings(root, Usd.TraverseInstanceProxies()):
        skeleton = cache.GetSkelQuery(binding.GetSkeleton())
        transforms = skeleton.ComputeSkinningTransforms(time)
        world = np.asarray(UsdGeom.Xformable(binding.GetSkeleton().GetPrim()).ComputeLocalToWorldTransform(time))
        order = list(skeleton.GetJointOrder())
        bind_joints.update({path: np.asarray(matrix)[3, :3] for path, matrix in
                            zip(order, binding.GetSkeleton().GetBindTransformsAttr().Get())})
        for target in binding.GetSkinningTargets():
            mesh_prim = target.GetPrim()
            if UsdGeom.Imageable(mesh_prim).ComputeVisibility(time) == UsdGeom.Tokens.invisible \
                    or not mesh_prim.IsA(UsdGeom.Mesh):
                continue
            mesh = UsdGeom.Mesh(mesh_prim)
            rest = mesh.GetPointsAttr().Get(time)
            if not rest:
                continue
            points = deformed(target, skeleton.GetAnimQuery(), time, Vt.Vec3fArray(rest))
            target.ComputeSkinnedPoints(transforms, points, time)
            posed = np.asarray(points, dtype=np.float64) @ world[:3, :3] + world[3, :3]
            faces = fans(mesh.GetFaceVertexCountsAttr().Get(), mesh.GetFaceVertexIndicesAttr().Get())
            pieces.append(trimesh.Trimesh(posed, faces, process=False))
            joint_of += dominant_joints(target, order, len(rest))
            drawn.append((np.asarray(rest, dtype=np.float64), np.asarray(points, dtype=np.float64), faces))
    if not pieces:
        return None
    return Body(trimesh.util.concatenate(pieces), joint_of, drawn, bind_joints)


def copies_posed(prim):
    """A crowd's every copy posed (skinned.copies_of's names): its prototype's posed skin (posed_body, once a prototype)
    carried from the prototype's own frame to the copy's; None for a copy whose prototype holds no skinned mesh."""
    from score.stages.place_build import skinned  # skinned reads the package, which reads the check
    bodies, frames, copies = {}, {}, {}
    for root, name, world in skinned.copies_of(prim):
        path = str(root.GetPath())
        if path not in bodies:
            bodies[path] = posed_body(root)
            frames[path] = np.linalg.inv(np.asarray(
                UsdGeom.Xformable(root).ComputeLocalToWorldTransform(Usd.TimeCode.Default())))
        copies[name] = moved(bodies[path], frames[path] @ world)
    return copies


def moved(body, move):
    """`body` carried by the row-major transform `move` (its skin's points only; its joints and bind are its own)."""
    if body is None:
        return None
    points = np.asarray(body.mesh.vertices) @ move[:3, :3] + move[3, :3]
    return Body(trimesh.Trimesh(points, body.mesh.faces, process=False), body.joint_of, body.drawn, body.bind_joints)


def dominant_joints(target, order, count):
    """Each point's joint of most weight (its path), or the mesh's one joint for a rigid one."""
    indices, weights = target.ComputeJointInfluences()
    width = target.GetNumInfluencesPerComponent()
    mapped = target.GetJointOrder() or order
    indices, weights = np.asarray(indices).reshape(-1, width), np.asarray(weights).reshape(-1, width)
    picked = indices[np.arange(len(indices)), weights.argmax(axis=1)]
    names = [str(mapped[index]) for index in picked]
    return names if len(names) == count else [names[0]] * count


def torn_share(rest, posed, faces):
    """The share of a drawn mesh's triangles whose longest edge more than doubles (TEAR) and grows over TEAR_METRES
    from its bind: skin pulled apart where a joint bends, not stretched."""
    grown, bound = route_stretch.longest_edges(posed, faces), route_stretch.longest_edges(rest, faces)
    return float(np.mean((grown > TEAR * bound) & (grown - bound > TEAR_METRES)))


def shape_faults(body):
    """What says a body is broken: torn skin, a missing part, a height or share outside a person's."""
    faults = []
    worst = max(float((route_stretch.longest_edges(posed, faces) - route_stretch.longest_edges(rest, faces)).max())
                for rest, posed, faces in body.drawn if len(faces))
    torn = max(torn_share(*drawn) for drawn in body.drawn if len(drawn[2]))
    if worst > STRETCH or torn > TORN:
        faults.append({"fault": "broken body", "stretch": round(worst, 3), "torn": round(torn, 3),
                       "why": f"its skin tears where a joint bends: a triangle grows {worst * 100:.0f} cm from its "
                              f"bind (at most {STRETCH * 100:.0f}), {torn * 100:.1f}% of a garment's triangles more "
                              f"than double (at most {TORN * 100:.0f}%)"})
    missing = [part for part, words in PARTS.items() if not len(body.points_of(*words))]
    missing += [f"{side[0]} {part}" for part, words in (("hand", PARTS["hands"]), ("foot", PARTS["feet"]))
                for side in (LEFT, RIGHT) if part + "s" not in missing and not len(body.points_of(*words, side=side))]
    if missing:
        faults.append({"fault": "broken body", "missing": missing, "why": f"no skin on its {', '.join(missing)}"})
    rest = np.vstack([rest for rest, _, _ in body.drawn])
    height = float(np.ptp(rest[:, 1]))
    shares = {}
    head = [path for path in body.bind_joints if "head" in path.split("/")[-1].lower()]
    hips = [path for path in body.bind_joints if path.count("/") == 1 or "hips" in path.split("/")[-1].lower()]
    if head and height > 0:
        joint = min(head, key=len)
        shares["head"] = (rest[:, 1].max() - body.bind_joints[joint][1]) / height
    if hips and height > 0:
        shares["legs"] = (body.bind_joints[min(hips, key=len)][1] - rest[:, 1].min()) / height
    wrong = [f"{name} {share:.2f} of its height (a person's {low}-{high})"
             for name, share, (low, high) in [(name, value, HEAD if name == "head" else LEGS)
                                              for name, value in shares.items()] if not low <= share <= high]
    if not HEIGHT[0] <= height <= HEIGHT[1]:
        wrong.insert(0, f"{height:.2f} m tall at its bind (a person's {HEIGHT[0]}-{HEIGHT[1]})")
    if wrong:
        faults.append({"fault": "broken body", "proportions": wrong, "why": "; ".join(wrong)})
    return faults
