"""The g-texture method's split (round 4's best: multiview.split with the texture's features) of every model a place's
data lists (data/surfaces/<place>.json `takes`), as the free steps of the split rows (the paid ones are
split_batch_paid.py's). Steps needing trimesh run in the prop environment through this module's command line
(prop_env.py).

Rows (place grain, split-<step>@<place>):
    inputs        (free)  flat/takes.json from the place's data (each take's place, kind, object and library places),
                          the close-up on white for the unlit copy, and the turntable's cameras (multiview.cameras)
    turntable     (paid)  the raw model's own texture drawn unlit round a turntable
    unlit         (paid)  the close-up's unlit copy (delight.py, Marigold-IID)
    regions       (paid)  the unlit copy's SAM 2.1 regions (segment.py)
    asks          (free)  each region's surface question on the unlit copy (R-unlit~<take>), one ask each
    judge         (paid)  the asks answered by the judge (Gemini 3.1 Pro, gemini_judge.py)
    prompts       (free)  SAM 3's pictures and phrases per finish over the turntable (multiview.prompts)
    masks         (paid)  SAM 3 per finish over every view (finish_masks.py)
    split         (free)  multiview.split per take and its gate: no part mixes two finishes by the measured texture
                          (measure.texture_reference's finish per face, measure.part_measures' mixing)
"""
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import surface_gates as gates  # noqa: E402
import prop_env  # noqa: E402

# The turntable's camera check: view c's outline against the close-up's (multiview.close_up_overlap).
OVERLAP_LEAST = 0.8


def takes_of(folder):
    return json.loads((pathlib.Path(folder) / "flat" / "takes.json").read_text())


# --- inputs ---------------------------------------------------------------------------------------------------------

def make_inputs(inputs, out, seed, params):
    prop_env.handover(__file__, "inputs", inputs, out)


def inputs_step(inputs, out):
    """The prop environment's side: flat/takes.json, unlit-in/<take>.png (the close-up on white), multiview/job.json."""
    from PIL import Image
    import multiview
    takes = json.loads(inputs["surfaces"].read_text())["takes"]
    (out / "flat").mkdir(parents=True)
    (out / "flat" / "takes.json").write_text(json.dumps(takes, indent=1))
    (out / "unlit-in").mkdir()
    for take in takes:
        picture = Image.open(inputs[f"close-up {take}"] / "input.png").convert("RGBA")
        white = Image.new("RGBA", picture.size, (255, 255, 255, 255))
        Image.alpha_composite(white, picture).convert("RGB").save(out / "unlit-in" / f"{take}.png")
    multiview.cameras(out, sorted(takes))


def inputs_faults(folder):
    if not (folder / "flat" / "takes.json").exists() or not (folder / "multiview" / "job.json").exists():
        return ["no flat/takes.json or multiview/job.json"]
    missing = [take for take in takes_of(folder) if not (folder / "unlit-in" / f"{take}.png").exists()]
    return [f"no close-up for {missing}"] if missing else []


def judge_inputs(output, inputs, evidence):
    """Pass when every take has its row, its close-up and its cameras."""
    takes = takes_of(output)
    job = json.loads((output / "multiview" / "job.json").read_text())
    named = {entry["take"] for entry in job["takes"]}
    return gates.verdict("inputs", [take for take in takes if take not in named], len(takes), "takes without cameras")


# --- asks -----------------------------------------------------------------------------------------------------------

def scratch_work(inputs, folder, wanted):
    """A work folder for the method modules (they read <work>/<name>/...): flat from inputs, seg-unlit from regions,
    multiview as a real folder holding the cameras, the renders and (from prompts and masks) each take's
    finishes and SAM 3's masks."""
    folder.mkdir(parents=True)
    (folder / "flat").symlink_to(inputs["inputs"] / "flat", target_is_directory=True)
    if "regions" in wanted:
        (folder / "seg-unlit").symlink_to(inputs["regions"] / "seg-unlit", target_is_directory=True)
    if "turntable" in wanted:
        multiview = folder / "multiview"
        multiview.mkdir()
        shutil.copy2(inputs["inputs"] / "multiview" / "job.json", multiview / "job.json")
        unpacked_renders(inputs["turntable"] / "renders", multiview / "renders")
    if "prompts" in wanted:
        for path in (inputs["prompts"] / "takes").iterdir():
            shutil.copytree(path, folder / "multiview" / path.name)
    if "masks" in wanted:
        (folder / "multiview" / "sam3").symlink_to(inputs["masks"] / "sam3", target_is_directory=True)
    return folder


def unpacked_renders(stored, folder):
    """The turntable's renders as multiview reads them: each file linked, each compressed face map (<view>-id.npz,
    as the turntable row keeps them) written out as the <view>-id.npy multiview loads."""
    import numpy as np
    for take in sorted(stored.iterdir()) if stored.is_dir() else []:
        (folder / take.name).mkdir(parents=True)
        for path in take.iterdir():
            if path.name.endswith("-id.npz"):
                np.save(folder / take.name / path.name.replace("-id.npz", "-id.npy"), np.load(path)["ids"])
            else:
                (folder / take.name / path.name).symlink_to(path)


def written_asks(questions, out):
    """The question list part_judge wrote under `questions`, its pictures named from `out`, as asks.json."""
    import part_judge
    listing = questions / part_judge.QUESTIONS
    jobs = json.loads(listing.read_text()) if listing.exists() else []
    jobs = [dict(job, images=[str(pathlib.Path(image).relative_to(out)) for image in job["images"]]) for job in jobs]
    (out / "asks.json").write_text(json.dumps(jobs, indent=1))
    if listing.exists():
        listing.unlink()


def make_asks(inputs, out, seed, params):
    prop_env.handover(__file__, "asks", inputs, out)


def asks_step(inputs, out):
    """The prop environment's side: R-unlit~<take> questions of every region, then asks.json."""
    from PIL import Image
    import measure
    import part_judge
    work = scratch_work(inputs, out / ".work", ("regions",))
    questions = out / "questions"
    for take, entry in takes_of(work).items():
        picture = Image.open(work / "seg-unlit" / f"{take}.png").convert("RGBA")
        pixels = measure.region_pixels(work, "unlit", take)
        part_judge.write_questions(questions, f"R-unlit~{take}", picture, pixels, list(range(int(pixels.max()) + 1)),
                                   entry["object"], measure.materials_of(entry))
    written_asks(questions, out)
    shutil.rmtree(out / ".work")


def asks_faults(folder):
    if not (folder / "asks.json").exists():
        return ["no asks.json"]
    missing = [image for job in json.loads((folder / "asks.json").read_text()) for image in job["images"]
               if not (folder / image).exists()]
    return [f"{len(missing)} pictures missing"] if missing else []


def judge_asks(output, inputs, evidence):
    """Pass when every take has questions."""
    asks = json.loads((output / "asks.json").read_text())
    takes = takes_of(prop_env.short(inputs)["inputs"])
    failing = [take for take in takes if not any(job["name"].startswith(f"R-unlit~{take}-part") for job in asks)]
    return gates.verdict("asks", failing, len(takes), "takes without questions")


# --- prompts --------------------------------------------------------------------------------------------------------

def make_prompts(inputs, out, seed, params):
    prop_env.handover(__file__, "prompts", inputs, out)


def prompts_step(inputs, out):
    """The prop environment's side: multiview.prompts per take; sam3/ and takes/<take>/ (finishes.json,
    finish_pixels.npy, poly_face.npy) kept."""
    import multiview
    work = scratch_work(inputs, out / ".work", ("regions", "turntable"))
    answers = inputs["judge"] / "answers"
    (work / "multiview" / "sam3").mkdir(parents=True)
    for take, entry in takes_of(work).items():
        (work / "multiview" / take).mkdir(parents=True, exist_ok=True)
        multiview.prompts(work, answers, take, entry)
    shutil.move(work / "multiview" / "sam3", out / "sam3")
    (out / "takes").mkdir()
    for take in takes_of(work):
        shutil.move(work / "multiview" / take, out / "takes" / take)
    shutil.rmtree(out / ".work")


def prompts_faults(folder):
    return [] if (folder / "sam3").is_dir() and (folder / "takes").is_dir() else ["no sam3/ or takes/"]


def judge_prompts(output, inputs, evidence):
    """Pass when every take has its finishes and the turntable's view c lies on its close-up (OVERLAP_LEAST)."""
    failing = []
    takes = takes_of(prop_env.short(inputs)["inputs"])
    for take in takes:
        path = output / "takes" / take / "finishes.json"
        if not path.exists():
            failing.append(f"{take}: no finishes")
            continue
        overlap = json.loads(path.read_text())["overlap_c"]
        if overlap < OVERLAP_LEAST:
            failing.append(f"{take}: view c overlaps the close-up {overlap}")
    return gates.verdict("prompts", failing, len(takes), "takes")


# --- split ----------------------------------------------------------------------------------------------------------

def texture_finish(mesh, names, features):
    """The finish per face the measured texture says (measure.texture_reference on the split's own finishes, the
    faces no view saw left out), as indices into the reference's names, -1 unseen; the reference's record."""
    import numpy as np
    import measure
    seen = ~np.isnan(features[:, :measure.TEXTURE_FEATURES]).all(1)
    surface = np.array(names, dtype=object)
    surface[~seen] = None
    found, record = measure.texture_reference(mesh, surface, features)
    return measure.whole_finishes(found), sorted(set(found[found != None].tolist())), record  # noqa: E711


def part_rows(mesh, part_of, part_names, features, reference, reference_names):
    """Per part: its area share, the finish the split gives it, the finish the texture gives most of its seen area
    and the share it gives another, and whether it is big enough to count (measure.PART_LEAST)."""
    import numpy as np
    import measure
    areas = mesh.area_faces
    rows = []
    for part in range(int(part_of.max()) + 1):
        members = part_of == part
        seen = members & (reference >= 0)
        shares = np.bincount(reference[seen], weights=areas[seen], minlength=len(reference_names))
        total = shares.sum()
        order = np.argsort(-shares)
        rows.append({
            "part": part, "area_share": round(float(areas[members].sum() / areas.sum()), 4),
            "finish": part_names[part],
            "texture_finish": reference_names[order[0]] if total > 0 else None,
            "other_finish_share": round(float(shares[order[1]] / total), 3) if total > 0 and len(order) > 1 else 0.0,
            "counted": bool(areas[seen].sum() >= measure.PART_LEAST * areas[reference >= 0].sum())})
    return rows


def measured(mesh, part_of, part_names, face_names, features):
    """A split measured against the texture's finish per face: measure.part_measures (mixing: counted parts whose
    second finish holds MIX_SHARE of their seen area) and the per-part rows."""
    import measure
    reference, reference_names, record = texture_finish(mesh, face_names, features)
    measures = measure.part_measures(mesh.area_faces, reference, part_of)
    rows = part_rows(mesh, part_of, part_names, features, reference, reference_names)
    mixing = [row["part"] for row in rows if row["counted"] and row["other_finish_share"] >= measure.MIX_SHARE]
    return {"measures": measures, "mixing_parts": mixing, "texture": record, "parts": rows}


def split_take(work, take, out):
    """multiview.split with the texture's features, measured; its arrays kept under <out>/<take>/."""
    import numpy as np
    import multiview
    import split_compare
    mesh = split_compare.raw_model(take)
    report = multiview.split(work, take, "split")
    folder = work / "split" / take
    record = json.loads((work / "multiview" / take / "finishes.json").read_text())
    codes = [record["codes"][f"S{number}"] for number in range(len(record["codes"]))]
    part_of, finish = np.load(folder / "parts.npy"), np.load(folder / "finish.npy")
    features = np.load(folder / "features.npy")
    face_names = [codes[number] for number in finish]
    part_names = [codes[int(np.bincount(finish[part_of == part], weights=mesh.area_faces[part_of == part]).argmax())]
                  for part in range(int(part_of.max()) + 1)]
    found = {"method": "multiview", "report": report, **measured(mesh, part_of, part_names, face_names, features)}
    (out / take).mkdir()
    for name in ("parts.npy", "finish.npy", "features.npy", "split.json"):
        shutil.copy2(folder / name, out / take / name)
    shutil.copy2(work / "multiview" / take / "finishes.json", out / take / "finishes.json")
    return found


def make_split(inputs, out, seed, params):
    prop_env.handover(__file__, "split", inputs, out)


def split_step(inputs, out):
    """The prop environment's side: every take split and measured; splits.json and the arrays under <out>/<take>/.
    A take whose split errs is recorded as such and the others go on (its gate fails it)."""
    work = scratch_work(inputs, out / ".work", ("regions", "turntable", "prompts", "masks"))
    found = {}
    for take in takes_of(work):
        try:
            found[take] = split_take(work, take, out)
        except Exception as error:  # noqa: BLE001 - recorded on its take; the gate fails it, the others go on
            found[take] = {"method": "multiview", "error": repr(error)[:600]}
    (out / "splits.json").write_text(json.dumps(found, indent=1))
    shutil.rmtree(out / ".work")


def split_faults(folder):
    return [] if (folder / "splits.json").exists() else ["no splits.json"]


def passes(result):
    return "error" not in result and not result["mixing_parts"]


def judge_split(output, inputs, evidence):
    """The split's own gate: every take split with no part mixing two finishes by the measured texture; a take that
    fails is named and blocks the line (the owner may waive it: the later rows then leave it out)."""
    found = json.loads((output / "splits.json").read_text())
    failing = [f"{take}: " + (entry.get("error") or f"parts {entry['mixing_parts']} mix two finishes")
               for take, entry in found.items() if not passes(entry)]
    return gates.verdict("split", failing, len(found), "takes whose split mixes finishes (one finish a part)")


STEPS = {"inputs": inputs_step, "asks": asks_step, "prompts": prompts_step, "split": split_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
