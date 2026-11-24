"""A generated model's finish shades into its own creases (#206): bake.occlusion bakes the model's ambient occlusion
from its shape alone, so the floor of an L (a floor and a wall meeting at a crease) is darker where it meets the wall
than out in the open, while a slab laid just over the floor (as a piece's cut-down copy lies a voxel proud of its full
model) shades nothing, and the scene's samples and the slab are as they were after. And a flat panel shades the seam
its decoded mesh holds (#159: bake.seamed, TRELLIS.2's mesh before the remesh closed its drawer seams): a 2 cm slit
3 mm deep across the decoded panel darkens the panel's texels over it and nowhere else; of a seam's run, a pinhole's
dot, a hole's blot and a hole's slot dark in a decoded occlusion, only the seam shades (bake.seam_shade).

Breaks (each applied once, seen red, reverted, 2026-11-24):
- bake.occlusion not taking the other meshes out (`others = []`) -> the slab over the floor shuts its open end too;
  taking out those `among` too (its `item not in among` dropped) -> the floor baked apart from its wall is open at
  the crease (#209: a place's part shaded by the model's other parts); bake.new_picture square whatever its sides ->
  the part's map is not 64 x 32 (its pixels read back short).
- bake.occlusion baking at the reach given 0 (`light_settings.distance = reach` -> `= 0.0`) -> no crease is darker.
- bake.occlusion leaving its samples (`scene.cycles.samples, ... = held` dropped) -> the scene's samples are not 16.
- bake.seamed not baking across from the decoded mesh (`source=decoded` dropped) -> the panel over the slit is not
  darker.
- bake.seam_shade keeping every dark texel (seam_lines dropped) -> the dot, the blot and the slot shade too;
  seam_lines not holding both sides lighter (`sides` dropped) -> the blot's rim shades as a seam; SEAM_ACROSS made 9
  -> the slot, 6 texels wide, shades.
"""
import json
import os
import pathlib
import subprocess

import pytest

from score.stages.place_build import render

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = '''
import json, sys
sys.path.insert(0, sys.argv[-2])
import runtime
runtime.ready()
import bpy
import scene_setup
import bake

scene = scene_setup.empty_scene(64, 16)
steps = 8
points, faces, uvs = [], [], []
def grid(corner, across, up, left):
    start = len(points)
    for row in range(steps + 1):
        for column in range(steps + 1):
            points.append([corner[axis] + across[axis] * column / steps + up[axis] * row / steps for axis in range(3)])
            uvs.append((left + 0.5 * column / steps, row / steps))
    for row in range(steps):
        for column in range(steps):
            first = start + row * (steps + 1) + column
            faces.append((first, first + 1, first + steps + 2, first + steps + 1))
grid((0, 0, 0), (1, 0, 0), (0, 1, 0), 0.0)  # the floor, up +z: u 0 at the crease, 0.5 out in the open
grid((0, 0, 0), (0, 0, 1), (0, 1, 0), 0.5)  # the wall, facing +x
mesh = bpy.data.meshes.new("l")
mesh.from_pydata(points, [], faces)
layer = mesh.uv_layers.new(name="texels")
for loop in mesh.loops:
    layer.data[loop.index].uv = uvs[loop.vertex_index]
model = bpy.data.objects.new("l", mesh)
scene.collection.objects.link(model)
slab = bpy.data.meshes.new("slab")
slab.from_pydata([(0.3, -0.5, 0.02), (1.5, -0.5, 0.02), (1.5, 1.5, 0.02), (0.3, 1.5, 0.02)], [], [(0, 1, 2, 3)])
copy = bpy.data.objects.new("slab", slab)
scene.collection.objects.link(copy)
picture = bake.occlusion([model], "texels", 64, 0.5)
shut = list(picture.pixels)
def at(u, v):
    column, row = int(u * 63), int(v * 63)
    return shut[(row * 64 + column) * 4]
def plate(points, faces, low, high, z):
    start = len(points)
    points.extend([(low[0], low[1], z), (high[0], low[1], z), (high[0], high[1], z), (low[0], high[1], z)])
    faces.append((start, start + 1, start + 2, start + 3))
panel_points, panel_faces, panel_uvs = [], [], []
for row in range(steps + 1):
    for column in range(steps + 1):
        panel_points.append((5.0 + column / steps, row / steps, 0.0))
        panel_uvs.append((column / steps, row / steps))
for row in range(steps):
    for column in range(steps):
        first = row * (steps + 1) + column
        panel_faces.append((first, first + 1, first + steps + 2, first + steps + 1))
mesh = bpy.data.meshes.new("panel")
mesh.from_pydata(panel_points, [], panel_faces)
layer = mesh.uv_layers.new(name="texels")
for loop in mesh.loops:
    layer.data[loop.index].uv = panel_uvs[loop.vertex_index]
panel = bpy.data.objects.new("panel", mesh)
scene.collection.objects.link(panel)
slit_points, slit_faces = [], []
plate(slit_points, slit_faces, (5.0, 0.0), (5.24, 1.0), 0.0)  # the panel either side of a 2 cm slit at u 0.25
plate(slit_points, slit_faces, (5.26, 0.0), (6.0, 1.0), 0.0)
plate(slit_points, slit_faces, (5.2, 0.0), (5.3, 1.0), -0.003)  # the slit's floor, 3 mm down
mesh = bpy.data.meshes.new("decoded")
mesh.from_pydata(slit_points, [], slit_faces)
decoded = bpy.data.objects.new("decoded", mesh)
scene.collection.objects.link(decoded)
seams = list(bake.seamed([panel], decoded, "texels", 64, 0.5).pixels)
def on_panel(u, v):  # the darkest of the texels round (u, v) along u: a slit 1.3 texels wide falls between centres
    return min(seams[(int(v * 63) * 64 + int(u * 63) + step) * 4] for step in (-2, -1, 0, 1, 2))
import numpy as np
def part(name, corner, across, up):  # one grid of the L alone, its own object (a place's part, #209)
    start = len(points)
    grid(corner, across, up, 0.0)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points[start:], [], [[corner - start for corner in face] for face in faces[len(faces) - steps * steps:]])
    layer = mesh.uv_layers.new(name="texels")
    for loop in mesh.loops:
        layer.data[loop.index].uv = (uvs[start + loop.vertex_index][0] * 2, uvs[start + loop.vertex_index][1])
    found = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(found)
    return found
floor = part("floor", (20, 0, 0), (1, 0, 0), (0, 1, 0))  # the L again apart: its floor and its wall two objects
wall = part("wall", (20, 0, 0), (0, 0, 1), (0, 1, 0))
apart = bake.occlusion([floor], "texels", [64, 32], 0.5, among=[wall])
alone = np.asarray(apart.pixels[:]).reshape(32, 64, 4)
dark = np.ones((64, 64), np.float32)
dark[8:40, 10] = 0.5  # a seam's run
dark[50, 50] = 0.5  # a pinhole's dot
dark[16:32, 36:52] = 0.5  # a hole's blot
dark[40:60, 20:26] = 0.5  # a hole's slot, 6 texels wide
shade = bake.seam_shade(dark)
print("FOUND", json.dumps({"crease": at(0.01, 0.5), "open": at(0.49, 0.5), "samples": scene.cycles.samples,
                           "slab_drawn": not copy.hide_render, "slit": on_panel(0.25, 0.5),
                           "panel": on_panel(0.75, 0.5), "seam": float(shade[24, 10]), "dot": float(shade[50, 50]),
                           "blot": float(shade[24, 36]), "slot": float(shade[50, 22]),
                           "part_crease": float(alone[16, 0, 0]), "part_open": float(alone[16, 62, 0]),
                           "part_size": list(apart.size)}))
'''


@pytest.mark.skipif(not render.BLENDER.exists(), reason="no Blender on this box (render.BLENDER)")
def test_a_model_shades_into_its_own_creases(tmp_path):
    script = tmp_path / "occluded.py"
    script.write_text(SCRIPT)
    env = {**os.environ, "PROPS_HOME": str(render.BLENDER.parents[2]),  # the Blender install's own pf-site
           "LD_LIBRARY_PATH": render.libraries()}  # the X libraries it links, as render.queued runs it
    done = subprocess.run([str(render.BLENDER), "-b", "--factory-startup", "--python-exit-code", "1", "-P",
                           str(script), "--", str(HERE), "x"],
                          capture_output=True, text=True, env=env, timeout=50)
    lines = [line for line in done.stdout.splitlines() if line.startswith("FOUND ")]
    assert done.returncode == 0 and lines, done.stdout[-2000:] + done.stderr[-2000:]
    found = json.loads(lines[0][len("FOUND "):])
    # the floor's crease shut by the wall, its open end under nothing (the slab out of the bake); the scene as it was
    # and the panel shaded over its decoded slit alone, by the seam's run alone of the three dark marks
    # and the floor baked alone on a 64 x 32 map, its wall another object among it, shut at the crease all the same
    assert (found["crease"] < 0.8, found["open"] > 0.9, found["samples"], found["slab_drawn"], found["slit"] < 0.85,
            found["panel"] > 0.97, found["seam"] < 0.9, found["dot"], found["blot"], found["slot"],
            found["part_crease"] < 0.8, found["part_open"] > 0.9, found["part_size"]) == \
        (True, True, 16, True, True, True, True, 1.0, 1.0, 1.0, True, True, [64, 32]), json.dumps(found)
