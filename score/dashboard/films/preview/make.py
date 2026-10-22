"""The free preview of a film script, end to end, rendered on the store's machine (`python -m score.dashboard
film-preview <film>`): nothing rented, nothing bought, no button that spends ever clicked.

1. The cockpit the takes record: the hosted cockpit as the owner sees it, served on loopback from a state export (built
   now from the store by the export command, or `--export` an existing one) in a home of its own under the preview's
   work folder, signed in as the owner by the trusted proxy's header; its film scripts are this checkout's and the
   cockpit home's.
2. Every segment drawn frame by frame in headless Chromium (recorder.mjs): a screen take on its cockpit page, a setting
   animation or a scale zoom by scene.js (scenes.py works out what it shows), any other cut through the FILM page's
   own player at its moment; each segment's captions and picture-in-picture over it.
3. Each segment's frames made a clip (kept in `<film>-takes/`, where the environment-film row cuts its recorded
   segments from), the clips joined by the script's transitions on its clock (script.timeline) under one grade (GRADE:
   a gentle contrast curve, the same for every segment), the sound bed (the bed the sound stage
   made from the design for the first place the film shows, bed_sound; silence, WAITING_BED, while none is made) under
   the whole film at one loudness, started where its strongest onsets fall on the cuts (beat_offset), silence
   where a segment says so.

Out: `$SCORE_DASHBOARD_HOME/films/previews/<film>.mp4` and `<film>.json` (the script it was made from, made_at, each
segment's start, seconds and clip, whose bed it plays and where it starts), which the FILM page plays and the export carries (not the
takes folder).
"""
import datetime
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

from django.conf import settings

from score.dashboard.films import script, takes
from score.dashboard.films.preview import scenes

PLAYWRIGHT = "playwright@1.62.1"  # viewer_look.py's: its Chromium (1234) is the one installed in ~/.cache/ms-playwright
HERE = pathlib.Path(__file__).resolve().parent
FOLDER = "films/previews"
SCALE = 2  # each frame drawn at twice its size and brought down to it, so the cockpit's text stays sharp
TARGET_LUFS = -16.0  # demo_film/final.py's TARGET_LUFS: one loudness for the whole film
BED_FADE = (1.0, 2.0)
WAITING_BED = "waiting on the sound bed"  # the record's and the run's word while no scene's bed is made: silence
# The film's one grade, every segment alike: a gentle S curve (shadows down, highlights up a little);
# nothing added to what is shown. demo_film/final.py grades the environment film the same way.
GRADE = "curves=master='0/0 0.25/0.23 0.5/0.5 0.75/0.77 1/1'"  # no vignette (owner 2026-10-21)
# A bed's onsets are found on hops of a frame; a start is taken only when its onsets on the cuts stand this many
# deviations over the average start's (a steady hum has none, and starts at 0).
ONSET_RATE = 12000
BEAT_STANDOUT = 3.0
XFADES = {"cross-fade": "fade", "push": "slideleft"}
BLACK_HALF = script.TRANSITION_SECONDS / 2
THREE = "https://cdnjs.cloudflare.com/ajax/libs/three.js/0.170.0/three.module.min.js"  # the FILM page's own
SCENE_HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="/static/design/fonts/poppins/poppins.css">
<style>
html, body { margin: 0; width: 100vw; height: 100vh; overflow: hidden; background: #05060a; font-family: Poppins, system-ui, sans-serif; }
#views .view { position: absolute; inset: 0; width: 100vw !important; height: 100vh !important; }
.rooms .room { position: absolute; inset: 0; overflow: hidden; }
.rooms img { width: 100%; height: 100%; object-fit: cover; transform-origin: 50% 55%; }
.rooms span { position: absolute; left: 48px; top: 40px; font-size: 22px; font-weight: 600; color: #f4f2fa;
  background: rgba(10, 11, 16, .7); padding: 6px 16px; border-radius: 10px; }
#labels { position: absolute; inset: 0; pointer-events: none; z-index: 50; }
.label { position: absolute; transform: translate(-50%, 0); color: #e9e7f3; font-size: 16px; font-weight: 600;
  text-shadow: 0 1px 4px #000; white-space: nowrap; }
.label.block { font-size: 13px; background: rgba(10, 11, 16, .72); padding: 2px 9px; border-radius: 6px; transform: translate(-50%, -100%); }
.label.site { color: #c9b5ff; font-size: 18px; }
.label.note { left: auto !important; right: 40px; top: auto !important; bottom: 30px; transform: none; font-size: 13px; color: #a9a6bd; font-weight: 400; }
#tag { position: absolute; z-index: 60; right: 40px; top: 34px; font-size: 13px; color: #f4f2fa; background: rgba(10, 11, 16, .72);
  border: 1px solid rgba(185, 156, 255, .6); padding: 5px 12px; border-radius: 8px; }
</style>
<script type="importmap">{"imports": {"three": "%THREE%"}}</script>
</head><body><div id="views"></div><div id="labels"></div><div id="tag" hidden></div>
<script type="module" src="/__film/scene.js"></script></body></html>
""".replace("%THREE%", THREE)


class Refused(Exception):
    """The preview is not made, with why in words."""


def preview_paths(home, film):
    """(the film's preview, its record) in the cockpit home."""
    folder = pathlib.Path(home) / FOLDER
    return folder / f"{film}.mp4", folder / f"{film}.json"


def takes_folder(home, film):
    """The folder of the preview's segment clips: `<film>-takes/<NNN>.mp4`, segment numbers from 1."""
    return pathlib.Path(home) / FOLDER / f"{film}-takes"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def owner_name():
    """The name the takes sign in as: SCORE_OWNER, else the local owner account, else "owner"."""
    if settings.SCORE_OWNER:
        return settings.SCORE_OWNER
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(is_superuser=True).values_list("username", flat=True).first() or "owner"


def built_export(out):
    """A fresh state export of the store into `out`, by the export command itself; its folder."""
    from score.dashboard import __main__ as commands
    commands.export(str(out))
    return pathlib.Path(out)


def cockpit_home(work, export, film):
    """The recorded cockpit's own home: the export as its current one, the film's saved script beside."""
    home = work / "cockpit"
    (home / "export").mkdir(parents=True, exist_ok=True)
    current = home / "export" / "current"
    if current.is_symlink() or current.exists():
        current.unlink()
    current.symlink_to(pathlib.Path(export).resolve())
    saved = script.saved_path(settings.SCORE_HOME, film)
    if saved.is_file():
        (home / "films").mkdir(exist_ok=True)
        shutil.copyfile(saved, home / "films" / saved.name)
    return home


def started_cockpit(home, user):
    """(the hosted-mode cockpit serving `home` on a free loopback port, its address); waits until it answers."""
    port = free_port()
    environment = {**os.environ, "SCORE_DASHBOARD_MODE": "hosted", "SCORE_DASHBOARD_HOME": str(home),
                   "SCORE_BIND": f"127.0.0.1:{port}", "SCORE_TRUSTED_PROXIES": "127.0.0.1/32",
                   "SCORE_ALLOWED_USERS": user, "SCORE_OWNER": user}
    log = open(home / "serve.log", "w")
    server = subprocess.Popen([sys.executable, "-m", "score.dashboard", "serve"], cwd=settings.SCORE_REPO,
                              env=environment, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=2):
                return server, base
        except OSError:
            if server.poll() is not None:
                raise Refused(f"the cockpit to record did not start: see {home / 'serve.log'}")
            time.sleep(0.5)
    server.terminate()
    raise Refused("the cockpit to record did not answer in 60 s")


def pip_of(state, segment):
    """A segment's picture-in-picture with its link resolved, or None."""
    pip = segment.get("pip")
    if not pip:
        return None
    url = pip.get("picture") or scenes.picked_url(state, pip["concept"])
    if not url:
        raise Refused(f"no concept of {pip['concept']} to show in a corner")
    return {"url": url, "corner": pip.get("corner", "top-right"), "label": pip.get("label", ""),
            "from": float(pip.get("from", 0.0)), "to": float(pip.get("to", 1e9))}


def job_segment(film_script, state, index, segment, start, seconds, work):
    """What the recorder makes of one segment."""
    shown = {"index": index + 1, "seconds": seconds, "out": str(work / f"{index + 1:03d}"),
             "captions": segment.get("captions", []), "pip": pip_of(state, segment)}
    cut = segment["cut"]
    if cut == "screen-take":
        return {**shown, "kind": "take", "page": segment["shows"]["page"], "take": segment.get("take", []),
                "view": segment.get("view")}
    if cut in ("setting-animation", "scale-zoom"):
        return {**shown, "kind": "scene", "scene": scenes.scene_for(state, {**segment, "seconds": seconds},
                                                                    float(film_script.get("rate", 24)))}
    return {**shown, "kind": "player", "page": f"/film/{film_script['film']}/", "start": start}


def recorded(job, work):
    """Run the recorder over the job; each segment's frame folder. Refused with the recorder's words."""
    listing = work / "job.json"
    listing.write_text(json.dumps(job))
    done = subprocess.run(["npx", "-y", "-p", PLAYWRIGHT, "node", str(HERE / "recorder.mjs"), str(listing)],
                          capture_output=True, text=True)
    (work / "recorder.log").write_text(done.stdout + done.stderr)
    lines = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
    failed = [line["error"] for line in lines if "error" in line]
    if failed or done.returncode != 0:
        raise Refused(failed[0] if failed else f"the recorder failed: {done.stderr[-2000:]}")
    return {line["segment"]: pathlib.Path(line["out"]) for line in lines}


def clip(frames, out, size, rate):
    """One segment's frames made a clip at the film's size and rate."""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", f"{rate:g}", "-i", str(frames / "%05d.jpg"),
                    "-vf", f"scale={size[0]}:{size[1]}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "16",
                    "-preset", "medium", "-r", f"{rate:g}", str(out)], check=True)
    return out


def joined_filter(film_script, lengths):
    """(the ffmpeg filter joining the clips by the script's transitions, its output's name, its length): an overlap of
    TRANSITION_SECONDS for a cross-fade or a push (script.timeline's clock), a fade through black split over the two
    sides of a cut."""
    segments, rate = film_script["segments"], float(film_script.get("rate", 24))
    parts = []
    for index, length in enumerate(lengths):
        fades = []
        if segments[index].get("transition") == "fade-through-black":
            fades.append(f"fade=t=in:st=0:d={BLACK_HALF}")
        if index + 1 < len(lengths) and segments[index + 1].get("transition") == "fade-through-black":
            fades.append(f"fade=t=out:st={length - BLACK_HALF:.3f}:d={BLACK_HALF}")
        parts.append(f"[{index}:v]fps={rate:g},settb=AVTB,setpts=PTS-STARTPTS,{GRADE}"
                     f"{''.join(',' + fade for fade in fades)}[c{index}]")
    made, clock = "c0", lengths[0]
    for index in range(1, len(lengths)):
        overlap = script.overlap_of(index, segments[index])
        if overlap:
            kind = XFADES[segments[index]["transition"]]
            parts.append(f"[{made}][c{index}]xfade=transition={kind}:duration={overlap}:offset={clock - overlap:.3f}"
                         f"[j{index}]")
            clock += lengths[index] - overlap
        else:
            parts.append(f"[{made}][c{index}]concat=n=2:v=1:a=0[j{index}]")
            clock += lengths[index]
        made = f"j{index}"
    return ";".join(parts), made, clock


def bed_sound(film_script, state):
    """The film's sound bed, (the place whose bed it is, its first file), its tone: the bed the sound stage made from
    the design (the state's `sound_beds`, score/stages/sound beds.py) of the first place the film shows that has one,
    else of the first place that has one; (None, None) while no bed is made (the film is silent, WAITING_BED)."""
    beds = state.get("sound_beds") or {}
    shown = [segment.get("shows", {}).get("place") for segment in film_script["segments"]]
    place = next((place for place in [*shown, *sorted(beds)] if beds.get(place)), None)
    if place is None:
        return None, None
    from score.dashboard.state import source
    return place, source().blob_path(beds[place][0]["sha"])


def cut_moments(film_script):
    """The film's seconds where one segment gives way to the next: a cross-fade's or push's middle, else the joint."""
    return [start + script.overlap_of(index, segment) / 2
            for index, ((start, _), segment) in enumerate(zip(script.timeline(film_script), film_script["segments"]))
            if index]


def onsets(bed, rate):
    """How sharply the bed's sound rises at each hop of 1 / `rate` s (its log energy's rise, never below 0)."""
    import numpy
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(bed), "-ac", "1", "-ar", str(ONSET_RATE), "-f",
                          "f32le", "-"], capture_output=True, check=True).stdout
    samples = numpy.frombuffer(pcm, dtype=numpy.float32)
    hop = int(ONSET_RATE / rate)
    hops = samples[:len(samples) // hop * hop].reshape(-1, hop)
    energy = numpy.log((hops.astype(numpy.float64) ** 2).mean(axis=1) + 1e-9)
    return numpy.maximum(numpy.diff(energy, prepend=energy[:1]), 0.0)


def beat_offset(rises, cuts, rate):
    """The bed's second to start the film at so its strongest onsets (`rises`, one a hop of 1 / `rate` s, the bed
    looping) fall on the `cuts`; 0 where no start stands out by BEAT_STANDOUT deviations (a bed with no beat)."""
    import numpy
    if not len(rises) or not cuts:
        return 0.0
    at = numpy.round(numpy.asarray(cuts) * rate).astype(int)
    scores = numpy.array([rises[(at + start) % len(rises)].sum() for start in range(len(rises))])
    best = int(scores.argmax())
    return round(best / rate, 3) if scores[best] > scores.mean() + BEAT_STANDOUT * scores.std() else 0.0


def silences(film_script):
    """The ffmpeg volume filters that silence the bed under every segment whose sound is silence."""
    return [f"volume=enable='between(t,{start:.3f},{start + length:.3f})':volume=0"
            for (start, length), segment in zip(script.timeline(film_script), film_script["segments"])
            if segment.get("sound") == "silence"]


def joined(film_script, clips, out, bed, bed_from):
    """The clips joined by the script's transitions with the sound bed under them from its `bed_from` second, at
    one loudness (silence where `bed` is None); its length."""
    lengths = [script.seconds_of(film_script, segment) for segment in film_script["segments"]]
    video, made, total = joined_filter(film_script, lengths)
    sound = ",".join([f"atrim=0:{total:.3f}", "asetpts=PTS-STARTPTS", f"afade=t=in:st=0:d={BED_FADE[0]}",
                      f"afade=t=out:st={total - BED_FADE[1]:.3f}:d={BED_FADE[1]}", *silences(film_script),
                      f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11", "aresample=48000"])
    inputs = [part for path in clips for part in ("-i", str(path))]
    sound_input = ["-stream_loop", "-1", "-ss", f"{bed_from:.3f}", "-i", str(bed)] if bed else \
        ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, *sound_input,
                    "-filter_complex", f"{video};[{len(clips)}:a]{sound}[bed]", "-map", f"[{made}]", "-map", "[bed]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)], check=True)
    return total


def record_of(film_script, total, bed_place, bed_from):
    """What the preview was made from: the script, when, each segment's place on its clock and its clip, whose bed
    it plays (the place, else WAITING_BED) and where the bed starts."""
    return {"film": film_script["film"], "made_at": datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds"), "seconds": round(total, 3), "script": film_script,
        "bed": f"sound@{bed_place}" if bed_place else WAITING_BED, "bed_from": bed_from,
        "segments": [{"index": index + 1, "cut": segment["cut"], "start": start, "seconds": length,
                      "clip": f"{film_script['film']}-takes/{index + 1:03d}.mp4"}
                     for index, ((start, length), segment) in enumerate(zip(script.timeline(film_script),
                                                                             film_script["segments"]))]}


def make(film, export=None, user=None, keep=False):
    """Render the film's free preview end to end; (its path, its record's path)."""
    film_script, _ = script.read(settings.SCORE_REPO, settings.SCORE_HOME, film)
    if film_script is None:
        raise Refused(f"no film script {film}")
    found = script.faults(film_script)
    if found:
        raise Refused("; ".join(found))
    out, record = preview_paths(settings.SCORE_HOME, film)
    work = out.parent / f"work-{film}"
    shutil.rmtree(work / "frames", ignore_errors=True)
    (work / "frames").mkdir(parents=True, exist_ok=True)
    export = pathlib.Path(export) if export else built_export(work / "export")
    state = json.loads((export / "state.json").read_text())
    user = user or owner_name()
    server, base = started_cockpit(cockpit_home(work, export, film), user)
    try:
        timeline = script.timeline(film_script)
        segments = [job_segment(film_script, state, index, segment, start, length, work / "frames")
                    for index, ((start, length), segment) in enumerate(zip(timeline, film_script["segments"]))]
        job = {"base": base, "user": user, "size": film_script.get("size", [1280, 720]), "scale": SCALE,
               "rate": float(film_script.get("rate", 24)), "spend": takes.SPEND.pattern,
               "scene_js": str(scenes.SCENE_JS), "scene_html": SCENE_HTML, "segments": segments}
        folders = recorded(job, work)
    finally:
        server.terminate()
        server.wait(timeout=30)
    clips_folder = takes_folder(settings.SCORE_HOME, film)
    clips_folder.mkdir(parents=True, exist_ok=True)
    clips = [clip(folders[index + 1], clips_folder / f"{index + 1:03d}.mp4", job["size"], job["rate"])
             for index in range(len(film_script["segments"]))]
    bed_place, bed = bed_sound(film_script, state)
    bed_from = beat_offset(onsets(bed, job["rate"]), cut_moments(film_script), job["rate"]) if bed else 0.0
    partial = out.with_suffix(".partial.mp4")
    total = joined(film_script, clips, partial, bed, bed_from)
    partial.replace(out)
    record.write_text(json.dumps(record_of(film_script, total, bed_place, bed_from), indent=1) + "\n")
    if not keep:
        shutil.rmtree(work / "frames", ignore_errors=True)
    return out, record
