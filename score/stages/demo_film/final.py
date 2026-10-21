"""environment-film: the environment's own final film, cut once from each film script the creator locked (CONTEXT.md
"film script", "lock": the Film step's Lock in the cockpit keeps a copy in the cockpit's home,
`$SCORE_DASHBOARD_HOME/films/locked/<film>.json`, on the store's machine, hosted through the sync) over its places'
accepted films; one environment node, free (a local cut with ffmpeg, no card), so the runner plans and prices it with
the films it reads (the paid demo-film and demo-film-extra rows). A new lock moves its key; the starters in
data/films/ and his unlocked edits are read by nothing here.

    files      every locked film script, the cut's tools and type (lettering.py), each script's sound bed (a
               library sound, `bed`) and, for a script with recorded segments (screen takes, physics animations,
               scale zooms), its free preview's record and each such segment's take
               (`$SCORE_DASHBOARD_HOME/films/previews/<film>.json`, `<film>-takes/<NNN>.mp4`)
    beside     demo-film@<place> and demo-film-extra@<place> for each place a script's walk-through or hero still
               shows (shown_places), each where that row applies

A script is cut only after the creator's yes, his lock: with none locked the node stands Blocked, and the free
preview is the FILM page's (score/dashboard/films). Before anything is cut every segment must say its `seconds` (a
final cut holds no default that could move under it) and be a cut this row makes (MADE: title and text cards, a
place's walk-through from its accepted film, a hero still from its film's first frame, and a recorded segment from
its take in the free preview: the cockpit's own page or the setting as the preview drew it, recorded from the very
segment the lock holds, else Blocked until the preview is rendered again), its walk-through's sound its place's own;
anything else is named and the node Blocked: those cuts need frames no row makes yet (exploded, isolate, layer focus
and split, step cards, before and after, orbit).

    make   per script, in a folder of its name: each segment's clip (a walk-through `seconds` of its film from the
           film's title card's end under a lower third, a hero still, a title or text card in the cockpit's type
           drawn on its clock (lettering.py), a recorded take; a walk-through's and a still's film brought to the
           films' middle brightness by one gain, matched_gain), a card's or take's sound the script's bed at its
           place on the film's clock, else the nearest film's), joined by half-second cross-fades
           (showcase.joined_in_groups), then graded (GRADE, the free preview's) and the whole film's sound brought
           to TARGET_LUFS by one gain (one loudness: never a level per segment), faded in and out; film.mp4 and
           timeline.json (each segment's cut, place, film node, start, seconds and exposure gain, and the gain).
    gate   film    each film: film_checks.video_checks (its script's size, a sound track, no black or frozen
                   stretch but a title or text card's own dark ground, its timeline's length within
                   LENGTH_SLACK), pacing (every place shown at least
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
from score.stages.demo_film import lettering
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
# The cockpit's home (score/dashboard/site/settings.py SCORE_HOME), the environment's `dashboard` root, and the locked
# scripts in it (score/dashboard/films/script.py LOCKED_FOLDER).
DASHBOARD = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", PROPS_HOME / "dashboard"))
LOCKED = "films/locked"
OWN, EXTRA = "demo-film", "demo-film-extra"
# The cuts this row makes from what its films hold; every other cut needs frames no row renders yet.
WORDS, WALK, STILL = ("title", "text"), "walk-through", "hero-still"
# The cuts the free preview records (the cockpit's own pages, the setting drawn from its physics), cut from its takes.
RECORDED = ("screen-take", "setting-animation", "scale-zoom")
MADE = (*WORDS, WALK, STILL, *RECORDED)
PREVIEWS = "films/previews"
# The free preview's grade (score/dashboard/films/preview/make.py GRADE), so the final looks as the preview did.
GRADE = "curves=master='0/0 0.25/0.23 0.5/0.5 0.75/0.77 1/1',vignette=angle=PI/7"
# A walk-through's or still's film is brought towards the films' middle brightness (mean luma over the part shown)
# by one gain, never past these, so a cut between two places does not jump in exposure.
GAIN_RANGE = (0.8, 1.25)
FILM_FADE = (0.6, 1.2)  # the whole film's sound fading in and out, seconds
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
    """Every locked film script, keyed `script <film>`, every tool file the cut is made with (the place films',
    showcase.py and the type), and each script's bed and recorded takes, so a lock or a change to them makes the film
    again."""
    tools = {f"tool {path}": "{repo}/" + path for path in (*demo_film.TOOLS, "tools/review/showcase.py",
                                                            "score/stages/demo_film/lettering.py")}
    found = {**tools, **lettering.FILES}
    for film, script in scripts().items():
        found[f"script {film}"] = "{dashboard}/" + f"{LOCKED}/{film}.json"
        found.update(recorded_files(film, script))
        if script.get("bed"):
            found[f"bed {film}"] = str(bed_file(script))
    return found


def recorded(script):
    """[(segment number from 1, segment)] of the segments the free preview records."""
    return [(number, segment) for number, segment in enumerate(script.get("segments", []), 1)
            if segment.get("cut") in RECORDED]


def recorded_files(film, script):
    """{name: pattern} of the free preview's record and its take of each recorded segment, for a script with any."""
    numbers = [number for number, _ in recorded(script)]
    if not numbers:
        return {}
    return {f"preview {film}": "{dashboard}/" + f"{PREVIEWS}/{film}.json",
            **{f"take {film} {number}": "{dashboard}/" + f"{PREVIEWS}/{film}-takes/{number:03d}.mp4"
               for number in numbers}}


def bed_file(script):
    """The script's sound bed: the library sound it names (`bed`, "sound/<entry>"), its newest version in the library
    cache, its made take first (as the free preview takes it); a path that does not exist where none is cached, which
    the runner names as a missing input."""
    entry = str(script["bed"]).partition("/")[2]
    root = PROPS_HOME / "cache/library/score_lib/sound" / entry
    versions = sorted((path for path in root.glob("*") if path.name.isdigit()), key=lambda path: int(path.name))
    found = sorted(versions[-1].glob("audio/**/*.wav"), key=lambda path: "made" not in path.parts) if versions else []
    return found[0] if found else root / "missing.wav"


def takes(film, script, inputs):
    """{segment number: its take} of the script's recorded segments from the free preview among the node's inputs;
    Blocked naming each segment the preview recorded from another script, size or rate than the lock holds."""
    numbers = recorded(script)
    if not numbers:
        return {}
    made = json.loads(pathlib.Path(inputs[f"preview {film}"]).read_text()).get("script", {})
    same = all(made.get(key, default) == script.get(key, default) for key, default in (("size", [1280, 720]),
                                                                                        ("rate", 24)))
    stale = [number for number, segment in numbers
             if not same or len(made.get("segments", [])) < number or made["segments"][number - 1] != segment]
    if stale:
        raise graph.Blocked(f"{film}: segment(s) {', '.join(map(str, stale))} of the free preview were recorded from "
                            "another script than the lock: render the preview again")
    return {number: pathlib.Path(inputs[f"take {film} {number}"]) for number, _ in numbers}


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
    found = [] if shown(script) or script.get("bed") else ["it shows no place's film and names no bed"]
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


def mean_luma(video, start, seconds):
    """The video's mean luma (0 to 255) over `seconds` from `start`, two frames a second."""
    _, _, film_checks = cut_tools()
    found = re.findall(r"YAVG=([\d.]+)", film_checks.filtered(
        video, f"trim=duration={seconds:.3f},fps=2,scale=320:-2,signalstats,"
        "metadata=print:key=lavfi.signalstats.YAVG", start=start))
    if not found:
        raise RuntimeError(f"no luma measured in {video}")
    return sum(map(float, found)) / len(found)


def matched_gain(luma, middle):
    """The gain bringing a film of mean `luma` to the films' `middle`, within GAIN_RANGE (luma above video black)."""
    return round(min(GAIN_RANGE[1], max(GAIN_RANGE[0], (middle - 16.0) / max(luma - 16.0, 1.0))), 3)


def gained(film, gain, out):
    """`film` with its picture multiplied by `gain` (its sound copied), or `film` itself at a gain of 1."""
    if abs(gain - 1.0) < 1e-3:
        return film
    demo, _, _ = cut_tools()
    demo.ffmpeg("-i", film, "-vf", f"colorchannelmixer=rr={gain}:gg={gain}:bb={gain}", "-c:a", "copy", "-c:v",
                "libx264", "-crf", "12", "-pix_fmt", "yuv420p", out)
    return out


def card_clip(segment, seconds, silent):
    """A title or text card in the cockpit's type, drawn on its clock (lettering.card_frame)."""
    _, showcase, _ = cut_tools()
    ground = lettering.card_ground((showcase.W, showcase.H))
    showcase.write_frames(lambda number, count: lettering.card_frame(
        ground, segment.get("text") or "", segment.get("line") or "", number / showcase.RATE, seconds).convert("RGB"),
        seconds, silent)


def under_layer(video, layer, seconds, out):
    """A silent `video` under `layer` (an RGBA picture), the layer fading in and out as a place's caption does."""
    demo, _, _ = cut_tools()
    still = pathlib.Path(out).with_suffix(".layer.png")
    layer.save(still)
    chain = (f"[1:v]format=rgba,fade=t=in:st=0.3:d=0.6:alpha=1,fade=t=out:st={seconds - 0.9:.3f}:d=0.6:alpha=1[l];"
             "[0:v][l]overlay=format=auto[v]")
    demo.ffmpeg("-i", video, "-loop", "1", "-t", f"{seconds:.3f}", "-i", still, "-filter_complex", chain, "-map", "[v]",
                *demo.encode(out))
    still.unlink()


def picture_clip(segment, source, out, parts):
    """One segment's picture with its sound: a walk-through of its film under a lower third (its own sound), else a
    silent clip (a hero still from its film's first frame, a recorded take, or a card); whether it carries sound."""
    demo, showcase, _ = cut_tools()
    from PIL import Image
    seconds = float(segment["seconds"])
    layer = lettering.lower_third((showcase.W, showcase.H), segment.get("line") or "", segment.get("text") or "")
    if segment["cut"] == WALK:
        showcase.result_clip(source, seconds, layer, out)
        return True
    if segment["cut"] == STILL:
        first, held = parts / f"{out.stem}-first.png", parts / f"{out.stem}-held.mp4"
        demo.ffmpeg("-ss", f"{demo.TITLE_SECONDS:.3f}", "-i", source, "-frames:v", "1", first)
        showcase.still_clip(Image.open(first).convert("RGB"), seconds, held)
        under_layer(held, layer, seconds, out)
    elif segment["cut"] in RECORDED:
        demo.ffmpeg("-i", source, "-t", f"{seconds:.3f}", "-vf", f"scale={showcase.W}:{showcase.H}:flags=lanczos",
                    "-an", *demo.encode(out))
    else:
        card_clip(segment, seconds, out)
    return False


def script_bed(bed, start, seconds, out):
    """`seconds` of the script's bed from `start` on the film's clock (the bed looping), so the cards' and takes'
    sound runs on unbroken across their cross-fades."""
    demo, _, _ = cut_tools()
    demo.ffmpeg("-stream_loop", "-1", "-ss", f"{start:.3f}", "-i", bed, "-t", f"{seconds:.3f}", "-ac", "2", "-ar",
                demo.SAMPLE_RATE, "-c:a", "aac", "-b:a", "160k", out)


def segment_clip(segment, source, out, parts, sound):
    """One segment's clip with its sound: its picture (picture_clip), and, where that has none, `sound(seconds, path)`
    under it (the script's bed or a film's), or silence; its length in seconds."""
    _, showcase, _ = cut_tools()
    seconds = float(segment["seconds"])
    silent = parts / f"{out.stem}-picture.mp4"
    if picture_clip(segment, source, silent, parts):
        silent.replace(out)
    elif segment.get("sound") == "silence":
        showcase.silence_under(silent, seconds, out)
    else:
        sound(seconds, parts / f"{out.stem}-bed.m4a")
        showcase.sound.with_sound(silent, parts / f"{out.stem}-bed.m4a", out)
    return seconds


def integrated_loudness(video):
    """The video's integrated loudness (EBU R128, ffmpeg's ebur128), LUFS; None for a film with no sound."""
    _, _, film_checks = cut_tools()
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", film_checks.filtered(video, "ebur128", audio=True))
    return float(found[-1]) if found else None


def one_loudness(joined, out, size, seconds):
    """The joined film written at its script's `size` (showcase's clips are 1920x1080) under the one GRADE, its whole
    sound moved by one gain to TARGET_LUFS, never a level per segment, and faded in and out over its `seconds`; the
    gain."""
    demo, _, _ = cut_tools()
    loudness = integrated_loudness(joined)
    if loudness is None:
        raise RuntimeError(f"{joined} has no sound to bring to one loudness")
    gain = TARGET_LUFS - loudness
    fades = f"afade=t=in:d={FILM_FADE[0]},afade=t=out:st={max(0.0, seconds - FILM_FADE[1]):.3f}:d={FILM_FADE[1]}"
    demo.ffmpeg("-i", joined, "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos,{GRADE}", "-af",
                f"volume={gain:.2f}dB,alimiter=limit=0.891,{fades}", "-c:a", "aac", "-b:a", "160k", *demo.encode(out))
    return round(gain, 2)


def gains(script, films):
    """{segment number: its exposure gain} of the segments showing a film ({segment number: film.mp4}), each film's
    mean luma over the part it shows brought to the middle of theirs (matched_gain)."""
    demo, _, _ = cut_tools()
    lumas = {number: mean_luma(films[number], demo.TITLE_SECONDS, float(segment["seconds"]))
             for number, segment in shown(script) if number in films}
    if not lumas:
        return {}
    ordered = sorted(lumas.values())
    middle = ordered[len(ordered) // 2]
    return {number: matched_gain(luma, middle) for number, luma in lumas.items()}


def cut_one(script, films, out, recorded_takes=None, bed=None):
    """One script's film and its timeline in `out`, from its segments' films ({segment number: film.mp4}), its
    recorded segments' takes ({segment number: take.mp4}) and its `bed` (a card's and take's sound; else the nearest
    film's)."""
    _, showcase, _ = cut_tools()
    parts = out / ".parts"
    parts.mkdir(parents=True, exist_ok=True)
    exposure = gains(script, films)
    clips, lengths, timeline, clock = [], [], [], 0.0
    for number, segment in enumerate(script["segments"], 1):
        clip = parts / f"segment-{number:03d}.mp4"
        near = nearest(films, number) if films else None
        source = (recorded_takes or {}).get(number) or (
            gained(films[number], exposure[number], parts / f"matched-{number:03d}.mp4") if number in films else near)
        start = clock
        sound = ((lambda seconds, path, start=start: script_bed(bed, start, seconds, path)) if bed else
                 (lambda seconds, path, near=near: showcase.bed_track(near, seconds, path)))
        lengths.append(segment_clip(segment, source, clip, parts, sound))
        clips.append(clip)
        node = film_node(segment)[0] if number in films else None
        timeline.append({"segment": number, "cut": segment["cut"], "place": (segment.get("shows") or {}).get("place"),
                         "film": node, "start": round(clock, 3), "seconds": lengths[-1],
                         "exposure_gain": exposure.get(number, 1.0)})
        clock += lengths[-1] - TRANSITION_SECONDS
    showcase.joined_in_groups(clips, lengths, parts / "joined.mp4", parts)
    size = script.get("size", [1280, 720])
    gain = one_loudness(parts / "joined.mp4", out / "film.mp4", size, clock + TRANSITION_SECONDS)
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
    recorded_takes = {film: takes(film, script, inputs) for film, script in sorted(named.items())}
    for film, script in sorted(named.items()):
        bed = inputs.get(f"bed {film}")
        cut_one(script, films[film], pathlib.Path(out) / film, recorded_takes[film], pathlib.Path(bed) if bed else None)


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
    black = unplanned_black(video["black"], timeline["segments"])
    found = [fault for fault in video["failures"] if not fault.startswith("black ")] + (
        [f"black {black}"] if black else [])
    return [f"{folder.name}: {fault}" for fault in found + pacing_faults(timeline["segments"]) + loud]


def unplanned_black(stretches, segments):
    """The black stretches ([[start, end]], seconds) not lying within a title or text card: a card's words rise in on
    its dark ground by plan, so only black elsewhere is a fault."""
    cards = [(segment["start"], segment["start"] + segment["seconds"]) for segment in segments
             if segment.get("cut") in WORDS]
    return [stretch for stretch in stretches
            if not any(start - 1e-3 <= stretch[0] and stretch[1] <= end + 1e-3 for start, end in cards)]


def judge(output, inputs, evidence):
    folders = sorted(path for path in pathlib.Path(output).iterdir() if path.is_dir())
    faults = [fault for folder in folders for fault in film_faults(folder)]
    return checks.Verdict("film", checks.FAIL if faults else checks.PASS,
                          "; ".join(faults[:3]) if faults else f"{len(folders)} film(s) paced, at one loudness",
                          {"films": len(folders), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("film", judge),)
