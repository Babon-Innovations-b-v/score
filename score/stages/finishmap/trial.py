"""EXPERIMENTAL: the finish-map test on round 4's six models (owner's approval of 2026-10-11, EUR 15 in all) as stage
rows, so the runner clears and runs every step, the paid ones included, and nothing spends outside it.

    .venv/bin/python -m score.stages.finishmap.trial status|run      # the rows below, world-grain nodes
    .venv/bin/python -m score.stages.finishmap.trial why <node>

    fm-lists     (paid)  Gemini 3.1 Pro's finish list of each close-up, each finish a library surface or a proposed
                         new one (ask.finish_list)
    fm-maps      (paid)  Nano Banana Pro's finish map of each close-up, checked by measurement and drawn once more
                         when it fails (ask.draw_map, maps.check); a take whose two maps fail gets none
    fm-segvigen  (paid)  SegviGen guided by each finish map on a rented card (tools/props/cloud/meshparts.py)
    fm-arms      (free)  the maps laid on the raw models, three arms (lay.py), each take's faces.npz and labels.json

The arms are measured beside round 4's today and g-texture by round 4's own measures (score/stages/surfaces/measure.py,
on the surface-first branch), outside these rows: measuring spends nothing.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS = REPO / "tools/props"
for folder in (HERE, PROPS, PROPS / "library", PROPS / "cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
ROUND = PROPS_HOME / "score-coordinator/refocus/surface"
WORK = PROPS_HOME / "work"
TAKES = ("hab_lander-r1", "power_unit-r3", "aft_section-r1", "chair-b", "desk_chair-lab1", "telephone-r6")
# Estimates, rounded up: six lists at about EUR 0.03 each; up to twelve 2K maps at $0.134; one or two L4 cards for
# SegviGen's 15 min set-up and about 6 min a take (meshparts.py's guesses).
LIST_EUROS, MAP_EUROS, SEGVIGEN_EUROS = 0.5, 2.0, 3.0
SEEDS = (1, 2)
MEMORY_CAP = "MemoryMax=16G"  # every local step on a raw model (tools/props/library overlay)


def model_files():
    """{name: pattern} of each take's close-up, camera and raw model."""
    found = {}
    for take in TAKES:
        found[f"close-up {take}"] = "{work}/pixal/" + f"{take}.svviews"
        found[f"raw {take}"] = "{work}/pixal/" + f"{take}.glb"
    return found


FILES = {"takes": "{round}/work/flat/takes.json", "library": "{repo}/data/library", **model_files()}


def entry_of(inputs, take):
    return json.loads(pathlib.Path(inputs["takes"]).read_text())[take]


def surfaces_of(entry):
    """The take's allowed library surfaces (the same list round 4's judge chose from)."""
    import labels
    return labels.allowed_materials(entry["library_places"][0], entry["kind"], [])


def close_up(inputs, take):
    from PIL import Image
    return Image.open(pathlib.Path(inputs[f"close-up {take}"]) / "input.png").convert("RGBA")


# --- fm-lists ------------------------------------------------------------------------------------------------------

def make_lists(inputs, out, seed, params):
    """Each take's finish list as <out>/<take>.json."""
    import ask
    for take in TAKES:
        entry = entry_of(inputs, take)
        finishes = ask.finish_list(close_up(inputs, take), entry["object"], surfaces_of(entry))
        (out / f"{take}.json").write_text(json.dumps({"take": take, "finishes": finishes}, indent=1))


def lists_faults(folder):
    return [f"no list for {take}" for take in TAKES if not (folder / f"{take}.json").exists()]


def judge_lists(output, inputs, evidence):
    """Pass when every take has one to eight finishes; the proposed new surfaces as findings."""
    from score import checks
    counts = {take: len(json.loads((output / f"{take}.json").read_text())["finishes"]) for take in TAKES}
    proposed = tuple(f"{take}: {entry['new_surface']}" for take in TAKES
                     for entry in json.loads((output / f"{take}.json").read_text())["finishes"]
                     if not entry["fits"] and entry.get("new_surface"))
    good = all(1 <= count <= 8 for count in counts.values())
    return checks.Verdict("listed", checks.PASS if good else checks.FAIL,
                          f"finishes per take {counts}; {len(proposed)} new surfaces proposed", counts, {}, proposed)


# --- fm-maps -------------------------------------------------------------------------------------------------------

def make_maps(inputs, out, seed, params):
    """Each take's map drawn (a second seed when the first fails its check) into <out>/<take>/: map-<seed>.png, the
    laid labels of the passing one (labels.npy, laid.png) and map.json with every attempt's measures."""
    import numpy as np
    import ask
    import maps
    lists = pathlib.Path(inputs["fm-lists"])
    for take in TAKES:
        finishes = json.loads((lists / f"{take}.json").read_text())["finishes"]
        picture = close_up(inputs, take)
        alpha = maps.alpha_of(picture)
        folder = out / take
        folder.mkdir()
        attempts, kept = [], None
        for map_seed in SEEDS:
            drawn = ask.draw_map(picture, finishes, map_seed)
            if drawn is None:
                attempts.append({"seed": map_seed, "passes": False, "why": "no picture in the answer"})
                continue
            drawn.save(folder / f"map-{map_seed}.png")
            measures, per_pixel = maps.check(drawn, alpha, len(finishes), ask.LABELS)
            attempts.append({"seed": map_seed, **measures})
            if measures["passes"]:
                kept = per_pixel
                break
        if kept is not None:
            np.save(folder / "labels.npy", kept.astype(np.int8))
            maps.label_picture(kept, ask.LABELS[:len(finishes)]).save(folder / "laid.png")
        (folder / "map.json").write_text(json.dumps({"take": take, "finishes": finishes, "attempts": attempts,
                                                     "passes": kept is not None}, indent=1))


def maps_faults(folder):
    return [f"no map.json for {take}" for take in TAKES if not (folder / take / "map.json").exists()]


def passed_takes(maps_folder):
    return [take for take in TAKES if json.loads((maps_folder / take / "map.json").read_text())["passes"]]


def judge_maps(output, inputs, evidence):
    """Pass when every take's maps were drawn and measured and at least one take has a passing map; the takes whose
    maps both failed as findings (they get no arm, so they fail against today)."""
    from score import checks
    passed = passed_takes(output)
    failed = tuple(f"{take}: {json.loads((output / take / 'map.json').read_text())['attempts']}" for take in TAKES
                   if take not in passed)
    return checks.Verdict("maps checked", checks.PASS if passed else checks.FAIL,
                          f"{len(passed)} of {len(TAKES)} takes have a finish map that passed its check",
                          {"passed": len(passed)}, {"passed": "higher"}, failed)


# --- fm-segvigen ---------------------------------------------------------------------------------------------------

def make_segvigen(inputs, out, seed, params):
    """SegviGen guided by each passing finish map (in its own part colours) on a rented card, each raw model turned
    half round so SegviGen's camera sees its close-up side (lay.turned); each take's down/ kept (its uploads removed
    after)."""
    import numpy as np
    import trimesh
    import labels
    import split_compare
    maps_folder = pathlib.Path(inputs["fm-maps"])
    takes = passed_takes(maps_folder)
    turn = np.eye(4)
    turn[:3, :3] = labels.VIEW_TURN
    for take in takes:
        up = out / take / "up"
        up.mkdir(parents=True)
        scene = trimesh.load(inputs[f"raw {take}"], force="scene")
        for geometry in scene.geometry.values():  # into the vertices, not a node: every reader then sees it turned
            geometry.apply_transform(turn)
        scene.export(up / "raw.glb")
        split_compare.guide_map(np.load(maps_folder / take / "labels.npy").astype(int)).save(up / "map.png")
    command = [sys.executable, str(PROPS / "cloud/meshparts.py"), str(out), "--who", "finishmap trial",
               "--methods", "segvigen", "--takes", ",".join(takes)]
    done = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    (out / "meshparts.log").write_text(done.stdout + done.stderr)
    for take in takes:
        shutil.rmtree(out / take / "up")
    if done.returncode:
        raise RuntimeError(f"meshparts.py failed: {done.stderr[-2000:]}")


def segvigen_faults(folder):
    return [] if (folder / "meshparts.log").exists() else ["no meshparts.log"]


def judge_segvigen(output, inputs, evidence):
    """Pass when every take with a passing map came back with SegviGen's guided split."""
    from score import checks
    takes = passed_takes(pathlib.Path(inputs["fm-maps"]))
    missing = tuple(take for take in takes if not (output / take / "down" / "segvigen_guided.npz").exists())
    return checks.Verdict("split back", checks.FAIL if missing else checks.PASS,
                          f"{len(takes) - len(missing)} of {len(takes)} guided splits back",
                          {"missing": len(missing)}, {"missing": "lower"}, missing)


# --- fm-arms -------------------------------------------------------------------------------------------------------

def make_arms(inputs, out, seed, params):
    """lay.py on every take with a passing map, under the memory cap."""
    takes = passed_takes(pathlib.Path(inputs["fm-maps"]))
    command = ["systemd-run", "--user", "--scope", "-q", "-p", MEMORY_CAP, sys.executable, str(HERE / "lay.py"),
               inputs["fm-maps"], inputs["fm-segvigen"], str(out), *takes]
    done = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
    (out / "lay.log").write_text(done.stdout + done.stderr)
    if done.returncode:
        raise RuntimeError(f"lay.py failed: {done.stderr[-2000:]}")


def arms_faults(folder):
    return [] if (folder / "lay.log").exists() else ["no lay.log"]


def judge_arms(output, inputs, evidence):
    """Pass when every take with a passing map has every arm's faces.npz."""
    from score import checks
    import lay
    takes = passed_takes(pathlib.Path(inputs["fm-maps"]))
    missing = tuple(f"{arm}/{take}" for arm in lay.ARMS for take in takes
                    if not (output / arm / take / "faces.npz").exists())
    return checks.Verdict("laid", checks.FAIL if missing else checks.PASS,
                          f"{len(takes) * len(lay.ARMS) - len(missing)} of {len(takes) * len(lay.ARMS)} arms laid",
                          {"missing": len(missing)}, {"missing": "lower"}, missing)


# --- the rows ------------------------------------------------------------------------------------------------------

def stages():
    from score import checks, contracts, graph
    code = {"lay": str(HERE / "lay.py")}  # run as a program, so the code version does not reach it: declared
    return (
        graph.Stage("fm-lists", "world", make_lists, contracts.Contract("finish-lists", 1, lists_faults),
                    (checks.Check("listed", judge_lists),), files=FILES, paid=True, euros=LIST_EUROS),
        graph.Stage("fm-maps", "world", make_maps, contracts.Contract("finish-maps", 1, maps_faults),
                    (checks.Check("maps checked", judge_maps),), files=FILES,
                    after={"fm-lists": ("finish-lists", 1)}, paid=True, euros=MAP_EUROS),
        graph.Stage("fm-segvigen", "world", make_segvigen, contracts.Contract("finish-segvigen", 1, segvigen_faults),
                    (checks.Check("split back", judge_segvigen),),
                    files={**FILES, "meshparts": "{repo}/tools/props/cloud/meshparts.py",
                           "segvigen worker": "{repo}/tools/props/cloud/segvigen_worker.py"},
                    after={"fm-maps": ("finish-maps", 1)}, paid=True, euros=SEGVIGEN_EUROS),
        graph.Stage("fm-arms", "world", make_arms, contracts.Contract("finish-arms", 1, arms_faults),
                    (checks.Check("laid", judge_arms),), files={**FILES, **code},
                    after={"fm-maps": ("finish-maps", 1), "fm-segvigen": ("finish-segvigen", 1)}))


def runner():
    from score import graph
    from score.store import Store
    world = graph.World.from_file(REPO / "data/definitions/world.json", round=str(ROUND), work=str(WORK),
                                  repo=str(REPO))
    return graph.Runner(stages(), world, Store.default())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    sys.path.insert(0, str(REPO))
    if argv[:1] == ["why"]:
        print("\n".join(runner().why(argv[1])))
        return
    done = runner().run([]) if argv[:1] == ["run"] else runner().status([])
    for node, state in done.items():
        print(f"{node}: {state}")


if __name__ == "__main__":
    main()
