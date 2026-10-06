"""Runs inside Blender: the solid shapes code-built kit pieces are made of, in a kit piece's own frame.

A kit piece's frame (HubKit, tools/props/scene/hub_kit.py): as wide as x, as tall as y, as deep as z, standing on its
origin at the middle of its foot, its front toward -z. glTF, which the game reads, is y-up with -z forward; Blender is
z-up, so a kit point (x, y, z) is Blender (x, -z, y) and the exported file lands back in the kit's frame.

Every shape is its own object carrying one material slot named for its library material (library.py), so the bake
knows which recipe paints which faces. Edges stay true (bevelled a few millimetres), which is what the library's edge
wear reads.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


def to_blender(point):
    """A kit-frame point as Blender coordinates."""
    return Vector((point[0], -point[2], point[1]))


def slot(material_name):
    """The placeholder material for a library material: named for it, coloured only so a preview reads."""
    found = bpy.data.materials.get(material_name)
    if found is None:
        found = bpy.data.materials.new(material_name)
    return found


def mesh_object(name, mesh_data, material_name):
    item = bpy.data.objects.new(name, mesh_data)
    bpy.context.scene.collection.objects.link(item)
    item.data.materials.append(slot(material_name))
    return item


def box(low, high, material_name, name="box"):
    """An axis-aligned box between two kit-frame corners."""
    built = bmesh.new()
    bmesh.ops.create_cube(built, size=1.0)
    middle = (Vector(low) + Vector(high)) / 2
    size = Vector(high) - Vector(low)
    for vertex in built.verts:
        vertex.co = to_blender(Vector((middle.x + vertex.co.x * size.x, middle.y + vertex.co.y * size.y,
                                       middle.z + vertex.co.z * size.z)))
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return mesh_object(name, data, material_name)


def prism(outline, depth_from, depth_to, material_name, name="prism"):
    """A flat shape: a polygon in the kit frame's x-y plane, solid between two depths along z."""
    built = bmesh.new()
    front = [built.verts.new(to_blender((x, y, depth_from))) for x, y in outline]
    back = [built.verts.new(to_blender((x, y, depth_to))) for x, y in outline]
    built.faces.new(front)
    built.faces.new(list(reversed(back)))
    count = len(outline)
    for at in range(count):
        following = (at + 1) % count
        built.faces.new([front[at], back[at], back[following], front[following]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return mesh_object(name, data, material_name)


def cylinder(start, end, radius, material_name, segments=24, name="cylinder"):
    """A round bar from one kit-frame point to another."""
    start, end = to_blender(start), to_blender(end)
    built = bmesh.new()
    bmesh.ops.create_cone(built, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius,
                          depth=(end - start).length)
    turn = (end - start).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(built, matrix=Matrix.Translation((start + end) / 2) @ turn, verts=built.verts)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return mesh_object(name, data, material_name)


def ring(middle, axis_end, outer, inner, material_name, segments=48, name="ring"):
    """A flat round ring (a flange) from `middle` along to `axis_end`: a tube with walls."""
    solid = cylinder(middle, axis_end, outer, material_name, segments, name)
    hole_start = Vector(middle) - (Vector(axis_end) - Vector(middle)) * 0.5
    hole_end = Vector(axis_end) + (Vector(axis_end) - Vector(middle)) * 0.5
    cutter = cylinder(hole_start, hole_end, inner, material_name, segments, "cutter")
    cut(solid, cutter)
    return solid


def cut(target, cutter):
    """Take `cutter`'s solid out of `target` (an exact boolean), then remove the cutter."""
    change = target.modifiers.new("cut", "BOOLEAN")
    change.operation = "DIFFERENCE"
    change.solver = "EXACT"
    change.object = cutter
    apply_modifiers(target)
    bpy.data.objects.remove(cutter, do_unlink=True)


def apply_modifiers(item):
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    for change in list(item.modifiers):
        bpy.ops.object.modifier_apply(modifier=change.name)


def bevelled(item, width):
    """Round a part's sharp edges by `width` metres, so its edges catch light and wear like a made part's."""
    if width <= 0:
        return item
    change = item.modifiers.new("bevel", "BEVEL")
    change.width = width
    change.segments = 2
    change.limit_method = "ANGLE"
    change.angle_limit = math.radians(40)
    change.harden_normals = False
    apply_modifiers(item)
    return item


def joined(parts, name):
    """One object of all the parts, their material slots kept, shaded smooth only across gentle angles."""
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    whole = bpy.context.view_layer.objects.active
    whole.name = name
    whole.data.name = name
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return whole
