"""pixal@<place>: the prop objects' raw models from their close-ups, by Pixal3D through the existing cloud batch.

tools/props/cloud/batch.py makes every take on rented cards (the close-up cut out on the machine, Pixal3D, the
finish here with pixal.py --finish-only) and brings each back into WORK/pixal/ as <take>.glb, <take>.svviews (the
close-up and its camera) and <take>-final.glb: the files the surface stage's line reads for every take its data lists
(score/stages/surfaces, surface_data.take_files), so the surface line (split, library paint, made solid in the bake)
takes the prop route's models from here, and its first row waits on this one. A take already made is not made again
(the batch refuses to overwrite one).

The gate `takes`: every prop object's three files are there and listed in takes.json with their hashes, and every take
is one of the place's surface data's takes, or the surface line would never paint it.
"""
import hashlib
import json
import pathlib
import subprocess

import score.stages.props.prop_data as prop_data
from score.stages.surfaces.prop_env import PROPS_PYTHON
from score.stages.surfaces.surface_gates import verdict

REPO = pathlib.Path(__file__).resolve().parents[3]
# Pixal3D measured at EUR 0.09 to 0.55 a model in the 8-model batches of 2026-10-11 (cloud ledger); the hub's 56
# objects at about EUR 0.2 each, and the cards' cold start, rounded up.
EUROS = 20.0
SUFFIXES = (".glb", "-final.glb", ".svviews")


def take_files(take):
    """A take's three files in WORK/pixal (tools/props/paths.py), where the batch brings them and the surface line
    reads them."""
    with prop_data.tools("props"):
        from paths import WORK
    return [WORK / "pixal" / f"{take}{suffix}" for suffix in SUFFIXES]


def made(take):
    return all(path.exists() for path in take_files(take))


def file_hash(path):
    """A file's sha256, or a folder's over its files' names and bytes."""
    digest = hashlib.sha256()
    for part in sorted(path.rglob("*")) if path.is_dir() else [path]:
        if part.is_file():
            digest.update(part.relative_to(path).as_posix().encode() if path.is_dir() else b"")
            digest.update(part.read_bytes())
    return digest.hexdigest()


def batch_list(objects, closeups, out):
    """The batch's list, one missing take a line with its close-up; its path, or None when every take is made."""
    lines = [f"{entry['take']} {closeups / f'{row}.png'}" for row, entry in sorted(objects.items())
             if not made(entry["take"])]
    if not lines:
        return None
    (out / "list.txt").write_text("\n".join(lines) + "\n")
    return out / "list.txt"


def make_pixal(inputs, out, seed, params):
    """Every prop object's take, made by the batch where missing; takes.json with each take's file hashes."""
    objects = prop_data.prop_objects(prop_data.record_at(inputs["props"]))
    listing = batch_list(objects, inputs["closeup"] / "closeups", out)
    if listing:
        done = subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/batch.py"), str(listing), "--who",
                               f"score pixal {prop_data.record_at(inputs['props'])['place']}", "--inventory",
                               str(inputs["inventory"])], cwd=REPO, capture_output=True, text=True)
        (out / "batch.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
        if done.returncode:
            raise RuntimeError(f"the Pixal3D batch failed (exit {done.returncode}); its log is batch.log")
    takes = {row: {"take": entry["take"],
                   **{path.name: file_hash(path) for path in take_files(entry["take"]) if path.exists()}}
             for row, entry in objects.items()}
    (out / "takes.json").write_text(json.dumps(takes, indent=1))


def pixal_faults(folder):
    return [] if (folder / "takes.json").exists() else ["no takes.json"]


def judge_takes(output, inputs, evidence):
    """Every prop object's take has its three files, unchanged since made, and the surface data lists it."""
    takes = json.loads((output / "takes.json").read_text())
    listed = json.loads(inputs["surfaces"].read_text()).get("takes", {})
    failing = []
    for row, entry in sorted(takes.items()):
        for path in take_files(entry["take"]):
            if path.name not in entry or not path.exists():
                failing.append(f"{row}: no {path.name}")
            elif file_hash(path) != entry[path.name]:
                failing.append(f"{row}: {path.name} changed since it was made")
        if entry["take"] not in listed:
            failing.append(f"{row}: take {entry['take']} is not in the place's surface data")
    return verdict("takes", failing, len(takes), "takes")
