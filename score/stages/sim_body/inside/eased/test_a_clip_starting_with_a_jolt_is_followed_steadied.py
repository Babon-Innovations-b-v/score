"""eased: a clip of two segments starting with a jolt (the upper one's place 0.03 (1 - exp(-t / 1.5)) + 0.01 sin(2 pi
t / 30) along x a frame t, its turn about up 0.2 such: its first three accelerations over twice its largest after, as
Kimodo's standing clip's 0.5 to 0.7 m/s2 against at most 0.4) is followed steadied: its first frame its own, steadied
over two to MOST frames, its accelerations over them one steady value (its place's second differences equal), as it
came from there on, and no acceleration of it over the clip's own largest after the steadied frames; a clip moving at
a steady speed from its first frame (no acceleration at its start) is followed as it came, steadied over 0 frames.
Pure: the score venv runs it.

Breaks (each applied once, seen red, reverted), 2026-11-13:
- eased's `own[judged:]` made `own` (its start judged against its own jolt: as it came, 0 frames).
- steady_path's `accelerating * count ** 2 / 2.0` made `accelerating * count ** 2` (the path overshoots its end:
  frame `frames` not the clip's own, its acceleration past the clip's range).
- run_person's `eased.eased(targets["world"], job["rate"])` is not seen here (Newton's Python): the base, greenhouse
  and hangar probes on this PC's card are its measure.

Run: .venv/bin/python -m pytest score/stages/sim_body/inside/eased/test_a_clip_starting_with_a_jolt_is_followed_steadied.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import eased  # noqa: E402


def clip(along, turn):
    """Two segments a frame: a still one at the origin and one 1 m over it at `along` on x, turned `turn` about up."""
    worlds = np.tile(np.eye(4), (len(along), 2, 1, 1))
    worlds[:, 1, 0, 3], worlds[:, 1, 1, 3] = along, 1.0
    worlds[:, 1, 0, 0], worlds[:, 1, 0, 2] = np.cos(turn), np.sin(turn)
    worlds[:, 1, 2, 0], worlds[:, 1, 2, 2] = -np.sin(turn), np.cos(turn)
    return worlds


def test_a_clip_starting_with_a_jolt_is_followed_steadied():
    count = np.arange(40)
    start = 0.03 * (1.0 - np.exp(-count / 1.5)) + 0.01 * np.sin(2.0 * np.pi * count / 30.0)
    jolting = clip(start, start / 0.03 * 0.2)
    own = eased.mean_acceleration(jolting)
    assert own[:3].max() > 2.0 * own[3:].max()  # it jolts
    worlds, frames = eased.eased(jolting)
    assert 2 <= frames <= eased.MOST
    np.testing.assert_allclose(worlds[0], jolting[0])
    np.testing.assert_allclose(worlds[frames:], jolting[frames:])
    np.testing.assert_allclose(np.diff(worlds[:frames + 1, 1, 0, 3], 2), np.diff(worlds[:3, 1, 0, 3], 2)[0], atol=1e-12)
    assert eased.mean_acceleration(worlds).max() <= own[frames + 1:].max() + 1e-9
    steady = clip(0.01 * count, 0.0 * count)
    worlds, frames = eased.eased(steady)
    assert frames == 0 and np.array_equal(worlds, steady)
