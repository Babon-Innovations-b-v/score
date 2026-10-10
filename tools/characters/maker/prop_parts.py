"""The prop route's parts and paint for a person's Pixal3D mesh, as every prop's (tools/props/library/CLAUDE.md: the
painting unit is a 3D part, each part one surface; no picture colour reaches the mesh):

    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_parts.py questions <run> <take> <spec.json> [--outfit work]
    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_parts.py parts <run> <take> <spec.json> [--outfit work]

Before `questions`: the close-up's SAM 2.1 regions (../../props/cloud/segment.py on <run>/pictures/<take>.png, the
batch's cut-out), split_compare.py `inputs` (<run>/<take>/up/), GeoSAM2 seeded with them on the raw model
(../../props/cloud/meshparts.py --methods geosam2) and the split laid on the raw model (split_spread.lay_geosam2).

`questions` writes each GeoSAM2 part outlined on the close-up with the person's allowed materials (part_judge.py) to
<run>/questions/ for ../../props/cloud/judge.py, each asked with three seeds; `regions` adds each finish region of the
close-up (`finish_regions`: SAM 2.1's smaller masks, a shoulder panel, the flag, the belt's front, the piping) to the
same list, so one judge run answers both. `parts` reads the answers (<run>/answers/), names each part's material (most
of its seeds' usable answers, else the nearest allowed colour), gives each part its role in the body (skin, hair,
garment, hard) and the name joins.py knows it by (skin_head, skin_hands, hair, cloth, a boot or a mitt, split by side in
the build, and any other hard part by its material), gives each judged finish region's seen faces a part of its own
where its material differs from theirs (`with_regions`; an answer whose colour lies far from the region's own on the
close-up is not believed), carries the split from the raw model onto the finished one (the finish's own turn, refined:
labels.finish_turn and onto_finished) and writes <run>/<take>/parts.npz (each finished face's part, the parts' names,
roles, materials and linear colours) and parts.json.

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
from PIL import Image
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
                "red piping print": ("print", (178, 58, 44)), "black leather belt": ("rubber", (30, 31, 34)),
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
# Finishes inside a part (labels.with_finishes) are not painted by colour here: on klein's darker render of the
# player the navy reads L* 18 to 33, nearer the hair's and the belt's anchors (tuned to the props' studio close-ups)
# than the navy's, and the finish pass turned his judged grey yoke navy (0.69 % of the surface to 0.02 %) while it
# found the red piping on 0.04 %. A finish gets a part of its own only where the split gives it one.
# Each part is asked with these seeds and most of the usable answers decide (closeup/check.py's rule: one answer alone
# called a pocket a steel buckle, and another ran out of thinking before it answered).
SEEDS = (7, 8, 9)
# A skin part above this share of the height is the head's.
HEAD_SHARE = 0.8
# A finish region (finish_regions) is a SAM 2.1 mask of at least REGION_FLOOR pixels and at most FINISH_MOST of the
# figure (the player's piping on one upper arm is 1,007 pixels, his flag 1,863, his suit's front 73,000); it takes
# faces from its parts only where at least REGION_FACES_LEAST seen faces change material.
REGION_FLOOR = 150
FINISH_MOST = 0.06
REGION_FACES_LEAST = 20
REGION_COLOUR_MOST = 50.0


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


def finish_regions(run, take):
    """The close-up's finishes as regions: each pixel's smallest SAM 2.1 mask (segment.py's, of the batch's
    cut-out) holding between REGION_FLOOR pixels and FINISH_MOST of the figure, -1 elsewhere. The grey shoulder
    panels, the flag, the belt's front and the piping on the player's upper arms are masks of their own there, where
    GeoSAM2's parts kept one panel, no flag, no piping and the belt only at the back (review, 2026-10-10)."""
    import regions
    masks = regions.masks_of(run / "pictures" / "masks" / f"{take}.npz")
    figure = np.asarray(Image.open(labels.PIXAL / f"{take}.svviews" / "input.png").convert("RGBA"))[..., 3] > 127
    area = (masks & figure).sum(axis=(1, 2))
    found = np.full(figure.shape, -1)
    for index in np.argsort(-area):  # largest first, so the smallest over a pixel is laid last
        if REGION_FLOOR <= area[index] <= FINISH_MOST * figure.sum():
            found[masks[index] & figure] = index
    return found


def region_questions(run, take, spec, outfit):
    """Each finish region outlined on the close-up with its question, into <run>/questions/ beside the parts'; the
    names."""
    found = finish_regions(run, take)
    picture = Image.open(labels.PIXAL / f"{take}.svviews" / "input.png")
    words = f"a person: {spec['description']}, wearing {spec['outfit_words'][outfit]}"
    asked = part_judge.write_questions(run / "questions", region_take(take), picture, found,
                                       [int(region) for region in np.unique(found) if region >= 0], words,
                                       person_materials(spec, outfit))
    return seeded(run / "questions" / part_judge.QUESTIONS, asked)


def region_take(take):
    """The name a take's region questions go by, beside its part questions in one list for one judge run."""
    return f"{take}-region"


def with_regions(run, take, mesh, part_of, chosen, materials):
    """The split with each judged finish region carried onto the raw model's faces the close-up's camera sees: a seen
    face whose pixel lies in a region judged a material other than its part's goes to that region's own part
    (numbered after the last). The new split and every part's material."""
    found = finish_regions(run, take)
    judged = judged_by_most(run / "answers", region_take(take), int(found.max()) + 1, list(materials))
    if not judged:
        return part_of, chosen
    picture, seen, row, column = labels.picture_view(mesh, take)
    judged = believable(judged, found, np.asarray(picture.convert("RGB")) / 255, materials)
    region = np.where(seen, found[row, column], -1)
    part_of, chosen = part_of.copy(), dict(chosen)
    following = int(part_of.max()) + 1
    for number, material in sorted(judged.items()):
        moved = (region == number) & (np.array([chosen.get(int(part)) for part in part_of]) != material)
        if moved.sum() >= REGION_FACES_LEAST:
            part_of[moved] = following
            chosen[following] = material
            following += 1
    return part_of, chosen


def believable(judged, found, picture, materials):
    """The judged regions whose median colour on the close-up lies within REGION_COLOUR_MOST (Lab) of their material's
    colour: the judge called the player's white sleeve stripe red piping (66 apart), while the thin piping itself,
    mixed with the navy round it, reads 45 apart."""
    kept = {}
    for region, material in judged.items():
        pixels = picture[found == region]
        colour = labels.lab(labels.srgb(np.asarray(materials[material]["colour"])))
        if len(pixels) and np.linalg.norm(labels.lab(np.median(pixels, 0)) - colour) <= REGION_COLOUR_MOST:
            kept[region] = material
    return kept


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


def colour_pick(part_of, part, colours, names, anchors):
    """The allowed material whose colour is nearest the part's seen colour (its median), or None where unseen."""
    seen = colours[part_of == part]
    seen = seen[~np.isnan(seen).any(1)]
    return names[int(np.argmin([labels.weighted(np.median(seen, 0), anchor) for anchor in anchors]))] if len(seen) \
        else None


def bordering(mesh, part_of, part, answered):
    """The answered part `part` shares the most edges with, or None."""
    pairs = mesh.face_adjacency
    sides = part_of[pairs]
    across = sides[(sides[:, 0] == part) ^ (sides[:, 1] == part)].ravel()
    across = across[(across != part) & np.isin(across, list(answered))]
    return int(np.bincount(across).argmax()) if len(across) else None


def materials_of_parts(run, take, part_of, materials, mesh):
    """The split and each part's material name: the judge's answer by most seeds; a part it gave no usable answer for
    is cut by its mirror image and each piece takes its mirror part's answer (the player's left forearm and hand, one
    part every seed thought about past its limit, take his right cuff's navy and his right hand's skin); a piece with
    no answered mirror takes the answered part it borders most (labels.py's rule for a part the camera hardly saw),
    and only one bordering none the allowed colour nearest its own. The close-up's colours are a poor guide on a dark
    suit: the player's navy reads L* 18 to 33, nearer the hair's and the belt's anchors than the navy's (the colour
    pick painted that forearm hair). (split, {part: material})"""
    judged = judged_by_most(run / "answers", take, int(part_of.max()) + 1, list(materials))
    unanswered = [int(part) for part in np.unique(part_of) if part not in judged]
    part_of, mirror_of = mirrored(part_of, unanswered, judged, mesh.triangles_center)
    found = dict(judged)
    found.update({piece: judged[mirror] for piece, mirror in mirror_of.items()})
    for part in np.unique(part_of):
        if int(part) not in found:
            neighbour = bordering(mesh, part_of, part, judged)
            found[int(part)] = judged[neighbour] if neighbour is not None else None
    if any(name is None for name in found.values()):
        colours = labels.face_colours(mesh, labels.picture_view(mesh, take))
        names, anchors = labels.anchors_of(materials)
        found = {part: name or colour_pick(part_of, part, colours, names, anchors) for part, name in found.items()}
    return part_of, found


def mirrored(part_of, unanswered, judged, middles):
    """The unanswered parts cut by their mirror image: each of their faces takes the part of the face nearest its
    mirror across the figure's middle (the raw model's x is the close-up's across, the figure stands in a symmetric
    A-pose), where that part is answered. The new split (pieces numbered after the last) and each piece's mirror
    part."""
    part_of = part_of.copy()
    middle = np.median(middles[:, 0])
    flipped = middles * [-1.0, 1.0, 1.0] + [2 * middle, 0.0, 0.0]
    answered = np.isin(part_of, list(judged))
    if not answered.any():
        return part_of, {}
    tree = cKDTree(middles[answered])
    answered_parts = part_of[answered]
    following, mirror_of = int(part_of.max()) + 1, {}
    for part in unanswered:
        faces = np.flatnonzero(part_of == part)
        mirrors = answered_parts[tree.query(flipped[faces])[1]]
        for mirror in np.unique(mirrors):
            part_of[faces[mirrors == mirror]] = following
            mirror_of[following] = int(mirror)
            following += 1
    return part_of, mirror_of


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
    raw, chosen = materials_of_parts(run, take, raw_parts(run, take), materials, mesh)
    raw, chosen = with_regions(run, take, mesh, raw, chosen, materials)
    raw_of_final, final, gap = onto_final(take, mesh)
    part_of = raw[raw_of_final]
    used = sorted(set(part_of.tolist()))
    roles = {part: ROLES[materials[chosen[part]]["family"]] for part in used}
    names = part_names(final, part_of, roles, chosen)
    record = {"take": take, "registration_gap_m": round(float(gap), 4), "faces": len(final.faces),
              "parts": [{"part": part, "name": names[part], "role": roles[part], "material": chosen[part],
                         "family": materials[chosen[part]]["family"],
                         "share": round(float((part_of == part).mean()), 4)} for part in used]}
    np.savez_compressed(run / take / "parts.npz", part_of=part_of, names=np.array([names[part] for part in used]),
                        parts=np.array(used), roles=np.array([roles[part] for part in used]),
                        materials=np.array([chosen[part] for part in used]),
                        colours=np.array([materials[chosen[part]]["colour"] for part in used]))
    (run / take / "parts.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=("questions", "regions", "parts"))
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("take")
    parser.add_argument("more", help="the prop route spec (data/characters/makes/<name>.json)")
    parser.add_argument("--outfit", default="work", choices=sorted(OUTFIT_PALETTES))
    options = parser.parse_args()
    spec = json.loads(pathlib.Path(options.more).read_text())
    if options.what == "questions":
        print(f"{len(questions(options.run, options.take, spec, options.outfit))} questions in {options.run / 'questions'}")
    elif options.what == "regions":
        print(f"{len(region_questions(options.run, options.take, spec, options.outfit))} questions in "
              f"{options.run / 'questions'}")
    else:
        record = parts(options.run, options.take, spec, options.outfit)
        print(json.dumps(record["parts"]))


if __name__ == "__main__":
    main()
