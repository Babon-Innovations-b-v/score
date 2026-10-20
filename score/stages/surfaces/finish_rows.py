"""The finish-map method's Google rows (the surface stage's method; their asks in finish_ask.py, every one cached by
its input's hash, so a rerun of an unchanged ask is free), in a module of their own so a change to the free steps
does not ask again.

Every paid ask runs once (the batch rule, #21): one finish list a take, one draw of each map, no paid naming. What
does not come back or does not settle is a hole, named in its row's gate; new spend on it is a new batch. The risk
work is free and comes first: the close-up's measured colours and the library surfaces near them go into the list
ask (close_up_regions), a piece with a declared surface asks nothing (declared_list), and the names are decided by
rule from the close-up's colours (named_by_rule).

Rows (place grain, surfaces-<step>@<place>):
    lists   (paid)  Gemini 3.1 Pro's finish list of each close-up, each finish one of the take's library surfaces or
                    the closest with a proposed new one (finish_ask.finish_list, on the flex tier); a kit or shell
                    piece whose surfaces data names its `surface` takes that one finish, asked of nobody
    maps    (paid)  Nano Banana Pro's finish map of each close-up (finish_ask.draw_map), drawn once (SEEDS) and asked
                    strictly, checked by measurement (finish_maps): filled when only its labelled share fell short,
                    else split by the close-up's own colours (finish_maps.colour_split, free); a take with none
                    settled is named in the gate's fail and stops its place's line (the owner may waive it: later
                    rows then leave it out). Then a finish map of each turntable view in turntable_views.MAP_VIEWS
                    (sides and back), drawn once (VIEW_SEEDS), given the close-up and its settled map as the
                    reference, so each finish keeps its label colour; a view whose map does not settle gets none. A
                    one-finish take is not drawn: its map is the close-up's object mask (one_finish_map).
    names   (free)  each finish's surface decided by rule (named_by_rule): lamp light by its colour's chroma, a
                    finish whose words name another material the nearest surface of that material by colour, else a
                    hole; the paint's colour and order check (finish_parts.checked_finishes) run ahead as a
                    prediction.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
for folder in (HERE, REPO / "tools/props", REPO / "tools/props/library", REPO / "tools/props/cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import prop_env  # noqa: E402

import surface_gates as gates  # noqa: E402

# A finish whose words say it gives off light (GLOW_WORDS) and whose close-up colour lies over this chroma (CIELAB)
# takes the nearest light or screen surface by colour: the garage beacon's red light measured chroma 57, its metal
# housing named for it (2026-10-13).
GLOW_CHROMA = 40.0
GLOW_WORDS = ("lamp", "beacon", "indicator", "lens", "screen", "display", "glow", "glowing", "led", "lit",
              "illuminated", "emissive")
GLOW_FAMILIES = ("light", "screen")
# The close-up's colours given to the list ask: its object's Lab colours in REGION_COLOURS k-means groups, each over
# REGION_LEAST of the object, with at most NEAR_MOST library surfaces within finish_parts.COLOUR_DELTA_E of it.
REGION_COLOURS, REGION_LEAST, NEAR_MOST = 6, 0.05, 4
# Estimates (EUR), rounded up: a list about EUR 0.03 a take (half that on flex); a map $0.134, one of the close-up and
# one of each of three views a take, for a place of up to a dozen takes.
LIST_EUROS, MAP_EUROS = 0.5, 7.0
SEEDS = (1,)  # the close-up's one draw, asked strictly (finish_ask.STRICT)
VIEW_SEEDS = (1,)
# What an ask that got no usable answer raises: a timeout or dropped connection (OSError), an answer that does not
# parse (ValueError, KeyError). Each makes its take or draw a hole, never an ask again.
UNANSWERED = (OSError, ValueError, KeyError)


def takes_of(inputs):
    return json.loads((inputs["inputs"] / "flat" / "takes.json").read_text())


def close_up(inputs, take):
    from PIL import Image
    return Image.open(pathlib.Path(inputs[f"close-up {take}"]) / "input.png").convert("RGBA")


def surfaces_of(entry):
    """The take's allowed library surfaces."""
    import labels
    return labels.allowed_materials(entry["library_places"][0], entry["kind"], [])


# --- lists ---------------------------------------------------------------------------------------------------------

def close_up_regions(picture, surfaces):
    """The close-up's main colours, measured free before the list ask: its object's Lab colours (labels.picture_lab)
    in REGION_COLOURS k-means groups, each over REGION_LEAST of the object as [share, median L*a*b*, the surfaces
    within COLOUR_DELTA_E of it, nearest first, at most NEAR_MOST], largest first; finish_ask.region_lines' form."""
    import numpy as np
    from scipy.cluster.vq import kmeans2
    import finish_maps
    import finish_parts
    import labels
    alpha = finish_maps.alpha_of(picture)
    lab = labels.picture_lab(picture.convert("RGB"))[alpha]
    found = {"within": finish_parts.COLOUR_DELTA_E, "regions": []}
    if len(lab) < REGION_COLOURS:
        return found
    _, colour_of = kmeans2(lab, REGION_COLOURS, seed=0, minit="++")
    library = {name: finish_parts.library_lab(spec) for name, spec in surfaces.items() if "colour" in spec}
    for colour in range(REGION_COLOURS):
        pixels = lab[colour_of == colour]
        if len(pixels) < REGION_LEAST * len(lab):
            continue
        middle = np.median(pixels, axis=0)
        near = sorted((float(np.linalg.norm(value - middle)), name) for name, value in library.items())
        found["regions"].append([round(len(pixels) / len(lab), 3), [round(float(value), 1) for value in middle],
                                 [name for apart, name in near if apart <= finish_parts.COLOUR_DELTA_E][:NEAR_MOST]])
    found["regions"].sort(key=lambda region: -region[0])
    return found


def declared_list(take, entry, surfaces):
    """A kit or shell piece's list, asked of nobody: the one library surface its place's surfaces data names for it
    (`surface`: its shell section's or kit's finish) on all of it; a hole when the take may not take that surface."""
    if entry["surface"] not in surfaces:
        return {"take": take, "finishes": [], "hole": f"its declared surface {entry['surface']} is not one it may take"}
    return {"take": take, "finishes": [{"parts": "all of it", "finish": entry["surface"].replace("_", " "),
                                        "surface": entry["surface"], "fits": True, "by": "its declared surface"}]}


def take_list(inputs, take, entry):
    """One take's list record: declared (declared_list), else asked once with its close-up's colours; an ask with no
    usable answer leaves the take a hole, its reason in the record."""
    import finish_ask
    surfaces = surfaces_of(entry)
    if "surface" in entry:
        return declared_list(take, entry, surfaces)
    picture = close_up(inputs, take)
    try:
        finishes = finish_ask.finish_list(picture, entry["object"], surfaces, close_up_regions(picture, surfaces))
    except UNANSWERED as error:
        return {"take": take, "finishes": [], "hole": f"no usable finish list: {error!r}"[:300]}
    return {"take": take, "finishes": finishes}


def make_lists(inputs, out, seed, params):
    """Each take's finish list as <out>/<take>.json (take_list)."""
    inputs = prop_env.short(inputs)
    for take, entry in takes_of(inputs).items():
        (out / f"{take}.json").write_text(json.dumps(take_list(inputs, take, entry), indent=1))


def lists_faults(folder):
    return [] if list(folder.glob("*.json")) else ["no finish list"]


def judge_lists(output, inputs, evidence):
    """Every take has one to eight finishes; a hole is named with its reason. The proposed new library surfaces and
    the declared pieces as measures."""
    takes = takes_of(prop_env.short(inputs))
    found = {take: json.loads((output / f"{take}.json").read_text()) for take in takes
             if (output / f"{take}.json").exists()}
    failing = [f"{take}: no finish list" for take in takes if take not in found]
    failing += [f"{take}: " + (record.get("hole") or f"{len(record['finishes'])} finishes")
                for take, record in found.items() if not 1 <= len(record["finishes"]) <= 8]
    finishes = [entry for record in found.values() for entry in record["finishes"]]
    return gates.verdict("listed", failing, len(takes), "takes without a usable finish list",
                         {"proposed surfaces": sum(1 for entry in finishes if not entry["fits"]),
                          "declared": sum(entry.get("by") == "its declared surface" for entry in finishes)})


# --- maps ----------------------------------------------------------------------------------------------------------

def drawn_attempts(draw, seeds, alpha, listed, every_label, folder, name):
    """Each seed's draw checked (finish_maps.check), the pictures kept as <name>-<seed>.png; (records, attempts,
    seeds of the attempts) with a record for every seed, a draw that held no picture or got no answer too."""
    import finish_ask
    import finish_maps
    records, attempts, kept_seeds = [], [], []
    for map_seed in seeds:
        try:
            picture = draw(map_seed)
        except UNANSWERED as error:
            records.append({"seed": map_seed, "passes": False, "why": f"no answer: {error!r}"[:300]})
            continue
        if picture is None:
            records.append({"seed": map_seed, "passes": False, "why": "no picture in the answer"})
            continue
        picture.save(folder / f"{name}-{map_seed}.png")
        measures, per_pixel = finish_maps.check(picture, alpha, listed, finish_ask.LABELS, every_label)
        records.append({"seed": map_seed, **measures})
        attempts.append((measures, per_pixel))
        kept_seeds.append(map_seed)
        if measures["passes"]:
            break
    return records, attempts, kept_seeds


def settled_map(draw, seeds, alpha, listed, every_label, folder, name, split=None):
    """A picture's draws settled (finish_maps.settled): its record, and <name>.npy and <name>.png when one settled.
    With `split` (the close-up) and no draw settled, the close-up's colours split it and the draws name the regions
    (finish_maps.colour_split)."""
    import numpy as np
    import finish_ask
    import finish_maps
    records, attempts, kept_seeds = drawn_attempts(draw, seeds, alpha, listed, every_label, folder, name)
    settled = finish_maps.settled(attempts, alpha, every_label)
    record = {"attempts": records, "passes": settled is not None}
    if settled is None and split is not None and attempts:
        per_pixel = finish_maps.colour_split(split, alpha, attempts)
        used = np.bincount(per_pixel[alpha & (per_pixel >= 0)], minlength=listed) / max(alpha.sum(), 1)
        if int((used >= finish_maps.USED_LEAST).sum()) == listed:
            record.update(passes=True, by="the close-up's colours split it, the draws named the regions")
            np.save(folder / f"{name}.npy", per_pixel.astype(np.int8))
            finish_maps.label_picture(per_pixel, finish_ask.LABELS[:listed]).save(folder / f"{name}.png")
    if settled is not None:
        index, per_pixel, was_filled = settled
        record.update(kept=kept_seeds[index], filled=was_filled,
                      filled_share=round(float(attempts[index][0]["near_label"]), 3) if was_filled else None)
        np.save(folder / f"{name}.npy", per_pixel.astype(np.int8))
        finish_maps.label_picture(per_pixel, finish_ask.LABELS[:listed]).save(folder / f"{name}.png")
    return record


def view_alpha(inputs, take, view):
    import numpy as np
    return np.load(inputs["turntable"] / "renders" / take / f"{view}-id.npz")["ids"] >= 0


def one_finish_map(alpha, folder):
    """A one-finish take's close-up map: its only finish on every pixel of the close-up's object (alpha), none drawn.
    With one finish the map holds nothing but the object's outline, which the alpha gives exactly; asked to paint it
    one colour, the picture model tinted the photo instead (the wreck's tank dome and pressure sphere, old_station's
    bag stack: 10 to 53% of the object near the label on every draw, 2026-10-12)."""
    import numpy as np
    import finish_ask
    import finish_maps
    per_pixel = np.where(alpha, 0, -1)
    np.save(folder / "front.npy", per_pixel.astype(np.int8))
    finish_maps.label_picture(per_pixel, finish_ask.LABELS[:1]).save(folder / "front.png")
    return {"attempts": [], "passes": True, "by": "one finish: the close-up's object mask"}


def take_maps(inputs, take, finishes, folder):
    """One take's maps: the close-up's, then each view's against it (a one-finish take: its mask, no views; every
    face it has takes that finish); its map.json record."""
    from PIL import Image
    import finish_ask
    import finish_maps
    import turntable_views as views
    picture = close_up(inputs, take)
    listed = len(finishes)
    alpha = finish_maps.alpha_of(picture)
    if listed == 1:
        front = one_finish_map(alpha, folder)
    else:
        front = settled_map(lambda map_seed: finish_ask.draw_map(picture, finishes, map_seed),
                            SEEDS, alpha, listed, True, folder, "front", split=picture)
    record = {"take": take, "finishes": finishes, "front": front, "views": {}, "passes": front["passes"]}
    if front["passes"] and listed > 1:
        reference = Image.open(folder / "front.png")
        for view in views.MAP_VIEWS:
            shown = Image.open(inputs["turntable"] / "renders" / take / f"{view}.png").convert("RGBA")
            record["views"][view] = settled_map(
                lambda map_seed: finish_ask.draw_view_map(picture, reference, shown, finishes, map_seed),
                VIEW_SEEDS, view_alpha(inputs, take, view), listed, False, folder, view)
    (folder / "map.json").write_text(json.dumps(record, indent=1))


def hole_map(take, folder, why):
    """The map.json of a take with no finish list (a hole in the lists row): nothing drawn, it does not pass."""
    front = {"attempts": [], "passes": False, "why": why}
    (folder / "map.json").write_text(json.dumps({"take": take, "finishes": [], "front": front, "views": {},
                                                 "passes": False}, indent=1))


def make_maps(inputs, out, seed, params):
    """Every take's maps into <out>/<take>/ (take_maps); a take its list left a hole is not drawn (hole_map)."""
    inputs = prop_env.short(inputs)
    for take in takes_of(inputs):
        finishes = json.loads((inputs["lists"] / f"{take}.json").read_text())["finishes"]
        (out / take).mkdir()
        if finishes:
            take_maps(inputs, take, finishes, out / take)
        else:
            hole_map(take, out / take, "no finish list (a hole in the lists row)")


def maps_faults(folder):
    return [] if list(folder.glob("*/map.json")) else ["no map.json"]


# --- names ---------------------------------------------------------------------------------------------------------

def glowing(words, colour, spec):
    """True for a finish whose words say it gives off light (GLOW_WORDS), whose close-up colour lies over GLOW_CHROMA
    and whose surface is not already light or a screen."""
    import re
    import numpy as np
    return (colour is not None and float(np.hypot(colour[1], colour[2])) > GLOW_CHROMA
            and spec.get("family") not in GLOW_FAMILIES
            and any(re.search(rf"\b{word}\b", words.lower()) for word in GLOW_WORDS))


def nearest_surface(colour, every, takes_family, within):
    """The name of the surface nearest `colour` (CIE76) among `every`'s with a colour whose family `takes_family`
    allows, within `within` (None: any distance); None when there is none."""
    import numpy as np
    import finish_parts
    fits = sorted((float(np.linalg.norm(finish_parts.library_lab(spec) - colour)), name)
                  for name, spec in every.items() if "colour" in spec and takes_family(spec.get("family")))
    return fits[0][1] if fits and (within is None or fits[0][0] <= within) else None


def named_by_rule(finish, colour, every):
    """One finish's surface decided free, with no ask: lamp light (glowing) takes the nearest light or screen surface
    by colour; a finish whose words name a material its surface's family is not (finish_parts.contradicts: black
    rubber as bare_steel) takes the nearest surface by colour, within COLOUR_DELTA_E, of a family its words allow,
    else stays a hole. (its record, the hole's reason or None)."""
    import finish_parts
    words = f"{finish['finish']} {finish['parts']}"
    spec = every.get(finish["surface"], {})
    record = dict(finish, listed_surface=finish["surface"], by=finish.get("by", "the list"))
    if glowing(words, colour, spec):
        light = nearest_surface(colour, every, lambda family: family in GLOW_FAMILIES, None)
        if light is not None:
            return dict(record, surface=light, by="lamp light by its colour"), None
    if not finish_parts.contradicts(words, spec.get("family")):
        return record, None
    allowed = None if colour is None else nearest_surface(
        colour, every, lambda family: family in finish_parts.FAMILY_CLASSES and not finish_parts.contradicts(
            words, family), finish_parts.COLOUR_DELTA_E)
    if allowed is None:
        return dict(record, by="off its material", fits=False), (
            f"{finish['finish']}: its words name a material {finish['surface']} is not, and no surface of that "
            f"material lies within dE {finish_parts.COLOUR_DELTA_E:.0f} of its close-up colour")
    return dict(record, surface=allowed, by="its words' material by colour"), None


def take_names(inputs, take, entry, record):
    """One take's names record: each finish named by rule (named_by_rule) from its colour in the close-up's map, its
    holes, and the finishes the paint's colour and order check (finish_parts.checked_finishes) will fail, predicted."""
    import numpy as np
    import finish_parts
    every = finish_parts.take_surfaces(entry)
    front = np.load(inputs["maps"] / take / "front.npy").astype(int)
    measured = finish_parts.measured_colours(take, front, [every.get(finish["surface"])
                                                           for finish in record["finishes"]])
    found, holes = [], []
    for finish, colour in zip(record["finishes"], measured):
        named, hole = named_by_rule(finish, colour, every)
        found.append(named)
        holes += [hole] if hole else []
    predicted = finish_parts.checked_finishes(entry, found, measured)
    return {"take": take, "finishes": found, "holes": holes,
            "predicted_off": [finish["finish"] for finish in predicted if finish.get("by") == "off its colour"]}


def make_names(inputs, out, seed, params):
    """Each take whose close-up map settled, its finishes named by rule (take_names), as <out>/<take>.json. Free."""
    inputs = prop_env.short(inputs)
    for take, entry in takes_of(inputs).items():
        path = inputs["maps"] / take / "map.json"
        record = json.loads(path.read_text())
        if record["passes"]:
            (out / f"{take}.json").write_text(json.dumps(take_names(inputs, take, entry, record), indent=1))


def names_faults(folder):
    return [] if list(folder.glob("*.json")) else ["no names"]


def judge_names(output, inputs, evidence):
    """Every take whose close-up map settled has its finishes named, and none is a hole (a finish whose words name a
    material no surface near its colour is). The ones named by rule, and the finishes the paint's gate is predicted
    to fail by colour or order, as measures."""
    short = prop_env.short(inputs)
    takes = [take for take in takes_of(short)
             if json.loads((short["maps"] / take / "map.json").read_text())["passes"]]
    failing = [f"{take}: not named" for take in takes if not (output / f"{take}.json").exists()]
    records = [json.loads((output / f"{take}.json").read_text()) for take in takes
               if (output / f"{take}.json").exists()]
    failing += [f"{record['take']}: {hole}" for record in records for hole in record.get("holes", [])]
    by_rule = sum(finish["by"] not in ("the list", "its declared surface", "off its material")
                  for record in records for finish in record["finishes"])
    return gates.verdict("named", failing, len(takes), "takes",
                         {"named by rule": by_rule,
                          "predicted off colour": sum(len(record.get("predicted_off", [])) for record in records)})


def map_fault(record):
    """Why a take's close-up map failed: its hole's reason, else its draws' measures in short."""
    if record["front"].get("why"):
        return f"{record['take']}: {record['front']['why']}"
    tried = ", ".join(f"seed {entry['seed']}: " + (entry.get("why") or f"iou {entry['iou']}, near a label "
                                                   f"{entry['near_label']}, {entry['labels_used']} of "
                                                   f"{entry['labels_listed']} finishes")
                      for entry in record["front"]["attempts"])
    return f"{record['take']}: no finish map settled ({tried})"


def judge_maps(output, inputs, evidence):
    """Every take's close-up map settled; a take with none is named and blocks (it is never painted from a map that
    failed). The views' maps as measures."""
    takes = takes_of(prop_env.short(inputs))
    records = {take: json.loads((output / take / "map.json").read_text()) for take in takes
               if (output / take / "map.json").exists()}
    failing = [f"{take}: no map.json" for take in takes if take not in records]
    failing += [map_fault(record) for record in records.values() if not record["passes"]]
    views = [view for record in records.values() for view in record["views"].values()]
    return gates.verdict("maps checked", failing, len(takes), "takes without a finish map",
                         {"views drawn": sum(view["passes"] for view in views), "views asked": len(views),
                          "filled": sum(bool(record["front"].get("filled")) for record in records.values())})
