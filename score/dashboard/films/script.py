"""The film script's words, defaults and checks, and where its file lives (the package docstring has the format).
Plain Python only: the hosted process reads it too."""
import json
import os
import pathlib
import re

FORMAT = "score-film-script"
VERSION = 1
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
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
TARGET_SECONDS = 180

# Each cut type: its words, its default length, what it must name besides what it shows, and its usual transition
# and sound. A walk-through is 3.5 s by default because that is the shot every accepted film already holds.
CUTS = {
    "walk-through": {"label": "Walk-through", "seconds": FILM_SHOT_SECONDS, "needs": ("place",),
                     "transition": "cross-fade", "sound": "place",
                     "words": "the camera's path through the place"},
    "orbit": {"label": "Orbit", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade", "sound": "bed",
              "words": "a slow circle round the whole place"},
    "hero-still": {"label": "Hero still", "seconds": 3.0, "needs": ("place",), "transition": "cross-fade",
                   "sound": "bed", "words": "one picture held, slowly closing in"},
    "exploded": {"label": "Exploded view", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade",
                 "sound": "bed", "words": "the room split apart into its parts"},
    "isolate": {"label": "Isolate a part", "seconds": 4.0, "needs": ("place", "part"), "transition": "cross-fade",
                "sound": "bed", "words": "zoom in on one part, the rest falls away"},
    "layer-focus": {"label": "Layer focus", "seconds": 4.0, "needs": ("place", "layer"), "transition": "cross-fade",
                    "sound": "bed", "words": "one OpenUSD layer lit, the others ghosted"},
    "layer-split": {"label": "Layer split", "seconds": 6.0, "needs": ("place",), "transition": "cross-fade",
                    "sound": "bed", "words": "the layer stack lifted apart"},
    "step-card": {"label": "Step card", "seconds": 3.0, "needs": ("place", "step"), "transition": "push",
                  "sound": "bed", "words": "a framework step's own pictures"},
    "before-after": {"label": "Before and after", "seconds": 4.0, "needs": ("place",), "transition": "cross-fade",
                     "sound": "bed", "words": "the concept wiped into the result"},
    "title": {"label": "Title card", "seconds": 4.0, "needs": (), "transition": "fade-through-black",
              "sound": "bed", "words": "the film's title"},
    "text": {"label": "Text card", "seconds": 3.0, "needs": (), "transition": "cross-fade", "sound": "bed",
             "words": "a line of words"},
}
TRANSITIONS = {"cut": "Cut", "cross-fade": "Cross-fade", "fade-through-black": "Fade through black",
               "push": "Push"}
OVERLAPPING = ("cross-fade", "push")
SOUNDS = {"place": "The place's own sound", "bed": "Sound bed (nearest film)", "silence": "Silence"}
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
    if segment.get("transition", "cut") not in TRANSITIONS:
        found.append(f"segment {number}: no transition {segment.get('transition')!r}")
    if segment.get("sound", "bed") not in SOUNDS:
        found.append(f"segment {number}: no sound {segment.get('sound')!r}")
    length = segment.get("seconds")
    if length is not None and not (isinstance(length, (int, float)) and SHORTEST <= length <= LONGEST):
        found.append(f"segment {number}: {length!r} s is not between {SHORTEST} and {LONGEST}")
    return found


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
        found += [f"segment {number}: no place {segment['shows']['place']!r}"
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
