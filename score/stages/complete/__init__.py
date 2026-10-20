"""The complete stage (P11): a place's manifest, made from the store and never from file times, and the completion
gate on what the place holds.

The runner makes it only once every stage before it passed its gates and stands accepted, so its manifest names, for
each of them, the accepted output it read (an earlier stage's input is a checkout named by its output's hash). Its
gates:

    manifest      the manifest names the output read for every stage it reads
    the rest      tools/usd/complete.py's checks, the same code that gate runs on a work stage (one gate, two ways
                  in), on the place's assembled stage: its neighbours output where the place shows others, else its
                  assembly. Rows, made-only, placeholders, picks, boxes, and the contents checks (tools/usd/contents.py:
                  people, effects, motion, crops, likeness, painted, light, sound, neighbours, game), the contents
                  reading the accepted likeness and surfaces-check outputs it reads (and the characters layer's, once
                  the cast stage's characters-layer row is in the table and in `after`: until then the people check
                  judges the seed's bodies); reach (experimental) passes once recorded, its faults shown. Resting is
                  the assembly's gate, judged there on its drop run.
"""
import json
import pathlib
import sys

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on the path by the assembly stage's import: no new folder
import complete  # noqa: E402
import contents  # noqa: E402

READS = ("assembly", "neighbours", "surfaces-check", "likeness")
GATE = tuple(check for check in complete.CHECKS if check != "resting")
# The world folders the checks read (complete.py and contents.py read them from the repository's data, the same
# folders for world 1), declared so a change to any reruns the gate.
FILES = {"inventories": "{data}/inventory", "kits": "{data}/kit", "casts": "{data}/characters",
         "effects": "{data}/effects", "motions": "{data}/motion", "scenes": "{data}/scene",
         "sound table": "{data}/sound/places.json", "expected contents": "{data}/checks/contents.json",
         "full looks": "{data}/people/bodies.json"}


def files(place):
    """The world folders, the place's rigid record when it has one, and the built body's report of every body the
    place's cast draws."""
    moves = {"moves": "{data}/motion/rigid/{place}.json"} if contents.record("motion/rigid", place) else {}
    cast = contents.record("characters", place) or {}
    bodies = {person["character"] for person in cast.get("people", [])}
    bodies |= {cast["crowd"]["character"]} if cast.get("crowd") else set()
    bodies |= {path.stem for path in contents.BODIES.glob("kit_*.json")} if cast.get("groups") else set()  # dealt mixes
    reports = {f"body {body}": str(contents.BODIES / f"{body}.json") for body in sorted(bodies)
               if (contents.BODIES / f"{body}.json").exists()}  # a missing one the people check fails by name
    return {**FILES, **moves, **reports}


def make_manifest(inputs, out, seed, params):
    """Write the manifest: each earlier stage with the accepted output read."""
    (out / "manifest.json").write_text(json.dumps({"stages": {name: pathlib.Path(inputs[name]).name for name in READS
                                                              if name in inputs}}, indent=1))


def judge_manifest(output, inputs, evidence):
    """Pass when the manifest names the output read for every stage before it."""
    named = json.loads((output / "manifest.json").read_text())["stages"]
    missing = sorted(name for name in READS if name in inputs and named.get(name) != pathlib.Path(inputs[name]).name)
    if missing:
        return checks.Verdict("manifest", checks.FAIL, f"the manifest lacks {', '.join(missing)}",
                              {"missing": len(missing)}, {"missing": "lower"})
    return checks.Verdict("manifest", checks.PASS, f"every stage before it passed and was accepted: {', '.join(named)}")


def assembled_stage(inputs):
    """The place's assembled stage: its neighbours output when it shows other places, else its assembly."""
    from score.stages.assembly import stage_file
    return stage_file(pathlib.Path(inputs.get("neighbours") or inputs["assembly"]))


def gate_check(name):
    """complete.py's check `name` as this stage's gate, on the assembled stage."""
    def judge(output, inputs, evidence):
        stage = assembled_stage(inputs)
        read = {**{read: inputs.get(read) for read in contents.OUTPUTS},
                **{node: path for node, path in inputs.items() if node.startswith(contents.LIKENESS_BESIDE)}}
        found = complete.run_check(name, stage.stem, stage, read)
        answer, why = found["result"], found["note"] or found["result"]
        if name in complete.EXPERIMENTAL:
            answer, why = complete.recorded(answer, why)
        faults = found["faults"]
        counted = name not in complete.EXPERIMENTAL  # an experimental check's faults never make an output worse
        return checks.Verdict(name, answer, f"{len(faults)} faults: {why}" if faults and counted else why,
                              {"faults": len(faults)}, {"faults": "lower"} if counted else {},
                              tuple(fault if isinstance(fault, str) else json.dumps(fault) for fault in faults))
    judge.__name__ = f"judge_{name}"
    return checks.Check(name, judge)


CHECKS = (checks.Check("manifest", judge_manifest), *map(gate_check, GATE))
