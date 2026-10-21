"""A kit bake's gates: the made models of make_kit's jobs (tools/props/library/inside/make_kit.py, baked with the
material library on rented cards by tools/props/cloud/library_bake.py) judged by its reports. The ship kits' and the
earth kit's rows take them; the late-bake row that baked the camp's game kit (camp_kit.py, the old seed's made folder)
is retired (2026-10-21).

    `made`      every planned model has its model and a report with triangles
    `surfaces`  every slot of every made model is a library variant, data/library/materials.json, or one of its
                printed pictures, data/library/pictures: each part takes exactly one surface from the shared library
"""
import json
import pathlib

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[3]


def late_faults(folder):
    """Why a folder is not a late bake, or [] when it is."""
    return [f"no {name}" for name in ("layout.json", "plan.json", "made") if not (folder / name).exists()]


def reports(output):
    """{model: make_kit's report entry} from every report in the made folder."""
    found = {}
    for path in sorted((output / "made").glob("report*.json")):
        found.update(json.loads(path.read_text()).get("pieces", {}))
    return found


def judge_made(output, inputs, evidence):
    """Every planned model has its model file and a report with triangles."""
    planned = sorted(json.loads((output / "plan.json").read_text())["models"])
    found = reports(output)
    missing = [name for name in planned if not (output / "made" / f"{name}.gltf").exists()
               or not found.get(name, {}).get("triangles")]
    answer = checks.FAIL if missing else checks.PASS
    reason = f"{len(planned) - len(missing)} of {len(planned)} planned models made" + (
        f"; missing {', '.join(missing)}" if missing else "")
    return checks.Verdict("made", answer, reason, {"planned": len(planned), "missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


def library_names():
    """Every library variant and printed picture by name."""
    library = json.loads((REPO / "data/library/materials.json").read_text())
    names = {variant for family in library["families"].values() for variant in family.get("variants", {})}
    return names | {path.stem for path in (REPO / "data/library/pictures").glob("*.png")}


def judge_surfaces(output, inputs, evidence):
    """Every slot of every made model is one of the shared library's surfaces."""
    names = library_names()
    foreign = sorted({f"{model}: {slot}" for model, entry in reports(output).items()
                      for slot in entry.get("slots", []) if slot not in names})
    answer = checks.FAIL if foreign else checks.PASS
    reason = "every slot a library surface" if not foreign else f"{len(foreign)} slots off the library: " + ", ".join(
        foreign[:8])
    return checks.Verdict("surfaces", answer, reason, {"foreign": len(foreign)}, {"foreign": "lower"}, tuple(foreign))
