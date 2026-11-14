"""A film is made only as a locked film script shows it, within the forecast its yes was cleared at, and is gated on
what its frames show: only a place a locked script shows has the row, its cameras the script's or its scene record's,
its forecast prices fog and glass high before anything is bought, a film too short or too dear is refused before its
frames are rented, and its gate fails a silent, still, unpeopled or unsounded film by name. The environment's own film
is cut only from locked scripts, paced as the owner asked (about 7 s a place), at one loudness. No Blender, no spend:
stages and scripts made here, one small local ffmpeg cut.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/demo_film/test_a_film_shows_its_locked_script_within_its_forecast.py
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from pxr import Gf, Usd, UsdGeom, UsdMedia, UsdSkel, Vt  # noqa: E402

from score import checks, graph  # noqa: E402
from score.stages import demo_film  # noqa: E402
from score.stages.demo_film import final, needs, shots  # noqa: E402

SMALL = (64, 36)
# A stage with a plain-card puff emitter (fog), as tools/usd/effects.py writes one.
FOGGED = """#usda 1.0
(
    defaultPrim = "hall"
)
def Xform "hall"
{
    def Xform "Effects"
    {
        def Xform "pump_fog"
        {
            token score:effect:look = "puff"
            token score:effect:card = "plain"
        }
    }
}
"""
# A see-through pane and an opaque wall.
GLASSED = """#usda 1.0
(
    defaultPrim = "hall"
)
def Xform "hall"
{
    def Material "pane"
    {
        def Shader "surface"
        {
            uniform token info:id = "UsdPreviewSurface"
            float inputs:opacity = 0.3
        }
    }
    def Material "wall"
    {
        def Shader "surface"
        {
            uniform token info:id = "UsdPreviewSurface"
            float inputs:opacity = 1
        }
    }
}
"""
PLAIN = "#usda 1.0\ndef Xform \"hall\"\n{\n}\n"


# One locked script, its stages and its scans: the hall's own film walked 7 s from its record's first camera, its other
# film (porch) walked 7 s from the record's `back`, and the yard shown only as a 3 s hero still from its own `gate`.
TOUR = [{"cut": "walk-through", "shows": {"place": "hall"}, "sound": "place", "seconds": 7.0},
        {"cut": "walk-through", "shows": {"place": "hall", "film": "porch", "camera": "back"}, "sound": "place",
         "seconds": 7.0},
        {"cut": "hero-still", "shows": {"place": "yard", "camera": "gate"}, "sound": "bed", "seconds": 3.0}]
DOOR = {"name": "door", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1]}
BACK = {"name": "back", "eye": [5, 1.6, 5], "aim": [0, 1.6, 0]}
NO_SLOW = {"fog": 0, "volumes": 0, "glass": 0}


# --- the cases the one world is judged on ---------------------------------------------------------------------------

# A scene record's cameras: the second shot is the one standing furthest from the first (spot-3, 3.6 m off; spot-2 is
# 0.5 m), none looking up at a roof.
SPOTS = [{"name": "spot-1", "eye": [0, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
         {"name": "spot-2", "eye": [0.5, 1.6, 0], "aim": [1, 1, 0], "fov": 75},
         {"name": "spot-3", "eye": [3, 1.6, 2], "aim": [0, 1, 0], "fov": 75},
         {"name": "roof", "eye": [9, 1.6, 9], "aim": [9, 9, 9.5], "fov": 75}]
OUTSIDE = "/room/Places/tube/Outside"  # a joined tube's own outside ground, shown inside the room it joins
# (what the film names, the film, its cameras, the own spots it adds to the record's copy, its start, whether the
# tube's Outside is still on in the copy after it). A spot of its own (`eye`/`aim`, or `across` the floor from (-2, -1)
# to (2, 3): shares (0, 1) are (-2, 3), (1, 0) is (2, -1)) is added as a camera of its name; record cameras add nothing.
CAMERA_FILMS = [
    ("no camera: the record's first, then the furthest; its own start", {"place": "yard", "start": 6},
     ["spot-1", "spot-3"], {}, 6.0, True),
    ("its camera, then the furthest", {"camera": "spot-1"}, ["spot-1", "spot-3"], {}, 0.0, True),
    ("leaving the tube's Outside out", {"camera": "spot-1", "leave_out": [OUTSIDE]}, ["spot-1", "spot-3"], {}, 0.0,
     False),
    ("spots of its own: eye and aim, then across the floor",
     {"camera": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5],
      "then": {"camera": "corner", "across": {"eye": [0.0, 1.0], "aim": [1.0, 0.0]}, "fov": 90, "stand": True}},
     ["bed", "corner"], {"bed": {"name": "bed", "eye": [-1.5, 1.4, 0.5], "aim": [-4.5, 0.3, 3.5], "fov": 75},
                         "corner": {"name": "corner", "eye": [-2.0, 1.6, 3.0], "aim": [2.0, 1.2, -1.0], "fov": 90,
                                    "stand": True}}, 0.0, False),
    ("its camera, then the one it names", {"camera": "spot-2", "then": "spot-1"}, ["spot-2", "spot-1"], {}, 0.0,
     False)]

DOOR_PATH = "/hall/Objects/door"
# (the stage and film, where a person stands, whether the door has a sound of its own, the view's aim along z, its
# frames, people_seen: {shot: frames seeing a person} or None for nobody there, silent_moving). Looking north from the
# origin at 75 degrees, out to the 25 m reach (the owner's review of 2026-10-18: no people in any film, no event
# sounds).
SEEN = [
    ("nobody there, the door sliding silent in view", None, False, -10.0, range(4), None, {"shot0": [DOOR_PATH]}),
    ("someone 5 m ahead", (0, 1.6, -5), False, -10.0, range(4), {"shot0": 4}, {"shot0": [DOOR_PATH]}),
    ("someone 6 m ahead, standing low", (0, 0.5, -6), False, -10.0, range(4), {"shot0": 4}, {"shot0": [DOOR_PATH]}),
    ("someone 3 m ahead and a little low", (0, 1.0, -3), False, -10.0, range(4), {"shot0": 4},
     {"shot0": [DOOR_PATH]}),
    ("someone 5 m behind the camera", (0, 1.6, 5), False, -10.0, range(4), {"shot0": 0}, {"shot0": [DOOR_PATH]}),
    ("someone 9 m aside, outside the angle", (9, 1.6, -5), False, -10.0, range(4), {"shot0": 0},
     {"shot0": [DOOR_PATH]}),
    ("someone 40 m ahead, past the reach", (0, 1.6, -40), False, -10.0, range(4), {"shot0": 0},
     {"shot0": [DOOR_PATH]}),
    ("the door with a sound of its own", None, True, -10.0, range(4), None, {}),
    ("the door looked away from", None, False, 10.0, range(4), None, {}),
    ("one frame: nothing seen moving", None, False, -10.0, [0], None, {})]

LEADER_GAPPED = [{"row": "characters-layer", "check": "bodies", "objects": ["leader"]},
                 {"row": "likeness", "check": "outline", "objects": ["crowd"]}]  # an outline gap gives no body gap
# (the square's design: one speaker and a far crowd of `count`, rows read or not, the gaps accepted, the place asked,
# the people its film owes). A crowd SAM 3 could not part (no count) counts one at least; cockpit (2026-11-11): its
# officer and pilot, accepted gaps with no body of their look, failed its film only once its frames were bought.
CAST = [("a speaker and a far crowd of 10000", 10000, True, [], "square", 10001),
        ("a crowd SAM 3 could not part", None, True, [], "square", 2),
        ("a place with no rows", 10000, True, [], "hub", 0),
        ("no rows read", 10000, False, [], "square", 0),
        ("the speaker an accepted bodies gap", None, True, LEADER_GAPPED, "square", 1),
        ("speaker and crowd both bodies gaps", None, True,
         [{"row": "characters-layer", "check": "bodies", "objects": ["leader", "crowd"]}], "square", 0)]


def a_script(segments):
    return {"format": "score-film-script", "version": 1, "film": "toy", "size": [1280, 720], "rate": 24,
            "segments": segments}


WALKS = [{"cut": "title", "shows": {"world": "toy"}, "sound": "bed", "text": "Toy", "seconds": 2.0},
         {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "place", "text": "Alpha", "seconds": 7.0},
         {"cut": "walk-through", "shows": {"place": "beta"}, "sound": "place", "text": "Beta", "seconds": 7.0}]
CROWD_PEEL = {"cut": "body-peel", "shows": {"place": "square"}, "seconds": 5.0}
LAB_PEEL = {"cut": "body-peel", "shows": {"place": "lab"}, "seconds": 5.0}
# The peels a locked script asks: a body peel of alpha wide and a close-up of its walker, a place peel of beta.
PEELED = [{"cut": "body-peel", "shows": {"place": "alpha"}, "seconds": 5.0},
          {"cut": "body-peel", "shows": {"place": "alpha"}, "seconds": 4.0, "close": "walker"},
          {"cut": "place-peel", "shows": {"place": "beta"}, "seconds": 5.0}]
LAB_HANGAR = [{"cut": "walk-through", "shows": {"place": place}, "seconds": 7.0} for place in ("lab", "hangar")]
NO_ROW_YET = "every fault a cut no row makes yet"
NO_DESIGN_PEELED = ["the design of lab shows people and no layer peel shows them",
                    "the design of stairwell shows people and no layer peel shows them"]
CROWD_UNPLACED = "the cast of square is a crowd with no sim body and no place peel shows it"
# (the script, judged against the kept designs or alone, its plan faults, its pacing faults). A script is cut only
# when every segment names its seconds, is a cut a row makes, and a walk-through plays its place's own sound; one
# showing no film needs a bed. The owner's pacing (review of 2026-10-18): about 3.5 s a place was far too fast; about
# 7 s, two steady shots, summed over its walk-throughs. Every place whose design shows people is layer peeled (owner,
# 2026-10-27), every other designed place it walks through place peeled (owner, 2026-11-05: "every scene needs the
# peel"), and a crowd alone (no sim body) place peeled, never layer peeled.
SCRIPTS = [
    ("the toy's two walk-throughs", a_script(WALKS), False, [], []),
    ("an exploded cut and a walk-through at the bed",
     a_script([{"cut": "exploded", "shows": {"place": "alpha"}},
               {"cut": "walk-through", "shows": {"place": "alpha"}, "sound": "bed", "seconds": 7.0}]), False,
     ["segment 1 (exploded) names no seconds", "segment 1: no row makes exploded frames yet",
      "segment 2: a walk-through plays its place's own sound, not bed"], []),
    ("a title alone", a_script(WALKS[:1]), False, ["it shows no place's film and names no bed"], []),
    ("a title over a bed", dict(a_script(WALKS[:1]), bed="sound/hum"), False, [], []),
    ("places cut at 3.5 and 3 s", a_script([dict(WALKS[1], seconds=3.5), dict(WALKS[2], seconds=3.0)]), False, [],
     ["beta: a walk-through of 3 s, under 3.5 s", "alpha: on screen 3.5 s, under 7 s",
      "beta: on screen 3 s, under 7 s"]),
    ("two 3.5 s walk-throughs of one place", a_script([dict(WALKS[1], seconds=3.5), dict(WALKS[1], seconds=3.5)]),
     False, [], []),
    ("world1's own script, data/films/k9.json", json.loads((REPO / "data/films/k9.json").read_text()), False,
     NO_ROW_YET, []),
    ("the toy against the designs", a_script(WALKS), True, [*NO_DESIGN_PEELED, CROWD_UNPLACED], []),
    ("the crowd layer peeled", a_script([*WALKS, CROWD_PEEL]), True,
     [*NO_DESIGN_PEELED, "the cast of square is a crowd with no sim body and a layer peel shows it"], []),
    ("the crowd place peeled", a_script([*WALKS, dict(CROWD_PEEL, cut="place-peel")]), True, NO_DESIGN_PEELED, []),
    ("lab layer peeled", a_script([*WALKS, LAB_PEEL]), True, [NO_DESIGN_PEELED[1], CROWD_UNPLACED], []),
    ("lab and hangar walked, lab peeled", a_script([*LAB_HANGAR, LAB_PEEL]), True,
     [NO_DESIGN_PEELED[1], CROWD_UNPLACED, "hangar is walked through and no place peel shows it"], []),
    ("lab and hangar walked, lab layer and hangar place peeled",
     a_script([*LAB_HANGAR, LAB_PEEL, {"cut": "place-peel", "shows": {"place": "hangar"}, "seconds": 5.0}]), True,
     [NO_DESIGN_PEELED[1], CROWD_UNPLACED], []),
    ("body and place peels over a bed, one a close-up", dict(a_script(PEELED), bed="sound/hum"), False, [], [])]

# The cut (final.py): a title, a screen take the free preview records, the two walk-throughs, a body and a place peel
# and a hero still: 2 + 3 + 7 + 7 + 5 + 5 + 3 less six half-second transitions, 29 s.
TAKE = {"cut": "screen-take", "shows": {"page": "/"}, "sound": "bed", "seconds": 3.0}
CUT_PEELS = [{"cut": "body-peel", "shows": {"place": "alpha"}, "sound": "place", "seconds": 5.0,
              "captions": [{"from": 0.3, "to": 4.7, "line": "Alpha", "text": "clothed, bare mesh, sim body"}]},
             {"cut": "place-peel", "shows": {"place": "beta"}, "sound": "place", "seconds": 5.0}]
STILL = {"cut": "hero-still", "shows": {"place": "alpha"}, "sound": "bed", "text": "Alpha", "seconds": 3.0}

WALKER = {"doing": "walking"}
STREET = [dict(WALKER, name="ann"), {"name": "bo", "doing": "standing"}, dict(WALKER, name="cy"),
          dict(WALKER, name="di")]
# (the close-up's case, the cast, the scene-made clips, the walker it follows or `refused: <why>`): the walker whose
# clip crosses the most relief, the first on a tie; one walker needs no record, several do, none is refused.
CLOSE_WALKERS = [
    ("the most relief, the first of a tie", STREET,
     {"clips": [{"name": "ann", "relief": 0.02}, {"name": "cy", "relief": 0.31}, {"name": "di", "relief": 0.31}]},
     "cy"),
    ("one walker, no record", STREET[:2], None, "ann"),
    ("several walkers, no record", STREET, None, "refused: no scene-made clips"),
    ("no walker", STREET[1:2], None, "refused: no walker")]

# The fogged hall's planned frames as film_one deals them (wide SIZE[0], one frame code apart): (view, its eye, its aim,
# the blur its frame is drawn with: None, "open" (SHUTTER towards the next frame of its shot) or "streak" (shortened
# so nothing streaks further than MOST_STREAK of the width)). Half a frame open, never for a camera standing still, a
# shot's last frame, or across a cut.
FORWARD = [0, 1.6 - 0.04 * 0.4 / 5.016, 5 - 0.04 * 5 / 5.016]  # 4 cm along the line of sight, as walkway's walk
SIDEWAYS = [0.02, FORWARD[1], FORWARD[2] - 0.02]
BLUR_SHOT = [("shot0-000", [0, 1.6, 5], [0, 1.2, 0], None),  # standing still into the next frame
             ("shot0-001", [0, 1.6, 5], [0, 1.2, 0], "open"),  # a straight walk forward
             ("shot0-002", FORWARD, [0, 1.2, 0], "open"),  # a step aside
             ("shot0-003", SIDEWAYS, [0, 1.2, 0], "streak"),  # a fast turn
             ("shot0-004", SIDEWAYS, [0.6, 1.2, 0], None),  # its shot's last frame, the cut after it
             ("shot1-000", [3, 1.6, 3], [0, 1.2, 0], None)]

# A peel's shot of 120 frames: (frame, the pass shown, the pass coming, the share it has risen (low, high: exact when
# equal), how far the push arrows have faded in): clothed, mesh and sim body in thirds, each next rising over the
# wipe, the arrows in with the sim body's.
WIPES = [(0, 0, 0, (0.0, 0.0), 0.0), (40, 0, 1, (0.4, 0.6), 0.0), (60, 1, 1, (0.0, 0.0), 0.0),
         (80, 1, 2, (0.4, 0.6), (0.0, 1.0)), (119, 2, 2, (0.0, 0.0), 1.0)]
# (a shot's seconds, the record's rate and frames, its last frame or `refused: <why>`): never longer than the record.
SOURCE_FRAMES = [(5.0, 30.0, 150, 149), (5.5, 30.0, 150, "refused: outlasts")]
# (its clip, where its points go from the bind): the bare mesh is the rig's points carried by its clip and weights.
SKINS = [("still", [0.0, 0.0, 0.0]), ("step", [0.0, 0.0, 1.0])]


def test_a_film_shows_its_locked_script_within_its_forecast(tmp_path, monkeypatch, still_film, small_cut):
    """One world (a cockpit home holding TOUR locked, a fogged hall's stage, a yard's, a plain, a fogged and a glassed
    scan) driven through the rows' own entries.

    Which films: a place's films are its locked film scripts' (the lock his yes), never a record written per place:
    hall and yard have the row, keyed on the script and the people its design stands; porch is the hall's extra row's
    (demo-film-extra@hall), the yard and an unshown hub have none; each make films at the script's camera, and an extra
    row's output with no film folder fails its contract. A film a starter shows that no locked script shows waits on
    his lock (needs.py), its node named. The environment-film row reads only the locked scripts, so a lock and a
    changed lock each move the files part of its key.

    Within its forecast (#21): two shots of 4 s at 24 frames are 192 frames, one 96; the free scan finds a plain-card
    puff (fog) and a see-through pane, never the opaque wall, nor a prim the film leaves out, and leaves the stage's
    files alone; fog or glass is priced high at FOG_FRAME_MINUTES a frame (over 20 times its likely euros), a plain
    stage at FRAME_SPREAD over the measured frame time, its high the row's estimate. The runner clears the rows at their
    films' forecast high, the figure film_one refuses over (fault 2026-10-25: cleared at the row's EUR 3.50, a fogged
    film Blocked itself); a fogged film over a plain clearance is a new ask, and outside a cleared run nothing is
    compared. A film's record keeps the longest walk-through showing it, and a plan whose shots show less is refused
    before its frames are rented (fault 2026-10-25: a 3.5 s film Blocked the 7 s walk-through after everything was
    bought); a film shown only as a hero still keeps one shot. The frames ask cards only, planned at SIZE over the jobs
    the forecast sizes, no review frames, each job's deadline its frames at the forecast's high (the fogged hall's 3
    frames a job at 17 minutes plus 10 to set up, 61), each job drawing into a folder of its own (blender_cloud's
    shared_outputs) and drawn by film_frames, its first frame kept as concept.png. Each frame blurs by how fast its
    picture moves towards the next frame of its shot (BLUR_SHOT): half a frame open (180 degrees), shorter where the
    picture would streak further than MOST_STREAK of its width, none for a camera standing still or a shot's last
    frame, never across a cut.

    Break: score/stages/demo_film/__init__.py: `return films().get(place, {}).get("place") == place` -> `return True`
    Break: score/stages/demo_film/__init__.py: `found["people"] = ("{data}/people/rows.json",
        people_rows.place_part(place))` -> `pass`
    Break: score/stages/demo_film/__init__.py: `if film["place"] == place and name != place]` -> `if film["place"] ==
        place]`
    Break: score/stages/demo_film/needs.py: `for film in wanted(place, data) if film not in locked]` -> `for film in
        wanted(place, data)]`
    Break: score/stages/demo_film/final.py: `found[f"script {film}"] = "{dashboard}/" + f"{LOCKED}/{film}.json"` ->
        `pass`
    Break: score/stages/demo_film/__init__.py: `high = FOG_FRAME_MINUTES if any(slow.values()) else likely *
        FRAME_SPREAD` -> `high = likely * FRAME_SPREAD`
    Break: score/stages/demo_film/__init__.py: `if opacity and opacity.Get() is not None and float(opacity.Get()) <
        1.0:` -> `if opacity and opacity.Get() is not None:`
    Break: score/stages/demo_film/__init__.py: `shots = len(film_cameras(record, film)[:SHOTS])` -> `shots = SHOTS`
    Break: score/stages/demo_film/__init__.py: `if cleared is not None and planned["high_euros"] > cleared + 1e-6:` ->
        `if False:`
    Break: score/stages/demo_film/__init__.py: `round(sum(film["high_euros"] for film in planned), 2)` ->
        `round(sum(film["euros"] for film in planned), 2)`
    Break: score/stages/demo_film/__init__.py: `film["walk_seconds"] = max(film["walk_seconds"],
        float(segment.get("seconds") or 0.0))` -> `pass`
    Break: score/stages/demo_film/__init__.py: `if shown < film.get("walk_seconds", 0.0) - 1e-3:` -> `if False:`
    Break: score/stages/demo_film/__init__.py: `CLASSES = "gpu-24gb"` -> `CLASSES = "gpu-24gb,cpu-8c-32gb"`
    Break: score/stages/demo_film/__init__.py: `job["minutes"] = round(JOB_LEAD_MINUTES + frame_minutes * len(views))`
        -> `job["minutes"] = JOB_LEAD_MINUTES`
    Break: score/stages/demo_film/__init__.py: drop `own_folders(jobs)` in film_one
    Break: score/stages/demo_film/__init__.py: `return 0.0 if speed < STILL_PIXELS else round(min(SHUTTER, MOST_STREAK *
        wide / speed), 3)` -> `return 0.0 if speed < STILL_PIXELS else SHUTTER`
    Break: score/stages/demo_film/__init__.py: `(later if demo.shot_of(later) == demo.shot_of(view) else None)` ->
        `later`
    Break: score/stages/demo_film/__init__.py: `+ wide / 2.0 * abs(along) / distance)` -> `)` (a straight walk
        forward, 4 cm a frame as walkway's walk-through, unblurred)

    Its cameras (CAMERA_FILMS over one record): no camera named starts at the record's first, the second shot its
    `then` or the record camera furthest from the first; its own spots are added to the record's copy, record
    cameras add nothing; a record with none refuses. What it names to leave out is made inactive in its copy of the
    stage, nothing named leaves the tube's Outside on; it starts at its own `start`, else the stage's.

    Its gate: a still, silent film cut free fails `film` naming both, held to its planned 9 s (a 2 s title and two 4 s
    shots joined by half-second fades) and to the size its views planned (SMALL), never the row's default. What its
    frames see (SEEN, shots.py): a person in front within the angle and reach, a thing seen moving with no sound of its
    own; a design standing people its stage never got fails the gate and is refused before renting (CAST counts them,
    less an accepted bodies gap's). The environment film (SCRIPTS): nothing is cut before a lock, every plan fault and
    the owner's pacing named, the places a locked script shows its walk-throughs' and stills', a segment naming a film
    the extra row's, a peel node only where it can draw, every kept design the row's input.

    Break: score/stages/demo_film/__init__.py: `return record["views"][0]["name"]` -> `return
        record["views"][-1]["name"]`
    Break: score/stages/demo_film/__init__.py: `return max(others, key=lambda view:
        float(np.linalg.norm(np.subtract(view["eye"], first["eye"]))))` -> `return others[0]`
    Break: score/stages/demo_film/__init__.py: `flat = low + np.asarray(share, dtype=float) * (high - low)` -> `flat =
        np.asarray(share, dtype=float) * (high - low)`
    Break: score/stages/demo_film/__init__.py: `    stage.GetRootLayer().Save()` -> `    pass`
    Break: score/stages/demo_film/__init__.py: `return float(film.get("start", 0.0))` -> `return 0.0`
    Break: score/stages/demo_film/__init__.py: `return demo.TITLE_SECONDS + shots * (SECONDS - demo.FADE_SECONDS)` ->
        `return shots * SECONDS`
    Break: score/stages/demo_film/__init__.py: `size = tuple(planned.get("size", SIZE))` -> `size = SIZE`
    Break: score/stages/demo_film/__init__.py: `faults = [fault for _, _, _, found in measured.values() for fault in
        found]` -> `faults = []`
    Break: score/stages/demo_film/shots.py: `(np.linalg.norm(offsets, axis=1) <= reach)` -> `(np.linalg.norm(offsets,
        axis=1) <= 100 * reach)`
    Break: score/stages/demo_film/shots.py: `int(bool(len(middles)) and bool(in_view(view, middles).any()))` -> `1`
    Break: score/stages/demo_film/__init__.py: `elif seen is None and people:` -> `elif False:`
    Break: score/stages/demo_film/__init__.py: `((people_rows.crowd_count(crowd[1]) or 1) if crowd and crowd[0] not in
        gapped else 0)` -> `(1 if crowd else 0)`
    Break: score/stages/demo_film/__init__.py: cast_people's `if person["name"] not in gapped` dropped, or
        refuse_peopleless' `if people and shots.people_seen(...) is None:` -> `if False:`
    Break: score/stages/demo_film/shots.py: `quiet = [not sounded(prim) for prim in things]` -> `quiet = [True for prim
        in things]`
    Break: score/stages/demo_film/shots.py: `moving & in_view(view, now) & np.asarray(quiet)` -> `moving &
        np.asarray(quiet)`
    Break: score/stages/demo_film/final.py: `if not named:` -> `if False:`
    Break: score/stages/demo_film/final.py: `elif cut == WALK and segment.get("sound", "place") != "place":` -> `elif
        False:`
    Break: score/stages/demo_film/final.py: `for place, seconds in shown_for.items() if seconds < PLACE_SECONDS - 1e-6]`
        -> `for place, seconds in shown_for.items() if False]`
    Break: score/stages/demo_film/final.py: `for segment in walks if segment["seconds"] < SHOT_SECONDS]` -> `for segment
        in walks if False]`
    Break: score/stages/demo_film/final.py: `return f"{EXTRA}@{shows['place']}", shows["film"]` -> `return
        f"{OWN}@{shows['place']}", shows["film"]`
    Break: score/stages/demo_film/final.py: `if place not in peeled]` -> `if False]`
    Break: score/stages/demo_film/final.py: `sorted(unpeopled - placed)` -> `[]`
    Break: score/stages/demo_film/final.py: `if design_layers.has_layer(place, "people") and not crowd_only(place)]` ->
        `if not crowd_only(place)]`
    Break: score/stages/demo_film/final.py: `all("crowd" in fields` -> `any("crowd" in fields`
    Break: score/stages/demo_film/final.py: `for place in crowds if place in peeled or place not in placed]` ->
        `for place in crowds if False]`
    Break: score/stages/demo_film/peel_rows.py: `and not final.crowd_only(place)` -> `` (a crowd's layer peel a node)

    The cut (TAKE, CUT_PEELS, STILL): a lock with a recorded segment and no preview wants it, a preview of the very
    lock does not, one recorded from another script (the take now 4 s) wants it again and Blocks the cut by name; a
    peel the node does not hold Blocks by name; two place films at very different loudness, the take and the peels
    cut into one 29 s film, each segment from its own film, take or peel, exposure matched (a film at the middle
    keeps gain 1, a dark one brought up at most GAIN_RANGE's top), the whole at TARGET_LUFS passing; a card held
    still is planned, a walk-through held still is not; a place cut at 3.5 s fails. The close-up's walker
    (CLOSE_WALKERS) is the one crossing the most relief, by rule.

    The peels: rows only where a locked script peels a place, keyed on that script, its shots the script's (a close-up
    where a segment names one, the longest segment's seconds), and the environment's film names a peel as a cut a row
    makes. A shot is the record's own frames, refused when longer (SOURCE_FRAMES); it shows clothed, mesh and sim body
    in thirds, each next rising from the bottom over the wipe, the push arrows fading in with the sim body's (WIPES).
    The bare mesh is the rig's points carried by its clip and skin weights (SKINS); every body the ground pushes gets an
    arrow from its centre of pressure along its push, METRES_PER_NEWTON a newton (a seated pelvis as its feet, a sixth
    on the Moon), none for one barely touching, and a record written before its touches is refused; the arrows stand
    where the person stands, in the film's push colour; the ground is what is underfoot (level, below their heads). A
    person with no dressed body is left out where an accepted bodies gap names them (CAST's gaps; cockpit 2026-11-11,
    its officer and pilot), refused by name where none does. Its forecast prices each pass's frame as a measured film
    frame, a fogged stage's passes high, its high never under its cards' own time; the fogged hall's place peel is made
    from its finished stage, its frames dealt over the forecast's cards, each slice its own frames into its own folder,
    all joined, and judged on its film.

    Break: score/stages/demo_film/final.py: `for kind in ("black", "frozen"))` -> `for kind in ("black", "black"))`
        -> a still card fails the gate as frozen; or `            if not any(start - 1e-3` -> `            if True or not
        any(start - 1e-3` -> a still card's stretch is kept as a fault.
    Break: score/stages/demo_film/final.py: `gain = TARGET_LUFS - loudness` -> `gain = 0.0`
    Break: score/stages/demo_film/final.py: `return f"{segment['cut']}@{segment['shows']['place']}", "close" if
        segment.get("close") else "wide"` -> `return f"demo-film@{segment['shows']['place']}", "wide"`
    Break: score/stages/demo_film/final.py: `    if stale:` -> `    if False:`
    Break: score/stages/demo_film/final.py: `return round(min(GAIN_RANGE[1], max(GAIN_RANGE[0], (middle - 16.0) /
        max(luma - 16.0, 1.0))), 3)` -> `return 1.0`
    Break: score/stages/demo_film/final.py: `if recorded(script) and (made is None or stale_segments(script, made)):` ->
        `if recorded(script) and made is None:`
    Break: score/stages/demo_film/peel.py: `relief.get(name, -1.0)` -> `-relief.get(name, -1.0)`
    Break: score/stages/demo_film/peel.py: `@ np.linalg.inv(np.asarray(rig["bind"], dtype=float))` -> `` (in skinned)
    Break: score/stages/demo_film/peel.py: `arrows = pushes(frames, touching(frames))` ->
        `arrows = pushes(frames, [body for body in touching(frames) if body.startswith("calcn")])`
    Break: score/stages/demo_film/peel.py: `arrows[index, number] = [*centre, *(force * METRES_PER_NEWTON)]` ->
        `arrows[index, number] = [*centre, 0.0, np.linalg.norm(force) * METRES_PER_NEWTON, 0.0]`
    Break: score/stages/demo_film/peel.py: `begins = (len(PASSES) - 1) * third - wipe / 2` -> `begins = 0`
    Break: score/stages/demo_film/peel_rows.py: `if single["name"] in gapped: return None` -> `if False: return None`
    Break: score/stages/demo_film/peel.py: `if found[-1] >= record_frames:` -> `if False:`
    Break: score/stages/demo_film/peel.py: `edge = round(tall * (1 - share))` -> `edge = round(tall * share)`
    Break: score/stages/demo_film/peel.py: `edges = np.linspace(0, count, min(parts, count) + 1).round().astype(int)`
        -> `edges = np.array([0, count // parts])`
    Break: score/stages/demo_film/peel_rows.py: `high = sum(demo_film.FOG_FRAME_MINUTES if slowed else likely *
        demo_film.FRAME_SPREAD for slowed in slow_passes)` -> `high = likely * demo_film.FRAME_SPREAD`
    Break: score/stages/demo_film/peel_rows.py: `"high_euros": round(max(per_render * frames * high / likely, card_high *
        card_euros_a_minute()), 2),` -> `"high_euros": round(per_render * frames * high / likely, 2),`
    Break: score/stages/demo_film/peel_rows.py: `shot = CLOSE if cut == final.PEEL and segment.get("close") else
        WIDE` -> `shot = WIDE`
    Break: score/stages/demo_film/final.py: `MADE = (*WORDS, WALK, STILL, *RECORDED, *PEELS)` -> `MADE = (*WORDS,
        WALK, STILL, *RECORDED)`
    Break: score/stages/demo_film/peel.py: `return triangles[level & (lengths > 0) & (triangles[:, :, 2].max(axis=1)
        < top)]` -> `return triangles[level & (lengths > 0)]`"""
    from score import stages
    from score.store import Store
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import blender_cloud
    import provider
    demo, _ = demo_film.film_tools()
    home = tmp_path / "home"
    world = graph.Environment("world1", 0, {**stages.world1().roots, "dashboard": str(home)})
    runner = graph.Runner(stages.STAGES, world, Store.in_folder(tmp_path / "store"))
    row = runner.stages["environment-film"]
    locked_in(home, monkeypatch)
    assert not any(name.startswith("script ") for name in runner.file_keys(row, None)), "nothing locked, no script"
    locked_in(home, monkeypatch, ("tour", a_script(TOUR)))
    script = home / final.LOCKED / "tour.json"
    keyed = runner.file_keys(row, None)["script tour"]
    assert final.shown_places() == ["hall", "yard"]

    # which places have which rows, keyed on what
    assert demo_film.applies("hall") and demo_film.applies("yard")
    assert not demo_film.applies("porch") and not demo_film.applies("hub")
    assert demo_film.extras("hall") == ["porch"] and demo_film.applies_extra("hall")
    assert not demo_film.applies_extra("yard") and not demo_film.applies_extra("hub")
    found = demo_film.files("yard")
    assert found["script tour"] == "{dashboard}/films/locked/tour.json", found
    assert found["people"][0] == "{data}/people/rows.json", "the people its design stands (seen_faults)"
    assert not any(name.startswith("film ") for name in found), "no per-place film record"
    assert demo_film.extra_files("hall")["script tour"] == "{dashboard}/films/locked/tour.json"
    assert all((REPO / path).exists() for path in demo_film.TOOLS)
    assert "tool " + demo_film.FRAMES_SCRIPT in demo_film.common_files("launch")
    (tmp_path / "data/films").mkdir(parents=True)
    starter = [{"cut": "walk-through", "seconds": 4.0, "shows": {"place": place}} for place in ("alpha", "hall")]
    (tmp_path / "data/films/env.json").write_text(json.dumps({"segments": starter}))
    waiting = [(gap["id"], gap["node"]) for gap in needs.gaps("alpha", tmp_path / "data")]
    assert waiting == [("film:yes:alpha", "demo-film@alpha")], waiting
    assert needs.gaps("hall", tmp_path / "data") == [] and needs.gaps("gamma", tmp_path / "data") == []

    # each film's record holds the walk-through it must fill; a plan showing less is refused before renting
    filmed = demo_film.films()
    assert filmed["hall"]["final"] is True
    walks = {name: filmed[name]["walk_seconds"] for name in ("hall", "porch", "yard")}
    assert walks == {"hall": 7.0, "porch": 7.0, "yard": 0.0}, walks
    two, one = [{"camera": "a"}, {"camera": "b"}], [{"camera": "a"}]
    demo_film.refuse_short("hall", two, filmed["hall"])
    demo_film.refuse_short("yard", one, filmed["yard"])
    with pytest.raises(RuntimeError, match="wants 7 s") as refused:
        demo_film.refuse_short("hall", one, filmed["hall"])
    assert "3.50 s" in str(refused.value)

    # the free scan and the price it sets: (stage, what it finds slow, the high frame minutes)
    scans = {}
    for name, text, slow, high_minutes in (
            ("plain", PLAIN, NO_SLOW, demo.FRAME_MINUTES * demo_film.FRAME_SPREAD),
            ("fog", FOGGED, dict(NO_SLOW, fog=1), demo_film.FOG_FRAME_MINUTES),
            ("glass", GLASSED, dict(NO_SLOW, glass=1), demo_film.FOG_FRAME_MINUTES)):
        (tmp_path / f"{name}.usda").write_text(text)
        scans[name] = demo_film.forecast(tmp_path / f"{name}.usda", demo_film.SHOTS)
        assert scans[name]["frames"] == 192 and scans[name]["frame_minutes"] == demo.FRAME_MINUTES, name
        assert scans[name]["slow"] == slow, (name, scans[name]["slow"])
        assert scans[name]["high_frame_minutes"] == high_minutes, (name, scans[name])
    plain, fog = scans["plain"], scans["fog"]
    assert plain["euros"] == demo_film.LIKELY_EUROS and plain["high_euros"] == demo_film.EUROS
    assert fog["high_euros"] > 20 * fog["euros"] and fog["jobs"] == plain["jobs"] >= 1
    assert "1 fog" in demo_film.forecast_line(fog), demo_film.forecast_line(fog)
    demo_film.refuse_over_clearance("hall", plain, demo_film.EUROS)
    demo_film.refuse_over_clearance("hall", fog, None)
    with pytest.raises(graph.Blocked, match="a new ask"):
        demo_film.refuse_over_clearance("hall", fog, demo_film.EUROS)
    assert all(provider.cards(name) for name in demo_film.CLASSES.split(",")), "cards only: none in stock is a gap"

    # the fogged hall with one record camera: one shot, filmed as one batch over the forecast's cards
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "hall.usda").write_text(FOGGED)
    (stage / "scene.json").write_text(json.dumps({"views": [DOOR]}))
    assert demo_film.film_forecast(stage, {"place": "hall", "camera": "door"})["frames"] == 96
    planned, deadlines = [], []

    def plan(work, stages, given, jobs_each, size, ink, shots, seconds, start):
        planned.append((tuple(size), jobs_each))
        (work / "views").mkdir(parents=True, exist_ok=True)
        (work / "jobs").mkdir(parents=True, exist_ok=True)
        views = [{"name": name, "eye": eye, "aim": aim, "up": [0, 1, 0], "fov": 75, "frame": number}
                 for number, (name, eye, aim, _) in enumerate(BLUR_SHOT)]
        written = demo.film_jobs(work, "hall", stages / "hall/hall.usda", [], views, "look", 2, size, ink)
        (work / "views/hall.json").write_text(json.dumps({"size": list(size), "views": views, "moves": []}))
        return written

    def render(jobs, log_folder):
        asked = [json.loads(pathlib.Path(json.loads(path.read_text())["args"][1]).read_text()) for path in jobs]
        deadlines.extend(json.loads(path.read_text())["minutes"] for path in jobs)
        assert not any(view.get("review") for job in asked for view in job["views"])
        assert all(view["look_only"] for job in asked for view in job["views"])
        loaded = [json.loads(path.read_text()) for path in jobs]
        assert blender_cloud.shared_outputs(loaded) is None, blender_cloud.shared_outputs(loaded)
        assert all(job["script"] == demo_film.FRAMES_SCRIPT for job in loaded)
        blurs = {view["name"]: view.get("blur") for job in asked for view in job["views"]}
        wide = demo_film.SIZE[0]
        for (name, eye, aim, blur), later in zip(BLUR_SHOT, [*BLUR_SHOT[1:], None]):
            if blur is None:
                assert blurs[name] is None, (name, blurs[name])
                continue
            assert blurs[name]["eye"] == later[1] and blurs[name]["codes"] == 1, (name, blurs[name])
            speed = demo_film.picture_speed({"eye": eye, "aim": aim, "fov": 75}, {"eye": later[1], "aim": later[2]},
                                            wide)
            if blur == "open":
                assert blurs[name]["shutter"] == demo_film.SHUTTER, (name, blurs[name]["shutter"])
            else:
                assert abs(blurs[name]["shutter"] - demo_film.MOST_STREAK * wide / speed) < 1e-3 and speed > 40, \
                    (name, speed)
        for job, listing in zip(loaded, asked):
            frames = pathlib.Path(job["args"][2])
            frames.mkdir(parents=True)
            for view in listing["views"]:
                Image.new("RGB", tuple(listing["size"]), (90, 90, 90)).save(frames / f"{view['name']}-look.png")

    def cut(work, names):
        (work / "videos").mkdir()
        (work / "videos/hall.mp4").write_bytes(b"")

    monkeypatch.setattr(demo, "plan", plan)
    monkeypatch.setattr(demo, "cut", cut)
    monkeypatch.setattr(demo_film, "render", render)
    demo_film.film_one(stage, "hall", {"place": "hall", "camera": "door", "final": True}, tmp_path / "filmed",
                       tmp_path / "log")
    assert planned == [(demo_film.SIZE, demo_film.forecast(stage / "hall.usda", 1)["jobs"])], planned
    assert deadlines == [61, 61], deadlines
    assert Image.open(tmp_path / "filmed/concept.png").size == demo_film.SIZE

    # two record cameras: two shots; the clearance reserves the very forecast the make holds each film to
    record = {"views": [DOOR, BACK]}
    (stage / "scene.json").write_text(json.dumps(record))
    hall = demo_film.film_forecast(stage, {"place": "hall", "camera": "door"})
    assert hall["frames"] == 192 and hall["slow"]["fog"] == 1
    left = demo_film.film_forecast(stage, {"place": "hall", "camera": "door", "leave_out": ["/hall/Effects"]})
    assert left["slow"]["fog"] == 0
    assert json.loads((stage / "scene.json").read_text()) == record and (stage / "hall.usda").read_text() == FOGGED
    inputs = {"assembly": str(stage), "script tour": str(script)}
    own = stages.DEMO_FILM.forecast(inputs)
    own_planned = demo_film.film_forecast(stage, {"place": "hall"})
    assert own == {"euros": own_planned["high_euros"], "minutes": None, "high_minutes": None, "measured": 0}, own
    demo_film.refuse_over_clearance("hall", own_planned, own["euros"])
    extra = stages.DEMO_FILM_EXTRA.forecast(inputs)
    assert extra["euros"] == demo_film.film_forecast(stage, {"place": "hall", "camera": "back"})[
        "high_euros"] > demo_film.EUROS, extra

    # the rows' makes film each place's films at the script's camera
    made = []
    monkeypatch.setattr(demo_film, "film_one", lambda stage_folder, name, film, out, log, start, people=0:
                        made.append((name, film["camera"], start, out.name)))
    (tmp_path / "yard").mkdir()
    (tmp_path / "yard/yard.usda").write_text("#usda 1.0\n")
    demo_film.make({"assembly": tmp_path / "yard", "script tour": script}, tmp_path / "out", 0, {})
    demo_film.make_extra({"assembly": stage, "script tour": script}, tmp_path / "extra", 0, {})
    assert made == [("yard", "gate", 0.0, "out"), ("porch", "back", 0.0, "porch")], made
    assert demo_film.extra_faults(stage) == ["no film"]

    # a changed lock moves the environment film's key
    locked_in(home, monkeypatch, ("tour", a_script(TOUR[:2])))
    assert runner.file_keys(row, None)["script tour"] != keyed
    assert final.shown_places() == ["hall"]
    assert final.film_node(TOUR[1]) == ("demo-film-extra@hall", "porch") and final.film_node(TOUR[2]) == (
        "demo-film@yard", "")

    # each film's cameras over one scene record, its spots added to the record's copy only, what it leaves out made
    # inactive in its copy of the stage (kept by the films after it), its own start
    record_path = tmp_path / "cameras/scene.json"
    record_path.parent.mkdir()
    record_path.write_text(json.dumps({"views": SPOTS, "floor": [[-2, -1], [2, 3]]}))
    room = record_path.parent / "room.usda"
    made_room = Usd.Stage.CreateNew(str(room))
    UsdGeom.Xform.Define(made_room, OUTSIDE + "/near")
    made_room.GetRootLayer().Save()
    own = {}
    for name, film, cameras, added, start, outside_on in CAMERA_FILMS:
        assert demo_film.own_cameras(record_path, film) == cameras, (name, cameras)
        own.update(added)
        kept = {view["name"]: view for view in json.loads(record_path.read_text())["views"]}
        assert sorted(kept) == sorted([spot["name"] for spot in SPOTS] + [*own]), (name, sorted(kept))
        assert all(kept[camera] == view for camera, view in added.items()), (name, kept)
        assert demo_film.film_start(film) == start, name
        demo_film.leave_out(room, film)
        opened = Usd.Stage.Open(str(room), Usd.Stage.LoadAll)
        opened.Reload()
        assert opened.GetPrimAtPath(OUTSIDE).IsActive() == outside_on, name
    record_path.write_text(json.dumps({"views": []}))
    with pytest.raises(ValueError, match="no camera"):
        demo_film.own_cameras(record_path, {"place": "yard"})

    # the gate on a film cut free: a still colour, no sound, two shots planned at SMALL; it fails naming both, held
    # to its planned 9 s and the size its views planned, never the row's default
    assert demo_film.planned_seconds(2) == 9.0
    gated = tmp_path / "gated"
    (gated / "hall").mkdir(parents=True)
    shutil.copy(still_film, gated / "hall/film.mp4")
    (gated / "hall/views.json").write_text(json.dumps({"size": list(SMALL), "views": [], "moves": [{}, {}]}))
    (gated / "stage").mkdir()
    (gated / "stage/hall.usda").write_text("#usda 1.0\n")
    _, film_checks = demo_film.film_tools()
    monkeypatch.setattr(film_checks, "clearance_checks", lambda stage, views: ({}, []))
    verdict = demo_film.judge_film(gated / "hall", {"assembly": gated / "stage"}, {})
    found = " ".join(verdict.findings)
    assert verdict.answer == checks.FAIL and "no sound track" in found and "frozen" in found, found
    assert not any(fault.startswith(("size", "length")) for fault in verdict.findings), verdict.findings

    # what a film's frames see on a stage with a door sliding at z = -5: the people in view, the things seen moving
    # with no sound, the faults the gate names, and a film refused before renting when the design stands people the
    # stage never got
    for number, (name, person_at, door_sound, aim_z, frames, seen, silent) in enumerate(SEEN):
        stage_path = a_stage(tmp_path / f"seen{number}", person_at, door_sound)
        film = views(aim_z, frames)
        assert shots.people_seen(stage_path, film) == seen, name
        assert shots.silent_moving(stage_path, film) == silent, name
        faults = demo_film.seen_faults(stage_path, film, people=2)
        assert ("the place's design stands 2 people and the film's stage holds none" in faults) == (seen is None), (
            name, faults)
        assert ("the place holds people and no frame shows one" in faults) == (seen == {"shot0": 0}), (name, faults)
        assert [fault for fault in faults if "moves in view" in fault] == [
            f"{shot}: {path} moves in view with no sound" for shot, paths in silent.items() for path in paths], name
        assert not any("design stands" in fault for fault in demo_film.seen_faults(stage_path, film, people=0)), name
        demo_film.refuse_peopleless(name, stage_path, film, 0)
        if seen is None:
            with pytest.raises(RuntimeError, match="nothing rented"):
                demo_film.refuse_peopleless(name, stage_path, film, 2)
        else:
            demo_film.refuse_peopleless(name, stage_path, film, 2)

    # how many people a design stands, less those an accepted bodies gap names
    # (and whom its peel leaves out: a person with no dressed body is left out where a bodies gap names them, refused
    # by name where none does)
    import numpy as np
    from score.stages import sim_body
    from score.stages.demo_film import peel, peel_rows
    people = tmp_path / "people"
    (people / "clips").mkdir(parents=True)
    np.savez(people / "clips/rig.npz", names=np.array(["hips"]))
    for name, count, read, gaps, place, expected in CAST:
        square = {"rows": {"leader": {"looks": ["leader-drawn"]}, "crowd": {"crowd": "far-coat", "count": count}}}
        (people / "rows.json").write_text(json.dumps({"places": {"square": square}}))
        (people / "gaps.json").write_text(json.dumps({"gaps": gaps}))
        given = {"gaps": str(people / "gaps.json")} if gaps else {}
        gapped = demo_film.gapped_people(given)
        assert demo_film.cast_people(place, people / "rows.json" if read else None, gapped) == expected, name
        person_of = peel_rows.people_of({sim_body.CLIPS_ROW: str(people / "clips"), **given})
        for person in square["rows"]:
            if person in gapped:
                assert person_of({"name": person, "look": person}, {"clip": "idle"}) is None, (name, person)
            else:
                with pytest.raises(ValueError, match=f"{person}: no accepted dressed body"):
                    person_of({"name": person, "look": person}, {"clip": "idle"})

    # the environment's film cut from a locked script: its recorded take from the free preview of that very lock (a
    # preview recorded from another script wants making again and Blocks the cut), its peels the peel rows', two place
    # films at very different loudness matched in exposure and brought to one loudness, the gate holding the pacing
    from score.stages import design_layers
    monkeypatch.setattr(design_layers, "KEPT", tmp_path / "no-designs")  # no kept design shows people: no peel owed
    cut_script = dict(a_script([WALKS[0], TAKE, *WALKS[1:], *CUT_PEELS, STILL]), size=small_cut)
    moved = dict(cut_script, segments=[WALKS[0], dict(TAKE, seconds=4.0), *cut_script["segments"][2:]])
    locked_in(home, monkeypatch, ("toy", cut_script), ("plain", a_script(WALKS)))
    assert final.previews_wanted() == ["toy"]
    preview = home / final.PREVIEWS / "toy.json"
    preview.parent.mkdir(parents=True)
    preview.write_text(json.dumps({"script": cut_script}))
    assert final.previews_wanted() == []
    locked_in(home, monkeypatch, ("toy", moved))
    assert final.previews_wanted() == ["toy"]
    cutting = tmp_path / "cutting"
    cutting.mkdir()
    (cutting / "toy.json").write_text(json.dumps(cut_script))
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size={SMALL_CUT[0]}x{SMALL_CUT[1]}:rate=24:duration=3", "-pix_fmt", "yuv420p",
                    str(cutting / "002.mp4")], check=True)
    inputs = {"script toy": cutting / "toy.json", "preview toy": preview, "take toy 2": cutting / "002.mp4",
              "demo-film@alpha": a_film(cutting / "alpha", 330, 0.05),
              "demo-film@beta": a_film(cutting / "beta", 440, 0.6), "place-peel@beta": a_peel(cutting / "beta-peel")}
    assert final.takes("toy", cut_script, inputs) == {2: cutting / "002.mp4"}
    assert set(final.recorded_files("toy", cut_script)) == {"preview toy", "take toy 2"}
    with pytest.raises(graph.Blocked, match="segment\\(s\\) 2 of the free preview"):
        final.takes("toy", moved, inputs)
    with pytest.raises(graph.Blocked, match="segment 5: no accepted peel body-peel@alpha/wide"):
        final.peels(cut_script, inputs)
    inputs["body-peel@alpha"] = a_peel(cutting / "alpha-peel")
    assert final.matched_gain(116.0, 116.0) == 1.0 and final.matched_gain(40.0, 200.0) == final.GAIN_RANGE[1]
    out = tmp_path / "cut"
    out.mkdir()
    final.make(inputs, out, 0, {})
    assert final.output_faults(out) == []
    timeline = json.loads((out / "toy" / "timeline.json").read_text())
    assert [(segment["cut"], segment["film"]) for segment in timeline["segments"]] == [
        ("title", None), ("screen-take", None), ("walk-through", "demo-film@alpha"),
        ("walk-through", "demo-film@beta"), ("body-peel", "body-peel@alpha"), ("place-peel", "place-peel@beta"),
        ("hero-still", "demo-film@alpha")], timeline["segments"]
    assert timeline["segments"][2]["exposure_gain"] == 1.0 and timeline["seconds"] == 29.0, timeline
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.PASS, verdict
    # a card held still is planned (a 7 s card read frozen at 1280x720); a walk-through held still is not
    _, _, film_checks = final.cut_tools()
    measured = film_checks.video_checks
    for stretch, faults in (([0.0, 2.0], []), ([9.0, 13.0], ["toy: frozen [[9.0, 13.0]]"])):
        monkeypatch.setattr(film_checks, "video_checks", lambda *given, stretch=stretch: {  # the cut measured above
            "black": [], "frozen": [stretch], "failures": [f"frozen {[stretch]}"]})
        assert final.film_faults(out / "toy") == faults
    monkeypatch.setattr(film_checks, "video_checks", measured)
    timeline["segments"][2]["seconds"] = 3.5  # the 18 Oct cut's pace, written into the record
    (out / "toy" / "timeline.json").write_text(json.dumps(timeline))
    verdict = final.judge(out, inputs, {})
    assert verdict.answer == checks.FAIL and "toy: alpha: on screen 3.5 s, under 7 s" in verdict.findings, verdict

    # which scripts are cut: against the kept designs (lab and stairwell stand people with sim bodies, hangar none,
    # square a crowd alone), its plan faults and the owner's pacing; locked, the places its films show
    from score.stages import people_rows
    designs = tmp_path / "designs"
    designs.mkdir()
    for place in ("lab", "stairwell", "hangar", "square"):
        (designs / f"{place}.json").write_text("{}")
    monkeypatch.setattr(design_layers, "KEPT", designs)
    monkeypatch.setattr(design_layers, "has_layer", lambda place, kind: kind == "people" and place != "hangar")
    cast = {"square": {"rows": {"crowd": {"crowd": "far"}}},
            "lab": {"rows": {"crowd": {"crowd": "far"}, "ann": {"looks": ["ann_coat"]}}}}
    monkeypatch.setattr(people_rows, "place_entry", lambda place, found=None: cast.get(place))
    assert final.peopled() == ["lab", "stairwell"] and final.crowded() == ["square"]
    against = (final.peopled(), final.designed(), final.crowded())
    locked_in(home, monkeypatch)
    with pytest.raises(graph.Blocked, match="no film script locked"):
        final.require_yes(final.scripts())
    for name, script, designed, plan_faults, pacing in SCRIPTS:
        faults = final.plan_faults(script, *(against if designed else ()))
        if plan_faults == NO_ROW_YET:
            assert faults and all("no row makes" in fault for fault in faults), (name, faults)
        else:
            assert faults == plan_faults, (name, faults)
        assert final.pacing_faults(final.script_segments(script)) == pacing, name
        locked_in(home, monkeypatch, ("toy", script))
        final.require_yes(final.scripts())
        assert final.shown_places() == sorted({segment["shows"]["place"] for segment in script["segments"]
                                               if segment["cut"] in ("walk-through", "hero-still")}), name
    # the peels are rows: only a place a locked script peels has one, keyed on that script, a crowd's never a body
    # peel's; its shots the script's (a close-up where a segment names one, the longest segment's seconds)
    peeling = a_script([*WALKS, CROWD_PEEL, LAB_PEEL, *PEELED])
    locked_in(home, monkeypatch, ("toy", peeling))
    assert not peel_rows.applies_body("square") and peel_rows.applies_body("lab"), "no node that cannot draw"
    assert peel_rows.applies_body("alpha") and not peel_rows.applies_body("beta") and peel_rows.applies_place("beta")
    assert final.peeled_places() == ["alpha", "beta", "lab", "square"]
    assert peel_rows.body_files("alpha")["script toy"] == "{dashboard}/films/locked/toy.json"
    assert "script toy" not in peel_rows.place_files("alpha")
    assert all((REPO / path).exists() for path in peel_rows.TOOLS)
    assert {"design lab", "design stairwell", "design hangar"} <= set(final.files()), "a design gaining people moves it"
    (tmp_path / "peeling.json").write_text(json.dumps(peeling))
    assert peel_rows.shots_of({"script toy": tmp_path / "peeling.json"}, "alpha", final.PEEL) == {"wide": 5.0,
                                                                                                  "close": 4.0}
    assert peel_rows.shots_of({"script toy": tmp_path / "peeling.json"}, "beta", final.PLACE_PEEL) == {"wide": 5.0}

    # the close-up's walker by rule, never by hand
    for name, characters, clips, expected in CLOSE_WALKERS:
        cast = {"place": "street", "characters": characters}
        if expected.startswith("refused: "):
            with pytest.raises(ValueError, match=expected.removeprefix("refused: ")):
                peel.close_walker(cast, clips)
        else:
            assert peel.close_walker(cast, clips) == expected, name

    # a peel's frames: the record's own, wiped up in thirds, the push arrows fading in with the sim body
    for seconds, rate, frames, last in SOURCE_FRAMES:
        if isinstance(last, str):
            with pytest.raises(ValueError, match=last.removeprefix("refused: ")):
                peel.source_frames(seconds, rate, frames)
        else:
            assert peel.source_frames(seconds, rate, frames)[-1] == last, seconds
    fade = peel.arrow_fade(120)
    for frame, shown, coming, (low, high), faded in WIPES:
        found = peel.stage_of(frame, 120)
        assert found[:2] == (shown, coming) and (found[2] == low if low == high else low < found[2] < high), (frame,
                                                                                                         found)
        assert (fade[frame] == faded if isinstance(faded, float) else faded[0] < fade[frame] < faded[1]), frame
    pictures = [Image.new("RGB", SMALL, colour) for colour in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    frame = peel.wiped(pictures, 36, 120)  # a fifth of the way up: the mesh below, the clothed above
    assert frame.getpixel((5, SMALL[1] - 2)) == (0, 255, 0) and frame.getpixel((5, SMALL[1] // 2)) == (255, 0, 0)

    # what a body peel draws: the clip rig's own surface, an arrow at every body the ground pushes from its centre of
    # pressure along its push (a seated body's pelvis on its seat, as its feet; METRES_PER_NEWTON a newton, so a
    # sixth on the Moon), none for a body barely touching, standing where the person stands in the film's push colour
    rig = toy_rig()
    for clip, moved in SKINS:
        assert np.allclose(peel.skinned(rig, clip)[0], rig["points"] + moved), clip
    seated = {"touches": {"pelvis": [0.0, 520.0, 30.0, 0.0, 0.45, 0.1], "calcn_r": [5.0, 140.0, 0.0, 0.1, 0.0, 0.5],
                          "calcn_l": [0.0, 0.5, 0.0, -0.1, 0.0, 0.5]}}
    rig["clip_sitting"] = np.concatenate([rig["clip_still"], rig["clip_still"]])
    record = {"at": [2.0, 0.0, 1.0], "turn": 30.0, "clip": "sitting"}
    drawn = peel.person_arrays(record, rig, [seated, seated], [0, 1])
    where = sim_body.own_frame(record["at"], record["turn"])
    assert drawn["arrow_start"].shape == (2, 2, 3)  # the seat's push and the planted foot's; a foot barely touching none
    seat = where[:3, :3] @ np.array([0.0, 0.45, 0.1]) + where[:3, 3]
    assert np.allclose(drawn["arrow_start"][1, 0], peel.points_to_z(seat))
    assert np.allclose(drawn["arrow_vector"][1, 0], peel.points_to_z(where[:3, :3] @ np.array([0.0, 0.52, 0.03])))
    bodies = peel.touching([seated])
    moon = peel.pushes([{"touches": {"pelvis": [0.0, 520.0 / 6, 5.0, 0.0, 0.45, 0.1]}}], bodies)
    assert np.isclose(moon[0, 0, 4] * 6, peel.pushes([seated], bodies)[0, 0, 4]) and np.isnan(moon[0, 1]).all()
    with pytest.raises(ValueError, match="no `touches`"):
        peel.touching([{"feet": {"calcn_r": [0.0, 700.0]}}])
    linear = np.array(peel.push_colour())
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    from score.stages.demo_film import lettering
    assert np.allclose(srgb, np.array(lettering.token("film-push")[:3]) / 255.0, atol=2e-3)
    floor, roof = [[0, 0, 0], [1, 0, 0], [0, 1, 0]], [[0, 0, 2.5], [0, 1, 2.5], [1, 0, 2.5]]
    wall = [[0, 0, 0], [1, 0, 0], [0, 0, 2]]
    person = {"points": np.array([[[0.0, 0.0, 0.0], [0.0, 0.0, 1.8]]])}
    assert peel.underfoot(np.array([floor, roof, wall], dtype=float), [person]).tolist() == [floor], "level, below heads"

    # a peel's forecast prices each pass's frame as a measured film frame, a fogged stage's passes high, its high
    # never under its cards' own time
    plain = peel_rows.forecast({"wide": 5.0}, [False, False, False])
    fogged = peel_rows.forecast({"wide": 5.0}, [True, True, False])
    assert plain["frames"] == 120 and plain["renders"] == 360
    assert plain["card_minutes"] == round(360 * demo.FRAME_MINUTES)
    assert plain["euros"] == round(demo_film.LIKELY_EUROS * 360 / 192, 2)
    assert fogged["high_frame_minutes"] == 2 * demo_film.FOG_FRAME_MINUTES + demo.FRAME_MINUTES * demo_film.FRAME_SPREAD
    assert fogged["high_euros"] > 5 * plain["high_euros"]
    cards = plain["jobs"] * (8 + demo_film.JOB_LEAD_MINUTES) + 120 * plain["high_frame_minutes"]
    assert plain["high_euros"] >= round(cards * peel_rows.card_euros_a_minute(), 2) > plain["euros"]

    # the fogged hall's place peel, made from its finished stage: its frames dealt over the forecast's cards, each
    # slice its own frames into its own folder, all joined, judged on its film
    (tmp_path / "hall-peel.json").write_text(json.dumps(
        dict(peeling, segments=[{"cut": "place-peel", "shows": {"place": "hall"}, "seconds": 1.0}])))
    monkeypatch.setattr(demo_film, "SIZE", SMALL)
    monkeypatch.setattr(peel_rows, "forecast", lambda shots, passes, slow=None: dict(plain, jobs=3))

    def drawn_here(cloud, node, out):  # the cards' part, drawn here: each slice its own frames, in its own folder
        for path in cloud:
            job = json.loads(pathlib.Path(json.loads(path.read_text())["args"][0]).read_text())
            for frame in range(*job["frames"]):
                for number, name in enumerate(job["passes"]):
                    (pathlib.Path(job["out"]) / name).mkdir(parents=True, exist_ok=True)
                    Image.new("RGB", SMALL, (60 * number, 90, 30 + frame)).save(
                        pathlib.Path(job["out"]) / name / f"{frame:04d}.png")
    monkeypatch.setattr(peel_rows, "render", drawn_here)
    peeled = tmp_path / "peeled"
    peeled.mkdir()
    peel_rows.make_place({"assembly": stage, "script toy": tmp_path / "hall-peel.json"}, peeled, 0, {})
    made = json.loads((peeled / "peel.json").read_text())
    assert made["shots"]["wide"]["frames"] == 24 and peel_rows.output_faults(peeled) == []
    assert peel_rows.judge(peeled, {}, {}).answer == checks.PASS
    assert not (peeled / ".work").exists()


# --- the film gate --------------------------------------------------------------------------------------------------

def look_only_film(root):
    """A planned look-only film of SHOTS shots whose frames are all one colour, cut by demo.py at SMALL: its video."""
    demo, _ = demo_film.film_tools()
    frames = root / "frames/hall"
    frames.mkdir(parents=True)
    count = round(demo_film.SECONDS * demo.RATE)
    views = [{"name": f"shot{shot}-{number:03d}"} for shot in range(demo_film.SHOTS) for number in range(count)]
    for view in views:
        Image.new("RGB", SMALL, (90, 110, 130)).save(frames / f"{view['name']}-look.png")
    (root / "views").mkdir()
    (root / "views/hall.json").write_text(json.dumps({"size": list(SMALL), "ink": False, "seconds": demo_film.SECONDS,
                                                      "views": views}))
    demo.cut(root, ["hall"])
    return root / "videos/hall.mp4"


@pytest.fixture(scope="module")
def still_film(tmp_path_factory):
    return look_only_film(tmp_path_factory.mktemp("cut"))



def views(aim_z=-10.0, frames=range(4)):
    """A standing shot looking along z, one view a frame."""
    return [{"name": f"shot0-{frame:03d}", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, aim_z], "fov": 75.0,
             "frame": frame} for frame in frames]


def a_stage(folder, person_at=None, door_sound=False):
    """A place with a person standing at `person_at` and a door sliding 0.5 m a frame along x at z = -5."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"hall-{person_at}-{door_sound}.usda"
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, "/hall")
    stage.SetDefaultPrim(root.GetPrim())
    for group in ("Characters", "Objects"):
        UsdGeom.Xform.Define(stage, f"/hall/{group}")
    if person_at is not None:
        person = UsdSkel.Root.Define(stage, "/hall/Characters/walker")
        person.AddTranslateOp().Set(Gf.Vec3d(*person_at))
        person.CreateExtentAttr().Set(Vt.Vec3fArray([(-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)]))  # no skeleton: bound given
    door = UsdGeom.Xform.Define(stage, "/hall/Objects/door")
    slide = door.AddTranslateOp()
    for frame in range(4):
        slide.Set(Gf.Vec3d(0.5 * frame, 1.0, -5.0), frame)
    UsdGeom.Cube.Define(stage, "/hall/Objects/door/leaf").CreateSizeAttr(1.0)
    if door_sound:
        UsdMedia.SpatialAudio.Define(stage, "/hall/Objects/door/Sound_0")
    stage.GetRootLayer().Save()
    return path


# --- the environment's own film (final.py) --------------------------------------------------------------------------

def locked_in(home, monkeypatch, *films):
    """The cockpit's home `home` holding `films` ({film: script}) locked, as the Film step's Lock keeps them."""
    folder = home / final.LOCKED
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*.json"):
        path.unlink()
    for film, script in films:
        (folder / f"{film}.json").write_text(json.dumps(script))
    monkeypatch.setattr(final, "DASHBOARD", home)


# The cut tests' frame: the cut's own steps at a small size, so a gate pod of 2-4 cores encodes them well inside the
# time budget (at the showcase's 1920x1080 the two tests took 108 s of 110 on two cores); loudness, pacing, sources,
# exposure and the timeline are measured as at full size.
SMALL_CUT = (480, 270)


@pytest.fixture
def small_cut(monkeypatch):
    """The showcase's clips drawn at SMALL_CUT (final.cut_tools' showcase W, H); the script's size to give the cut."""
    _, showcase, _ = final.cut_tools()
    monkeypatch.setattr(showcase, "W", SMALL_CUT[0])
    monkeypatch.setattr(showcase, "H", SMALL_CUT[1])
    return list(SMALL_CUT)


def a_film(folder, tone, volume):
    """A place film as demo-film keeps one: 9 s at SMALL_CUT, its sound a tone at `volume`."""
    folder.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size={SMALL_CUT[0]}x{SMALL_CUT[1]}:rate=24:duration=9", "-f", "lavfi", "-i",
                    f"sine=frequency={tone}:duration=9,volume={volume}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-shortest", str(folder / "film.mp4")], check=True)
    return folder


def a_peel(folder, shot="wide"):
    """A peel as the peel rows keep one: 5 s at SMALL_CUT, silent, in its shot's folder."""
    (folder / shot).mkdir(parents=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"testsrc2=size={SMALL_CUT[0]}x{SMALL_CUT[1]}:rate=24:duration=5", "-pix_fmt", "yuv420p",
                    str(folder / shot / "peel.mp4")],
                   check=True)
    return folder


def toy_rig():
    """Two joints (a root at the floor, a hip 1 m over it) and three points: one on each joint, one shared half and
    half; a clip `still` at the bind and `step` with the root moved 1 m along z."""
    import numpy as np
    bind = np.tile(np.eye(4), (2, 1, 1))
    bind[1, 1, 3] = 1.0
    local = np.tile(np.eye(4), (1, 2, 1, 1))
    local[0, 1, 1, 3] = 1.0
    step = local.copy()
    step[0, 0, 2, 3] = 1.0
    return {"names": np.array(["Root", "Hips"]), "parents": np.array([-1, 0]), "bind": bind,
            "points": np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 0.0]]),
            "weights": np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]), "clip_still": local, "clip_step": step}
