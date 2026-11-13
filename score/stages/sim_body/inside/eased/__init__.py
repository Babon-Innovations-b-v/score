"""A clip's start eased (2026-11-13): Kimodo's standing clip starts with a jolt (the mean acceleration of its segments
0.5 to 0.7 m/s2 on frames 1 to 3, at most 0.4 after); on frame 2 its right foot carried 0 N and every standing body
under Moon gravity held 1.5 to 3.2 N m of residual moment, over its 1 N m (base, greenhouse, hangar). The sim body
follows the clip with its first frames steadied (`steadied`: from its first pose at one steady acceleration to the
clip's own place and speed), over the fewest frames, at most MOST, that keep its start within the clip's own largest
acceleration after them; a calm start is followed as it came. Never from rest: a start held still and blended in
(smootherstep from the first pose) made the body catch up with the clip's own drift, 6 N m on base's frame 21
(2026-11-13). Only the path the sim body follows is eased: the stage's `poses` (the drawn person) stay the clip's
own. Numpy and scipy only."""
import numpy as np
from scipy.spatial.transform import Rotation

RATE = 30.0  # the clips' frames a second (the job's "rate", the stage's RATE)
MOST = 60  # frames: 2 s at RATE
JUDGED = 3  # frames: a start is judged on its first three accelerations (frames 1 to 3) at least
SLACK = 1e-9  # m/s2: a start this little over the clip's range is within it (rounding)


def mean_acceleration(worlds, rate=RATE):
    """The mean over segments of each one's acceleration (m/s2, frames less two: the second differences of its place,
    frame 1 on) over `worlds` (frames x segments x 4 x 4)."""
    places = np.asarray(worlds, dtype=float)[..., :3, 3]
    return np.linalg.norm(np.diff(places, 2, axis=0) * rate ** 2, axis=2).mean(axis=1)


def steady_path(start, end, speed, frames):
    """Frames 0 to `frames` of a path at one steady acceleration (each row of `start`, `end`, `speed`: a quantity per
    frame) leaving `start` and reaching `end` at frame `frames` at `speed` (a frame)."""
    accelerating = 2.0 * (speed * frames - (end - start)) / frames ** 2
    leaving = speed - accelerating * frames
    count = np.arange(frames + 1).reshape(-1, *([1] * np.ndim(start)))
    return start + leaving * count + accelerating * count ** 2 / 2.0


def steadied(worlds, frames):
    """`worlds` with frames 0 to `frames` on a steady acceleration (`steady_path`) from its first frame to frame
    `frames`' own place and turn and their speed there (the central difference): each segment's place, and its turn
    from its first frame's as a rotation vector; the rest as it is (`frames` under 2 or past the clip: as it came)."""
    moved = np.array(worlds, dtype=float)
    if frames < 2 or frames + 1 >= len(moved):
        return moved
    places = moved[:, :, :3, 3]
    moved[:frames + 1, :, :3, 3] = steady_path(places[0], places[frames],
                                               (places[frames + 1] - places[frames - 1]) / 2.0, frames)
    first = moved[0, :, :3, :3].copy()
    turns = [Rotation.from_matrix(np.swapaxes(first, 1, 2) @ moved[frame, :, :3, :3]).as_rotvec()
             for frame in (frames - 1, frames, frames + 1)]
    path = steady_path(np.zeros_like(turns[1]), turns[1], (turns[2] - turns[0]) / 2.0, frames)
    for frame in range(1, frames + 1):
        moved[frame, :, :3, :3] = first @ Rotation.from_rotvec(path[frame]).as_matrix()
    return moved


def eased(worlds, rate=RATE):
    """(`worlds` with its start steadied, the frames steadied): `steadied` over the fewest frames, up to MOST, whose
    start (the steadied frames' accelerations, and at least its first JUDGED) keeps its mean acceleration within the
    clip's own largest after it; a clip whose start is already within it, or too short to measure one after it, as it
    came (0 frames); one no ease brings within it steadied over MOST."""
    worlds = np.asarray(worlds, dtype=float)
    own = mean_acceleration(worlds, rate)
    for frames in [0, *range(2, MOST + 1)]:
        judged = max(frames + 1, JUDGED)
        if judged >= len(own):
            break
        if mean_acceleration(steadied(worlds[:judged + 2], frames), rate)[:judged].max() <= own[judged:].max() + SLACK:
            return steadied(worlds, frames), frames
    return (worlds, 0) if len(own) <= JUDGED else (steadied(worlds, MOST), MOST)
