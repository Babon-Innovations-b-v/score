"""The free preview of a film script, end to end, rendered on the store's machine (`python -m score.dashboard
film-preview <film>`): nothing rented, nothing bought, no button that spends ever clicked.

1. The cockpit the takes record: the hosted cockpit as the owner sees it, served on loopback from a state export (built
   now from the store by the export command, or `--export` an existing one) in a home of its own under the preview's
   work folder, signed in as the owner by the trusted proxy's header; its film scripts are this checkout's and the
   cockpit home's.
2. Every segment drawn frame by frame in headless Chromium (recorder.mjs): a screen take on its cockpit page, a setting
   animation or a scale zoom by scene.js (scenes.py works out what it shows), any other cut through the FILM page's
   own player at its moment; each segment's captions and picture-in-picture over it.
3. Each segment's frames made a clip, the clips joined by the script's transitions on its clock (script.timeline),
   the sound bed (a library sound, `bed`) under the whole film at one loudness, silence where a segment says so.

Out: `$SCORE_DASHBOARD_HOME/films/previews/<film>.mp4` and `<film>.json` (the script it was made from, made_at, each
segment's start and seconds), which the FILM page plays and the export carries.
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
        parts.append(f"[{index}:v]fps={rate:g},settb=AVTB,setpts=PTS-STARTPTS"
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


def bed_sound(film_script):
    """The sound bed's file: the library sound the script names (`bed`, "sound/<entry>"), its made take first."""
    entry = str(film_script.get("bed", "")).partition("/")[2]
    folder = scenes.library_folder("sound", entry) if entry else None
    found = sorted(folder.glob("audio/**/*.wav"), key=lambda path: "made" not in path.parts) if folder else []
    if not found:
        raise Refused(f"no sound bed: the script's bed {film_script.get('bed')!r} is no sound in the score_lib cache")
    return found[0]


def silences(film_script):
    """The ffmpeg volume filters that silence the bed under every segment whose sound is silence."""
    return [f"volume=enable='between(t,{start:.3f},{start + length:.3f})':volume=0"
            for (start, length), segment in zip(script.timeline(film_script), film_script["segments"])
            if segment.get("sound") == "silence"]


def joined(film_script, clips, out):
    """The clips joined by the script's transitions with the sound bed under them, at one loudness; its length."""
    lengths = [script.seconds_of(film_script, segment) for segment in film_script["segments"]]
    video, made, total = joined_filter(film_script, lengths)
    bed = bed_sound(film_script)
    sound = ",".join([f"atrim=0:{total:.3f}", "asetpts=PTS-STARTPTS", f"afade=t=in:st=0:d={BED_FADE[0]}",
                      f"afade=t=out:st={total - BED_FADE[1]:.3f}:d={BED_FADE[1]}", *silences(film_script),
                      f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11", "aresample=48000"])
    inputs = [part for path in clips for part in ("-i", str(path))]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-stream_loop", "-1", "-i", str(bed),
                    "-filter_complex", f"{video};[{len(clips)}:a]{sound}[bed]", "-map", f"[{made}]", "-map", "[bed]",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)], check=True)
    return total


def record_of(film_script, total):
    """What the preview was made from: the script, when, and each segment's place on its clock."""
    return {"film": film_script["film"], "made_at": datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds"), "seconds": round(total, 3), "script": film_script,
        "segments": [{"index": index + 1, "cut": segment["cut"], "start": start, "seconds": length}
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
    clips = [clip(folders[index + 1], work / f"{index + 1:03d}.mp4", job["size"], job["rate"])
             for index in range(len(film_script["segments"]))]
    partial = out.with_suffix(".partial.mp4")
    total = joined(film_script, clips, partial)
    partial.replace(out)
    record.write_text(json.dumps(record_of(film_script, total), indent=1) + "\n")
    if not keep:
        shutil.rmtree(work / "frames", ignore_errors=True)
    return out, record
