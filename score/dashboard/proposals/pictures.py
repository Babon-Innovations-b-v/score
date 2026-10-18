"""A proposal's pictures: small stills of a stage drawn as its drawing (drawing.py) says, from the branch's cameras at
its moments and lit by the stage's own lamps (one local Blender job, Eevee on the processor, under the machine's
one-heavy-job lock), each labelled in a strip under the picture, and the draft films and sounds the branch made."""
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

from score.dashboard.proposals import drawing

REPO = pathlib.Path(__file__).resolve().parents[3]
SESSION = REPO / "tools/blender/session.py"
VIEWS_SCRIPT = REPO / "tools/blender/inside/usd_views.py"
FILM_PLANNER = "tools/review/film_preview.py"
THREADS = "4"
JPEG_QUALITY = 85
# The labels' strip under a still: a line's height in pixels, its ground and its ink.
LABEL_LINE = 16
LABEL_BACK = (17, 18, 21)
LABEL_INK = (236, 236, 232)
FILMS = {".mp4", ".webm", ".mov"}
SOUNDS = {".wav", ".ogg", ".mp3", ".flac", ".m4a", ".opus"}
# Folders of a branch's drafts that hold inputs or the old version, never its drafts.
NOT_DRAFTS = {"old", "before", "stages", "work", "inputs", "scripts"}
# Smaller than this is a stand-in (a 115-byte pointer), not a film or a sound.
LEAST_BYTES = 1024


def record_views(stage_folder, tree, place):
    """The scene record's cameras: the record the stage was assembled from (scene.json beside it), else the
    branch's data/scene/<place>.json; [] when neither has any."""
    for path in (pathlib.Path(stage_folder) / "scene.json", pathlib.Path(tree) / "data/scene" / f"{place}.json"):
        found = json.loads(path.read_text()).get("views", []) if path.is_file() else []
        if found:
            return found
    return []


def opened(stage_file):
    """The stage composed by OpenUSD, read only (local mode only: the hosted process never comes here)."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_file))
    if stage is None:
        raise RuntimeError(f"OpenUSD could not open {stage_file}")
    return stage


def stage_lamps(stage_file):
    """Every sphere light the stage holds (its light layer's lamps, a shown place's too) as usd_views.py's point
    lights: [{at, energy, radius}], watts as Blender's USD reader takes them (intensity times pi, times two to the
    exposure)."""
    from pxr import Usd, UsdGeom, UsdLux
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    found = []
    stage = opened(stage_file)  # held while its prims are read: a prim of a dropped stage has expired
    for prim in stage.Traverse():
        if not prim.IsA(UsdLux.SphereLight):
            continue
        light = UsdLux.SphereLight(prim)
        exposure = float(light.GetExposureAttr().Get() or 0.0)
        watts = float(light.GetIntensityAttr().Get() or 0.0) * math.pi * 2.0 ** exposure
        spot = cache.GetLocalToWorldTransform(prim).ExtractTranslation()
        found.append({"at": [float(value) for value in spot], "energy": watts,
                      "radius": float(light.GetRadiusAttr().Get() or 0.1)})
    return found


def time_span(stage_file):
    """The stage's (start, end) time codes, or None when it holds no time span (nothing moves in it)."""
    stage = opened(stage_file)
    if not stage.HasAuthoredTimeCodeRange():
        return None
    return float(stage.GetStartTimeCode()), float(stage.GetEndTimeCode())


def film_views(tree, place, moved, work):
    """The branch's own plan of the place's film (its tools/review/film_preview.py --no-draw, run in its checkout,
    reading the store only), when the branch moves the film row and has that planner: its views, else []."""
    planner = pathlib.Path(tree) / FILM_PLANNER
    if drawing.FILM_ROW not in moved or not planner.is_file():
        return []
    out = pathlib.Path(work) / "film-plan"
    shutil.rmtree(out, ignore_errors=True)
    done = subprocess.run([sys.executable, str(planner), place, str(out), "--no-draw"], cwd=tree, capture_output=True,
                          text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(tree)})
    planned = out / "views.json"
    if done.returncode != 0 or not planned.is_file():
        raise RuntimeError(f"the branch's film plan failed (exit {done.returncode}): {done.stderr[-1500:]}")
    return json.loads(planned.read_text()).get("views", [])


def render(stage_file, drawn, folder):
    """usd_views.py's look of each view of the drawing into `folder`, lit by the stage's own lamps, at the drawing's
    size on at most THREADS threads; Blender's exit code."""
    job = folder / "views.json"
    job.write_text(json.dumps({"size": drawn["size"], "views": drawn["views"], "lights": stage_lamps(stage_file)}))
    environment = {**os.environ, "OMP_NUM_THREADS": THREADS, "LP_NUM_THREADS": THREADS}
    done = subprocess.run([sys.executable, str(SESSION), "batch", str(VIEWS_SCRIPT), "--", str(stage_file), str(job),
                           str(folder)], env=environment, capture_output=True, text=True)
    (folder / "blender.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    return done.returncode


def labelled(look, labels, out):
    """The look with its labels in a strip under it (the picture itself untouched), as JPEG at `out`."""
    with Image.open(look) as found:
        picture = found.convert("RGB")
    sheet = Image.new("RGB", (picture.width, picture.height + LABEL_LINE * len(labels)), LABEL_BACK)
    sheet.paste(picture, (0, 0))
    pen = ImageDraw.Draw(sheet)
    for number, line in enumerate(labels):
        pen.text((8, picture.height + 2 + number * LABEL_LINE), line, fill=LABEL_INK)
    sheet.save(out, quality=JPEG_QUALITY)


def stills(stage_file, drawn, out, folder_name="stills"):
    """The stills of the stage from each view of the drawing (drawing.py), labelled, as JPEG in `out`:
    [{name, file}] of those Blender drew, each file under `folder_name`/."""
    if not drawn or not drawn.get("views"):
        return []
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-stills-"))
    try:
        code = render(stage_file, drawn, work)
        if code != 0:
            raise RuntimeError(f"Blender's stills failed (exit {code}): {(work / 'blender.log').read_text()[-1500:]}")
        out.mkdir(parents=True, exist_ok=True)
        found = []
        for view in drawn["views"]:
            look = work / f"{view['name']}-look.png"
            if look.is_file():
                labelled(look, drawn.get("labels") or [], out / f"{view['name']}.jpg")
                found.append({"name": view["name"], "file": f"{folder_name}/{view['name']}.jpg"})
        return found
    finally:
        shutil.rmtree(work, ignore_errors=True)


def kind_of(path):
    """"film", "sound" or None for a file a proposal could carry."""
    suffix = path.suffix.lower()
    return "film" if suffix in FILMS else "sound" if suffix in SOUNDS else None


def for_place(relative, place):
    """True when a draft at `relative` (inside the branch's folder) is this place's or the whole branch's: at the top
    of the folder, or with the place named in its path (a folder, `<stage>@<place>`, or in the file's name), and not
    under one of NOT_DRAFTS."""
    folders = relative.parts[:-1]
    if any(folder in NOT_DRAFTS for folder in folders):
        return False
    return (not folders or relative.stem.startswith(place)
            or any(folder == place or folder.endswith(f"@{place}") for folder in folders))


def media(drafts, place, out):
    """The draft films and sounds of this place under `drafts` (the branch's own folder of them), copied into `out`:
    [{name, kind, file, bytes}]. None found, or no such folder: []."""
    drafts = pathlib.Path(drafts) if drafts else None
    if drafts is None or not drafts.is_dir():
        return []
    found = []
    for path in sorted(drafts.rglob("*")):
        if not path.is_file() or kind_of(path) is None or path.stat().st_size < LEAST_BYTES:
            continue
        if not for_place(path.relative_to(drafts), place):
            continue
        name = re.sub(r"[^A-Za-z0-9._-]", "-", path.relative_to(drafts).as_posix()).lstrip(".-_")
        out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out / name)
        found.append({"name": name, "kind": kind_of(path), "file": f"media/{name}", "bytes": path.stat().st_size})
    return found
