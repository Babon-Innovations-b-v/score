"""Runs inside Blender: the placing agent's preview (render.py), tools/blender/inside/usd_views.py with two changes a
laid place needs, made here so the films' and the physics' renders (which key usd_views.py) stay as they are:

- **A laid ground is the ground.** Every mesh of an object the agent laid with `put --ground` (score:ground on it or
  a parent) is joined into one `Ground`, which usd_views takes as the stage's own ground: no grey plane of its own
  under it (the camp pilot's plane fought the laid regolith), and the ground left out of the objects' mask.
- **See-through looks are thin glass.** A look with opacity under 1 (which Blender 5's reader brings in as the
  Principled BSDF's transmission, 1 - opacity, at IOR 1.5: solid refracting glass, whose skin bends what is behind
  it and darkens the shadow it casts like a block of glass; or as its alpha) is drawn as a thin glass skin: light passes it tinted by its colour as much as it is opaque, and it gives back a Fresnel share of what
  is around it at its roughness, so a dome's glass shows what stands inside and throws only a faint shadow, never a
  dark shell.

    blender -b --python blender_views.py -- <stage.usda> <views.json> <out folder>   (usd_views.py's arguments)
"""
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender/inside"))
import usd_views  # noqa: E402

GLASS_IOR = 1.5  # a thin glass look's reflection share at each angle (window glass)
SEE_THROUGH = ("Alpha", "Transmission Weight")  # the Principled inputs a look's opacity comes in on
GROUND = "Ground"  # the name usd_views.stage_ground takes as the stage's own ground


def laid_grounds(objects):
    """The meshes of every object laid as the place's ground (score:ground true on it or a parent)."""
    found = []
    for item in objects:
        holder = item
        while item.type == "MESH" and holder is not None:
            if usd_views.score_value(holder, "ground"):
                found.append(item)
                break
            holder = holder.parent
    return found


def joined_ground(objects):
    """The laid ground's meshes joined into one object named GROUND (kept where they stand); the objects without the
    ones joined away."""
    grounds = laid_grounds(objects)
    if not grounds:
        return objects
    first = grounds[0]
    if len(grounds) > 1:
        with bpy.context.temp_override(active_object=first, selected_editable_objects=grounds,
                                       selected_objects=grounds):
            bpy.ops.object.join()
    first.name = GROUND
    gone = set(grounds[1:])
    return [item for item in objects if item not in gone]


def thin_glass(objects):
    """Every see-through look drawn as thin glass (the module's rule); the looks it changed."""
    changed = []
    for material in {slot.material for item in objects if item.type == "MESH" for slot in item.material_slots
                     if slot.material and slot.material.use_nodes}:
        tree = material.node_tree
        shader = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is None or any(shader.inputs[name].is_linked for name in SEE_THROUGH):
            continue
        opacity = shader.inputs["Alpha"].default_value * (1.0 - shader.inputs["Transmission Weight"].default_value)
        if opacity >= 1.0:
            continue
        colour = shader.inputs["Base Color"].default_value
        output = next(node for node in tree.nodes if node.type == "OUTPUT_MATERIAL")
        passing = tree.nodes.new("ShaderNodeBsdfTransparent")
        passing.inputs["Color"].default_value = [1.0 - opacity * (1.0 - value) for value in colour[:3]] + [1.0]
        mirror = tree.nodes.new("ShaderNodeBsdfGlossy")
        mirror.inputs["Roughness"].default_value = shader.inputs["Roughness"].default_value
        share = tree.nodes.new("ShaderNodeFresnel")
        share.inputs["IOR"].default_value = GLASS_IOR
        mix = tree.nodes.new("ShaderNodeMixShader")
        tree.links.new(share.outputs["Fac"], mix.inputs["Fac"])
        tree.links.new(passing.outputs["BSDF"], mix.inputs[1])
        tree.links.new(mirror.outputs["BSDF"], mix.inputs[2])
        tree.links.new(mix.outputs["Shader"], output.inputs["Surface"])
        changed.append(material.name)
    print("blender_views: thin glass", sorted(changed))
    return changed


def with_laid_ground(importer):
    def imported(stage):
        return joined_ground(importer(stage))
    return imported


def with_thin_glass(haze):
    def drawn(objects):
        thin_glass(objects)
        return haze(objects)
    return drawn


usd_views.import_stage = with_laid_ground(usd_views.import_stage)
usd_views.haze_volumes = with_thin_glass(usd_views.haze_volumes)  # the looks' pass, never in a plain view
usd_views.main()
