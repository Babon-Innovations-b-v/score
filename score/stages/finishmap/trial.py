"""The finish-map method's re-test on round 4's six models as stage rows (world grain), so the runner clears and runs
every paid step and nothing spends outside it. The method's own rows of the surface stage run here on the six takes;
round 4's paid turntable is read back, not rendered again.

    .venv/bin/python -m score.stages.finishmap.trial status|run      # the rows below, world-grain nodes
    .venv/bin/python -m score.stages.finishmap.trial why <node>

    fm-inputs     (free)  the six takes' rows (round 4's flat/takes.json) and the turntable's cameras for them
    fm-turntable  (free)  round 4's turntable renders of the close-up's camera and turntable_views.MAP_VIEWS, face maps
                          compressed as the surface stage's turntable row keeps them
    fm-lists, fm-maps, fm-names, fm-segvigen (paid), fm-parts (free): the surface stage's method rows (finish_rows.py,
                          segvigen_row.py, finish_parts.py), unchanged

fm-parts' parts.json holds the re-test's measures per take (agreement with each map on the faces its view sees, the
parts mixing two finishes, the parts) and its front and back pictures.
"""
import json
import os
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
SURFACES = REPO / "score/stages/surfaces"
for folder in (SURFACES, REPO / "tools/props", REPO / "tools/props/library", REPO / "tools/props/cloud"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))  # appended: the method modules must not shadow the framework's

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
ROUND = PROPS_HOME / "score-coordinator/refocus/surface"
WORK = PROPS_HOME / "work"
TAKES = ("hab_lander-r1", "power_unit-r3", "aft_section-r1", "chair-b", "desk_chair-lab1", "telephone-r6")


def model_files():
    """{name: pattern} of each take's close-up and raw model."""
    found = {}
    for take in TAKES:
        found[f"close-up {take}"] = "{work}/pixal/" + f"{take}.svviews"
        found[f"raw {take}"] = "{work}/pixal/" + f"{take}.glb"
    return found


FILES = {"takes": "{round}/work/flat/takes.json", "round job": "{round}/work/multiview/job.json",
         "round renders": "{round}/work/multiview/renders", "library": "{repo}/data/library", **model_files()}
NAMING = {**FILES, "places": "{repo}/data/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json"}


def wanted_views():
    import turntable_views as views
    return (views.FRONT, *views.MAP_VIEWS)


# --- fm-inputs, fm-turntable: round 4's, read back -----------------------------------------------------------------

def make_inputs(inputs, out, seed, params):
    """flat/takes.json and multiview/job.json of the six takes, only the views the method reads."""
    takes = json.loads(pathlib.Path(inputs["takes"]).read_text())
    (out / "flat").mkdir(parents=True)
    (out / "flat" / "takes.json").write_text(json.dumps({take: takes[take] for take in TAKES}, indent=1))
    job = json.loads(pathlib.Path(inputs["round job"]).read_text())
    kept = [dict(entry, views=[view for view in entry["views"] if view["name"] in wanted_views()])
            for entry in job["takes"] if entry["take"] in TAKES]
    (out / "multiview").mkdir()
    (out / "multiview" / "job.json").write_text(json.dumps(dict(job, takes=kept), indent=1))


def make_turntable(inputs, out, seed, params):
    """Round 4's renders of the six takes' wanted views; each face map compressed (<view>-id.npz)."""
    import numpy as np
    renders = pathlib.Path(inputs["round renders"])
    for take in TAKES:
        folder = out / "renders" / take
        folder.mkdir(parents=True)
        shutil.copy2(renders / take / "faces.npy", folder / "faces.npy")
        for view in wanted_views():
            for suffix in (".png", "-mr.png"):
                shutil.copy2(renders / take / f"{view}{suffix}", folder / f"{view}{suffix}")
            np.savez_compressed(folder / f"{view}-id.npz", ids=np.load(renders / take / f"{view}-id.npy"))


# --- the rows ------------------------------------------------------------------------------------------------------

def stages():
    from score import contracts, graph
    import finish_parts
    import finish_rows
    import segvigen_row
    import turntable_row
    from surface_gates import guarded

    def stage(name, make, faults, check, judge, after=(), files=FILES, **more):
        return graph.Stage(name, "world", make, contracts.Contract(name, 1, faults), (guarded(check, judge),),
                           files=files, after={row: (row, 1) for row in after}, **more)
    return (
        stage("fm-inputs", make_inputs, finish_parts.inputs_faults, "inputs", finish_parts.judge_inputs),
        stage("fm-turntable", make_turntable, turntable_row.turntable_faults, "turntable",
              turntable_row.judge_turntable, ("fm-inputs",)),
        stage("fm-lists", finish_rows.make_lists, finish_rows.lists_faults, "listed", finish_rows.judge_lists,
              ("fm-inputs",), NAMING, paid=True, euros=finish_rows.LIST_EUROS),
        stage("fm-maps", finish_rows.make_maps, finish_rows.maps_faults, "maps checked", finish_rows.judge_maps,
              ("fm-inputs", "fm-turntable", "fm-lists"), paid=True, euros=finish_rows.MAP_EUROS),
        stage("fm-names", finish_rows.make_names, finish_rows.names_faults, "named", finish_rows.judge_names,
              ("fm-inputs", "fm-maps"), NAMING, paid=True, euros=finish_rows.LIST_EUROS),
        stage("fm-segvigen", segvigen_row.make_segvigen, segvigen_row.segvigen_faults, "split back",
              segvigen_row.judge_segvigen, ("fm-maps",), {**FILES, **segvigen_row.FILES}, paid=True,
              euros=segvigen_row.SEGVIGEN_EUROS),
        stage("fm-parts", finish_parts.make_parts, finish_parts.parts_faults, "parts", finish_parts.judge_parts,
              ("fm-inputs", "fm-turntable", "fm-maps", "fm-names", "fm-segvigen"), NAMING))


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
