"""Contact sheets of the whole library for a review by eye (owner, 2026-11-22: is the library "nice and clean?", then
"yes" to a full visual pass): every current entry that has a look is one labelled tile, so a broken one shows.

    python tools/library/sheets/sheets.py prepare --work <folder> [--jobs N]
    PROPS_HOME=... python tools/library/sheets/sheets.py render --work <folder> --who <session> [--detach]
    python tools/library/sheets/sheets.py compose --work <folder> --out <folder>

`prepare` reads every entry of score_lib (withdrawn ones left out) and writes the cloud jobs: a model, kit piece,
character, take or effect as library_demo.py stages it, a surface on a sphere (tools/blender/inside/library_sheet.py),
each machine fetching its entries' files itself from the library's public copy by sha256, so only the job lists go up.
An effect's clip is read here at its fullest time, Z-up (its particles as the README's picture reads them, or a baked
clip's mesh as a PLY), and goes up with its job. `render` runs the jobs on rented
cards (tools/cloud/blender_cloud.py, spread over machines; a spend ticket in SCORE_SPEND_TICKET). `compose` lays the
pictures six across and five down, each tile labelled with its address, a concept or place from the picture its entry
holds, and writes <out>/<kind>/NN.jpg and <out>/index.json (sheet tile -> address; every entry that failed to fetch
or render, or holds no picture, with its error). The pictures are small and quick (REVIEW_SIZE, REVIEW_SAMPLES): they
never ship and only show whether an entry draws.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/library"))
sys.path.insert(0, str(REPO / "tools/library/demo"))
import library_files  # noqa: E402

INSIDE = REPO / "tools/blender/inside/library_sheet.py"
RECIPE_DEFAULTS = REPO / "data/library/materials.json"
BLOBS = f"https://huggingface.co/datasets/{library_files.HUB_REPO}/resolve/main/blobs"
MACHINE_CACHE = "/root/sheet-cache"
CLASSES = ["gpu-24gb"]
# The recipes' code the surface jobs import on the machine (tools/props/library/inside/runtime.py's paths).
RECIPE_CODE = ["tools/props/library", "vendor/procfunc/src", "vendor/infinigen2"]
REVIEW_SIZE = (320, 320)
REVIEW_SAMPLES = 32
JOBS = 14
# A job's seconds per entry, set apart from its bytes fetched (a guess for the spread; the run measures each).
SECONDS_EACH = 5.0
BYTES_PER_SECOND = 25e6
KINDS = ("model", "kit", "character", "surface", "take", "effect", "concept", "place")
# The kinds whose entries hold their own picture: drawn on the sheets, never rendered.
HELD = {"concept": "concept.png", "place": "render.png"}
# Kinds whose entries may hold no look by design (a character's motion clips or hand pose, a kit's floor plan): one
# with no file to draw is left off the sheets, listed as skipped; a model, take or place without one is a failure.
LOOKLESS = ("kit", "character")
# A surface painted for one model (surface.json's `tiling` false: its maps cover that model's own UVs once) has no look
# on a sphere: it is left off the surface sheets, listed as skipped, and seen on its model's tile.
ON_ITS_MODEL = "painted for one model: its maps are seen on its model's tile, not on a sphere"
# A recipe surface's palette slots have no token outside a place: the review draws them in plain greys (linear RGB).
REVIEW_GREYS = {"colour": [0.32, 0.32, 0.32], "second": [0.12, 0.12, 0.12], "bare": [0.6, 0.6, 0.6],
                "dirt_colour": [0.2, 0.17, 0.14]}
ACROSS, DOWN = 6, 5
TILE = 250
LABEL = 44
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
STAGING = {
    "model": {"heading": 40, "elevation": 16},
    "kit": {"heading": 35, "elevation": 16},
    "take": {"heading": 40, "elevation": 16},
    "character": {"hide": ["far", "Icosphere"], "action": "walking", "frame": 6, "heading": 200, "elevation": 6,
                  "lens": 85, "margin": 0.95},
    "effect": {"ground": "dark", "heading": -30, "elevation": 10, "margin": 1.2},
}


def current_entries(root):
    """Every entry record of the wanted kinds that is not withdrawn, by kind then address."""
    found = []
    for path in sorted(pathlib.Path(root, "entries").glob("*/*/*/entry.json")):
        record = json.loads(path.read_text())
        if record["kind"] in KINDS and record.get("state") != "withdrawn":
            found.append(record)
    return sorted(found, key=lambda record: (KINDS.index(record["kind"]), record["address"]))


def model_file(record):
    """The file a model is opened by: its USD root, else its glTF, else its final (or only) GLB, else its one USD."""
    files = record["files"]
    root = (record.get("usd") or {}).get("root")
    if root in files:
        return root
    for ending in (".gltf", "-final.glb", ".glb", ".usdc", ".usd", ".usda"):
        named = sorted(file for file in files if file.endswith(ending) and (ending != ".usda" or "/" not in file))
        if named:
            return named[0]
    return None


def shown_file(record):
    """The one file an entry of a 3D kind is drawn from, or None when it holds none (it has no look)."""
    files = record["files"]
    if record["kind"] == "model":
        return model_file(record)
    wanted = {"kit": "piece.usdc", "character": "body.glb"}.get(record["kind"])
    if wanted:
        return wanted if wanted in files else None
    if record["kind"] == "take":
        return next(iter(sorted(file for file in files if file.endswith("-final.glb"))), None)
    return None


def fetch_list(record, files):
    """{file: sha256} of the named files of an entry."""
    return {file: record["files"][file]["sha256"] for file in files}


def shown_item(record):
    """A model, kit piece, character or take as library_sheet.py draws it; a reason when it has no look."""
    main = shown_file(record)
    if main is None:
        return None, f"holds no {record['kind']} file to draw ({', '.join(sorted(record['files']))})"
    files = sorted(record["files"]) if record["kind"] == "model" else [main]
    return {"fetch": fetch_list(record, files), "show": {"files": [main], **STAGING[record["kind"]]}}, None


def local_file(record, file):
    """One file of an entry fetched into this PC's library cache (library_files), or None when the library lacks it."""
    found = library_files.resolve(library_files.reference(record["address"], file))
    return pathlib.Path(found) if found else None


def map_files(maps):
    """A surface record's maps as {colour|normal|orm|roughness|metalness: file}; the record gives either a role table
    (`albedo`, ...) or a list of files named for their role (`colour.jpg`, ...)."""
    roles = {"albedo": "colour", "colour": "colour", "normal": "normal", "orm": "orm", "roughness": "roughness",
             "metalness": "metalness", "metallic": "metalness"}
    pairs = maps.items() if isinstance(maps, dict) else ((pathlib.Path(file).stem, file) for file in maps)
    return {roles[role]: file for role, file in pairs if role in roles}


def recipe_spec(recipe, settings, colours, defaults):
    """A recipe surface as recipes.channels takes it: the recipe's defaults under the entry's settings, its palette
    slots in the review's greys unless the entry gives its own colours."""
    if recipe not in defaults:
        raise ValueError(f"recipe {recipe!r} is not one of data/library/materials.json's")
    return {**defaults[recipe], **settings, **REVIEW_GREYS, **colours, "recipe": recipe}


def surface_item(record, defaults):
    """A surface as library_sheet.py draws it on a sphere (image or constant maps, or a ProcFunc recipe)."""
    files = record["files"]
    if "face.json" in files:
        face = json.loads(local_file(record, "face.json").read_text())
        palette = list((face.get("palette") or {}).values())
        colours = {"colour": face["colour"]}
        if len(palette) > 1:
            colours["second"] = linear(palette[1])
        settings = {"roughness": face["roughness"], "metal": face["metal"]}
        return {"fetch": {}, "surface": {"recipe": recipe_spec(face["recipe"], settings, colours, defaults)}}, None
    if "surface.json" not in files:
        return None, f"holds no surface.json ({', '.join(sorted(files))})"
    surface = json.loads(local_file(record, "surface.json").read_text())
    if surface.get("tiling") is False:
        return None, ON_ITS_MODEL
    if surface.get("recipe"):
        return {"fetch": {}, "surface": {"recipe": recipe_spec(surface["recipe"], surface.get("settings", {}), {},
                                                               defaults)}}, None
    maps = map_files(surface.get("maps") or {})
    missing = sorted(file for file in maps.values() if file not in files)
    if missing:
        return None, f"its surface.json names maps it does not hold: {missing}"
    return {"fetch": fetch_list(record, maps.values()),
            "surface": {"maps": maps, "constants": surface.get("constants") or {},
                        "transmission": surface.get("transmission"), "metre": surface.get("tile_metres") or 1.0}}, None


def linear(hex_colour):
    channels = [int(hex_colour.lstrip("#")[at:at + 2], 16) / 255 for at in (0, 2, 4)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]


def fullest_time(attribute):
    """The clip time whose points attribute holds the most points (a pour's settled heap, a jet in full flow)."""
    times = attribute.GetTimeSamples() or [0.0]
    return max(times, key=lambda time: len(attribute.Get(time) or ()))


def effect_stem(record, work):
    """Where an effect's files for its job are written here (they go up with the job)."""
    folder = work / "effects"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / record["address"].replace("/", "__").replace("@", "_")


def clip_mesh(stage, prim, stem):
    """A baked clip's mesh (the drill's settled pour) at its fullest clip time as a Z-up PLY: Blender's USD reader
    opens an animated mesh at the scene's first frame, where a pour has not begun, so the machine would see no mesh."""
    import numpy
    from pxr import UsdGeom
    import pictures

    mesh = UsdGeom.Mesh(prim)
    time = fullest_time(mesh.GetPointsAttr())
    points = numpy.array(mesh.GetPointsAttr().Get(time), dtype=float)
    world = numpy.array(UsdGeom.XformCache(time).GetLocalToWorldTransform(prim))
    points = pictures.z_up((numpy.c_[points, numpy.ones(len(points))] @ world)[:, :3],
                           UsdGeom.GetStageUpAxis(stage) == "Y")
    counts = numpy.array(mesh.GetFaceVertexCountsAttr().Get(time))
    indices = numpy.array(mesh.GetFaceVertexIndicesAttr().Get(time))
    faces = numpy.split(indices, numpy.cumsum(counts)[:-1])
    path = stem.with_suffix(".ply")
    pictures.write_ply(path, points, [face.tolist() for face in faces])
    return path


def clip_points(stage, cloud, settings, stem):
    """A clip's particles at its fullest clip time, Z-up, as the npz and Points file library_demo.py reads; read in the
    clip's own numbers as the README's picture reads them (pictures.steam_points): a SCORE clip's values are metres
    (it says so since score #156; the versions before said metersPerUnit 0.01 over the same metres), and scaling the
    points by a stated unit and not the widths left a 5 mm cloud inside 5 cm puffs, a blank tile."""
    import numpy
    from pxr import UsdGeom
    import pictures

    time = fullest_time(cloud.GetPointsAttr())
    points = numpy.array(cloud.GetPointsAttr().Get(time), dtype=float)
    points = pictures.z_up(points, UsdGeom.GetStageUpAxis(stage) == "Y")
    widths = numpy.asarray(cloud.GetWidthsAttr().Get(time) or [settings.get("size", 0.02)] * len(points),
                           dtype=numpy.float32)
    if len(widths) == 1:
        widths = numpy.full(len(points), widths[0], dtype=numpy.float32)
    opacity = UsdGeom.PrimvarsAPI(cloud).GetPrimvar("displayOpacity")
    opacity = numpy.asarray(opacity.Get(time) if opacity and opacity.Get(time) is not None else
                            numpy.ones(len(points)), dtype=numpy.float32)
    numpy.savez(stem.with_suffix(".npz"), points=points.astype(numpy.float32), widths=widths, opacity=opacity)
    pictures.points_file(stem.with_suffix(".usda"), points, widths)
    return {"npz": str(stem.with_suffix(".npz")), "usd": str(stem.with_suffix(".usda")),
            "look": settings.get("look", "puff"), "colour": settings.get("colour", [0.9, 0.9, 0.89])}


def effect_item(record, work):
    """An effect drawn from its clip at its fullest clip time, Z-up: its particles in their own look and colour, or a
    baked clip's mesh; the files written here go up with the job (`upload`), so the machine fetches nothing."""
    from pxr import Usd, UsdGeom

    clip_path, settings_path = local_file(record, "clip.usdc"), local_file(record, "settings.json")
    if clip_path is None or settings_path is None:
        return None, "holds no clip.usdc and settings.json"
    settings = json.loads(settings_path.read_text())
    stage = Usd.Stage.Open(str(clip_path))
    stem = effect_stem(record, work)
    cloud = next((UsdGeom.Points(prim) for prim in stage.Traverse() if prim.IsA(UsdGeom.Points)), None)
    mesh = next((prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh)), None)
    if cloud is not None:
        spec = clip_points(stage, cloud, settings, stem)
        show, upload = {"files": [], "points": [spec]}, [spec["npz"], spec["usd"]]
    elif mesh is not None:
        path = clip_mesh(stage, mesh, stem)
        show, upload = {"files": [str(path)]}, [str(path)]
    else:
        show = None
    del stage
    clip_path.unlink()  # 165 MB for the drill's pour: this PC keeps no library bytes it has done with
    if show is None:
        return None, "its clip holds neither particles (a Points prim) nor a mesh"
    return {"fetch": {}, "show": {**show, **STAGING["effect"]}, "upload": upload}, None


def planned(record, work, defaults):
    """(item, None) for an entry library_sheet.py renders, (None, None) for one whose own picture is drawn, (None,
    reason) for one with no look."""
    kind = record["kind"]
    if kind in HELD:
        return None, None if HELD[kind] in record["files"] else f"holds no {HELD[kind]}"
    if kind == "surface":
        return surface_item(record, defaults)
    if kind == "effect":
        return effect_item(record, work)
    return shown_item(record)


def item_bytes(record, item):
    return sum(record["files"][file]["bytes"] for file in item["fetch"])


def spread_jobs(items, count):
    """The items dealt over `count` jobs so each fetches and draws about as long (largest first onto the lightest)."""
    jobs = [{"seconds": 0.0, "items": []} for _ in range(count)]
    for item in sorted(items, key=lambda item: -item["estimate"]):
        lightest = min(jobs, key=lambda job: job["seconds"])
        lightest["items"].append(item)
        lightest["seconds"] += item["estimate"]
    for job in jobs:
        job["items"].sort(key=lambda item: item["name"])
    return [job for job in jobs if job["items"]]


def prepare(work, count):
    """Every entry's plan into <work>/items.json and the cloud jobs into <work>/jobs/; one line."""
    root = library_files.settings()["SCORE_LIB_ROOT"]
    defaults = json.loads(RECIPE_DEFAULTS.read_text())["recipes"]
    plan, rendered = [], []
    for number, record in enumerate(current_entries(root), start=1):
        name = f"{number:04d}"
        row = {"name": name, "address": record["address"], "kind": record["kind"]}
        try:
            item, reason = planned(record, work, defaults)
        except Exception as error:  # an entry whose record cannot be read is a finding, not a stop
            item, reason = None, f"{type(error).__name__}: {error}"
        if item is not None:
            item.update(name=name, address=record["address"],
                        estimate=SECONDS_EACH + item_bytes(record, item) / BYTES_PER_SECOND)
            rendered.append(item)
        elif reason and (record["kind"] in LOOKLESS or reason == ON_ITS_MODEL):
            row["skipped"] = reason
        elif reason:
            row["error"] = reason
        else:
            row["picture"] = HELD[record["kind"]]
        plan.append(row)
    jobs_folder, renders = work / "jobs", work / "renders"
    jobs_folder.mkdir(parents=True, exist_ok=True)
    cloud_jobs = []
    for index, job in enumerate(spread_jobs(rendered, count), start=1):
        listing, out = jobs_folder / f"{index:02d}.list.json", renders / f"{index:02d}"
        listing.write_text(json.dumps({"size": list(REVIEW_SIZE), "samples": REVIEW_SAMPLES, "blobs": BLOBS,
                                       "cache": f"{MACHINE_CACHE}/{index:02d}", "items": job["items"]}, indent=1))
        effects = sorted({path for item in job["items"] for path in item.get("upload", [])})
        cloud_job = {"script": str(INSIDE.relative_to(REPO)), "args": [str(listing), str(out)],
                     "inputs": [str(listing), *effects], "outputs": [str(out)],
                     "minutes": round(job["seconds"] / 60 * 1.5 + 5), "code": RECIPE_CODE}
        path = jobs_folder / f"{index:02d}.json"
        path.write_text(json.dumps(cloud_job, indent=1))
        cloud_jobs.append(path)
        for item in job["items"]:
            next(row for row in plan if row["name"] == item["name"])["job"] = f"{index:02d}"
    (work / "items.json").write_text(json.dumps(plan, indent=1))
    longest = max((json.loads(path.read_text())["minutes"] for path in cloud_jobs), default=0)
    print(f"library sheets: {len(rendered)} to render in {len(cloud_jobs)} jobs (longest about {longest} min), "
          f"{sum('error' in row for row in plan)} failed already, {sum('skipped' in row for row in plan)} with no look; "
          f"{work / 'items.json'}")
    return cloud_jobs


def render(work, who, detach):
    """The prepared jobs on rented cards through blender_cloud.py."""
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import blender_cloud
    jobs = sorted(str(path) for path in (work / "jobs").glob("[0-9][0-9].json"))
    command = [str(blender_cloud.cloud_python()), str(REPO / "tools/cloud/blender_cloud.py"), *jobs, "--who", who,
               "--classes", ",".join(CLASSES)] + (["--detach"] if detach else [])
    raise SystemExit(subprocess.run(command).returncode)


def result_of(row, work):
    """An entry's tile: (picture path or None, error or None), from its render's result or its held picture."""
    if "error" in row:
        return None, row["error"]
    if "picture" in row:
        found = local_file(row, row["picture"])
        return (found, None) if found else (None, f"its {row['picture']} could not be fetched")
    folder = work / "renders" / row["job"]
    result = folder / f"{row['name']}.json"
    if not result.is_file():
        return None, f"no result: job {row['job']} did not return one"
    answer = json.loads(result.read_text())
    if not answer.get("ok"):
        return None, answer.get("error", "failed with no error given")
    return folder / f"{row['name']}.png", None


def tile(picture, address, error, font):
    """One tile: the picture fitted in a square (or the error written there) over its address."""
    from PIL import Image, ImageDraw
    canvas = Image.new("RGB", (TILE, TILE + LABEL), (24, 24, 26))
    draw = ImageDraw.Draw(canvas)
    if picture is not None:
        with Image.open(picture) as shown:
            shown = shown.convert("RGB")
            shown.thumbnail((TILE, TILE))
            canvas.paste(shown, ((TILE - shown.width) // 2, (TILE - shown.height) // 2))
    else:
        draw.rectangle((0, 0, TILE - 1, TILE - 1), fill=(90, 20, 20))
        draw.text((8, 8), "FAILED", fill=(255, 220, 220), font=font)
        draw.multiline_text((8, 30), "\n".join(textwrap.wrap(error, 34)[:12]), fill=(255, 235, 235), font=font)
    lines = textwrap.wrap(address, 36, break_on_hyphens=False)[:3]
    draw.multiline_text((4, TILE + 2), "\n".join(lines), fill=(235, 235, 235), font=font, spacing=1)
    return canvas


def compose(work, out):
    """The sheets of every kind and their index; one line."""
    from PIL import Image, ImageFont
    font = ImageFont.truetype(FONT, 12)
    title_font = ImageFont.truetype(FONT, 20)
    plan = json.loads((work / "items.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    index = {"sheets": {}, "failures": [], "counts": {},
             "skipped": [{"address": row["address"], "why": row["skipped"]} for row in plan if "skipped" in row]}
    for kind in KINDS:
        rows = [row for row in plan if row["kind"] == kind and "skipped" not in row]
        per_sheet = ACROSS * DOWN
        sheets = []
        for start in range(0, len(rows), per_sheet):
            number = start // per_sheet + 1
            target = out / kind / f"{number:02d}.jpg"
            target.parent.mkdir(parents=True, exist_ok=True)
            sheet = Image.new("RGB", (ACROSS * TILE, 32 + DOWN * (TILE + LABEL)), (10, 10, 12))
            title(sheet, f"{kind}  sheet {number:02d}  ({start + 1}-{min(start + per_sheet, len(rows))} "
                                   f"of {len(rows)})", title_font)
            tiles = []
            for position, row in enumerate(rows[start:start + per_sheet]):
                picture, error = result_of(row, work)
                across, down = position % ACROSS, position // ACROSS
                sheet.paste(tile(picture, row["address"], error, font), (across * TILE, 32 + down * (TILE + LABEL)))
                if "picture" in row and picture is not None:
                    picture.unlink()  # a held picture fetched into this PC's library cache: its tile is all we keep
                tiles.append({"tile": position + 1, "row": down + 1, "column": across + 1, "address": row["address"],
                              "ok": error is None, **({"error": error} if error else {})})
                if error:
                    index["failures"].append({"address": row["address"], "sheet": f"{kind}/{number:02d}.jpg",
                                              "tile": position + 1, "error": error})
            sheet.save(target, quality=88)
            sheets.append({"sheet": f"{kind}/{number:02d}.jpg", "tiles": tiles})
        index["sheets"][kind] = sheets
        index["counts"][kind] = {"entries": len(rows),
                                 "drawn": sum(placed["ok"] for sheet in sheets for placed in sheet["tiles"])}
    (out / "index.json").write_text(json.dumps(index, indent=1))
    drawn = sum(count["drawn"] for count in index["counts"].values())
    print(f"library sheets: {drawn} drawn, {len(index['failures'])} failed, "
          f"{sum(len(sheets) for sheets in index['sheets'].values())} sheets in {out}; {out / 'index.json'}")
    return index


def title(sheet, text, font):
    from PIL import ImageDraw
    ImageDraw.Draw(sheet).text((8, 4), text, fill=(240, 240, 240), font=font)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=("prepare", "render", "compose"))
    parser.add_argument("--work", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--jobs", type=int, default=JOBS)
    parser.add_argument("--who", default="library review sheets")
    parser.add_argument("--detach", action="store_true")
    given = parser.parse_args()
    work = given.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if given.step == "prepare":
        prepare(work, given.jobs)
    elif given.step == "render":
        render(work, given.who, given.detach)
    else:
        if given.out is None:
            raise SystemExit("compose needs --out")
        compose(work, given.out.resolve())


if __name__ == "__main__":
    main()
