"""LabValidation's own files (Uhlrich et al. 2023, OpenCap's lab validation, public on SimTK:
simtk.org/projects/opencap), read as they come, nothing about them assumed that the file does not say: OpenSim storage (.mot, .sto: IK, forces,
EMG), TRC markers and sessionMetadata.yaml. A file that is not what its reader expects raises, naming what it found."""
import pathlib
import re

import numpy as np

G = 9.81  # m/s2: a subject's weight is its mass times this
TRANSLATIONS = ("pelvis_tx", "pelvis_ty", "pelvis_tz")  # an IK's coordinates in metres, never turned to degrees
# Where a subject's files lie under its folder (`subject<N>/`), by kind: glob patterns tried in order, `{trial}` the
# trial's name (walking1, squats1, STS1, DJ1, ...). The first that finds exactly one file is taken.
# SCORE's store copy (labvalidation/manifest.json's layout) holds them as ik/, forces/, markers/ and metadata.yaml.
WHERE = {"ik": ("OpenSimData/Mocap/IK/{trial}.mot", "**/IK/{trial}.mot", "ik/{trial}.mot"),
         "forces": ("ForceData/{trial}_forces.mot", "ForceData/{trial}.mot", "**/{trial}_forces.mot",
                    "forces/{trial}.mot"),
         "emg": ("EMGData/{trial}_EMG.sto", "EMGData/{trial}_EMG.mot", "EMGData/{trial}.sto", "EMGData/{trial}.mot",
                 "emg/{trial}.sto"),
         "markers": ("MarkerData/Mocap/{trial}.trc", "MarkerData/{trial}.trc", "**/Mocap/**/{trial}.trc",
                     "markers/{trial}.trc"),
         "metadata": ("sessionMetadata.yaml", "metadata.yaml")}
# A force column's side and quantity: R_/L_ (or _r_/_l_, right_/left_) and force v<x|y|z>, p<x|y|z> or torque <x|y|z>.
SIDES = {"r": "right", "right": "right", "l": "left", "left": "left"}
QUANTITY = (("force", re.compile(r"force_?v([xyz])$")), ("cop", re.compile(r"force_?p([xyz])$")),
            ("torque", re.compile(r"(?:torque|moment)_?([xyz])$")))


def found(subject_folder, kind, trial):
    """The one file of `kind` (WHERE) for `trial` under a subject's folder, else None for EMG (not every trial has
    it); any other kind missing, or a pattern matching several files, raises."""
    folder = pathlib.Path(subject_folder)
    for pattern in WHERE[kind]:
        hits = sorted(folder.glob(pattern.format(trial=trial)))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise ValueError(f"{folder}: {len(hits)} {kind} files for {trial}: {[str(hit) for hit in hits]}")
    if kind == "emg":
        return None
    raise FileNotFoundError(f"{folder}: no {kind} file for {trial} (tried {', '.join(WHERE[kind])})")


def storage(path):
    """An OpenSim storage file (.mot, .sto): (its header's key=value pairs, its column labels, its rows as an array)."""
    lines = pathlib.Path(path).read_text(errors="replace").splitlines()
    ends = [number for number, line in enumerate(lines) if line.strip().lower() == "endheader"]
    if not ends:
        raise ValueError(f"{path}: no endheader line, not an OpenSim storage file")
    header = dict(line.split("=", 1) for line in lines[:ends[0]] if "=" in line)
    labels = lines[ends[0] + 1].split("\t") if "\t" in lines[ends[0] + 1] else lines[ends[0] + 1].split()
    labels = [label.strip() for label in labels if label.strip()]  # LabValidation's forces end the line in a tab
    rows = np.array([[float(value) for value in line.split()] for line in lines[ends[0] + 2:] if line.strip()])
    if rows.ndim != 2 or rows.shape[1] != len(labels):
        raise ValueError(f"{path}: {len(labels)} labels but rows of {rows.shape[1:] or 'nothing'}")
    return {key.strip(): value.strip() for key, value in header.items()}, labels, rows


def timed(path):
    """A storage file as (times s, {label: column}), its time column first; raises when it has none."""
    _, labels, rows = storage(path)
    if labels[0].lower() != "time":
        raise ValueError(f"{path}: its first column is {labels[0]!r}, not time")
    return rows[:, 0], {label: rows[:, column] for column, label in enumerate(labels) if column}


def ik(path):
    """An IK .mot: (times s, {coordinate: degrees}); a file in radians (inDegrees=no) is turned to degrees, its
    translations (pelvis_tx, _ty, _tz) kept in metres."""
    header, _, _ = storage(path)
    times, columns = timed(path)
    if header.get("inDegrees", "yes").lower() == "no":
        columns = {name: values if name in TRANSLATIONS else np.degrees(values) for name, values in
                   columns.items()}
    return times, columns


def side_of(label):
    """'right', 'left' or None: a force column's side from its R_ / L_ / _r_ / _l_ / right_ / left_ token."""
    words = [word for word in re.split(r"[_\s]+", label.lower()) if word]
    sides = {SIDES[word] for word in words if word in SIDES}
    return sides.pop() if len(sides) == 1 else None


def forces(path):
    """A forces .mot (LabValidation: 2000 Hz, each foot's plates summed): (times s, {side: {"force", "cop",
    "torque": frames x 3}}), in the file's own frame and units (N, m, N m). A column of no side that is zero
    throughout is a plate no foot stood on and is left out (LabValidation's third plate, `3_ground_...`, in 90 of its
    144 force files, zero in every one); a column whose side or quantity is not read otherwise, or a foot short of any
    of the nine, raises with the labels."""
    times, columns = timed(path)
    feet = {"right": {}, "left": {}}
    for label, values in columns.items():
        side = side_of(label)
        if side is None and not np.any(values):
            continue
        tail = re.sub(r"[^a-z_]", "", label.lower().replace(" ", "_"))
        matched = [(quantity, axis.group(1)) for quantity, pattern in QUANTITY for axis in [pattern.search(tail)]
                   if axis]
        if side is None or len(matched) != 1:
            raise ValueError(f"{path}: column {label!r} is no foot's force, centre of pressure or torque")
        quantity, axis = matched[0]
        feet[side].setdefault(quantity, {})[axis] = values
    lacking = [f"{side} {quantity}" for side in feet for quantity, _ in QUANTITY
               if set(feet[side].get(quantity, {})) != {"x", "y", "z"}]
    if lacking:
        raise ValueError(f"{path}: lacks {', '.join(lacking)} (labels {list(columns)})")
    return times, {side: {quantity: np.stack([axes[axis] for axis in "xyz"], axis=1)
                          for quantity, axes in quantities.items()} for side, quantities in feet.items()}


def emg(path):
    """An EMG storage file: (times s, {channel: values}), as the file holds them (raw or an envelope: its rate says
    which, `score.envelope`)."""
    return timed(path)


def trc(path):
    """A TRC marker file: (times s, {marker: frames x 3 in metres}), its Units (mm or m) read from its header."""
    lines = pathlib.Path(path).read_text(errors="replace").splitlines()
    keys, values = lines[1].split("\t"), lines[2].split("\t")
    header = dict(zip([key.strip() for key in keys], [value.strip() for value in values]))
    scale = {"mm": 0.001, "m": 1.0}.get(header.get("Units", "").lower())
    if scale is None:
        raise ValueError(f"{path}: Units {header.get('Units')!r}, neither mm nor m")
    names = [name.strip() for name in lines[3].split("\t")[2:] if name.strip()]
    rows = [[float(value) if value.strip() else np.nan for value in line.split("\t")]
            for line in lines[5:] if line.strip()]
    width = 2 + 3 * len(names)
    data = np.array([row[:width] + [np.nan] * (width - len(row)) for row in rows])
    return data[:, 1], {name: data[:, 2 + 3 * index:5 + 3 * index] * scale for index, name in enumerate(names)}


def metadata(path):
    """A sessionMetadata.yaml's subject: {"kg", "height"} from its top-level mass_kg and height_m (plain key: value
    lines; no YAML library), raising when either is missing."""
    found = {}
    for line in pathlib.Path(path).read_text(errors="replace").splitlines():
        match = re.match(r"^(mass_kg|height_m)\s*:\s*([-+0-9.eE]+)\s*$", line)
        if match:
            found[match.group(1)] = float(match.group(2))
    if set(found) != {"mass_kg", "height_m"}:
        raise ValueError(f"{path}: no mass_kg and height_m (found {sorted(found)})")
    return {"kg": found["mass_kg"], "height": found["height_m"]}
