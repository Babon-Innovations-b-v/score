"""The film script's words, defaults and checks, and where its file lives (the package docstring has the format).
Plain Python only: the hosted process reads it too."""
import json
import os
import pathlib
import re

from score.dashboard.films import takes

FORMAT = "score-film-script"
VERSION = 1
NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
SEED_FOLDER = "data/films"
SAVED_FOLDER = "films"
# The overlap of a cross-fade or a push (tools/review/demo.py FADE_SECONDS).
TRANSITION_SECONDS = 0.5
# An accepted demo-film's shot: after its 2 s title card (demo.py TITLE_SECONDS), 4 s of walking less the card's
# half-second fade (score/stages/demo_film SECONDS; showcase.py SHOT_SHOWN): what a walk-through reuses for free.
FILM_SHOT_FROM = 2.0
FILM_SHOT_SECONDS = 3.5
SHORTEST, LONGEST = 0.5, 60.0
MOST_SEGMENTS = 200
TARGET_SECONDS = 240
WALK_SECONDS = 7.0

# Each cut type: its words, its default length, what it must name besides what it shows, its usual transition and
# sound, and its group in the Add segment menu. A walk-through is WALK_SECONDS: 3.5 s a place read far too fast (the
# owner, 2026-10-18), so a place gets 7 s of its finished state, rendered again where its accepted 4 s film is too
# short. Every default is long enough to read what the cut shows (owner, 2026-10-21: "this gonna be to short"): a
# physics animation 12 s, so a body goes a clear way round its orbit.
SCENE, INSIDE, APP, PHYSICS, WORDS = "A scene", "Inside a scene", "The app", "The physics", "Words"
GROUPS = (APP, PHYSICS, SCENE, INSIDE, WORDS)
CUTS = {
    "walk-through": {"label": "Walk-through", "seconds": WALK_SECONDS, "needs": ("place",),
                     "transition": "cross-fade", "sound": "place", "group": SCENE,
                     "words": "the camera's path through the scene"},
    "orbit": {"label": "Orbit", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade", "sound": "bed",
              "group": SCENE, "words": "a slow circle round the whole scene"},
    "hero-still": {"label": "Still picture", "seconds": 4.0, "needs": ("place",), "transition": "cross-fade",
                   "sound": "bed", "group": SCENE, "words": "one picture held, slowly closing in"},
    "exploded": {"label": "Exploded view", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade",
                 "sound": "bed", "group": INSIDE, "words": "the room split apart into its parts"},
    "isolate": {"label": "Isolate a part", "seconds": 5.0, "needs": ("place", "part"), "transition": "cross-fade",
                "sound": "bed", "group": INSIDE, "words": "zoom in on one part, the rest falls away"},
    "layer-focus": {"label": "Layer focus", "seconds": 5.0, "needs": ("place", "layer"), "transition": "cross-fade",
                    "sound": "bed", "group": INSIDE, "words": "one OpenUSD layer lit, the others ghosted"},
    "layer-split": {"label": "Layer split", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade",
                    "sound": "bed", "group": INSIDE, "words": "the layer stack lifted apart"},
    "step-card": {"label": "Step card", "seconds": 5.0, "needs": ("place", "step"), "transition": "push",
                  "sound": "bed", "group": SCENE, "words": "a framework step's own pictures"},
    "before-after": {"label": "Before and after", "seconds": 5.0, "needs": ("place",), "transition": "cross-fade",
                     "sound": "bed", "group": SCENE, "words": "the concept wiped into the result"},
    "title": {"label": "Title card", "seconds": 4.0, "needs": (), "transition": "fade-through-black",
              "sound": "bed", "group": WORDS, "words": "the film's title"},
    "text": {"label": "Text card", "seconds": 4.0, "needs": (), "transition": "cross-fade", "sound": "bed",
             "group": WORDS, "words": "a line of words"},
    "screen-take": {"label": "Screen take", "seconds": 8.0, "needs": ("page",), "transition": "cross-fade",
                    "sound": "bed", "group": APP,
                    "words": "a real cockpit page, its cursor, clicks and highlights scripted"},
    "setting-animation": {"label": "Physics animation", "seconds": 12.0, "needs": ("world",),
                          "transition": "cross-fade", "sound": "bed", "group": PHYSICS,
                          "words": "the physics' bodies on their orbits, time sped up"},
    "scale-zoom": {"label": "Scale zoom", "seconds": 22.0, "needs": ("place",), "transition": "cross-fade",
                   "sound": "bed", "group": PHYSICS,
                   "words": "one camera path from the physics down to the scene's rooms"},
}
# The cuts the free preview renders itself in headless Chromium (films/preview), not the editor's live player.
RECORDED = ("screen-take", "setting-animation", "scale-zoom")
# A scale zoom's layers, top down (CONTEXT.md "scale zoom"), and the corners a picture-in-picture may sit in.
LAYERS = ("setting", "world", "site", "place", "room")
CORNERS = ("top-left", "top-right", "bottom-left", "bottom-right")
TRANSITIONS = {"cut": "Cut", "cross-fade": "Cross-fade", "fade-through-black": "Fade through black",
               "push": "Push"}
OVERLAPPING = ("cross-fade", "push")
SOUNDS = {"place": "The scene's own sound", "bed": "Sound bed (nearest film)", "silence": "Silence"}
# The framework's steps a step card shows, in the chain's order.
STEPS = {"reference": "References and style", "concept": "Concept", "plan": "Plan", "pieces": "Pieces"}


def default_seconds(script, cut):
    """The length a segment of `cut` takes when it names none: the script's own default, else CUTS'."""
    return float((script.get("defaults") or {}).get(cut, CUTS[cut]["seconds"]))


def seconds_of(script, segment):
    """A segment's length in seconds."""
    given = segment.get("seconds")
    return float(given) if given is not None else default_seconds(script, segment["cut"])


def overlap_of(index, segment):
    """The seconds a segment starts before the one before it ends: TRANSITION_SECONDS for a cross-fade or a push
    after the first segment, else none."""
    return TRANSITION_SECONDS if index > 0 and segment.get("transition") in OVERLAPPING else 0.0


def timeline(script):
    """Each segment's (start, seconds) on the film's clock, in order."""
    found, clock = [], 0.0
    for index, segment in enumerate(script.get("segments", [])):
        start = max(0.0, clock - overlap_of(index, segment))
        length = seconds_of(script, segment)
        found.append((round(start, 3), length))
        clock = start + length
    return found


def total_seconds(script):
    """The film's whole length in seconds."""
    return round(max((start + length for start, length in timeline(script)), default=0.0), 3)


def segment_faults(script, number, segment):
    """What is wrong with one segment, in words (number counts from 1)."""
    cut = segment.get("cut")
    if cut not in CUTS:
        return [f"segment {number}: no cut type {cut!r}"]
    found = []
    shows = segment.get("shows") or {}
    found += [f"segment {number} ({CUTS[cut]['label']}) names no {need}" for need in CUTS[cut]["needs"]
              if not shows.get(need)]
    if cut == "step-card" and shows.get("step") and shows["step"] not in STEPS:
        found.append(f"segment {number}: no framework step {shows['step']!r}")
    found += takes.faults(number, segment) if cut == "screen-take" else []
    found += zoom_faults(number, segment) if cut == "scale-zoom" else []
    found += pip_faults(number, segment.get("pip"))
    if segment.get("transition", "cut") not in TRANSITIONS:
        found.append(f"segment {number}: no transition {segment.get('transition')!r}")
    if segment.get("sound", "bed") not in SOUNDS:
        found.append(f"segment {number}: no sound {segment.get('sound')!r}")
    length = segment.get("seconds")
    if length is not None and not (isinstance(length, (int, float)) and SHORTEST <= length <= LONGEST):
        found.append(f"segment {number}: {length!r} s is not between {SHORTEST} and {LONGEST}")
    return found


def zoom_faults(number, segment):
    """What is wrong with a scale zoom's legs: each a layer of LAYERS, top down, with its seconds summing to the
    segment's."""
    legs = segment.get("legs")
    if not isinstance(legs, list) or not legs:
        return [f"segment {number}: a scale zoom lists its legs"]
    found = [f"segment {number}: no layer {leg.get('layer')!r}" for leg in legs if leg.get("layer") not in LAYERS]
    order = [LAYERS.index(leg["layer"]) for leg in legs if leg.get("layer") in LAYERS]
    if order != sorted(order):
        found.append(f"segment {number}: a scale zoom goes down through the layers, never back up")
    if any(not isinstance(leg.get("seconds"), (int, float)) or leg["seconds"] <= 0 for leg in legs):
        found.append(f"segment {number}: every leg names its seconds")
    elif segment.get("seconds") is not None and abs(sum(leg["seconds"] for leg in legs) - segment["seconds"]) > 1e-6:
        found.append(f"segment {number}: its legs last {sum(leg['seconds'] for leg in legs):g} s, not its "
                     f"{segment['seconds']:g} s")
    return found


def pip_faults(number, pip):
    """What is wrong with a segment's picture-in-picture (none is sound)."""
    if pip is None:
        return []
    if not isinstance(pip, dict) or not (pip.get("concept") or pip.get("picture")):
        return [f"segment {number}: a picture-in-picture names a scene's concept or a picture"]
    return [f"segment {number}: no corner {pip.get('corner')!r}"] if pip.get("corner", "top-right") not in CORNERS \
        else []


def faults(script, places=None):
    """What is wrong with a script, in words; empty when it is sound. With `places`, a place it names must be one."""
    if script.get("format") != FORMAT or script.get("version") != VERSION:
        return [f"not a {FORMAT} version {VERSION}"]
    if not NAME.match(str(script.get("film", ""))):
        return [f"the film's name {script.get('film')!r} is not lower-case letters, digits and dashes"]
    segments = script.get("segments")
    if not isinstance(segments, list) or len(segments) > MOST_SEGMENTS:
        return [f"segments is a list of at most {MOST_SEGMENTS}"]
    found = [fault for number, segment in enumerate(segments, 1)
             for fault in segment_faults(script, number, segment)]
    for cut, seconds in (script.get("defaults") or {}).items():
        if cut not in CUTS or not (isinstance(seconds, (int, float)) and SHORTEST <= seconds <= LONGEST):
            found.append(f"default {cut!r}: {seconds!r} s")
    if places is not None:
        found += [f"segment {number}: no scene {segment['shows']['place']!r}"
                  for number, segment in enumerate(segments, 1)
                  if (segment.get("shows") or {}).get("place") and segment["shows"]["place"] not in places]
    return found


def blank(film, title):
    """A new film's script: its title card only."""
    return {"format": FORMAT, "version": VERSION, "film": film, "title": title, "world": "world1",
            "target_seconds": TARGET_SECONDS, "size": [1280, 720], "rate": 24, "defaults": {},
            "segments": [{"cut": "title", "shows": {"world": "world1"}, "transition": "fade-through-black",
                          "sound": "bed", "text": title}]}


def seed_path(repo, film):
    return pathlib.Path(repo) / SEED_FOLDER / f"{film}.json"


def saved_path(home, film):
    return pathlib.Path(home) / SAVED_FOLDER / f"{film}.json"


def preview_files(home, hosted, film):
    """(the film's rendered free preview, its record) where a cockpit holds them: its home's previews
    (films/preview/make.py), hosted the export's copy."""
    folder = pathlib.Path(home) / ("export/current/films" if hosted else "films/previews")
    return folder / f"{film}.mp4", folder / f"{film}.json"


def names(repo, home):
    """Every film with a script, the starters' and the saved ones'."""
    found = {path.stem for folder in (pathlib.Path(repo) / SEED_FOLDER, pathlib.Path(home) / SAVED_FOLDER)
             if folder.is_dir() for path in folder.glob("*.json")}
    return sorted(name for name in found if NAME.match(name))


def read(repo, home, film):
    """(the film's script, where it was read from: "saved" or "starter"), or (None, None) when it has none."""
    for path, origin in ((saved_path(home, film), "saved"), (seed_path(repo, film), "starter")):
        if path.is_file():
            return json.loads(path.read_text()), origin
    return None, None


def save(home, script):
    """Write the script to the cockpit's home, swapped in whole; its path."""
    path = saved_path(home, script["film"])
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(f".{os.getpid()}.partial")
    partial.write_text(json.dumps(script, indent=1) + "\n")
    partial.replace(path)
    return path


# The lock (CONTEXT.md "lock", "film script"): the creator's approval of a script, a copy of it as he locked it. The
# environment-film row reads only these (score/stages/demo_film/final.py), so a new lock moves its key.
LOCKED_FOLDER = "films/locked"
# The rows that film (the place films and the environment's cut): Buy refuses them while no script is locked.
FILM_STAGES = ("demo-film", "demo-film-extra", "environment-film")


def locked_path(home, film):
    return pathlib.Path(home) / LOCKED_FOLDER / f"{film}.json"


def locked(home, film):
    """The film's script as he locked it, or None while it is not locked."""
    path = locked_path(home, film)
    return json.loads(path.read_text()) if path.is_file() else None


def lock(home, script):
    """Keep the script as locked, swapped in whole; its path."""
    path = locked_path(home, script["film"])
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(f".{os.getpid()}.partial")
    partial.write_text(json.dumps(script, indent=1) + "\n")
    partial.replace(path)
    return path


def unlock(home, film):
    locked_path(home, film).unlink(missing_ok=True)


def locked_films(home, world):
    """The names of the environment's locked scripts, sorted."""
    folder = pathlib.Path(home) / LOCKED_FOLDER
    return sorted(path.stem for path in folder.glob("*.json")
                  if json.loads(path.read_text()).get("world") == world) if folder.is_dir() else []


def films_node(node):
    """Whether a node is one of the film rows (FILM_STAGES)."""
    return node.partition("@")[0] in FILM_STAGES


def default_name(repo, home, world):
    """The environment's own film: the script of it marked `"default": true` (a starter or his saved one), else
    `<world>-film`, built from default.py until he saves it."""
    for film in names(repo, home):
        found = read(repo, home, film)[0]
        if found.get("world") == world and found.get("default") is True:
            return film
    return f"{world}-film"
