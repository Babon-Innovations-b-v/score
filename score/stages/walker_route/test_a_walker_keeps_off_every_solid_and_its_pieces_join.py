"""Invariant: a walker's route goes round a wall in its way and up a stair flight on the walkers' floor, never nearer
a solid than a body's radius; it is cut into pieces Kimodo can make (a climb its own piece, none longer than
PIECE_FRAMES, together every frame once); a later piece is asked to start in the pose the one before it stood in
(its fullbody keyframes, back in the scene's frame, are that pose), its join keeps that pose and the foot
standing across it on its spot, and a stance slipping over 2 cm is held on its spot; and the measures
tell a planted foot that slides 5 cm, a root off its route and a body brushing a wall; a walk whose knees never
straighten past 14 degrees, or whose hands hang still, is told slouched, an upright one with swinging arms is not, one walking under a stride is not judged. A walker given `seconds` walks on
round its spots (the last back to the first) until its clip lasts that long; two spots make no loop and are refused. A shut
door in the wall's gap is a solid (no route through it); marked `score:opens`, the walker goes through it, the door
stands open from OPEN_AHEAD before she crosses to SHUT_AFTER past it, and the swing written on its prim lays its leaf
where the walkers' floor took it open (shut at the start). The flight is planned foot by foot: one foothold on each
tread, the feet alternating, each sole whole on its tread back from its nosing, the route's height the treads' stood
on, a climb's foot keyframes setting each sole on its foothold, a short landing between two flights climbed
through; the footholds check passes feet planted on them and tells a sole on its nosing and the same foot on two
treads running. A made walk floating over its ground is stood back
on it (its standing foot's gap within GROUND_MOST), and the measures tell the floating one.

Breaks that turn this red (each applied once and seen red, then reverted):
- walker_route.route: ready.route swapped for the straight line through the spots -> the route crosses the wall
- walker_route.pieces: the flight's runs merged into the walk -> no `up` piece
- walker_route.pieces: `count` fixed at 1 -> a piece longer than PIECE_FRAMES
- walker_route.pieces: `< LANDING_FRAMES` made `< 0` -> the landing between two flights is a walk of its own
- walker_route.moved: the root's local turn left unturned -> the held pose's root turn is off by the piece's heading
- walker_route.axis_angle: `angle / (2 * sin)` made `angle / sin` -> the keyframe's turns are doubled
- walker_route.joined: the blend's weights reversed -> the join jumps
- walker_route.anchored: the slip left unsubtracted -> the foot sliding through the join's stance still slides
- walker_route.held_feet: `> SKATE_MOST` made `> 1.0` -> the sliding stance is left sliding
- walker_route.skates: the travel measured from the stance's last frame -> the sliding foot reads still
- walker_route.clearance: the band's KNEE taken off -> the floor under the walker reads a clash
- walker_route.filled: `>= seconds` made `>= 0` -> the filled walk ends at its last spot, short of its seconds
- ready.doors_standing: an opening door taken as shut -> no route through the marked door
- ready.walkers_floor: the doors given left out -> the shut door is routed through
- walker_route.crossings: the plane's side taken as the across distance -> no crossing, no swing
- walker_route.swung_in: the inverse hinge left out of the op order -> the open leaf stands off its hinge
- walker_route.round_again: `index % len(through)` made `min(index, len(through) - 1)` -> the walk stands at its last
  spot rather than going round (refused: the route no longer lengthens)
- walker_route.posture: the knee's flex taken as the angle itself (180 - angle dropped) -> the upright walk is
  told crouched
- walker_route.slouched: `max(measured["knee least"])` made `min(...)` of a walk with one bent leg -> passes
- walker_route.slouched: the swing check dropped -> the walk with its hands hanging passes
- walker_route.posture: the stride's least dropped (`walking.sum() < 2 * STEP_FRAMES` made `not walking.any()`) ->
  a 30-frame walk is judged
- walker_route.levels: `> RISER_LEAST` made `> 1.0` -> the flight reads one floor, no tread
- walker_route.placed_on: `+ SOLE / 2` dropped -> the planted heel hangs over its nosing, the check fails them
- walker_route.footholds: the side taken as "right" every step -> the feet do not alternate
- walker_route.stood_roots: the roots returned unchanged -> the route's height is not its treads'
- walker_route.hips_over: `- SOLE_MIDDLE * sin` made `+` -> the rest pose's sole lands off its foothold
- walker_route.sided: the piece before left unread (`if before is not None` made `if False`) -> the climb keys the
  plan's foot, not the one the piece before left free to step
- walker_route.foothold_faults: the sole's points left unread (`> ON_TREAD_MOST` made `> 1.0`) and the nosing
  test dropped -> the sole on its nosing passes
- walker_route.foothold_faults: the alternation left out -> the same foot on two treads running passes
- walker_route.grounded: the lift added with its sign turned -> the floating walk floats twice as high
- walker_route.measures: the standing gap left out of `within` -> the floating walk reads within
"""
import math

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, UsdGeom

from score.stages import place_build, walker_route
from score.stages.place_build import ready
from score.stages.walker_route.__main__ import ground_reader

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


def gait(knee_least, swing, frames=90, bent=None):
    """SOMA77 posed joints of a walk at 1 m/s along +Z: each knee flexing between `knee_least` (the right one's
    `bent`, when given) and 40 degrees each stride, each hand swinging `swing` m fore and aft about the hips."""
    joints = np.zeros((frames, 77, 3))
    time = np.arange(frames) / walker_route.RATE
    for side, ((hip, knee, ankle), hand) in enumerate(zip(walker_route.LEGS, walker_route.HANDS)):
        phase = 2 * math.pi * time + side * math.pi
        least = knee_least if bent is None or side == 0 else bent
        flex = np.radians(least + (40.0 - least) * (1 - np.cos(phase)) / 2)
        joints[:, hip] = [0.1 - 0.2 * side, 0.95, 0.0]
        joints[:, knee] = joints[:, hip] - [0.0, 0.45, 0.0]
        joints[:, ankle] = joints[:, knee] + 0.45 * np.column_stack([np.zeros(frames), -np.cos(flex), -np.sin(flex)])
        joints[:, hand] = [0.2 - 0.4 * side, 0.8, 0.0]
        joints[:, hand, 2] = swing / 2 * np.sin(phase)
    joints[:, :, 2] += time[:, None]
    return joints


def planted(holds, count, moved=None):
    """A motion standing SOMA77's rest feet on the footholds over 7 frames round each one's frame (`moved`: {frame:
    metres} the sole slid back along its heading there), the feet elsewhere 5 m under the floor and swinging fast."""
    joints = np.zeros((count, 77, 3)) + [0.0, -5.0, 0.0]
    joints[:, :, 0] += np.arange(count)[:, None]  # 30 m/s: no stance but the planted ones
    for hold in holds:
        ahead = np.array([math.sin(hold["heading"]), 0.0, math.cos(hold["heading"])])
        sole = walker_route.sole_at(hold, hold["side"]) - ahead * (moved or {}).get(hold["frame"], 0.0)
        rest = (walker_route.HEEL, 0.1154, walker_route.TOE)  # SOMA77's rest ankle, ball and toe end
        for joint, along, up in zip(walker_route.SOLE_JOINTS[hold["side"]], rest, walker_route.REST_HEIGHTS):
            joints[hold["frame"] - 3:hold["frame"] + 4, joint] = sole + ahead * (along - walker_route.SOLE_MIDDLE) + \
                [0.0, up, 0.0]
    return {"posed_joints": joints, "foot_contacts": np.zeros((count, 6), bool)}


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

    landing = np.column_stack([np.arange(330) * 0.02, np.interp(np.arange(330), [0, 60, 120, 200, 260, 329],
                                                                [0.0, 0.0, 1.0, 1.0, 2.0, 2.0]), np.zeros(330)])
    kinds = [piece["kind"] for piece in walker_route.pieces(landing)]
    runs = [kind for index, kind in enumerate(kinds) if not index or kind != kinds[index - 1]]
    assert runs == ["walk", "up", "walk"], walker_route.pieces(landing)  # the 2.7 s landing between two flights climbed through
    ground_at = ground_reader(found)
    holds, runs = walker_route.footholds(points, roots, ground_at)
    treads = [index for index, run in enumerate(runs) if run["kind"] == "tread"]
    on = [hold for hold in holds if hold["tread"] is not None]
    assert len(treads) == STEPS - 1 and [hold["tread"] for hold in on] == treads, (runs, holds)  # the last: the landing
    assert all(one["side"] != two["side"] for one, two in zip(holds, holds[1:])), holds
    risen = walker_route.stood_roots(roots, holds)
    assert all(abs(risen[hold["frame"], 1] - runs[hold["tread"]]["y"]) < 1e-6 for hold in on), risen[:, 1]
    for hold in on:
        sin, cos = math.sin(hold["heading"]), math.cos(hold["heading"])
        hips = walker_route.hips_over(hold, hold["side"])
        across = walker_route.FOOT_SIDE * (1 if hold["side"] == "left" else -1)
        rest = [hips[0] + across * cos + walker_route.SOLE_MIDDLE * sin, hips[1] - walker_route.HIP_OVER_SOLE,
                hips[2] - across * sin + walker_route.SOLE_MIDDLE * cos]
        assert np.allclose(rest, walker_route.sole_at(hold, hold["side"]), atol=1e-9), (rest, hold)
    faults, stances = walker_route.foothold_faults(planted(holds, len(roots)), runs, points, ground_at)
    assert not faults and [stance[2] for stance in stances] == treads, (faults, stances)
    nosed, _ = walker_route.foothold_faults(planted(holds, len(roots), {on[2]["frame"]: 0.03}), runs, points, ground_at)
    assert nosed and all("nosing" in fault or "not whole" in fault for fault in nosed), nosed
    same = [dict(hold, side=on[1]["side"]) if hold is on[2] else hold for hold in holds]
    twice, _ = walker_route.foothold_faults(planted(same, len(roots)), runs, points, ground_at)
    assert twice and all("two treads running" in fault for fault in twice), twice
    climb = next(piece for piece in walker_route.pieces(risen) if piece["kind"] == "up")
    flat = slice(0, walker_route.HOLD + 10)
    floating = synthetic(roots, headings)
    floating["posed_joints"] = floating["posed_joints"] + [0.0, 0.15, 0.0]
    stood = walker_route.grounded(floating, ground_at)
    standing = walker_route.standing_gap(stood, walker_route.foot_gaps(stood, ground_at))
    assert np.abs(standing[flat]).max() <= walker_route.GROUND_MOST, standing[flat]
    high = walker_route.standing_gap(floating, walker_route.foot_gaps(floating, ground_at))
    assert not walker_route.measures(floating, roots, triangles, high)["within"]

    feet = np.column_stack([roots[:, 1], roots[:, 1]])
    walk = synthetic(roots, headings)
    later = next(piece for piece in pieces if piece["start"] > 0)
    first = walker_route.asked(pieces[0], roots, headings, feet)
    assert np.allclose(first["constraints"][0]["smooth_root_2d"][0], 0.0, atol=1e-4)
    ask = walker_route.asked(later, roots, headings, feet, walk)
    other = dict(walk, foot_contacts=walk["foot_contacts"][:, [3, 4, 5, 0, 1, 2]])  # the right foot standing instead
    firsts = []
    for before in (walk, other):
        keyed = walker_route.sided(holds, climb["start"], climb["end"] - climb["start"] + walker_route.TAIL, before)
        frame, side = walker_route.next_stance(before["foot_contacts"][:climb["start"] + walker_route.OVERLAP],
                                               climb["start"] + walker_route.OVERLAP - 1)
        steps = round((keyed[0][0]["frame"] - frame) / walker_route.STEP_FRAMES)
        assert keyed[0][1] == (side if steps % 2 == 0 else {"left": "right", "right": "left"}[side]), (keyed[0], frame)
        assert all(one[1] != two[1] for one, two in zip(keyed, keyed[1:])), keyed
        firsts.append(keyed[0][1])
        climbed = walker_route.asked(climb, risen, headings, feet, before, holds)
        for hold, which in keyed:
            key = next(item for item in climbed["constraints"] if item["type"] == f"{which}-foot")
            assert hold["frame"] - climb["start"] in key["frame_indices"], (hold, key["frame_indices"])
    assert firsts[0] != firsts[1], firsts
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

    loop = [(-2.5, 0.0, -1.0), (-1.0, 0.0, -2.5), (-2.5, 0.0, -3.0)]  # three spots before the wall
    walked, points, _, roots, _ = walker_route.filled(folder, loop, seconds=12.0)
    assert walker_route.seconds_of(len(roots)) >= 12.0 and walked[3] == list(loop[0]) and len(walked) > 4, walked
    assert np.all(walker_route.clearance(roots, roots[:, 1], triangles) >= walker_route.BODY_RADIUS)
    assert walker_route.filled(folder, loop)[0] == [list(spot) for spot in loop]
    with pytest.raises(ValueError, match="no loop"):
        walker_route.filled(folder, loop[:2], seconds=12.0)

    stage, place = place_build.opened(folder)
    box(stage, place, "door", (0.05, 2.1, 1.38), (-0.025, 0.0, 1.61))  # in the wall's gap, z 1.6 .. 3.0
    door = stage.GetPrimAtPath(f"/{place}/Objects/door")
    door.GetAttribute("score:role").Set("door")
    stage.GetRootLayer().Save()
    through = [(-2.0, 0.0, -1.0), (2.0, 0.0, 2.3)]
    with pytest.raises(place_build.Refused):
        walker_route.route(folder, through)
    door.CreateAttribute(ready.OPENS, Sdf.ValueTypeNames.Bool).Set(True)
    stage.GetRootLayer().Save()
    roots, _ = walker_route.timed(np.asarray(walker_route.route(folder, through)[0]))
    laid = ready.Place(stage, place)
    middle, axes, half = ready.frame_of(laid, "door")
    swing = ready.swing_of(laid, "door")
    swings = walker_route.door_swings({"door": {"middle": middle, "axes": axes, "half": half, **swing}},
                                      {"walker": roots})
    crossed = swings["door"]["crossed"]["walker"]
    assert len(crossed) == 1 and abs(roots[crossed[0], 0]) < 0.1, swings
    window = swings["door"]["open"][0]
    assert np.allclose(window, [crossed[0] / walker_route.RATE - walker_route.OPEN_AHEAD,
                                crossed[0] / walker_route.RATE + walker_route.SHUT_AFTER], atol=1e-3), swings
    opened = ready.turned(laid.meshes["door"], swing["hinge"], swing["degrees"]).bounds
    walker_route.swung_in(place_build.scene_path(folder), place, swings)
    stage, _ = place_build.opened(folder)
    cache = UsdGeom.BBoxCache(0.0, ["default", "render"])
    for seconds, bounds in ((window[0] - walker_route.SWING_SECONDS - 0.1, laid.meshes["door"].bounds),
                            (sum(window) / 2, opened)):
        cache.SetTime(seconds * stage.GetTimeCodesPerSecond())
        box_now = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/{place}/Objects/door")).ComputeAlignedRange()
        assert np.allclose([box_now.GetMin(), box_now.GetMax()], bounds, atol=0.01), (seconds, box_now, bounds)
    upright = walker_route.posture(gait(2.0, 0.3))
    assert walker_route.slouched(upright) is None and max(upright["knee least"]) < 2.5, upright
    assert "knees" in walker_route.slouched(walker_route.posture(gait(14.0, 0.3)))
    assert "knees" in walker_route.slouched(walker_route.posture(gait(2.0, 0.3, bent=14.0)))
    assert "hand" in walker_route.slouched(walker_route.posture(gait(2.0, 0.05)))
    assert walker_route.posture(gait(14.0, 0.3, frames=30)) is None  # under a stride: no posture to judge
