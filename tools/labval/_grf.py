"""Ground reaction forces scored as OpenCap scored them (Uhlrich et al. 2023, PLOS Comput Biol 19(10): e1011462,
Methods, "Experimental data" and "Error analysis"), per foot and both feet summed:

- Filter: the plates and the run's pushes low-passed alike, 4th-order Butterworth, zero lag, at the activity's
  cutoff (OpenCap's: walking 6 Hz, squats 4, sit-to-stand 4, drop jump 30), held under NYQUIST_SHARE of the run's
  Nyquist (a 30 Hz run carries nothing over 15 Hz: the drop jump's 30 becomes 12, on both sides alike).
- Error: MAE in % of body weight, each of the three axes (vertical; anterior-posterior along the subject's mean
  heading; medial-lateral, positive to the subject's right), and the same MAE as % of the measured signal's range over
  the trial; over every frame the run and the plates both give (OpenCap names no phase window for its GRF errors).
  RMSE and Pearson's r beside them (r nan, not 0, where the run's foot never pushes: flat).
- Beyond OpenCap (it scores neither): each whole stance's impulse (a stance: the frames the plate carries the foot
  over LOADED of the weight, the frame before and after inside the scored frames and unloaded), the run's over the
  same frames, % body weight times s; and the centre of pressure's travel inside each stance, anterior-posterior and
  medial-lateral, mm, each side centred on its own stance mean over the frames both carry the foot: the run's world
  is not registered to the lab's, so where on the floor the foot stands is not comparable, only how the pressure moves
  under it. The plate's centre of pressure is read unfiltered (its value under a foot it barely carries is noise the
  filter would smear into the stance)."""
import numpy as np
from scipy import signal

from tools.labval import _score

CUTOFFS = {"walking": 6.0, "walking (trunk sway)": 6.0, "squats": 4.0, "sit-to-stand": 4.0, "drop jump": 30.0}
NYQUIST_SHARE = 0.8
AXES = ("vertical", "anterior-posterior", "medial-lateral")


def cutoff_of(activity, rate):
    """The activity's OpenCap cutoff (Hz), held under NYQUIST_SHARE of `rate`'s Nyquist."""
    return min(CUTOFFS[activity], NYQUIST_SHARE * rate / 2.0)


def filtered(times, values, cutoff):
    """`values` (frames x n) low-passed at `cutoff` Hz, 4th order, zero lag."""
    rate = 1.0 / float(np.median(np.diff(times)))
    numerator, denominator = signal.butter(4, cutoff / (rate / 2.0))
    return signal.filtfilt(numerator, denominator, np.asarray(values, dtype=float), axis=0)


def directions(forward):
    """(3 x 3) rows: up, forward and to the subject's right (forward x up), of a forward across the ground."""
    forward = np.asarray(forward, dtype=float)
    return np.stack([np.array([0.0, 1.0, 0.0]), forward, np.cross(forward, [0.0, 1.0, 0.0])])


def axis_measures(predicted, reference, weight):
    """MAE, RMSE (% body weight), MAE as % of the reference's range over the trial, and r of one axis."""
    inside = np.isfinite(predicted) & np.isfinite(reference)
    mine, theirs = 100.0 * predicted[inside] / weight, 100.0 * reference[inside] / weight
    span = float(theirs.max() - theirs.min()) if inside.any() else float("nan")
    mae = float(np.mean(np.abs(mine - theirs))) if inside.any() else float("nan")
    return {"mae %bw": mae, "mae %range": 100.0 * mae / span if span > 0 else float("nan"),
            "rmse %bw": float(np.sqrt(np.mean((mine - theirs) ** 2))) if inside.any() else float("nan"),
            "r": _score.correlation(mine, theirs) if inside.sum() > 2 else float("nan"), "range %bw": span,
            "frames": int(inside.sum())}


def stances(reference_vertical, weight):
    """[(first, last)] frame of each whole stance: the plate carries the foot over LOADED of the weight on every frame
    from first to last, and on neither neighbour, both inside (finite)."""
    loaded = np.nan_to_num(reference_vertical, nan=-1.0) > _score.LOADED * weight
    found, start = [], None
    for frame, carried in enumerate(loaded):
        if carried and start is None:
            start = frame
        if not carried and start is not None:
            if start > 0 and np.isfinite(reference_vertical[start - 1]) and np.isfinite(reference_vertical[frame]):
                found.append((start, frame - 1))
            start = None
    return found


def stance_measures(step, mine, theirs, my_cop, their_cop, frames, weight):
    """One stance's impulse per axis (run, plate, error; % body weight times s) and its centred centre-of-pressure
    MAE (mm) along anterior-posterior and medial-lateral over the frames both carry the foot; `mine`, `theirs` frames x
    3 on (up, forward, right), the cops (frames x 3, m) on the same axes."""
    first, last = frames
    window = slice(first, last + 1)
    impulse = {}
    for index, axis in enumerate(AXES):
        run = 100.0 * step * float(np.nansum(mine[window, index])) / weight
        plate = 100.0 * step * float(np.nansum(theirs[window, index])) / weight
        impulse[axis] = {"run %bw.s": run, "plate %bw.s": plate, "error %bw.s": run - plate}
    both = (mine[window, 0] > _score.LOADED * weight) & np.isfinite(my_cop[window]).all(axis=1) \
        & np.isfinite(their_cop[window]).all(axis=1)
    cop = {}
    for index, axis in ((1, "anterior-posterior"), (2, "medial-lateral")):
        if both.sum() < 2:
            cop[axis] = float("nan")
            continue
        run, plate = my_cop[window, index][both], their_cop[window, index][both]
        cop[axis] = 1000.0 * float(np.mean(np.abs((run - run.mean()) - (plate - plate.mean()))))
    return {"frames": [int(first), int(last)], "impulse": impulse, "cop mae mm": cop, "cop frames": int(both.sum())}


def scores(times, pushes, turn, plate_times, plates, forward, activity, weight):
    """{"cutoff hz", "feet": {right, left, both: {axis: `axis_measures`}}, "stances": {side: [`stance_measures`]}} of
    the run's pushes ({side: (force, cop)} in its own frame, sampled at `times`, the reference's clock) turned by `turn`
    onto the lab, against the plates ({side: {"force", "cop"}} at `plate_times`, the lab's frame)."""
    rate = 1.0 / float(np.median(np.diff(times)))
    cutoff = cutoff_of(activity, rate)
    onto = directions(forward)
    feet, stance_rows, sums = {}, {}, []
    for side, (force, cop) in pushes.items():
        mine = filtered(times, np.asarray(force, dtype=float) @ np.asarray(turn).T, cutoff) @ onto.T
        theirs = _score.resampled(plate_times, filtered(plate_times, plates[side]["force"], cutoff), times) @ onto.T
        my_cop = np.asarray(cop, dtype=float) @ np.asarray(turn).T @ onto.T
        their_cop = _score.resampled(plate_times, plates[side]["cop"], times) @ onto.T
        feet[side] = {axis: axis_measures(mine[:, index], theirs[:, index], weight) for index, axis in enumerate(AXES)}
        stance_rows[side] = [stance_measures(1.0 / rate, mine, theirs, my_cop, their_cop, frames, weight)
                             for frames in stances(theirs[:, 0], weight)]
        sums.append((mine, theirs))
    mine, theirs = sum(pair[0] for pair in sums), sum(pair[1] for pair in sums)
    feet["both"] = {axis: axis_measures(mine[:, index], theirs[:, index], weight) for index, axis in enumerate(AXES)}
    return {"cutoff hz": cutoff, "feet": feet, "stances": stance_rows}


def stance_values(trial, metric):
    """Every stance's value of `metric` (a function of one `stance_measures` row) in a scored trial, both feet."""
    return [metric(row) for side in ("right", "left") for row in trial["grf"]["stances"][side]]


def spread(values):
    """mean, SD (over the finite values) and their count."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not len(values):
        return {"mean": float("nan"), "sd": float("nan"), "n": 0}
    return {"mean": float(values.mean()), "sd": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "n": int(len(values))}


def by_subject(trials, value):
    """{subject: [values]}: `value(trial)` a list for each trial, its subject's lists joined; a subject with no finite
    value left out (it adds nothing to the pooled mean, and a draw of only such subjects would have no mean)."""
    found = {}
    for trial in trials:
        found.setdefault(trial["subject"], []).extend(value(trial))
    return {subject: values for subject, values in found.items() if np.isfinite(np.asarray(values, float)).any()}


def pooled_group(trials):
    """One group's GRF rows: per foot (and both) and axis, the MAE (% BW: mean, SD over trials, the per-subject
    bootstrap's CI), the MAE as % of range, RMSE, r over the trials it is defined on; OpenCap's three-axis average;
    the stance carried; and the stances' impulse errors and centred centre-of-pressure MAE."""
    found = {"trials": len(trials), "subjects": len({trial["subject"] for trial in trials})}
    for foot in ("right", "left", "both"):
        for axis in AXES:
            def pick(metric, foot=foot, axis=axis):
                return lambda trial: [trial["grf"]["feet"][foot][axis][metric]]
            rs = [trial["grf"]["feet"][foot][axis]["r"] for trial in trials]
            found[f"{foot} {axis}"] = {
                "mae %bw": {**spread([pick("mae %bw")(trial)[0] for trial in trials]),
                            "ci": _score.bootstrapped(by_subject(trials, pick("mae %bw")))},
                "mae %range": spread([pick("mae %range")(trial)[0] for trial in trials]),
                "rmse %bw": spread([pick("rmse %bw")(trial)[0] for trial in trials]),
                "r": spread(rs), "r trials": int(np.isfinite(rs).sum())}
        found[f"{foot} 3-axis mae %bw"] = spread([np.mean([trial["grf"]["feet"][foot][axis]["mae %bw"]
                                                           for axis in AXES]) for trial in trials])
    for side in ("right", "left"):
        found[f"{side} stance carried"] = spread([trial["forces"][side]["stance carried"] for trial in trials])
    for axis in AXES:
        error = lambda row, axis=axis: abs(row["impulse"][axis]["error %bw.s"])
        found[f"impulse {axis} abs error %bw.s"] = {
            **spread([value for trial in trials for value in stance_values(trial, error)]),
            "ci": _score.bootstrapped(by_subject(trials, lambda trial, error=error: stance_values(trial, error)))
            if any(stance_values(trial, error) for trial in trials) else None}
    vertical = lambda row: 100.0 * row["impulse"]["vertical"]["error %bw.s"] / row["impulse"]["vertical"]["plate %bw.s"]
    found["impulse vertical error % of plate"] = spread([value for trial in trials
                                                        for value in stance_values(trial, vertical)])
    for axis in ("anterior-posterior", "medial-lateral"):
        found[f"cop {axis} centred mae mm"] = spread([value for trial in trials for value in stance_values(
            trial, lambda row, axis=axis: row["cop mae mm"][axis])])
    found["stances"] = sum(len(stance_values(trial, lambda row: 0)) for trial in trials)
    return found


def pooled(trials):
    """GRF rows for every group: all, each activity, each camera, each activity and camera."""
    trials = [trial for trial in trials if trial.get("grf")]
    groups = {"all": trials}
    for key in ("activity", "camera"):
        for value in sorted({trial[key] for trial in trials}):
            groups[value] = [trial for trial in trials if trial[key] == value]
    for activity in sorted({trial["activity"] for trial in trials}):
        for camera in sorted({trial["camera"] for trial in trials}):
            mine = [trial for trial in trials if trial["activity"] == activity and trial["camera"] == camera]
            if mine:
                groups[f"{activity} | {camera}"] = mine
    return {group: pooled_group(mine) for group, mine in groups.items()}


def table(pooled_rows):
    """`pooled`'s rows as a table (header first, every cell text): group, trials, subjects, measure, mean, SD, n (the
    values the mean is over: trials, or stances), the per-subject bootstrap's 95% CI where it was drawn."""
    rows = [["group", "trials", "subjects", "measure", "mean", "sd", "n", "ci low", "ci high"]]
    for group, found in pooled_rows.items():
        head = [group, str(found["trials"]), str(found["subjects"])]
        for measure, value in found.items():
            if not isinstance(value, dict):
                continue
            parts = value if "mean" not in value else {"": value}
            for part, numbers in parts.items():
                if not isinstance(numbers, dict) or "mean" not in numbers:
                    continue
                ci = numbers.get("ci") or {}
                name = f"{measure} {part}".strip()
                rows.append([*head, name, f"{numbers['mean']:.3f}", f"{numbers['sd']:.3f}",
                             str(numbers["n"]) if part != "r" else f"{value['r trials']} of {found['trials']}",
                             f"{ci['low']:.3f}" if ci else "", f"{ci['high']:.3f}" if ci else ""])
    return rows
