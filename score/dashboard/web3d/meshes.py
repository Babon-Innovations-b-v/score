"""A place's drawn meshes into the web copy's two glTF documents: the place's own (`own`) and the other places its scene
shows that have no web copy of their own (`around`: the far city, a seed place no stage makes), each mesh written by
the films' exporter (tools/review/viewer/export.py's add_mesh, never edited). A shown place that has its own copy
(`elsewhere`) is not written again: the viewer loads that copy and stands it on its seat (facts.shown_places), so
the city's five places are each sent once and never simplified. A point instancer (the far city's towers) has its
prototypes written once and its instances listed, so the viewer draws them as instanced meshes; every other shape
the exporter cannot write is counted in `left_out`.

A shown place's Outside ring (its far ground, horizon and water, the same city laid round its own seat) is left out
where the place has its own of the same name: the film draws both, one over the other a few hundred metres apart.
"""
import numpy as np

from score.dashboard.web3d import facts

OUTSIDE = "Outside"


def document_of(prim):
    """Which document a prim's meshes go in: "around" for another place the scene shows, else "own"."""
    return "around" if facts.shown_place(prim) else "own"


def own_outside(stage):
    """The names of the place's own Outside parts (near, far, horizon, water), or an empty set."""
    outside = stage.GetDefaultPrim().GetChild(OUTSIDE)
    return {child.GetName() for child in outside.GetChildren()} if outside.IsValid() else set()


def doubled_outside(prim, kept):
    """Whether a prim is a shown place's Outside part that the place's own Outside already has (other than its near
    ground, which is cut round that place alone)."""
    parts = prim.GetPath().pathString.split("/")
    return (facts.shown_place(prim) is not None and len(parts) > 5 and parts[4] == OUTSIDE
            and parts[5] in kept and parts[5] != "near")


def left_to_its_copy(prim, elsewhere):
    """Whether a prim is a shown place's root whose own web copy the viewer loads instead."""
    parts = prim.GetPath().pathString.split("/")
    return len(parts) == 4 and facts.shown_place(prim) in elsewhere


def instance_matrices(instancer, root, time):
    """Each instance's move of a prototype written where it stands under the instancer (its root's own place in the
    world), as 16 numbers row by row (USD's row-vector form, which three.js reads column by column as the same
    move)."""
    from pxr import UsdGeom
    turns = instancer.ComputeInstanceTransformsAtTime(time, time)
    world = np.array(UsdGeom.Xformable(instancer.GetPrim()).ComputeLocalToWorldTransform(time))
    written = np.linalg.inv(np.array(UsdGeom.Xformable(root).ComputeLocalToWorldTransform(time)))
    indices = np.asarray(instancer.GetProtoIndicesAttr().Get(time), dtype=np.int64)
    targets = instancer.GetPrototypesRel().GetTargets()
    chosen = [number for number, index in enumerate(indices) if targets[index] == root.GetPath()]
    return [np.round(written @ np.array(turns[number]) @ world, 4).ravel().tolist() for number in chosen]


def add_instancer(export, documents, prim, skinned, time, boxes):
    """A point instancer's prototypes written once into its document and its instances listed: (triangles,
    {name, prototypes: [{objects, matrices}]})."""
    from pxr import Usd, UsdGeom
    instancer = UsdGeom.PointInstancer(prim)
    stage = prim.GetStage()
    triangles, prototypes = 0, []
    for target in instancer.GetPrototypesRel().GetTargets():
        root = stage.GetPrimAtPath(target)
        objects = []
        for mesh in Usd.PrimRange(root):
            if export.drawn(mesh, time):
                triangles += export.add_mesh(documents[document_of(prim)], mesh, skinned, time, boxes)
                objects.append(export.object_name(mesh))
        prototypes.append({"objects": sorted(set(objects)), "matrices": instance_matrices(instancer, root, time)})
    return triangles, {"name": export.object_name(prim), "prototypes": prototypes}


def write_meshes(export, stage, documents, time, elsewhere=()):
    """Every drawn mesh of the stage into its document, but those of the shown places in `elsewhere`: the objects'
    boxes, the triangle count, what was left out (other shapes, counted by kind) and the instancers."""
    from pxr import Usd, UsdGeom
    skinned = export.skins(stage)
    kept = own_outside(stage)
    boxes, triangles, left_out, instancers = {}, 0, {}, []
    prims = iter(Usd.PrimRange(stage.GetDefaultPrim()))
    for prim in prims:
        if doubled_outside(prim, kept) or left_to_its_copy(prim, elsewhere):
            prims.PruneChildren()
        elif prim.IsA(UsdGeom.PointInstancer):
            made, entry = add_instancer(export, documents, prim, skinned, time, boxes)
            triangles += made
            instancers.append(entry)
            prims.PruneChildren()
        elif prim.IsA(UsdGeom.Points):
            prims.PruneChildren()  # an effect's points: facts.effects
        elif prim.IsA(UsdGeom.Gprim) and not (prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Sphere)):
            if UsdGeom.Imageable(prim).ComputeVisibility(time) != UsdGeom.Tokens.invisible:
                left_out[str(prim.GetTypeName())] = left_out.get(str(prim.GetTypeName()), 0) + 1
            prims.PruneChildren()
        elif export.drawn(prim, time):
            triangles += export.add_mesh(documents[document_of(prim)], prim, skinned, time, boxes)
    return boxes, triangles, left_out, instancers
