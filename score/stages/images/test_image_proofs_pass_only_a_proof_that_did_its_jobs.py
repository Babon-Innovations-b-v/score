"""The images environment proves each job image on its own table and its gates pass only a proof that did its jobs
(images/__init__.py): each kind with a plan has its free pins row and its paid proof row on an environment with no
places and none on environment 1's table; loose pins fail `pins hashed` (a repository wheel pinned by its hash is not
loose); the runner's pins pass only as uv.lock's fresh export, a hand-edited line failing; the runner's proof passes
only when every row's code version in the image is the conductor's; the moss takes pass only at their length,
heard, and scoring no more than CLAP_SLACK under the build before; the walking clip fails standing still; `jobs ran`
fails a planned job that never reached its first result; `publish` refuses a proof that does not stand accepted, and
writes an accepted one with the parent image it built and ran on.
Synthetic takes and clips in a temp folder; no cloud.

Breaks that turn it red (each applied once and seen red, then reverted):
- `judge_hashed`: `not version or not hashes` read as `not version`  -> test_loose_pins_fail.
- `lock_faults`: the requirements' comparison left out (only lock.sha256 compared)  -> test_loose_pins_fail.
- `version_faults`: the per-row comparison left out (only the Python compared)  -> the walking clip test.
- `take_faults`: the `dbfs < SILENT_DBFS` fault, the length fault, or the CLAP fault left out  -> the moss test.
- `clip_faults`: the travel range left out of the checked pair  -> the walking clip test.
- `smoke_faults`: the pins' comparison or the fall's range left out  -> the walking clip test (its newton smoke part).
- `judge_jobs_ran`: `"first_result" not in ...marks` read as `False`  -> the jobs test.
- `publish`: `runner.usable(...)` read as `runner.store.records(...)`, any record  -> the publish test.
- `publish`: the `built[PARENT] = parent` write left out  -> the publish test.
"""
import json
import pathlib
import tempfile
import wave

import numpy as np
import pytest

from score import checks, graph, stages
from score.stages import images
from score.store import Store

RATE = 48000


def write_wav(path, seconds, amplitude):
    """A 24-bit mono WAV of a 440 Hz tone at `amplitude` (0 to 1)."""
    times = np.arange(int(seconds * RATE)) / RATE
    samples = (np.sin(2 * np.pi * 440 * times) * amplitude * (2 ** 23 - 1)).astype("<i4")
    raw = samples.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(str(path), "wb") as sound:
        sound.setnchannels(1)
        sound.setsampwidth(3)
        sound.setframerate(RATE)
        sound.writeframes(raw)


def moss_output(root, amplitude=0.3, short=False, clap=0.45):
    """A moss proof output and its inputs, with the plan's two takes made as asked (or not)."""
    output, folder = root / "out", images.IMAGES / "moss"
    takes = output / images.PROOF / "takes"
    takes.mkdir(parents=True)
    (output / images.PLAN).write_text((folder / images.PLAN).read_text())
    jobs = json.loads((folder / "prove-jobs.json").read_text())
    for job in jobs:
        write_wav(takes / job["file"], job["seconds"] * (0.5 if short else 1), amplitude)
    (takes / "scores-0.json").write_text(json.dumps({job["file"]: clap for job in jobs}))
    return output, {"folder": folder}


def test_the_images_world_has_its_own_table_and_no_places():
    runner = stages.runner(world=images.image_world())
    assert stages.places(runner.world) == []
    assert {"image-pins-moss", "image-proof-moss", "image-pins-characters-motion",
            "image-proof-characters-motion", "image-pins-newton", "image-proof-newton", "image-pins-runner",
            "image-proof-runner"} <= set(runner.stages)
    assert runner.stages["image-pins-runner"].files["lock"] == "{repo}/uv.lock"  # its pins move with the lock
    assert "code tools" not in runner.stages["image-proof-runner"].files  # the tree it carries proves nothing again
    assert runner.stages["image-proof-moss"].paid and runner.stages["image-proof-moss"].euros > 0
    assert not runner.stages["image-pins-moss"].paid
    assert "image-pins-moss" not in stages.runner().stages  # environment 1's table has none of them


def test_loose_pins_fail():
    with tempfile.TemporaryDirectory() as temp:
        output = pathlib.Path(temp)
        (output / "requirements.txt").write_text("numpy==1.26.4 \\\n    --hash=sha256:00\nscipy>=1.0\npillow==10.0.0\n")
        verdict = images.judge_hashed(output, {}, None)
        assert verdict.answer == checks.FAIL and verdict.findings == ("pillow", "scipy")
        (output / "requirements.txt").write_text("numpy==1.26.4 \\\n    --hash=sha256:00\n"
                                                 "./vendor/w-1.0-py3-none-any.whl ; python_version >= '3.12' \\\n"
                                                 "    --hash=sha256:01\n")
        assert images.judge_hashed(output, {}, None).answer == checks.PASS
        build, _ = images.image_tools()
        lock = {"lock": images.REPO / "uv.lock"}
        (output / "requirements.txt").write_text(build.lock_export(images.REPO))
        (output / images.LOCK_SHA).write_text(build.lock_sha256(images.REPO))
        assert images.judge_lock_export(output, lock, None).answer == checks.PASS
        edited = (output / "requirements.txt").read_text().replace("numpy==", "numpy==0", 1)
        (output / "requirements.txt").write_text(edited)
        assert images.judge_lock_export(output, lock, None).answer == checks.FAIL


def test_moss_takes_pass_heard_at_length_and_fail_otherwise():
    for changes, wanted in (({}, checks.PASS), ({"amplitude": 0.0}, checks.FAIL), ({"short": True}, checks.FAIL),
                            ({"clap": 0.2}, checks.FAIL)):
        with tempfile.TemporaryDirectory() as temp:
            output, inputs = moss_output(pathlib.Path(temp), **changes)
            verdict = images.judge_moss_takes(output, inputs, None)
            assert verdict.answer == wanted, (changes, verdict)


def test_the_walking_clip_passes_and_one_standing_still_fails():
    for travel, wanted in ((6.0, checks.PASS), (0.0, checks.FAIL)):
        with tempfile.TemporaryDirectory() as temp:
            output = pathlib.Path(temp)
            clip = output / images.PROOF / "clip"
            clip.mkdir(parents=True)
            (output / images.PLAN).write_text((images.IMAGES / "characters-motion" / images.PLAN).read_text())
            joints = np.zeros((150, 77, 3), dtype=np.float32)
            joints[:, :, 1] = 0.98
            joints[:, :, 2] = np.linspace(0, travel, 150)[:, None]
            np.savez(clip / "walking.npz", posed_joints=joints)
            assert images.judge_motion_clip(output, {}, None).answer == wanted
    pins = {"newton": "1.7.0", "mujoco": "3.15.0", "mujoco-warp": "3.15.0", "warp-lang": "1.18.0", "usd-core": "26.8",
            "newton-usd-schemas": "0.5.0", "numpy": "2.5.3", "scipy": "1.18.1", "python-fcl": "0.7.0.11",
            "mink": "1.3.0", "qpsolvers": "4.13.0", "daqp": "0.10.3", "typing-extensions": "4.16.0"}
    smoke = {"versions": pins, "cuda_devices": 1, "kernel_sum": 500500, "fall_metres": 4.91}  # the newton image's
    for broken, wanted in (({}, checks.PASS), ({"versions": {**pins, "mink": "1.2.0"}}, checks.FAIL),
                           ({"fall_metres": 0.0}, checks.FAIL)):
        with tempfile.TemporaryDirectory() as temp:
            output = pathlib.Path(temp)
            (output / images.PROOF / "smoke").mkdir(parents=True)
            (output / images.PLAN).write_text((images.IMAGES / "newton" / images.PLAN).read_text())
            (output / images.PROOF / "smoke" / "smoke.json").write_text(json.dumps({**smoke, **broken}))
            assert images.judge_newton_smoke(output, {}, None).answer == wanted
    conductor = {"python": "python 3.12", "versions": {"terrain": "a1", "assembly": "b2"}}
    assert images.version_faults(conductor, conductor) == []
    assert images.version_faults({**conductor, "versions": {"terrain": "a1", "assembly": "c3"}}, conductor) == [
        "assembly: c3 in the image, b2 here"]


def test_a_job_that_did_not_finish_fails_jobs_ran():
    with tempfile.TemporaryDirectory() as temp:
        output = pathlib.Path(temp)
        (output / images.PLAN).write_text((images.IMAGES / "moss" / images.PLAN).read_text())
        image = "registry/score-moss:1-x@sha256:y"
        record = {"image": image, "digest": "sha256:y",
                  "proof": {"L4": {"image": image, "type": "L4-1-24G", "jobs": {"takes": {"marks": {}}}}}}
        (output / images.RECORD).write_text(json.dumps(record))
        assert images.judge_jobs_ran(output, {}, None).answer == checks.FAIL
        record["proof"]["L4"]["jobs"]["takes"]["marks"]["first_result"] = 30.0
        (output / images.RECORD).write_text(json.dumps(record))
        assert images.judge_jobs_ran(output, {}, None).answer == checks.PASS


def test_publish_refuses_a_proof_not_accepted(tmp_path):
    runner = stages.runner(store=Store.in_folder(tmp_path / "store"), world=images.image_world())
    (tmp_path / "images.json").write_text("{}")
    with pytest.raises(graph.Blocked):
        images.publish(runner, "moss", tmp_path / "images.json")
    assert json.loads((tmp_path / "images.json").read_text()) == {}  # nothing written
    records = {images.RECORD: {"tag": "1-kid"}, images.PARENT_RECORD: {"tag": "1-new-base"}}
    runner.usable = lambda *_: "accepted"
    runner.store.read_file = lambda output, name: records.get(name) if output == "accepted" else None
    images.publish(runner, "moss", tmp_path / "images.json")
    assert json.loads((tmp_path / "images.json").read_text()) == {"base": {"tag": "1-new-base"},
                                                                  "moss": {"tag": "1-kid"}}

