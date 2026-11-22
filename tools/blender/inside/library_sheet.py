"""Runs inside Blender: one small studio picture per library entry for the review contact sheets
(tools/library/sheets/sheets.py), each entry's files fetched first from the library's public copy by their sha256, so
only the job list goes up to the machine.

    blender -b --python tools/blender/inside/library_sheet.py -- <job.json> <out folder>

job.json: {"size": [wide, tall], "samples": n, "blobs": "<base url>", "cache": "/abs/folder", "items": [item, ...]}.
An item:
    {"name": "0001", "address": "model/x@1",
     "fetch": {"<file in the entry>": "<sha256>", ...},   fetched from <blobs>/<sha[:2]>/<sha>, its hash checked
     "show": {...},        a library_demo.py item whose file paths are files of the entry (an effect's particle files
                           are absolute: they come up with the job), or
     "surface": {...}}     a library surface on a sphere: {"maps": {"colour"|"normal"|"orm"|"roughness"|"metalness":
                           file}, "constants": {...}, "metre": m} for an image or constant surface, {"recipe": spec}
                           for a ProcFunc recipe (tools/props/library/recipes.py, shipped with the job)
Writes <out>/<name>.png and <out>/<name>.json ({"address", "ok": true, "seconds"} or {"address", "error"}); one
broken entry is its own result and the rest still render. Each entry's fetched files are removed once it is drawn.
The studio, the camera and the render settings are library_demo.py's.
"""
import hashlib
import json
import pathlib
import shutil
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request

import bpy

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library_demo  # noqa: E402

RECIPES = HERE.parents[1] / "props/library/inside"
TRIES = 5
TIMEOUT = 300


def download(url, target, sha):
    """One blob into `target`, its sha256 checked; tried again after a refusal or a dropped link."""
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(TRIES):
        try:
            digest = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=TIMEOUT) as answer, open(target, "wb") as written:
                for block in iter(lambda: answer.read(1 << 20), b""):
                    digest.update(block)
                    written.write(block)
            if digest.hexdigest() != sha:
                raise ValueError(f"{target.name}: fetched bytes hash {digest.hexdigest()}, the entry records {sha}")
            return
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            if attempt == TRIES - 1:
                raise RuntimeError(f"{target.name}: not fetched from {url}: {error!r}") from error
            time.sleep(2 ** attempt * 3)


def fetch(job, item):
    """Every file the item names, in its own cache folder; the folder."""
    folder = pathlib.Path(job["cache"]) / item["name"]
    for file, sha in item["fetch"].items():
        download(f"{job['blobs']}/{sha[:2]}/{sha}", folder / file, sha)
    return folder


class Prefetch:
    """The next item's files fetched while this one renders."""

    def __init__(self, job, item):
        self.error, self.folder = None, None
        self.thread = threading.Thread(target=self.work, args=(job, item), daemon=True)
        self.thread.start()

    def work(self, job, item):
        try:
            self.folder = fetch(job, item)
        except Exception as error:  # the item's own result says so
            self.error = error

    def result(self):
        self.thread.join()
        if self.error:
            raise self.error
        return self.folder


def in_folder(show, folder):
    """The library_demo item with each entry file as its path in the fetched folder."""
    files = []
    for given in show.get("files", []):
        given = dict(given) if isinstance(given, dict) else {"path": given}
        given["path"] = str(folder / given["path"])
        files.append(given)
    return dict(show, files=files)


def image_material(surface, folder):
    """An image or constant library surface: its maps (an ORM map's green as roughness, blue as metal) and its constants
    on a principled surface, laid by box projection at the surface's own tile size."""
    material = bpy.data.materials.new("surface")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes["Principled BSDF"]
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = [1.0 / (surface.get("metre") or 1.0)] * 3
    links.new(nodes.new("ShaderNodeTexCoord").outputs["Object"], mapping.inputs["Vector"])
    maps, constants = surface.get("maps", {}), surface.get("constants", {})

    def texture(key, colour):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(folder / maps[key]))
        node.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        node.projection, node.projection_blend = "BOX", 0.25
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node.outputs["Color"]

    if "colour" in maps:
        links.new(texture("colour", True), shader.inputs["Base Color"])
    elif "diffuseColor" in constants:
        shader.inputs["Base Color"].default_value = (*constants["diffuseColor"], 1.0)
    if "orm" in maps:
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(texture("orm", False), split.inputs["Color"])
        links.new(split.outputs["Green"], shader.inputs["Roughness"])
        links.new(split.outputs["Blue"], shader.inputs["Metallic"])
    for key, socket in (("roughness", "Roughness"), ("metalness", "Metallic")):
        if key in maps:
            links.new(texture(key, False), shader.inputs[socket])
    for key, socket in (("roughness", "Roughness"), ("metallic", "Metallic"), ("ior", "IOR")):
        if key in constants and not shader.inputs[socket].is_linked:
            shader.inputs[socket].default_value = constants[key]
    if "normal" in maps:
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(texture("normal", False), normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    if "emissiveColor" in constants:
        shader.inputs["Emission Color"].default_value = (*constants["emissiveColor"], 1.0)
        shader.inputs["Emission Strength"].default_value = 1.0
    if constants.get("opacity", 1.0) < 1.0:
        shader.inputs["Transmission Weight"].default_value = 1.0 - constants["opacity"]
    return material


def recipe_material(spec):
    """A ProcFunc recipe surface, new and clean, as the library's swatch renders it."""
    sys.path.insert(0, str(RECIPES))
    import runtime
    runtime.ready()
    import recipes
    material = recipes.shaded(recipes.channels(spec, 0.0, 0.0, 0.0)).item()
    material.displacement_method = "BUMP"
    return material


def render_surface(job, item, folder, out):
    """The surface on a sphere in library_demo's studio."""
    scene = library_demo.empty_scene(job["size"], job["samples"])
    surface = item["surface"]
    material = recipe_material(surface["recipe"]) if "recipe" in surface else image_material(surface, folder)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=96, ring_count=48)
    sphere = bpy.context.object
    sphere.data.shade_smooth()
    sphere.data.materials.append(material)
    look = {"heading": 30, "elevation": 15, "margin": 1.1}
    low, high, _ = library_demo.stand_on_ground([sphere])
    centre, radius = library_demo.camera_for(scene, low, high, look)
    library_demo.backdrop(radius, "light")
    library_demo.studio_lights(radius, centre, 1.0)
    library_demo.world_light(scene, (0.6, 0.65, 0.72), 0.08)
    scene.render.filepath = str(out / f"{item['name']}.png")
    bpy.ops.render.render(write_still=True)


def render_shown(job, item, folder, out):
    """A model, kit piece, character, take or effect through library_demo.py; a character with no walking clip is drawn
    in its rest pose, noted."""
    show = in_folder(dict(item["show"], name=item["name"]), folder)
    try:
        library_demo.render_item(job, show, out)
        return None
    except KeyError as error:
        if "action" not in show or show["action"] not in str(error):
            raise
    library_demo.render_item(job, {key: value for key, value in show.items() if key not in ("action", "frame")}, out)
    return f"no '{show['action']}' clip: drawn in its rest pose"


def render_one(job, item, folder, out):
    began = time.time()
    result = {"address": item["address"]}
    try:
        if "surface" in item:
            render_surface(job, item, folder, out)
        else:
            note = render_shown(job, item, folder, out)
            if note:
                result["note"] = note
        if not (out / f"{item['name']}.png").is_file():
            raise RuntimeError("the render wrote no picture")
        result.update(ok=True)
    except BaseException as error:  # one broken entry is its own finding; the rest still render
        result.update(ok=False, error=f"{type(error).__name__}: {error}"[:800],
                      trace=traceback.format_exc(limit=4)[-1500:])
    result["seconds"] = round(time.time() - began, 1)
    (out / f"{item['name']}.json").write_text(json.dumps(result, indent=1))
    print(f"library_sheet: {item['name']} {item['address']} {'ok' if result['ok'] else 'FAILED ' + result['error']}",
          flush=True)


def main():
    job, out = library_demo.arguments()
    out.mkdir(parents=True, exist_ok=True)
    items = [item for item in job["items"] if not (out / f"{item['name']}.json").is_file()]
    coming = Prefetch(job, items[0]) if items else None
    for index, item in enumerate(items):
        current = coming
        coming = Prefetch(job, items[index + 1]) if index + 1 < len(items) else None
        try:
            folder = current.result()
        except Exception as error:
            (out / f"{item['name']}.json").write_text(json.dumps(
                {"address": item["address"], "ok": False, "error": f"fetch: {error}"[:800]}, indent=1))
            print(f"library_sheet: {item['name']} {item['address']} FAILED fetch: {error}", flush=True)
            shutil.rmtree(pathlib.Path(job["cache"]) / item["name"], ignore_errors=True)
            continue
        render_one(job, item, folder, out)
        shutil.rmtree(folder, ignore_errors=True)


main()
