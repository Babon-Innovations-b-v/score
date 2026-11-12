"""A floor thing's model stood on what holds it where the footing's cut (footing.needed_cut, at most its REACH) and the
feet's stretch (even_feet.level_feet) leave it tipping or with a foot off: a model its code leaned stood up, a tall
one cut deeper, and a broad one's sole cut level, in the place's own copy of its baked asset (even_feet.level_asset).

base, 2026-11-12 (the make of assembly@base from its accepted inputs, the resting triage as laid, no settle row):
its seven connecting tubes, a code build the bake keeps as its code made it, leaned 33 degrees (tumble.measure), stood
on two legs at one side of their 8 m length, their weight 2.70 m outside them: no cut within 1 m holds them, turned
upright a cut of 0.15 m does. Its central hub, a 10.5 m dome whose bottom slopes 6 m across it, touched at one spot,
its weight 1.04 m outside: a cut of 1.18 m holds it. Its large hangar (68 x 49 m) and greenhouse dome (20 m across)
stood on footings that hold them, with 623 and 1,605 feet 3 to 10 cm up that even_feet's stretch did not bring down in
its three rounds (the dome's took over 5 minutes): the triage samples a foot's band at most FOOT_SAMPLES points, so on
a band of 200 m^2 its points lie 6 cm apart, over its 5 cm FOOT_LINK, and a gently sloping face rising out of the band
reads as hundreds of feet off; brought down the stretch reads them again apart. Cut level 0.30 and 0.50 m deep, none
is off. A foot's test against the outlines of the touching feet (triage.within_a_foot) made each outline again for
each foot asked: 2.4 million outlines on the dome, 3 minutes a round; made once here, 4 seconds.

base, later that day: its tube, retaken from its picture (a Pixal3D model, no longer a code build), lay 22 degrees off
its frame, a round tube squashed in depth (its oriented box 1.9 x 3.8 x 6.9 m). The box axis nearest up was its 3.8
m side, turned up on which no footing within 1 m holds it, so it was left leaned and tipped 0.28 m in the triage;
turned 69 degrees onto its 1.9 m side (the next axis, least turn first) a cut of 0.09 m holds it.

    levelled(points, triangles)  (the points, [what was done: the turn in degrees, the cuts and gaps in metres]): the
                                 model stood upright when its code leaned it (upright), cut where its footing does not
                                 hold it (footing.needed_cut, else deep_cut), its feet brought down (even_feet.
                                 level_feet) and its sole cut where one is still off (sole_cut)
    upright(points, triangles)   a model tumbled in its frame (tumble.tumbled) that no footing within REACH holds,
                                 turned so an axis of its oriented box stands up, the least turn first, the first a
                                 footing within REACH then holds; its middle across and its lowest where they were
    deep_cut(points, triangles)  the least cut past REACH, at most DEEP of its height, after which its footing holds
                                 its weight as made (footing.holds); 0.0 when none does
    sole_cut(points, triangles)  the least cut (SOLE_STEP apart, at most SOLE of its height) after which no foot is off
                                 (even_feet.off_feet: by SPARE under the triage's TOLERANCE where a cut does it)
    outlines(down)               whether a foot lies inside the outline of one of the touching feet `down`, as
                                 triage.within_a_foot judges it, each outline made once
"""
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# The most a footing is cut past footing.REACH, a share of the model's height: base's central hub (10.5 m) was cut
# 1.18 m. A model under 2 m tall is cut no deeper than REACH.
DEEP = 0.125
# The most a sole is cut level, a share of the model's height, and the cuts tried, metres apart: base's greenhouse
# dome (12.2 m) was cut 0.50 m, its hangar (11.2 m) 0.30 m; its dome as baked again (528647ac) 0.65 m.
SOLE = 0.06
SOLE_STEP = 0.05
# How far, metres, under the triage's TOLERANCE a sole is cut until no foot is off, where a cut within SOLE does it:
# the triage reads the laid model over its made ground, never quite level. base's greenhouse dome (2026-11-12), cut
# 0.60 m, kept a foot 2.99 cm up (a face rising out of its sole, sampled), read 3.03 cm over its ground.
SPARE = 0.005


def levelled(points, triangles):
    """The model's points (+y up, metres, as laid) stood on what holds it (module docstring), and what was done ([]
    with nothing)."""
    from score.stages.assembly import even_feet, footing
    points, turned = upright(points, triangles)
    cut = footing.needed_cut(points, triangles)
    cut = deep_cut(points, triangles) if cut is None else cut
    stood = footing.cut_at(points, cut) if cut else np.asarray(points, dtype=np.float64)
    stood, gaps = even_feet.level_feet(stood, triangles)
    stood, sole = sole_cut(stood, triangles)
    return stood, turned + ([round(cut, 4)] if cut else []) + gaps + sole


def upright(points, triangles):
    """(the points, [the turn, degrees]) of a model tumbled in its frame that no footing within REACH holds, turned
    onto the first axis of its oriented box (the least turn first) on which a footing within REACH then holds it; the
    points as they are and [] when none does."""
    from score.stages.assembly import footing
    from score.stages.surfaces import tumble
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 4 or not tumble.tumbled(points) or footing.needed_cut(points, triangles) is not None:
        return points, []
    axes, _, _ = tumble.oriented(points)
    middle = (points.min(axis=0) + points.max(axis=0)) / 2
    # each axis of its oriented box, the least turn first: a round section's box turns freely about its length
    for up in sorted((axes[:, column] / np.linalg.norm(axes[:, column]) * (np.sign(axes[1, column]) or 1.0)
                      for column in range(3)), key=lambda way: -way[1]):
        turn = turned_onto(up, np.array([0.0, 1.0, 0.0]))
        stood = (points - middle) @ turn.T
        stood += [middle[0] - (stood[:, 0].min() + stood[:, 0].max()) / 2, points[:, 1].min() - stood[:, 1].min(),
                  middle[2] - (stood[:, 2].min() + stood[:, 2].max()) / 2]
        if footing.needed_cut(stood, triangles) is not None:
            return stood, [round(float(np.degrees(np.arccos(np.clip(up[1], -1.0, 1.0)))), 2)]
    return points, []


def turned_onto(way, onto):
    """The least turn (3 x 3) taking the unit vector `way` onto the unit vector `onto` (Rodrigues)."""
    axis = np.cross(way, onto)
    sine, cosine = np.linalg.norm(axis), float(way @ onto)
    if sine < 1e-9:
        return np.eye(3)
    axis /= sine
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) + sine * cross + (1.0 - cosine) * cross @ cross


def deep_cut(points, triangles):
    """The least cut past footing.REACH (footing.CUT_STEP apart, at most DEEP of the model's height) after which its
    footing holds both its weights as made (holds_as_made: read on the model as cut, whose faces reaching over the cut
    still slope up from it); 0.0 when none does."""
    from score.stages.assembly import footing
    points = np.asarray(points, dtype=np.float64)
    deepest = DEEP * float(np.ptp(points[:, 1]))
    heights = np.arange(footing.REACH + footing.CUT_STEP, deepest + footing.CUT_STEP / 2, footing.CUT_STEP)
    return next((round(float(height), 4) for height in heights
                 if holds_as_made(footing.cut_at(points, float(height)), triangles)), 0.0)


def holds_as_made(points, triangles):
    """Whether the model's footing holds both its weights as it is (footing.holds as made: the triage's tip and the
    drop's sole)."""
    import trimesh
    from score.stages.assembly import footing
    mesh = trimesh.Trimesh(points, np.asarray(triangles).reshape(-1, 3), process=False)
    if mesh.area <= 0:
        return True
    dense = np.vstack([points, mesh.sample(footing.SAMPLES, seed=0)])
    return footing.holds(footing.weights_of(mesh), dense, 0.0, made=True)


def sole_cut(points, triangles):
    """(the points, [the cut, metres]) with the model's sole cut level at the least cut (SOLE_STEP apart, at most SOLE
    of its height) after which no foot is off SPARE under the triage's TOLERANCE, else none off at its TOLERANCE; the
    points as they are and [] when none is off or no such cut is."""
    from score.stages.assembly import even_feet, footing
    points = np.asarray(points, dtype=np.float64)
    cuts = np.arange(SOLE_STEP, SOLE * float(np.ptp(points[:, 1])) + SOLE_STEP / 2, SOLE_STEP)
    for spare in (SPARE, 0.0):
        if not even_feet.off_feet(points, triangles, spare):
            return points, []
        for cut in cuts:
            flat = footing.cut_at(points, float(cut))
            if not even_feet.off_feet(flat, triangles, spare):
                return flat, [round(float(cut), 4)]
    return points, []


def outlines(down):
    """Whether a foot's points lie, seen from above, inside the outline of one of the touching feet `down` (each a
    foot's points), as triage.within_a_foot judges it: a function of the foot's points. Each outline is made once and
    asked only of a foot inside its box."""
    from scipy.spatial import Delaunay
    made = []
    for touching in down:
        across = touching[:, [0, 2]]
        if len(across) < 3 or np.linalg.matrix_rank(across - across.mean(axis=0), tol=1e-6) < 2:
            continue
        made.append((across.min(axis=0), across.max(axis=0), Delaunay(across)))

    def within(members):
        across = members[:, [0, 2]]
        low, high = across.min(axis=0), across.max(axis=0)
        return any(bool(np.all(low >= box_low) and np.all(high <= box_high) and
                        (outline.find_simplex(across) >= 0).all()) for box_low, box_high, outline in made)
    return within
