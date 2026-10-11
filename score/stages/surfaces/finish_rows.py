"""The finish-map method's paid Google rows (the surface stage's method; their asks in finish_ask.py, every one cached
by its input's hash, so a rerun of an unchanged ask is free), in a module of their own so a change to the free steps
does not ask again.

Rows (place grain, surfaces-<step>@<place>):
    lists   (paid)  Gemini 3.1 Pro's finish list of each close-up, each finish one of the take's library surfaces or
                    the closest with a proposed new one (finish_ask.finish_list)
    maps    (paid)  Nano Banana Pro's finish map of each close-up (finish_ask.draw_map), checked by measurement
                    (finish_maps): drawn up to len(SEEDS) times, the last more strictly, the best filled when only its
                    labelled share fell short; a take with none settled is named in the gate's fail and stops its
                    place's line (the owner may waive it: later rows then leave it out). Then a finish map of each
                    turntable view in turntable_views.MAP_VIEWS (sides and back), given the close-up and its settled
                    map as the reference, so each finish keeps its label colour; a view whose map does not settle
                    gets none.
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

# Estimates (EUR), rounded up: a list about EUR 0.03 a take; a map $0.134, up to three of the close-up and two of each
# of three views a take, for a place of up to a dozen takes.
LIST_EUROS, MAP_EUROS = 0.5, 10.0
SEEDS = (1, 2, 3)  # the close-up's draws, the last asked more strictly (finish_ask.STRICT)
VIEW_SEEDS = (1, 2)


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

def make_lists(inputs, out, seed, params):
    """Each take's finish list as <out>/<take>.json."""
    import finish_ask
    inputs = prop_env.short(inputs)
    for take, entry in takes_of(inputs).items():
        finishes = finish_ask.finish_list(close_up(inputs, take), entry["object"], surfaces_of(entry))
        (out / f"{take}.json").write_text(json.dumps({"take": take, "finishes": finishes}, indent=1))


def lists_faults(folder):
    return [] if list(folder.glob("*.json")) else ["no finish list"]


def judge_lists(output, inputs, evidence):
    """Every take has one to eight finishes; the proposed new library surfaces as a measure."""
    takes = takes_of(prop_env.short(inputs))
    found = {take: json.loads((output / f"{take}.json").read_text())["finishes"] for take in takes
             if (output / f"{take}.json").exists()}
    failing = [f"{take}: no finish list" for take in takes if take not in found]
    failing += [f"{take}: {len(finishes)} finishes" for take, finishes in found.items()
                if not 1 <= len(finishes) <= 8]
    proposed = sum(1 for finishes in found.values() for entry in finishes if not entry["fits"])
    return gates.verdict("listed", failing, len(takes), "takes without a usable finish list",
                         {"proposed surfaces": proposed})


# --- maps ----------------------------------------------------------------------------------------------------------

def drawn_attempts(draw, seeds, alpha, listed, every_label, folder, name):
    """Each seed's draw checked (finish_maps.check), the pictures kept as <name>-<seed>.png; (records, attempts,
    seeds of the attempts) with a record for every seed, a draw that held no picture too."""
    import finish_ask
    import finish_maps
    records, attempts, kept_seeds = [], [], []
    for number, map_seed in enumerate(seeds):
        picture = draw(map_seed, number == len(seeds) - 1)
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


def settled_map(draw, seeds, alpha, listed, every_label, folder, name):
    """A picture's draws settled (finish_maps.settled): its record, and <name>.npy and <name>.png when one settled."""
    import numpy as np
    import finish_ask
    import finish_maps
    records, attempts, kept_seeds = drawn_attempts(draw, seeds, alpha, listed, every_label, folder, name)
    settled = finish_maps.settled(attempts, alpha, every_label)
    record = {"attempts": records, "passes": settled is not None}
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


def take_maps(inputs, take, finishes, folder):
    """One take's maps: the close-up's, then each view's against it; its map.json record."""
    from PIL import Image
    import finish_ask
    import finish_maps
    import turntable_views as views
    picture = close_up(inputs, take)
    listed = len(finishes)
    front = settled_map(lambda map_seed, last: finish_ask.draw_map(picture, finishes, map_seed, strict=last), SEEDS,
                        finish_maps.alpha_of(picture), listed, True, folder, "front")
    record = {"take": take, "finishes": finishes, "front": front, "views": {}, "passes": front["passes"]}
    if front["passes"]:
        reference = Image.open(folder / "front.png")
        for view in views.MAP_VIEWS:
            shown = Image.open(inputs["turntable"] / "renders" / take / f"{view}.png").convert("RGBA")
            record["views"][view] = settled_map(
                lambda map_seed, last: finish_ask.draw_view_map(picture, reference, shown, finishes, map_seed),
                VIEW_SEEDS, view_alpha(inputs, take, view), listed, False, folder, view)
    (folder / "map.json").write_text(json.dumps(record, indent=1))


def make_maps(inputs, out, seed, params):
    """Every take's maps into <out>/<take>/ (take_maps)."""
    inputs = prop_env.short(inputs)
    for take in takes_of(inputs):
        finishes = json.loads((inputs["lists"] / f"{take}.json").read_text())["finishes"]
        (out / take).mkdir()
        take_maps(inputs, take, finishes, out / take)


def maps_faults(folder):
    return [] if list(folder.glob("*/map.json")) else ["no map.json"]


def map_fault(record):
    """Why a take's close-up map failed, its draws' measures in short."""
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
