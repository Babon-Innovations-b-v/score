"""Runs inside Blender (on a rented machine, cloud/library_bake.py): build a list of code-built kit pieces and bake
them all into one shared picture set (bake.Atlas), one .gltf each beside the shared pictures.

The job: {"out": folder, "atlas": name, "density": px a metre, "wear", "dirt", "seed",
"specs": {library variant: resolved entry}, "pieces": [{"name", "kind", "size", "laid"}]}. Writes
<out>/<name>.gltf (+ .bin), <out>/textures/<atlas>_*.png and <out>/report.json (the atlas's sides, and per piece its
slots and triangles).
"""
import json
import pathlib
import sys
import time

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
    began = time.time()
    scene_setup.empty_scene(256, BAKE_SAMPLES)
    items = [pieces.build(entry["kind"], entry["size"], entry.get("laid", {}), entry["name"])
             for entry in job["pieces"]]
    slots = {item.name: bake.slot_names(item) for item in items}
    atlas = bake.Atlas(job["atlas"], items, job["density"])
    for item in items:
        atlas.bake_self(item, job["specs"], job["wear"], job["dirt"], job["seed"])
        print("BAKED", item.name, flush=True)
    atlas.finish()
    report = {"atlas": {"normal": atlas.side, "colour": atlas.pictures["base_color"].size[0],
                        "seconds": round(time.time() - began, 1)}, "pieces": {}}
    for item in items:
        report["pieces"][item.name] = dict(atlas.export(item, out), slots=slots[item.name])
    (out / "report.json").write_text(json.dumps(report, indent=1))


main()
