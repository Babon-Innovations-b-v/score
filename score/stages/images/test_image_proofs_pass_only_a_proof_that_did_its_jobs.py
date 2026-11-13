"""The images environment proves each job image on its own table and its gates pass only a proof that did its jobs
(images/__init__.py): each kind with a plan has its free pins row and its paid proof row on an environment with no
places and none on environment 1's table; loose pins fail `pins hashed` (a repository wheel pinned by its hash is not
loose); the runner's pins pass only as uv.lock's fresh export, a hand-edited line failing; the runner's proof passes
only when every row's code version in the image is the conductor's; the moss takes pass only at their length,
heard, and scoring no more than CLAP_SLACK under the build before; the walking clip fails standing still; `jobs ran`
fails a planned job that never reached its first result; `publish` refuses a proof that does not stand accepted, and
writes an accepted one with the parent image it built and ran on.
Synthetic takes and clips in a temp folder; no cloud. One test: the images world is built once and published from,
and every gate's verdict is a row of one table (the output it reads, the answer it must give).

Breaks that turn it red (each applied once and seen red, then reverted):
- `judge_hashed`: the `or not hashes` fault left out (a pin without a hash passed)  -> row `pins loose`.
- `lock_faults`: the requirements' comparison left out (only lock.sha256 compared)  -> row `lock export hand-edited`.
- `version_faults`: the per-row comparison left out (only the Python compared)  -> the version row `a row moved`.
- `take_faults`: the `dbfs < SILENT_DBFS` fault, the length fault, or the CLAP fault left out  -> rows `moss silent`,
  `moss short`, `moss clap dropped`.
- `clip_faults`: the travel range left out of the checked pair  -> row `clip standing still`.
- `smoke_faults`: the pins' comparison or the fall's range left out  -> rows `newton pin moved`, `newton no fall`.
- `judge_jobs_ran`: `"first_result" not in ...marks` read as `False`  -> row `jobs never reached a result`.
- `publish`: `runner.usable(...)` read as `runner.store.records(...)`, any record  -> the publish refusal.
- `publish`: the `built[PARENT] = parent` write left out  -> the accepted publish's images.json.
- `judge_only_packages`: the first-build pass without `== []` (a first image's models passed unread)  -> row
  `first build with a model`.
"""
import json
import pathlib
import wave

import numpy as np
import pytest

from score import checks, graph, stages
from score.stages import images
from score.store import Store

RATE = 48000
NEWTON_PINS = {"newton": "1.7.0", "mujoco": "3.15.0", "mujoco-warp": "3.15.0", "warp-lang": "1.18.0",
               "usd-core": "26.8", "newton-usd-schemas": "0.5.0", "numpy": "2.5.3", "scipy": "1.18.1",
               "python-fcl": "0.7.0.11", "mink": "1.3.0", "qpsolvers": "4.13.0", "daqp": "0.10.3",
               "typing-extensions": "4.16.0"}
CONDUCTOR = {"python": "python 3.12", "versions": {"terrain": "a1", "assembly": "b2"}}
IMAGE = "registry/score-moss:1-x@sha256:y"


class Tone(tuple):
    """A 440 Hz tone file to write: (seconds, amplitude 0 to 1)."""


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


def lay(output, files):
    """Write each file of a row into `output`: text, a joints array as an npz clip, or a Tone as a WAV."""
    for name, content in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, Tone):
            write_wav(path, *content)
        elif isinstance(content, np.ndarray):
            np.savez(path, posed_joints=content)
        else:
            path.write_text(content)


def plan(kind):
    """A kind's proof plan, as its output carries it."""
    return {images.PLAN: (images.IMAGES / kind / images.PLAN).read_text()}


def moss(amplitude=0.3, short=False, clap=0.45):
    """A moss proof output with the plan's takes made as asked (or not)."""
    jobs = json.loads((images.IMAGES / "moss" / "prove-jobs.json").read_text())
    takes = f"{images.PROOF}/takes"
    files = {f"{takes}/{job['file']}": Tone((job["seconds"] * (0.5 if short else 1), amplitude)) for job in jobs}
    return {**plan("moss"), **files, f"{takes}/scores-0.json": json.dumps({job["file"]: clap for job in jobs})}


def walking(travel):
    """A characters-motion proof output whose clip's root travels `travel` metres at standing height."""
    joints = np.zeros((150, 77, 3), dtype=np.float32)
    joints[:, :, 1] = 0.98
    joints[:, :, 2] = np.linspace(0, travel, 150)[:, None]
    return {**plan("characters-motion"), f"{images.PROOF}/clip/walking.npz": joints}


def newton(**broken):
    """A newton proof output whose smoke job reported the env script's pins, a kernel sum and a fall."""
    smoke = {"versions": NEWTON_PINS, "cuda_devices": 1, "kernel_sum": 500500, "fall_metres": 4.91, **broken}
    return {**plan("newton"), f"{images.PROOF}/smoke/smoke.json": json.dumps(smoke)}


def jobs_record(marks):
    """A moss proof output whose record's one planned job reached `marks`."""
    record = {"image": IMAGE, "digest": "sha256:y",
              "proof": {"L4": {"image": IMAGE, "type": "L4-1-24G", "jobs": {"takes": {"marks": marks}}}}}
    return {**plan("moss"), images.RECORD: json.dumps(record)}


def test_image_proofs_pass_only_a_proof_that_did_its_jobs(tmp_path):
    runner = stages.runner(store=Store.in_folder(tmp_path / "store"), world=images.image_world())
    assert stages.places(runner.world) == []
    assert {"image-pins-moss", "image-proof-moss", "image-pins-characters-motion",
            "image-proof-characters-motion", "image-pins-newton", "image-proof-newton", "image-pins-runner",
            "image-proof-runner"} <= set(runner.stages)
    assert runner.stages["image-pins-runner"].files["lock"] == "{repo}/uv.lock"  # its pins move with the lock
    assert "code tools" not in runner.stages["image-proof-runner"].files  # the tree it carries proves nothing again
    assert runner.stages["image-proof-moss"].paid and runner.stages["image-proof-moss"].euros > 0
    assert not runner.stages["image-pins-moss"].paid
    assert "image-pins-moss" not in stages.runner().stages  # environment 1's table has none of them

    build, _ = images.image_tools()
    lock = {"lock": images.REPO / "uv.lock"}
    export = {"requirements.txt": build.lock_export(images.REPO), images.LOCK_SHA: build.lock_sha256(images.REPO)}
    edited = {**export, "requirements.txt": export["requirements.txt"].replace("numpy==", "numpy==0", 1)}
    first = {"images.json": "{}"}
    # (row, gate, the output's files, its inputs (a str is a file in the output), answer, findings or None)
    rows = (
        ("pins loose", images.judge_hashed,
         {"requirements.txt": "numpy==1.26.4 \\\n    --hash=sha256:00\nscipy>=1.0\npillow==10.0.0\n"}, {},
         checks.FAIL, ("pillow", "scipy")),
        ("pins hashed with a repository wheel", images.judge_hashed,
         {"requirements.txt": "numpy==1.26.4 \\\n    --hash=sha256:00\n"
                              "./vendor/w-1.0-py3-none-any.whl ; python_version >= '3.12' \\\n"
                              "    --hash=sha256:01\n"}, {}, checks.PASS, None),
        ("lock export fresh", images.judge_lock_export, export, lock, checks.PASS, None),
        ("lock export hand-edited", images.judge_lock_export, edited, lock, checks.FAIL, None),
        ("first build with no models", images.judge_only_packages("first"), {**first, "models.json": "[]"},
         {"published": "images.json"}, checks.PASS, None),
        ("first build with a model", images.judge_only_packages("first"),
         {**first, "models.json": '[{"name": "a model", "licence": "unread"}]'}, {"published": "images.json"},
         checks.UNKNOWN, None),
        ("moss heard at length", images.judge_moss_takes, moss(), {"folder": images.IMAGES / "moss"},
         checks.PASS, None),
        ("moss silent", images.judge_moss_takes, moss(amplitude=0.0), {"folder": images.IMAGES / "moss"},
         checks.FAIL, None),
        ("moss short", images.judge_moss_takes, moss(short=True), {"folder": images.IMAGES / "moss"},
         checks.FAIL, None),
        ("moss clap dropped", images.judge_moss_takes, moss(clap=0.2), {"folder": images.IMAGES / "moss"},
         checks.FAIL, None),
        ("clip walking", images.judge_motion_clip, walking(6.0), {}, checks.PASS, None),
        ("clip standing still", images.judge_motion_clip, walking(0.0), {}, checks.FAIL, None),
        ("newton smoke right", images.judge_newton_smoke, newton(), {}, checks.PASS, None),
        ("newton pin moved", images.judge_newton_smoke, newton(versions={**NEWTON_PINS, "mink": "1.2.0"}), {},
         checks.FAIL, None),
        ("newton no fall", images.judge_newton_smoke, newton(fall_metres=0.0), {}, checks.FAIL, None),
        ("jobs never reached a result", images.judge_jobs_ran, jobs_record({}), {}, checks.FAIL, None),
        ("jobs reached a result", images.judge_jobs_ran, jobs_record({"first_result": 30.0}), {}, checks.PASS,
         None),
    )
    for name, gate, files, inputs, answer, findings in rows:
        output = tmp_path / name.replace(" ", "-")
        output.mkdir()
        lay(output, files)
        verdict = gate(output, {key: output / value if isinstance(value, str) else value
                                for key, value in inputs.items()}, None)
        assert verdict.answer == answer, (name, verdict)
        assert findings is None or verdict.findings == findings, (name, verdict)
    # (row, the image's versions, the faults against the conductor's)
    for name, image, faults in (("versions the conductor's", CONDUCTOR, []),
                                ("a row moved", {**CONDUCTOR, "versions": {"terrain": "a1", "assembly": "c3"}},
                                 ["assembly: c3 in the image, b2 here"])):
        assert images.version_faults(image, CONDUCTOR) == faults, name

    published = tmp_path / "images.json"
    published.write_text("{}")
    with pytest.raises(graph.Blocked):
        images.publish(runner, "moss", published)
    assert json.loads(published.read_text()) == {}  # nothing written
    records = {images.RECORD: {"tag": "1-kid"}, images.PARENT_RECORD: {"tag": "1-new-base"}}
    runner.usable = lambda *_: "accepted"
    runner.store.read_file = lambda output, name: records.get(name) if output == "accepted" else None
    images.publish(runner, "moss", published)
    assert json.loads(published.read_text()) == {"base": {"tag": "1-new-base"}, "moss": {"tag": "1-kid"}}
