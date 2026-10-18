"""A place's fresh web copy for the dashboard's 3D viewer, from its ACCEPTED OpenUSD stage (assembly@<place>), made
on this machine for free, one place at a time:

    systemd-run --user --scope -q -p MemoryMax=8G nice .venv/bin/python -m score.dashboard web3d <place>

The accepted output's files are linked (never copied, never written) into a work folder and opened with usd-core.
Meshes, surfaces, lights and the sky are read by tools/review/viewer/export.py's own functions, loaded by path and
never edited (it is part of the films' key). Unlike that export, each object stays its own named node (gltfpack
-kn), so the viewer can show or hide each OpenUSD layer and name what is clicked; each object's layer is the
sublayer of the place's stage that defines it. gltfpack (meshoptimizer, MIT; npx at export.py's pinned version)
compresses the meshes with meshopt; pictures go in as downsized JPEG (PNG where see-through), at most FULL_TEXTURE px
a side (gltfpack's node.js build has no KTX2 encoder). Two copies: a light preview shown first (meshes simplified
hard, gltfpack -sa, pictures at LIGHT_TEXTURE px; the hangar: 3.1 MB) that the whole one replaces once loaded; the
whole one is never simplified (the hangar: 2.5 million triangles, 26.7 MB, 2026-10-18). Out: $SCORE_DASHBOARD_HOME/web3d/<place>/{<place>.glb, <place>-light.glb, <place>.json}; nothing in the
store, the repository or the work folder is written.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
EXPORT = REPO / "tools/review/viewer/export.py"
FULL_TEXTURE = 512
LIGHT_TEXTURE = 128
JPEG_QUALITY = 80
LIGHT_RATIO = 0.1
# The preview may move a surface by up to this share of its mesh's size (gltfpack -se, with -sa): without -sa its
# default 0.01 kept the hangar's preview at 15.6 MB of 26.7.
LIGHT_ERROR = "0.05"
THREADS = "2"
POSITIONS = ("-vp", "16")
# The layers of a place's stage that may define objects, by the file stem in layers/ (score/stages/assembly/record.py).
LAYER_STEMS = ("edit", "characters", "sound", "light", "motion", "effects", "crops", "machines", "settle", "ground",
               "base")


def exporter():
    """tools/review/viewer/export.py as a module, loaded from its file (read only)."""
    spec = importlib.util.spec_from_file_location("score_viewer_export", EXPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def linked_output(store_root, output, folder):
    """The output's files as links into `folder` to the stored blobs (read only); the folder."""
    listing = json.loads((store_root / "objects" / "outputs" / f"{output}.json").read_text())
    for name, sha in listing.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(store_root / "objects" / "blobs" / sha)
    return folder


def accepted_assembly(store_root, place):
    """The newest standing accept of assembly@<place> (no later reject of its output), or None."""
    def read_all(area):
        folder = store_root / "objects" / area / f"assembly@{place}"
        found = [json.loads(path.read_text()) for path in folder.glob("*.json")] if folder.is_dir() else []
        return sorted(found, key=lambda item: item["at"])
    rejected = {item["output"]: item["at"] for item in read_all("rejects")}
    standing = [item for item in read_all("accepts") if item["at"] > rejected.get(item["output"], "")]
    return standing[-1] if standing else None


def layer_of(prim):
    """The layer of the place's stage that defines a prim (or its nearest ancestor that one defines): the weakest
    sublayer spec that is a `def`; "base" when none says."""
    from pxr import Sdf
    while prim and prim.IsValid():
        defining = [spec.layer for spec in prim.GetPrimStack()
                    if spec.specifier == Sdf.SpecifierDef and "/layers/" in spec.layer.identifier]
        if defining:
            stem = pathlib.PurePosixPath(defining[-1].identifier).stem
            return stem if stem in LAYER_STEMS else "base"
        prim = prim.GetParent()
    return "base"


def cameras(place):
    """The scene record's cameras (data/scene/<place>.json `views`), read as a file: name, eye, aim, fov."""
    path = REPO / "data/scene" / f"{place}.json"
    record = json.loads(path.read_text()) if path.is_file() else {}
    return [{"name": view["name"], "eye": view["eye"], "aim": view["aim"], "fov": float(view.get("fov", 75.0))}
            for view in record.get("views", [])]


def node_layers(stage, export, time):
    """{object name as the viewer names it: layer} of every drawn mesh."""
    from pxr import Usd
    found = {}
    for prim in Usd.PrimRange(stage.GetDefaultPrim()):
        if export.drawn(prim, time):
            found.setdefault(export.object_name(prim), layer_of(prim))
    return found


def smaller_copy(source, folder, side):
    """The glTF document at `source` copied into `folder` with every picture at most `side` px a side: its path."""
    from PIL import Image
    shutil.copytree(source.parent, folder)
    for picture in [*folder.glob("*.jpg"), *folder.glob("*.png")]:
        with Image.open(picture) as opened:
            opened.thumbnail((side, side))
            opened.save(picture, **({"quality": JPEG_QUALITY} if picture.suffix == ".jpg" else {}))
    return folder / source.name


def pack(export, source, out, ratio):
    """gltfpack: named nodes kept, meshopt meshes, simplified to `ratio` when under 1."""
    command = ["npx", "-y", export.GLTFPACK, "-i", str(source), "-o", str(out), "-cc", "-kn", "-km", *POSITIONS,
               *(["-si", str(ratio), "-se", LIGHT_ERROR, "-sa"] if ratio < 1 else [])]
    done = subprocess.run(command, capture_output=True, text=True, env={**os.environ, "OMP_NUM_THREADS": THREADS})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"gltfpack failed:\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}")


def convert(place, store_root, out_root):
    """Write the place's two web copies and sidecar from its accepted assembly; the sidecar."""
    accept = accepted_assembly(store_root, place)
    if accept is None:
        raise RuntimeError(f"{place} has no accepted assembly: nothing to show in 3D")
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"web3d-{place}-"))
    try:
        linked = linked_output(store_root, accept["output"], work / "stage")
        return write_copies(place, linked, out_root, {"from_output": accept["output"], "accepted_at": accept["at"]},
                            cameras(place))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def write_copies(place, stage_folder, out_root, origin, views):
    """Write the two web copies and sidecar of the OpenUSD stage in `stage_folder` (<place>.usda) into
    out_root/<place>/, swapped in whole; the sidecar, which carries `origin` (where the stage came from) and the
    cameras `views`."""
    export = exporter()
    export.TEXTURE_SIZE, export.JPEG_QUALITY = FULL_TEXTURE, JPEG_QUALITY
    from pxr import Usd
    started = time.monotonic()
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"web3d-{place}-"))
    folder = out_root / place
    partial = out_root / f"{place}.partial"
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    try:
        stage = Usd.Stage.Open(str(stage_folder / f"{place}.usda"))
        moment = Usd.TimeCode(stage.GetStartTimeCode())
        gltf = export.Gltf(work / "gltf")
        (work / "gltf").mkdir()
        boxes, triangles, left_out = export.write_meshes(stage, gltf, moment)
        source = gltf.write()
        pack(export, smaller_copy(source, work / "light", LIGHT_TEXTURE), partial / f"{place}-light.glb", LIGHT_RATIO)
        pack(export, source, partial / f"{place}.glb", 1.0)
        layers = node_layers(stage, export, moment)
        lights = [entry for entry in (export.light_entry(prim, moment) for prim in stage.Traverse()) if entry]
        sky = export.sky(stage, moment)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    sidecar = {"place": place, **origin,
               "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "triangles": triangles,
               "left_out": left_out, "lights": lights, "sky": sky, "cameras": views,
               "objects": [{"name": name, "layer": layers.get(name, "base"), "low": low.round(4).tolist(),
                            "high": high.round(4).tolist()} for name, (low, high) in boxes.items()],
               "bytes": (partial / f"{place}.glb").stat().st_size,
               "light_bytes": (partial / f"{place}-light.glb").stat().st_size,
               "packed_with": f"{export.GLTFPACK} -cc -kn -km, pictures JPEG at most {FULL_TEXTURE} px", "seconds": round(time.monotonic() - started, 1)}
    (partial / f"{place}.json").write_text(json.dumps(sidecar))
    shutil.rmtree(folder, ignore_errors=True)
    partial.rename(folder)
    return sidecar


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.dashboard web3d", description=__doc__.split("\n")[0])
    parser.add_argument("place")
    parser.add_argument("--store", type=pathlib.Path, help="the store folder (default $PROPS_HOME/store)")
    parser.add_argument("--out", type=pathlib.Path, help="default $SCORE_DASHBOARD_HOME/web3d")
    options = parser.parse_args(argv)
    props = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
    home = pathlib.Path(os.environ.get("SCORE_DASHBOARD_HOME", props / "dashboard"))
    sidecar = convert(options.place, options.store or props / "store", options.out or home / "web3d")
    print(f"{options.place}: {sidecar['triangles']} triangles, {sidecar['bytes'] / 1e6:.1f} MB "
          f"(light {sidecar['light_bytes'] / 1e6:.1f} MB), {sidecar['seconds']} s, "
          f"left out {sidecar['left_out'] or 'nothing'}")


if __name__ == "__main__":
    sys.exit(main())
