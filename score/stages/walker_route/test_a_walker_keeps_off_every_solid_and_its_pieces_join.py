"""Invariant: a walker's route goes round a wall in its way and up a stair flight on the walkers' floor, never nearer
a solid than a body's radius; it is cut into pieces Kimodo can make (a climb its own piece, none longer than
PIECE_FRAMES, together every frame once); a later piece is asked to start in the pose the one before it stood in
(its fullbody keyframes, back in the scene's frame, are that pose), its join keeps that pose and the foot
standing across it on its spot, and a stance slipping over 2 cm is held on its spot; and the measures
tell a planted foot that slides 5 cm, a root off its route and a body brushing a wall.

Breaks that turn this red (each applied once and seen red, then reverted):
- walker_route.route: ready.route swapped for the straight line through the spots -> the route crosses the wall
- walker_route.pieces: the flight's runs merged into the walk -> no `up` piece
- walker_route.pieces: `count` fixed at 1 -> a piece longer than PIECE_FRAMES
- walker_route.moved: the root's local turn left unturned -> the held pose's root turn is off by the piece's heading
- walker_route.axis_angle: `angle / (2 * sin)` made `angle / sin` -> the keyframe's turns are doubled
- walker_route.joined: the blend's weights reversed -> the join jumps
- walker_route.anchored: the slip left unsubtracted -> the foot sliding through the join's stance still slides
- walker_route.held_feet: `> SKATE_MOST` made `> 1.0` -> the sliding stance is left sliding
- walker_route.skates: the travel measured from the stance's last frame -> the sliding foot reads still
- walker_route.clearance: the band's KNEE taken off -> the floor under the walker reads a clash
"""
import math

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, UsdGeom

from score.stages import place_build, walker_route
from score.stages.place_build import ready

RISER, TREAD, STEPS = 0.167, 0.28, 6


def box(stage, place, name, size, low):
    """An object of one cube `size` (x, y, z metres) whose lowest corner is `low`."""
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
    cube = UsdGeom.Cube.Define(stage, f"/{place}/Objects/{name}/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    holder.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    holder.GetPrim().CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set(
        "structure" if name.startswith(("wall", "step", "landing")) else "prop")


def room(folder):
    """A ground 7 m round, a wall across it at x = 0 with a 1.4 m gap at its far end, and past it a flight of STEPS
    steps up +x onto a landing."""
    Image.new("RGB", (8, 8)).save(folder / "concept.png")
    place_build.start(folder / "place", "room", folder / "concept.png")
    folder = folder / "place"
    place_build.ground(folder, "ground", 7.0, (0.0, -0.02, 0.0))
    stage, place = place_build.opened(folder)
    box(stage, place, "wall", (0.2, 2.5, 8.6), (-0.1, 0.0, -7.0))  # z -7.0 .. 1.6, the gap z 1.6 .. 3.0 open
    box(stage, place, "wall_end", (0.2, 2.5, 4.0), (-0.1, 0.0, 3.0))
    for step in range(STEPS):
        box(stage, place, f"step{step}", (TREAD, RISER * (step + 1), 1.4), (1.5 + step * TREAD, 0.0, -2.0))
    box(stage, place, "landing", (1.6, RISER * STEPS, 1.4), (1.5 + STEPS * TREAD, 0.0, -2.0))
    stage.GetRootLayer().Save()
    return folder


def synthetic(roots, headings, slide=0.0):
    """A Kimodo-shaped motion walking the route: the root on it at hip height, every joint 0.1 m beside it, its left
    toe end's contact runs of 10 frames, the stance at frames 20-29 sliding `slide` metres."""
    count = len(roots)
    motion = {"root_positions": roots + [0.0, 1.0, 0.0], "smooth_root_pos": roots.copy(),
              "global_root_heading": np.column_stack([np.cos(headings), np.sin(headings)]),
              "local_rot_mats": np.tile(np.eye(3), (count, 77, 1, 1)), "global_rot_mats": np.tile(np.eye(3), (count, 77, 1, 1)),
              "posed_joints": roots[:, None] + np.zeros((count, 77, 3)), "foot_contacts": np.zeros((count, 6), bool)}
    for start in range(0, count - 10, 20):
        motion["foot_contacts"][start:start + 10, 2] = True
        motion["posed_joints"][start:start + 10, 71] = motion["posed_joints"][start, 71]
    motion["posed_joints"][20:30, 71, 0] += np.linspace(0.0, slide, 10)
    for index, angle in enumerate(headings):  # the root's turn its heading's
        motion["local_rot_mats"][index, 0] = motion["global_rot_mats"][index, 0] = walker_route.turn_y(angle)
    return motion


def test_a_walker_keeps_off_every_solid_and_its_pieces_join(tmp_path):
    folder = room(tmp_path)
    found = ready.solids(folder)
    triangles = np.concatenate(list(found.values()))
    points, metres = walker_route.route(folder, [(-2.0, 0.0, -1.0), (1.0, 0.0, -1.3), (3.9, STEPS * RISER, -1.3)])
    points = np.asarray(points)
    roots, headings = walker_route.timed(points, tread=TREAD)
    assert np.all(walker_route.clearance(roots, roots[:, 1], triangles) >= walker_route.BODY_RADIUS), metres
    crossing = np.flatnonzero(np.diff(np.sign(roots[:, 0])) != 0)[0]
    assert roots[crossing, 2] > 1.6, roots[crossing]  # through the gap, never the wall
    assert abs(roots[-1, 1] - STEPS * RISER) < 0.05 and roots[0, 1] < 0.05, (roots[0], roots[-1])

    pieces = walker_route.pieces(roots)
    assert [piece["start"] for piece in pieces][1:] == [piece["end"] for piece in pieces][:-1], pieces
    assert pieces[0]["start"] == 0 and pieces[-1]["end"] == len(roots), pieces
    assert "up" in {piece["kind"] for piece in pieces} and \
        all(piece["end"] - piece["start"] <= walker_route.PIECE_FRAMES for piece in pieces), pieces

    feet = np.column_stack([roots[:, 1], roots[:, 1]])
    walk = synthetic(roots, headings)
    later = next(piece for piece in pieces if piece["start"] > 0)
    first = walker_route.asked(pieces[0], roots, headings, feet)
    assert np.allclose(first["constraints"][0]["smooth_root_2d"][0], 0.0, atol=1e-4)
    ask = walker_route.asked(later, roots, headings, feet, walk)
    held = next(item for item in ask["constraints"] if item["type"] == "fullbody")
    turns = np.asarray(held["local_joints_rot"])[:, 0]
    back = walker_route.moved({key: np.asarray(walk[key])[later["start"]:later["start"] + walker_route.OVERLAP]
                               for key in walker_route.KEYS}, np.asarray(ask["origin"]), ask["heading"], inverse=True)
    assert np.allclose(np.asarray(held["root_positions"]), back["root_positions"], atol=1e-4)
    assert np.allclose(np.linalg.norm(turns, axis=1), [abs((math.atan2(*row[::-1]) + math.pi) % (2 * math.pi) - math.pi)
                                                       for row in back["global_root_heading"]], atol=1e-3)
    made = walker_route.moved(back, np.asarray(ask["origin"]), ask["heading"])
    tail = {key: np.concatenate([np.asarray(made[key]), np.asarray(walk[key])[later["start"] + walker_route.OVERLAP:]])
            for key in walker_route.KEYS}
    whole = walker_route.joined(walk, tail, later["start"])
    assert np.allclose(whole["posed_joints"], walk["posed_joints"], atol=1e-4)
    shifted = dict(tail, root_positions=tail["root_positions"] + [0.05, 0.0, 0.0])  # a piece standing 5 cm aside
    eased = walker_route.joined(walk, shifted, later["start"])["root_positions"][:, 0] - walk["root_positions"][:, 0]
    assert np.abs(np.diff(eased)).max() <= 0.05 / (walker_route.OVERLAP + 1) + 1e-6 and abs(eased[-1] - 0.05) < 1e-9

    still, slid = walker_route.measures(walk, roots, triangles), walker_route.measures(synthetic(roots, headings, 0.05),
                                                                                       roots, triangles)
    assert still["within"] and still["skate max"] < 1e-6 and not slid["within"] and slid["skate over"] == 1, (still,
                                                                                                         slid)
    assert max(walker_route.skates(walker_route.anchored(synthetic(roots, headings, 0.05), 20))) < 1e-6
    assert max(walker_route.skates(walker_route.held_feet(synthetic(roots, headings, 0.05)))) < 1e-6
    off = synthetic(roots + [0.0, 0.0, 0.2], headings)
    assert walker_route.measures(off, roots, triangles)["route off max"] > walker_route.ROUTE_MOST
    brushing = np.array([[-0.25, 0.0, -1.0]])
    assert walker_route.clearance(brushing, [0.0], triangles)[0] < walker_route.BODY_RADIUS
