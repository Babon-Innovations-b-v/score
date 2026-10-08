"""Runs inside Blender: writes a scene in LEGO-Anything's artifact format (#128).

Their scorer takes a folder with scene.blend (renderable geometry and an active camera matching
the input view), scene.glb and final.png; a submission without geometry or an active camera is
invalid (their Validity, V). `write` refuses such a scene rather than writing it.

    import artifacts; artifacts.write("/some/folder")
"""
import pathlib

import bpy

MESH_TYPES = {"MESH", "CURVE", "SURFACE", "META", "FONT"}


def check_valid(scene):
    """Raise when the scene would score V = 0: no active camera, or nothing to draw."""
    if scene.camera is None:
        raise RuntimeError("the scene has no active camera")
    if not any(item.type in MESH_TYPES and item.visible_get() for item in scene.objects):
        raise RuntimeError("the scene has no visible geometry")


def save_blend(folder):
    path = folder / "scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, compress=False)
    return path


def export_glb(folder):
    path = folder / "scene.glb"
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_visible=True,
                              export_cameras=True, export_lights=True, export_apply=True)
    return path


def render_png(scene, folder):
    path = folder / "final.png"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def write(folder):
    """scene.blend, scene.glb and final.png of the current scene into `folder`."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    check_valid(scene)
    for path in (save_blend(folder), export_glb(folder), render_png(scene, folder)):
        print(f"{path.name} {path.stat().st_size}")
