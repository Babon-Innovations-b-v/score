"""The demo's measured checks on its films (tools/review/demo.py) and the showcase (showcase.py), never a judgement by
eye: what ffmpeg measures on the video, and on the film's own frames what the camera stood near and what was drawn.

    .venv/bin/python tools/review/film_checks.py films <out> <film> [<film> ...]
    .venv/bin/python tools/review/film_checks.py video <video> --least 120 --most 180 [--out <checks.json>]
    .venv/bin/python tools/review/film_checks.py report <out> <summary.txt> <cloud log> [<cloud log> ...]

`films` checks each film's video (<out>/videos/<film>.mp4) and its frames: the size 1920x1080, a sound track that is
not silent (volumedetect), no black stretch after the title card (blackdetect), no frozen stretch (freezedetect), the
length between FILM_SECONDS; and on every frame of its views (<out>/views/<film>.json) the camera's eye at least the
planner's clearance (tools/usd/camera_paths.py CLEARANCE) from every mesh of the stage and outside and as far from
every person's box where that person stands at the frame's own moment of the stage's time, and the game's ink lines
drawn (its <name>-lines.png and <name>-ink.png there, and every shot's lines touching some pixel; a frame whose lines
are faint or touch nothing, everything it sees past the ink's fade, is counted, not failed). It writes every number
to <out>/checks/<film>.json and prints one line a film. `video` runs the video checks alone (the showcase: its title card is not skipped). `report` writes the
demo's summary: every film's and the showcase's checks, and the cloud cost of each batch from its detached log's
last summary line.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import demo  # noqa: E402  (puts tools/usd on the path)
import camera_paths  # noqa: E402  (tools/usd)

SIZE = list(demo.SIZE)
# Silent: a mean level under this (dB). Black: blackdetect's defaults (98% of pixels under 10% grey) held this long.
# Frozen: freezedetect's default noise (-60 dB) held this long.
SILENT_DB = -50.0
BLACK_SECONDS = 0.5
FROZEN_SECONDS = 2.0
# A place film's length, and the showcase's (seconds).
FILM_SECONDS = (20.0, 40.0)
SHOWCASE_SECONDS = (120.0, 180.0)
# A pixel counts as inked from this share of ink (the lines' alpha, 0 to 255).
INKED_ALPHA = 128


def tool(name):
    """ffmpeg's or ffprobe's path."""
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"{name} is not on the path")
    return found


def probe(video):
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height", "-of", "json", str(video)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def filtered(video, chain, audio=False, start=0.0):
    """ffmpeg's log of a filter run over the video's pictures (or its sound) from `start` seconds."""
    command = [tool("ffmpeg"), "-hide_banner", "-nostats", "-ss", str(start), "-i", str(video)]
    command += (["-af", chain, "-vn"] if audio else ["-vf", chain, "-an"]) + ["-f", "null", "-"]
    return subprocess.run(command, capture_output=True, text=True, check=True).stderr


def loudness(video):
    """The sound's mean and peak level (dB), None for silence."""
    text = filtered(video, "volumedetect", audio=True)
    found = [re.search(rf"{kind}_volume: (-?[\d.]+|-inf) dB", text) for kind in ("mean", "max")]
    return [float(match.group(1)) if match and match.group(1) != "-inf" else None for match in found]


def stretches(video, seconds, skip_start):
    """The black stretches after `skip_start` and the frozen ones: [[start, end], ...] each, seconds."""
    text = filtered(video, f"blackdetect=d={BLACK_SECONDS}", start=skip_start)
    black = [[float(start) + skip_start, float(end) + skip_start]
             for start, end in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", text)]
    text = filtered(video, f"freezedetect=d={FROZEN_SECONDS}")
    starts = [float(value) for value in re.findall(r"freeze_start: ([\d.]+)", text)]
    ends = [float(value) for value in re.findall(r"freeze_end: ([\d.]+)", text)]
    return black, [[start, ends[index] if index < len(ends) else seconds] for index, start in enumerate(starts)]


def video_checks(video, least, most, skip_start=0.0):
    """The video's measures and what fails: {"video", "seconds", "size", "audio", "mean_db", "max_db", "black",
    "frozen", "failures"}."""
    info = probe(video)
    streams = info.get("streams", [])
    seconds = float(info["format"]["duration"])
    picture = next((stream for stream in streams if stream["codec_type"] == "video"), {})
    result = {"video": str(video), "seconds": round(seconds, 2), "size": [picture.get("width"), picture.get("height")],
              "audio": any(stream["codec_type"] == "audio" for stream in streams), "mean_db": None, "max_db": None}
    if result["audio"]:
        result["mean_db"], result["max_db"] = loudness(video)
    result["black"], result["frozen"] = stretches(video, seconds, skip_start)
    failures = [f"size {result['size']}"] if result["size"] != SIZE else []
    if not result["audio"]:
        failures.append("no sound track")
    elif result["mean_db"] is None or result["mean_db"] < SILENT_DB:
        failures.append(f"silent (mean {result['mean_db']} dB)")
    failures += [f"black {result['black']}"] if result["black"] else []
    failures += [f"frozen {result['frozen']}"] if result["frozen"] else []
    if not least <= seconds <= most:
        failures.append(f"length {seconds:.1f} s outside {least:g}-{most:g}")
    return dict(result, failures=failures)


def clearance_checks(stage, views):
    """Per shot, the nearest any eye came to a mesh and to a person, and the frames nearer than the clearance."""
    walls, persons = camera_paths.frame_clearances(camera_paths.place_scenes(stage), stage, views)
    shots, failures = {}, []
    for index, view in enumerate(views):
        shot = demo.shot_of(view)
        found = shots.setdefault(shot, {"walls": np.inf, "people": np.inf, "near_walls": 0, "near_people": 0})
        found["walls"], found["people"] = min(found["walls"], walls[index]), min(found["people"], persons[index])
        found["near_walls"] += int(not camera_paths.stands_clear(walls[index], np.inf))
        found["near_people"] += int(not camera_paths.stands_clear(np.inf, persons[index]))
    for shot, found in shots.items():
        for kind in ("walls", "people"):
            if found[f"near_{kind}"]:
                failures.append(f"{shot}: {found[f'near_{kind}']} frames nearer than {camera_paths.CLEARANCE} m to "
                                f"{'a mesh' if kind == 'walls' else 'a person'} (nearest {found[kind]:.3f} m)")
            found[kind] = round(float(found[kind]), 3) if np.isfinite(found[kind]) else None
    return shots, failures


def inked_pixels(lines):
    """How many pixels of a lines picture (usd_views.py's <name>-lines.png) the ink touches at all, and how many it
    inks at least half."""
    with Image.open(lines) as picture:
        alpha = np.asarray(picture.getchannel("A"))
    return int((alpha > 0).sum()), int((alpha >= INKED_ALPHA).sum())


def ink_checks(frames, views):
    """Every frame's ink: the frames whose lines or inked picture are missing and the shots whose lines touch no pixel
    in any frame (failures); the frames the ink touches nowhere and those with no line at half strength or more
    (everything they see lies past the game's ink fade, 60 to 120 m, as the launch's far harbour view: counted, not
    failed), with the fewest pixels inked at half strength."""
    missing, empty, faint, fewest, touched_shots = [], [], [], None, {}
    for view in views:
        lines = frames / f"{view['name']}-lines.png"
        if not lines.exists() or not (frames / f"{view['name']}-ink.png").exists():
            missing.append(view["name"])
            continue
        touched, inked = inked_pixels(lines)
        fewest = inked if fewest is None else min(fewest, inked)
        touched_shots[demo.shot_of(view)] = touched_shots.get(demo.shot_of(view), 0) + touched
        (empty if touched == 0 else faint if inked == 0 else []).append(view["name"])
    blank = [shot for shot, touched in touched_shots.items() if touched == 0]
    failures = [f"{len(missing)} frames with no ink (first {missing[0]})"] if missing else []
    failures += [f"{shot}: the ink touches no pixel in any frame" for shot in blank]
    return {"missing": len(missing), "empty": len(empty), "faint": len(faint), "fewest_inked_pixels": fewest}, failures


def film_checks(out, film):
    """A film's video and frame checks, written to <out>/checks/<film>.json."""
    planned = json.loads((out / "views" / f"{film}.json").read_text())
    result = video_checks(out / "videos" / f"{film}.mp4", *FILM_SECONDS, skip_start=demo.TITLE_SECONDS)
    result["clearance"], failures = clearance_checks(planned["stage"], planned["views"])
    result["ink"], inked = ink_checks(out / "frames" / film, planned["views"])
    result["failures"] += failures + inked
    (out / "checks").mkdir(parents=True, exist_ok=True)
    (out / "checks" / f"{film}.json").write_text(json.dumps(result, indent=1))
    return result


def said(result):
    """One line for a checked video: PASS or FAIL, its length and what failed."""
    verdict = "PASS" if not result["failures"] else "FAIL"
    return f"{verdict} {pathlib.Path(result['video']).name} {result['seconds']} s " + "; ".join(result["failures"])


def batch_cost(log):
    """A detached cloud log's last summary line as (jobs, minutes, machines, euros), or None."""
    found = re.findall(r"blender: (\d+) jobs in ([\d.]+) min on (\d+) machines, €([\d.]+)",
                       pathlib.Path(log).read_text())
    return found[-1] if found else None


def summary_lines(results, title):
    lines = [title]
    for result in results:
        verdict = "PASS" if not result["failures"] else "FAIL " + "; ".join(result["failures"])
        lines += [f"- {result['video']}",
                  f"  {result['seconds']} s, {result['size'][0]}x{result['size'][1]}, "
                  f"{pathlib.Path(result['video']).stat().st_size / 1e6:.1f} MB, audio mean {result['mean_db']} dB, "
                  f"max {result['max_db']} dB, black {result['black'] or 'none'}, frozen {result['frozen'] or 'none'}: "
                  f"{verdict}"]
    return lines + [""]


def cost_lines(logs):
    lines, total = ["CLOUD COST (each batch's own summary line)"], 0.0
    for log in logs:
        found = batch_cost(log)
        if found is None:
            lines.append(f"- {log}: no summary line (did not finish)")
            continue
        jobs, minutes, machines, euros = found
        total += float(euros)
        lines.append(f"- {log}: {jobs} jobs, {minutes} min, {machines} machines, €{euros}")
    return lines + [f"total €{total:.2f}"]


def report(out, summary, logs):
    """The demo's summary: the showcase's and every film's checks as written, and the cloud cost."""
    checks = out / "checks"
    films = [json.loads(path.read_text()) for path in sorted(checks.glob("*.json")) if path.stem != "showcase"]
    showcase = [json.loads((checks / "showcase.json").read_text())] if (checks / "showcase.json").exists() else []
    lines = summary_lines(showcase, "SHOWCASE") + summary_lines(films, "PLACE FILMS") + cost_lines(logs)
    pathlib.Path(summary).write_text("\n".join(lines) + "\n")
    print(f"{summary}: {len(films)} films, {len(showcase)} showcase, {lines[-1]}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=["films", "video", "report"])
    parser.add_argument("given", nargs="+",
                        help="films: <out> <film>...; video: <video>; report: <out> <summary> <log>...")
    parser.add_argument("--least", type=float, default=SHOWCASE_SECONDS[0])
    parser.add_argument("--most", type=float, default=SHOWCASE_SECONDS[1])
    parser.add_argument("--out", type=pathlib.Path, help="video: where its checks are written")
    options = parser.parse_args()
    if options.step == "films":
        out = pathlib.Path(options.given[0]).resolve()
        results = [film_checks(out, film) for film in options.given[1:]]
    elif options.step == "video":
        results = [video_checks(pathlib.Path(options.given[0]).resolve(), options.least, options.most)]
        if options.out:
            options.out.parent.mkdir(parents=True, exist_ok=True)
            options.out.write_text(json.dumps(results[0], indent=1))
    else:
        report(pathlib.Path(options.given[0]).resolve(), options.given[1], options.given[2:])
        return
    for result in results:
        print(said(result))
    if any(result["failures"] for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
