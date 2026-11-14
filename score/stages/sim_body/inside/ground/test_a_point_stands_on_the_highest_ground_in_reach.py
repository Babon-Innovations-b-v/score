"""ground: a point stands on the highest drawn triangle under it at most REACH_UP (the cast's KNEE) over it, a body's
points over its lowest point, with HEADROOM free over it or within a knee of the body's lowest point, never one over
it with another between, at the height worked out by hand; a point within GAP of a back (a steep triangle) leans on
it along its normal towards the body's middle; and every triangle's normal points up (pure numpy: the score venv
runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28, 2026-10-30, 2026-10-31, 2026-11-07 and 2026-11-13:
- standing's `free = (above - heights >= HEADROOM) & ...` made `>= 0`: a point 1.1 m over a floor, over a counter
  top at 1.0 m with a cupboard 0.5 m over it, stands on the counter top, under the cupboard.
- standing's `top = which != np.append(which[1:], -1)` made the first of each point (the lowest, as before
  2026-10-30): a point on a deck 2.958 m over a floor stands on the floor, the deck read as its roof (greenhouse's
  astronauts on Structure/deck_2).
- standing's `& (heights <= points[which, 1] + REACH_UP)` dropped: a point on the floor under the deck stands on the
  deck.
- standing's `reach = points[:, 1] + REACH_UP if reach is None else ...` made to ignore `reach` (each point its own
  reach, as 75903a1a left it, 2026-10-31): a 1.76 m body under a roof at 1.84 m reads 0.24 m into its ground, its
  head grounded on the roof (tube's person_mid_left_2, greenhouse's astronauts 1, 4 and 5).
- body_reach's `max(..., float(np.median(points[:, 1])))` dropped (its lowest point plus REACH_UP alone, as before
  2026-11-07): a body seated on a 0.40 m seat, its feet on the floor, has no ground under its seat (nan), the seat
  past its reach and the floor under it covered (#98's sit-to-stand chair).
- standing's `| (heights <= floor[which])` dropped (2026-11-13): a body standing on a deck with a foot under a desk
  (its underside 0.72 m, its top 0.75 m) has no floor under that foot, the deck read as a block; with `&
  ~beneath(...)` dropped too, the foot reads 0.75 m into the desk's top (greenhouse's astronaut_1 and astronaut_4).
- `beneath`'s return made `over & False`: the foot under the desk stands on its top, 0.75 m into it; made `over`: a
  foot 3 mm into its floor reads 0.2 m over the floor's underside, never sunk; its `+ SAME` dropped: a point 3 mm into a bent
  floor, on the edge its two triangles share (their heights 4e-17 apart), has no ground (nan).
- standing's `& ~outside(...)` dropped (2026-11-14): the toe on the floor under the closed drawer block reads 0.158 m
  into its underside (quarters' person_desk's toes under its desk's apron); outside's `% 2 == 0` made `>= 0` (every
  piece over a point read as one it is under): the shin in the block reads 0.04 m over the block's underside, never
  sunk; its `~same` dropped: the foot 3 mm into the floor, on the edge its square's two triangles share, reads 0.197 m
  over the floor's underside.
- body_floor's `+ REACH_UP` made `+ HEADROOM`: the desk's underside, 0.72 m up, counts as the foot's floor (-0.72).
- standing's `room = np.minimum(HEADROOM, tops[which] - heights)` made `HEADROOM` (2026-11-13): a body seated on a
  lower bunk's mattress, 0.6 m free under the upper bunk, its own top 0.55 m over the mattress, has no ground under its
  thighs (nan; quarters' person_bed's centre of mass, a NaN in RRA's Cholesky); made `tops[which] - heights` (no
  HEADROOM): a point with no body over it (no top) finds no room under anything, the floor under the counter top and
  under the deck read nan.
- REACH_UP made 0.4: it no longer agrees with the cast's KNEE.
- (2026-11-14) _near_steep's `up[:, 1] < STEEP` made `< 1.1`: the point 1 mm over the floor leans on it as on a
  back; leaning's side `< 0.0` made `< -9.0` (every back pushing out of its upward side): the point with the body's
  middle behind the back reads 3 mm in front of it, not in it; its `(one + two <= 1)` dropped: the point beside the
  triangular back, inside its box, leans on it; its `np.abs(distance) <= within` made `<= 1.0`: the point 6 mm in
  front leans on it; its foot made the point itself: the push acts off the back's face; its `raised`
  `points[:, 1] > floor` made `> -inf`: the point as low as its body's floor (a toe at a riser) leans on the back;
  _near_steep's `steep[counts > BIG_CELLS]` loop dropped: the points by the long slanted wall lean on nothing; its
  cells' `held` made `<= within`: the points near the wall in cells whose middles stand further off it lean on nothing.
- normals' `found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)` dropped: a triangle wound the other way points
  down.

Run: .venv/bin/python score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[5]
sys.path[:0] = [str(INSIDE), str(REPO)]
import ground  # noqa: E402


def square(height, low=-5.0, high=5.0):
    """A flat square at `height` (Y up) as two triangles."""
    return [[[low, height, low], [high, height, high], [high, height, low]],
            [[low, height, low], [low, height, high], [high, height, high]]]


def a_point_over_a_slope_stands_at_its_height():
    """The slope through (0, 0, 0), (2, 1, 0) and (0, 0, 2) is y = x / 2: a point at x 1, z 0.5, 5 m up, stands on
    it at 0.5 m, 4.5 m over it; a point off every triangle has no ground (nan, -1)."""
    slope = np.array([[[0.0, 0.0, 0.0], [2.0, 1.0, 0.0], [0.0, 0.0, 2.0]]])
    points = np.array([[1.0, 5.0, 0.5], [100.0, 0.0, 100.0]])
    heights, triangles = ground.standing(points, slope)
    problems = [] if abs(heights[0] - 0.5) < 1e-12 and triangles[0] == 0 else [
        f"over the slope: {heights[0]} on triangle {triangles[0]}, not 0.5 on 0"]
    problems += [] if np.isnan(heights[1]) and triangles[1] == -1 else [f"off the ground: {heights[1]}, {triangles[1]}"]
    over = ground.heights_over(points[:1], slope)[0]
    return problems + ([] if abs(over - 4.5) < 1e-12 else [f"height over the slope {over}, not 4.5"])


def a_low_top_is_a_block_not_a_floor():
    """A floor at 0, a counter top at 1.0 m and a cupboard's bottom at 1.5 m over it: the top has 0.5 m free, under
    HEADROOM (1 m), so a point 1.1 m up, the top within its reach, stands on the floor (1.0 m free); a point 3 m up
    stands on the cupboard."""
    under = np.array(square(0.0) + square(1.0, -1.0, 1.0) + square(1.5, -1.0, 1.0))
    on_floor = ground.standing(np.array([[0.5, 1.1, 0.5]]), under)[0][0]
    on_cupboard = ground.standing(np.array([[0.5, 3.0, 0.5]]), under)[0][0]
    return ([] if on_floor == 0.0 else [f"over the counter top under the cupboard: stands at {on_floor}, not 0"]) + (
        [] if on_cupboard == 1.5 else [f"over the cupboard: stands at {on_cupboard}, not 1.5"])


def a_point_on_a_deck_stands_on_the_deck():
    """A floor at 0 and a deck at 2.958 m (greenhouse's Structure/deck_2): a point on the deck stands on it, not on
    the floor 2.958 m under it; a point on the floor under the deck, the deck out of its reach, stands on the floor."""
    decked = np.array(square(0.0) + square(2.958, -1.0, 1.0))
    on_deck = ground.standing(np.array([[0.5, 2.958, 0.5]]), decked)[0][0]
    on_floor = ground.standing(np.array([[0.5, 0.0, 0.5]]), decked)[0][0]
    return ([] if on_deck == 2.958 else [f"on the deck: stands at {on_deck}, not 2.958"]) + (
        [] if on_floor == 0.0 else [f"under the deck: stands at {on_floor}, not 0"])


def a_body_under_a_roof_stands_on_its_floor():
    """A floor at 0 and a single-sided roof at 1.84 m: a 1.76 m body standing on the floor (points from its feet to its
    head) reads 0 m over its ground, its head not grounded on the roof 0.08 m over it; the same body on a deck at
    2.958 m stands on the deck, and one on the floor under the deck on the floor. A seated body sits on its seat
    (`seated_reach_problems`); a foot under a desk stands on its floor (`under_a_desk_problems`); a point leans on a
    back (`leaning_problems`)."""
    body = np.array([[0.5, height, 0.5] for height in np.linspace(0.0, 1.76, 12)])
    roofed = np.array(square(0.0) + square(1.84, -1.0, 1.0))
    decked = np.array(square(0.0) + square(2.958, -1.0, 1.0))
    found = {name: np.nanmin(ground.heights_over(points, under, ground.body_reach(points)))
             for name, points, under in (("under the roof", body, roofed), ("on the deck", body + [0, 2.958, 0], decked),
                                         ("under the deck", body, decked))}
    return [f"{name}: {over} over its ground, not 0" for name, over in found.items() if abs(over) > 1e-9] + \
        seated_reach_problems() + under_a_desk_problems() + leaning_problems()


def seated_reach_problems():
    """A floor at 0 and a chair's seat 0.40 m up under a seated body's thighs, its feet on the floor before it and its
    trunk up to 1.3 m: its thighs stand 0 m over the seat, its feet 0 m over the floor. The same seat a lower bunk's
    mattress, the upper bunk's underside 1.0 m up (0.6 m free, under HEADROOM), the body's trunk up to 0.95 m (0.55 m
    over the mattress): its thighs, its centre of mass among them, stand 0 m over the mattress (quarters'
    person_bed, 2026-11-13); a body reaching 1.1 m up there has no room, the mattress a block: its thighs stand on the
    floor under it, 0.4 m over it."""
    feet = [[0.5, height, 0.0] for height in np.linspace(0.0, 0.4, 5)]
    thighs = [[x, 0.4, 0.0] for x in np.linspace(-0.3, 0.1, 5)]
    body = np.array(feet + thighs + [[-0.3, height, 0.0] for height in np.linspace(0.5, 1.3, 9)])
    seated = np.array(square(0.0) + square(0.4, -0.4, 0.2))
    over = ground.heights_over(body, seated, ground.body_reach(body))
    bunk = np.array(square(0.0) + square(0.4, -0.4, 0.2) + square(1.0, -0.4, 0.2))
    low, high = (np.array(feet + thighs + [[-0.3, height, 0.0] for height in np.linspace(0.5, top, 9)])
                 for top in (0.95, 1.1))
    under_bunk = ground.heights_over(low, bunk, ground.body_reach(low), ground.body_floor(low), ground.body_top(low))
    no_room = ground.heights_over(high, bunk, ground.body_reach(high), ground.body_floor(high), ground.body_top(high))
    return [f"{name}: {found} over its ground, not 0" for name, found in
            (("the thighs", np.nanmax(np.abs(over[5:10])) if not np.isnan(over[5:10]).any() else np.nan),
             ("the feet", over[0]),
             ("the thighs on the bunk", np.nanmax(np.abs(under_bunk[5:10])) if not np.isnan(under_bunk[5:10]).any()
              else np.nan)) if not abs(found) < 1e-9] + (
        [] if np.allclose(no_room[5:10], 0.4) else [f"a body too tall for the bunk: its thighs {no_room[5:10]} over its "
                                                     "ground, not 0.4 over the floor"])


def drawer_block():
    """A closed box 0.4 m square round (2, 2) from 0.16 to 0.47 m up, its twelve triangles sharing their corners."""
    low, high = np.array([1.8, 0.16, 1.8]), np.array([2.2, 0.47, 2.2])
    corners = np.array([[low[0] if x else high[0], low[1] if y else high[1], low[2] if z else high[2]]
                        for x in (0, 1) for y in (0, 1) for z in (0, 1)])
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 2, 6),
             (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return corners[np.array(faces)]


def under_a_desk_problems():
    """A body standing on a floor 0.2 m thick (its top at 0), one foot under a desk (its underside at 0.72 m, its top
    at 0.75 m, 0.72 m free under it: under HEADROOM), its hand at 1.1 m over a counter top at 1.0 m under a cupboard at
    1.5 m: the foot under the desk stands 0 m over the floor, never 0.75 m into the desk's top; a foot 3 mm into the
    floor reads 3 mm into it, never over the floor's underside; the hand stands on the floor, the counter top still a
    block. A point 3 mm into a bent floor, on the edge its two triangles share, reads 3 mm into it. A toe on the floor
    under a closed drawer block (its underside 0.16 m up, its top 0.47, within a knee of the toe) stands 0.002 m over
    the floor, never 0.158 into the block's underside (quarters' person_desk's toes under its desk's apron and a bunk's
    rail over person_bed's foot, 2026-11-14); a shin in the block reads 0.27 m into its top."""
    floor = square(0.0) + square(-0.2)
    room = np.array(floor + square(0.72, 0.0, 1.0) + square(0.75, 0.0, 1.0) + square(1.0, -1.0, -0.5)
                    + square(1.5, -1.0, -0.5))
    body = np.array([[0.5, 0.0, 0.5], [-0.3, -0.003, -0.3], [-0.2, 0.9, 0.2], [-0.75, 1.1, -0.75]]
                    + [[-0.2, height, 0.2] for height in np.linspace(0.1, 1.7, 9)])
    over = ground.heights_over(body, room, ground.body_reach(body), ground.body_floor(body), ground.body_top(body))
    corners = np.array([[0.2, 0.0, 1.6], [1.2, 0.1, 0.9], [1.0, 0.0, 1.5], [0.2, 0.3, 1.0]])  # a bent floor 0.2 thick
    bent = np.array([corners[[0, 1, 2]], corners[[0, 2, 3]]])
    on_edge = corners[0] + (corners[2] - corners[0]) * 0.43 - [0.0, 0.003, 0.0]  # its two triangles cross 4e-17 apart
    block = drawer_block()
    toe = np.array([[2.0, 0.002, 2.0], [2.0, 0.2, 2.1]] + [[2.0, height, 1.6] for height in np.linspace(0.5, 1.2, 8)])
    with_block = np.concatenate([room, block])
    under_block = ground.heights_over(toe, with_block, ground.body_reach(toe), ground.body_floor(toe),
                                      ground.body_top(toe))
    found = {"the foot under the desk": (over[0], 0.0), "the foot into the floor": (over[1], -0.003),
             "the toe under the drawer block": (under_block[0], 0.002), "the shin in the block": (under_block[1], -0.27),
             "the hand over the counter top": (over[3], 1.1),
             "a point into a bent floor on its edge": (
                 ground.heights_over(on_edge[None], np.concatenate([bent, bent - [0.0, 0.2, 0.0]]))[0], -0.003)}
    return [f"{name}: {height} over its ground, not {wanted}" for name, (height, wanted) in found.items()
            if not abs(height - wanted) < 1e-9]


def reach_up_is_the_casts_knee():
    """REACH_UP is the cast's KNEE, so the cast and the sim body stand a person on the same surface."""
    from score.stages.cast import measure
    return [] if ground.REACH_UP == measure.KNEE else [f"REACH_UP {ground.REACH_UP}, the cast's KNEE {measure.KNEE}"]


def leaning_problems():
    """A seat's back, a triangle 0.5 m wide and 0.6 m tall, its face through the origin leant 15 degrees back from
    upright, and a floor under it, the body's middle 0.3 m in front: a point 3 mm in front of the face leans on it
    3 mm off, pushed towards the middle along the face's normal from its foot on the face; one 2 mm into it 2 mm in
    (-0.002); one 6 mm in front, one beside the back (its foot past its slanted edge, inside its box) and one 1 mm
    over the floor (no back) lean on nothing, and so does the first where its body's floor (a knee over its lowest
    point) is as high as it, as a toe at a riser; with the middle behind the back the first is 3 mm into it
    (cockpit's pilot on his seat's back, 2026-11-14). Two points 3 mm in front of a 4 m wall slanted across the room
    (its box over BIG_CELLS among points spanning the room) lean on it 3 mm off."""
    tilt = np.radians(15.0)
    up, across = np.array([0.0, np.cos(tilt), -np.sin(tilt)]), np.array([1.0, 0.0, 0.0])
    normal = np.cross(across, up)  # towards +z, the front
    back = np.array([[across * x + up * y for x, y in ((-0.25, 0.0), (0.25, 0.0), (-0.25, 0.6))]])
    room = np.concatenate([back, np.array(square(-0.4))])
    on_face = up * 0.2
    points = np.array([on_face + normal * 0.003, on_face - normal * 0.002, on_face + normal * 0.006,
                       across * 0.2 + up * 0.5 + normal * 0.001, [0.0, -0.399, 0.5]])
    middle = np.array([0.0, 0.3, 0.3])
    distance, triangle, turned, foot = ground.leaning(points, room, middle, 0.005, -1.0)
    behind = ground.leaning(points[:1], room, np.array([0.0, 0.3, -0.3]), 0.005, -0.1)[0][0]
    riser = ground.leaning(points[:1], room, middle, 0.005, points[0, 1])[0][0]  # a knee over its lowest: a toe
    problems = []
    for name, found, wanted in (("in front", distance[0], 0.003), ("into it", distance[1], -0.002),
                                ("behind the back's middle", behind, -0.003)):
        if not abs(found - wanted) < 1e-9:
            problems.append(f"the point {name}: {found} off the back, not {wanted}")
    if not (np.allclose(turned[0], normal) and np.allclose(foot[0], on_face) and triangle[0] == 0):
        problems.append(f"the point in front pushed along {turned[0]} from {foot[0]}, not {normal} from {on_face}")
    wall = np.array([[[-2.0, -1.0, 2.0], [2.0, -1.0, -2.0], [2.0, 3.0, -2.0]]])  # 4 m slanted across the room
    facing = np.array([1.0, 0.0, 1.0]) / np.sqrt(2.0)
    near_wall = np.array([[1.0, 1.5, -1.0], [0.5, 0.5, -0.5]]) + 0.003 * facing
    room_wide = np.array([[-1.5, -0.5, -1.5], [1.5, 2.5, 1.5]])  # the body's other points, spanning the room
    slanted = ground.leaning(np.concatenate([near_wall, room_wide]), wall, np.array([1.0, 1.0, 1.0]), 0.005,
                             -1.0)[0][:2]
    if not np.allclose(slanted, 0.003):
        problems.append(f"the points 3 mm off the long slanted wall: {slanted} off it, not 0.003")
    problems += [f"the point {name} leans {found} off a back, not on none" for name, found in
                 zip(("6 mm in front", "beside the back", "over the floor", "as low as its body's floor"),
                     [*distance[2:], riser]) if not np.isnan(found)]
    return problems


def every_normal_points_up():
    """A triangle wound either way has the upward unit normal (0, 1, 0)."""
    both = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                     [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]]])
    found = ground.normals(both)
    return [] if np.allclose(found, [[0.0, 1.0, 0.0]] * 2) else [f"normals {found.tolist()}"]


CHECKS = (a_point_over_a_slope_stands_at_its_height, a_low_top_is_a_block_not_a_floor,
          a_point_on_a_deck_stands_on_the_deck, a_body_under_a_roof_stands_on_its_floor,
          reach_up_is_the_casts_knee, every_normal_points_up)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
