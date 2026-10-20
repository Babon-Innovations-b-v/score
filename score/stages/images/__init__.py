"""The images world: each job image of tools/cloud/images rebuilt and proved by the runner, as a world of its own
(world-independent: no world 1 node reads it, and nothing here is in any world 1 node's code version).

    .venv/bin/python -m score run images [--stage image-proof-moss]   # pins checked, then built and proved (paid)
    .venv/bin/python -m score images publish <kind>                    # the accepted record into images.json

A kind with a proof plan in its folder (`<kind>/prove.json`, images/prove.py's plan, its inputs' `from` relative to
the folder and its outputs' `to` relative to the proof) has two world nodes:

    image-pins-<kind>    (free)  the folder's requirements.txt, Dockerfile and models.json. Gates: every pin exact
                         and hashed; the pins resolve (uv, for the Dockerfile's Python and package indexes);
                         images/build_test.py passes; models.json (the models and their licences) and the
                         Dockerfile's instructions are those of the build images.json holds (the folder at the commit
                         that first named its tag), so only the packages moved.
    image-proof-<kind>   (PAID, the plan's `euros`, cleared against the stop) reads the accepted pins:
                         images/build.py builds and pushes the image, images/prove.py runs the plan's jobs in it on
                         a rented card, both writing into a copy of images.json inside the output, never the
                         repository's. Gates: every planned job ran, and the kind's own check of what they made
                         (PROOF_CHECKS). Its output's record.json is the kind's new images.json entry.

`publish` writes an accepted proof's record into images.json; until then every reader of images.json (the runners,
score.adapters.models and the keys of the nodes that pin a kind) sees the build before.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave

import numpy as np

from score import checks, contracts, graph

REPO = pathlib.Path(__file__).resolve().parents[3]
IMAGES = REPO / "tools/cloud/images"
IMAGES_JSON = IMAGES / "images.json"
PLAN = "prove.json"
PINNED_FILES = ("requirements.txt", "Dockerfile", "models.json")
# A pin a kind holds over a dependency's own cap (moss: protobuf over descript-audiotools' <3.20), declared in its
# folder so the resolve check sees it as chosen; the image installs its pins without resolving (uv pip sync).
OVERRIDES = "overrides.txt"
RECORD = "record.json"
PROOF = "proof"
WHO = "score runner, images world"
WAIT_MINUTES = 90
RETRY_SECONDS = 180
PLATFORM = "x86_64-unknown-linux-gnu"
PINS = contracts.Contract("image-pins", 1, lambda folder: [f"{name} is missing" for name in PINNED_FILES
                                                            if not (folder / name).is_file()])
# A take may score this much under the same prompt, seed and weights on the build before (CLAP's cosine).
CLAP_SLACK = 0.1
# A take whose RMS is under this (dBFS) is silent.
SILENT_DBFS = -60.0
LENGTH_SLACK = 0.02


def image_world():
    """The images world: the image folders, keyed on their own content; no world data, no places."""
    return graph.World("images", 0, {"images": str(IMAGES), "repo": str(REPO)})


def proved_kinds():
    """The image kinds with a proof plan in their folder."""
    return sorted(path.parent.name for path in IMAGES.glob(f"*/{PLAN}"))


# --- image-pins ----------------------------------------------------------------------------------------------

def make_pins(inputs, out, seed, params):
    """Copy the folder's pinned files into the output."""
    for name in (*PINNED_FILES, OVERRIDES):
        if name in PINNED_FILES or (inputs["folder"] / name).is_file():
            shutil.copy2(inputs["folder"] / name, out / name)


def pinned_lines(requirements):
    """{package: (version, hashes)} of a hashed requirements file; a package without `==` has version None."""
    found, current = {}, None
    for line in requirements.read_text().splitlines():
        text = line.strip().rstrip("\\").strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("--hash="):
            if current:
                found[current][1].append(text)
            continue
        _, _, version = text.partition("==")
        current = re.split(r"[<>=!~;\s\[]", text)[0].lower()
        found[current] = (version.split()[0] if version else None, [])
    return found


def judge_hashed(output, inputs, evidence):
    """Pass when every package is pinned to one version with at least one hash."""
    pins = pinned_lines(output / "requirements.txt")
    loose = sorted(name for name, (version, hashes) in pins.items() if not version or not hashes)
    if not pins:
        return checks.Verdict("pins hashed", checks.FAIL, "requirements.txt pins nothing")
    if loose:
        return checks.Verdict("pins hashed", checks.FAIL, f"{len(loose)} packages lack an exact pin or a hash",
                              {"loose": len(loose)}, {"loose": "lower"}, tuple(loose))
    return checks.Verdict("pins hashed", checks.PASS, f"all {len(pins)} packages pinned with hashes",
                          {"packages": len(pins)})


def dockerfile_python(dockerfile):
    """The Python minor version the Dockerfile builds its environment with (`ARG PYTHON=3.12.13` gives 3.12); None
    when it names none."""
    found = re.search(r"^ARG PYTHON=(\d+\.\d+)", dockerfile.read_text(), re.MULTILINE)
    return found.group(1) if found else None


def dockerfile_indexes(dockerfile):
    """The uv flags of the package indexes the Dockerfile installs from."""
    text = dockerfile.read_text()
    flags = [f"--extra-index-url={url}" for url in re.findall(r"--extra-index-url\s+(\S+)", text)]
    return flags + (["--index-strategy=unsafe-best-match"] if "unsafe-best-match" in text else [])


def judge_resolves(output, inputs, evidence):
    """Pass when uv resolves the pins together for the Dockerfile's Python and indexes, with the kind's declared
    overrides."""
    python = dockerfile_python(output / "Dockerfile")
    if python is None:
        return checks.Verdict("pins resolve", checks.UNKNOWN, "the Dockerfile names no ARG PYTHON to resolve for")
    overrides = output / OVERRIDES
    with tempfile.TemporaryDirectory() as resolved:
        command = ["uv", "pip", "compile", str(output / "requirements.txt"), "--python-version", python,
                   "--python-platform", PLATFORM, "--quiet", "--no-header", "-o", f"{resolved}/resolved.txt",
                   *dockerfile_indexes(output / "Dockerfile"),
                   *(["--override", str(overrides)] if overrides.is_file() else [])]
        done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode:
        return checks.Verdict("pins resolve", checks.FAIL, "uv cannot resolve the pins together",
                              findings=tuple(done.stderr.strip().splitlines()[-8:]))
    return checks.Verdict("pins resolve", checks.PASS, f"the pins resolve together for Python {python}")


def judge_build_test(output, inputs, evidence):
    """Pass when images/build_test.py passes."""
    done = subprocess.run([sys.executable, str(IMAGES / "build_test.py")], capture_output=True, text=True, cwd=REPO)
    if done.returncode:
        return checks.Verdict("build test", checks.FAIL, "images/build_test.py failed",
                              findings=tuple((done.stdout + done.stderr).strip().splitlines()[-8:]))
    return checks.Verdict("build test", checks.PASS, "images/build_test.py passes")


def published_tag(kind, images_json):
    """The tag images.json holds for the kind ('' when none)."""
    return json.loads(pathlib.Path(images_json).read_text()).get(kind, {}).get("tag", "")


def tag_commit(tag):
    """The commit that first named the tag in images.json; None when no commit did."""
    done = subprocess.run(["git", "log", "--format=%H", f"-S\"tag\": \"{tag}\"", "--",
                           str(IMAGES_JSON.relative_to(REPO))], capture_output=True, text=True, cwd=REPO, check=True)
    commits = done.stdout.split()
    return commits[-1] if commits else None


def file_at(commit, path):
    """A repository file's text at a commit."""
    return subprocess.run(["git", "show", f"{commit}:{path.relative_to(REPO)}"], capture_output=True, text=True,
                          cwd=REPO, check=True).stdout


def instructions(dockerfile_text):
    """A Dockerfile's lines less its comments and blank lines."""
    return [line for line in dockerfile_text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def moved_packages(before_text, after):
    """'name old -> new' for each package whose pin moved, came or went."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as before:
        before.write(before_text)
        before.flush()
        old = {name: version for name, (version, _) in pinned_lines(pathlib.Path(before.name)).items()}
    new = {name: version for name, (version, _) in pinned_lines(after).items()}
    return tuple(f"{name} {old.get(name, '-')} -> {new.get(name, '-')}" for name in sorted({*old, *new})
                 if old.get(name) != new.get(name))


def judge_only_packages(kind):
    """The check that the kind's models, licences and Dockerfile instructions are the published build's."""
    def judge(output, inputs, evidence):
        tag = published_tag(kind, inputs["published"])
        commit = tag_commit(tag) if tag else None
        if commit is None:
            return checks.Verdict("only packages moved", checks.UNKNOWN,
                                  f"no commit names the published tag {tag!r}: nothing to compare with")
        folder = IMAGES / kind
        changed = [name for name, same in (
            ("models.json", file_at(commit, folder / "models.json") == (output / "models.json").read_text()),
            ("Dockerfile", instructions(file_at(commit, folder / "Dockerfile"))
             == instructions((output / "Dockerfile").read_text()))) if not same]
        moved = moved_packages(file_at(commit, folder / "requirements.txt"), output / "requirements.txt")
        if changed:
            return checks.Verdict("only packages moved", checks.FAIL,
                                  f"{' and '.join(changed)} differ from the published build's ({commit[:10]})",
                                  {"moved": len(moved)}, findings=moved)
        return checks.Verdict("only packages moved", checks.PASS,
                              f"models, licences and Dockerfile as built at {commit[:10]}; {len(moved)} packages moved",
                              {"moved": len(moved)}, findings=moved)
    return judge


def pins_checks(kind):
    return (checks.Check("pins hashed", judge_hashed), checks.Check("pins resolve", judge_resolves),
            checks.Check("build test", judge_build_test),
            checks.Check("only packages moved", judge_only_packages(kind)))


# --- image-proof ---------------------------------------------------------------------------------------------

def image_tools():
    """images/build.py and images/prove.py, loaded only when a proof makes."""
    if str(IMAGES) not in sys.path:
        sys.path.insert(0, str(IMAGES))
    import build
    import prove
    return build, prove


def local_plan(folder, out):
    """The kind's plan with its inputs' `from` in the folder and its outputs' `to` in the output's proof folder."""
    plan = json.loads((folder / PLAN).read_text())
    for kind_run in plan["runs"]:
        for item in kind_run.get("inputs", []):
            item["from"] = str(folder / item["from"])
        for job in kind_run["jobs"]:
            for item in job.get("outputs", []):
                item["to"] = str(out / PROOF / item["to"])
                pathlib.Path(item["to"]).mkdir(parents=True, exist_ok=True)
    return plan


def proved(plan, prove):
    """Prove the plan on a rented card, asking again while none is in stock; the results by kind."""
    from provider import cloud  # prove.py put it on the path
    batch = prove.batch
    account = cloud.account()
    batch.sweep(account)
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    registry, store_spec = cloud.registry(), cloud.object_store()
    results, give_up = {}, time.time() + WAIT_MINUTES * 60
    while not prove.one_attempt(plan, account, registry, store_spec, WHO, results):
        if time.time() > give_up:
            raise graph.Blocked(f"no machine of {', '.join(plan['classes'])} in {WAIT_MINUTES} min")
        time.sleep(RETRY_SECONDS)
    return results


def pointed_at(build, prove, working):
    """Point build.py, prove.py and submit.py at the output's copy of images.json (this forked node's own modules)."""
    build.IMAGES_JSON = working
    prove.submit.IMAGES = working


def make_proof(kind):
    """The make of a kind's proof: build and push the image, prove it, its images.json entry as record.json."""
    def make(inputs, out, seed, params):
        build, prove = image_tools()
        working = out / "images.json"
        shutil.copy2(IMAGES_JSON, working)
        pointed_at(build, prove, working)
        build.build([kind], WHO, False)
        plan = local_plan(inputs["folder"], out)
        (out / PLAN).write_text(json.dumps(plan, indent=1))
        prove.save_results(proved(plan, prove))
        (out / RECORD).write_text(json.dumps(json.loads(working.read_text())[kind], indent=1))
        working.unlink()
    return make


def proof_faults(folder):
    """What a proof output lacks: its record with a digest and a proof, and its plan."""
    record = folder / RECORD
    if not record.is_file() or not (folder / PLAN).is_file():
        return [f"{RECORD} or {PLAN} is missing"]
    entry = json.loads(record.read_text())
    return [f"{RECORD} lacks {name}" for name in ("image", "digest", "proof") if not entry.get(name)]


PROVED = contracts.Contract("image-proof", 1, proof_faults)


def this_build_proofs(entry):
    """The proofs of the record's own image (a record keeps the proofs of the builds before it)."""
    return [proof for proof in entry.get("proof", {}).values() if proof.get("image") == entry["image"]]


def judge_jobs_ran(output, inputs, evidence):
    """Pass when every job the plan names ran in this build's image and reached its first result."""
    entry = json.loads((output / RECORD).read_text())
    planned = [job["name"] for kind_run in json.loads((output / PLAN).read_text())["runs"] for job in kind_run["jobs"]]
    proofs = this_build_proofs(entry)
    if not proofs:
        return checks.Verdict("jobs ran", checks.FAIL, f"no proof of {entry['image']}")
    jobs = proofs[-1]["jobs"]
    failed = tuple(f"{name}: {jobs.get(name, {}).get('failed', 'not run')}" for name in planned
                   if "first_result" not in jobs.get(name, {}).get("marks", {}))
    if failed:
        return checks.Verdict("jobs ran", checks.FAIL, f"{len(failed)} of {len(planned)} jobs did not finish",
                              {"failed": len(failed)}, {"failed": "lower"}, failed)
    return checks.Verdict("jobs ran", checks.PASS, f"all {len(planned)} jobs ran on {proofs[-1]['type']}",
                          {"jobs": len(planned)})


def wav_seconds_and_dbfs(path):
    """A PCM WAV's length in seconds and its RMS in dBFS."""
    with wave.open(str(path)) as sound:
        width, frames = sound.getsampwidth(), sound.getnframes()
        raw = np.frombuffer(sound.readframes(frames), dtype=np.uint8).reshape(-1, width)
        seconds = frames / sound.getframerate()
    padded = np.zeros((len(raw), 4), dtype=np.uint8)
    padded[:, 4 - width:] = raw  # little-endian samples into the top bytes of an int32, sign kept
    samples = padded.view("<i4").ravel().astype(np.float64) / 2 ** 31
    rms = float(np.sqrt(np.mean(samples ** 2))) if samples.size else 0.0
    return seconds, 20 * np.log10(max(rms, 1e-12))


def take_faults(take, job, clap, before):
    """What is wrong with one MOSS take: missing, wrong length, silent, or scoring under the build before."""
    if not take.is_file():
        return [f"{job['file']}: no take"]
    seconds, dbfs = wav_seconds_and_dbfs(take)
    faults = []
    if abs(seconds - job["seconds"]) > LENGTH_SLACK * job["seconds"]:
        faults.append(f"{job['file']}: {seconds:.2f} s, asked {job['seconds']} s")
    if dbfs < SILENT_DBFS:
        faults.append(f"{job['file']}: silent ({dbfs:.1f} dBFS)")
    if clap is None or clap < before - CLAP_SLACK:
        faults.append(f"{job['file']}: CLAP {clap} against {before} on the build before")
    return faults


def judge_moss_takes(output, inputs, evidence):
    """Pass when every take is there at its asked length, not silent, and scores with CLAP no more than CLAP_SLACK
    under the same prompt, seed and weights on the build before."""
    expect = json.loads((output / PLAN).read_text())["expect"]["takes"]
    jobs = json.loads((inputs["folder"] / expect["jobs"]).read_text())
    folder = output / PROOF / "takes"
    scores_file = folder / expect["scores"]
    scores = json.loads(scores_file.read_text()) if scores_file.is_file() else {}
    faults = [fault for job in jobs for fault in take_faults(folder / job["file"], job, scores.get(job["file"]),
                                                             expect["clap_before"][job["file"]])]
    measures = {f"clap {name}": value for name, value in scores.items()}
    if faults:
        return checks.Verdict("takes sound right", checks.FAIL, f"{len(faults)} faults in {len(jobs)} takes",
                              measures, findings=tuple(faults))
    return checks.Verdict("takes sound right", checks.PASS,
                          f"{len(jobs)} takes at length, heard, CLAP within {CLAP_SLACK} of the build before",
                          measures)


def clip_faults(npz, expect):
    """What is wrong with a Kimodo clip: missing, wrong length, not finite, or not walking as asked."""
    if not npz.is_file():
        return [f"{npz.name}: no clip"], {}
    joints = np.load(npz)["posed_joints"]
    root = joints[:, 0]
    travel = float(np.linalg.norm((root[-1] - root[0])[[0, 2]]))
    height = float(root[:, 1].mean())
    measures = {"frames": int(len(joints)), "travel_metres": round(travel, 2), "root_height_metres": round(height, 2)}
    faults = []
    if len(joints) != int(expect["seconds"] * expect["fps"]):
        faults.append(f"{len(joints)} frames, asked {expect['seconds']} s at {expect['fps']} fps")
    if not np.isfinite(joints).all():
        faults.append("joints not finite")
    for name, value in (("travel_metres", travel), ("root_height_metres", height)):
        low, high = expect[name]
        if not low <= value <= high:
            faults.append(f"{name} {value:.2f} outside {low} to {high}")
    return faults, measures


def judge_motion_clip(output, inputs, evidence):
    """Pass when the walking clip has its asked length, finite joints, and walks: its root travels and stands at a
    person's hip height."""
    expect = json.loads((output / PLAN).read_text())["expect"]["clip"]
    faults, measures = clip_faults(output / PROOF / "clip" / expect["npz"], expect)
    if faults:
        return checks.Verdict("clip walks", checks.FAIL, f"{len(faults)} faults in the clip", measures,
                              findings=tuple(faults))
    return checks.Verdict("clip walks", checks.PASS, "the clip has its length and walks", measures)


PROOF_CHECKS = {"moss": checks.Check("takes sound right", judge_moss_takes),
                "characters-motion": checks.Check("clip walks", judge_motion_clip)}


def proof_checks(kind):
    """Every planned job ran, and the kind's own check of what they made (unknown for a kind without one)."""
    own = PROOF_CHECKS.get(kind) or checks.Check(
        "outputs checked", lambda output, inputs, evidence: checks.Verdict(
            "outputs checked", checks.UNKNOWN, f"no check of what {kind}'s proof jobs make (PROOF_CHECKS)"))
    return (checks.Check("jobs ran", judge_jobs_ran), own)


def plan_euros(kind):
    return float(json.loads((IMAGES / kind / PLAN).read_text())["euros"])


def plan_code(kind):
    """{input name: path pattern} of the repository files the kind's proof jobs run (the plan's `code`), so a change
    to one proves the image again."""
    plan = json.loads((IMAGES / kind / PLAN).read_text())
    return {f"code {path}": f"{{repo}}/{path}" for kind_run in plan["runs"] for path in kind_run.get("code", [])}


# --- the table and publishing --------------------------------------------------------------------------------

def tag_part(kind):
    """images.json read as the kind's published tag alone, so a node keys on its own kind's build only."""
    return lambda path: published_tag(kind, path)


def kind_stages(kind):
    """The kind's pins and proof stages."""
    folder = f"{{images}}/{kind}"
    pins = graph.Stage(f"image-pins-{kind}", "world", make_pins, PINS, pins_checks(kind),
                       files={"folder": folder, "published": ("{images}/images.json", tag_part(kind))})
    proof = graph.Stage(f"image-proof-{kind}", "world", make_proof(kind), PROVED, proof_checks(kind),
                        files={"folder": folder, **plan_code(kind)}, after={pins.name: (PINS.schema, PINS.version)},
                        paid=True, euros=plan_euros(kind))
    return pins, proof


STAGES = tuple(stage for kind in proved_kinds() for stage in kind_stages(kind))


def publish(runner, kind, images_json=IMAGES_JSON):
    """Write the kind's accepted proof record into images.json; the record. Blocked unless the proof passed and
    stands accepted on its current inputs."""
    output = runner.usable(f"image-proof-{kind}", None, (PROVED.schema, PROVED.version))
    record = runner.store.read_file(output, RECORD)
    built = json.loads(pathlib.Path(images_json).read_text())
    built[kind] = record
    pathlib.Path(images_json).write_text(json.dumps(dict(sorted(built.items())), indent=1) + "\n")
    return record
