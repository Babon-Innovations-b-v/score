"""The measures of a sim body run against LabValidation's reference, by the protocol of the owner's GEM-X validation
(Kardolus, Hendriks and Jansen, arXiv:2607.17639: its alignment, metrics, flag and bootstrap, never its angle method):

- Time: one sub-frame shift a trial (`shift`), found on the joint angles and used for every measure of it: the
  reference is moved, never the prediction, to the shift that minimises the centred residual pooled across both
  sides' hip, knee and ankle flexion (each series less its mean over the overlap).
- Angles, per coordinate: RMSE, MAE, centred MAE (the trial's mean error removed) and Pearson's r; r flagged † where
  the reference's range of motion is under SMALL_RANGE degrees (MAE stays meaningful there).
- Ground reaction force, per foot, vertical and anterior (along the subject's mean heading): RMSE and peak error as %
  of body weight, and r, against the plates low-passed as the sim body's path is (CUTOFF, zero lag).
- Knee adduction moment (walking): the external moment of each foot's push about its knee, about the tibia's forward
  axis (positive is adduction on both sides), in % of body weight times height: its peak's error and RMSE over the
  frames the plate carries the foot (over LOADED of the weight), the same computation on both sides of the comparison.
- Residual: a trial passes when every frame's pelvis residual is within the stage's limits (2% of the weight, 1% of
  it times the centre of mass' height); the pass fraction is over trials.
- Muscle timing (where the trial has EMG): each matched muscle's envelope and the run's activation, each on where it
  is over ON_SHARE of its range: the share of frames on which the two agree, and the lag at their cross-correlation's
  peak.
- Uncertainty: a per-subject bootstrap (DRAWS draws of the subjects with replacement) of a pooled mean, its 95% CI."""
import re

import numpy as np
from scipy import signal

SMALL_RANGE = 15.0  # degrees: the reference's range of motion under which r is flagged †
FLEXIONS = ("hip_flexion_r", "hip_flexion_l", "knee_angle_r", "knee_angle_l", "ankle_angle_r", "ankle_angle_l")
MOST_SHIFT = 1.0  # s either way the reference may be moved
# Of the shorter one's frames (the prediction's, or the reference's window) the two must share: more than half, so
# MOST_SHIFT is reachable on a walking trial's one gait cycle (1.2 to 1.9 s; LabValidation's video and mocap are cut
# to the same length but not the same instants: at 0.8 the shift could move only about 0.27 s and sat on that edge
# for 132 of 211 walking trials whose five cameras all agreed the walk was out of phase there, #98, 2026-11-06).
OVERLAP = 0.5
CUTOFF = 6.0  # Hz, 4th-order Butterworth, zero lag: the sim body's own path filter (Winter 2009)
LOADED = 0.05  # of the body weight: a foot the plate carries
ON_SHARE = 0.25  # of a signal's range over its minimum: a muscle on
EMG_BAND = (20.0, 450.0)  # Hz: raw EMG's band before rectifying (a file over RAW_RATE is raw)
RAW_RATE = 1000.0  # Hz
LAG_MOST = 0.3  # s either way the timing's cross-correlation looks
DRAWS = 20000
# EMG channel names (lower case, letters only, the side token removed) -> MyoFullBody's muscle stem.
EMG_MUSCLES = {"vaslat": ("vl", "vaslat", "vastuslateralis", "vastlat"),
               "vasmed": ("vm", "vasmed", "vastusmedialis", "vastmed"),
               "recfem": ("rf", "recfem", "rectusfemoris"), "bflh": ("bf", "bflh", "bicepsfemoris"),
               "semiten": ("st", "semiten", "semitendinosus"), "tibant": ("ta", "tibant", "tibialisanterior"),
               "gasmed": ("mg", "gasmed", "gastrocmed", "medialgastrocnemius", "gastrocnemiusmedialis"),
               "gaslat": ("lg", "gaslat", "gastroclat", "lateralgastrocnemius", "gastrocnemiuslateralis"),
               "soleus": ("sol", "soleus"), "glmed1": ("gmed", "glmed", "gluteusmedius"),
               "glmax1": ("gmax", "glmax", "gluteusmaximus")}


def resampled(times, values, at):
    """`values` (a series, or frames x n) at times `at`, linearly; nan outside `times`."""
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        return np.interp(at, times, values, left=np.nan, right=np.nan)
    return np.stack([np.interp(at, times, column, left=np.nan, right=np.nan) for column in values.T], axis=1)


def centred_cost(shift, times, predicted, ref_times, reference):
    """The mean squared centred residual, pooled over the series both give, of the reference moved by `shift` (s);
    inf when the two share under OVERLAP of the shorter one's frames at the prediction's rate (LabValidation's IK
    covers only its window of a drop jump's video: 1.0 of 2.5 s, subject10_DJ1)."""
    times = np.asarray(times, dtype=float)
    step = float(np.median(np.diff(times)))
    shorter = min(len(times), int((ref_times[-1] - ref_times[0]) / step) + 1)
    costs, covered = [], []
    for name, mine in predicted.items():
        theirs = resampled(ref_times, reference[name], times + shift)
        inside = np.isfinite(theirs) & np.isfinite(mine)
        covered.append(inside.sum() / shorter)
        if inside.sum() > 2:
            error = (mine[inside] - mine[inside].mean()) - (theirs[inside] - theirs[inside].mean())
            costs.append(np.mean(error ** 2))
    if not costs or min(covered) < OVERLAP:
        return np.inf
    return float(np.mean(costs))


def shift(times, predicted, ref_times, reference, around=0.0):
    """The sub-frame shift (s) of the reference minimising `centred_cost` over FLEXIONS within MOST_SHIFT of
    `around`: every reference frame step first, then a golden section inside the best step's neighbours."""
    series = {name: np.asarray(predicted[name], dtype=float) for name in FLEXIONS}
    step = float(np.median(np.diff(ref_times)))
    grid = around + np.arange(-MOST_SHIFT, MOST_SHIFT + step / 2, step)
    costs = [centred_cost(value, times, series, ref_times, reference) for value in grid]
    best = int(np.argmin(costs))
    if not np.isfinite(costs[best]):
        raise ValueError("the reference never covers the prediction within the shifts tried")
    low, high = grid[max(best - 1, 0)], grid[min(best + 1, len(grid) - 1)]
    ratio = (np.sqrt(5.0) - 1.0) / 2.0
    for _ in range(40):
        left, right = high - ratio * (high - low), low + ratio * (high - low)
        if centred_cost(left, times, series, ref_times, reference) <= centred_cost(right, times, series, ref_times,
                                                                                    reference):
            high = right
        else:
            low = left
    return float((low + high) / 2.0)


def correlation(first, second):
    """Pearson's r, nan when either is flat."""
    first, second = first - first.mean(), second - second.mean()
    spread = np.sqrt((first ** 2).sum() * (second ** 2).sum())
    return float((first * second).sum() / spread) if spread > 0 else float("nan")


def angle_measures(predicted, reference):
    """RMSE, MAE, centred MAE (degrees), r and its † flag (the reference's range under SMALL_RANGE) of one
    coordinate on the frames both give."""
    inside = np.isfinite(predicted) & np.isfinite(reference)
    mine, theirs = predicted[inside], reference[inside]
    error = mine - theirs
    span = float(theirs.max() - theirs.min())
    return {"rmse": float(np.sqrt(np.mean(error ** 2))), "mae": float(np.mean(np.abs(error))),
            "cmae": float(np.mean(np.abs(error - error.mean()))), "r": correlation(mine, theirs),
            "range": span, "dagger": span < SMALL_RANGE, "frames": int(inside.sum())}


def low_passed(times, values):
    """`values` (frames x n, or a series) low-passed at CUTOFF, zero lag."""
    rate = 1.0 / float(np.median(np.diff(times)))
    numerator, denominator = signal.butter(4, CUTOFF / (rate / 2.0))
    return signal.filtfilt(numerator, denominator, np.asarray(values, dtype=float), axis=0)


def peak_error(predicted, reference):
    """The error at the reference's largest swing: the prediction's extreme of the same sign less the reference's."""
    if abs(reference.max()) >= abs(reference.min()):
        return float(predicted.max() - reference.max())
    return float(predicted.min() - reference.min())


def force_measures(predicted, reference, weight):
    """RMSE and peak error (% of body weight) and r of one force channel on the frames both give."""
    inside = np.isfinite(predicted) & np.isfinite(reference)
    mine, theirs = 100.0 * predicted[inside] / weight, 100.0 * reference[inside] / weight
    return {"rmse %bw": float(np.sqrt(np.mean((mine - theirs) ** 2))), "peak error %bw": peak_error(mine, theirs),
            "r": correlation(mine, theirs), "range %bw": float(theirs.max() - theirs.min()),
            "frames": int(inside.sum())}


def stance_carried(predicted, reference, weight):
    """The share of the frames the plate carries the foot (over LOADED of the weight) on which the run's foot is
    carried too; nan when the plate carries it on none of the frames both give."""
    inside = np.isfinite(predicted) & np.isfinite(reference)
    loaded = inside & (np.nan_to_num(reference) > LOADED * weight)
    if not loaded.any():
        return float("nan")
    return float(np.mean(predicted[loaded] > LOADED * weight))


def forward_of(heading):
    """The unit forward direction across the ground of a heading (radians about up): Ry(heading) x."""
    return np.array([np.cos(heading), 0.0, -np.sin(heading)])


def knee_adduction(force, centre, knee, forward, side):
    """The external knee adduction moment (N m, every frame): (centre of pressure - knee) x force about the tibia's
    forward axis, positive adduction on both sides (the right's moment about forward, the left's against it; x
    forward, y up, z to the subject's right, as OpenSim's frames)."""
    moment = np.cross(np.asarray(centre) - np.asarray(knee), np.asarray(force))
    about = np.einsum("fa,fa->f", moment, np.asarray(forward))
    return about if side == "right" else -about


def marker_shank(markers, side, names):
    """(knee centre, the tibia's forward axis) every frame from markers: `names` ({"knee", "mknee", "ankle",
    "mankle"} for the side, each `{s}` the side's letter, r or L as LabValidation writes them), the knee the epicondyles' middle, up the ankle's
    middle to the knee, the axis to the subject's right from the medial to the lateral epicondyle on the right (from
    lateral to medial on the left), forward = up x right."""
    letter = {"right": "r", "left": "L"}[side]
    get = {key: np.asarray(markers[name.format(s=letter)], dtype=float) for key, name in names.items()}
    knee = (get["knee"] + get["mknee"]) / 2.0
    up = knee - (get["ankle"] + get["mankle"]) / 2.0
    across = get["knee"] - get["mknee"] if side == "right" else get["mknee"] - get["knee"]
    forward = np.cross(up, across)
    return knee, forward / np.linalg.norm(forward, axis=1, keepdims=True)


def moment_measures(predicted, reference, loaded, scale):
    """The knee adduction moment's peak error and RMSE (% of body weight times height) over the `loaded` frames."""
    inside = loaded & np.isfinite(predicted) & np.isfinite(reference)
    if not inside.any():
        return {"peak error %bw.ht": float("nan"), "rmse %bw.ht": float("nan"), "frames": 0}
    mine, theirs = 100.0 * predicted[inside] / scale, 100.0 * reference[inside] / scale
    return {"peak error %bw.ht": float(mine.max() - theirs.max()),
            "rmse %bw.ht": float(np.sqrt(np.mean((mine - theirs) ** 2))), "frames": int(inside.sum())}


def residual_passes(force, moment, weight, com_height, limits):
    """(the trial passes, the share of its frames that pass): every frame's pelvis residual force within limits'
    force share of the weight and its moment within the moment share of the weight times the centre's height."""
    good = ((np.linalg.norm(force, axis=1) <= limits[0] * weight)
            & (np.linalg.norm(moment, axis=1) <= limits[1] * weight * com_height))
    return bool(good.all()), float(good.mean())


# Words a channel's name carries that name no muscle: LabValidation's processed EMG (the store's emg/<trial>.sto)
# names its channels <muscle>_<side>_activation.
NOT_MUSCLE = ("activation", "emg")


def emg_muscle(channel):
    """(MyoFullBody muscle, e.g. vaslat_r) an EMG channel's name reads as, else None; LabValidation's own suffix
    "activation" (vaslat_r_activation) is not part of the muscle's name."""
    words = [word for word in re.split(r"[^a-z]+", channel.lower()) if word and word not in NOT_MUSCLE]
    sides = [word for word in words if word in ("r", "l", "right", "left")]
    if len(sides) != 1:
        return None
    rest = "".join(word for word in words if word not in sides)
    stems = [stem for stem, spellings in EMG_MUSCLES.items() if rest in spellings]
    return f"{stems[0]}_{sides[0][0]}" if len(stems) == 1 else None


def envelope(times, values):
    """An EMG channel's linear envelope: a raw channel (sampled over RAW_RATE) band-passed (EMG_BAND), rectified and
    low-passed at CUTOFF; a slower one (already an envelope) rectified alone."""
    rate = 1.0 / float(np.median(np.diff(times)))
    values = np.asarray(values, dtype=float)
    if rate <= RAW_RATE:
        return np.abs(values)
    numerator, denominator = signal.butter(4, [EMG_BAND[0] / (rate / 2.0), EMG_BAND[1] / (rate / 2.0)], "bandpass")
    return low_passed(times, np.abs(signal.filtfilt(numerator, denominator, values)))


def switched_on(values):
    """Where a signal is on: over ON_SHARE of its range above its minimum."""
    return values > values.min() + ON_SHARE * (values.max() - values.min())


def timing_measures(times, activation, envelope_at):
    """On/off agreement (share of frames), Pearson's r of the two series at no lag (the angles' shift already put
    them in time; r is the same for any normalisation of either, OpenCap's to each participant's maximum included)
    and the lag (s, positive: the activation later) at the peak of the centred cross-correlation within LAG_MOST,
    of an activation and the EMG envelope sampled at the same `times`. r is nan when either series is flat."""
    inside = np.isfinite(envelope_at)
    mine, theirs = activation[inside], envelope_at[inside]
    agree = float(np.mean(switched_on(mine) == switched_on(theirs)))
    step = float(np.median(np.diff(times)))
    most = int(round(LAG_MOST / step))
    mine, theirs = mine - mine.mean(), theirs - theirs.mean()
    spread = float(np.sqrt(np.sum(mine * mine) * np.sum(theirs * theirs)))
    pearson = float(np.sum(mine * theirs) / spread) if spread > 0 else float("nan")
    lags = np.arange(-most, most + 1)
    scores = [np.sum(mine[max(lag, 0):len(mine) + min(lag, 0)] * theirs[max(-lag, 0):len(theirs) - max(lag, 0)])
              for lag in lags]
    return {"on/off agreement": agree, "r": pearson, "lag s": float(lags[int(np.argmax(scores))] * step)}


def bootstrapped(by_subject, draws=DRAWS, seed=0):
    """A pooled mean and its 95% CI by a per-subject bootstrap: {subject: [values]} -> {"mean", "low", "high",
    "subjects", "values"}; each draw takes the subjects with replacement and pools all their values."""
    subjects = sorted(by_subject)
    sums = np.array([np.nansum(by_subject[subject]) for subject in subjects])
    counts = np.array([np.isfinite(np.asarray(by_subject[subject], dtype=float)).sum() for subject in subjects])
    picks = np.random.default_rng(seed).integers(0, len(subjects), size=(draws, len(subjects)))
    means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    return {"mean": float(sums.sum() / counts.sum()), "low": float(np.percentile(means, 2.5)),
            "high": float(np.percentile(means, 97.5)), "subjects": len(subjects), "values": int(counts.sum())}
