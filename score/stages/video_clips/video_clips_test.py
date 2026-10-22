"""The video clip rows: one paid row an uploaded video, none without one, and the gates on a clip held as the make
writes it (the retarget itself: tools/characters/clips/retarget_test.py). Nothing paid runs."""
import numpy as np
from scipy.spatial.transform import Rotation

from score.checks import FAIL, PASS, UNKNOWN
from score.stages import video_clips


def written(folder, clip, names):
    np.savez_compressed(folder / "clip.npz", clip=clip, names=np.array(names), parents=np.array([-1, 0]))


def test_a_row_an_uploaded_video_and_none_without(tmp_path, monkeypatch):
    monkeypatch.setattr(video_clips, "VIDEOS", tmp_path)
    assert video_clips.rows() == ()
    (tmp_path / "wave.mp4").write_bytes(b"video")
    (row,) = video_clips.rows()
    assert row.name == "video-clip-wave" and row.paid and row.euros and row.grain == "world"
    assert row.after == {"people-clips-made": ("people-clips-made", 1)} and row.params == {"clip": "wave"}


def test_the_gates_read_a_clip_and_refuse_a_flip(tmp_path):
    rig = tmp_path / "rig"
    rig.mkdir()
    np.savez_compressed(rig / "rig.npz", names=np.array(["Root", "Hips"]), parents=np.array([-1, 0]),
                        bind=np.stack([np.eye(4)] * 2))
    inputs = {"people-clips-made": str(rig)}
    read, steady = (video_clips.guarded(name, judge) for name, judge in
                    (("clip read", video_clips.judge_read), ("steady", video_clips.judge_steady)))
    assert read.judge(tmp_path, inputs, None).answer == UNKNOWN
    clip = np.tile(np.eye(4), (40, 2, 1, 1))
    clip[:, 1, :3, :3] = Rotation.from_euler("y", np.arange(40)[:, None] * 2.0, degrees=True).as_matrix()
    written(tmp_path, clip, ["Root", "Hips"])
    assert read.judge(tmp_path, inputs, None).answer == PASS and steady.judge(tmp_path, inputs, None).answer == PASS
    clip[20, 1, :3, :3] = Rotation.from_euler("x", 180, degrees=True).as_matrix()
    written(tmp_path, clip, ["Root", "Hips"])
    flipped = steady.judge(tmp_path, inputs, None)
    assert flipped.answer == FAIL and flipped.findings == ("Hips",)
    written(tmp_path, clip[:10], ["Root", "Hips"])
    assert read.judge(tmp_path, inputs, None).answer == FAIL
