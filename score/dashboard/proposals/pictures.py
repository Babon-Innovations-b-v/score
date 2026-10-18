"""A proposal's pictures: a few small stills of its stage from the scene record's cameras (one local Blender job,
Eevee on the processor, under the machine's one-heavy-job lock), and the draft films and sounds the branch made."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
SESSION = REPO / "tools/blender/session.py"
VIEWS_SCRIPT = REPO / "tools/blender/inside/usd_views.py"
SIZE = (640, 360)
MOST_STILLS = 4
THREADS = "4"
JPEG_QUALITY = 85
UP = [0.0, 1.0, 0.0]
FILMS = {".mp4", ".webm", ".mov"}
SOUNDS = {".wav", ".ogg", ".mp3", ".flac", ".m4a", ".opus"}
# Folders of a branch's drafts that hold inputs or the old version, never its drafts.
NOT_DRAFTS = {"old", "before", "stages", "work", "inputs", "scripts"}
# Smaller than this is a stand-in (a 115-byte pointer), not a film or a sound.
LEAST_BYTES = 1024


def views(tree, place):
    """The first MOST_STILLS cameras of the place's scene record in the branch's checkout, as usd_views.py takes
    them; [] when the record has none."""
    path = pathlib.Path(tree) / "data/scene" / f"{place}.json"
    record = json.loads(path.read_text()) if path.is_file() else {}
    return [{"name": view["name"], "eye": view["eye"], "aim": view["aim"], "up": view.get("up", UP),
             "fov": float(view.get("fov", 75.0)), "look_only": True}
            for view in record.get("views", [])[:MOST_STILLS]]


def render(stage_file, chosen, folder):
    """usd_views.py's look of each view of the stage into `folder`, at SIZE on at most THREADS threads; Blender's
    exit code."""
    job = folder / "views.json"
    job.write_text(json.dumps({"size": list(SIZE), "views": chosen}))
    environment = {**os.environ, "OMP_NUM_THREADS": THREADS, "LP_NUM_THREADS": THREADS}
    done = subprocess.run([sys.executable, str(SESSION), "batch", str(VIEWS_SCRIPT), "--", str(stage_file), str(job),
                           str(folder)], env=environment, capture_output=True, text=True)
    (folder / "blender.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
    return done.returncode


def stills(stage_file, chosen, out):
    """The stills of the stage from each chosen view, as JPEG in `out`: [{name, file}] of those Blender drew."""
    if not chosen:
        return []
    work = pathlib.Path(tempfile.mkdtemp(prefix="proposal-stills-"))
    try:
        code = render(stage_file, chosen, work)
        if code != 0:
            raise RuntimeError(f"Blender's stills failed (exit {code}): {(work / 'blender.log').read_text()[-1500:]}")
        out.mkdir(parents=True, exist_ok=True)
        found = []
        for view in chosen:
            look = work / f"{view['name']}-look.png"
            if look.is_file():
                with Image.open(look) as opened:
                    opened.convert("RGB").save(out / f"{view['name']}.jpg", quality=JPEG_QUALITY)
                found.append({"name": view["name"], "file": f"stills/{view['name']}.jpg"})
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
