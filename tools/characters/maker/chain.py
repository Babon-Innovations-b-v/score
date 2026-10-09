"""One person's whole chain on a rented card, from the spec to the built character: runs on the machine
tools/props/cloud/characters.py set up (characters_setup.sh), never on the owner's PC.

    /root/envs/motion/bin/python chain.py /root/make/<name>

The make folder holds `in/` (make.py wrote it). The chain works in `work/`, laid out as the people tools' looks were
made by hand before (#100, #112): `gc/body` (the body at rest), `head`, `hairgen`, `pics`, `parts`, `face` and
`look/`, the look the people tools build from. It writes `out/`: `<name>.glb` (the built person: skeleton, the bare
far body, each outfit, the clips), `<name>.json` (the build's report), `usd/` (UsdSkel), `steps/` (every picture and
mesh a step made, for the review page) and `make.json`: each step's minutes, the card it ran on, and what failed.

The steps, each a program in its own environment:
  picture   the A-pose picture: the spec's own, or drawn by FLUX.2 klein 4B from its description and references
  body      the body read off the picture by SAM3DBody-cpp (body_picture.py)
  rest      the body at rest for the drapes and the head (export_body.py)
  clips     every clip the spec names that is not made yet, from its sentence (Kimodo, people/clips.py)
  drapes    each outfit's GarmentCode pattern draped on the body by Newton's cloth (drape_garment.py)
  head      the skin above the collar and MakeHuman's eyes seated on it (head.py)
  hair      the bald head drawn in clay with the reference's hair (klein), made a mesh (Hi3DGen), laid on the scalp
            as a clean shell (hair_fit.py) and thinned (Blender)
  face      a first build's head as a depth view (face_depth.py), the face drawn on it (klein base 4B with the
            refcontrol depth LoRA), the first seed kept (face_pick.py)
  build     the person built (people/body.py), then made a UsdSkel asset (skel_usd.py), and its joins and stance
            measured into out/checks/ (people/joins.py)
  review    turntables of each outfit and frames through a few clips, rendered by Cycles (blender_review.py)
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

MAKER = pathlib.Path(__file__).resolve().parent
PEOPLE = MAKER.parent / "people"
ENVS = pathlib.Path("/root/envs")
MOTION = ENVS / "motion/bin/python"
PICTURE = ENVS / "picture/bin/python"
HI3DGEN = ENVS / "hi3dgen/bin/python"
GARMENT = ENVS / "garment/bin/python"
BLENDER = pathlib.Path("/root/blender/blender")
# The people tools find their chain through MOTION_HOME (people/paths.py); up here it is a folder whose `env` is the
# motion environment.
MOTION_HOME = pathlib.Path("/root/motion-home")
CUDA_LIBRARIES = "/usr/local/cuda-12.6/lib64"
SEEDS = (1, 2)
HAIR_TRIANGLES = 3600
HAIR_MESH_TRIANGLES = 60000
BALD_VIEW_SIZE = 0.34


class Chain:
    """One person's make: its folders, its spec, and the record of every step."""

    def __init__(self, folder):
        self.folder = folder
        self.spec = json.loads((folder / "in/spec.json").read_text())
        self.work = folder / "work"
        self.out = folder / "out"
        self.look = self.work / "look"
        for place in (self.work, self.out / "steps", self.look, self.work / "pics", self.work / "motionwork"):
            place.mkdir(parents=True, exist_ok=True)
        self.record = {"name": self.spec["name"], "card": card_name(), "steps": []}
        # A chain run again for some steps (mending one on a held machine) keeps the steps run before.
        if (self.out / "make.json").exists():
            self.record["steps"] = json.loads((self.out / "make.json").read_text())["steps"]

    def file(self, relative):
        """A file the spec names, as it lies in the make folder."""
        return self.folder / relative

    def environment(self):
        """What every step's program runs with: the people tools pointed at this make's look and work."""
        return dict(os.environ, MOTION_HOME=str(MOTION_HOME), MOTION_LOOK=str(self.look),
                    MOTION_WORK=str(self.work / "motionwork"), MOTION_PERSON=self.spec["name"],
                    PROPS_BLENDER=str(BLENDER), FARM_LOCAL_MODELS="1",
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

    def write_record(self):
        latest = {entry["step"]: entry["minutes"] for entry in self.record["steps"]}
        self.record["minutes"] = round(sum(latest.values()), 2)
        (self.out / "make.json").write_text(json.dumps(self.record, indent=1))

    def keep(self, path, name=None):
        """Copy a step's picture or mesh into out/steps for the review page."""
        shutil.copy2(path, self.out / "steps" / (name or path.name))


def card_name():
    """The card this chain runs on, as the driver names it."""
    answer = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                            text=True)
    return answer.stdout.strip().splitlines()[0] if answer.returncode == 0 else "unknown"


def prepare_home(chain):
    """The motion home the people tools expect, the clips already made, the shared boots and the look's settings."""
    MOTION_HOME.mkdir(exist_ok=True)
    if not (MOTION_HOME / "env").exists():
        (MOTION_HOME / "env").symlink_to(ENVS / "motion")
    motions = chain.work / "motionwork" / "motions"
    if not motions.exists() and (chain.folder / "in/motions").exists():
        shutil.copytree(chain.folder / "in/motions", motions)
    motions.mkdir(parents=True, exist_ok=True)
    for boot in ("work_boot.npz", "space_boot.npz"):
        shutil.copy2(chain.folder / "in/shared" / boot, chain.look / boot)
    (chain.look / "person.json").write_text(json.dumps(chain.spec.get("look", {}), indent=1))


def picture(chain):
    """The A-pose picture the body is read off: the spec's own, or drawn from its words and references."""
    target = chain.work / "pics" / "apose.png"
    if chain.spec.get("picture"):
        shutil.copy2(chain.file(chain.spec["picture"]), target)
        chain.keep(target)
        return "the spec's own picture"
    references = [chain.file(path) for path in chain.spec.get("references", [])]
    chain.run([PICTURE, MAKER / "drawings.py", "apose", target, chain.spec["description"], *references,
               "--seeds", *map(str, SEEDS)])
    shutil.copy2(chain.work / "pics" / f"apose_s{SEEDS[0]}.png", target)
    for seed in SEEDS:
        chain.keep(chain.work / "pics" / f"apose_s{seed}.png")
    return f"drawn by klein from the description and {len(references)} references; seed {SEEDS[0]} kept"


def body(chain):
    """The identity read off the A-pose picture."""
    chain.run([MOTION, MAKER / "body_picture.py", chain.work / "pics/apose.png", chain.look / "identity.npz"])


def rest(chain):
    """The body at rest, and where its joints sit, into the look."""
    chain.run([MOTION, MAKER / "export_body.py", chain.look / "identity.npz", chain.work / "gc/body"])
    shutil.copy2(chain.work / "gc/body/joints.json", chain.look / "joints.json")


# The garment design each outfit is draped from (data/characters/garments/).
DESIGNS = {"work": "work_suit", "space": "space_suit", "jacket": "jacket", "coat": "coat", "trousers": "trousers"}


def drapes(chain):
    """Each outfit's pattern draped on the body (GarmentCode's pattern, Newton's cloth: drape_garment.py)."""
    made = []
    reference = chain.spec.get("garment_body", "mean_male")
    for outfit in chain.spec.get("outfits", ["work"]):
        chain.run([sys.executable, MAKER / "drape_garment.py", chain.work / "gc/body", DESIGNS[outfit],
                   chain.look / f"{outfit}_drape", "--kind", outfit, "--reference", reference, "--blender", BLENDER],
                  GARMENTCODE="/root/garmentcode", GARMENTCODE_PYTHON=str(GARMENT))
        made.append(outfit)
    return "draped: " + ", ".join(made)


def head(chain):
    """The head's skin and the eyes seated on it."""
    chain.run([MOTION, MAKER / "head.py", chain.work, chain.folder / "in/shared/makehuman"])


def head_picture(chain):
    """What the face and the hair are drawn after: the spec's head, else its picture, else the A-pose drawing."""
    return chain.file(chain.spec.get("head") or chain.spec.get("picture") or "work/pics/apose.png")


def views(chain, prefix, size, azimuths, parts):
    """Grey stills of npz parts round the head (blender_views.py)."""
    eye_height = json.loads((chain.work / "gc/body/joints.json").read_text())["LeftEye"][1]
    centre = f"0,{eye_height + 0.016:.4f},0.0"
    chain.run([BLENDER, "-b", "-P", MAKER / "blender_views.py", "--", prefix, centre, size, "700x700", azimuths,
               *parts])


def hair(chain):
    """The hair: the bald head in clay with the reference's hair (klein), a mesh of it (Hi3DGen), laid on the scalp
    as a shell (hair_fit.py) and thinned (Blender)."""
    made = chain.work / "hairgen"
    made.mkdir(exist_ok=True)
    head_parts = [f"{chain.work / 'head/skin_head.npz'}:0.78", f"{chain.work / 'head/eyes.npz'}:0.97"]
    views(chain, chain.work / "pics/bald", BALD_VIEW_SIZE, "0,35,90,180", head_parts)
    chain.run([PICTURE, MAKER / "drawings.py", "hair", made, chain.spec["hair"], chain.work / "pics/bald_035.png",
               head_picture(chain), "--seeds", *map(str, SEEDS)])
    clay = made / f"klein_s{SEEDS[0]}.png"
    chain.run([HI3DGEN, MAKER / "hair_mesh.py", clay, made / "h3d.glb"])
    chain.run([BLENDER, "-b", "-P", MAKER / "blender_clean.py", "--", made / "h3d.glb", made / "h3d_60k.glb",
               HAIR_MESH_TRIANGLES], NO_DISSOLVE="1")
    chain.run([MOTION, MAKER / "hair_fit.py", chain.work, made / "h3d_60k.glb", made / "hair_full.npz",
               *chain.spec.get("hair_options", [])])
    chain.run([BLENDER, "-b", "-P", MAKER / "blender_decimate.py", "--", made / "hair_full.npz",
               chain.look / "hair.npz", HAIR_TRIANGLES])
    views(chain, chain.work / "pics/hair", 0.32, "0,35,90,180", [*head_parts, f"{chain.look / 'hair.npz'}:0.10"])
    for seed in SEEDS:
        chain.keep(made / f"klein_s{seed}.png", f"hair_clay_s{seed}.png")
    for azimuth in ("000", "035", "090", "180"):
        chain.keep(chain.work / f"pics/hair_{azimuth}.png")
    chain.keep(chain.work / "pics/bald_035.png")


def blank_face(chain):
    """A blank face drawing, so the first build's head is plain skin (the build reads a face before one is drawn)."""
    import numpy as np
    from PIL import Image
    face = chain.look / "face"
    face.mkdir(exist_ok=True)
    Image.new("RGB", (1024, 1024), "white").save(face / "drawn.png")
    np.save(face / "depth.npy", np.full((1024, 1024), -10.0))
    (face / "view.json").write_text(json.dumps({"window": [-0.145, 0.145, 1.0, 1.29], "size": 1024, "keep": []}))


def face(chain):
    """The face: a first build's parts as a depth view, the face drawn on it, the first seed kept."""
    blank_face(chain)
    chain.run([MOTION, PEOPLE / "body.py", "--out", chain.work / "first.glb", "--clips", "standing", "walking",
               "--identity", chain.look / "identity.npz"], DUMP_PARTS=str(chain.work / "parts"))
    chain.run([MOTION, MAKER / "face_depth.py", chain.work])
    chain.run([PICTURE, MAKER / "drawings.py", "face", chain.work / "face", chain.spec["face"],
               chain.work / "face/depth.png", head_picture(chain), "--seeds", *map(str, SEEDS)])
    chain.run([MOTION, MAKER / "face_pick.py", chain.work, str(SEEDS[0]), *chain.spec.get("face_options", [])])
    for seed in SEEDS:
        chain.keep(chain.work / f"face/drawn_s{seed}.png", f"face_s{seed}.png")
    chain.keep(chain.work / "face/depth.png", "face_depth.png")


def clips(chain):
    """Every clip the spec names whose sentence has no clip yet, made by Kimodo up here."""
    sys.path.insert(0, str(PEOPLE))
    import clips as sentences
    wanted = chain.spec.get("clips") or list(sentences.SENTENCES)
    motions = chain.work / "motionwork" / "motions"
    missing = [name for name in wanted if not (motions / f"{name}.npz").exists()]
    made = []
    for name in missing:
        began = time.time()
        sentence, seconds = sentences.SENTENCES[name]
        chain.run([MOTION_HOME / "env/bin/kimodo_gen", sentence, "--model", sentences.MODEL, "--duration",
                   str(seconds), "--output", motions / name, "--bvh", "--bvh_standard_tpose"])
        made.append(f"{name} {time.time() - began:.0f}s")
    return f"made {len(made)}: " + ", ".join(made) if made else "every clip was made already"


def build(chain):
    """The person built from the look, and made a UsdSkel asset."""
    name = chain.spec["name"]
    wanted = chain.spec.get("clips") or []
    chain.run([MOTION, PEOPLE / "body.py", "--out", chain.out / f"{name}.glb", "--report", chain.out / f"{name}.json",
               "--identity", chain.look / "identity.npz", *(["--clips", *wanted] if wanted else [])])
    chain.run([MOTION, MAKER.parent / "skel_usd.py", chain.out / f"{name}.glb", "--out", chain.out / "usd"])
    chain.run([MOTION, PEOPLE / "joins.py", chain.out / f"{name}.glb", "--out", chain.out / "checks", "--record-only"])


# The clips the review page shows moving, where the make has them.
REVIEW_CLIPS = ("standing", "walking", "bench", "waiting", "suit")


def review(chain):
    """The review pictures: a turntable of each outfit and frames through a few clips (blender_review.py)."""
    sys.path.insert(0, str(PEOPLE))
    import clips as sentences
    made = chain.spec.get("clips") or list(sentences.SENTENCES)
    shown = [sentences.in_game(name) for name in made if sentences.in_game(name) in REVIEW_CLIPS]
    chain.run([BLENDER, "-b", "-P", MAKER / "blender_review.py", "--", chain.out / f"{chain.spec['name']}.glb",
               chain.out / "review", "--clips", *shown, "--angles", "8", "--frames", "4", "--size", "448"])
    return f"turntables and {len(shown)} clips"


STEPS = (("picture", picture), ("body", body), ("rest", rest), ("clips", clips), ("drapes", drapes), ("head", head),
         ("hair", hair), ("face", face), ("build", build), ("review", review))


def main():
    chain = Chain(pathlib.Path(sys.argv[1]))
    wanted = sys.argv[2:] or [name for name, _ in STEPS]
    chain.step("prepare", lambda: prepare_home(chain))
    for name, work in STEPS:
        if name in wanted:
            chain.step(name, lambda work=work: work(chain))
    print(f"made {chain.spec['name']} in {chain.record['minutes']} min on {chain.record['card']}", flush=True)


if __name__ == "__main__":
    main()
