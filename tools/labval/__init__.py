"""The sim body validated on OpenCap's LabValidation (#98; Uhlrich et al. 2023, public on SimTK, never a private
copy): GEM-X Motion on one phone video gives a SOMA body (on_gemx.py, on a rented card in GEM-X's own environment),
the sim body runs it on the lab's floor at the subject's measured mass (the measure folder `prepared` writes, run by
tools/cloud/sim_measure), and its record is scored against the lab's own IK, force plates and EMG (`scored`,
`pooled`).

    prepared(soma, template, root, name, model, folder)   a run's job in a measure folder (subject<N>_<trial>_<Cam>)
    scored(run_folder, root)                               a run's measures (`_score`'s), root LabValidation's folder
    pooled(trials)                                         the measures over runs, per activity, per-subject CIs

Never the owner's patented joint-angle method (arXiv:2607.17639, NL4001444: no swing-twist split, no calibration
table of axes and offsets, no regression against the reference): the angles are MyoFullBody's own coordinates after
the sim body's fit (`_run`), scored by that paper's protocol only (`_score`)."""
import json
import pathlib
import re

import numpy as np
from scipy.spatial.transform import Rotation

from score.stages import sim_body
from tools.labval import _files, _grf, _job, _moments, _run, _score, _soma

# The matched envelope (the owner's validation, after OpenCap Monocular's 18): 15 coordinates.
MATCHED = ("ankle_angle_r", "ankle_angle_l", "knee_angle_r", "knee_angle_l", "hip_flexion_r", "hip_flexion_l",
           "hip_adduction_r", "hip_adduction_l", "hip_rotation_r", "hip_rotation_l", "pelvis_tilt", "pelvis_list",
           "lumbar_extension", "lumbar_bending", "lumbar_rotation")
ACTIVITIES = (("walkingTS", "walking (trunk sway)"), ("walking", "walking"), ("squats", "squats"),
              ("STS", "sit-to-stand"), ("DJ", "drop jump"))
# The knee's and ankle's markers in a LabValidation TRC ({s}: r or l): the epicondyles and malleoli.
# LabValidation's .trc carries the medial epicondyles and malleoli only in its `_study` set (side letters r and L).
MARKERS = {"knee": "{s}_knee_study", "mknee": "{s}_mknee_study", "ankle": "{s}_ankle_study", "mankle": "{s}_mankle_study"}
TRIAL_NAME = re.compile(r"^(subject\d+)_(.+)_(Cam\d+)$")


def activity_of(trial):
    """A LabValidation trial's activity by its name's start (walking1, walkingTS2, squats1, STS1, DJ3, ...)."""
    for start, name in ACTIVITIES:
        if trial.startswith(start):
            return name
    raise ValueError(f"{trial}: no LabValidation activity starts its name")


def prepared(soma, template, root, name, model, folder, gemx=None, moge=None):
    """Run `name`'s (subject<N>_<trial>_<Cam>) sim body job in measure folder `folder` (trials/<name>/: job.json,
    targets.npz, record.json; and scripts/go.sh): `soma` on_gemx.py's npz (a mapping), `template` the clips rig
    (people-clips-made's rig.npz), the subject's mass from its sessionMetadata.yaml under LabValidation's `root`,
    `model` the fetched MyoFullBody folder; `gemx` (GEM-X's contact_ik.npz) and `moge` (on_moge.py's npz) as
    `_soma.person` takes them."""
    subject_name, trial, camera = subject_of(name)
    subject = _files.metadata(_files.found(pathlib.Path(root) / subject_name, "metadata", trial))
    rig, worlds, segments, record = _soma.person(soma, template, gemx, moge, activity_of(trial))
    mine = pathlib.Path(folder) / "trials" / name
    mine.mkdir(parents=True, exist_ok=True)
    person = _job.written_person(name, rig, worlds, segments, subject["kg"], mine)
    _job.write_go(folder)
    record.update(name=name, subject=subject_name, trial=trial, camera=camera, measured=subject,
                  start=float(soma["start"]), gemx={**{key: str(soma[key]) for key in ("gemx", "soma", "variant")
                                                       if key in soma}, **({"variant": "contact_ik"} if gemx else {})})
    return _job.write_trial(folder, name, person, model, record)


def reference_heading(columns):
    """The reference pelvis' mean heading (radians about up) from its IK tilt, list and rotation, on the frames the
    run is scored on (the same frames as the run's own heading: a global turn about up is then taken off exactly).
    Frames outside the IK's window come back nan from the resampling and are left out; none inside raises."""
    angles = np.stack([columns[name] for name in _run.PELVIS], axis=1)
    inside = np.isfinite(angles).all(axis=1)
    if not inside.any():
        raise ValueError("the reference's IK covers none of the run's frames")
    turns = Rotation.from_euler("ZXY", angles[inside], degrees=True).as_matrix()
    return _run.heading(turns)


def angle_scores(times, predicted, ik_times, ik_columns, lag):
    """{coordinate: `_score.angle_measures`} of every predicted coordinate the IK holds, the IK moved by `lag`; a
    coordinate whose zero differs between the models (`_run.OWN_ZERO`) keeps only its offset-free measures."""
    found = {}
    for name, series in predicted.items():
        if name in ik_columns:
            measures = _score.angle_measures(series, _score.resampled(ik_times, ik_columns[name], times + lag))
            found[name] = ({key: value for key, value in measures.items() if key not in ("mae", "rmse")}
                           if name in _run.OWN_ZERO else measures)
    return found


def plate_at(force_times, plates, at):
    """Each foot's plate force and centre of pressure, low-passed (`_score.low_passed`), at times `at`."""
    return {side: (_score.resampled(force_times, _score.low_passed(force_times, values["force"]), at),
                   _score.resampled(force_times, _score.low_passed(force_times, values["cop"]), at))
            for side, values in plates.items()}


def force_scores(pushes, plates, own_heading, lab_heading, weight):
    """{side: {"vertical", "anterior"}: `_score.force_measures`, "stance carried": `_score.stance_carried`}: the run's
    pushes turned onto the lab's heading. A foot the run never pushes on the scored frames has r nan (flat), never 0:
    the stance it carries says why."""
    turn = _run.about_up(lab_heading - own_heading)
    forward = _score.forward_of(lab_heading)
    found = {}
    for side, (force, _) in pushes.items():
        mine, theirs = force @ turn.T, plates[side][0]
        found[side] = {"vertical": _score.force_measures(mine[:, 1], theirs[:, 1], weight),
                       "anterior": _score.force_measures(mine @ forward, theirs @ forward, weight),
                       "stance carried": _score.stance_carried(mine[:, 1], theirs[:, 1], weight)}
    return found


def knee_scores(entry, arrays, pushes, plates, marker_file, at, weight, height):
    """{side: `_score.moment_measures`} of the knee adduction moment, the run's on its tibias and pushes, the
    reference's on the TRC's knee markers and the plates, over the frames the plate carries the foot."""
    marker_times, markers = _files.trc(marker_file)
    found = {}
    for side, tibia in _run.TIBIAS.items():
        knee, forward = _score.marker_shank(markers, side, MARKERS)
        theirs = _score.knee_adduction(plates[side][0], plates[side][1], _score.resampled(marker_times, knee, at),
                                       _score.resampled(marker_times, forward, at), side)
        mine = _score.knee_adduction(pushes[side][0], pushes[side][1], _run.body_places(entry, arrays, tibia),
                                     _run.body_turns(entry, arrays, tibia)[:, :, 0], side)
        loaded = plates[side][0][:, 1] > _score.LOADED * weight
        found[side] = _score.moment_measures(mine, theirs, loaded, weight * height)
    return found


def emg_scores(entry, emg_file, at, times):
    """{muscle: `_score.timing_measures`} of every EMG channel that names a muscle the run has; the channels that
    name none listed under "not matched"."""
    emg_times, channels = _files.emg(emg_file)
    activations = _run.activations(entry)
    found, unmatched = {}, []
    for channel, values in channels.items():
        muscle = _score.emg_muscle(channel)
        if muscle not in activations:
            unmatched.append(channel)
            continue
        envelope = _score.resampled(emg_times, _score.envelope(emg_times, values), at)
        found[muscle] = {"channel": channel, **_score.timing_measures(times, activations[muscle], envelope)}
    return {**found, "not matched": unmatched}


def scored(run_folder, root):
    """One run's measures: the run in `run_folder` (out.json, out.npz, and record.json, `prepared`'s: its name and
    its GEM-X clip's start in the video, s) against its subject's IK, forces, markers and EMG under LabValidation's
    `root`. The shift is found on the angles once and used for every measure."""
    record = json.loads((pathlib.Path(run_folder) / "record.json").read_text())
    subject_name, trial, camera = subject_of(record["name"])
    subject_folder, start = pathlib.Path(root) / subject_name, float(record["start"])
    entry, arrays, rate = _run.read(run_folder)
    subject = _files.metadata(_files.found(subject_folder, "metadata", trial))
    weight = subject["kg"] * _files.G
    times = start + np.arange(len(entry["frames"])) / rate
    ik_times, ik_columns = _files.ik(_files.found(subject_folder, "ik", trial))
    lag = _score.shift(times, _run.angles(entry, arrays, 0.0), ik_times, ik_columns)  # on the legs alone
    at = times + lag
    lab_heading = reference_heading({name: _score.resampled(ik_times, ik_columns[name], at) for name in _run.PELVIS})
    predicted = _run.angles(entry, arrays, lab_heading)
    force_times, raw_plates = _files.forces(_files.found(subject_folder, "forces", trial))
    plates = plate_at(force_times, raw_plates, at)
    if np.nanmean(plates["right"][0][:, 1] + plates["left"][0][:, 1]) <= 0:
        raise ValueError(f"{trial}: the plates' y does not carry the weight; their frame is not y up")
    pushes = _run.pushes(entry)
    own_heading = _run.heading(_run.body_turns(entry, arrays, "pelvis"))
    passed, frames_passed = _score.residual_passes(*_run.residuals(entry), entry["weight N"], entry["com height"],
                                                   (sim_body.RESIDUAL_FORCE, sim_body.RESIDUAL_MOMENT))
    found = {"name": record["name"], "subject": subject_name, "trial": trial, "camera": camera,
             "activity": activity_of(trial), "shift s": lag, "kg": subject["kg"],
             "height": subject["height"], "angles": angle_scores(times, predicted, ik_times, ik_columns, lag),
             "forces": force_scores(pushes, plates, own_heading, lab_heading, weight),
             "residual": {"passes": passed, "frames passing": frames_passed},
             "grf": _grf.scores(at, pushes, _run.about_up(lab_heading - own_heading), force_times, raw_plates,
                                _score.forward_of(lab_heading), activity_of(trial), weight)}
    if found["activity"].startswith("walking"):
        found["knee adduction"] = knee_scores(entry, arrays, pushes, plates,
                                              _files.found(subject_folder, "markers", trial), at, weight,
                                              subject["height"])
    emg_file = _files.found(subject_folder, "emg", trial)
    found["emg"] = emg_scores(entry, emg_file, at, times) if emg_file else None
    return found


def moments_scored(run_folder, root, reference_folder):
    """One run's joint moments (`_moments.trial_measures`) against the reference ID on_opensim.py made of its trial
    (<reference_folder>/<subject>_<trial>.npz), on the same shift `scored` finds on the angles; None when that trial
    has no reference (the lab gave it no ID setup)."""
    record = json.loads((pathlib.Path(run_folder) / "record.json").read_text())
    subject_name, trial, camera = subject_of(record["name"])
    made = pathlib.Path(reference_folder) / f"{subject_name}_{trial}.npz"
    if not made.exists():
        return None
    subject_folder, start = pathlib.Path(root) / subject_name, float(record["start"])
    entry, arrays, rate = _run.read(run_folder)
    subject = _files.metadata(_files.found(subject_folder, "metadata", trial))
    weight = subject["kg"] * _files.G
    times = start + np.arange(len(entry["frames"])) / rate
    ik_times, ik_columns = _files.ik(_files.found(subject_folder, "ik", trial))
    lag = _score.shift(times, _run.angles(entry, arrays, 0.0), ik_times, ik_columns)
    at = times + lag
    ref_times, ref_columns, ref_knees = _moments.reference(made)
    theirs = {name: _score.resampled(ref_times, values, at) for name, values in ref_columns.items()}
    knees = {name: _score.resampled(ref_times, values, at) for name, values in ref_knees.items()}
    activity = activity_of(trial)
    walking = None
    if activity.startswith("walking"):
        force_times, raw = _files.forces(_files.found(subject_folder, "forces", trial))
        plates = plate_at(force_times, raw, at)
        loaded = {side[0]: plates[side][0][:, 1] > _score.LOADED * weight for side in ("right", "left")}
        windows = {side[0]: _moments.stances(force_times, _score.low_passed(force_times, raw[side]["force"])[:, 1]
                                             > _score.LOADED * weight) for side in ("right", "left")}
        walking = (at, ref_times, ref_knees, windows, loaded)
        for side, (force, centre) in _run.pushes(entry).items():
            tibia = _run.TIBIAS[side]
            knees[f"run kam {side[0]}"] = _score.knee_adduction(
                force, centre, _run.body_places(entry, arrays, tibia), _run.body_turns(entry, arrays, tibia)[:, :, 0],
                side)
    pelvis_height = _score.resampled(ik_times, ik_columns["pelvis_ty"], at) if "pelvis_ty" in ik_columns else None
    measures = _moments.trial_measures(_moments.predicted(entry), theirs, knees, weight * subject["height"], activity,
                                       walking, pelvis_height, at)
    return {"name": record["name"], "subject": subject_name, "trial": trial, "camera": camera, "activity": activity,
            "shift s": lag, "kg": subject["kg"], "height": subject["height"], "moments": measures}


def subject_of(name):
    """(subject, trial, camera) of a run's name, `subject<N>_<trial>_<Cam>`."""
    match = TRIAL_NAME.match(name)
    if not match:
        raise ValueError(f"{name}: not subject<N>_<trial>_<Cam>")
    return match.groups()


def by_subject(trials, value):
    """{subject: [value(trial) for its trials]} with the trials' nan values left in (the bootstrap skips them)."""
    found = {}
    for trial in trials:
        found.setdefault(trial["subject"], []).append(value(trial))
    return found


def pooled_angles(trials):
    """Each coordinate's MAE, centred MAE and RMSE bootstrapped over subjects, its mean r with the † flag (the
    reference's mean range under `_score.SMALL_RANGE`), and the matched envelope's MAE pooled over its 15."""
    names = sorted({name for trial in trials for name in trial["angles"]})
    found = {}
    for name in names:
        mine = [trial for trial in trials if name in trial["angles"]]
        row = {metric: _score.bootstrapped(by_subject(mine, lambda trial: trial["angles"][name][metric]))
               for metric in ("mae", "cmae", "rmse") if metric in mine[0]["angles"][name]}
        span = float(np.mean([trial["angles"][name]["range"] for trial in mine]))
        found[name] = {**row, "r": float(np.nanmean([trial["angles"][name]["r"] for trial in mine])),
                       "range": span, "dagger": span < _score.SMALL_RANGE}
    matched = {}
    for trial in trials:
        matched.setdefault(trial["subject"], []).extend(trial["angles"][name]["mae"] for name in MATCHED
                                                        if name in trial["angles"])
    return {"coordinates": found, "matched mae": _score.bootstrapped(matched) if matched else None}


def pooled_forces(trials):
    """Each foot's vertical and anterior force RMSE and peak error bootstrapped over subjects, its mean r over the
    trials it is defined on ("r trials": a foot the run never pushes has none), and the share of the plate's stance the
    run's foot carries, bootstrapped."""
    found = {}
    for side in ("right", "left"):
        for axis in ("vertical", "anterior"):
            def pick(metric):
                return lambda trial: trial["forces"][side][axis][metric]
            found[f"{side} {axis}"] = {"rmse %bw": _score.bootstrapped(by_subject(trials, pick("rmse %bw"))),
                                       "peak error %bw": _score.bootstrapped(by_subject(
                                           trials, lambda trial: abs(pick("peak error %bw")(trial)))),
                                       "r": float(np.nanmean([pick("r")(trial) for trial in trials])),
                                       "r trials": int(np.isfinite([pick("r")(trial) for trial in trials]).sum())}
        found[f"{side} stance carried"] = _score.bootstrapped(by_subject(
            trials, lambda trial, side=side: trial["forces"][side]["stance carried"]))
    return found


def pooled(trials):
    """The measures over trials (each `scored`'s, with its "subject"), per activity and over all: angles, forces,
    the knee adduction moment (walking), the residual pass fraction, muscle timing."""
    found = {}
    groups = {"all": trials, **{activity: [trial for trial in trials if trial["activity"] == activity]
                                for activity in sorted({trial["activity"] for trial in trials})}}
    for group, mine in groups.items():
        row = {"trials": len(mine), "subjects": len({trial["subject"] for trial in mine}),
               "angles": pooled_angles(mine), "forces": pooled_forces(mine),
               "residual pass fraction": _score.bootstrapped(by_subject(
                   mine, lambda trial: float(trial["residual"]["passes"])))}
        walking = [trial for trial in mine if trial.get("knee adduction")]
        if walking:
            row["knee adduction"] = {f"{side} {metric}": _score.bootstrapped(by_subject(
                walking, lambda trial, side=side, metric=metric: abs(trial["knee adduction"][side][metric])))
                for side in ("right", "left") for metric in ("peak error %bw.ht", "rmse %bw.ht")}
        timed = [trial for trial in mine if trial.get("emg")]
        muscles = sorted({muscle for trial in timed for muscle in trial["emg"] if muscle != "not matched"})
        row["emg"] = {muscle: {metric: _score.bootstrapped(by_subject(
            [trial for trial in timed if muscle in trial["emg"]],
            lambda trial, muscle=muscle, metric=metric: trial["emg"][muscle][metric]))
            for metric in ("on/off agreement", "r", "lag s")} for muscle in muscles}
        found[group] = row
    return found
