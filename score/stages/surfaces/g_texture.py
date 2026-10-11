"""The g-texture method's naming rows (round 4's best arm: the texture-feature split, every part asked on the raw
texture's views) and its seed of the finish registry, after its split rows (split_batch.py). Its last row writes the
method's interface: per model its parts, each with its measured finish and the judge's surface for it (PARTS in
__init__.py); everything after it (the registry, the paint, the bake, the checks) is the framework's (place_line.py).

Rows (place grain, surfaces-<step>@<place>):
    asks    (free)  each split part's question on the raw texture's front (turntable view c) or on the turntable view
                    showing most of it (paint.ask), one ask each
    judge   (paid)  the asks answered by the judge (split_batch_paid.make_judge: Gemini 3.1 Pro)
    parts   (free)  per part its measured finish (multiview.exemplar over its core faces: the unlit texture's L*, a*,
                    b*, metalness, roughness), the judge's surface and words, set aside or unknown; per face its seen
                    colour
Rows (world grain), the hub's picked models (data/surfaces/finish-seed.json) as the registry's first groups:
    surfaces-seed-inputs, surfaces-seed-turntable (paid): split_batch's and split_batch_paid's, on the seed's takes
    surfaces-seed   (free)  per picked model and surface its stored paint gives (data/parts/<take>.npz), the finish
                    its faces measure on the turntable: one group, that surface
"""
import argparse
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
import split_batch  # noqa: E402

ARM = "g-texture"  # round 4's best arm: the texture-feature split, every part asked on the raw texture's views


def takes_of(inputs):
    return json.loads((inputs["inputs"] / "flat" / "takes.json").read_text())


def passing(inputs):
    """The takes whose split passed its gate (a failed one the owner waived is left out from here on)."""
    found = json.loads((inputs["split"] / "splits.json").read_text())
    return [take for take, entry in found.items() if split_batch.passes(entry)]


def work_folder(inputs, folder):
    """A work folder as paint.py and multiview read it: flat/ (the takes), multiview/job.json, the turntable's
    renders (face maps unpacked) and, with a split, each take's finishes."""
    folder.mkdir(parents=True)
    (folder / "flat").symlink_to(inputs["inputs"] / "flat", target_is_directory=True)
    multiview = folder / "multiview"
    multiview.mkdir()
    shutil.copy2(inputs["inputs"] / "multiview" / "job.json", multiview / "job.json")
    split_batch.unpacked_renders(inputs["turntable"] / "renders", multiview / "renders")
    for take in takes_of(inputs):
        if "split" in inputs and (inputs["split"] / take / "finishes.json").exists():
            (multiview / take).mkdir()
            shutil.copy2(inputs["split"] / take / "finishes.json", multiview / take / "finishes.json")
    return folder


def paint_arguments(work, take, entry, parts, answers=None, questions=None):
    """paint.py's arguments for one take (the g-texture arm: texture front, every turntable view), its surfaces read
    under the name the library knows its place by (the data's library_places)."""
    return argparse.Namespace(arm=ARM, take=take, parts=parts, front=work / "multiview/renders" / take / "c.png",
                              place=entry["library_places"][0], kind=entry["kind"], object=entry["object"],
                              questions=questions, answers=answers, turntable=True, work=work)


# --- asks ----------------------------------------------------------------------------------------------------------

def make_asks(inputs, out, seed, params):
    prop_env.handover(__file__, "asks", inputs, out)


def asks_step(inputs, out):
    """The prop environment's side: every passing split's part questions (paint.ask), then asks.json."""
    import numpy as np
    import labels
    import paint
    work = work_folder(inputs, out / ".work")
    questions = out / "questions"
    for take in passing(inputs):
        entry = takes_of(inputs)[take]
        parts = work / f"{take}-parts.npy"
        np.save(parts, np.load(inputs["split"] / take / "parts.npy").astype(int))
        arguments = paint_arguments(work, take, entry, parts, questions=questions)
        paint.ask(arguments, paint.raw_mesh(take), np.load(parts),
                  labels.allowed_materials(arguments.place, arguments.kind, []))
    split_batch.written_asks(questions, out)
    shutil.rmtree(out / ".work")


def asks_faults(folder):
    if not (folder / "asks.json").exists():
        return ["no asks.json"]
    missing = [image for job in json.loads((folder / "asks.json").read_text()) for image in job["images"]
               if not (folder / image).exists()]
    return [f"{len(missing)} pictures missing"] if missing else []


def judge_asks(output, inputs, evidence):
    """Pass when every take whose split passed has questions."""
    asks = json.loads((output / "asks.json").read_text())
    takes = passing(prop_env.short(inputs))
    failing = [take for take in takes if not any(f"~{take}-part" in job["name"] for job in asks)]
    return gates.verdict("asks", failing, len(takes), "takes without questions", {"asks": len(asks)})


# --- parts: the method's interface ---------------------------------------------------------------------------------

def part_finish(features, mesh, members):
    """A part's measured finish (multiview.exemplar over its exemplar faces): {centre, spread} of L*, a*, b*,
    metalness and roughness; None when no face of it has a measured texture."""
    import numpy as np
    import measure
    import multiview
    texture = features[:, :measure.TEXTURE_FEATURES]
    faces = multiview.exemplar_faces(mesh, texture[:, :3], members)
    if faces.sum() < 1:
        return None
    centre, spread = multiview.exemplar(texture, faces)
    if np.isnan(centre).all():
        return None
    return {"centre": [None if value != value else round(float(value), 4) for value in centre],
            "spread": [None if value != value else round(float(value), 4) for value in spread]}


def parts_take(inputs, work, take, out):
    """One take's parts: each part's finish, the judge's surface and words, set aside or not; the arrays kept."""
    import numpy as np
    import labels
    import paint
    entry = takes_of(inputs)[take]
    part_of = np.load(inputs["split"] / take / "parts.npy").astype(int)
    parts = work / f"{take}-parts.npy"
    np.save(parts, part_of)
    arguments = paint_arguments(work, take, entry, parts, answers=inputs["judge"] / "answers")
    mesh = paint.raw_mesh(take)
    materials = labels.allowed_materials(arguments.place, arguments.kind, [])
    front, others = paint.views(mesh, arguments)
    judged, set_aside, undecided = paint.judged_parts(arguments, part_of, materials, front, others)
    features = np.load(inputs["split"] / take / "features.npy")
    areas = mesh.area_faces
    rows = [{"part": part, "share": round(float(areas[part_of == part].sum() / areas.sum()), 4),
             "finish": part_finish(features, mesh, part_of == part),
             "judge": judged[part][0] if part in judged else None,
             "words": judged[part][1] if part in judged else None, "set_aside": part in set_aside}
            for part in range(int(part_of.max()) + 1)]
    (out / take).mkdir(parents=True)
    np.save(out / take / "parts.npy", part_of.astype(np.int32))
    np.save(out / take / "colours.npy", paint.seen_colours(mesh, front, others).astype(np.float32))
    return {"method": ARM, "parts": rows, "judge_unknown": undecided}


def make_parts(inputs, out, seed, params):
    prop_env.handover(__file__, "parts", inputs, out)


def parts_step(inputs, out):
    """The prop environment's side: every passing take's parts (parts.json and its arrays); a take whose split
    failed is listed as left out."""
    work = work_folder(inputs, out / ".work")
    takes = passing(inputs)
    found = {take: parts_take(inputs, work, take, out) for take in takes}
    left = {take: "its split failed its gate" for take in takes_of(inputs) if take not in takes}
    (out / "parts.json").write_text(json.dumps({"takes": found, "left_out": left}, indent=1))
    shutil.rmtree(out / ".work")


def parts_faults(folder):
    if not (folder / "parts.json").exists():
        return ["no parts.json"]
    missing = [take for take in json.loads((folder / "parts.json").read_text())["takes"]
               if not (folder / take / "parts.npy").exists()]
    return [f"no parts.npy for {missing}"] if missing else []


def judge_parts(output, inputs, evidence):
    """Pass when every take whose split passed has its parts; the judge's unknown parts as a measure."""
    found = json.loads((output / "parts.json").read_text())["takes"]
    takes = passing(prop_env.short(inputs))
    failing = [f"{take}: no parts" for take in takes if take not in found]
    return gates.verdict("parts", failing, len(takes), "models",
                         {"judge unknown": sum(len(record["judge_unknown"]) for record in found.values())})


# --- the registry's seed: the owner's picks -------------------------------------------------------------------------

def seed_take(inputs, work, take):
    """One picked model's groups: per surface its stored paint gives, the finish its faces measure."""
    import multiview
    import paint
    import stored_parts
    from scipy.spatial import cKDTree
    mesh = paint.raw_mesh(take)
    folder = work / "features" / take
    folder.mkdir(parents=True)
    features = multiview.face_features(work, take, mesh, multiview.texture_colours(work, take, mesh), folder)
    matrix, _, _ = paint.finished_frame(mesh, take)
    moved = mesh.copy()
    moved.apply_transform(matrix)
    points, names = stored_parts.read(inputs[f"parts {take}"])
    surface = names[cKDTree(points).query(moved.triangles_center)[1]]
    groups = []
    for name in sorted(set(surface.tolist())):
        finish = part_finish(features, mesh, surface == name)
        if finish is not None:
            groups.append({"id": f"S-{take}-{name}", "surface": str(name), "judge": None, **finish,
                           "first": {"seed": "the owner's pick", "take": take}})
    return groups


def make_seed(inputs, out, seed, params):
    prop_env.handover(__file__, "seed", inputs, out)


def seed_step(inputs, out):
    """The prop environment's side: seed.json, every picked model's groups."""
    work = work_folder(inputs, out / ".work")
    found = {take: seed_take(inputs, work, take) for take in takes_of(inputs)}
    (out / "seed.json").write_text(json.dumps({"groups": [group for groups in found.values() for group in groups],
                                               "takes": {take: len(groups) for take, groups in found.items()}},
                                              indent=1))
    shutil.rmtree(out / ".work")


def seed_faults(folder):
    return [] if (folder / "seed.json").exists() else ["no seed.json"]


def judge_seed(output, inputs, evidence):
    """Pass when every picked model gave at least one measured group."""
    found = json.loads((output / "seed.json").read_text())["takes"]
    failing = [f"{take}: no surface with a measured finish" for take, count in found.items() if not count]
    return gates.verdict("seed", failing, len(found), "picked models", {"groups": sum(found.values())})


STEPS = {"asks": asks_step, "parts": parts_step, "seed": seed_step}

if __name__ == "__main__":
    prop_env.main(STEPS)
