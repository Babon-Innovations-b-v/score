"""Runs inside Blender (`session.py batch`): build and bake a list of code-built kit pieces, one .glb each.

    python3 tools/blender/session.py batch tools/props/library/inside/make_kit.py -- <job.json>

The job: {"out": folder, "density": px a metre, "wear", "dirt", "seed", "specs": {library name: resolved entry},
"pieces": [{"name", "kind", "size", "laid"}]}. Writes <out>/<name>.glb and <out>/report.json (picture side, slots,
triangles, seconds per piece). Each piece starts from an empty scene, so one piece's data never weighs on the next.
"""
import json
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import pieces  # noqa: E402
import scene_setup  # noqa: E402

BAKE_SAMPLES = 16


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for entry in job["pieces"]:
        scene_setup.empty_scene(256, BAKE_SAMPLES)
        item = pieces.build(entry["kind"], entry["size"], entry.get("laid", {}), entry["name"])
        report[entry["name"]] = bake.baked(item, job["specs"], job["wear"], job["dirt"], job["seed"], job["density"],
                                           out / f"{entry['name']}.glb")
        print("PIECE", entry["name"], json.dumps(report[entry["name"]]), flush=True)
        bpy.ops.wm.read_factory_settings(use_empty=True)
    (out / "report.json").write_text(json.dumps(report, indent=1))


main()
