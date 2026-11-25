"""A generated model's finish shades into its own creases (#206): bake.occlusion bakes the model's ambient occlusion
from its shape alone, so the floor of an L (a floor and a wall meeting at a crease) is darker where it meets the wall
than out in the open, while a slab laid just over the floor (as a piece's cut-down copy lies a voxel proud of its full
model) shades nothing, and the scene's samples and the slab are as they were after. And a flat panel shades the seam
its decoded mesh holds (#159: bake.seamed, TRELLIS.2's mesh before the remesh closed its drawer seams): a 2 cm slit
3 mm deep across the decoded panel darkens the panel's texels over it and nowhere else; of a seam's run, a pinhole's
dot, a hole's blot and a hole's slot dark in a decoded occlusion, only the seam shades (bake.seam_shade). And a door
closed under a mark (#159 round 13, bake.pressed_under and cards_over) has its bump in the mark's region pressed onto its plate and
one card over the region in the finish of its plate, and a cut's blob pressed past its box over the next face eases into
it (bake.closed_points, #159 r15f).

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
- bake.closed_points `<= decal["closed"]["most"]` -> `<= 0.0` -> the bump is left standing; closing_card's
  `+ CARD_PROUD * normal` dropped -> the card lies in the plate; cards_over's `face.material_index` -> 0 -> the
  card in the steel, not the paint its plate point is in; plate_texel's middle -> its first loop's -> the card's
  texel on its face's rim; plate_texel's facing filter dropped -> the card in the steel
  of the sheet's back; its `closed` filter dropped (`list(decals)`) -> a decal with no region
  closed, KeyError; pressed_under's `if decal.get("closed")` dropped -> KeyError (#159 round 13).
- bake.closed_boxes' `*closed.get("also", [])` dropped -> the hole's rim left standing and no card over it (r13's
  dots); closed_points' `pressed` loop dropped -> the blob past the cut's box left standing (a lump beside the lock),
  its `least` -> 0 -> the face's own step pressed too (the neighbouring door's white crumpled strip); cards_over laying
  one card a decal (`closing_cards(decal)` -> its first) -> two cards, the hole's rim uncovered (#212, r14l).
- bake.closed_points' `surface_under(...)` -> `np.zeros(len(offset))` -> the strip's blob pressed straight onto the
  plate beside the next face, stretched 4.2; PRESS_ROUNDS 200 -> 1 -> stretched 2.6; its near points'
  `height >= -PRESS_SURFACE / 2` dropped -> laid toward the sheet's back, stretched 6.9; their
  `lowered <= PRESS_SURFACE` dropped -> the bumps beside the handle raised toward it (1.4 mm) (#159 r15f, seen red in
  numpy on the strip, 2026-11-25; the edge band, `eased = inside & (depth < PRESS_REACH)`, on r15f's locker: its
  upper right lock stretched 3.2 without it, 1.43 with).
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
door_points = [(column / 10 - 0.5, row / 10 - 0.5, 0.0) for row in range(11) for column in range(11)]
door_points[5 * 11 + 5] = (0.0, 0.0, 0.003)  # a 3 mm bump in the middle, inside the closed box
door_points[5 * 11 + 1] = (-0.4, 0.0, 0.003)  # one outside it
door_points[1 * 11 + 9] = (0.4, -0.4, 0.004)  # a hole's rim far off it, in its `also` box (#159 r13: the dots)
door_points[1 * 11 + 1] = (-0.4, -0.4, 0.02)  # a hardware blob 2 cm high in a cut's box (#212)
door_points[1 * 11 + 2] = (-0.3, -0.4, 0.02)  # past its box, in its `pressed`, a blob still
door_points[1 * 11 + 3] = (-0.2, -0.4, 0.004)  # in its `pressed` too, the face's own step under its `least`
door_faces = [(row * 11 + column, row * 11 + column + 1, (row + 1) * 11 + column + 1, (row + 1) * 11 + column)
              for row in range(10) for column in range(10)]
door_points += [(0.46, 0.06, -0.002), (0.46, 0.1, -0.002), (0.5, 0.1, -0.002), (0.5, 0.06, -0.002)]
door_faces.append((121, 122, 123, 124))  # the sheet's back 2 mm behind the plate point, facing in
mesh = bpy.data.meshes.new("door")
mesh.from_pydata(door_points, [], door_faces)
mesh.materials.append(bpy.data.materials.new("steel"))
mesh.materials.append(bpy.data.materials.new("paint"))
for face in mesh.polygons:
    face.material_index = 1 if face.center.x > 0.3 and face.center.z > -0.001 else 0
layer = mesh.uv_layers.new(name="texels")
for loop in mesh.loops:
    layer.data[loop.index].uv = (door_points[loop.vertex_index][0] + 0.5, door_points[loop.vertex_index][1] + 0.5)
door = bpy.data.objects.new("door", mesh)
scene.collection.objects.link(door)
door_decals = [{"at": [0.0, 0.0, 0.0], "normal": [0.0, 0.0, 1.0], "up": [0.0, 1.0, 0.0], "size_m": [0.2, 0.2],
                "closed": {"box": [-0.25, -0.25, 0.25, 0.25], "also": [[0.35, -0.45, 0.45, -0.35]], "most": 0.006,
                           "plate_point": [0.48, 0.08, 0.0]}},
               {"at": [0.0, 0.0, 0.0], "normal": [0.0, 0.0, 1.0], "up": [0.0, 1.0, 0.0], "size_m": [0.2, 0.2]},
               {"at": [-0.4, -0.4, 0.0], "normal": [0.0, 0.0, 1.0], "up": [0.0, 1.0, 0.0],
                "closed": {"box": [-0.05, -0.05, 0.05, 0.05], "pressed": [{"box": [-0.05, -0.05, 0.25, 0.05],
                                                                          "least": 0.006}],
                           "most": 0.05, "plate_point": [-0.35, -0.15, 0.0]}}]
bake.pressed_under(door, door_decals)
strip_across, strip_upward = np.meshgrid(np.arange(-0.09, 0.0705, 0.001), np.arange(-0.004, 0.0045, 0.001))
strip_points = np.c_[strip_across.ravel(), strip_upward.ravel(), (
    0.005 * np.clip((-0.048 - strip_across) / 0.004, 0.0, 1.0)  # the next face, 5 mm proud past a slope at the box
    + 0.02 * np.exp(-((strip_across + 0.04) ** 2) / (2 * 0.012 ** 2))  # the blob, its tail over that face
    + np.where((strip_across > 0.0455) & (strip_across < 0.05), 0.001, 0.0)  # 1 mm bumps at the box's other edge
    + np.where((strip_across > 0.0525) & (strip_across < 0.0605), 0.03, 0.0)).ravel()]  # a handle 3 cm proud past it
strip_back = strip_points[strip_points[:, 0] < -0.05] * [1, 1, 0] + [0, 0, -0.007]  # the next face's sheet's back
strip_side = strip_across.shape[1]
strip_corner = (np.arange(strip_across.shape[0] - 1)[:, None] * strip_side + np.arange(strip_side - 1)[None, :]).ravel()
strip_faces = np.r_[np.c_[strip_corner, strip_corner + 1, strip_corner + strip_side + 1],
                    np.c_[strip_corner, strip_corner + strip_side + 1, strip_corner + strip_side]]
strip_pressed = bake.closed_points(np.r_[strip_points, strip_back], {
    "at": [0.0, 0.0, 0.0], "normal": [0.0, 0.0, 1.0], "up": [0.0, 1.0, 0.0],
    "closed": {"box": [-0.05, -0.05, 0.05, 0.05], "pressed": [{"box": [-0.09, -0.05, 0.05, 0.05], "least": 0.006}],
               "most": 0.05, "plate_point": [0.0, 0.03, 0.0]}})[:len(strip_points)]
def strip_longest(found):
    return np.max([np.linalg.norm(found[strip_faces[:, first]] - found[strip_faces[:, second]], axis=1)
                   for first, second in ((0, 1), (1, 2), (2, 0))], axis=0)
cards = bake.cards_over(door, door_decals)
laid_cards = {}
for face in door.data.polygons[101:]:
    middle = [round(value, 2) for value in face.center[:2]]
    heights = [round(door.data.vertices[vertex].co.z, 6) for vertex in face.vertices]
    texel = door.data.uv_layers["texels"].data[face.loop_indices[0]].uv
    laid_cards[str(middle)] = [face.material_index, heights, [round(value, 3) for value in texel]]
print("FOUND", json.dumps({"cards": cards, "faces": len(door.data.polygons), "bump": door.data.vertices[60].co.z,
                           "outside": door.data.vertices[56].co.z, "laid_cards": laid_cards,
                           "rims": [round(door.data.vertices[index].co.z, 6) for index in (20, 12, 13, 14)],
                           "crease": at(0.01, 0.5), "open": at(0.49, 0.5), "samples": scene.cycles.samples,
                           "slab_drawn": not copy.hide_render, "slit": on_panel(0.25, 0.5),
                           "panel": on_panel(0.75, 0.5), "seam": float(shade[24, 10]), "dot": float(shade[50, 50]),
                           "blot": float(shade[24, 36]), "slot": float(shade[50, 22]),
                           "part_crease": float(alone[16, 0, 0]), "part_open": float(alone[16, 62, 0]),
                           "part_size": list(apart.size),
                           "strip_grown": float((strip_longest(strip_pressed) / strip_longest(strip_points)).max()),
                           "strip_most": float(strip_pressed[strip_points[:, 0] < 0.05, 2].max()),
                           "strip_inside": float(np.abs(strip_pressed[(np.abs(strip_points[:, 0]) < 0.05)
                                                                     & (strip_points[:, 0] > -0.04), 2]).max())}))
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
    # a door closed under its closed decals (#159 round 13): the bump in its box pressed flat, the one outside left,
    # a card in front of it in the finish of the face nearest its plate point, at that face's middle's texel; a hole's
    # rim far off it in its `also` pressed and carded the same (r13's dots); a hardware cut's blob pressed in its box
    # and past it in its `pressed` where it stands over its `least`, the face's own step there left, one card over
    # its box alone in its own plate's finish (#212, r14l)
    assert (found["cards"], found["faces"], found["bump"], found["outside"], found["rims"], found["laid_cards"]) == (
        3, 104, 0.0, pytest.approx(0.003), [0.0, 0.0, 0.0, pytest.approx(0.004)],
        {"[0.0, 0.0]": [1, [0.0003] * 4, [0.95, 0.55]], "[0.4, -0.4]": [1, [0.0003] * 4, [0.95, 0.55]],
         "[-0.4, -0.4]": [0, [0.0003] * 4, [0.15, 0.35]]}), json.dumps(found)
    assert (found["crease"] < 0.8, found["open"] > 0.9, found["samples"], found["slab_drawn"], found["slit"] < 0.85,
            found["panel"] > 0.97, found["seam"] < 0.9, found["dot"], found["blot"], found["slot"],
            found["part_crease"] < 0.8, found["part_open"] > 0.9, found["part_size"]) == \
        (True, True, 16, True, True, True, True, 1.0, 1.0, 1.0, True, True, [64, 32]), json.dumps(found)
    # a cut's blob pressed past its box over the next face 5 mm proud, the box's edge on that face's slope (r15f's
    # locker's right locks): laid on the surface round it, never that face's sheet's back nor a handle standing past
    # the box's other edge, no face stretched past look.stretched's 1.5 (pressed straight onto the plate, 4.2), the
    # blob gone, the box flat to its edge beside the handle
    assert (found["strip_grown"] < 1.5, found["strip_most"] <= 0.006, found["strip_inside"] < 1e-6) == (True,) * 3, \
        json.dumps(found)
