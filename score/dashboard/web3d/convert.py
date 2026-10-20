"""A place's fresh web copy for the dashboard's 3D viewer, from its ACCEPTED OpenUSD stage (assembly@<place>), made
on this machine for free, one place at a time:

    systemd-run --user --scope -q -p MemoryMax=8G nice .venv/bin/python -m score.dashboard web3d <place>

The accepted output's files are linked (never copied, never written) into a work folder and opened with usd-core;
the other places its scene shows (the city past the flat's balcony, the far city across the harbour) are linked
beside it from the place's accepted neighbours output, as the films see them. Meshes, surfaces, lights and the sky
are read by tools/review/viewer/export.py's own functions, loaded by path and never edited (it is part of the films'
key). Unlike that export, each object stays its own named node (gltfpack -kn), so the viewer can show or hide each
OpenUSD layer and name what is clicked; each object's layer is the sublayer of the place's stage that defines it
(web3d/facts.py, which also reads the lamps, the effects' points, the moving things' motion and the film's cameras).

gltfpack (meshoptimizer, MIT; npx at export.py's pinned version) compresses the meshes with meshopt, positions kept
as floats (16-bit positions over a place whose far ground ring is kilometres across moved surfaces by most of a
metre: the flat, 2026-10-18). Every surface keeps its baked pictures (colour, normal, roughness and metalness, glow)
as WebP, at most FULL_TEXTURE px a side (gltfpack's node.js build has no KTX2 encoder; three.js decodes WebP
natively). Three copies, loaded in this order: the place's light preview (meshes simplified hard, gltfpack -sa,
pictures at LIGHT_TEXTURE px), the shown places that have no copy of their own (`-around`: the far city, pictures
at AROUND_TEXTURE px) and the place's whole copy (never simplified). A shown place with its own copy is not written
again: the viewer loads that copy onto its seat (the sidecar's `shows`). Never simplify a shown place to save bytes:
gltfpack -sa folded the square's stage and backdrop into shards (2026-10-18), and without -sa it stops at the seams
of Pixal3D's models. Out: $SCORE_DASHBOARD_HOME/web3d/<place>/
{<place>.glb, <place>-light.glb, <place>-around.glb, <place>.json}; nothing in the store, the repository or the work
folder is written.
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

from score.dashboard.web3d import facts, meshes

REPO = pathlib.Path(__file__).resolve().parents[3]
EXPORT = REPO / "tools/review/viewer/export.py"
# The whole copies of every place must fit the hosted export's cap with the rest of the cockpit (600 MB on the
# hosted site): at 1024 px the workshop's and the wreck's were left out of it (2026-10-18).
FULL_TEXTURE = 768
AROUND_TEXTURE = 512
LIGHT_TEXTURE = 256
WEBP_QUALITY = 82
LIGHT_RATIO = 0.1
# The preview may move a surface by up to this share of its mesh's size (gltfpack -se, with -sa): without -sa its
# default 0.01 kept the hangar's preview at 15.6 MB of 26.7.
LIGHT_ERROR = "0.05"
THREADS = "2"
POSITIONS = ("-vpf",)
TEXCOORDS = ("-vt", "14")


def exporter():
    """tools/review/viewer/export.py as a module, loaded from its file (read only)."""
    spec = importlib.util.spec_from_file_location("score_viewer_export", EXPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def linked_output(store_root, output, folder, within=""):
    """The output's files (those under `within`, that prefix dropped) as links into `folder` to the stored blobs (read
    only); the folder."""
    listing = json.loads((store_root / "objects" / "outputs" / f"{output}.json").read_text())
    for name, sha in listing.items():
        if not name.startswith(within):
            continue
        target = folder / name[len(within):]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(store_root / "objects" / "blobs" / sha)
    return folder


def accepted_assembly(store_root, place):
    """The newest standing accept of assembly@<place> (no later reject of its output), or None."""
    return standing_accept(store_root, f"assembly@{place}")


def standing_accept(store_root, node):
    """The newest standing accept of a node (no later reject of its output), or None."""
    def read_all(area):
        folder = store_root / "objects" / area / node
        found = [json.loads(path.read_text()) for path in folder.glob("*.json")] if folder.is_dir() else []
        return sorted(found, key=lambda item: item["at"])
    rejected = {item["output"]: item["at"] for item in read_all("rejects")}
    standing = [item for item in read_all("accepts") if item["at"] > rejected.get(item["output"], "")]
    return standing[-1] if standing else None


def linked_neighbours(store_root, place, work):
    """Every other place the place's scene shows (its accepted neighbours output's places/<other>/, the far city among
    them) linked into work/<other>/, where the stage's references (../../<other>/<other>.usda) find them: their
    names; none when the place has no neighbours output."""
    accept = standing_accept(store_root, f"neighbours@{place}")
    if accept is None:
        return []
    listing = json.loads((store_root / "objects" / "outputs" / f"{accept['output']}.json").read_text())
    others = sorted({name.split("/")[1] for name in listing if name.startswith(f"{facts.NEIGHBOURS}/")})
    for other in others:
        linked_output(store_root, accept["output"], work / other, f"{facts.NEIGHBOURS}/{other}/")
    return others


def cameras(place):
    """The scene record's cameras (data/scene/<place>.json `views`), read as a file: name, eye, aim, fov."""
    path = REPO / "data/scene" / f"{place}.json"
    record = json.loads(path.read_text()) if path.is_file() else {}
    return [{"name": view["name"], "eye": view["eye"], "aim": view["aim"], "fov": float(view.get("fov", 75.0))}
            for view in record.get("views", [])]


def place_cameras(store_root, place):
    """The cameras the viewer offers: the accepted film's shots first (the viewer opens on the first), then the
    scene record's."""
    film = standing_accept(store_root, f"demo-film@{place}")
    return [*(facts.film_cameras(store_root, film["output"]) if film else []), *cameras(place)]


def node_layers(stage, export, time):
    """{object name as the viewer names it: layer} of every drawn mesh, prototypes of instancers among them."""
    from pxr import Usd
    found = {}
    for prim in Usd.PrimRange(stage.GetDefaultPrim()):
        if export.drawn(prim, time):
            found.setdefault(export.object_name(prim), facts.layer_of(prim))
    return found


def webp_copy(source, folder, side):
    """The glTF document at `source` copied into `folder` with every picture as WebP at most `side` px a side (its
    see-through kept): the copy's path."""
    from PIL import Image
    shutil.copytree(source.parent, folder)
    document = json.loads((folder / source.name).read_text())
    for image in document.get("images", []):
        picture = folder / image["uri"]
        with Image.open(picture) as opened:
            opened.thumbnail((side, side), Image.LANCZOS)
            opened.save(picture.with_suffix(".webp"), quality=WEBP_QUALITY, method=4)
        picture.unlink()
        image["uri"] = picture.with_suffix(".webp").name
    (folder / source.name).write_text(json.dumps(document))
    return folder / source.name


def pack(export, source, out, ratio, error=LIGHT_ERROR):
    """gltfpack: named nodes kept, meshopt meshes, simplified hard to `ratio` when under 1 (within `error` of each
    mesh's size)."""
    simplify = ["-si", str(ratio), "-se", error, "-sa"] if ratio < 1 else []
    command = ["npx", "-y", export.GLTFPACK, "-i", str(source), "-o", str(out), "-cc", "-kn", "-km", *POSITIONS,
               *TEXCOORDS, *simplify]
    done = subprocess.run(command, capture_output=True, text=True, env={**os.environ, "OMP_NUM_THREADS": THREADS})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"gltfpack failed:\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}")


def convert(place, store_root, out_root):
    """Write the place's web copies and sidecar from its accepted assembly and the places it shows; the sidecar."""
    accept = accepted_assembly(store_root, place)
    if accept is None:
        raise RuntimeError(f"{place} has no accepted assembly: nothing to show in 3D")
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"web3d-{place}-"))
    try:
        linked = linked_output(store_root, accept["output"], work / place)
        shown = linked_neighbours(store_root, place, work)
        copied = {other for other in shown if accepted_assembly(store_root, other)}
        return write_copies(place, linked, out_root, {"from_output": accept["output"], "accepted_at": accept["at"]},
                            place_cameras(store_root, place), copied)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def packed(export, documents, work, partial, place):
    """The documents written and packed into partial/: the light preview and the whole copy of the place's own, the
    places it shows when it shows any. {file kind: bytes}."""
    own = documents["own"].write()
    pack(export, webp_copy(own, work / "light", LIGHT_TEXTURE), partial / f"{place}-light.glb", LIGHT_RATIO)
    pack(export, webp_copy(own, work / "whole", FULL_TEXTURE), partial / f"{place}.glb", 1.0)
    sizes = {"light_bytes": (partial / f"{place}-light.glb").stat().st_size,
             "bytes": (partial / f"{place}.glb").stat().st_size, "around_bytes": None}
    if documents["around"].document["nodes"]:
        around = documents["around"].write()
        pack(export, webp_copy(around, work / "around-web", AROUND_TEXTURE), partial / f"{place}-around.glb", 1.0)
        sizes["around_bytes"] = (partial / f"{place}-around.glb").stat().st_size
    return sizes


def stage_facts(export, stage, moment, elsewhere, effects_at=None):
    """The sidecar's facts of the stage beyond its meshes: lights, sky, haze, layers, effects (at the time code
    `effects_at`, else where each shows most), motion, sounds and the places it shows."""
    doubled = meshes.own_outside(stage)
    return {"shows": facts.shown_places(stage, elsewhere, doubled, moment),
            "lights": facts.lamps(export, stage, moment), "sky": export.sky(stage, moment), "glow": facts.glow(stage),
            "hazes": facts.hazes(stage, moment), "stage_layers": facts.stage_layers(stage),
            "effects": facts.effects(stage, effects_at), "motion": facts.motion(export, stage, moment),
            "sounds": facts.sounds(stage)}


def objects(boxes, layers):
    """The sidecar's objects: each written one with its layer and box, then each one of a shown place's own copy
    (named as this stage names it) with its layer and no box."""
    written = [{"name": name, "layer": layers.get(name, "base"), "low": low.round(4).tolist(),
                "high": high.round(4).tolist()} for name, (low, high) in boxes.items()]
    return written + [{"name": name, "layer": layer, "low": None, "high": None}
                      for name, layer in layers.items() if name not in boxes]


def write_copies(place, stage_folder, out_root, origin, views, elsewhere=()):
    """Write the web copies and sidecar of the OpenUSD stage in `stage_folder` (<place>.usda) into out_root/<place>/,
    swapped in whole; the sidecar, which carries `origin` (where the stage came from) and the cameras `views`. The
    shown places in `elsewhere` are left to their own copies."""
    export = exporter()
    export.TEXTURE_SIZE = FULL_TEXTURE
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
        documents = {name: export.Gltf(work / name) for name in ("own", "around")}
        for document in documents.values():
            document.folder.mkdir()
        boxes, triangles, left_out, instancers = meshes.write_meshes(export, stage, documents, moment, elsewhere)
        sizes = packed(export, documents, work, partial, place)
        layers = node_layers(stage, export, moment)
        # The effects as the film's first shot starts, where the viewer opens (the launch's plume at lift-off).
        effects_at = next((view["frame"] for view in views if view.get("frame") is not None), None)
        described = stage_facts(export, stage, moment, elsewhere, effects_at)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    sidecar = {"place": place, **origin,
               "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "triangles": triangles,
               "left_out": left_out, "cameras": views, **described, "instancers": instancers,
               "objects": objects(boxes, layers),
               **sizes, "packed_with": f"{export.GLTFPACK} -cc -kn -km -vpf, pictures WebP at most {FULL_TEXTURE} px",
               "seconds": round(time.monotonic() - started, 1)}
    (partial / f"{place}.json").write_text(json.dumps(sidecar, separators=(",", ":")))
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
    around = f", around {sidecar['around_bytes'] / 1e6:.1f} MB" if sidecar.get("around_bytes") else ""
    print(f"{options.place}: {sidecar['triangles']} triangles, {sidecar['bytes'] / 1e6:.1f} MB "
          f"(light {sidecar['light_bytes'] / 1e6:.1f} MB{around}), {sidecar['seconds']} s, "
          f"left out {sidecar['left_out'] or 'nothing'}")


if __name__ == "__main__":
    sys.exit(main())
