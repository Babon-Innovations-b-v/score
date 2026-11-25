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
  a clip with an arm's median past ARM_MOST_DEGREES or the gaze past GAZE_UP_MOST_DEGREES on any frame is faulted.

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
    where it is, at which the arm still `clears` the body (a callable taking a clip and the side), its forearm turned out at the
    elbow by the least of FOREARM_STEPS that lets it (the elbow's carrying angle: the hand kept off the thigh)."""
    from tools.characters import played
    world = played.chained(local, parents)
    for side, sign in SIDES:
        now = float(np.median(arms_out(world, names)[side]))
        for hang in np.arange(min(ARM_HANG_DEGREES, now), now + 1e-9, ARM_HANG_STEP):
            arm = turned(local, parents, names.index(f"{side}Arm"), forward, -sign * (now - hang))
            tried = [turned(arm, parents, names.index(f"{side}ForeArm"), forward, sign * out) for out in FOREARM_STEPS]
            cleared = next((clip for clip in tried if clears(clip, side)), None)
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
