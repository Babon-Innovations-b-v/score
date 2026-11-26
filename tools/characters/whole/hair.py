"""A person's strand hair combed on the head it is worn on (#223): roots on that head's own scalp, each strand laid
from its root by the style (`data/people/hair/<look>.json`: its length, wave, parting and fringe), and the checks
that fail a groom that does not sit on its head.

The groom grown in Blender on the made person's hair shell (`../hair/groom.py`, #227) does not fit the face's head
the whole person wears: brought onto it point by point (each point dropped to its nearest skin), whole rows of
strands collapsed into flat blocks over the eyes, the crown showed bald and strands stood out straight
(2026-11-25). So the hair is combed again here on the worn head, at the build's bind, in the rig's frame (y up, the
face looking along +z, the person's left +x):

- `scalp_mask`: the head's skin above its hairline, read off the eyes (the head's middle behind them): HAIRLINE gives
  the hairline's height over the eyes round the head (the forehead's front, the temples, over the ears, the nape),
  jittered along the head (HAIRLINE_JITTER), and the ears (skin standing EAR_OUT_M further off the head's upright
  than the skull round it) are left out.
- `parting_line`: the parting as one explicit curve on the scalp, from the hairline at the style's side and offset
  back to the crown's whorl (WHORL). Round 1 (2026-11-26) ended its parting short of the crown and combed the hair
  behind it straight back: from above, a bald oval beside the parting and bald strips fanning from it.
- `combed`: GUIDES guides rooted on the scalp by area (`roots`): full density from HAIRLINE_RAMP_M over the
  hairline, and under it a BABY_BAND_M band of baby hairs at BABY_DENSITY (owner, 2026-11-25: "hairline is also
  still just crazy gap"; round 1's judges: no baby hairs), each short (BABY_LENGTH_M), fine (BABY_RADIUS) and lying its
  own way (BABY_LEAN, `wisped`). Each guide is stepped STEP_M at a time by `comb`: beside the parting away from it and
  COMB_BACK back along it, the roots within PART_CROSS_M of it first leaning across it (`part_lean`: flat hair combed
  away from a line leaves some 6 mm of scalp bare beside it), round the whorl spiralling out of it (WHORL_TWIST), each
  with its own lean (LEAN), its layer its lock's (LOCK_LAYER, the roots' lift and the crown's volume thickest at the
  parting and the whorl) and its own (LAYER_SPREAD), so the hair is not laid as one shell; turning to gravity below
  the crown, lying LAYER over the head's hull (`head_hull`, ears and all: laid on the skin it stood out round the ears
  in a ledge), rising to it over ROOT_RISE_M, free once below the head's widest (HUG_OVER_EYES_M) so the bob hangs as
  a curtain, one the skin holds from falling moved out over it (`draped`). A strand in front of the head never falls
  over the face: within the face's width it runs across (the fringe to the style's fringe side) until it is past the
  eyes. Its end falls at the bob's line (END_BELOW_EYES_M under the eyes, its lock's LOCK_ENDS_M and its own
  ENDS_SPREAD_M round it), its tip turned in (TIP_TURN_M). Then a head's hairs are rooted (`full_density`) and grown
  from the guides (`grown`): each the shape of its nearest guide on its side of the parting, drawn towards its lock's
  middle where it hangs (LOCKS locks, LOCK_PULL: hair hangs in locks; drawn together on the head too they left bare
  wedges between the locks), cut up to CUT_SOFT_M short (CUT_SHAPE: a point cut, never a blunt line), the style's
  wave across it in its lock's phase, a few strayed out as flyaways (FLYAWAY_SHARE) and a few on the crown cut short
  and lifted off it (FRIZZ_SHARE); POINTS points closer near the root (POINT_SPACING), its radius a human hair's,
  its tip tapered (RADIUS, TIP_TAPER; three times that read as a wet wig's).

`measured` reads the groom on its head and `faults` names what is past a limit:
- roots off the scalp: a root further than ROOT_OFF_M from the scalp's skin (off the skin, or on the face or an ear);
- strands before the eyes: any strand point in the box before the eyes (EYE_BOX: past their outer corners, from
  over the brows to the cheeks, in front of the eyeballs' middles);
- scalp seen bare from above (`top_bare`): the hair rendered from above, straight down and tilted to each side
  (TOP_VIEWS), the scalp's picture and the strands' cover over each pixel; the share of the seen scalp showing bare
  away from the parting's own 3 mm line and the whorl's middle (past TOP_BARE_LIMIT) and its largest bare patch (past
  TOP_PATCH_LIMIT_M2). Round 1's measures (a share of the scalp with no hair in a column over it, and the parting's
  bare run from above) passed a groom the judges saw bald strips and an oval in from above;
- clumps: the most strands in one CLUMP_CELL_M cell over the 99th percentile of the cells holding hair;
- strays: strand points standing further than STRAY_M off the skin over the eyes (a strand standing out straight);
- gaps in the roots: a place on the scalp further than ROOT_GAP_M from its nearest root (`root_gap`);
- a hard hairline: the forehead's root density per area of skin rising from a tenth to nine tenths of the hair's full
  density over less than HAIRLINE_SOFT_LIMIT_M (`hairline_soft`);
- a strand thicker than a hair: past HAIR_RADIUS_LIMIT_M;
- a blunt cut: the hanging ends spread less than CUT_SPREAD_LIMIT_M round their neighbours' (`cut_spread`);
- a ledge: the outline seen from behind stepping out more than OUTLINE_STEP_LIMIT_M over the band before
  (`outline_step`).
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

# The scalp's full root density (hairs a m2) at the temples, the nape and the vertex, rising from the hairline to the
# vertex's over DENSITY_RISE_M: phototrichograms of healthy women count some 200 to 300 hairs a cm2 at the vertex
# (one 1 cm2 vertex study: 300 +/- 20 in women 18 to 30; 293 at 35 falling to 211 at 70), temple < nape < vertex (Eur
# J Dermatol 2015, "Diversity in human hair growth"). Round 1 rooted 100 000 evenly, 134 a cm2: from above the scalp
# showed through.
DENSITY = {"temple": 1.6e6, "nape": 2.0e6, "vertex": 2.6e6}
DENSITY_RISE_M = 0.05
GUIDES = 12000  # strands combed step by step; every other strand is grown from them (`grown`)
BLEND_GUIDES = 3  # each strand the shape of its nearest guides blended (one guide's copies laid ribbons with gaps),
BLEND_APART_M = 0.004  # each counting less the further its path runs from the nearest's (on average, m)
GUIDE_SAMPLES = 96  # points a guide is read at when its strands are grown
POINTS = 32
POINT_SPACING = 1.5  # a strand's points closer near its root, where it turns most, as this power of the share along
STEP_M = 0.003
WHORL = {"behind_m": 0.045, "toward_part": 0.4}  # the crown's whorl: behind the head's middle, a share of the parting's
# offset to its side
PART_SAMPLES = 200  # the parting curve is read at this many places
RADIUS = 0.00004  # a strand's radius: a human hair is 50 to 100 um across, the same along its shaft
TIP_TAPER = (0.1, 0.5)  # only its last share tapers, to this share at the tip (tapered root to tip, the hair lying
# over the crown from roots a hand away was half its thickness: thin cover)
# The hairline's height over the eyes' middle (m) round the head, by the angle off the face's front (degrees): the
# forehead's front, the temples, over the ear, behind it, the nape.
HAIRLINE = ((0.0, 0.072), (30.0, 0.066), (55.0, 0.045), (75.0, 0.030), (95.0, 0.032), (115.0, -0.030),
            (140.0, -0.060), (180.0, -0.072))
EAR_OUT_M = 0.010  # skin this much further off the head's upright than the skull at its height and angle is an ear
SURFACE_M = 0.0012  # the head's skin is read at about this spacing as strands are stepped over it
HULL_UNDER_EYES_M = 0.045  # the hair lying on the head lies over the head's hull from this far under the eyes up
CROWN_ABOVE_EYES_M = 0.10  # the turn to gravity starts this far over the eyes
FALL_M = 0.06  # and is whole this far under that
HUG_OVER_EYES_M = -0.005  # over this height the hair lies on the head; under it it hangs
LAYER = (0.002, 0.010)  # how far a strand lies off the hull: from the hairline's roots to the parting's
LAYER_SPREAD = 0.35  # each strand's own layer, varied by up to this share of it (one layer read as flat sheets)
LEAN = 0.12  # each strand's own level lean off the comb on the head, a share of its direction (one read as sheets)
# The hairline's jitter along the head (each: m up and down, its wavelength along the head in m, its phase), read
# along an arc of JITTER_RADIUS_M (round 1's smooth line read as a wig's edge)
HAIRLINE_JITTER = ((0.0012, 0.013, 0.7), (0.0006, 0.0045, 2.1), (0.0003, 0.0021, 4.0))
JITTER_RADIUS_M = 0.09
BABY_BAND_M = 0.009  # a band of baby hairs this deep under the hairline (a real hairline's 8 to 10 mm of fine hairs)
BABY_DENSITY = (0.3, 0.5)  # rooted at this share of the full density, from the band's outer edge to the hairline
HAIRLINE_RAMP_M = 0.002  # over which the density rises from the band's to full over the hairline
BABY_LENGTH_M = (0.006, 0.025)  # a baby hair's length
BABY_RADIUS = 0.5  # and its share of a strand's radius
BABY_LEAN = 0.5  # its own lean off the comb, a share of the direction
BABY_WISP = (0.15, 0.45)  # and its tip bent off its way by this share of its length
ROOT_RISE_M = 0.006  # along which a strand rises from its root to its layer (rising over 12 mm, the hair at the
# parting stood as a thin forest the scalp showed through, 2026-11-26)
FACE_HALF_M = 0.058  # the face's half width from the eyes' middle: a strand within it in front never falls
FACE_FRONT_M = 0.035  # a place this far in front of the head's middle is in front of the head
SWEEP_DOWN = 0.18  # how much a strand running across the forehead falls for each metre across
PART_CROSS_M = 0.003  # roots this near the parting first lean across it, as hair at a parting stands and falls over
PART_LEAN = 2.5  # it: up to this much of the comb's direction, fading with the distance (flat hair combed away from a
# line covers the scalp only some 6 mm off it: hair 70 um across at 1.7 roots a mm2)
COMB_FORWARD = 0.6  # how far forward along the parting the comb runs for each metre it runs away from it
PART_ALONG_M = 0.015  # within this of the parting the comb's way away from it falls, to PART_ALONG_LEAST at the line
PART_ALONG_LEAST = 0.15
# The whorl: the hair round it spirals out, turned WHORL_TWIST radians off straight out at its middle, the turn
# fading over WHORL_R_M; the comb turns from the parting's to the whorl's over the line's last (1 - WHORL_BLEND)
# (round 1 ended the parting short of the crown and combed straight back behind it: a bare oval between)
WHORL_TWIST = 1.45
WHORL_R_M = 0.05
WHORL_BLEND = 0.7
WHORL_CROSS_M = 0.015  # roots this near the whorl's middle first lean in over it (`part_lean`) by up to WHORL_LEAN
WHORL_LEAN = 1.0  # of the comb's direction (2.5 over 25 mm stood the crown up in loops, 2026-11-26)
TURN = 0.4  # how much of its wanted direction a strand lying on the head takes each step
TURN_HANGING = 0.8  # and one hanging: it drops as soon as it leaves the head
SNAG_DOWN = 0.7  # a hanging strand heading down at least this steeply that the skin holds is snagged (`draped`)
HANG_OUT = 0.08  # a hanging strand's lean out from the head's upright, for each metre down
END_BELOW_EYES_M = 0.105  # the bob's ends: the jaw and the neck's top under the eyes
ENDS_SPREAD_M = 0.008  # each guide's end varied by this (one sigma) round its lock's
LOCKS = 1500  # the hair falls in locks: guides rooted together hang together
LOCK_ENDS_M = 0.014  # each lock's end varied by this (one sigma) round the bob's line: a soft, uneven cut
LOCK_PULL = (0.3, 0.75)  # how far a strand is drawn to its lock's middle at its tip, each lock its own
LOCK_REACH_M = 0.015  # and the less the further its middle hangs from it
LOCK_HANG_M = 0.03  # the draw fading in over this much under the height the hair starts to hang (none on the head)
LOCK_LAYER = (0.7, 1.3)  # each lock's layer off the head a share of its place's: the top in locks, not one shell
LOCK_SHAPE = 1.6  # the draw rising from the root to the tip as this power of the share along
CUT_SOFT_M = 0.02  # each strand cut up to this much shorter than its guide (a point cut, not a blunt line)
CUT_SHAPE = 2.0  # the cut drawn as a uniform share to this power: most strands near full length, a few much shorter
WAVE_SPREAD = 0.4  # a lock's wave varied by up to this share of the style's; its strands keep its phase
FLYAWAY_SHARE = 0.008  # this share of the strands rooted past the hairline stray out of their locks
FLYAWAY_M = (0.003, 0.012)  # by this much at their tips
TIP_IN_M = 0.04  # the last of a strand that turns in under the bob
TIP_TURN_M = 0.012  # how far its very tip turns in
# The crown's frizz: this share of the strands rooted this far over the eyes, cut to this length and their tips
# lifted this far off the head
FRIZZ_SHARE = 0.006
FRIZZ_OVER_EYES_M = 0.09
FRIZZ_LENGTH_M = (0.03, 0.10)
FRIZZ_LIFT_M = (0.003, 0.010)
SEED = 223
# The checks.
ROOT_OFF_M = 0.001
EYE_BOX = {"beside_m": 0.018, "over_m": 0.035, "under_m": 0.03, "behind_m": 0.0}  # round the eyes, m
COVER_SAMPLES = 6000
CLUMP_CELL_M = 0.004
CLUMP_LIMIT = 4.0  # the most strands in a cell over the 99th percentile of the cells holding hair
STRAY_M = 0.035
DENSE_M = 0.002  # the strands are read at this spacing by the checks
# The hair rendered from above (`top_bare`): straight down and tilted TOP_TILT degrees towards the front, both sides
# and the back, at pixel_m pixels, the strands within near_m of the scalp read every step_m (segments at a time); the
# full-density scalp from over_m over the hairline, where it faces the camera more than `facing`; a pixel is bare when
# more than `bare` of it shows the scalp, and the parting's own line (part_half_m either side: a real parting is a 2
# to 3 mm line) and the whorl's middle (whorl_m round it) may show. Round 1's groom (2026-11-26: bald strips and an
# oval beside the parting, judged from above) showed 6.4% of its scalp bare and a bare patch of 367 mm2.
TOP_TILT = 30.0
TOP_VIEWS = ((0.0, 0.0), (TOP_TILT, 0.0), (TOP_TILT, 90.0), (TOP_TILT, 180.0), (TOP_TILT, 270.0))
TOP_READ = {"pixel_m": 0.0002, "step_m": 0.0002, "segments": 300000, "near_m": 0.03, "over_m": 0.002, "facing": 0.35,
            "bare": 0.5, "part_half_m": 0.0015, "whorl_m": 0.002}
TOP_BARE_LIMIT = 0.005  # the most of the seen scalp one view may show bare
TOP_PATCH_LIMIT_M2 = 4e-6  # and its largest bare patch (4 mm2: a few hairs' gap, never a strip or an oval)
ROOT_GAP_M = 0.0025  # no place on the scalp further than this from a root
HAIRLINE_SOFT_LIMIT_M = 0.006  # the forehead's root density rises from a tenth to nine tenths over at least this
HAIRLINE_READ = {"skin": 100000, "front_deg": 45.0, "from_m": -0.01, "to_m": 0.02, "band_m": 0.001, "full_from_m": 0.01}
HAIR_RADIUS_LIMIT_M = 0.00006  # no strand thicker than a thick human hair (120 um across)
CUT_READ = 3000  # the ends read, evenly through them
CUT_NEAR = 300  # each read off the median of this many ends nearest it (some 3 mm round it on a head)
CUT_SPREAD_LIMIT_M = 0.008  # the hanging strands' ends spread at least this (one sigma): no blunt, flat cut line
OUTLINE_READ = {"share": 0.999, "band_m": 0.01, "under_eyes_m": 0.06, "fewest": 200}
OUTLINE_STEP_LIMIT_M = 0.002  # the outline seen from behind steps out at most this more than the band before


def unit(vectors):
    return vectors / np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)


def tangent(vectors, normals):
    """The vectors laid flat on the surface with `normals`, unit length."""
    return unit(vectors - normals * np.einsum("pi,pi->p", vectors, normals)[:, None])


def head_frame(points, eyes):
    """The eyes' middle, the head's middle (at the eyes' height, x and z of the skull's top) and its top's height."""
    middle = np.asarray(eyes, float).mean(axis=0)
    cap = points[points[:, 1] > middle[1] + 0.04]
    return middle, np.array([cap[:, 0].mean(), middle[1], cap[:, 2].mean()]), float(cap[:, 1].max())


def around(points, centre):
    """Each point's angle off the face's front round the head's upright (degrees, 0..180) and its distance off it."""
    flat = points[:, [0, 2]] - centre[[0, 2]]
    return np.degrees(np.abs(np.arctan2(flat[:, 0], flat[:, 1]))), np.linalg.norm(flat, axis=1)


def is_ear(points, centre, angle, radius):
    """Points beside the head standing EAR_OUT_M further off its upright than the skull's median at their height
    (1 cm rows) and angle (10 degree sectors)."""
    keys = np.round((points[:, 1] - centre[1]) / 0.01) * 100 + np.round(angle / 10.0)
    skull = np.zeros(len(points))
    for key in np.unique(keys):
        mine = keys == key
        skull[mine] = np.median(radius[mine])
    return (radius - skull > EAR_OUT_M) & (angle > 60.0) & (angle < 130.0)


def over_hairline(points, eyes, centre):
    """Each point's height over the hairline (HAIRLINE, jittered along the head by HAIRLINE_JITTER: a real hairline
    is never one smooth curve) at its angle round the head (m, negative under it)."""
    angle, _ = around(points, centre)
    table = np.asarray(HAIRLINE)
    arc = np.arctan2(points[:, 0] - centre[0], points[:, 2] - centre[2]) * JITTER_RADIUS_M
    jitter = sum(size * np.sin(2.0 * np.pi * arc / wave + phase) for size, wave, phase in HAIRLINE_JITTER)
    return (points[:, 1] - np.asarray(eyes, float).mean(axis=0)[1] - np.interp(angle, table[:, 0], table[:, 1])
            - jitter)


def scalp_mask(points, faces, eyes, under_m=0.0):
    """Which of the skin's triangles are the scalp: every corner over the hairline (HAIRLINE; lowered `under_m`, the
    soft hairline's fine hairs), on the head and none an ear."""
    middle, centre, _ = head_frame(points, eyes)
    angle, radius = around(points, centre)
    over = over_hairline(points, eyes, centre) > -under_m
    near = (points[:, 1] > middle[1] - 0.12) & (radius < 0.16)
    keep = over & near & ~is_ear(points, centre, angle, radius)
    return keep[faces].all(axis=1)


def parting_line(points, faces, eyes, style):
    """The parting as one explicit curve on the scalp, from the hairline at the style's side and offset back to the
    crown's whorl (WHORL: behind the head's middle, a share of the parting's offset to its side), bending towards
    the whorl behind (its offset falling as the square of the share along): (PART_SAMPLES places on the scalp, the
    whorl's place)."""
    middle, centre, _ = head_frame(points, eyes)
    offset = (1.0 if style["parting_side"] == "left" else -1.0) * style["parting_m"]
    scalp = np.unique(faces[scalp_mask(points, faces, eyes)])
    normals = np.asarray(trimesh.Trimesh(points, faces, process=False).vertex_normals)[scalp]
    upward = points[scalp[normals[:, 1] > 0.3]]
    start = np.array([middle[0] + offset, upward[np.abs(upward[:, 0] - middle[0] - offset) < 0.004, 2].max()])
    whorl = np.array([middle[0] + WHORL["toward_part"] * offset, centre[2] - WHORL["behind_m"]])
    share = np.linspace(0.0, 1.0, PART_SAMPLES)
    flat = np.stack([start[0] + (whorl[0] - start[0]) * share ** 2, start[1] + (whorl[1] - start[1]) * share], axis=1)
    distance, nearest = cKDTree(upward[:, [0, 2]]).query(flat, k=6)
    weight = 1.0 / np.maximum(distance, 1e-6)
    height = (upward[nearest, 1] * weight).sum(axis=1) / weight.sum(axis=1)
    line = np.stack([flat[:, 0], height, flat[:, 1]], axis=1)
    return line, line[-1]


def root_density(over):
    """The roots' density, a share of the hair's full, at `over` (m) over the hairline: BABY_DENSITY across the
    BABY_BAND_M band of baby hairs under it, rising to full over HAIRLINE_RAMP_M over it, none under the band."""
    band = BABY_DENSITY[0] + (BABY_DENSITY[1] - BABY_DENSITY[0]) * (over + BABY_BAND_M) / BABY_BAND_M
    ramp = BABY_DENSITY[1] + (1.0 - BABY_DENSITY[1]) * over / HAIRLINE_RAMP_M
    return np.where(over < -BABY_BAND_M, 0.0, np.where(over < 0.0, band, np.minimum(ramp, 1.0)))


def full_density(places, eyes, centre):
    """The scalp's full root density at each place (hairs a m2, DENSITY): the temples' at the hairline in front of the
    ears, the nape's behind them, rising to the vertex's over DENSITY_RISE_M over the hairline."""
    angle, _ = around(places, centre)
    edge = np.interp(angle, [0.0, 100.0, 140.0, 180.0], [DENSITY["temple"], DENSITY["temple"], DENSITY["nape"],
                                                          DENSITY["nape"]])
    rise = np.clip(over_hairline(places, eyes, centre) / DENSITY_RISE_M, 0.0, 1.0)
    return edge + (DENSITY["vertex"] - edge) * rise


def roots(points, faces, eyes, rng, count=None):
    """Roots on the scalp at `full_density` times `root_density` (`count` of them, or as many as the scalp holds):
    (the roots, 1 for a full hair's root and 0 for a baby hair's, under the hairline)."""
    _, centre, _ = head_frame(points, eyes)
    scalp = faces[scalp_mask(points, faces, eyes, BABY_BAND_M)]
    if count is None:
        places = on_triangles(points, scalp, 200000, np.random.default_rng(SEED + 7))[0]
        corners = points[scalp]
        area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum()
        count = int(area / 2.0 * np.mean(full_density(places, eyes, centre)
                                         * root_density(over_hairline(places, eyes, centre))))
    found, full = [], []
    while sum(len(place) for place in found) < count:
        places = on_triangles(points, scalp, count, rng)[0]
        over = over_hairline(places, eyes, centre)
        share = root_density(over) * full_density(places, eyes, centre) / DENSITY["vertex"]
        kept = rng.random(len(places)) < share
        found.append(places[kept])
        full.append((over[kept] >= 0.0).astype(float))
    return np.concatenate(found)[:count], np.concatenate(full)[:count]


def on_triangles(points, faces, count, rng):
    """`count` places on the triangles, by area."""
    corners = points[faces]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2.0
    picked = rng.choice(len(faces), size=count, p=area / area.sum())
    weights = rng.dirichlet(np.ones(3), count)
    return np.einsum("pc,pcd->pd", weights, corners[picked]), picked, weights


def head_surface(points, faces, eyes):
    """The head's skin read every SURFACE_M or so: (places, their smooth outward normals, a tree of the places)."""
    middle = np.asarray(eyes, float).mean(axis=0)
    normals = np.asarray(trimesh.Trimesh(points, faces, process=False).vertex_normals)
    head = faces[(points[faces][..., 1] > middle[1] - 0.25).all(axis=1)]
    corners = points[head]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum() / 2.0
    places, picked, weights = on_triangles(points, head, int(area / SURFACE_M ** 2), np.random.default_rng(SEED + 2))
    return places, unit(np.einsum("pc,pcd->pd", weights, normals[head[picked]])), cKDTree(places)


def head_hull(points, eyes):
    """The head's convex hull from HULL_UNDER_EYES_M under the eyes up, ears and all, read every SURFACE_M or so:
    (places, their outward normals, a tree of the places). The hair lying on the head lies over it: laid over the
    skin it ran in under the ears' tops and stood out round them in a ledge ("earmuffs" seen from behind,
    2026-11-26)."""
    middle, centre, _ = head_frame(points, eyes)
    _, radius = around(points, centre)
    head = points[(points[:, 1] > middle[1] - HULL_UNDER_EYES_M) & (radius < 0.16)]
    hull = trimesh.convex.convex_hull(head)
    faces = np.asarray(hull.faces)
    area = float(hull.area)
    places, picked, _ = on_triangles(np.asarray(hull.vertices), faces, int(area / SURFACE_M ** 2),
                                     np.random.default_rng(SEED + 5))
    return places, np.asarray(hull.face_normals)[picked], cKDTree(places)


def nearest_on(surface, places):
    """Each place's nearest point on the head's skin and the outward normal there."""
    _, index = surface[2].query(places, workers=-1)
    return surface[0][index], surface[1][index]


def parted(places, line):
    """Each place's side of the parting curve `line` (+1 on her left of it; behind the whorl, the line's end, by the
    side of the whorl it is on), the share along the line of its nearest place there (0 at the hairline, 1 at the
    whorl) and the line's way back there (x, z)."""
    nearest = cKDTree(line[:, [0, 2]]).query(places[:, [0, 2]])[1]
    ahead = np.clip(nearest + 1, 0, len(line) - 1)
    behind = np.clip(nearest - 1, 0, len(line) - 1)
    way = unit(line[ahead][:, [0, 2]] - line[behind][:, [0, 2]])
    off = places[:, [0, 2]] - line[nearest][:, [0, 2]]
    # her left is +x; going back along the line (-z), her left lies at the way turned by (-z, x)
    side = np.sign(off[:, 0] * -way[:, 1] + off[:, 1] * way[:, 0])
    return np.where(side == 0.0, 1.0, side), nearest / (len(line) - 1.0), way


def comb(places, normals, line, sweep, middle, centre, hanging):
    """Each strand's wanted direction at its place: beside the parting `line` away from it and COMB_BACK back along
    it; round the crown's whorl (the line's end) spiralling out of it (WHORL_TWIST, fading over WHORL_R_M), so the hair
    behind the parting flows from the whorl, never from a second parting or a bare oval; turning to gravity below
    the crown, straight down once hanging; in front of the head within the face's width, across to `sweep` and only
    a little down."""
    count = len(places)
    down = np.tile([0.0, -1.0, 0.0], (count, 1))
    side, along, way = parted(places, line)
    across_part = np.stack([-way[:, 1], way[:, 0]], axis=1) * side[:, None]
    # Beside the parting the hair lies back along it before it turns away: combed straight away from a line it
    # covers the scalp only some 6 mm off it (hair 70 um across at 1.3 to 2 roots a mm2), so the line read wide
    off = np.clip(cKDTree(line[:, [0, 2]]).query(places[:, [0, 2]])[0] / PART_ALONG_M, PART_ALONG_LEAST, 1.0)
    # Along the parting the hair runs forward, away from the whorl, as a head's hair grows out of its one whorl and a
    # parting only splits it: combed back along the parting it met the whorl's own outward flow there and parted
    # round it bare, and nothing lay over the scalp behind the front hairline (2026-11-26)
    away = unit(across_part * off[:, None] - COMB_FORWARD * way)
    whorl = line[-1]
    out = places[:, [0, 2]] - whorl[[0, 2]]
    reach = np.linalg.norm(out, axis=1)
    turn = WHORL_TWIST * np.exp(-reach / WHORL_R_M)
    radial = unit(out)
    spiral = np.stack([np.cos(turn) * radial[:, 0] - np.sin(turn) * radial[:, 1],
                       np.sin(turn) * radial[:, 0] + np.cos(turn) * radial[:, 1]], axis=1)
    blend = np.clip((along - WHORL_BLEND) / (1.0 - WHORL_BLEND), 0.0, 1.0)[:, None]
    flat = unit(away * (1.0 - blend) + spiral * blend)
    over = tangent(np.stack([flat[:, 0], np.zeros(count), flat[:, 1]], axis=1), normals)
    fall = np.clip((middle[1] + CROWN_ABOVE_EYES_M - places[:, 1]) / FALL_M, 0.0, 1.0)[:, None]
    # falling, the hair keeps the comb's way across but never forward: combed forward down the temples it curved
    # round onto the face and over the eyes
    kept = over * [1.0, 1.0, 0.0] + over * [0.0, 0.0, 1.0] * (over[:, 2:] < 0.0)
    direction = over * (1.0 - fall) + (kept * 0.25 + tangent(down, normals)) * fall
    outward = np.zeros((count, 3))
    outward[:, [0, 2]] = places[:, [0, 2]] - centre[[0, 2]]
    direction[hanging] = down[hanging] + HANG_OUT * unit(outward[hanging])
    front = (places[:, 2] - centre[2] > FACE_FRONT_M) & (np.abs(places[:, 0] - middle[0]) < FACE_HALF_M)
    across = np.stack([sweep, np.full(count, -SWEEP_DOWN), np.zeros(count)], axis=1)
    direction[front] = tangent(across[front], normals[front])
    return unit(direction)


def stepped(points, faces, eyes, style, rng, rooted, lock):
    """Every guide's path from its root (guides x steps x 3; a strand that ended stays at its last place): lying over
    the head's hull (`head_hull`) while over HUG_OVER_EYES_M, rising from its root to its layer (thickest at the
    parting and the whorl, its lock's own LOCK_LAYER share of it: the roots' lift and the crown's volume) at most as
    steeply as it travels, then hanging off the skin; its end at the bob's line moved by its lock's (`lock`: ends
    shift, layer share). A baby hair's guide is BABY_LENGTH_M long and leans BABY_LEAN its own way."""
    skin, hull = head_surface(points, faces, eyes), head_hull(points, eyes)
    middle, centre, top = head_frame(points, eyes)
    line, _ = parting_line(points, faces, eyes, style)
    full = over_hairline(rooted, eyes, centre) >= 0.0
    side = parted(rooted, line)[0]
    sweep = np.where(side > 0.0, 1.0, 1.0 if style["fringe_side"] == "left" else -1.0)
    from_part = cKDTree(line).query(rooted)[0]
    layer = LAYER[0] + (LAYER[1] - LAYER[0]) * (1.0 - np.clip(from_part / np.percentile(from_part, 98), 0.0, 1.0))
    layer = layer * lock["layer"] * (1.0 + rng.uniform(-LAYER_SPREAD, LAYER_SPREAD, len(rooted)))
    crossing = part_lean(rooted, line, rng)
    lean = rng.normal(0.0, 1.0, (len(rooted), 3)) * [1.0, 0.0, 1.0] * np.where(full, LEAN, BABY_LEAN)[:, None]
    reach = np.where(full, style["length_m"], rng.uniform(*BABY_LENGTH_M, len(rooted)))
    ends = middle[1] - END_BELOW_EYES_M + lock["ends"] + rng.normal(0.0, ENDS_SPREAD_M, len(rooted))
    place = rooted.copy()
    direction = None
    path, alive, travelled = [place.copy()], np.ones(len(place), dtype=bool), np.zeros(len(place))
    for _ in range(int(style["length_m"] / STEP_M)):
        hanging = place[:, 1] < middle[1] + HUG_OVER_EYES_M
        normal = np.where(hanging[:, None], nearest_on(skin, place)[1], nearest_on(hull, place)[1])
        # The lean only while lying on the head: a hanging strand leaning in at the face's side ran before the eyes.
        wanted = unit(comb(place, normal, line, sweep, middle, centre, hanging) + lean * ~hanging[:, None])
        turn = np.where(hanging, TURN_HANGING, TURN)[:, None]
        direction = (unit(wanted + crossing) if direction is None
                     else unit(direction * (1.0 - turn) + wanted * turn))
        moved = place + direction * STEP_M
        moved = laid(moved, skin, hull, layer * np.clip((travelled + STEP_M) / ROOT_RISE_M, 0.0, 1.0),
                     moved[:, 1] < middle[1] + HUG_OVER_EYES_M)
        moved = draped(moved, place, direction, moved[:, 1] < middle[1] + HUG_OVER_EYES_M, centre)
        alive &= (moved[:, 1] > ends) & (travelled + STEP_M <= reach)
        place = np.where(alive[:, None], moved, place)
        travelled += np.where(alive, STEP_M, 0.0)
        path.append(place.copy())
        if not alive.any():
            break
    return np.stack(path, axis=1), centre, full.astype(float)


def laid(moved, skin, hull, wanted, free):
    """Each step's places at their layer: a strand lying on the head `wanted` off the hull, rising to it at most a
    step a step (a root in a hollow under the hull, behind the ear or at the nape, would jump straight out) and never
    under the skin's first layer; a hanging (`free`) one only kept `wanted` off the skin."""
    on, normal = nearest_on(hull, moved)
    height = np.einsum("pi,pi->p", moved - on, normal)
    moved = moved + normal * np.where(free, 0.0, np.minimum(wanted - height, STEP_M))[:, None]
    on, normal = nearest_on(skin, moved)
    height = np.einsum("pi,pi->p", moved - on, normal)
    floor = np.where(free, wanted, np.minimum(wanted, LAYER[0]))
    return moved + normal * np.maximum(floor - height, 0.0)[:, None]


def draped(moved, place, direction, free, centre):
    """A hanging strand heading down that the skin held from going half its step down (snagged behind an ear, where
    the skin turns under, it stood still and was left out as a strand that never left its root, a hole of roots
    there, 2026-11-25) moved half a step out from the head's upright, so it falls over what holds it."""
    snagged = free & (direction[:, 1] < -SNAG_DOWN) & (moved[:, 1] - place[:, 1] > -0.5 * STEP_M * -direction[:, 1])
    outward = np.zeros((len(moved), 3))
    outward[:, [0, 2]] = moved[:, [0, 2]] - centre[[0, 2]]
    return moved + unit(outward) * (0.5 * STEP_M * snagged)[:, None]


def part_lean(rooted, line, rng):
    """Each root's first lean across the parting `line`: roots within PART_CROSS_M of it lean over it by up to
    PART_LEAN of the comb's direction (fading with their distance from it and into the whorl, where there is no
    parting), so both sides meet over a 2 to 3 mm line instead of a bare strip."""
    side, along, way = parted(rooted, line)
    near = np.clip(1.0 - cKDTree(line).query(rooted)[0] / PART_CROSS_M, 0.0, 1.0)
    near = near * np.clip((WHORL_BLEND - along) / (1.0 - WHORL_BLEND), 0.0, 1.0)
    over = -np.stack([-way[:, 1], way[:, 0]], axis=1) * side[:, None]
    crossing = np.zeros((len(rooted), 3))
    crossing[:, [0, 2]] = over * (near * rng.uniform(0.0, PART_LEAN, len(rooted)))[:, None]
    # round the whorl the roots lean in over its middle before they spiral out: combed straight out of it the hair
    # left its middle bare a centimetre round
    inward = line[-1][[0, 2]] - rooted[:, [0, 2]]
    close = np.clip(1.0 - np.linalg.norm(inward, axis=1) / WHORL_CROSS_M, 0.0, 1.0)
    crossing[:, [0, 2]] += unit(inward) * (close * rng.uniform(0.0, WHORL_LEAN, len(rooted)))[:, None]
    return crossing


def lengths_along(strands):
    """Each strand's length from its root at each of its points."""
    steps = np.linalg.norm(np.diff(strands, axis=1), axis=2)
    return np.concatenate([np.zeros((len(strands), 1)), np.cumsum(steps, axis=1)], axis=1)


def tipped(path, centre):
    """The strands' last TIP_IN_M turned in towards the head's upright under the bob; a strand shorter than twice
    that (the hairline's fine hairs) less, none at all at TIP_IN_M, so its root stays on the scalp."""
    lengths = lengths_along(path)
    long = np.clip(lengths[:, -1:] / TIP_IN_M - 1.0, 0.0, 1.0)
    share = long * np.clip(1.0 - (lengths[:, -1:] - lengths) / TIP_IN_M, 0.0, 1.0) ** 2
    inward = np.zeros_like(path)
    inward[..., [0, 2]] = centre[[0, 2]] - path[..., [0, 2]]
    return path + unit(inward) * (share * TIP_TURN_M)[..., None]


def resampled(path, count):
    """Each strand at `count` points evenly along its length."""
    lengths = lengths_along(path)
    found = np.zeros((len(path), count, 3))
    for index in range(len(path)):
        wanted = np.linspace(0.0, lengths[index, -1], count)
        for axis in range(3):
            found[index, :, axis] = np.interp(wanted, lengths[index], path[index, :, axis])
    return found


def waved(strands, style, phase, size):
    """The style's wave across each strand (times its `size`, at its `phase`: a lock's strands wave together, each
    strand at its own phase crossed its neighbours, "stringy wiry strands", 2026-11-25), rising from its root over
    ROOT_RISE_M."""
    across = unit(np.cross(np.gradient(strands, axis=1), np.array([0.0, 1.0, 0.0])))
    lengths = lengths_along(strands)
    amount = (style["wave_m"] * size[:, None]) * np.sin(2.0 * np.pi * lengths / style["wave_period_m"]
                                                         + phase[:, None])
    return strands + across * (amount * np.clip(lengths / ROOT_RISE_M, 0.0, 1.0))[..., None]


def locks(rooted, side, rng):
    """Each guide's lock, named by its middle guide: LOCKS of the guides are the middles, every guide in the lock of
    its nearest middle on its own side of the parting."""
    middles = rng.choice(len(rooted), size=min(LOCKS, len(rooted)), replace=False)
    middle = np.arange(len(rooted))
    for sign in (-1.0, 1.0):
        mine, theirs = np.flatnonzero(side == sign), middles[side[middles] == sign]
        if len(mine) and len(theirs):
            middle[mine] = theirs[cKDTree(rooted[theirs]).query(rooted[mine])[1]]
    return middle


def read_along(guides, lengths, index, at):
    """The guides `index` (one per strand) read at the lengths `at` (strands x points) from their roots, each guide
    held at GUIDE_SAMPLES points evenly along its `lengths`."""
    share = np.clip(at / np.maximum(lengths[index], 1e-9)[:, None], 0.0, 1.0) * (guides.shape[1] - 1)
    low = np.minimum(np.floor(share).astype(np.int64), guides.shape[1] - 2)
    weight = (share - low)[..., None]
    rows = index[:, None]
    return guides[rows, low] * (1.0 - weight) + guides[rows, low + 1] * weight


def grown(guides, rooted, side, inner, style, rng, guide_side, guide_lock, centre):
    """The strands rooted at `rooted`, each grown from its BLEND_GUIDES nearest guides on its own side of the parting:
    their shapes blended by the inverse square of their distance and moved to the strand's root, drawn towards its
    lock's middle guide where it hangs (LOCK_PULL, LOCK_SHAPE; drawn together where they lie on the head they left
    bare wedges between the locks, round 1), cut up to CUT_SOFT_M
    shorter, the style's wave across it in its lock's phase; a baby hair (`inner` 0) cut to BABY_LENGTH_M and
    wisped (`wisped`); FLYAWAY_SHARE strayed out of their locks and FRIZZ_SHARE on the crown lifted (`strayed`,
    `frizzed`): strands x POINTS x 3."""
    lengths = lengths_along(guides)[:, -1]
    held = resampled(guides, GUIDE_SAMPLES)
    near = np.zeros((len(rooted), BLEND_GUIDES), np.int64)
    weight = np.zeros((len(rooted), BLEND_GUIDES))
    for sign in (-1.0, 1.0):
        mine, theirs = np.flatnonzero(side == sign), np.flatnonzero(guide_side == sign)
        distance, found = cKDTree(held[theirs, 0]).query(rooted[mine], k=BLEND_GUIDES)
        near[mine] = theirs[found]
        weight[mine] = 1.0 / np.maximum(distance, 1e-5) ** 2
    weight /= weight.sum(axis=1, keepdims=True)
    guide = near[:, 0]
    middle = guide_lock[guide]
    reach = np.where(inner > 0.0, style["length_m"], rng.uniform(*BABY_LENGTH_M, len(rooted)))
    full = np.minimum(reach, lengths[near].min(axis=1))
    cut = CUT_SOFT_M * rng.random(len(rooted)) ** CUT_SHAPE
    length = np.maximum(full - cut * (full > 3.0 * CUT_SOFT_M), full * 0.5)
    at = length[:, None] * np.linspace(0.0, 1.0, POINTS)[None] ** POINT_SPACING
    shapes = [read_along(held, lengths, near[:, column], at) - held[near[:, column], :1]
              for column in range(BLEND_GUIDES)]
    # A guide counts in the blend only as far as it runs with the nearest: blended across the whorl, guides heading
    # opposite ways averaged into a strand through the skull (2026-11-26)
    for column in range(1, BLEND_GUIDES):
        apart = np.linalg.norm(shapes[column] - shapes[0], axis=2).mean(axis=1)
        weight[:, column] *= np.exp(-(apart / BLEND_APART_M) ** 2)
    weight /= weight.sum(axis=1, keepdims=True)
    base = rooted[:, None] + sum(weight[:, column, None, None] * shapes[column] for column in range(BLEND_GUIDES))
    towards = read_along(held, lengths, middle, at)
    lock_ids = np.unique(middle, return_inverse=True)[1]
    pull = rng.uniform(*LOCK_PULL, lock_ids.max() + 1)[lock_ids] * inner
    hangs = np.clip((centre[1] + HUG_OVER_EYES_M - base[..., 1]) / LOCK_HANG_M, 0.0, 1.0)
    # drawn only to a middle hanging near it: a lock's middle hanging on the head's other side drew a strand across
    # the face (2026-11-26)
    near = np.exp(-(np.linalg.norm(towards - base, axis=2) / LOCK_REACH_M) ** 2)
    share = (np.linspace(0.0, 1.0, POINTS) ** (LOCK_SHAPE * POINT_SPACING))[None] * pull[:, None] * hangs * near
    strands = base + (towards - base) * share[..., None]
    phase = rng.uniform(0.0, 2.0 * np.pi, lock_ids.max() + 1)[lock_ids]
    size = 1.0 + rng.uniform(-WAVE_SPREAD, WAVE_SPREAD, lock_ids.max() + 1)[lock_ids]
    strands = waved(strands, style, phase, size)
    strands = wisped(strands, inner, centre, rng)
    return frizzed(strayed(strands, inner, centre, rng), inner, centre, rng)


def bent(strands, picked, sizes, centre, rng, outward):
    """The `picked` strands bent off their way by `sizes` (m) at the tip, rising as the share along squared: across
    the strand at random, or out from the head's middle when `outward`."""
    if outward:
        off = unit(strands[picked, -1] - centre)
    else:
        off = unit(np.cross(strands[picked, -1] - strands[picked, 0], rng.normal(size=(len(picked), 3))))
    along = np.linspace(0.0, 1.0, POINTS)[None] ** (2 * POINT_SPACING)
    strands = strands.copy()
    strands[picked] += off[:, None] * (sizes[:, None] * along)[..., None]
    return strands


def wisped(strands, inner, centre, rng):
    """The baby hairs (`inner` 0) bent off their way by BABY_WISP of their length at the tip: fine short hairs lie
    every which way, never combed with the hair behind them."""
    picked = np.flatnonzero(inner <= 0.0)
    length = np.linalg.norm(strands[picked, -1] - strands[picked, 0], axis=1)
    return bent(strands, picked, rng.uniform(*BABY_WISP, len(picked)) * length, centre, rng, False)


def strayed(strands, inner, centre, rng):
    """FLYAWAY_SHARE of the full strands, none of whose points is before the face, bent off their locks by FLYAWAY_M
    at the tip."""
    front = (strands[..., 2] - centre[2] > FACE_FRONT_M).any(axis=1)
    picked = np.flatnonzero((inner >= 1.0) & ~front)
    picked = picked[rng.random(len(picked)) < FLYAWAY_SHARE]
    return bent(strands, picked, rng.uniform(*FLYAWAY_M, len(picked)), centre, rng, False)


def frizzed(strands, inner, centre, rng):
    """FRIZZ_SHARE of the full strands rooted over the crown (FRIZZ_OVER_EYES_M over the eyes), none before the face,
    cut to FRIZZ_LENGTH_M and lifted out from the head by FRIZZ_LIFT_M at their tips: the short broken hairs that
    stand off a real head's top (a flat, smooth top read as a helmet, round 1)."""
    front = (strands[..., 2] - centre[2] > FACE_FRONT_M).any(axis=1)
    picked = np.flatnonzero((inner >= 1.0) & ~front & (strands[:, 0, 1] > centre[1] + FRIZZ_OVER_EYES_M))
    picked = picked[rng.random(len(picked)) < FRIZZ_SHARE]
    strands = strands.copy()
    keep = rng.uniform(*FRIZZ_LENGTH_M, len(picked))
    strands[picked] = resampled_to(strands[picked], keep)
    return bent(strands, picked, rng.uniform(*FRIZZ_LIFT_M, len(picked)), centre, rng, True)


def resampled_to(strands, keep):
    """Each strand cut to `keep` (m) from its root (or left whole when shorter), at POINTS points spaced as
    POINT_SPACING."""
    lengths = lengths_along(strands)
    found = np.zeros_like(strands)
    for index in range(len(strands)):
        wanted = min(keep[index], lengths[index, -1]) * np.linspace(0.0, 1.0, strands.shape[1]) ** POINT_SPACING
        for axis in range(3):
            found[index, :, axis] = np.interp(wanted, lengths[index], strands[index, :, axis])
    return found


def combed(points, faces, eyes, style):
    """The groom on this head at the build's bind: (counts, points, radius), POINTS points a strand. GUIDES guides
    are combed (`stepped`, their ends turned in, `tipped`) and the head's strands grown from them in locks (`grown`); a
    guide that never left its root grows no strand."""
    rng = np.random.default_rng(SEED)
    line, _ = parting_line(points, faces, eyes, style)
    guide_roots, _ = roots(points, faces, eyes, rng, GUIDES)
    guide_side = parted(guide_roots, line)[0]
    lock_middle = locks(guide_roots, guide_side, rng)
    lock = {"ends": rng.normal(0.0, LOCK_ENDS_M, len(guide_roots))[lock_middle],
            "layer": rng.uniform(*LOCK_LAYER, len(guide_roots))[lock_middle]}
    path, centre, inner_guide = stepped(points, faces, eyes, style, rng, guide_roots, lock)
    reach = np.where(inner_guide > 0.0, style["length_m"], BABY_LENGTH_M[0])
    moved = np.linalg.norm(path[:, -1] - path[:, 0], axis=1) > np.minimum(0.02, reach / 2.0)
    kept = np.flatnonzero(moved)
    renumber = np.full(len(path), -1)
    renumber[kept] = np.arange(len(kept))
    middle_kept = renumber[lock_middle[kept]]
    middle_kept = np.where(middle_kept < 0, np.arange(len(kept)), middle_kept)  # its middle never left its root
    guides = tipped(path[kept], centre)
    rooted, inner = roots(points, faces, eyes, rng)
    side = parted(rooted, line)[0]
    strands = grown(guides, rooted, side, inner, style, rng, guide_side[kept], middle_kept, centre)
    fine = BABY_RADIUS + (1.0 - BABY_RADIUS) * inner
    along = np.linspace(0.0, 1.0, POINTS)
    taper = 1.0 - (1.0 - TIP_TAPER[1]) * np.clip((along - 1.0 + TIP_TAPER[0]) / TIP_TAPER[0], 0.0, 1.0)
    radius = (fine[:, None] * RADIUS * taper[None]).reshape(-1)
    return np.full(len(strands), POINTS, np.int64), strands.reshape(-1, 3), radius


def dense(counts, points):
    """The strands read every DENSE_M: (places, the strand each is on)."""
    counts = np.asarray(counts, np.int64)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    steps[(starts + counts - 1)[:-1]] = 0.0  # no step from one strand's last point to the next one's root
    along = np.concatenate([[0.0], np.cumsum(steps)])  # length along every strand, run on through the next
    base, total = along[starts], along[starts + counts - 1] - along[starts]
    wanted = np.floor(total / DENSE_M + 1e-9).astype(np.int64) + 1
    owner = np.repeat(np.arange(len(counts)), wanted)
    at = base[owner] + (np.arange(len(owner)) - np.repeat(np.cumsum(wanted) - wanted, wanted)) * DENSE_M
    segment = np.clip(np.searchsorted(along, at, side="right") - 1, starts[owner], starts[owner] + counts[owner] - 2)
    share = np.clip((at - along[segment]) / np.maximum(steps[segment], 1e-12), 0.0, 1.0)
    return points[segment] + (points[segment + 1] - points[segment]) * share[:, None], owner


def before_eyes(places, eyes):
    """Which places are in the box before the eyes (EYE_BOX)."""
    eyes = np.asarray(eyes, float)
    middle = eyes.mean(axis=0)
    return ((places[:, 0] > eyes[:, 0].min() - EYE_BOX["beside_m"])
            & (places[:, 0] < eyes[:, 0].max() + EYE_BOX["beside_m"])
            & (places[:, 1] < middle[1] + EYE_BOX["over_m"]) & (places[:, 1] > middle[1] - EYE_BOX["under_m"])
            & (places[:, 2] > middle[2] - EYE_BOX["behind_m"]))


def clump_ratio(places, owner):
    """The most strands in one CLUMP_CELL_M cell over the 99th percentile of the cells holding hair."""
    cells = np.floor(places / CLUMP_CELL_M).astype(np.int64)
    cells -= cells.min(axis=0)
    span = cells.max(axis=0) + 1
    cell = (cells[:, 0] * span[1] + cells[:, 1]) * span[2] + cells[:, 2]  # one number a cell, so unique runs on 1-D
    strands_in = np.unique(cell * (int(owner.max()) + 1) + owner) // (int(owner.max()) + 1)
    _, per_cell = np.unique(strands_in, return_counts=True)
    return float(per_cell.max() / np.percentile(per_cell, 99))


def view_basis(view):
    """The camera's way into the scene for a view (degrees tilted off straight down, towards the side at degrees round
    the head from its front) and two directions across the picture: (way, across, up)."""
    tilt, side = np.radians(view)
    way = np.array([-np.sin(tilt) * np.sin(side), -np.cos(tilt), -np.sin(tilt) * np.cos(side)])
    across = unit(np.cross(way, [0.0, 0.0, 1.0] if abs(way[2]) < 0.9 else [1.0, 0.0, 0.0]))
    return way, across, np.cross(across, way)


def scalp_samples(skin_points, skin_faces, eyes):
    """The full-density scalp (TOP_READ over_m over the hairline) read four times a TOP_READ pixel: (places, their
    smooth outward normals)."""
    scalp = skin_faces[scalp_mask(skin_points, skin_faces, eyes, -TOP_READ["over_m"])]
    corners = skin_points[scalp]
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1).sum() / 2.0
    count = int(area / (TOP_READ["pixel_m"] / 2.0) ** 2)
    places, picked, weights = on_triangles(skin_points, scalp, count, np.random.default_rng(SEED + 6))
    normals = np.asarray(trimesh.Trimesh(skin_points, skin_faces, process=False).vertex_normals)
    return places, unit(np.einsum("pc,pcd->pd", weights, normals[scalp[picked]]))


def scalp_seen(samples, way, across, up):
    """The scalp's `samples` facing the camera (TOP_READ facing) seen along `way`, drawn into a picture of TOP_READ
    pixel_m pixels: (each pixel's scalp depth along `way`, inf where no scalp is seen; the scalp place each pixel
    shows; the pixel grid's origin)."""
    places = samples[0][samples[1] @ -way > TOP_READ["facing"]]
    flat = np.stack([places @ across, places @ up], axis=1)
    origin = flat.min(axis=0) - TOP_READ["pixel_m"]
    size = np.ceil((flat.max(axis=0) + TOP_READ["pixel_m"] - origin) / TOP_READ["pixel_m"]).astype(np.int64) + 1
    pixel = np.floor((flat - origin) / TOP_READ["pixel_m"]).astype(np.int64)
    index = pixel[:, 0] * size[1] + pixel[:, 1]
    depth = places @ way
    order = np.lexsort((depth, index))
    first = order[np.r_[True, index[order][1:] != index[order][:-1]]]
    grid = np.full(size[0] * size[1], np.inf)
    grid[index[first]] = depth[first]
    shows = np.full((size[0] * size[1], 3), np.nan)
    shows[index[first]] = places[first]
    return grid.reshape(size), shows.reshape(*size, 3), origin


def near_segments(counts, points, samples):
    """The strand segments (each by its first point) whose both ends lie within TOP_READ near_m of the scalp: the
    hair that can lie over it."""
    counts = np.asarray(counts, np.int64)
    last = np.zeros(len(points), dtype=bool)
    last[np.cumsum(counts) - 1] = True
    near = np.isfinite(cKDTree(samples[0][::16]).query(points, distance_upper_bound=TOP_READ["near_m"],
                                                       workers=-1)[0])
    return np.flatnonzero(~last & near & np.roll(near, -1))


def pieces_of(chunk, points, radius):
    """The strand segments `chunk` (each by its first point) read every TOP_READ step_m: (each piece's middle, its
    area seen square on: its width times its length)."""
    begin, end = points[chunk], points[chunk + 1]
    length = np.linalg.norm(end - begin, axis=1)
    pieces = np.maximum(np.ceil(length / TOP_READ["step_m"]).astype(np.int64), 1)
    owner = np.repeat(np.arange(len(chunk)), pieces)
    share = (np.arange(len(owner)) - np.repeat(np.cumsum(pieces) - pieces, pieces) + 0.5) / pieces[owner]
    place = begin[owner] + (end - begin)[owner] * share[:, None]
    return place, (2.0 * np.maximum(radius[chunk], radius[chunk + 1]) * length / pieces)[owner]


def covered_by(place, area, view, depth, origin):
    """How much of each pixel of one view's scalp picture (`depth`, `origin`) the pieces in front of the scalp cover,
    in pixel areas."""
    way, across, up = view
    cell = np.floor((np.stack([place @ across, place @ up], axis=1) - origin) / TOP_READ["pixel_m"]).astype(np.int64)
    inside = (cell >= 0).all(axis=1) & (cell[:, 0] < depth.shape[0]) & (cell[:, 1] < depth.shape[1])
    index = cell[inside, 0] * depth.shape[1] + cell[inside, 1]
    front = (place[inside] @ way) < depth.reshape(-1)[index]
    return np.bincount(index[front], weights=area[inside][front], minlength=depth.size) / TOP_READ["pixel_m"] ** 2


def hair_cover(first, points, radius, views, pictures):
    """How much of the scalp shows through each pixel of each view's picture (`views`: way, across, up; `pictures`:
    depth, origin): the strand segments `first` read every TOP_READ step_m (`pieces_of`, read once for every view),
    each piece in front of the scalp adding its area over the pixel's; the scalp shows through a pixel as exp(-that)
    (fibres laid at random): each picture's transmittance."""
    covered = [np.zeros(depth.size) for depth, _ in pictures]
    for chunk in np.array_split(first, max(1, len(first) // TOP_READ["segments"])):
        place, area = pieces_of(chunk, points, radius)
        for total, view, (depth, origin) in zip(covered, views, pictures):
            total += covered_by(place, area, view, depth, origin)
    return [np.exp(-total).reshape(depth.shape) for total, (depth, _) in zip(covered, pictures)]


def top_bare(counts, points, radius, skin_points, skin_faces, eyes, style):
    """The hair rendered from above (each of TOP_VIEWS, the scalp's picture and the hair's cover over it), and the
    scalp seen bare through it away from the parting's own line and the whorl's middle: (the most of the seen scalp
    shown bare in one view, as a share; the largest bare patch in one view, m2). A pixel is bare when more than
    TOP_READ bare of the scalp shows through it."""
    from scipy import ndimage
    line, whorl = parting_line(skin_points, skin_faces, eyes, style)
    samples = scalp_samples(skin_points, skin_faces, eyes)
    views = [view_basis(view) for view in TOP_VIEWS]
    seen_from = [scalp_seen(samples, *view) for view in views]
    shown = hair_cover(near_segments(counts, points, samples), points, radius, views,
                       [(depth, origin) for depth, _, origin in seen_from])
    share, patch = 0.0, 0.0
    for (depth, shows, _), through in zip(seen_from, shown):
        seen = np.isfinite(depth)
        bare = seen & (through > TOP_READ["bare"])
        places = shows[bare]
        excused = ((cKDTree(line).query(places)[0] < TOP_READ["part_half_m"])
                   | (np.linalg.norm(places - whorl, axis=1) < TOP_READ["whorl_m"]))
        bare[tuple(np.argwhere(bare)[excused].T)] = False
        share = max(share, float(bare.sum() / max(seen.sum(), 1)))
        labels, found = ndimage.label(bare)
        if found:
            patch = max(patch, float(np.bincount(labels.ravel())[1:].max()) * TOP_READ["pixel_m"] ** 2)
    return share, patch


def root_gap(roots_at, skin_points, skin_faces, eyes):
    """The farthest any place on the scalp past the soft hairline (HAIRLINE_RAMP_M over it, where the roots are at
    their full density) lies from its nearest root (m)."""
    scalp = skin_faces[scalp_mask(skin_points, skin_faces, eyes, -HAIRLINE_RAMP_M)]
    samples = on_triangles(skin_points, scalp, COVER_SAMPLES, np.random.default_rng(SEED + 3))[0]
    return float(cKDTree(roots_at).query(samples)[0].max())


def hairline_soft(roots_at, skin_points, skin_faces, eyes):
    """Over how much (m) the forehead's root density, per area of skin, rises from a tenth to nine tenths of the
    hair's full density (HAIRLINE_READ: the forehead within front_deg of the face's front, read in band_m bands of
    height over the hairline, full from full_from_m over it): a hard hairline rises within one band."""
    _, centre, _ = head_frame(skin_points, eyes)
    head = skin_faces[(skin_points[skin_faces][..., 1] > np.asarray(eyes, float).mean(axis=0)[1]).all(axis=1)]
    skin = on_triangles(skin_points, head, HAIRLINE_READ["skin"], np.random.default_rng(SEED + 4))[0]
    bands = np.arange(HAIRLINE_READ["from_m"], HAIRLINE_READ["to_m"] + 1e-9, HAIRLINE_READ["band_m"])

    def per_band(places):
        front = around(places, centre)[0] < HAIRLINE_READ["front_deg"]
        return np.histogram(over_hairline(places[front], eyes, centre), bins=bands)[0].astype(float)

    density = per_band(roots_at) / np.maximum(per_band(skin), 1.0)
    full = density[bands[:-1] >= HAIRLINE_READ["full_from_m"]].mean()
    middles = bands[:-1] + HAIRLINE_READ["band_m"] / 2.0
    low = middles[np.argmax(density >= 0.1 * full)]
    high = middles[np.argmax(density >= 0.9 * full)]
    return float(max(high - low, 0.0) + HAIRLINE_READ["band_m"])


def cut_spread(counts, points, eyes):
    """How unevenly the hanging strands end (m, one sigma): each end's height off the median of the CUT_NEAR ends
    nearest it seen from above (CUT_READ of them), for the strands ending OUTLINE_READ's under_eyes_m under the eyes or
    lower (a blunt cut ends every strand of a place at one height, "hard flat cut line", 2026-11-25)."""
    ends = points[np.cumsum(counts) - 1]
    ends = ends[ends[:, 1] < np.asarray(eyes, float).mean(axis=0)[1] - OUTLINE_READ["under_eyes_m"]]
    if len(ends) < 10:
        return 0.0
    read = ends[::max(1, len(ends) // CUT_READ)]
    near = cKDTree(ends[:, [0, 2]]).query(read[:, [0, 2]], k=min(CUT_NEAR, len(ends)), workers=-1)[1]
    return float(np.std(read[:, 1] - np.median(ends[near, 1], axis=1)))


def outline_step(points, skin_points, eyes):
    """The most the hair's outline seen from behind bends out going down (m): on each side, the hair's reach off the
    head's middle (OUTLINE_READ's share of its points, a stray hair aside) in each band_m band from the top of the
    head to under_eyes_m under the eyes, and how much more it steps out from one band to the next than from the one
    before: over a round head the steps only shrink; hair laid round the ears stepped out again under the crown's
    curve, a ledge ("earmuffs" seen from behind, 2026-11-26)."""
    middle, centre, top = head_frame(skin_points, eyes)
    bands = np.arange(top, middle[1] - OUTLINE_READ["under_eyes_m"], -OUTLINE_READ["band_m"])
    held = [(points[:, 1] <= high) & (points[:, 1] > high - OUTLINE_READ["band_m"]) for high in bands]
    held = [band for band in held if band.sum() >= OUTLINE_READ["fewest"]]
    worst = 0.0
    for sign in (-1.0, 1.0):
        off = (points[:, 0] - centre[0]) * sign
        steps = np.diff([np.percentile(off[band], OUTLINE_READ["share"] * 100.0) for band in held])
        worst = max(worst, float(np.max(np.diff(steps), initial=0.0)))
    return worst


def farthest_off(mesh, places):
    """The distances off the skin `mesh` of the places that may be the farthest: a place's nearest skin point lies on a
    triangle whose corners are all within the longest edge of it, so its distance is at least
    sqrt(corner^2 - edge^2) and at most `corner` (its nearest corner's); only places whose `corner` reaches the
    largest such floor are read. The farthest is exactly whole.closest's, read on a few places instead of millions."""
    from tools.characters import whole
    corner = cKDTree(mesh.vertices).query(places, workers=-1)[0]
    edge = float(mesh.edges_unique_length.max())
    floor = np.sqrt(np.maximum(corner ** 2 - edge ** 2, 0.0)).max()
    return whole.closest(mesh, places[corner >= floor])[1]


def top_found(counts, points, radius, skin_points, skin_faces, eyes, style):
    """`top_bare`'s two numbers as the measures name them."""
    share, patch = top_bare(counts, points, radius, skin_points, skin_faces, eyes, style)
    return {"scalp bare from above share": round(share, 4), "largest bare patch from above mm2": round(patch * 1e6, 1)}


def roots_found(counts, points, skin_points, skin_faces, eyes):
    """The roots read off the scalp (the soft hairline's band and over)."""
    from tools.characters import whole
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    scalp = trimesh.Trimesh(skin_points, skin_faces[scalp_mask(skin_points, skin_faces, eyes, BABY_BAND_M)],
                            process=False)
    off = whole.closest(scalp, points[starts])[1]
    return {"roots off the scalp": int((off > ROOT_OFF_M).sum()),
            "root farthest off the scalp mm": round(float(off.max()) * 1000.0, 2)}


def dense_found(counts, points, skin_points, skin_faces, eyes):
    """The strands read every DENSE_M: before the eyes, in clumps, standing off the skin over the eyes."""
    places, owner = dense(counts, points)
    middle = np.asarray(eyes, float).mean(axis=0)
    high = places[places[:, 1] > middle[1]]
    stand = farthest_off(trimesh.Trimesh(skin_points, skin_faces, process=False), high) if len(high) else np.zeros(1)
    return {"points before the eyes": int(before_eyes(places, eyes).sum()),
            "clump ratio": round(clump_ratio(places, owner), 2),
            "farthest off the skin over the eyes mm": round(float(stand.max()) * 1000.0, 1)}


# Each part of `measured`, by name: a function of (counts, points, radius, skin points, skin faces, eyes, style).
MEASURES = {
    "roots": lambda counts, points, radius, skin, faces, eyes, style: roots_found(counts, points, skin, faces, eyes),
    "dense": lambda counts, points, radius, skin, faces, eyes, style: dense_found(counts, points, skin, faces, eyes),
    "top": top_found,
    "gap": lambda counts, points, radius, skin, faces, eyes, style: {
        "scalp farthest from a root mm": round(root_gap(points[np.cumsum(counts) - counts], skin, faces, eyes)
                                               * 1000.0, 2)},
    "hairline": lambda counts, points, radius, skin, faces, eyes, style: {
        "hairline soft over mm": round(hairline_soft(points[np.cumsum(counts) - counts], skin, faces, eyes)
                                       * 1000.0, 1)},
    "thickness": lambda counts, points, radius, skin, faces, eyes, style: {
        "thickest strand um": round(float(np.max(radius)) * 2.0e6, 1)},
    "cut": lambda counts, points, radius, skin, faces, eyes, style: {
        "cut spread mm": round(cut_spread(counts, points, eyes) * 1000.0, 1)},
    "outline": lambda counts, points, radius, skin, faces, eyes, style: {
        "outline step mm": round(outline_step(points, skin, eyes) * 1000.0, 1)},
}


def measured(counts, points, skin_points, skin_faces, eyes, style, radius, parts=tuple(MEASURES)):
    """The groom read on its head at the build's bind (the checks the module docstring names; `parts` of MEASURES
    only, when given)."""
    counts = np.asarray(counts, np.int64)
    found = {"strands": int(len(counts))}
    for part in parts:
        found.update(MEASURES[part](counts, points, radius, skin_points, skin_faces, eyes, style))
    return found


def faults(found):
    """What is past its limit, one line each."""
    lines = []
    if found["roots off the scalp"]:
        lines.append(f"hair: {found['roots off the scalp']} roots off the scalp (limit 0, {ROOT_OFF_M * 1000:.0f} mm)")
    if found["points before the eyes"]:
        lines.append(f"hair: {found['points before the eyes']} strand points in front of the eyes (limit 0)")
    if found["scalp bare from above share"] > TOP_BARE_LIMIT:
        lines.append(f"hair: {found['scalp bare from above share']:.1%} of the scalp seen bare from above (limit "
                     f"{TOP_BARE_LIMIT:.1%})")
    if found["largest bare patch from above mm2"] > TOP_PATCH_LIMIT_M2 * 1e6:
        lines.append(f"hair: a bare patch of {found['largest bare patch from above mm2']:.0f} mm2 seen from above "
                     f"(limit {TOP_PATCH_LIMIT_M2 * 1e6:.0f})")
    if found["clump ratio"] > CLUMP_LIMIT:
        lines.append(f"hair: a clump of {found['clump ratio']:.1f} times the dense hair's strands (limit "
                     f"{CLUMP_LIMIT:.1f})")
    if found["farthest off the skin over the eyes mm"] > STRAY_M * 1000.0:
        lines.append(f"hair: a strand standing {found['farthest off the skin over the eyes mm']:.0f} mm off the head "
                     f"(limit {STRAY_M * 1000.0:.0f})")
    if found["scalp farthest from a root mm"] > ROOT_GAP_M * 1000.0:
        lines.append(f"hair: a gap in the roots, scalp {found['scalp farthest from a root mm']:.1f} mm from a root "
                     f"(limit {ROOT_GAP_M * 1000.0:.1f})")
    if found["hairline soft over mm"] < HAIRLINE_SOFT_LIMIT_M * 1000.0:
        lines.append(f"hair: a hard hairline, the roots thinning out over {found['hairline soft over mm']:.0f} mm "
                     f"(limit at least {HAIRLINE_SOFT_LIMIT_M * 1000.0:.0f})")
    if found["thickest strand um"] > HAIR_RADIUS_LIMIT_M * 2.0e6:
        lines.append(f"hair: a strand {found['thickest strand um']:.0f} um across, thicker than a hair (limit "
                     f"{HAIR_RADIUS_LIMIT_M * 2.0e6:.0f})")
    if found["cut spread mm"] < CUT_SPREAD_LIMIT_M * 1000.0:
        lines.append(f"hair: a blunt cut line, the ends spread {found['cut spread mm']:.1f} mm (limit at least "
                     f"{CUT_SPREAD_LIMIT_M * 1000.0:.0f})")
    if found["outline step mm"] > OUTLINE_STEP_LIMIT_M * 1000.0:
        lines.append(f"hair: a ledge in the outline beside the head, {found['outline step mm']:.0f} mm out (limit "
                     f"{OUTLINE_STEP_LIMIT_M * 1000.0:.0f})")
    return lines
