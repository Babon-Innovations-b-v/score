"""One paid row an uploaded video and none without one; its gates read a clip as the make writes it, refuse a short
clip or a flip, and never pass on a missing clip (video_clips/__init__.py; the retarget itself has its own test in
tools/characters/clips). Nothing paid runs.

Breaks that turn it red (each applied once and seen red, then reverted):
- `rows()` globbing `*.mov` instead of `*.mp4`  -> the rows test.
- `LEAST_FRAMES = 5`  -> the gates test (a 10-frame clip passes `clip read`).
- `MOST_TURN_DEG = 200.0`  -> the gates test (the 180-degree flip passes `steady`).
- `guarded` catching nothing (`except ()`)  -> the gates test (no clip raises instead of answering unknown).
"""
import numpy as np
from scipy.spatial.transform import Rotation

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import video_clips


def written(folder, clip):
    np.savez_compressed(folder / "clip.npz", clip=clip, names=np.array(["Root", "Hips"]), parents=np.array([-1, 0]))


def test_a_paid_row_an_uploaded_video_and_none_without(tmp_path, monkeypatch):
    monkeypatch.setattr(video_clips, "VIDEOS", tmp_path)
    assert video_clips.rows() == ()
    (tmp_path / "wave.mp4").write_bytes(b"video")
    (row,) = video_clips.rows()
    assert row.name == "video-clip-wave" and row.paid and row.params == {"clip": "wave"}
    assert row.after == {"people-clips-made": ("people-clips-made", 1)}  # retargeted onto the people's rig


def test_the_gates_read_a_clip_and_refuse_a_short_one_and_a_flip(tmp_path):
    rig = tmp_path / "rig"
    rig.mkdir()
    np.savez_compressed(rig / "rig.npz", names=np.array(["Root", "Hips"]), parents=np.array([-1, 0]),
                        bind=np.stack([np.eye(4)] * 2))
    inputs = {"people-clips-made": str(rig)}
    read, steady = (video_clips.guarded(name, judge) for name, judge in
                    (("clip read", video_clips.judge_read), ("steady", video_clips.judge_steady)))
    assert read.judge(tmp_path, inputs, None).answer == UNKNOWN
    assert steady.judge(tmp_path, inputs, None).answer == UNKNOWN
    clip = np.tile(np.eye(4), (40, 2, 1, 1))  # 40 frames, the hips turning 2 degrees a frame
    clip[:, 1, :3, :3] = Rotation.from_euler("y", np.arange(40)[:, None] * 2.0, degrees=True).as_matrix()
    written(tmp_path, clip)
    assert read.judge(tmp_path, inputs, None).answer == PASS and steady.judge(tmp_path, inputs, None).answer == PASS
    clip[20, 1, :3, :3] = Rotation.from_euler("x", 180, degrees=True).as_matrix()  # one frame flipped
    written(tmp_path, clip)
    flipped = steady.judge(tmp_path, inputs, None)
    assert flipped.answer == FAIL and flipped.findings == ("Hips",)
    written(tmp_path, clip[:10])  # a third of a second
    assert read.judge(tmp_path, inputs, None).answer == FAIL
