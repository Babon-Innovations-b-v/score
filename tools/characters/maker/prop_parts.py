"""The prop route's parts and paint for a person's Pixal3D mesh, as every prop's (tools/props/library/CLAUDE.md: the
painting unit is a 3D part, each part one surface; no picture colour reaches the mesh):

    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_parts.py questions <run> <take> <spec.json> [--outfit work]
    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_parts.py parts <run> <take> <spec.json> [--outfit work]

Before `questions`: the close-up's SAM 2.1 regions (../../props/cloud/segment.py on <run>/pictures/<take>.png, the
batch's cut-out), split_compare.py `inputs` (<run>/<take>/up/), GeoSAM2 seeded with them on the raw model
(../../props/cloud/meshparts.py --methods geosam2) and the split laid on the raw model (split_spread.lay_geosam2).

`questions` writes each GeoSAM2 part outlined on the close-up with the person's allowed materials (part_judge.py) to
<run>/questions/ for ../../props/cloud/judge.py, each asked with three seeds. `parts` reads the answers
(<run>/answers/), names each part's material (most of its seeds' usable answers, else the nearest allowed colour), gives each part its role in the
body (skin, hair, garment, hard) and the name joins.py knows it by (skin_head, skin_hands, hair, cloth, a boot or a
mitt, split by side in the build, and any other hard part by its material), carries the split from the raw model onto the finished one (the finish's own
turn, refined: labels.finish_turn and onto_finished) and writes <run>/<take>/parts.npz (each finished face's part,
the parts' names, roles, materials and linear colours) and parts.json.

The person's materials (`person_materials`, the outfit's palette) are library families with this person's own colours: the outfit's from
people/paint.py's palette for its design (the shipped people's colours), the skin and hair from its look
(person.json's `skin` and `hair`, take C's where the spec's look gives none), as a place passes its own tokens. No
colour is read off the picture.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
LIBRARY = HERE.parents[1] / "props" / "library"
sys.path.insert(0, str(LIBRARY))
sys.path.insert(0, str(LIBRARY.parent))

import labels  # noqa: E402
import part_judge  # noqa: E402
import split_compare  # noqa: E402

# Take C's skin and hair (people/person.py TAKE_C) and the chinese outfits' palettes (people/paint.py: the work suit's
# NAVY, GREY, RED, BLACK, STEEL, BOOT and FLAG; the space suit's SUIT_FLAT), in sRGB. Copied, not imported: people/
# has a paths.py of its own that shadows the props library's.
TAKE_C_SKIN, TAKE_C_HAIR = (226, 172, 138), (24, 24, 28)
WORK_CHINESE = {"navy fabric": ("fabric", (50, 57, 78)), "light grey fabric": ("fabric", (138, 136, 132)),
                "red piping fabric": ("fabric", (178, 58, 44)), "black leather belt": ("rubber", (30, 31, 34)),
                "steel buckle": ("steel", (150, 152, 156)), "black rubber boot": ("rubber", (32, 34, 34)),
                "printed flag patch": ("print", (184, 48, 38))}
SPACE_CHINESE = {"white suit fabric": ("fabric", (228, 224, 212)), "white backpack plastic": ("plastic", (220, 216, 202)),
                 "white helmet plastic": ("plastic", (228, 224, 212)), "gold visor rim": ("steel", (228, 174, 40)),
                 "dark visor glass": ("glass", (14, 14, 18)), "light grey box plastic": ("plastic", (190, 192, 186)),
                 "light grey neck ring plastic": ("plastic", (190, 192, 186)),
                 "green band fabric": ("fabric", (58, 128, 64)), "grey strap fabric": ("fabric", (150, 154, 150)),
                 "red band fabric": ("fabric", (200, 58, 40)), "gold band fabric": ("fabric", (228, 174, 40)),
                 "grey mitten rubber": ("rubber", (118, 120, 118)), "grey knee pad rubber": ("rubber", (150, 155, 148)),
                 "grey moon boot rubber": ("rubber", (140, 141, 137)), "dark knob plastic": ("plastic", (70, 72, 74)),
                 "printed flag patch": ("print", (184, 48, 38))}
OUTFIT_PALETTES = {"work": WORK_CHINESE, "space": SPACE_CHINESE}
# The materials a part named by them is: boots and mitts are split by side for joins.py (boot_l, mitt_r, ...).
BOOTS = ("black rubber boot", "grey moon boot rubber")
MITTS = ("grey mitten rubber",)
# A part's role in the body, by its material's family.
ROLES = {"skin": "skin", "hair": "hair", "fabric": "garment", "print": "garment", "rubber": "hard", "steel": "hard",
         "plastic": "hard", "glass": "hard"}
# Each part is asked with these seeds and most of the usable answers decide (closeup/check.py's rule: one answer alone
# called a pocket a steel buckle, and another ran out of thinking before it answered).
SEEDS = (7, 8, 9)
# A skin part above this share of the height is the head's.
HEAD_SHARE = 0.8


def linear(srgb):
    """An sRGB colour (0..255) as linear RGB, as the library's tokens are."""
    shares = np.asarray(srgb, float) / 255
    return np.where(shares <= 0.04045, shares / 12.92, ((shares + 0.055) / 1.055) ** 2.4).tolist()


def person_materials(spec, outfit):
    """The person's allowed materials in one outfit: name to {"family", "colour" (linear)}."""
    look = spec.get("look", {})
    found = {"skin": {"family": "skin", "colour": linear(look.get("skin", TAKE_C_SKIN))},
             "hair": {"family": "hair", "colour": linear(look.get("hair", TAKE_C_HAIR))}}
    for name, (family, colour) in OUTFIT_PALETTES[outfit].items():
        found[name] = {"family": family, "colour": linear(colour)}
    return found


def raw_parts(run, take):
    """GeoSAM2's split on the raw model's welded faces (split_spread.lay_geosam2's file)."""
    return np.load(run / take / "parts_geosam2_guided.npy")


def questions(run, take, spec, outfit):
    """Each part outlined on the close-up with its question, into <run>/questions/; the question names."""
    mesh = split_compare.raw_model(take)
    part_of = raw_parts(run, take)
    picture, seen, row, column = labels.picture_view(mesh, take)
    pixels = part_judge.part_pixels(part_of, seen, row, column, np.asarray(picture).shape[:2])
    parts = [int(part) for part in np.unique(pixels) if part >= 0]
    words = f"a person: {spec['description']}, wearing {spec['outfit_words'][outfit]}"
    asked = part_judge.write_questions(run / "questions", take, picture, pixels, parts, words,
                                       person_materials(spec, outfit))
    return seeded(run / "questions" / part_judge.QUESTIONS, asked)


def seeded(listing, asked):
    """Each question in `asked` asked with every one of SEEDS (its name ending -s<seed>), in the questions file."""
    jobs = json.loads(listing.read_text())
    kept = [job for job in jobs if job["name"] not in asked]
    for job in jobs:
        if job["name"] in asked:
            kept += [dict(job, name=f"{job['name']}-s{seed}", seed=seed) for seed in SEEDS]
    listing.write_text(json.dumps(kept, indent=1))
    return [f"{name}-s{seed}" for name in asked for seed in SEEDS]


def judged_by_most(folder, take, count, names):
    """Each part's material by most of its seeds' usable answers ({part: material}); a tie goes to the lowest seed's."""
    found = {}
    for part in range(count):
        picks = []
        for seed in SEEDS:
            path = pathlib.Path(folder) / f"{take}-part{part:02d}-s{seed}.txt"
            answer = part_judge.answer_of(path.read_text()) if path.exists() else None
            code = str((answer or {}).get("material", "")).strip().upper()
            codes = {part_judge.code(index): name for index, name in enumerate(names)}
            if code in codes:
                picks.append(codes[code])
        if picks:
            found[part] = max(picks, key=lambda name: (picks.count(name), -picks.index(name)))
    return found


def materials_of_parts(run, take, part_of, materials, mesh):
    """Each part's material name: the judge's answer, else the allowed colour nearest the part's seen colour."""
    view = labels.picture_view(mesh, take)
    colours = labels.face_colours(mesh, view)
    count = int(part_of.max()) + 1
    judged = judged_by_most(run / "answers", take, count, list(materials))
    names, anchors = labels.anchors_of(materials)
    found = {}
    for part in range(count):
        if part in judged:
            found[part] = judged[part]
            continue
        seen = colours[part_of == part]
        seen = seen[~np.isnan(seen).any(1)]
        found[part] = names[int(np.argmin(np.linalg.norm(anchors - np.median(seen, 0), axis=1)))] if len(seen) \
            else None
    return found


def onto_final(take, mesh):
    """The raw model's faces carried onto the finished model: each finished face's raw face."""
    final = labels.welded(trimesh.load(labels.PIXAL / f"{take}-final.glb", force="mesh", process=False))
    matrix, gap = labels.onto_finished(mesh.sample(labels.SAMPLED, seed=1), final.sample(labels.SAMPLED, seed=2),
                                       labels.finish_turn(take))
    moved = mesh.triangles_center @ matrix[:3, :3].T + matrix[:3, 3]
    return cKDTree(moved).query(final.triangles_center)[1], final, gap


def part_names(final, part_of, roles, materials):
    """Each part's name as joins.py and the build know it, from its role, material and place on the body."""
    height = final.bounds[1, 1] - final.bounds[0, 1]
    names = {}
    for part, role in roles.items():
        middle = final.triangles_center[part_of == part].mean(0)
        if role == "skin":
            names[part] = "skin_head" if middle[1] - final.bounds[0, 1] > HEAD_SHARE * height else "skin_hands"
        elif role == "hair":
            names[part] = "hair"
        elif role == "garment":
            names[part] = "cloth"
        elif materials[part] in BOOTS:
            names[part] = "boot"
        elif materials[part] in MITTS:
            names[part] = "mitt"
        else:
            names[part] = materials[part].replace(" ", "_")
    return names


def parts(run, take, spec, outfit):
    """The split on the finished model with each part's material, role and name: <run>/<take>/parts.npz and .json."""
    mesh = split_compare.raw_model(take)
    materials = person_materials(spec, outfit)
    fallback = next(iter(OUTFIT_PALETTES[outfit]))
    raw = raw_parts(run, take)
    chosen = materials_of_parts(run, take, raw, materials, mesh)
    raw_of_final, final, gap = onto_final(take, mesh)
    part_of = raw[raw_of_final]
    roles = {part: ROLES[materials[name]["family"]] if name else "garment" for part, name in chosen.items()}
    names = part_names(final, part_of, roles, {part: name or fallback for part, name in chosen.items()})
    used = sorted(set(part_of.tolist()))
    record = {"take": take, "registration_gap_m": round(float(gap), 4), "faces": len(final.faces),
              "parts": [{"part": part, "name": names[part], "role": roles[part], "material": chosen[part],
                         "family": materials[chosen[part]]["family"] if chosen[part] else None,
                         "share": round(float((part_of == part).mean()), 4)} for part in used]}
    np.savez_compressed(run / take / "parts.npz", part_of=part_of, names=np.array([names[part] for part in used]),
                        parts=np.array(used), roles=np.array([roles[part] for part in used]),
                        colours=np.array([materials[chosen[part] or fallback]["colour"] for part in used]))
    (run / take / "parts.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=("questions", "parts"))
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("take")
    parser.add_argument("more", help="the prop route spec (data/characters/makes/<name>.json)")
    parser.add_argument("--outfit", default="work", choices=sorted(OUTFIT_PALETTES))
    options = parser.parse_args()
    spec = json.loads(pathlib.Path(options.more).read_text())
    if options.what == "questions":
        print(f"{len(questions(options.run, options.take, spec, options.outfit))} questions in {options.run / 'questions'}")
    else:
        record = parts(options.run, options.take, spec, options.outfit)
        print(json.dumps(record["parts"]))


if __name__ == "__main__":
    main()
