"""A person standing or walking at ease (#223): the clip's feet under the hips, the arms hanging and the gaze level,
and the check that fails a clip that stands otherwise. numpy and scipy only.

Kimodo's standing and walking clips (people-clips-made) hold a person as a mannequin stands (owner, 2026-11-25, round 6:
"the posture head and pants are so weird"): played on woman_stair's build, the standing clip's ankles 0.38 m apart
on 0.20 m hips, the upper arms 13 to 17 degrees out from the sides (the hands 0.25 m out from the middle of the hips),
and the head tipped back 2 to 8 degrees from the bind (walking 4 to 14); the face's own rest (its eyes looking 4.6
degrees up as ICT's face sits on SOMA's head) put the drawn gaze 11 degrees up standing and 15 walking. No library
clip or commercially usable motion dataset is retargeted onto the clips rig yet, so the clips are kept and only what
is wrong in them is moved, each by one fixed turn for the whole clip (a clip's own sway, swing and nods are kept),
in the people route's way of bringing Kimodo's wide feet in (`tools/characters/people/stance.py`):

- `relaxed`: the feet brought in to the hips' width (`stance.narrowed`); each upper arm turned in towards the side
  about the body's forward line, its median over the clip to ARM_HANG_DEGREES out or, where the body that plays it
  is in the way (`hung`, `clearance`: on woman_stair's own skin her hands met her thighs at 12 degrees), the least
  angle above it that clears, its forearm turned out at the elbow first; the head turned down about
  the body's left-right line, half at the neck's base and half at the head, until its highest gaze over the clip is
  GAZE_TOP_DEGREES up (so a walk's nods look a little down, as people walking look at the ground ahead);
- `measured` and `faults`: the upper arms' angle out from the sides and the gaze's angle above level on every frame;
  a clip with an arm's median past ARM_MOST_DEGREES or the gaze past GAZE_UP_MOST_DEGREES on any frame is faulted;
- the hands at rest (`finger_joints`, `hand_rested`, `hand_faults`), the wrists, the arms' reach and a walk's swing,
  heels and knees (`clip_faults`): each block below says what it reads and why.

The angles are choices read off people at rest, not a study's: a relaxed arm hangs a few degrees out so the elbow
clears the hip, and a walk swings it a little further; a person at ease looks ahead, not up. Measured on woman_stair
(2026-11-25): standing arms 10 and 10 degrees (median), gaze at most 2 up; walking arms 8 and 10, gaze at most 2 up,
her ankles 0.21 m apart standing.
"""
import numpy as np

# The clips whose sentence asks nothing of the arms or the head (people/clips.py): the ones made to stand at ease.
RELAXED = ("standing", "walking")
ARM_HANG_DEGREES = 6.0  # an upper arm's median angle out from the side, at ease, where the body lets it
ARM_HANG_STEP = 2.0  # degrees between the angles tried
FOREARM_STEPS = np.arange(0.0, 16.0, 4.0)  # the forearm's turns out at the elbow tried, degrees (a carrying angle)
# The shoulder's turns forward tried where the forearm's are not enough, degrees: on woman_stair's walk with her hands
# at rest the right upper arm's top sank into the side of her chest at 12 degrees out (22 skin points past the
# played clip's 11 on its worst frame, 2026-11-26), and 4 degrees forward cleared it; a walk carries the shoulders a
# few degrees forward and back with the arms' swing.
SHOULDER_STEPS = (0.0, 2.0, 4.0)
# An upper arm whose median over the clip is further out than this is held out, not hanging (its median: a walk's
# swing takes it further out for a few frames).
ARM_MOST_DEGREES = 12.0
GAZE_TOP_DEGREES = 2.0  # the highest a relaxed clip's gaze is brought to above level
GAZE_UP_MOST_DEGREES = 5.0  # a gaze higher than this on any frame looks up into the sky
SIDES = (("Left", 1.0), ("Right", -1.0))
BODY_BESIDE_ARMS = ("Hips", "Spine1", "Spine2", "Chest", "LeftLeg", "RightLeg")  # what a hanging arm lies against
LOOKED_EVERY = 10  # clip frames between those an arm's clearance is looked at
SUNK_SPARE = 10  # skin points an arm brought to rest on the body may sink past the played clip's worst
UP = np.array([0.0, 1.0, 0.0])


def locals_of(world, parents):
    """Transforms against the parents (frames x joints x 4 x 4) of world transforms."""
    found = np.array(world, dtype=float)
    for joint, parent in enumerate(parents):
        if parent >= 0:
            found[:, joint] = np.linalg.inv(world[:, parent]) @ world[:, joint]
    return found


def facing(world, names):
    """Each frame's unit line from the right hip to the left on the floor, and the body's forward on the floor."""
    across = world[:, names.index("LeftLeg"), :3, 3] - world[:, names.index("RightLeg"), :3, 3]
    across[:, 1] = 0.0
    across /= np.linalg.norm(across, axis=1, keepdims=True)
    return across, np.cross(across, UP)


def arms_out(world, names):
    """Each upper arm's angle out from the side on every frame, degrees (the ForeArm joint off the Arm joint, against
    the hips' line): {side: frames}."""
    across, _ = facing(world, names)
    found = {}
    for side, sign in SIDES:
        bone = world[:, names.index(f"{side}ForeArm"), :3, 3] - world[:, names.index(f"{side}Arm"), :3, 3]
        bone /= np.linalg.norm(bone, axis=1, keepdims=True)
        found[side] = np.degrees(np.arcsin(np.clip(sign * np.einsum("fd,fd->f", bone, across), -1.0, 1.0)))
    return found


def gaze_up(world, names, bind, gaze):
    """The gaze's angle above level on every frame, degrees: `gaze` (the eyes' look at the bind, world) carried by
    the Head joint's turn off the bind's."""
    head = names.index("Head")
    turns = world[:, head, :3, :3] @ np.asarray(bind, dtype=float)[head, :3, :3].T
    looks = turns @ (np.asarray(gaze, dtype=float) / np.linalg.norm(gaze))
    return np.degrees(np.arcsin(np.clip(looks[:, 1], -1.0, 1.0)))


def turned(local, parents, joint, axes, degrees):
    """`local` with `joint` turned `degrees` about the world line `axes` (one a frame), its place kept."""
    from scipy.spatial.transform import Rotation
    from tools.characters import played
    world = played.chained(local, parents)
    parent_turn = world[:, parents[joint], :3, :3]
    turn = Rotation.from_rotvec(axes * np.radians(degrees)).as_matrix()
    found = np.array(local, dtype=float)
    found[:, joint, :3, :3] = np.transpose(parent_turn, (0, 2, 1)) @ turn @ parent_turn @ found[:, joint, :3, :3]
    return found


def hung(local, parents, names, forward, clears):
    """`local` with each upper arm turned in towards its side to the least angle out, from ARM_HANG_DEGREES up to
    where it is, at which the arm still `clears` the body (a callable taking a clip and the side): its forearm turned
    out at the elbow by the least of FOREARM_STEPS that lets it (the elbow's carrying angle: the hand kept off the
    thigh) and, where that is not enough, its shoulder brought forward by the least of SHOULDER_STEPS (the arm's top
    off the side of the chest)."""
    from tools.characters import played
    upright = np.tile(UP, (len(local), 1))
    for side, sign in SIDES:
        tries = []
        for shoulder in SHOULDER_STEPS:
            forth = turned(local, parents, names.index(f"{side}Shoulder"), upright, -sign * shoulder)
            now = float(np.median(arms_out(played.chained(forth, parents), names)[side]))
            tries.append((forth, now))
        start = tries[0][1]
        for hang in np.arange(min(ARM_HANG_DEGREES, start), start + 1e-9, ARM_HANG_STEP):
            cleared = None
            for forth, now in tries:
                arm = turned(forth, parents, names.index(f"{side}Arm"), forward, -sign * max(0.0, now - hang))
                tried = (turned(arm, parents, names.index(f"{side}ForeArm"), forward, sign * out)
                         for out in FOREARM_STEPS)
                cleared = next((clip for clip in tried if clears(clip, side)), None)
                if cleared is not None:
                    break
            if cleared is not None:
                local = cleared
                break
    return local


def clearance(skin, names, parents, bind, played_clip):
    """The test `hung` puts an arm to (`clears(clip, side)`): a clip clears the body on that side when no looked-at
    frame (every LOOKED_EVERY'th) sinks more of that arm's skin past the armpit's fold in the torso or the thighs than
    the played clip's worst frame does, give or take SUNK_SPARE points (a hanging hand already touches the thigh as
    Kimodo made it). `skin` the body's {points, faces, weights} at `bind`."""
    from score.stages.people_cloth import skinned
    from tools.characters import played
    from tools.characters.garments import shaped
    names = [str(name) for name in names]
    points, faces, weights = (np.asarray(skin[key]) for key in ("points", "faces", "weights"))
    strongest = weights.argmax(axis=1)
    body = np.isin(strongest, [names.index(name) for name in BODY_BESIDE_ARMS])
    joints = np.tile(np.arange(weights.shape[1]), (len(weights), 1))
    arms = {}
    for side, _ in SIDES:
        mine = np.isin(strongest, [index for index, name in enumerate(names) if name.startswith(side) and
                                   ("Arm" in name or name.endswith("Hand"))])
        arms[side] = shaped.past_armpits(bind, points, mine, names)

    def counts(clip, side):
        """Each looked-at frame's sunk points of the `side` arm, one at a time (`all` stops at the first past)."""
        for world in played.chained(clip[::LOOKED_EVERY], parents):
            yield shaped.sunk(skinned(points, joints, weights, world[None], bind)[0], faces, arms[side], body)
    most = {side: max(counts(played_clip, side)) + SUNK_SPARE for side, _ in SIDES}
    return lambda clip, side: all(count <= most[side] for count in counts(clip, side))


def relaxed(local, parents, names, bind, gaze, clears):
    """A clip (frames x joints x 4 x 4 against the parents) standing at ease: its feet under the hips, its upper arms
    hanging as close to the sides as `clears` lets them (`hung`), its gaze level (the module's header says how)."""
    from tools.characters import played
    from tools.characters.people import stance
    names = [str(name) for name in names]
    local = locals_of(stance.narrowed(played.chained(local, parents), names, parents), parents)
    world = played.chained(local, parents)
    across, forward = facing(world, names)
    local = hung(local, parents, names, forward, clears)
    excess = float(gaze_up(world, names, bind, gaze).max()) - GAZE_TOP_DEGREES
    if excess > 0.0:
        for joint in ("Neck1", "Head"):
            local = turned(local, parents, names.index(joint), across, excess / 2.0)
    return local


def measured(local, parents, names, bind, gaze):
    """A clip's posture: each upper arm's most and median angle out from the side and the gaze's highest and median
    angle above level, degrees."""
    from tools.characters import played
    names = [str(name) for name in names]
    world = played.chained(local, parents)
    arms = arms_out(world, names)
    looks = gaze_up(world, names, bind, gaze)
    return {"arms out degrees": {side: {"most": round(float(arms[side].max()), 1),
                                        "median": round(float(np.median(arms[side])), 1)} for side, _ in SIDES},
            "gaze up degrees": {"most": round(float(looks.max()), 1), "median": round(float(np.median(looks)), 1)}}


def faults(measures):
    """What is wrong with a relaxed clip's posture (`measured`): an arm held out, a gaze up into the sky."""
    found = [f"the {side.lower()} upper arm is held {values['median']} degrees out from the side over the clip (most "
             f"{ARM_MOST_DEGREES})" for side, values in measures["arms out degrees"].items()
             if values["median"] > ARM_MOST_DEGREES]
    if measures["gaze up degrees"]["most"] > GAZE_UP_MOST_DEGREES:
        found.append(f"the gaze is {measures['gaze up degrees']['most']} degrees up (most {GAZE_UP_MOST_DEGREES})")
    return found


def rest_gaze(face):
    """The face's look at its rest (face.npz: its corneas' middle off its eyeballs'), a unit line; with no face, the
    body's forward at the bind (+z)."""
    if face is None:
        return np.array([0.0, 0.0, 1.0])
    look = np.asarray(face["cornea.points"], float).mean(axis=0) - np.asarray(face["eyes.points"], float).mean(axis=0)
    return look / np.linalg.norm(look)


# A hand hanging at rest (owner, 2026-11-25: "stiff splayed fingers", a thumb standing out). SOMA's skeleton has each
# finger's joints (body_face.py writes their places: `<side>Hand<finger><1..4>`, `End`; the thumb 1..3, `End`), MHR's
# rest holds them straight and spread, the thumb out from the palm. Each finger is bent at its knuckle (2), middle (3)
# and end (4) joints, each a little more than the one on its thumb side (the resting cascade of a relaxed hand: a
# choice read off hands at rest, not one study's numbers), turned in towards the middle finger at the knuckle, and the
# thumb bent at its two joints and turned at its base to lie along the index finger's side.
FINGERS = ("Index", "Middle", "Ring", "Pinky")
# Each finger's bend at rest from its palm bone to its end bone, degrees, the bend it lacks shared out over its
# knuckle, middle and end joints by FINGER_BEND_SHARES.
FINGER_BEND_DEGREES = {"Index": 55.0, "Middle": 65.0, "Ring": 75.0, "Pinky": 85.0}
FINGER_BEND_SHARES = (0.35, 0.45, 0.2)
BEND_TRIES = 4
# Each finger's first bone's angle off the middle finger's across the palm, at rest (towards the thumb positive).
FINGER_SPREAD_DEGREES = {"Index": 4.0, "Middle": 0.0, "Ring": -4.0, "Pinky": -9.0}
THUMB_BEND_DEGREES = (15.0, 15.0)  # at the thumb's joints 2 and 3
# The thumb's tip laid this far out from the index finger's middle bone, towards the thumb's side and the palm's, m.
THUMB_REST_OFF_M = (0.012, 0.008)
THUMB_TURN_MOST_DEGREES = 60.0  # the most the thumb's base is turned to lay it there
BONE_BLEND_M = 0.002  # a hand point is carried by the bones within about this much of its nearest one
# The hand checks: a thumb's tip further than this from the index finger's bones stands out from the hand; two
# neighbouring fingers further apart than this across the palm are spread; a finger bent less than this from its
# palm bone to its tip is held straight and stiff.
THUMB_GAP_MOST_M = 0.03
FINGER_SPREAD_MOST_DEGREES = 10.0
FINGER_BEND_LEAST_DEGREES = 30.0


# The fingers read off the skin's own hand (SOMA's finger joints as body_face.py writes them are the template's, not
# this body's: its hand lies 8 cm off them, 2026-11-26): the hand's points by their distance over the skin from the
# wrist (`over_skin`), each finger the points past the web it parts from the hand at (`fingers_of`), its bones laid
# along its middle line (`finger_joints`) from a knuckle FINGER_ROOT_SHARE of its web-to-tip length back into the
# palm, its joints at the shares of its knuckle-to-tip length a finger's bones take (index: proximal 39.8, middle 22.4
# and distal 15.8 mm with the pad, Buryanov and Kotiuk 2010's means) and the thumb's (proximal 0.55).
FINGER_ROOT_SHARE = 0.2
FINGER_JOINT_SHARES = (0.47, 0.75)  # the middle and end joints along a finger from its knuckle to its tip
THUMB_JOINT_SHARE = 0.55  # the thumb's end joint along it from its knuckle to its tip
THUMB_ROOT_SHARE = 0.1
PALM_BONE_SHARE = 0.4  # a finger's palm bone's base (and the thumb's root joint) this far from the wrist to its knuckle
FINGER_LEAST_POINTS = 40  # a branch of fewer points is a bump, not a finger
LEVEL_M = 0.002  # the middle line read in steps of this much distance over the skin


def over_skin(points, faces, mask):
    """Each of the `mask` points' distance over the skin (along its triangles' edges) from the nearest point of the
    mask's border with the rest (the wrist), m: an array over the mask's points."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    local = np.full(len(points), -1)
    local[mask] = np.arange(mask.sum())
    inside = faces[mask[faces].all(axis=1)]
    border = np.unique(faces[mask[faces].any(axis=1) & ~mask[faces].all(axis=1)])
    border = local[border[mask[border]]]
    pairs = np.concatenate([inside[:, [0, 1]], inside[:, [1, 2]], inside[:, [2, 0]]])
    lengths = np.linalg.norm(points[pairs[:, 0]] - points[pairs[:, 1]], axis=1)
    graph = coo_matrix((lengths, (local[pairs[:, 0]], local[pairs[:, 1]])), shape=(mask.sum(),) * 2).tocsr()
    return dijkstra(graph, directed=False, indices=border, min_only=True)


def fingers_of(distance, pairs):
    """Each point's finger (a number; -1 the palm) and each finger's web (the distance over the skin it parts from
    the hand at): the points taken from the farthest in, a branch growing from each tip until it meets another
    branch of FINGER_LEAST_POINTS points (a finger and the hand, or two fingers, at a web), past which it is the palm;
    a smaller branch met (a bump) joins the one it meets."""
    neighbours = [[] for _ in distance]
    for one, two in pairs:
        neighbours[one].append(two)
        neighbours[two].append(one)
    root = np.full(len(distance), -1)
    members, open_, webs = {}, {}, {}

    def found(point):
        while root[point] != point:
            root[point] = root[root[point]]
            point = root[point]
        return point
    for point in np.argsort(-distance):
        met = {found(other) for other in neighbours[point] if root[other] >= 0}
        root[point] = point
        members[point], open_[point] = [point], True
        if not met:
            continue
        big = [branch for branch in met if len(members[branch]) >= FINGER_LEAST_POINTS]
        if len(big) > 1:
            for branch in big:
                if open_[branch]:
                    webs[branch] = (float(distance[point]), list(members[branch]))
                    open_[branch] = False
        elder = max(met, key=lambda branch: len(members[branch]))
        for branch in list(met) + [point]:
            if branch != elder:
                root[branch] = elder
                members[elder] += members.pop(branch)
        open_[elder] = open_[elder] and len(big) <= 1
    numbered = np.full(len(distance), -1)
    found_webs = []
    for web, points in sorted(webs.values(), key=lambda item: -len(item[1])):
        numbered[points] = len(found_webs)
        found_webs.append(web)
    return numbered, np.array(found_webs)


def middle_line(points, distance):
    """A finger's middle line, from its web to its tip: the mean point of each LEVEL_M step of distance over the
    skin."""
    steps = np.floor((distance - distance.min()) / LEVEL_M).astype(int)
    return np.array([points[steps == step].mean(axis=0) for step in np.unique(steps)])


def laid_along(line, base, shares):
    """The places `shares` of the way along the line from `base` (put before the line's first point) to its last
    point."""
    line = np.concatenate([base[None], line])
    run = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(line, axis=0), axis=1))])
    return np.array([[np.interp(share * run[-1], run, line[:, axis]) for axis in range(3)] for share in shares])


def finger_joints(points, faces, mask, wrist, side):
    """A hand's joints ({name: place}, the names SOMA's skeleton has: `<side>Hand`, `<side>Hand<finger><1..4>` and
    `End`, the thumb's 1..3 and `End`) read off its skin (the module's header above `over_skin`): `mask` its points,
    `wrist` its hand joint's place."""
    local = np.flatnonzero(mask)
    distance = over_skin(points, faces, mask)
    position = np.full(len(points), -1)
    position[local] = np.arange(len(local))
    inside = position[faces[mask[faces].all(axis=1)]]
    pairs = np.concatenate([inside[:, [0, 1]], inside[:, [1, 2]], inside[:, [2, 0]]])
    labels, webs = fingers_of(distance, pairs)
    if len(webs) != 5:
        raise ValueError(f"the {side.lower()} hand's skin parts into {len(webs)} fingers, not five")
    hand = points[local]
    lines = [middle_line(hand[labels == finger], distance[labels == finger]) for finger in range(5)]
    thumb = int(np.argmin(webs))
    others = [finger for finger in range(5) if finger != thumb]
    others.sort(key=lambda finger: np.linalg.norm(lines[finger][0] - lines[thumb][0]))
    joints = {f"{side}Hand": np.asarray(wrist, float)}
    for name, finger in zip(("Thumb",) + FINGERS, [thumb] + others):
        line = lines[finger]
        reach = np.linalg.norm(line[-1] - line[0])
        towards = line[min(len(line) - 1, max(2, len(line) // 3))] - line[0]
        towards /= np.linalg.norm(towards)
        root_share = THUMB_ROOT_SHARE if name == "Thumb" else FINGER_ROOT_SHARE
        knuckle = line[0] - towards * root_share * reach
        shares = (THUMB_JOINT_SHARE, 1.0) if name == "Thumb" else FINGER_JOINT_SHARES + (1.0,)
        laid = laid_along(line, knuckle, shares)
        base = joints[f"{side}Hand"] + PALM_BONE_SHARE * (knuckle - joints[f"{side}Hand"])
        chain = finger_chain(side, name)
        joints[chain[1]] = base
        for joint, place in zip(chain[2:], [knuckle] + list(laid)):
            joints[joint] = place
    return joints


def finger_chain(side, finger):
    """A finger's joints from the wrist out: the hand joint, the finger's joints and its end's."""
    count = 3 if finger == "Thumb" else 4
    return [f"{side}Hand"] + [f"{side}Hand{finger}{number}" for number in range(1, count + 1)] + \
        [f"{side}Hand{finger}End"]


def palm_frame(joints, side):
    """A hand's wrist-to-knuckles line, its thumb's side across it and its palm's side (unit lines) from its joints'
    places ({name: place}): the palm's side by the hand's handedness, so it holds in any pose."""
    wrist = joints[f"{side}Hand"]
    knuckles = np.array([joints[f"{side}Hand{finger}2"] for finger in FINGERS])
    along = knuckles.mean(axis=0) - wrist
    along /= np.linalg.norm(along)
    thumb_side = knuckles[0] - knuckles[-1]
    thumb_side -= along * (thumb_side @ along)
    thumb_side /= np.linalg.norm(thumb_side)
    return along, thumb_side, (1.0 if side == "Left" else -1.0) * np.cross(along, thumb_side)


def about(pivot, axis, degrees):
    """The 4 x 4 turn of `degrees` about the line through `pivot` along `axis`."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3] = Rotation.from_rotvec(axis / np.linalg.norm(axis) * np.radians(degrees)).as_matrix()
    found[:3, 3] = pivot - found[:3, :3] @ pivot
    return found


def bone_distances(points, starts, ends):
    """Each point's distance to each bone (the segment from its start to its end): points x bones."""
    span = ends - starts
    along = np.einsum("pbd,bd->pb", points[:, None] - starts[None], span) / np.einsum("bd,bd->b", span, span)
    nearest = starts[None] + np.clip(along, 0.0, 1.0)[..., None] * span[None]
    return np.linalg.norm(points[:, None] - nearest, axis=2)


def finger_bend(joints, chain, palm):
    """A finger's bend from its palm bone to its end bone, degrees, towards the `palm` side positive (`chain` its
    joints' names, `finger_chain`)."""
    palm_bone = joints[chain[2]] - joints[chain[1]]
    end_bone = joints[chain[5]] - joints[chain[4]]
    palm_bone, end_bone = palm_bone / np.linalg.norm(palm_bone), end_bone / np.linalg.norm(end_bone)
    bend = float(np.degrees(np.arccos(np.clip(palm_bone @ end_bone, -1.0, 1.0))))
    return bend if end_bone @ palm >= palm_bone @ palm else -bend


def chains_posed(joints, side):
    """Each finger's bones' moves (4 x 4, a bone the segment from one of its chain's joints to the next) laying the
    hand at rest (the module's hand header), and the joints' places so laid: ({finger: [moves]}, {name: place})."""
    placed = dict(joints)
    moves = {}
    along, thumb_side, palm = palm_frame(joints, side)
    middle = placed[f"{side}HandMiddle3"] - placed[f"{side}HandMiddle2"]
    middle -= palm * (middle @ palm)
    middle /= np.linalg.norm(middle)
    towards_thumb = np.cross(palm, middle) * (1.0 if np.cross(palm, middle) @ thumb_side > 0.0 else -1.0)
    for finger in FINGERS + ("Thumb",):
        chain = finger_chain(side, finger)
        bones = [np.eye(4) for _ in chain[:-1]]

        def turn(joint, move):
            """Every bone and joint past `joint` (its index in the chain) moved by `move`."""
            for index in range(joint, len(bones)):
                bones[index] = move @ bones[index]
            for name in chain[joint + 1:]:
                placed[name] = move[:3, :3] @ placed[name] + move[:3, 3]
        if finger != "Thumb":
            first = placed[chain[3]] - placed[chain[2]]
            spread = np.degrees(np.arctan2(first @ towards_thumb, first @ middle))
            turn(2, about(placed[chain[2]], np.cross(middle, towards_thumb), FINGER_SPREAD_DEGREES[finger] - spread))
            first = placed[chain[3]] - placed[chain[2]]
            bend_axis = np.cross(first / np.linalg.norm(first), palm)
            for _ in range(BEND_TRIES):  # a bend partly across the bend's own line reaches less than it turns
                lacking = max(0.0, FINGER_BEND_DEGREES[finger] - finger_bend(placed, chain, palm))
                for joint, share in zip((2, 3, 4), FINGER_BEND_SHARES):
                    turn(joint, about(placed[chain[joint]], bend_axis, lacking * share))
        else:
            index_side = placed[f"{side}HandIndex2"] - placed[chain[2]]
            bone = placed[chain[3]] - placed[chain[2]]
            bend_axis = np.cross(bone, index_side - bone * (index_side @ bone) / (bone @ bone))
            for joint, degrees in zip((2, 3), THUMB_BEND_DEGREES):
                turn(joint, about(placed[chain[joint]], bend_axis, degrees))
            index_middle = (placed[f"{side}HandIndex3"] + placed[f"{side}HandIndex4"]) / 2.0
            target = index_middle + THUMB_REST_OFF_M[0] * thumb_side + THUMB_REST_OFF_M[1] * palm
            base = placed[chain[1]]
            now, then = placed[chain[-1]] - base, target - base
            axis = np.cross(now, then)
            degrees = min(np.degrees(np.arctan2(np.linalg.norm(axis), now @ then)), THUMB_TURN_MOST_DEGREES)
            if np.linalg.norm(axis) > 1e-9:
                turn(1, about(base, axis, degrees))
        moves[finger] = bones
    return moves, placed


def hand_rested(points, joints, side):
    """A hand's skin points (all carried by its hand joint) laid at rest: each point moved by the bones of its
    fingers (`chains_posed`) within BONE_BLEND_M of its nearest one, blended by how near; and the joints so laid."""
    moves, placed = chains_posed(joints, side)
    starts, ends, bone_moves = [], [], []
    for finger in FINGERS + ("Thumb",):
        chain = finger_chain(side, finger)
        for index, move in enumerate(moves[finger]):
            starts.append(joints[chain[index]])
            ends.append(joints[chain[index + 1]])
            bone_moves.append(move)
    distances = bone_distances(points, np.array(starts), np.array(ends))
    shares = np.exp(-(distances - distances.min(axis=1, keepdims=True)) / BONE_BLEND_M)
    shares /= shares.sum(axis=1, keepdims=True)
    bone_moves = np.array(bone_moves)
    each = np.einsum("bij,pj->pbi", bone_moves[:, :3, :3], points) + bone_moves[None, :, :3, 3]
    return np.einsum("pb,pbi->pi", shares, each), placed


def hand_measured(joints, side):
    """A hand's rest, from its joints' places: its thumb's tip off the index finger's bones (m), each pair of
    neighbouring fingers' angle apart across the palm and each finger's bend from its palm bone to its tip
    (degrees)."""
    _, _, palm = palm_frame(joints, side)
    index = [joints[name] for name in finger_chain(side, "Index")[2:]]
    tip = joints[f"{side}HandThumbEnd"][None]
    gap = float(bone_distances(tip, np.array(index[:-1]), np.array(index[1:])).min())
    firsts = []
    for finger in FINGERS:
        first = joints[f"{side}Hand{finger}3"] - joints[f"{side}Hand{finger}2"]
        first -= palm * (first @ palm)
        firsts.append(first / np.linalg.norm(first))
    spread = [round(float(np.degrees(np.arccos(np.clip(one @ two, -1.0, 1.0)))), 1)
              for one, two in zip(firsts, firsts[1:])]
    bends = {finger: round(finger_bend(joints, finger_chain(side, finger), palm), 1) for finger in FINGERS}
    return {"thumb gap m": round(gap, 4), "spread degrees": spread, "bend degrees": bends}


def hand_faults(measures, side):
    """What is wrong with a hand at rest (`hand_measured`): a thumb standing out, fingers spread, a finger straight."""
    found = []
    if measures["thumb gap m"] > THUMB_GAP_MOST_M:
        found.append(f"the {side.lower()} thumb's tip stands {measures['thumb gap m']} m off the index finger "
                     f"(most {THUMB_GAP_MOST_M})")
    found += [f"the {side.lower()} {one.lower()} and {two.lower()} fingers are spread {angle} degrees (most "
              f"{FINGER_SPREAD_MOST_DEGREES})" for one, two, angle in zip(FINGERS, FINGERS[1:],
                                                                          measures["spread degrees"])
              if angle > FINGER_SPREAD_MOST_DEGREES]
    found += [f"the {side.lower()} {finger.lower()} finger is held straight, bent {bend} degrees (least "
              f"{FINGER_BEND_LEAST_DEGREES})" for finger, bend in measures["bend degrees"].items()
              if bend < FINGER_BEND_LEAST_DEGREES]
    return found


# The wrist, the walk and the arm's reach. Measured on woman_stair's relaxed clips with her hands read off her skin
# (2026-11-26): the wrist's ulnar turn 4 to 6 degrees (median), its bend towards the palm 0 to 12; the walk's arms
# swinging 33 degrees, against the leg on their side, the heel first (the foot 13 to 19 degrees toes up as it lands)
# and the knee bent 66 to 68 degrees at most; standing, the elbow at 0.617 of her height and the wrist at 0.468.
WRIST_ULNAR_MOST_DEGREES = 15.0  # a hanging wrist turned further to the little finger's side hooks the hand out
WRIST_BEND_DEGREES = (-15.0, 30.0)  # a hanging wrist's bend towards the palm (back negative), its median, at ease
# A walk's arms: the upper arm's swing forward and back over the walk, degrees, and how much it swings against the
# leg on its side (the correlation of the two; a walk swings each arm with the other leg).
ARM_SWING_DEGREES = (20.0, 60.0)
ARM_AGAINST_LEG_MOST = -0.5
HEEL_STRIKE_LEAST_DEGREES = 5.0  # the foot's most toes up over its flat stance: a walk lands on the heel
KNEE_SWING_DEGREES = (50.0, 75.0)  # the knee's most bend over a walk (its swing)
# Standing at ease, the elbow's and wrist's joint heights over the person's height: ANSUR II's women's and men's
# radiale and stylion heights (about 0.63 and 0.48 of stature), each give or take about 2.5 standard deviations.
ELBOW_HEIGHT_SHARE = (0.58, 0.68)
WRIST_HEIGHT_SHARE = (0.43, 0.53)


def wrist_measured(world, names, bind, hands):
    """Each wrist's ulnar turn and bend towards the palm on every frame, degrees: the hand's wrist-to-knuckles line
    and palm (`palm_frame` of `hands`, the hands' joints at the bind) carried by the Hand joint's turn, against the
    forearm's line. {side: {"ulnar": frames, "bend": frames}}."""
    found = {}
    for side, _ in SIDES:
        hand, forearm = names.index(f"{side}Hand"), names.index(f"{side}ForeArm")
        along, thumb_side, palm = palm_frame(hands, side)
        turns = world[:, hand, :3, :3] @ np.asarray(bind, float)[hand, :3, :3].T
        fore = world[:, hand, :3, 3] - world[:, forearm, :3, 3]
        fore /= np.linalg.norm(fore, axis=1, keepdims=True)
        straight = np.einsum("fd,fd->f", fore, turns @ along)
        found[side] = {"ulnar": np.degrees(np.arctan2(np.einsum("fd,fd->f", fore, turns @ thumb_side), straight)),
                       "bend": np.degrees(np.arctan2(-np.einsum("fd,fd->f", fore, turns @ palm), straight))}
    return found


def wrist_faults(world, names, bind, hands):
    """What is wrong with a relaxed clip's wrists: a hand hooked out to the little finger's side, or bent back or
    in, over the clip (medians)."""
    found = []
    for side, wrist in wrist_measured(world, names, bind, hands).items():
        ulnar, bend = float(np.median(wrist["ulnar"])), float(np.median(wrist["bend"]))
        if abs(ulnar) > WRIST_ULNAR_MOST_DEGREES:
            found.append(f"the {side.lower()} wrist is turned {ulnar:.1f} degrees to the side (most "
                         f"{WRIST_ULNAR_MOST_DEGREES})")
        if not WRIST_BEND_DEGREES[0] <= bend <= WRIST_BEND_DEGREES[1]:
            found.append(f"the {side.lower()} wrist is bent {bend:.1f} degrees (from {WRIST_BEND_DEGREES[0]} to "
                         f"{WRIST_BEND_DEGREES[1]})")
    return found


def forward_angle(bone, forward):
    """A bone's (frames x 3, from its joint down) angle forward of straight down, degrees."""
    return np.degrees(np.arctan2(np.einsum("fd,fd->f", bone, forward), -bone[:, 1]))


def walk_measured(world, names):
    """A walk's arms, heels and knees: each upper arm's swing (degrees) and its correlation with its own side's
    thigh's swing, each foot's most toes up over its flat stance and each knee's most bend (degrees)."""
    _, forward = facing(world, names)
    joint = {name: world[:, names.index(name), :3, 3] for name in names}
    found = {}
    for side, _ in SIDES:
        arm = forward_angle(joint[f"{side}ForeArm"] - joint[f"{side}Arm"], forward)
        thigh = forward_angle(joint[f"{side}Shin"] - joint[f"{side}Leg"], forward)
        foot = joint[f"{side}ToeBase"] - joint[f"{side}Foot"]
        pitch = np.degrees(np.arctan2(foot[:, 1], np.linalg.norm(foot[:, [0, 2]], axis=1)))
        flat = float(np.median(pitch[joint[f"{side}Foot"][:, 1] <= np.percentile(joint[f"{side}Foot"][:, 1], 20)]))
        upper, lower = joint[f"{side}Leg"] - joint[f"{side}Shin"], joint[f"{side}Foot"] - joint[f"{side}Shin"]
        knee = 180.0 - np.degrees(np.arccos(np.clip(np.einsum("fd,fd->f", upper, lower) / np.linalg.norm(
            upper, axis=1) / np.linalg.norm(lower, axis=1), -1.0, 1.0)))
        found[side] = {"arm swing": round(float(np.ptp(arm)), 1),
                       "arm with leg": round(float(np.corrcoef(arm, thigh)[0, 1]), 2),
                       "heel up": round(float(pitch.max() - flat), 1), "knee most": round(float(knee.max()), 1)}
    return found


def walk_faults(measures):
    """What is wrong with a walk (`walk_measured`): arms held still or flung, swung with their own leg, landing flat
    or on the toes, legs stiff or high-stepping."""
    found = []
    for side, values in measures.items():
        side = side.lower()
        if not ARM_SWING_DEGREES[0] <= values["arm swing"] <= ARM_SWING_DEGREES[1]:
            found.append(f"the {side} arm swings {values['arm swing']} degrees (from {ARM_SWING_DEGREES[0]} to "
                         f"{ARM_SWING_DEGREES[1]})")
        if values["arm with leg"] > ARM_AGAINST_LEG_MOST:
            found.append(f"the {side} arm swings with its own leg (correlation {values['arm with leg']}, most "
                         f"{ARM_AGAINST_LEG_MOST})")
        if values["heel up"] < HEEL_STRIKE_LEAST_DEGREES:
            found.append(f"the {side} foot lands {values['heel up']} degrees toes up (least "
                         f"{HEEL_STRIKE_LEAST_DEGREES}): not on its heel")
        if not KNEE_SWING_DEGREES[0] <= values["knee most"] <= KNEE_SWING_DEGREES[1]:
            found.append(f"the {side} knee bends {values['knee most']} degrees at most (from {KNEE_SWING_DEGREES[0]} "
                         f"to {KNEE_SWING_DEGREES[1]})")
    return found


def reach_faults(world, names, height):
    """What is wrong with a person's arms standing at ease: an elbow or a wrist (their joints' median heights over
    `height`) higher or lower than people's."""
    found = []
    for side, _ in SIDES:
        for joint, (low, high) in ((f"{side}ForeArm", ELBOW_HEIGHT_SHARE), (f"{side}Hand", WRIST_HEIGHT_SHARE)):
            share = float(np.median(world[:, names.index(joint), 1, 3])) / height
            if not low <= share <= high:
                found.append(f"the {joint} joint stands at {share:.3f} of the height (from {low} to {high})")
    return found


def clip_faults(local, parents, names, bind, gaze, clip, height, hands=None):
    """Everything wrong with a relaxed clip as played (`faults`, `reach_faults`, `wrist_faults` when the `hands`'
    joints at the bind are known, `walk_faults` for the walk)."""
    from tools.characters import played
    names = [str(name) for name in names]
    world = played.chained(local, parents)
    found = faults(measured(local, parents, names, bind, gaze)) + reach_faults(world, names, height)
    if hands is not None:
        found += wrist_faults(world, names, bind, hands)
    if clip == "walking":
        found += walk_faults(walk_measured(world, names))
    return found
