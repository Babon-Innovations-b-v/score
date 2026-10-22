"""The animal rows (experimental, #52): every scene inventory row whose kind roams (an animal, CONTEXT.md "row kind",
data/checks/row-kinds.json) gets two rows of its own at its place, made by the character maker's animal route
(tools/characters/animals/route.py, its overlay), never from a record written per scene:

    animal-body-<row>@<place>   paid: the row's picture cut from the place's locked concept by its box, Pixal3D's
                                model of it (route.mesh, the cloud batch) and, for a four-legged animal, UniRig's
                                skeleton and skin (route.unirig); a fish gets its spine in the clips row
    animal-clips-<row>@<place>  paid: the rig and its clips keyed in Blender, its review frames from the exported file
                                (route.blender_steps, one held cloud machine) and its UsdSkel asset (route.usd)

The row's kind decides its body (`fish` in its kind's rule, else four-legged), its length is the longer of its
inventory metres across, its clips the route's for that body (CLIPS). Gates, like the people's: `made` (the body's
model, and its rig for a four-legged animal) and `clips made` (the file, every clip with its review frames, the rig
record and the UsdSkel asset); a missing or unreadable record answers unknown, never pass.

Prices: no animal was ever made by a stage, so neither row has a measured price; each names a guess (BODY_EUROS,
CLIPS_EUROS) that the runner keeps apart and never shows as a price.
"""
import functools
import json
import pathlib
import shutil
import sys

from score import contracts, graph
from score.checks import FAIL, PASS, UNKNOWN, Check, Verdict
from score.stages import design_layers, row_kinds

REPO = pathlib.Path(__file__).resolve().parents[3]
ROUTE = REPO / "tools/characters/animals"
BODY, CLIPS_ROW = "animal-body", "animal-clips"
# The route's clips for each body (tools/characters/animals overlay: made, not captured).
CLIPS = {"fish": ["swim", "turn", "hover"], "quadruped": ["idle", "walk", "sit"]}
# The row's box widened by this share of its size each side, so the cut-out keeps the whole animal.
MARGIN = 0.1
# Not measured (no animal made by a stage yet): a guess each, kept apart by the runner, never shown as a price.
# Body: one Pixal3D model (pixal's measured high EUR 0.20 a model) and one UniRig run on a card (never timed).
BODY_EUROS = 0.5
# Clips: the route's 25 Blender minutes on one held card with its set-up.
CLIPS_EUROS = 0.6
FILES = {"design": design_layers.PATTERN, "row kinds": "{data}/checks/row-kinds.json",
         "concept": "{home}/design/concepts/{place}.png", "animal route": "{repo}/tools/characters/animals",
         "skel_usd": "{repo}/tools/characters/skel_usd.py"}


@functools.lru_cache(maxsize=256)
def kept_animals(path, stamp, rules_stamp):
    """The animal rows of a kept inventory, read once while neither it nor the rules change (`stamp` and
    `rules_stamp` are their files' times, the cache's key only)."""
    inventory = json.loads(pathlib.Path(path).read_text())
    return frozenset(row["id"] for row in row_kinds.rows_that(inventory, "roams", row_kinds.table()))


def animals_of(place):
    """The ids of the rows of the place's design whose kind roams; none for a place with no design."""
    path = design_layers.KEPT / f"{place}.json"
    if not path.is_file():
        return frozenset()
    return kept_animals(str(path), path.stat().st_mtime_ns, row_kinds.TABLE.stat().st_mtime_ns)


def holding(row):
    """A row's `applies`: the place's design shows the animal row `row`."""
    def applies(place):
        return row in animals_of(place)
    applies.__name__ = f"holds_{row}"
    return applies


def spec_of(place, row, kinds, picture):
    """The animal route's spec of an inventory row (route.py's docstring), approved by the place's lock."""
    noun = row_kinds.words(row.get("noun")) or row_kinds.words(row.get("name") or row["id"]).rsplit(" ", 1)[-1]
    body = "fish" if noun in kinds[row_kinds.kind_of(row, kinds)].get("fish", []) else "quadruped"
    return {"name": f"{place}_{row['id']}", "kind": "animal", "body": body,
            "length_m": round(max(row["size"][:2]), 3), "clips": CLIPS[body], "picture": str(picture),
            "approved": f"the creator's lock of {place}: its locked concept's scene inventory row {row['id']}"}


def cut_out(concept, box, out):
    """The row's box of the locked concept, widened by MARGIN each side, written to `out`."""
    from PIL import Image
    image = Image.open(concept)
    left, top, right, bottom = box
    wide, tall = (right - left) * MARGIN, (bottom - top) * MARGIN
    image.crop((max(0, int(left - wide)), max(0, int(top - tall)), min(image.width, int(right + wide)),
                min(image.height, int(bottom + tall)))).convert("RGB").save(out)
    return out


def route():
    sys.path.insert(0, str(ROUTE))
    import route as animal_route
    return animal_route


def make_body(inputs, out, seed, params):
    """animal.json (the spec), picture.png, model.glb and, four-legged, rigged.glb."""
    place = pathlib.Path(inputs["design"]).stem
    kinds = json.loads(pathlib.Path(inputs["row kinds"]).read_text())["kinds"]
    row = next(found for found in json.loads(pathlib.Path(inputs["design"]).read_text())["rows"]
               if found["id"] == params["row"])
    spec = spec_of(place, row, kinds, cut_out(inputs["concept"], row["box"], out / "picture.png"))
    (out / "work").mkdir()
    who, maker = f"{BODY}-{params['row']}@{place}", route()
    model = maker.mesh(spec, out, who, False)
    shutil.copy2(model, out / "model.glb")
    if spec["body"] != "fish":
        shutil.copy2(maker.unirig(model, out, who, False), out / "rigged.glb")
    shutil.rmtree(out / "work")
    (out / "animal.json").write_text(json.dumps(spec, indent=1))


def body_faults(folder):
    return [f"no {name}" for name in ("animal.json", "model.glb") if not (pathlib.Path(folder) / name).exists()]


def judge_made(output, inputs, evidence):
    """The body's model, and a four-legged animal's rig, each a file with something in it."""
    spec = json.loads((output / "animal.json").read_text())
    wanted = ["model.glb"] + ([] if spec["body"] == "fish" else ["rigged.glb"])
    failing = [f"{name}: missing or empty" for name in wanted
               if not (output / name).is_file() or not (output / name).stat().st_size]
    return Verdict("made", FAIL if failing else PASS, "; ".join(failing) or f"{spec['name']}: {', '.join(wanted)}",
                   {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


def make_clips(inputs, out, seed, params):
    """<name>.glb with its clips, lods/, rig.json, review/ (frames and GIFs), usd/ and clips.json."""
    body = pathlib.Path(inputs[f"{BODY}-{params['row']}"])
    spec = json.loads((body / "animal.json").read_text())
    model = body / ("model.glb" if spec["body"] == "fish" else "rigged.glb")
    maker = route()
    made = maker.blender_steps(spec, out, model, f"{CLIPS_ROW}-{params['row']}@{spec['name']}")
    usd = maker.usd(made, out)
    (out / "clips.json").write_text(json.dumps({"spec": spec, "glb": made.name, "usd": str(pathlib.Path(usd).name)},
                                               indent=1))


def clips_faults(folder):
    return [] if (pathlib.Path(folder) / "clips.json").exists() else ["no clips.json"]


def judge_clips_made(output, inputs, evidence):
    """The file, the rig record, the UsdSkel asset and every clip's review frames."""
    record = json.loads((output / "clips.json").read_text())
    spec = record["spec"]
    failing = [f"no {name}" for name in (record["glb"], "rig.json", "usd") if not (output / name).exists()]
    failing += [f"{clip}: no review frames" for clip in spec["clips"]
                if not any((output / "review" / clip).glob("*.png"))]
    return Verdict("clips made", FAIL if failing else PASS,
                   "; ".join(failing) or f"{len(spec['clips'])} clips with their review frames",
                   {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


def guarded(name, judge):
    """A check whose missing or unreadable record answers unknown, never pass."""
    def judged(output, inputs, evidence):
        try:
            return judge(output, inputs, evidence)
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as missing:
            return Verdict(name, UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")
    return Check(name, judged)


def rows_for(row):
    """The body and clips rows of one animal row id, at every place whose design shows it."""
    applies = holding(row)
    body = graph.Stage(f"{BODY}-{row}", "place", make_body, contracts.Contract(BODY, 1, body_faults),
                       (guarded("made", judge_made),), files=FILES, params={"row": row}, paid=True,
                       euros=BODY_EUROS, applies=applies)
    clips = graph.Stage(f"{CLIPS_ROW}-{row}", "place", make_clips, contracts.Contract(CLIPS_ROW, 1, clips_faults),
                        (guarded("clips made", judge_clips_made),), files=FILES, params={"row": row},
                        after={f"{BODY}-{row}": (BODY, 1)}, paid=True, euros=CLIPS_EUROS, applies=applies)
    return body, clips


def rows():
    """Every animal row's body and clips rows, one pair an animal row id the kept designs show."""
    shown = set().union(*(animals_of(path.stem) for path in design_layers.KEPT.glob("*.json")))
    return tuple(stage for row in sorted(shown) for stage in rows_for(row))
