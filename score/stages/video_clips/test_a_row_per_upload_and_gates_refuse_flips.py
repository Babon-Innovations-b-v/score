"""One paid row an uploaded video and none without one; that row's own gates read a clip as the make writes it,
refuse a short clip or a flip, and never pass on a missing clip (video_clips/__init__.py; the retarget itself has its
own test in tools/characters/clips). Nothing paid runs.

Breaks that turn it red (each applied once and seen red, then reverted):
- `rows()` globbing `*.mov` instead of `*.mp4`  -> no row for the uploaded video.
- `LEAST_FRAMES = 5`  -> the "a third of a second" case (a 10-frame clip passes `clip read`).
- `MOST_TURN_DEG = 200.0`  -> the "one frame flipped" case (the 180-degree flip passes `steady`).
- `guarded` catching nothing (`except ()`)  -> the "no clip" case (raises instead of answering unknown).
"""
import numpy as np
from scipy.spatial.transform import Rotation

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import video_clips


def turning(frames):
    """A clip of `frames` frames on the two-joint rig, the hips turning 2 degrees a frame about y."""
    clip = np.tile(np.eye(4), (frames, 2, 1, 1))
    clip[:, 1, :3, :3] = Rotation.from_euler("y", np.arange(frames)[:, None] * 2.0, degrees=True).as_matrix()
    return clip


def flipped_at(clip, frame):
    """The clip with the hips flipped 180 degrees about x on one frame."""
    clip = clip.copy()
    clip[frame, 1, :3, :3] = Rotation.from_euler("x", 180, degrees=True).as_matrix()
    return clip


# (case, the clip the make wrote or None, clip read's answer, steady's answer, steady's findings)
CASES = (
    ("no clip", None, UNKNOWN, UNKNOWN, ()),
    ("40 steady frames", turning(40), PASS, PASS, ()),
    ("one frame flipped", flipped_at(turning(40), 20), PASS, FAIL, ("Hips",)),
    ("a third of a second", turning(10), FAIL, PASS, ()),
)


def test_a_row_per_upload_and_its_gates_refuse_a_short_clip_or_a_flip(tmp_path, monkeypatch):
    videos, rig, output = (tmp_path / name for name in ("videos", "rig", "output"))
    for folder in (videos, rig, output):
        folder.mkdir()
    monkeypatch.setattr(video_clips, "VIDEOS", videos)
    assert video_clips.rows() == (), "a row without an uploaded video"
    (videos / "wave.mp4").write_bytes(b"video")
    (row,) = video_clips.rows()
    assert row.name == "video-clip-wave" and row.paid and row.params == {"clip": "wave"}
    assert row.after == {"people-clips-made": ("people-clips-made", 1)}  # retargeted onto the people's rig
    gates = {check.name: check for check in row.checks}
    np.savez_compressed(rig / "rig.npz", names=np.array(["Root", "Hips"]), parents=np.array([-1, 0]),
                        bind=np.stack([np.eye(4)] * 2))
    inputs = {"people-clips-made": str(rig)}
    for case, clip, read, steady, findings in CASES:
        if clip is not None:
            np.savez_compressed(output / "clip.npz", clip=clip, names=np.array(["Root", "Hips"]),
                                parents=np.array([-1, 0]))
        answers = {name: gate.judge(output, inputs, None) for name, gate in gates.items()}
        assert answers["clip read"].answer == read, f"{case}: clip read {answers['clip read']}"
        assert answers["steady"].answer == steady, f"{case}: steady {answers['steady']}"
        assert answers["steady"].findings == findings, f"{case}: steady named {answers['steady'].findings}"
