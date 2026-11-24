"""A generated model's finish shades into its own creases (#206): bake.occlusion bakes the model's ambient occlusion
from its shape alone, so the floor of an L (a floor and a wall meeting at a crease) is darker where it meets the wall
than out in the open, while a slab laid just over the floor (as a piece's cut-down copy lies a voxel proud of its full
model) shades nothing, and the scene's samples and the slab are as they were after.

Breaks (each applied once, seen red, reverted, 2026-11-24):
- bake.occlusion not taking the other meshes out (`others = []`) -> the slab over the floor shuts its open end too.
- bake.occlusion baking at the reach given 0 (`light_settings.distance = reach` -> `= 0.0`) -> no crease is darker.
- bake.occlusion leaving its samples (`scene.cycles.samples, ... = held` dropped) -> the scene's samples are not 16.
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
print("FOUND", json.dumps({"crease": at(0.01, 0.5), "open": at(0.49, 0.5), "samples": scene.cycles.samples,
                           "slab_drawn": not copy.hide_render}))
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
    assert (found["crease"] < 0.8, found["open"] > 0.9, found["samples"], found["slab_drawn"]) == \
        (True, True, 16, True), found
