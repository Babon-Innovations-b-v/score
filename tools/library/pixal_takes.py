"""Pixal3D's takes kept in the creator's library (score_lib's `take` entries) and put back where they lay.

A take in `$PROPS_HOME/work/pixal` is its raw model `<take>.glb`, its finished models `<take>-final.glb` and
`<take>-<faces>.glb`, its record `<take>.json` and its camera folder `<take>.svviews/` (the close-up `input.png` and
its camera `transforms.json`; `<take>-rebuilt.svviews/` when the finish rebuilt it), every one paid for once. The
library keeps a take as one `take/<id>@<version>` entry holding each file under that name (`take_id`: the take's name
with `-` as `_`; its title is the take's own name).

    pixal_takes.take_back(take, folder)     # the take's missing files fetched back into `folder`; the names put back
    pixal_takes.taken_in(takes, folder)     # the takes committed to the library through `score-lib take-in --save`
    pixal_takes.read_back(take, folder)     # None when the library hands back every file at its size and hash

`take_back` is what every reader of work/pixal goes through: score/stages/__init__.py calls it for a row's takes
before the row's files are read, so a take freed by `offload-pixal` (score/conductor/disk.py) comes back, the same
bytes, before anything reads or hashes it. Nothing here makes or changes a take: it is outside every code version
(score/graph/_code.py FRAMEWORK). The library is reached as library_files.py reaches it (its own command, its entry
records read only for each file's sha256).
"""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

HERE = str(pathlib.Path(__file__).resolve().parent)
if HERE not in sys.path:  # already there in the runner: score/stages/sound puts it there
    sys.path.insert(0, HERE)
import library_files  # noqa: E402

KIND = "take"
ID = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)?$")  # score_lib's entry.ID_PATTERN
FINISHED = re.compile(r"^-(final|[0-9]+)\.glb$")
CAMERAS = (".svviews", "-rebuilt.svviews")
SOURCE = "pixal3d"  # score_lib config/sources.toml: Pixal3D, picture to 3D


def take_id(take):
    """The take's entry id in the library, or None when its name makes none."""
    found = take.replace("-", "_")
    return found if ID.match(found) else None


def take_names(take, folder):
    """The names, from `folder`, of every file of the take there (its folders' files by their paths inside)."""
    folder = pathlib.Path(folder)
    names = [name for name in (f"{take}.glb", f"{take}.json") if (folder / name).is_file()]
    names += [path.name for path in folder.glob(f"{take}-*.glb") if FINISHED.match(path.name[len(take):])]
    for camera in CAMERAS:
        names += [path.relative_to(folder).as_posix() for path in (folder / f"{take}{camera}").rglob("*")
                  if path.is_file()]
    return sorted(names)


def newest_record(take):
    """The newest `take` entry the library's checkout holds for the take (its title the take's name), or None."""
    root, entry = library_files.settings().get("SCORE_LIB_ROOT"), take_id(take)
    if not root or entry is None:
        return None
    folder = pathlib.Path(root) / "entries" / KIND / entry
    versions = sorted(int(path.name) for path in folder.iterdir() if path.name.isdigit()) if folder.is_dir() else []
    if not versions:
        return None
    record = json.loads((folder / str(versions[-1]) / "entry.json").read_text())
    return record if record.get("title") == take else None


def take_back(take, folder):
    """Each file of the take's library entry missing from `folder` fetched (library_files.from_library: hash-checked)
    and linked in its place, made beside it and renamed in; the names put back ([] when none was missing or the
    library holds no such take). LibraryUnreachable when the library holds it and cannot hand it back."""
    folder = pathlib.Path(folder)
    if all((folder / f"{take}{suffix}").exists() for suffix in (".glb", "-final.glb", ".svviews")):
        return []
    record = newest_record(take)
    if record is None:
        return []
    missing = [name for name in sorted(record["files"]) if not (folder / name).exists()]
    for name in missing:
        reference = library_files.reference(record["address"], name)
        cached = library_files.from_library(reference, library_files.parsed(reference))
        placed(cached, folder / name)
    return missing


def placed(cached, target):
    """`cached` at `target`: a hard link (a copy on another disk), made beside it and renamed in."""
    target.parent.mkdir(parents=True, exist_ok=True)
    spare = target.with_name(f"{target.name}.{os.getpid()}.partial")
    try:
        os.link(cached, spare)
    except OSError:
        spare.write_bytes(pathlib.Path(cached).read_bytes())
    spare.replace(target)


def listing(takes, folder, commit):
    """score-lib take-in's list of the takes (each with every file `take_names` finds), as take_in.py reads it."""
    folder = pathlib.Path(folder)
    entries = [{"kind": KIND, "id": take_id(take), "title": take,
                "files": {name: {"path": str(folder / name), "from": f"work/pixal/{name}"}
                          for name in take_names(take, folder)},
                "made_with": [{"what": f"{take}: Pixal3D's raw model, its finished models and its camera folder",
                               "source": SOURCE}]} for take in takes]
    return {"world": "world1", "commit": commit, "taken_from": "score's work/pixal (Pixal3D's takes)",
            "entries": entries}


def library_command(values, *words):
    """The library's own command with `words` in its root, the blob store in its environment only; the finished
    process."""
    command = shlex.split(values.get("SCORE_LIB_COMMAND") or library_files.DEFAULT_COMMAND)
    return subprocess.run([*command, "--root", values["SCORE_LIB_ROOT"], *words],
                          env=library_files.blob_store(values), cwd=values["SCORE_LIB_ROOT"], capture_output=True,
                          text=True, timeout=library_files.TIMEOUT * 6)


def taken_in(takes, folder, commit, scratch):
    """The takes committed and pushed to the library (`score-lib take-in --save`); its report (new, unchanged, ...,
    refused, saved). LibraryUnreachable when the command fails as a whole or no library is configured."""
    values = library_files.settings()
    if not values.get("SCORE_LIB_ROOT"):
        raise library_files.LibraryUnreachable("no library is configured (SCORE_LIB_ROOT)")
    # The conductor's checkout is cloned once and never pulled: brought forward first, so it knows the take kind and
    # its push is no non-fast-forward; one that has its own commits refuses, and nothing is taken in.
    pulled = subprocess.run(["git", "-C", values["SCORE_LIB_ROOT"], "pull", "-q", "--ff-only"], capture_output=True,
                            text=True)
    if pulled.returncode != 0:
        raise library_files.LibraryUnreachable(f"the library's checkout could not be brought forward: "
                                               f"{pulled.stderr.strip()[-300:]}")
    scratch = pathlib.Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    asked, report = scratch / "takes.json", scratch / "report.json"
    asked.write_text(json.dumps(listing(takes, folder, commit), indent=1))
    done = library_command(values, "take-in", str(asked), "--save", "--report", str(report))
    if not report.is_file():
        raise library_files.LibraryUnreachable(f"score-lib take-in exited {done.returncode}: "
                                               f"{(done.stderr or done.stdout).strip()[-400:]}")
    return json.loads(report.read_text())


def upstream_holds(take):
    """Whether the take's newest entry is in the library's pushed history (its branch's upstream), not only here."""
    record, root = newest_record(take), library_files.settings().get("SCORE_LIB_ROOT")
    if record is None:
        return False
    path = f"entries/{KIND}/{take_id(take)}/{record['version']}/entry.json"
    done = subprocess.run(["git", "-C", root, "log", "-1", "--format=%H", "@{u}", "--", path], capture_output=True,
                          text=True)
    return done.returncode == 0 and bool(done.stdout.strip())


def read_back(take, folder, scratch):
    """Why the library does not hold the take whole (a file missing from its entry, or handed back at another size
    or hash than `folder` holds), or None: every file fetched again from the blob store into `scratch` and compared."""
    record = newest_record(take)
    names = take_names(take, folder)
    if record is None:
        return "no take entry in the library"
    if sorted(record["files"]) != names:
        return f"its entry holds {len(record['files'])} files, work/pixal {len(names)}"
    values = library_files.settings()
    with tempfile.TemporaryDirectory(dir=scratch) as into:
        words = ["fetch", record["address"], "--into", into, *(word for name in names for word in ("--file", name))]
        done = library_command(values, *words)
        if done.returncode != 0:
            return f"score-lib fetch exited {done.returncode}: {done.stderr.strip()[-200:]}"
        back = pathlib.Path(into) / "score_lib" / KIND / take_id(take) / str(record["version"])
        for name in names:
            here, there = pathlib.Path(folder) / name, back / name
            if not there.is_file() or there.stat().st_size != here.stat().st_size:
                return f"{name} came back at another size"
            if library_files.sha256(there) != library_files.sha256(here):
                return f"{name} came back with other bytes"
    return None
