"""environment-film: the environment's own final film, cut once from each film script the creator locked (CONTEXT.md
"film script", "lock": the Film step's Lock in the cockpit keeps a copy in the cockpit's home,
`$SCORE_DASHBOARD_HOME/films/locked/<film>.json`, on the store's machine, hosted through the sync) over its places'
accepted films; one environment node, free (a local cut with ffmpeg, no card), so the runner plans and prices it with
the films it reads (the paid demo-film and demo-film-extra rows). A new lock moves its key; the starters in
data/films/ and his unlocked edits are read by nothing here.

    files      every locked film script, and the cut's tools
    beside     demo-film@<place> and demo-film-extra@<place> for each place a script's walk-through or hero still
               shows (shown_places), each where that row applies

A script is cut only after the creator's yes, his lock: with none locked the node stands Blocked, and the free
preview is the FILM page's (score/dashboard/films). Before anything is cut every segment must say its `seconds` (a
final cut holds no default that could move under it) and be a cut this row makes (MADE: title and text cards, a
place's walk-through from its accepted film, a hero still from its film's first frame), its walk-through's sound its
place's own; anything else is named and the node Blocked: those cuts need frames no row makes yet (exploded, isolate,
layer focus and split, step cards, before and after, orbit).

    make   per script, in a folder of its name: each segment's clip (showcase.py's card, still and film clips: a
           walk-through `seconds` of its film from the film's title card's end, a card on the bed of the nearest
           film's sound), joined by half-second cross-fades (showcase.joined_in_groups), then the whole film's sound
           brought to TARGET_LUFS by one gain (one loudness: never a level per segment); film.mp4 and
           timeline.json (each segment's cut, place, film node, start and seconds, and the gain).
    gate   film    each film: film_checks.video_checks (its script's size, a sound track, no black or frozen
                   stretch, its timeline's length within LENGTH_SLACK), pacing (every place shown at least
                   PLACE_SECONDS and every walk-through at least SHOT_SECONDS, the owner's 3.5 s a place too fast)
                   and its integrated loudness within LOUDNESS_SLACK of TARGET_LUFS. Nothing passing through the
                   camera, people in view and every event's sound are the place films' own gate (demo-film), and this
                   node reads only films that passed it.
"""
import json
import os
import pathlib
import re
import shutil
import sys

from score import checks, contracts, graph
from score.stages import demo_film
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
# The cockpit's home (score/dashboard/site/settings.py SCORE_HOME), the environment's `dashboard` root, and the locked
# scripts in it (score/dashboard/films/script.py LOCKED_FOLDER).
DASHBOARD = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", PROPS_HOME / "dashboard"))
LOCKED = "films/locked"
OWN, EXTRA = "demo-film", "demo-film-extra"
# The cuts this row makes from what its films hold; every other cut needs frames no row renders yet.
WORDS, WALK, STILL = ("title", "text"), "walk-through", "hero-still"
MADE = (*WORDS, WALK, STILL)
# The owner's review of 2026-10-18: 3.5 s a place cut far too fast; a place on screen about 7 s, in two steady shots.
PLACE_SECONDS = 7.0
SHOT_SECONDS = 3.5
# One loudness for the whole film: its integrated loudness (EBU R128) set once, a common level for films on the web.
TARGET_LUFS = -16.0
LOUDNESS_SLACK = 1.0
LENGTH_SLACK = 1.0
TRANSITION_SECONDS = 0.5  # demo.FADE_SECONDS, every join's cross-fade
OUTPUTS = ("film.mp4", "timeline.json")


def scripts():
    """{film: its script} of every locked film script."""
    return {path.stem: json.loads(path.read_text()) for path in sorted((DASHBOARD / LOCKED).glob("*.json"))}


def files(place=None):
    """Every locked film script, keyed `script <film>`, and every tool file the cut is made with (the place films'
    and showcase.py), so a lock or a change to them makes the film again."""
    tools = {f"tool {path}": "{repo}/" + path for path in (*demo_film.TOOLS, "tools/review/showcase.py")}
    return {**tools, **{f"script {film}": "{dashboard}/" + f"{LOCKED}/{film}.json" for film in scripts()}}


def shown(script):
    """[(segment number from 1, segment)] of the segments that show a place's film: walk-throughs and hero stills."""
    return [(number, segment) for number, segment in enumerate(script.get("segments", []), 1)
            if segment.get("cut") in (WALK, STILL) and (segment.get("shows") or {}).get("place")]


def shown_places(place=None):
    """The places every script's films show, sorted: the node's beside reads."""
    return sorted({segment["shows"]["place"] for script in scripts().values() for _, segment in shown(script)})


def film_node(segment):
    """(the node whose output holds the segment's film, the folder inside it): a place's own film, or the extra film
    the segment names."""
    shows = segment["shows"]
    if shows.get("film"):
        return f"{EXTRA}@{shows['place']}", shows["film"]
    return f"{OWN}@{shows['place']}", ""


def require_yes(named):
    """Blocked while no script is locked (`named` {film: script}, the locked ones): the lock is the creator's yes."""
    if not named:
        raise graph.Blocked("no film script locked: play it free on the Film step, then lock it")


def plan_faults(script):
    """What keeps a script from being cut by this row, in words: a segment without its `seconds`, a cut this row does
    not make, a walk-through whose sound is not its place's own, a script that shows no place's film (its cards'
    sound and backdrop come from the films)."""
    found = [] if shown(script) else ["it shows no place's film"]
    for number, segment in enumerate(script.get("segments", []), 1):
        cut = segment.get("cut")
        if not isinstance(segment.get("seconds"), (int, float)):
            found.append(f"segment {number} ({cut}) names no seconds")
        if cut not in MADE:
            found.append(f"segment {number}: no row makes {cut} frames yet")
        elif cut == WALK and segment.get("sound", "place") != "place":
            found.append(f"segment {number}: a walk-through plays its place's own sound, not {segment.get('sound')}")
    return found


def pacing_faults(segments):
    """The owner's pacing as faults: a walk-through under SHOT_SECONDS, a place shown under PLACE_SECONDS in all
    (its walk-throughs summed). `segments` [{"cut", "place", "seconds"}]."""
    walks = [segment for segment in segments if segment.get("cut") == WALK]
    found = [f"{segment['place']}: a walk-through of {segment['seconds']:g} s, under {SHOT_SECONDS:g} s"
             for segment in walks if segment["seconds"] < SHOT_SECONDS]
    shown_for = {}
    for segment in walks:
        shown_for[segment["place"]] = shown_for.get(segment["place"], 0.0) + segment["seconds"]
    return found + [f"{place}: on screen {seconds:g} s, under {PLACE_SECONDS:g} s"
                    for place, seconds in shown_for.items() if seconds < PLACE_SECONDS - 1e-6]


def script_segments(script):
    """[{"cut", "place", "seconds"}] of a script's segments, as pacing_faults reads them."""
    return [{"cut": segment.get("cut"), "place": (segment.get("shows") or {}).get("place"),
             "seconds": float(segment.get("seconds") or 0.0)} for segment in script.get("segments", [])]


def named_scripts(inputs):
    """{film: script} of the scripts among the node's inputs."""
    return {name.removeprefix("script "): json.loads(pathlib.Path(path).read_text())
            for name, path in inputs.items() if name.startswith("script ")}


def cut_tools():
    """(demo, showcase, film_checks) of tools/review, imported with their folders on the path, put back after."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools/review"), str(REPO / "tools/usd")]
    try:
        import demo
        import film_checks
        import showcase
    finally:
        sys.path[:] = kept
    return demo, showcase, film_checks


def sources(script, inputs):
    """{segment number: its film.mp4} for every segment showing a film, read from the node's beside checkouts;
    Blocked naming each film the node does not hold or that is too short for its segment."""
    demo, showcase, _ = cut_tools()
    found, missing = {}, []
    for number, segment in shown(script):
        node, folder = film_node(segment)
        film = pathlib.Path(inputs[node]) / folder / "film.mp4" if node in inputs else None
        if film is None or not film.exists():
            missing.append(f"segment {number}: no accepted film {node}{'/' + folder if folder else ''}")
        elif segment["cut"] == WALK and showcase.length(film) - demo.TITLE_SECONDS < segment["seconds"] - 1e-3:
            missing.append(f"segment {number}: {node} shows {showcase.length(film) - demo.TITLE_SECONDS:.2f} s, "
                           f"the segment wants {segment['seconds']:g}")
        else:
            found[number] = film
    if missing:
        raise graph.Blocked("; ".join(missing))
    return found


def nearest(films, number):
    """The film of the segment nearest `number`, the later one on a tie: a card's sound bed and backdrop."""
    return films[min(films, key=lambda other: (abs(other - number), -other))]


def segment_clip(segment, film, out, parts):
    """One segment's clip with its sound: a card on the bed of `film`, a walk-through of `film`, or its first frame
    held; its length in seconds."""
    demo, showcase, _ = cut_tools()
    from PIL import Image
    seconds, words = float(segment["seconds"]), [line for line in (segment.get("text"), segment.get("line")) if line]
    if segment["cut"] == WALK:
        showcase.result_clip(film, seconds, showcase.caption_layer(words), out)
        return seconds
    silent = parts / f"{out.stem}-picture.mp4"
    first = parts / f"{out.stem}-first.png"
    demo.ffmpeg("-ss", f"{demo.TITLE_SECONDS:.3f}", "-i", film, "-frames:v", "1", first)
    if segment["cut"] == STILL:
        showcase.still_clip(Image.open(first), seconds, silent, words)
    else:
        showcase.card(words or [""], [(72, "Medium"), (40, "Light")][:max(1, len(words))], seconds, silent, first)
    if segment.get("sound") == "silence":
        showcase.silence_under(silent, seconds, out)
    else:
        showcase.bed_track(film, seconds, parts / f"{out.stem}-bed.m4a")
        showcase.sound.with_sound(silent, parts / f"{out.stem}-bed.m4a", out)
    return seconds


def integrated_loudness(video):
    """The video's integrated loudness (EBU R128, ffmpeg's ebur128), LUFS; None for a film with no sound."""
    _, _, film_checks = cut_tools()
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", film_checks.filtered(video, "ebur128", audio=True))
    return float(found[-1]) if found else None


def one_loudness(joined, out, size):
    """The joined film written at its script's `size` (showcase's clips are 1920x1080), its whole sound moved by one
    gain to TARGET_LUFS, never a level per segment; the gain."""
    demo, _, _ = cut_tools()
    loudness = integrated_loudness(joined)
    if loudness is None:
        raise RuntimeError(f"{joined} has no sound to bring to one loudness")
    gain = TARGET_LUFS - loudness
    demo.ffmpeg("-i", joined, "-vf", f"scale={size[0]}:{size[1]}", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.891",
                "-c:a", "aac", "-b:a", "160k", *demo.encode(out))
    return round(gain, 2)


def cut_one(script, films, out):
    """One script's film and its timeline in `out`, from its segments' films ({segment number: film.mp4})."""
    _, showcase, _ = cut_tools()
    parts = out / ".parts"
    parts.mkdir(parents=True, exist_ok=True)
    clips, lengths, timeline, clock = [], [], [], 0.0
    for number, segment in enumerate(script["segments"], 1):
        clip = parts / f"segment-{number:03d}.mp4"
        lengths.append(segment_clip(segment, films.get(number) or nearest(films, number), clip, parts))
        clips.append(clip)
        node = film_node(segment)[0] if number in films else None
        timeline.append({"segment": number, "cut": segment["cut"], "place": (segment.get("shows") or {}).get("place"),
                         "film": node, "start": round(clock, 3), "seconds": lengths[-1]})
        clock += lengths[-1] - TRANSITION_SECONDS
    showcase.joined_in_groups(clips, lengths, parts / "joined.mp4", parts)
    size = script.get("size", [1280, 720])
    gain = one_loudness(parts / "joined.mp4", out / "film.mp4", size)
    (out / "timeline.json").write_text(json.dumps({"film": script["film"], "size": size,
                                                   "seconds": round(clock + TRANSITION_SECONDS, 3), "gain_db": gain,
                                                   "segments": timeline}, indent=1))
    shutil.rmtree(parts)


def make(inputs, out, seed, params):
    """Every script's film, each in a folder of its name (module docstring)."""
    named = named_scripts(inputs)
    require_yes(named)
    faults = [f"{film}: {fault}" for film, script in sorted(named.items()) for fault in plan_faults(script)]
    if faults:
        raise graph.Blocked("; ".join(faults))
    films = {film: sources(script, inputs) for film, script in sorted(named.items())}  # every film found first
    for film, script in sorted(named.items()):
        cut_one(script, films[film], pathlib.Path(out) / film)


def output_faults(folder):
    filmed = [path for path in pathlib.Path(folder).iterdir() if path.is_dir()]
    return [f"{path.name}: no {name}" for path in filmed for name in OUTPUTS if not (path / name).exists()] or (
        [] if filmed else ["no film"])


CONTRACT = contracts.Contract("environment-film", 1, output_faults, {"time": "second"})


def film_faults(folder):
    """One cut film's faults: its video checks, pacing and loudness."""
    _, _, film_checks = cut_tools()
    timeline = json.loads((folder / "timeline.json").read_text())
    video = film_checks.video_checks(folder / "film.mp4", timeline["seconds"] - LENGTH_SLACK,
                                     timeline["seconds"] + LENGTH_SLACK, 0.0, tuple(timeline["size"]))
    loudness = integrated_loudness(folder / "film.mp4")
    loud = [] if loudness is not None and abs(loudness - TARGET_LUFS) <= LOUDNESS_SLACK else [
        f"loudness {loudness} LUFS, not {TARGET_LUFS:g} within {LOUDNESS_SLACK:g}"]
    return [f"{folder.name}: {fault}" for fault in video["failures"] + pacing_faults(timeline["segments"]) + loud]


def judge(output, inputs, evidence):
    folders = sorted(path for path in pathlib.Path(output).iterdir() if path.is_dir())
    faults = [fault for folder in folders for fault in film_faults(folder)]
    return checks.Verdict("film", checks.FAIL if faults else checks.PASS,
                          "; ".join(faults[:3]) if faults else f"{len(folders)} film(s) paced, at one loudness",
                          {"films": len(folders), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("film", judge),)
