"""The maker's step runner on a rented card (tools/cloud/characters.py sets the machine up with
characters_setup.sh; never on the owner's PC): a make folder's spec, its folders, every program a step runs and the
record of each step. prop_chain.py's steps run through it; its own step is the clips.

The make folder holds `in/` (prop_person.py wrote it). The chain works in `work/` and writes `out/`, with
`out/make.json`: each step's minutes, the card it ran on, and what failed.

  clips     every clip the spec names that is not made yet, from its sentence (Kimodo with the fixed seed,
            people/clips.py)
"""
import json
import os
import pathlib
import subprocess
import sys
import time

MAKER = pathlib.Path(__file__).resolve().parent
PEOPLE = MAKER.parent / "people"
ENVS = pathlib.Path("/root/envs")
MOTION = ENVS / "motion/bin/python"
# The people tools find their chain through MOTION_HOME (people/paths.py); up here it is a folder whose `env` is the
# motion environment.
MOTION_HOME = pathlib.Path("/root/motion-home")
CUDA_LIBRARIES = "/usr/local/cuda-12.6/lib64"


class Chain:
    """One person's make: its folders, its spec, and the record of every step."""

    def __init__(self, folder):
        self.folder = folder
        self.spec = json.loads((folder / "in/spec.json").read_text())
        self.work = folder / "work"
        self.out = folder / "out"
        self.look = self.work / "look"
        for place in (self.work, self.out, self.look, self.work / "motionwork"):
            place.mkdir(parents=True, exist_ok=True)
        self.record = {"name": self.spec["name"], "card": card_name(), "steps": []}
        # A chain run again for some steps (mending one on a held machine) keeps the steps run before.
        if (self.out / "make.json").exists():
            self.record["steps"] = json.loads((self.out / "make.json").read_text())["steps"]
        self.record["minutes"] = self.minutes()  # a make of no steps (a held machine's hold) took none

    def file(self, relative):
        """A file the spec names, as it lies in the make folder."""
        return self.folder / relative

    def environment(self):
        """What every step's program runs with: the people tools pointed at this make's look and work."""
        return dict(os.environ, MOTION_HOME=str(MOTION_HOME), MOTION_LOOK=str(self.look),
                    MOTION_WORK=str(self.work / "motionwork"), MOTION_PERSON=self.spec["name"],
                    FARM_LOCAL_MODELS="1",
                    LD_LIBRARY_PATH=":".join(filter(None, [CUDA_LIBRARIES, os.environ.get("LD_LIBRARY_PATH")])))

    def run(self, command, **extra):
        """Run one program of a step, its output into the chain's log; raise when it fails."""
        print("$", " ".join(map(str, command)), flush=True)
        environment = {**self.environment(), **extra}
        subprocess.run([str(part) for part in command], check=True, env=environment, cwd=self.work)

    def step(self, name, work):
        """Run one step, timed and recorded; a step that fails ends the chain with the record written."""
        began = time.time()
        entry = {"step": name}
        try:
            entry["notes"] = work() or ""
            entry["ok"] = True
        except Exception as failure:
            entry.update(ok=False, failure=f"{type(failure).__name__}: {failure}")
            raise
        finally:
            entry["minutes"] = round((time.time() - began) / 60, 2)
            entry["card"] = self.record["card"]
            entry["ended"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.record["steps"].append(entry)
            self.write_record()
            print(f"== {name}: {'ok' if entry.get('ok') else 'FAILED'} in {entry['minutes']} min", flush=True)

    def minutes(self):
        """The make's minutes: each step's latest run, summed."""
        latest = {entry["step"]: entry["minutes"] for entry in self.record["steps"]}
        return round(sum(latest.values()), 2)

    def write_record(self):
        self.record["minutes"] = self.minutes()
        (self.out / "make.json").write_text(json.dumps(self.record, indent=1))


def card_name():
    """The card this chain runs on, as the driver names it."""
    answer = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                            text=True)
    return answer.stdout.strip().splitlines()[0] if answer.returncode == 0 else "unknown"


def clips(chain):
    """Every clip the spec names whose sentence has no clip yet, made by Kimodo up here with the fixed seed, its record
    (sentence, model, seed) beside it."""
    sys.path.insert(0, str(PEOPLE))
    import clips as sentences
    wanted = chain.spec.get("clips") or list(sentences.SENTENCES)
    motions = chain.work / "motionwork" / "motions"
    missing = [name for name in wanted if not (motions / f"{name}.npz").exists()]
    made = []
    for name in missing:
        began = time.time()
        chain.run([MOTION_HOME / "env/bin/kimodo_gen", *sentences.kimodo_arguments(name, motions / name)])
        sentences.write_record(name, motions / name)
        made.append(f"{name} {time.time() - began:.0f}s")
    return f"made {len(made)}: " + ", ".join(made) if made else "every clip was made already"
