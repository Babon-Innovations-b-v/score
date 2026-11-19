"""A place's film (#128, owner 2026-11-16: "get me my demo"): a camera path that opens on the concept's view, glides
down into the place and moves through it at eye height (the place's named views as its waypoints), clear of every
solid the physics check reads (ready.Place), and its frames rendered on this PC's card.

    path(folder, through=None, seconds=SECONDS, eye=EYE, seed=0) -> {...}   writes <folder>/film/path.json
    render(folder, every=1, final=False, out=None) -> {...}                 <out>/f<NNNN>-look.png, timing

The path: HOLD seconds still on the concept's view, a straight glide (a ball of camera_paths.CLEARANCE swept along it
meets nothing) from the concept's eye to the first waypoint, then camera_paths' legs (a straight walkable edge, else
RRT*'s) waypoint to waypoint at `eye` over the floor (above it for an outdoor place). The corners are cut (Chaikin)
only where the cut path stays as clear. The camera's speed eases in and out (a smoothed speed curve, never a jump);
it looks from the concept's aim to LOOK_AHEAD further along its path over the glide, its field of view from the
concept's to WALK_FOV. Every frame's eye is measured against the meshes (camera_paths.clearances) and listed.

A frame carries `"frame": n`, the stage's time code, so walkers laid in the stage (sim body's solved motion as a
character's time samples) move with the film; a place with none is filmed without people.
"""
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import trimesh

from score.stages import place_build
from score.stages.place_build import ready
from score.stages.place_build import render as preview

sys.path.insert(0, str(place_build.REPO / "tools/usd"))
import camera_paths  # noqa: E402

FPS = 24
SECONDS = 25.0  # about 20-30 s a place (the owner's brief)
HOLD = 2.0  # seconds still on the concept's view
GLIDE_SPEED = 6.0  # metres a second the glide aims at, between GLIDE_SHARE's bounds of the moving time
GLIDE_SHARE = (0.15, 0.35)
EASE = 0.6  # seconds: the speed curve's smoothing (a gaussian's spread)
STOP = 1.0  # seconds the camera slows to a stop at its end
EYE = camera_paths.EYE_HEIGHT
LOW_VIEW = 2.5  # a named view whose eye stands at most this over its floor is a waypoint; higher ones are overviews
LOOK_AHEAD = 3.0  # metres along the path each walking frame looks
LOOK_DOWN = 0.3  # metres under the eye ahead it looks at
WALK_FOV = 70.0
TURN_EASE = 0.5  # seconds: the look's smoothing over frames
CHAIKIN = 3  # corner cuts tried (fewer when a cut path is not clear)
CLEAR = camera_paths.CLEARANCE
MARGIN = 5.0  # metres past the place's objects a walk may go round them


def place_scenes(folder):
    """The place as camera_paths' scenes, from the physics check's own solids (ready.Place): every object but its
    characters and its lights (a sky dome laid as an object holds the whole place), each door as it stands for the
    walkers (ready.doors_standing: one marked score:opens swung open, so a camera sees and follows a walker through
    its doorway), its laid grounds as the ground; an object the camera cuts (place.json `cut`) is no solid to it, so
    the camera passes the closed front it sees through."""
    stage, place = place_build.opened(folder)
    laid = ready.Place(stage, place)
    grounds = laid.with_role("ground")
    standing = ready.doors_standing(laid)
    cut = set(place_build.record_of(folder).get("cut") or [])
    shown = {name: standing.get(name, laid.meshes[name]) for name in laid.names
             if name not in grounds and name not in cut and ready.text_of(laid.prims[name], "score:kind") != "light"}
    ground = trimesh.util.concatenate([laid.meshes[name] for name in grounds]) if grounds else \
        trimesh.creation.box([2000.0, 0.01, 2000.0], trimesh.transformations.translation_matrix([0, -0.005, 0]))

    def height(flat):
        flat = np.atleast_2d(flat)
        origins = np.column_stack([flat[:, 0], np.full(len(flat), 10000.0), flat[:, 1]])
        far = camera_paths.first_hits(ground, origins, np.tile([0.0, -1.0, 0.0], (len(flat), 1)))
        return np.where(np.isfinite(far), 10000.0 - far, np.nan)

    return camera_paths.scenes_of(shown, ground, height, np.zeros((0, 8, 3)))


def stop_of(record, text, eye, scenes):
    """One stop of the film from its words: a named view (its eye set `eye` over the floor under it when it is a
    low one, its aim and field of view kept), `x,z` (`eye` over the floor there, looking ahead) or `x,y,z` (a point
    in free air); either point may end `>ax,ay,az`, a spot it looks at."""
    views = record.get("views", {})
    if text in views:
        view = views[text]
        spot, aim, fov = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float), view["fov"]
    else:
        where, _, looked = text.partition(">")
        spot = np.array([float(value) for value in where.split(",")])
        aim = np.array([float(value) for value in looked.split(",")]) if looked else None
        fov = WALK_FOV
        if len(spot) == 3:
            return {"name": text, "eye": spot, "aim": aim, "fov": fov, "floor": False}
        spot = np.array([spot[0], eye, spot[1]])
    found = camera_paths.eyes_over(scenes, [[spot[0], spot[2]]], eye, [max(spot[1], eye)])[0]
    if not np.isfinite(found[1]):
        raise place_build.Refused(f"no floor under the stop {text}")
    if spot[1] - (found[1] - eye) > LOW_VIEW:  # an overview: seen from where it stands
        return {"name": text, "eye": spot, "aim": aim, "fov": fov, "floor": False}
    return {"name": text, "eye": found, "aim": aim, "fov": fov, "floor": True}


def stops_of(record, scenes, through, eye):
    """The film's stops: the concept's view, then `through` in order (stop_of), else every low named view
    nearest-first from the concept's eye."""
    camera = record["camera"]
    first = {"name": "concept", "eye": np.asarray(camera["eye"], dtype=float),
             "aim": np.asarray(camera["aim"], dtype=float), "fov": camera["fov"], "floor": False}
    if through:
        return [first] + [stop_of(record, text, eye, scenes) for text in through]
    found = [stop for stop in (stop_of(record, name, eye, scenes) for name in record.get("views", {})) if stop["floor"]]
    if not found:
        raise place_build.Refused("no low named view to walk through: give --through")
    ordered = [first]
    while found:
        nearest = min(range(len(found)), key=lambda index: np.linalg.norm((found[index]["eye"] - ordered[-1]["eye"])
                                                                            [[0, 2]]))
        ordered.append(found.pop(nearest))
    return ordered


def straight(scenes, start, goal):
    """A free-air leg: straight when a ball swept along it is clear, else over the goal at the start's height and
    straight down; None when neither is."""
    for corners in ([start, goal], [start, np.array([goal[0], start[1], goal[2]]), goal]):
        if all(camera_paths.swept_clear(scenes["solid"], first, second, CLEAR)
               for first, second in zip(corners, corners[1:])):
            return [np.asarray(corner, dtype=float) for corner in corners]
    return None


def route(scenes, stops, eye, seed):
    """The path's corners stop to stop: camera_paths' walk (a walkable straight edge, else RRT*'s) between two
    floor stops, a straight free-air leg (straight) where either end is in the air; and each stop's corner index."""
    corners, at = [stops[0]["eye"]], [0]
    for number, (start, goal) in enumerate(zip(stops, stops[1:])):
        if start["floor"] and goal["floor"]:
            bounds = np.asarray(scenes["extent"]) + [-MARGIN, -MARGIN, MARGIN, MARGIN]
            found = camera_paths.leg(scenes, start["eye"], goal["eye"], bounds, seed + number, eye, CLEAR)
        else:
            found = straight(scenes, start["eye"], goal["eye"])
        if found is None:
            raise place_build.Refused(f"no clear way from {start['name']} to {goal['name']}")
        corners += found[1:]
        at.append(len(corners) - 1)
    return corners, at


def chaikin(corners, cuts):
    """The polyline with its corners cut `cuts` times (its ends kept)."""
    points = np.asarray(corners, dtype=float)
    for _ in range(cuts):
        if len(points) < 3:
            break
        inner = [points[0]]
        for first, second in zip(points[:-1], points[1:]):
            inner += [0.75 * first + 0.25 * second, 0.25 * first + 0.75 * second]
        inner.append(points[-1])
        points = np.array(inner)
    return points


def rounded(scenes, corners):
    """The corners cut as often as the cut path stays clear (every span a clear swept ball)."""
    for cuts in range(CHAIKIN, 0, -1):
        cut = chaikin(corners, cuts)
        if all(camera_paths.swept_clear(scenes["solid"], first, second, CLEAR) for first, second in zip(cut, cut[1:])):
            return cut, cuts
    return np.asarray(corners, dtype=float), 0


def smoothed(values, spread):
    """Values over frames blurred by a gaussian `spread` frames wide, their ends held."""
    if spread < 1e-6:
        return np.asarray(values, dtype=float)
    reach = int(3 * spread) + 1
    kernel = np.exp(-0.5 * (np.arange(-reach, reach + 1) / spread) ** 2)
    kernel /= kernel.sum()
    values = np.asarray(values, dtype=float)
    padded = np.concatenate([np.repeat(values[:1], reach, axis=0), values, np.repeat(values[-1:], reach, axis=0)])
    if values.ndim == 1:
        return np.convolve(padded, kernel, mode="valid")
    return np.column_stack([np.convolve(padded[:, axis], kernel, mode="valid") for axis in range(values.shape[1])])


def distances(count, glide_length, walk_length):
    """How far along the path (metres) the camera is at each frame: still for HOLD, then the glide and the walk at
    their own speeds, the speed eased between them and to a stop at the end."""
    held, moving = int(round(HOLD * FPS)), count - int(round(HOLD * FPS))
    low, high = GLIDE_SHARE
    glide_frames = int(round(np.clip(glide_length / GLIDE_SPEED * FPS, low * moving, high * moving)))
    stop = int(round(STOP * FPS))
    walk_frames = max(moving - glide_frames - stop, 1)
    moving_speed = np.concatenate([np.full(glide_frames, glide_length / max(glide_frames, 1)),
                                   np.full(walk_frames, walk_length / walk_frames),
                                   np.zeros(moving - glide_frames - walk_frames)])
    ramp = int(round(2 * EASE * FPS))  # starting from rest: the eased speed leaves the hold at nought
    speed = np.concatenate([np.zeros(held), smoothed(np.concatenate([np.zeros(ramp), moving_speed]), EASE * FPS)[ramp:]])
    along = np.concatenate([[0.0], np.cumsum(speed)[:-1]])
    return along * (glide_length + walk_length) / max(along[-1], 1e-9)


def at_distances(points, spots):
    """The points along the polyline at each distance."""
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    return np.column_stack([np.interp(spots, along, points[:, axis]) for axis in range(3)]), along[-1]


def stop_distances(points, at, corners):
    """How far along the rounded path each stop lies: its corner's nearest point on it."""
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    found = []
    for index in at:
        nearest = int(np.argmin(np.linalg.norm(points - corners[index], axis=1)))
        found.append(float(along[nearest]))
    return np.maximum.accumulate(found)


def ahead_ways(points, eyes, spots):
    """The way each frame looks when it looks ahead: LOOK_AHEAD further along the path, LOOK_DOWN under it."""
    total = at_distances(points, [0.0])[1]
    ahead, _ = at_distances(points, np.minimum(spots + LOOK_AHEAD, total))
    past = spots + LOOK_AHEAD > total
    way_out = points[-1] - points[-2]
    ahead[past] = points[-1] + np.outer(spots[past] + LOOK_AHEAD - total, way_out / np.linalg.norm(way_out))
    ahead[:, 1] -= LOOK_DOWN
    ways = ahead - eyes
    return ways / np.maximum(np.linalg.norm(ways, axis=1), 1e-9)[:, None]


def looks(stops, places, eyes, spots, ahead):
    """Each frame's way and field of view: between two stops, from the one's look to the next's (a stop with an aim
    looks at it from wherever the camera is, one without looks ahead), eased over the leg."""
    ways, fovs = np.zeros_like(eyes), np.zeros(len(eyes))
    for frame, (eye, spot) in enumerate(zip(eyes, spots)):
        leg = int(np.clip(np.searchsorted(places, spot, side="right") - 1, 0, len(stops) - 2))
        share = np.clip((spot - places[leg]) / max(places[leg + 1] - places[leg], 1e-9), 0.0, 1.0)
        share = share * share * (3 - 2 * share)
        ends = []
        for stop in (stops[leg], stops[leg + 1]):
            way = ahead[frame] if stop["aim"] is None else stop["aim"] - eye
            ends.append(way / max(np.linalg.norm(way), 1e-9))
        ways[frame] = (1 - share) * ends[0] + share * ends[1]
        fovs[frame] = (1 - share) * stops[leg]["fov"] + share * stops[leg + 1]["fov"]
    ways = smoothed(ways / np.maximum(np.linalg.norm(ways, axis=1), 1e-9)[:, None], TURN_EASE * FPS)
    return ways / np.maximum(np.linalg.norm(ways, axis=1), 1e-9)[:, None], fovs


def path(folder, through=None, seconds=SECONDS, eye=EYE, seed=0):
    """The place's film path as frames, measured, written to <folder>/film/path.json."""
    folder = pathlib.Path(folder)
    record = place_build.record_of(folder)
    scenes = place_scenes(folder)
    stops = stops_of(record, scenes, through, eye)
    corners, at = route(scenes, stops, eye, seed)
    points, cuts = rounded(scenes, corners)
    places = stop_distances(points, at, corners)
    total = float(places[-1])
    glide_length = float(places[1])
    count = int(round(seconds * FPS))
    spots = distances(count, glide_length, total - glide_length)
    eyes, _ = at_distances(points, spots)
    ways, fovs = looks(stops, places, eyes, spots, ahead_ways(points, eyes, spots))
    walls, _ = camera_paths.clearances(scenes, eyes)
    frames = [{"name": f"f{number:04d}", "eye": [round(float(value), 4) for value in spot],
               "aim": [round(float(value), 4) for value in spot + 10.0 * way], "up": [0.0, 1.0, 0.0],
               "fov": round(float(fov), 3), "frame": number, "look_only": True}
              for number, (spot, way, fov) in enumerate(zip(eyes, ways, fovs))]
    near = [frame["name"] for frame, wall in zip(frames, walls) if wall < CLEAR - camera_paths.KEPT_TO]
    walk_seconds = (count - int(round((HOLD + STOP) * FPS))) / FPS
    measured = {"place": record["place"], "frames": count, "fps": FPS, "seconds": count / FPS,
                "through": [stop["name"] for stop in stops[1:]], "eye": eye, "corner_cuts": cuts,
                "glide_metres": round(glide_length, 1), "metres": round(total, 1),
                "speed": round((total - glide_length) / max(walk_seconds, 1e-9), 2),
                "least_clearance": round(float(walls.min()), 3), "frames_too_near": near}
    out = folder / "film"
    out.mkdir(exist_ok=True)
    (out / "path.json").write_text(json.dumps(dict(measured, views=frames), indent=1))
    return dict(measured, frames_too_near=len(near), file=str(out / "path.json"))


def listing(folder, every, final, out):
    """usd_views' listing of every `every`th frame of the film's path: the films' samples at 1920x1080 when `final`,
    else the review's at half that; `cut` the objects the camera sees through (place.json `cut`)."""
    made = json.loads((pathlib.Path(folder) / "film" / "path.json").read_text())
    size = list(preview.FINAL_SIZE) if final else [size // 2 for size in preview.FINAL_SIZE]
    listed = {"size": size, "review": not final, "views": made["views"][::every],
              "cut": place_build.record_of(folder).get("cut") or []}
    path_out = out / "views.json"
    path_out.write_text(json.dumps(listed, indent=1))
    return path_out, len(listed["views"])


def render(folder, every=1, final=False, out=None):
    """The film's frames rendered on this PC's card (through the card queue, memory-capped); seconds a frame from
    the pictures' own times."""
    folder = pathlib.Path(folder).resolve()
    out = pathlib.Path(out or folder / "film" / ("final" if final else "preview")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    free = preview.available_gb()
    if free <= preview.FREE_GB:
        raise preview.RenderFailed(f"{free:.1f} GB memory available, a Blender needs over {preview.FREE_GB}")
    views, count = listing(folder, every, final, out)
    for stale in out.glob("f*-look.png"):
        stale.unlink()
    log = out / "blender.log"
    began = time.time()
    with log.open("w") as written:
        done = subprocess.run(preview.queued(f"film-{folder.name}", preview.SCRIPT,
                                             [str(place_build.scene_path(folder)), str(views), str(out)]),
                              stdout=written, stderr=subprocess.STDOUT, cwd=place_build.REPO)
    pictures = sorted(out.glob("f*-look.png"), key=lambda picture: picture.stat().st_mtime)
    if done.returncode or len(pictures) != count:
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise preview.RenderFailed(f"exit {done.returncode}, {len(pictures)} of {count} frames, log {log}: {tail}")
    times = [picture.stat().st_mtime for picture in pictures]
    per_frame = (times[-1] - times[0]) / (count - 1) if count > 1 else None
    return {"frames": count, "out": str(out), "seconds": round(time.time() - began, 1),
            "seconds_a_frame": None if per_frame is None else round(per_frame, 1)}
