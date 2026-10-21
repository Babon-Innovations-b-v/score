"""pixal@<place>: the prop objects' raw models from their close-ups, by Pixal3D through the existing cloud batch.

tools/props/cloud/batch.py makes every take on rented cards (the close-up cut out on the machine, Pixal3D, the
finish here with pixal.py --finish-only) and brings each back into WORK/pixal/ as <take>.glb, <take>.svviews (the
close-up and its camera) and <take>-final.glb: the files the surface stage's line reads for every take its data lists
(score/stages/surfaces, surface_data.take_files), so the surface line (split, library paint, made solid in the bake)
takes the prop route's models from here, and its first row waits on this one. A take already made is not made again
(the batch refuses to overwrite one).

The gate `takes`: every prop object's three files are there and listed in takes.json with their hashes, and every take
is one of the place's surface data's takes, or the surface line would never paint it. A take the batch ran once and got
no model back for, and an object whose close-up failed, is a batch gap (batch-gaps.json, score/stages/batch_gaps.py):
the gate still fails it by name, the table moves those faults to complete, and the finish route leaves the take out.
A batch that fails as a whole (its command exits other than 0: a set-up fault) still stops the row.
"""
import hashlib
import json
import pathlib
import re
import subprocess

import score.stages.batch_gaps as batch_gaps
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


def raw_made(take):
    """Whether the cloud brought the take's raw model and camera folder back (its finish may still be missing)."""
    raw, _, cameras = take_files(take)
    return raw.exists() and cameras.exists()


def faces_of(surfaces, take):
    """The triangles a take is finished to: the bake entry of the model the surface data bakes from it (route.faces_for
    its size), so a small object is not asked for more than its remeshed surface has (cable_drop: 32,362 after the
    remesh, 40,000 asked, the finish failed rather than write a worse model). The model is found by its take, never
    by a name made from the row (the camp grounds name theirs by the row alone, `cairn`). A new take's entry is written
    out in the surface data (compare.bake_entry), never left to an old bake job's file, which this row does not read."""
    bake = json.loads(surfaces.read_text())["bake"]
    model = next((model for model, made in bake["models"].items() if made == take), None)
    entry = bake.get("entries", {}).get(model)
    if not isinstance(entry, dict):
        raise KeyError(f"{surfaces}: the take {take} has no bake model with its entry written out (model {model})")
    return entry["faces"]


def finish_here(take, closeup, faces, out):
    """A take the cloud brought back but whose finish never ran or failed, finished here as the batch finishes every
    take: pixal.py --finish-only (Blender and the processor, no model)."""
    with (out / "finish.log").open("a") as log:
        done = subprocess.run([str(REPO / ".venv/bin/python"), str(REPO / "tools/props/pixal.py"), str(closeup), take,
                               "--who", "score pixal", "--finish-only", f"--faces={faces}"], cwd=REPO, stdout=log,
                              stderr=subprocess.STDOUT)
    if done.returncode:
        raise RuntimeError(f"the finish of {take} failed (exit {done.returncode}); its log is finish.log")


def seed_of(take):
    """A take's Pixal3D seed, its name's `-s<n>` (a retake of the same close-up is another seed: the galley's
    fold-down seat came out a floor block from seed 1, 2026-10-15); 1, pixal.py's own default, for any other name."""
    found = re.search(r"-s(\d+)$", take)
    return int(found.group(1)) if found else 1


def batch_list(objects, closeups, surfaces, out):
    """The batch's list, one take with no raw model a line with its close-up, its faces and its seed; its path, or
    None when there is none."""
    lines = [f"{entry['take']} {closeups / f'{row}.png'} --faces {faces_of(surfaces, entry['take'])} "
             f"--seed {seed_of(entry['take'])}"
             for row, entry in sorted(objects.items()) if not raw_made(entry["take"])]
    if not lines:
        return None
    (out / "list.txt").write_text("\n".join(lines) + "\n")
    return out / "list.txt"


def make_pixal(inputs, out, seed, params):
    """Every prop object's take, made by the batch where missing; takes.json with each take's file hashes."""
    closeups = inputs["closeup"] / "closeups"
    objects = {row: entry for row, entry in prop_data.prop_objects(prop_data.record_at(inputs["props"])).items()
               if (closeups / f"{row}.png").exists()}  # one with no close-up failed the prop route there
    listing = batch_list(objects, closeups, inputs["surfaces"], out)
    if listing:
        done = subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/batch.py"), str(listing), "--who",
                               f"score pixal {prop_data.record_at(inputs['props'])['place']}", "--inventory",
                               str(inputs["inventory"])], cwd=REPO, capture_output=True, text=True)
        (out / "batch.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
        if done.returncode:
            raise RuntimeError(f"the Pixal3D batch failed (exit {done.returncode}); its log is batch.log")
    for row, entry in sorted(objects.items()):
        if raw_made(entry["take"]) and not made(entry["take"]):
            finish_here(entry["take"], closeups / f"{row}.png", faces_of(inputs["surfaces"], entry["take"]), out)
    takes = {row: {"take": entry["take"],
                   **{path.name: file_hash(path) for path in take_files(entry["take"]) if path.exists()}}
             for row, entry in objects.items()}
    (out / "takes.json").write_text(json.dumps(takes, indent=1))
    batch_gaps.write(out, [*batch_gaps.of(inputs), *unmade_gaps(objects)])


def unmade_gaps(objects):
    """The batch gap of each take the batch brought no raw model back for: it ran once, never again inside the
    batch."""
    return [batch_gaps.gap(f"{row}: Pixal3D made no model", "pixal", "takes",
                           (row, entry["take"], *entry.get("rows", ())),
                           [f"{row}: no {path.name}" for path in take_files(entry["take"]) if not path.exists()],
                           "the Pixal3D job ran once in the batch and brought no model back (batch.log)")
            for row, entry in sorted(objects.items()) if not raw_made(entry["take"])]


def pixal_faults(folder):
    return [] if (folder / "takes.json").exists() else ["no takes.json"]


def judge_takes(output, inputs, evidence):
    """Every prop object with a close-up has its take's three files, unchanged since made, and the surface data lists
    those takes and no prop object's take that was not made (one listed with no take would block the surface line).
    Takes the place's earlier routes made (the camp grounds' twelve beside the cairn) are not this row's to judge."""
    takes = json.loads((output / "takes.json").read_text())
    listed = json.loads(inputs["surfaces"].read_text()).get("takes", {})
    made_takes = {entry["take"] for entry in takes.values()}
    prop_takes = {entry["take"] for entry in prop_data.prop_objects(prop_data.record_at(inputs["props"])).values()}
    failing = [f"{take}: in the place's surface data but not made (its object has no close-up)"
               for take in sorted(listed) if take in prop_takes and take not in made_takes]
    for row, entry in sorted(takes.items()):
        for path in take_files(entry["take"]):
            if path.name not in entry or not path.exists():
                failing.append(f"{row}: no {path.name}")
            elif file_hash(path) != entry[path.name]:
                failing.append(f"{row}: {path.name} changed since it was made")
        if entry["take"] not in listed:
            failing.append(f"{row}: take {entry['take']} is not in the place's surface data")
    return verdict("takes", failing, len(takes), "takes")
