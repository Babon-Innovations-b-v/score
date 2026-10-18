"""A free look at a place's film before it is bought: its shots as this checkout plans them, a few frames drawn here,
beside the same moments of the film the store holds, as one picture and one short film for the place's proposal.

    .venv/bin/python tools/review/film_preview.py <place> <out folder> [--film <film>] [--line "<words>" ...]

The plan is score/stages/demo_film's own (its film record's cameras and leave_out, demo.py's plan, from its start),
run over the place's accepted final stage (the neighbours output, else its assembly) with nothing rendered on the
cloud: the stage's big folders are linked, only its root layer and scene record are copied, so the store is never
written. The new frames are drawn from the place's assembly alone (drawn_stage) by one local Blender job (tools/blender/session.py batch, under the machine's
one-heavy-job lock: Eevee on the processor at SIZE, so the light is rougher than the film's); the old ones are frames
of the store's film.mp4 at the same shot moments (ffmpeg). Writes into <out folder>: before-after.jpg (the old film's
frames on top, the new plan's under them, each labelled, under the `--line`s: what the change fixes and what it
costs, in plain words for the owner), before-after.mp4 (that picture, held), views.json (the new
plan) and preview.json (which frames, from where). No cloud call, nothing bought.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import demo  # noqa: E402  (its plan, TITLE_SECONDS, RATE; puts tools/usd on the path)
sys.path.insert(0, str(REPO))
from score.stages import demo_film  # noqa: E402
from score.store import Store  # noqa: E402

SESSION = REPO / "tools/blender/session.py"
VIEWS_SCRIPT = REPO / "tools/blender/inside/usd_views.py"
SIZE = (640, 360)
THREADS = "4"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BACK = (17, 18, 21)
INK = (236, 236, 232)
DIM_INK = (150, 152, 158)
ACCENT = (232, 170, 90)
# The sketch from above: its margin and how long a shot's look line is drawn, in pixels.
SKETCH_MARGIN = 40
SKETCH_LOOK = 60
LABEL_HEIGHT = 40
GAP = 8
# A sheet is at least three pictures wide, so its words and titles fit.
LEAST_WIDE = 3 * SIZE[0] + 2 * GAP
HOLD_SECONDS = 8.0
# A shot's last frame is read this far before the film's end: the cut's fade-out ends the film a few frames early.
LAST_FRAME_MARGIN = 0.1
# Copied into the work stage (the film's planner writes them); everything else in the stage folder is linked.
WRITTEN = ("scene.json",)


def accepted_stages(store, place):
    """{row: folder} of the place's accepted assembly and, where it shows others, neighbours outputs."""
    inputs = {}
    for row in ("neighbours", "assembly"):
        output = store.accepted(f"{row}@{place}")
        if output:
            inputs[row] = store.checkout(output)
    if "assembly" not in inputs:
        raise SystemExit(f"{place} has no accepted assembly in the store")
    return inputs


def drawn_stage(assembly, place, film, work):
    """The stage the new frames are drawn from: the place's assembly alone, its film's leave_out applied (a place with
    its neighbours, the whole base at 3.5 GB, is more than Blender here holds: killed for memory, 2026-10-18)."""
    copy = work_stage(assembly, place, work / "alone")
    demo_film.leave_out(copy / f"{place}.usda", film_record(film))
    return copy / f"{place}.usda"


def work_stage(stage_folder, place, under):
    """A writable copy of the stage folder at under/<place>: its root layer and scene record copied, every
    other entry linked, so the planner's edits never reach the store's checkout. The copy's folder."""
    target = under / place
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for entry in pathlib.Path(stage_folder).iterdir():
        if entry.name == f"{place}.usda" or entry.name in WRITTEN:
            shutil.copyfile(entry, target / entry.name)
        else:
            (target / entry.name).symlink_to(entry.resolve())
    return target


def film_record(film):
    """This checkout's record of the film (data/definitions/demo_films/<film>.json)."""
    return json.loads((demo_film.FILMS / f"{film}.json").read_text())


def planned(stage_folder, place, film, work):
    """The new plan of the film over the stage, as demo_film's make plans it (own_cameras, leave_out, demo.plan from
    the film's start), its frames rendered nowhere: views.json's content."""
    record = film_record(film)
    copy = work_stage(stage_folder, place, work / "stages")
    cameras = demo_film.own_cameras(copy / "scene.json", record)
    demo_film.leave_out(copy / f"{place}.usda", record)
    motion = REPO / "data/motion" / f"{place}.json"
    start = demo_film.film_start(record, {"motion": str(motion)} if motion.exists() else {})
    given = f"{place}={','.join(cameras)}" if film == place else f"{film}@{place}={','.join(cameras)}"
    demo.plan(work, work / "stages", [given], jobs_each=1, size=SIZE, ink=False, shots=len(cameras),
              seconds=demo_film.SECONDS, start=start)
    return json.loads((work / "views" / f"{film}.json").read_text())


def plan_key(stage_folder, film):
    """What a plan is made from: the stage, the film's record and the planner's code (each file's hash), so a plan
    made from the same is not made again (a retry after Blender was refused for memory)."""
    code = [REPO / "tools/review/demo.py", REPO / "tools/usd/camera_paths.py", pathlib.Path(demo_film.__file__)]
    return {"stage": str(stage_folder), "record": film_record(film),
            "code": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in code}}


def same_frames(kept, new_plan):
    """True when the plan kept at `kept` has the new plan's frames (the planner's commit aside)."""
    return kept.exists() and json.loads(kept.read_text())["views"] == new_plan["views"]


def shot_moments(views):
    """Each shot's first and last frame (where it starts and where it ends up, about a minute of local drawing each):
    [(index into views, the view)] in film order."""
    shots = {}
    for number, view in enumerate(views):
        shots.setdefault(view["name"].split("-")[0], []).append(number)
    chosen = []
    for numbers in shots.values():
        for number in sorted({numbers[0], numbers[-1]}):
            chosen.append((number, views[number]))
    return chosen


def drawn(stage_file, moments, folder):
    """The chosen moments of the new plan drawn by one local Blender job into `folder`: their -look.png paths. Drawn
    already (the same plan, kept by preview): no job."""
    paths = [folder / f"{view['name']}-look.png" for _, view in moments]
    if all(path.exists() for path in paths):
        return paths
    folder.mkdir(parents=True, exist_ok=True)
    job = folder / "views.json"
    job.write_text(json.dumps({"size": list(SIZE), "views": [dict(view, look_only=True) for _, view in moments]}))
    environment = {**os.environ, "OMP_NUM_THREADS": THREADS, "LP_NUM_THREADS": THREADS}
    done = subprocess.run([sys.executable, str(SESSION), "batch", str(VIEWS_SCRIPT), "--", str(stage_file), str(job),
                           str(folder)], env=environment, capture_output=True, text=True)
    (folder / "blender.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    missing = [path.name for path in paths if not path.exists()]
    if done.returncode or missing:
        raise SystemExit(f"Blender drew {len(paths) - len(missing)} of {len(paths)} frames; log {folder / 'blender.log'}")
    return paths


def film_seconds(film_file):
    """A film's length in seconds (ffprobe)."""
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(film_file)], capture_output=True, text=True, check=True).stdout)


def film_frames(film_file, views, folder):
    """The frames of the store's film at each of its own shots' moments (shot_moments over its views), from the
    film.mp4 after its title card: [(label, path)]."""
    folder.mkdir(parents=True, exist_ok=True)
    last = film_seconds(film_file) - LAST_FRAME_MARGIN
    found = []
    for number, view in shot_moments(views):
        second = min(demo.TITLE_SECONDS + number / demo.RATE, last)
        path = folder / f"{view['name']}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{second:.3f}", "-i", str(film_file), "-frames:v", "1",
                        "-vf", f"scale={SIZE[0]}:{SIZE[1]}", str(path)], check=True)
        found.append((view["name"], path))
    return found


def labelled_row(title, pictures):
    """One row: its title over the pictures side by side, each labelled with its frame's name."""
    face = ImageFont.truetype(FONT, 22)
    small = ImageFont.truetype(FONT, 16)
    wide = max(len(pictures) * SIZE[0] + (len(pictures) - 1) * GAP, LEAST_WIDE)
    row = Image.new("RGB", (wide, LABEL_HEIGHT + SIZE[1]), BACK)
    pen = ImageDraw.Draw(row)
    pen.text((8, 8), title, font=face, fill=INK)
    for number, (name, path) in enumerate(pictures):
        left = number * (SIZE[0] + GAP)
        row.paste(Image.open(path).convert("RGB").resize(SIZE), (left, LABEL_HEIGHT))
        pen.text((left + 8, LABEL_HEIGHT + 8), name, font=small, fill=INK, stroke_width=2, stroke_fill=BACK)
    return row


def path_sketch(old_views, new_views, out):
    """The camera's paths seen from above at SIZE, as PNG at `out`: the bought film's in grey, the new plan's in
    amber, a dot where each shot starts and a short line along where it looks, with a 1 m bar; its path."""
    picture = Image.new("RGB", SIZE, BACK)
    pen = ImageDraw.Draw(picture)
    points = [(view["eye"][0], view["eye"][2]) for view in old_views + new_views]
    points += [(view["aim"][0], view["aim"][2]) for view in old_views[:1] + new_views[:1]]
    low = [min(point[axis] for point in points) for axis in (0, 1)]
    high = [max(point[axis] for point in points) for axis in (0, 1)]
    scale = min((SIZE[0] - 2 * SKETCH_MARGIN) / max(high[0] - low[0], 1.0),
                (SIZE[1] - 2 * SKETCH_MARGIN) / max(high[1] - low[1], 1.0))
    def spot(x, z):
        return (SKETCH_MARGIN + (x - low[0]) * scale, SKETCH_MARGIN + (z - low[1]) * scale)
    for views, colour in ((old_views, DIM_INK), (new_views, ACCENT)):
        shots = {}
        for view in views:
            shots.setdefault(view["name"].split("-")[0], []).append(view)
        for shot in shots.values():
            path = [spot(view["eye"][0], view["eye"][2]) for view in shot]
            pen.line(path if len(path) > 1 else path * 2, fill=colour, width=3)
            start, aim = path[0], spot(shot[0]["aim"][0], shot[0]["aim"][2])
            length = max(1e-6, ((aim[0] - start[0]) ** 2 + (aim[1] - start[1]) ** 2) ** 0.5)
            reach = min(length, SKETCH_LOOK)
            pen.line([start, (start[0] + (aim[0] - start[0]) / length * reach,
                              start[1] + (aim[1] - start[1]) / length * reach)], fill=colour, width=2)
            pen.ellipse([start[0] - 5, start[1] - 5, start[0] + 5, start[1] + 5], fill=colour)
    face = ImageFont.truetype(FONT, 16)
    pen.text((8, SIZE[1] - 48), "grey: the bought film's camera", font=face, fill=DIM_INK)
    pen.text((8, SIZE[1] - 26), "amber: the new plan's camera (dot: a shot starts, line: where it looks)", font=face,
             fill=ACCENT)
    bar = min(scale, SIZE[0] / 3)
    pen.line([(SIZE[0] - 16 - bar, 16), (SIZE[0] - 16, 16)], fill=INK, width=2)
    label = "1 m" if bar == scale else f"{bar / scale:.1f} m"
    pen.text((SIZE[0] - 16 - face.getlength(label), 22), label, font=face, fill=INK)
    picture.save(out)
    return out


def wrapped(lines, face, wide):
    """The lines broken at spaces so none is wider than `wide` pixels in `face`."""
    broken = []
    for line in lines:
        current = ""
        for word in line.split(" "):
            trial = f"{current} {word}".strip()
            if current and face.getlength(trial) > wide:
                broken.append(current)
                current = word
            else:
                current = trial
        broken.append(current)
    return broken


def words_row(lines, wide):
    """The proposal's own words over the pictures, wrapped to the sheet's width."""
    face = ImageFont.truetype(FONT, 24)
    shown = wrapped(lines, face, wide - 16)
    row = Image.new("RGB", (wide, 16 + 34 * len(shown)), BACK)
    pen = ImageDraw.Draw(row)
    for number, line in enumerate(shown):
        pen.text((8, 8 + 34 * number), line, font=face, fill=INK)
    return row


def sheet(rows, out):
    """The rows one under the other on the dark ground, as JPEG at `out`, its width even for the film's encoder."""
    wide = max(row.width for row in rows)
    wide += wide % 2
    tall = sum(row.height for row in rows) + GAP * (len(rows) - 1)
    tall += tall % 2
    canvas = Image.new("RGB", (wide, tall), BACK)
    top = 0
    for row in rows:
        canvas.paste(row, (0, top))
        top += row.height + GAP
    canvas.save(out, quality=88)


def held_film(picture, out):
    """The picture held HOLD_SECONDS as an H.264 film, so a proposal carries it as its draft film."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(picture), "-t", str(HOLD_SECONDS), "-r", "24",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=min(1920\\,iw):-2", str(out)], check=True)


def preview(place, out, film=None, lines=(), draw=True):
    """The before and after of the place's film into `out` (module docstring); preview.json's content. Without
    `draw`, the new plan is shown from above only (no Blender: the machine's one heavy job is shared)."""
    film = film or place
    store = Store.default()
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    stages = accepted_stages(store, place)
    stage_folder = demo_film.final_stage(stages)
    key = plan_key(stage_folder, film)
    kept = out / "plan-key.json"
    if (out / "views.json").exists() and kept.exists() and json.loads(kept.read_text()) == key:
        new_plan = json.loads((out / "views.json").read_text())
    else:
        new_plan = planned(stage_folder, place, film, work)
        if not same_frames(out / "views.json", new_plan):
            shutil.rmtree(out / "after", ignore_errors=True)
        (out / "views.json").write_text(json.dumps(new_plan, indent=1))
        kept.write_text(json.dumps(key, indent=1))
    moments = shot_moments(new_plan["views"])
    after = (list(zip([view["name"] for _, view in moments],
                      drawn(drawn_stage(stages["assembly"], place, film, work), moments, out / "after")))
             if draw else [])
    rows, before_source, old_views = [], None, []
    accepted = store.accepted(f"demo-film@{place}" if film == place else f"demo-film-extra@{place}")
    if accepted:
        folder = store.checkout(accepted) / ("" if film == place else film)
        old_views = json.loads((folder / "views.json").read_text())["views"]
        rows.append(labelled_row(f"Before: the {place} film as bought (frames of it)",
                                 film_frames(folder / "film.mp4", old_views, out / "before")))
        before_source = accepted
    sketch = path_sketch(old_views, new_plan["views"], out / "paths.png")
    rows.append(labelled_row("After: the new camera plan, seen from above, and drawn here quickly from the place alone "
                             "(rougher light than the paid film)" if draw else
                             "After: the new camera plan, seen from above (its frames are drawn when the film is bought)",
                             [("from above", sketch)] + after))
    if lines:
        rows.insert(0, words_row(lines, max(row.width for row in rows)))
    sheet(rows, out / "before-after.jpg")
    held_film(out / "before-after.jpg", out / "before-after.mp4")
    record = {"place": place, "film": film, "stage": str(stage_folder), "before": before_source,
              "after_frames": [name for name, _ in after], "moves": new_plan.get("moves")}
    (out / "preview.json").write_text(json.dumps(record, indent=1))
    shutil.rmtree(work / "stages", ignore_errors=True)
    shutil.rmtree(work / "alone", ignore_errors=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("place")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--film", help="another film of the place (the ship's hull through the hangar: hull)")
    parser.add_argument("--line", action="append", default=[], help="a line of words over the pictures (repeat it)")
    parser.add_argument("--no-draw", action="store_true", help="the new plan from above only, no Blender")
    options = parser.parse_args()
    record = preview(options.place, options.out.resolve(), options.film, options.line, not options.no_draw)
    print(f"{options.out / 'before-after.jpg'}: {len(record['after_frames'])} new frames"
          + ("" if record["before"] else "; no film bought yet, so no before"))


if __name__ == "__main__":
    main()
