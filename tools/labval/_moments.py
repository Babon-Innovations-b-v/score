"""The sim body's joint moments against LabValidation's reference inverse dynamics (on_opensim.py's npz: the lab's
OpenSim ID on its scaled LaiArnoldModified2017 model, IK and plates), by OpenCap's protocol (Uhlrich et al. 2023,
PLOS Comput Biol 19(10): e1011462): moments in % of body weight times height; the 15 rotational degrees of freedom it
reports (hips 2 x 3, knees 2 x 1, ankles 2 x 2 with the subtalar, lumbar 3) plus the elbows' flexion and the
forearms' pronation (the same coordinates on both models); MAE, with RMSE and Pearson's r beside it.

- The run's moments are its inverse dynamics' generalized forces (out.json frames' `torques`, one per joint of its
  `joints`, the coordinate's name the joint's ending as `_run.coordinate_column` finds it): MyoFullBody's legs, lumbar
  and arms carry LaiArnoldModified2017's coordinate names, axes and signs (`_run`'s docstring), so a generalized force
  on a coordinate is the same quantity on both sides. The pelvis' lumbar is the run's sacrum-lumbar5 joint (its
  coordinates `flex_extension`, `lat_bending`, `axial_rotation`, the first about z with extension positive as the
  lab's): MyoFullBody spreads the lumbar over five levels, and the lowest level's own moment (`own torques`: that one
  joint's, OWN) is the moment the whole trunk above puts on the pelvis, as the lab's one back joint's is. Its `torques`
  is not: a leader's carries its followers' (L4/L5 at 0.185 of L5/S1's turn, the abdomen at 0.643), and with the lab's
  own kinematics and plates it scored the three 0.2 to 0.7 %BW*ht further from the lab's (#98, 2026-11-09).
- The shoulders (LaiArnoldModified2017's arm_flex, arm_add, arm_rot on one ball joint) have no matching coordinates
  in MyoFullBody (its shoulder is a scapula, clavicle and humerus chain with elevation-plane coordinates): a named gap.
- The knee adduction moment (walking): OpenCap's (computeKAM's joint reaction, the reference's `kam_*`) is held
  beside the external moment about the model's knee (`external_kam_*`), and the run's own is the external moment of
  its pushes about its tibia (`_score.knee_adduction`): MyoFullBody's knee has no adduction coordinate and the run no
  joint reaction, so the external definition is the like-for-like one; OpenCap's peak is reported against it too.
- Peaks: walking's early-stance KAM (OpenCap: the peak in the first half of each stance; a stance the plate carries
  the foot over `_score.LOADED` of the weight, whole inside the plate's record, the reference's peak on its own 100 Hz
  samples and the run's on its frames in the same window); squats' and sit-to-stand's peak knee
  extension moment (each side's most negative knee_angle moment over the scored frames: extension is negative);
  sit-to-stand's rising phase means of the hip extension, knee extension and ankle plantarflexion moments (OpenCap's
  measure; the rising phase here: from the last frame before the pelvis' highest upward speed where that speed is
  under RISE_SHARE of it to the pelvis' highest point, the lab's IK pelvis_ty: the paper does not say its detection).
- Pooled per activity: each degree of freedom's MAE bootstrapped over subjects (`_score.bootstrapped`); each peak's
  MAE over trials and its r^2 over the subjects' means (OpenCap averaged three trials a subject)."""
import numpy as np

from tools.labval import _run, _score

# LaiArnoldModified2017 coordinate -> the run's joint ending (None: the coordinate's own name).
MOMENTS = {**{f"{stem}_{side}": None for side in "rl" for stem in (
    "hip_flexion", "hip_adduction", "hip_rotation", "knee_angle", "ankle_angle", "subtalar_angle")},
    "lumbar_extension": "flex_extension", "lumbar_bending": "lat_bending",
    "lumbar_rotation": "axial_rotation", "elbow_flex_r": None, "elbow_flex_l": None,
    "pro_sup_r": None, "pro_sup_l": None}
OPENCAP = tuple(name for name in MOMENTS if not name.startswith(("elbow", "pro_sup")))  # its 15
OWN = ("lumbar_extension", "lumbar_bending", "lumbar_rotation")  # read from the joint's own moment (`own torques`)
GAPS = {"arm_flex, arm_add, arm_rot (both sides)": "no matching MyoFullBody coordinates (its shoulder is a "
                                                  "scapula-clavicle-humerus chain, elevation-plane coordinates)"}
RISE_SHARE = 0.1
EXTENSORS = {"hip extension": "hip_flexion", "knee extension": "knee_angle", "ankle plantarflexion": "ankle_angle"}
LEAST_STANCE = 0.2  # s


def reference(path):
    """(times, {coordinate: N m}, {"kam r", "kam l", "external kam r", "external kam l": N m}) of on_opensim's npz."""
    with np.load(path) as saved:
        names = [str(name) for name in saved["names"]]
        columns = {name[:-len("_moment")]: saved["values"][:, column] for column, name in enumerate(names)
                   if name.endswith("_moment")}
        knees = {f"{kind}kam {side}": saved[f"{kind.replace(' ', '_')}kam_{side}"].astype(float)
                 for kind in ("", "external ") for side in "rl"}
        return saved["time"].astype(float), columns, knees


def predicted(entry):
    """{coordinate: N m every frame} of the run's generalized forces on MOMENTS' coordinates, OWN's from the joint's own
    moment; a coordinate the run's joints do not name once, or a run without its joints' own moments, raises."""
    names = list(entry["joints"])
    if any("own torques" not in frame for frame in entry["frames"]):
        raise ValueError("the run's frames carry no `own torques` (a run before 2026-11-09): its back moment is not the "
                         "one joint's")
    rows = np.array([frame["torques"] for frame in entry["frames"]], dtype=float)
    own = np.array([frame["own torques"] for frame in entry["frames"]], dtype=float)
    found = {}
    for coordinate, ending in MOMENTS.items():
        column = _run.coordinate_column(names, ending or coordinate)
        if column is None:
            raise ValueError(f"the run's joints name {ending or coordinate} not once")
        found[coordinate] = (own if coordinate in OWN else rows)[:, column]
    return found


def series_measures(mine, theirs, scale):
    """MAE, RMSE and range (% of body weight times height) and r of a moment on the frames both give."""
    inside = np.isfinite(mine) & np.isfinite(theirs)
    if inside.sum() < 3:
        return {"mae %bw.ht": float("nan"), "rmse %bw.ht": float("nan"), "r": float("nan"),
                "range %bw.ht": float("nan"), "frames": int(inside.sum())}
    mine, theirs = 100.0 * mine[inside] / scale, 100.0 * theirs[inside] / scale
    return {"mae %bw.ht": float(np.mean(np.abs(mine - theirs))),
            "rmse %bw.ht": float(np.sqrt(np.mean((mine - theirs) ** 2))), "r": _score.correlation(mine, theirs),
            "range %bw.ht": float(theirs.max() - theirs.min()), "frames": int(inside.sum())}


def stances(times, loaded):
    """[(start, end) s] of each whole stance in a plate's record: a run of `loaded` samples at least LEAST_STANCE s
    long with an unloaded sample before and after it."""
    found, edges = [], np.flatnonzero(np.diff(np.concatenate([[0], loaded.astype(int), [0]])))
    for first, after in zip(edges[::2], edges[1::2]):
        if first > 0 and after < len(loaded) and times[after - 1] - times[first] >= LEAST_STANCE:
            found.append((float(times[first]), float(times[after - 1])))
    return found


def early_peaks(at, mine, ref_times, theirs, windows, scale):
    """[(the run's, the reference's)] early-stance peak (% of body weight times height) of each stance window
    (`stances`, s): the largest value in its first half, the reference's on its own samples, the run's on its frames
    (`at`, its times on the reference's clock); a stance whose first half holds under two of the run's frames or none
    of the reference's is left out."""
    found = []
    for start, end in windows:
        middle = start + (end - start) / 2.0
        ours = (at >= start) & (at <= middle) & np.isfinite(mine)
        lab = (ref_times >= start) & (ref_times <= middle) & np.isfinite(theirs)
        if ours.sum() >= 2 and lab.any():
            found.append((float(100.0 * mine[ours].max() / scale), float(100.0 * theirs[lab].max() / scale)))
    return found


def peak_extension(mine, theirs, scale):
    """(the run's, the reference's) peak knee extension moment (% of body weight times height, positive) on the
    frames both give: each one's most negative knee_angle moment, its sign turned."""
    inside = np.isfinite(mine) & np.isfinite(theirs)
    if not inside.any():
        return (float("nan"), float("nan"))
    return (float(-100.0 * mine[inside].min() / scale), float(-100.0 * theirs[inside].min() / scale))


def rising(times, pelvis_height):
    """The rising phase's frames (a boolean mask): from the last frame before the pelvis' highest upward speed at
    which that speed is under RISE_SHARE of it to the pelvis' highest point after it; all False when not seen."""
    found = np.zeros(len(times), dtype=bool)
    inside = np.isfinite(pelvis_height)
    if inside.sum() < 5:
        return found
    rows = np.flatnonzero(inside)
    speed = np.gradient(pelvis_height[rows], times[rows])
    fastest = int(np.argmax(speed))
    if speed[fastest] <= 0:
        return found
    slow = np.flatnonzero(speed[:fastest] < RISE_SHARE * speed[fastest])
    start = int(slow[-1]) if len(slow) else 0
    top = fastest + int(np.argmax(pelvis_height[rows][fastest:]))
    found[rows[start:top + 1]] = True
    return found


def rising_means(mine, theirs, phase, scale):
    """{extensor: (the run's, the reference's) mean over the rising phase, % of body weight times height, positive
    extension} of each side's hip, knee and ankle (`EXTENSORS`: each a negative generalized force)."""
    found = {}
    for label, stem in EXTENSORS.items():
        for side in "rl":
            name = f"{stem}_{side}"
            inside = phase & np.isfinite(mine[name]) & np.isfinite(theirs[name])
            found[f"{label} {side}"] = ((float(-100.0 * mine[name][inside].mean() / scale),
                                         float(-100.0 * theirs[name][inside].mean() / scale))
                                        if inside.any() else (float("nan"), float("nan")))
    return found


def peak_pooled(pairs_by_subject):
    """{"mae", "r2 of subject means", "trials", "subjects"} of peaks: {subject: [(the run's, the reference's)]}."""
    pairs = [pair for found in pairs_by_subject.values() for pair in found if np.isfinite(pair).all()]
    means = [np.nanmean(np.array(found, dtype=float), axis=0) for found in pairs_by_subject.values() if found]
    means = [mean for mean in means if np.isfinite(mean).all()]
    if not pairs:
        return {"mae %bw.ht": float("nan"), "r2 of subject means": float("nan"), "trials": 0, "subjects": 0}
    pairs, means = np.array(pairs), np.array(means)
    r = _score.correlation(means[:, 0], means[:, 1]) if len(means) > 2 else float("nan")
    return {"mae %bw.ht": float(np.mean(np.abs(pairs[:, 0] - pairs[:, 1]))),
            "mean run %bw.ht": float(pairs[:, 0].mean()), "mean reference %bw.ht": float(pairs[:, 1].mean()),
            "r2 of subject means": float(r ** 2), "trials": len(pairs), "subjects": len(means)}


def trial_measures(mine, theirs, knees, scale, activity, walking=None, pelvis_height=None, times=None):
    """One run's moment measures: `mine` the run's {coordinate: N m}, `theirs` the reference's and `knees` its knee
    adduction moments ({"kam r", ..., and "run kam r", "run kam l": the run's}), all on the run's frames; for walking
    `walking` = (the run's frames' times on the reference's clock, the reference's own times and knee adduction
    moments, {side letter: the plate's stance windows}, {side letter: the plate carries the foot on the run's frames});
    the IK's pelvis height and the frames' times for sit-to-stand."""
    found = {"moments": {name: series_measures(mine[name], theirs[name], scale) for name in MOMENTS
                         if name in theirs}}
    if activity.startswith("walking"):
        at, ref_times, ref_knees, windows, loaded = walking
        found["early kam"] = {side: {kind: early_peaks(at, knees[f"run kam {side}"], ref_times,
                                                       ref_knees[f"{kind} {side}"], windows[side], scale)
                                     for kind in ("kam", "external kam")} for side in "rl"}
        found["kam series"] = {side: series_measures(np.where(loaded[side], knees[f"run kam {side}"], np.nan),
                                                     knees[f"external kam {side}"], scale) for side in "rl"}
    if activity in ("squats", "sit-to-stand"):
        found["peak knee extension"] = {side: peak_extension(mine[f"knee_angle_{side}"], theirs[f"knee_angle_{side}"],
                                                             scale) for side in "rl"}
    if activity == "sit-to-stand":
        found["rising means"] = rising_means(mine, theirs, rising(times, pelvis_height), scale)
    return found


def pooled(trials):
    """Per activity and over all: each coordinate's MAE and RMSE bootstrapped over subjects with its mean r, OpenCap's
    15 pooled, and each peak's `peak_pooled`. `trials` are {"subject", "activity", "moments": `trial_measures`}."""
    def by_subject(rows, value):
        found = {}
        for row in rows:
            found.setdefault(row["subject"], []).append(value(row))
        return found

    groups = {"all": trials, **{activity: [row for row in trials if row["activity"] == activity]
                                for activity in sorted({row["activity"] for row in trials})}}
    found = {}
    for group, rows in groups.items():
        coordinates = {}
        for name in MOMENTS:
            have = [row for row in rows if name in row["moments"]["moments"]]
            if not have:
                continue
            coordinates[name] = {metric: _score.bootstrapped(by_subject(
                have, lambda row, metric=metric: row["moments"]["moments"][name][metric]))
                for metric in ("mae %bw.ht", "rmse %bw.ht")}
            coordinates[name]["r"] = float(np.nanmean([row["moments"]["moments"][name]["r"] for row in have]))
        fifteen = {}
        for row in rows:
            fifteen.setdefault(row["subject"], []).extend(
                row["moments"]["moments"][name]["mae %bw.ht"] for name in OPENCAP if name in row["moments"]["moments"])
        entry = {"trials": len(rows), "coordinates": coordinates,
                 "opencap 15 mae %bw.ht": _score.bootstrapped(fifteen) if fifteen else None}
        peaks = {}
        for row in rows:
            for side, kinds in row["moments"].get("early kam", {}).items():
                for kind, pairs in kinds.items():
                    peaks.setdefault(f"early-stance {kind} {side}", {}).setdefault(row["subject"], []).extend(pairs)
            for side, pair in row["moments"].get("peak knee extension", {}).items():
                peaks.setdefault(f"peak knee extension {side}", {}).setdefault(row["subject"], []).append(pair)
            for label, pair in row["moments"].get("rising means", {}).items():
                peaks.setdefault(f"rising mean {label}", {}).setdefault(row["subject"], []).append(pair)
        entry["peaks"] = {label: peak_pooled(pairs) for label, pairs in sorted(peaks.items())}
        kam_rows = [row for row in rows if "kam series" in row["moments"]]
        if kam_rows:
            entry["kam series (loaded frames, external)"] = {side: _score.bootstrapped(by_subject(
                kam_rows, lambda row, side=side: row["moments"]["kam series"][side]["rmse %bw.ht"]))
                for side in "rl"}
        found[group] = entry
    return found
