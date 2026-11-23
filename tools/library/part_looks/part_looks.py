"""The October 2026 code-built library models remade part by part in library surfaces (the atlas fix, 2026-11-23).

Those models (provenance `framework_models`, route code, score 4547b8c54) were baked into one shared picture set with
every face toward the kit's back at a twentieth of the texel density (bake.py's shrink_hidden), so on 1,137 of them a
median 37% of the surface draws the atlas's unpainted black. Their geometry is right; their finish is not. Each is
made again as its next version:

- its geometry kept exactly (the entry's `model.usdc`, and `model_glow.usdc` where it has one: points, faces,
  normals and collision hull as they are), the shared atlas's material, maps and texture coordinates taken off;
- every face told which part of its old builder it is: the builder at the models' commit (`OLD_COMMIT`, read with
  `git archive`) built again in Blender (rebuild.py), its size fitted to the model's box, and its triangles taken in
  the order the old join laid them (the glowing parts' into the glow file), each checked to lie within TOLERANCE of
  the model's triangle in the same place; an entry where any does not is refused, never guessed;
- each part a GeomSubset (`materialBind`) bound to a look of the library surface its builder named
  (map/parts.json, recovered by `recover`): the library's recipe entry (`score:surface`, surface/<recipe>@<newest>)
  in the variant's own settings and the colour of its token in its place, as the old library at OLD_COMMIT resolved it
  (`score:recipe:spec`, `score:surface:colour`, its variant in `score:surface:variant`), the preview surface set from
  it as place_build's palette looks are (place_build.recipe_marked), so place_build and the game's piece lists read
  per-part palette looks and no picture is shared.

    part_looks.py make <address> ... [--list FILE] --into DIR [--previews DIR]
    part_looks.py recover

`make` writes DIR/made/<id>/ (the files), DIR/listing.json (a `score-lib take-in` list, each entry its next version),
DIR/replaced.json ([{old, new}], for `score-lib withdraw <old> --replaced-by <new>`), DIR/report.json (per entry:
made or refused, and why) and, with --previews, `<id>-before.png` and `<id>-after.png` drawn per pixel by the
library's own preview (score_lib.preview.mesh, run as its own process); it prints one line. `--list FILE` reads
addresses one a line (`#` starts a note). `recover` builds every builder at OLD_COMMIT at a size its rooms laid it at
and writes map/parts.json. Blender runs once a call (tools/blender/session.py batch, its lock and watchdog).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/library"))
import library_files  # noqa: E402
from score.stages import place_build  # noqa: E402

OLD_COMMIT = "4547b8c549eccfad6c9df83965fb452bead83560"  # the score commit the code-built models were made at
MAKER = "framework_models"  # their provenance's maker
MAP = HERE / "map" / "parts.json"
REBUILD = HERE / "rebuild.py"
BLENDER = "5.2.2"
TOLERANCE = 1e-4  # metres a model's triangle middle may lie from its twin built again
GLOWING_FAMILIES = ("screen", "light")  # the old library's families split into a glow file (build_only.GLOWING)
FILES = ("model.usdc", "model_glow.usdc")
RECORD = "model.json"
OLD_FILES = ("tools/props/library", "data/library/materials.json", "data/definitions/place.json",
             "design/tokens/tokens.json", "data/kit")
NOT_IN_SPEC = ("reference",)  # the old variant's words about the picture it was matched to, no part of the finish
DEFAULT_SIZE = (0.5, 0.5, 0.5)  # a builder no room laid at OLD_COMMIT is listed at this size
PREVIEW_SIZE = 640
STEP = ("remade part by part in library surfaces by score's part_looks (tools/library/part_looks): its geometry "
        "kept, each part of its old code builder (score {old}) bound to the library recipe its builder named, in the "
        "colour and settings the old library gave it in its place; the shared atlas (every face toward the kit's back "
        "at a twentieth of the texel density) taken off (score {commit})")


class Refused(ValueError):
    """An entry this tool cannot remake as it stands, in words."""


# --- the old builders and library ---------------------------------------------------------------------------------

def old_tree(into):
    """The builders, library and rooms at OLD_COMMIT unpacked under `into`; its path."""
    archive = subprocess.run(["git", "-C", str(REPO), "archive", OLD_COMMIT, *OLD_FILES], capture_output=True,
                             check=True)
    subprocess.run(["tar", "-x", "-C", str(into)], input=archive.stdout, check=True)
    return pathlib.Path(into)


def old_library(tree):
    """The old library module (tools/props/library/library.py at OLD_COMMIT), its paths in `tree`."""
    import importlib.util
    found = importlib.util.spec_from_file_location("old_library", tree / "tools/props/library/library.py")
    module = importlib.util.module_from_spec(found)
    found.loader.exec_module(module)
    return module


def token_hex(tree, token):
    """A token's '#rrggbb' in the game's look (`ops`), as the old library read it."""
    for entry in json.loads((tree / "design/tokens/tokens.json").read_text())["color"]["tokens"]:
        if entry["name"] == token:
            return entry["value"]["ops"] if isinstance(entry["value"], dict) else entry["value"]
    raise Refused(f"token {token} is not in the old palette")


def variant_spec(library, tree, place, variant):
    """The old library's finish of `variant` in `place` (by_library: the place's token where it names one), with
    its token's hex and the place's wear and dirt; Refused for a variant that needs a picture the library lacks."""
    found = library.by_library(place).get(variant)
    if found is None:
        raise Refused(f"surface {variant} is not in the old library")
    if "picture" in found:
        raise Refused(f"surface {variant} prints the old picture {found['picture']}, which the library does not hold")
    wear, dirt = library.wear_of(place)
    spec = {key: value for key, value in found.items() if key not in NOT_IN_SPEC}
    return dict(spec, hex=token_hex(tree, found["token"]), wear=wear, dirt=dirt)


def glowing(library, surface):
    return library.variants(library.theme_library()).get(surface, {}).get("family") in GLOWING_FAMILIES


# --- Blender ------------------------------------------------------------------------------------------------------

def rebuilt(tree, jobs, scratch):
    """rebuild.py's answers to `jobs`, one Blender for all."""
    asked, answers = scratch / "jobs.json", scratch / "answers.json"
    asked.write_text(json.dumps(jobs))
    log = scratch / "blender.log"
    with open(log, "w") as stream:
        done = subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch", "--version", BLENDER,
                               str(REBUILD), "--", str(tree / "tools/props/library/inside"), str(asked),
                               str(answers)], stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    if done.returncode != 0 or not answers.is_file():
        raise SystemExit(f"Blender exited {done.returncode}: see {log}")
    return {answer["name"]: answer for answer in json.loads(answers.read_text())}


# --- recover: the map -----------------------------------------------------------------------------------------------

def laid_first(tree):
    """{builder: (size, laid)} as the rooms at OLD_COMMIT laid each kind first (data/kit/<room>.json)."""
    found = {}
    for path in sorted((tree / "data/kit").glob("*.json")):
        room = json.loads(path.read_text())
        for piece in room.get("pieces", []):
            builder = builder_of(piece.get("kind", ""), room.get("room", ""))
            if "size" in piece and "part" not in piece:
                found.setdefault(builder, (piece["size"], piece.get("laid", {})))
    return found


def recover():
    """map/parts.json written from every builder at OLD_COMMIT; one line."""
    with tempfile.TemporaryDirectory(prefix="part-looks-") as scratch:
        scratch = pathlib.Path(scratch)
        tree = old_tree(scratch)
        laid = laid_first(tree)
        names = rebuilt(tree, [{"name": "*", "kind": "*"}], scratch)["*"]["builders"]
        jobs = [{"name": name, "kind": name, "size": laid.get(name, (DEFAULT_SIZE, {}))[0],
                 "laid": laid.get(name, (DEFAULT_SIZE, {}))[1]} for name in names]
        answers = rebuilt(tree, jobs, scratch)
    built = {name: answer["parts"] for name, answer in answers.items() if "parts" in answer}
    failed = {name: answer["error"] for name, answer in answers.items() if "error" in answer}
    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps({"commit": OLD_COMMIT, "made_by": "tools/library/part_looks/part_looks.py recover",
                               "how": "each builder built at the size and layout its room first laid it (data/kit), "
                                      f"else {list(DEFAULT_SIZE)}; its parts as [part, library surface]",
                               "builders": dict(sorted(built.items())), "not_built": dict(sorted(failed.items()))},
                              indent=1) + "\n")
    print(f"part_looks recover: {len(built)} builders mapped, {len(failed)} not built; {MAP}")


# --- make -----------------------------------------------------------------------------------------------------------

def builder_of(kind, place):
    """The builder a model's kind names: the kind without its room's prefix (build_only: kind.split('_', 1)[1])."""
    if place and kind.startswith(place + "_"):
        return kind[len(place) + 1:]
    return kind.split("_", 1)[1] if "_" in kind else kind


def file_path(address, name):
    found = library_files.resolve(library_files.reference(address, name))
    if found is None:
        raise Refused(f"{address}/{name}: the library holds no such file")
    return found


def entry_record(address):
    kind, rest = address.split("/", 1)
    entry_id, version = rest.split("@")
    record = library_files.entry_record(library_files.settings()["SCORE_LIB_ROOT"],
                                        {"kind": kind, "id": entry_id, "version": version})
    if record is None:
        raise Refused(f"{address}: the library holds no such entry")
    return record


def checked_record(address):
    """The entry's record and model record; Refused for one this tool does not remake."""
    record = entry_record(address)
    if record["kind"] != "model":
        raise Refused(f"{address} is a {record['kind']}, not a model")
    provenance = record.get("provenance", {})
    if MAKER not in [step.get("by") for step in provenance.get("made_with", [])]:
        raise Refused(f"{address} was not made by {MAKER}")
    if provenance.get("commit") != OLD_COMMIT:
        raise Refused(f"{address} was made at score {provenance.get('commit')}, not {OLD_COMMIT[:9]}")
    newer = newer_in_force(record)
    if newer:
        raise Refused(f"{address} is remade already as {newer}: build on that, or withdraw it first")
    model = json.loads(file_path(address, RECORD).read_text())
    if (model.get("kit") or {}).get("route") != "code":
        raise Refused(f"{address} is no code build (its kit route is {(model.get('kit') or {}).get('route')})")
    return record, model


def mesh_of(stage):
    """The stage's shown mesh (`<default prim>/geo`)."""
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(stage.GetDefaultPrim().GetPath().AppendChild("geo")))
    if not mesh:
        raise Refused(f"{stage.GetRootLayer().identifier}: no geo mesh under its default prim")
    return mesh


def triangle_middles(mesh):
    """Each face's middle; Refused for a mesh not all triangles (the bake wrote triangles, one a face)."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    counts = np.array(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    indices = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
    if not (counts == 3).all():
        raise Refused(f"{mesh.GetPath()}: faces of {sorted(set(counts.tolist()) - {3})} corners, not the bake's "
                      "triangles")
    return points[indices.reshape(-1, 3)].mean(axis=1)


def job_of(name, builder, laid, stages):
    """rebuild.py's job for one model: its files' box together."""
    every = np.vstack([np.array(mesh_of(stage).GetPointsAttr().Get(), dtype=np.float64) for stage in stages])
    return {"name": name, "kind": builder, "laid": laid,
            "box": [every.min(axis=0).tolist(), every.max(axis=0).tolist()]}


def parts_by_order(answer, counts, glows, points):
    """Each file's triangles' part index: the built triangles in the old join's order, the glowing parts' after the
    rest (into the glow file, as the old bake split them), each checked within TOLERANCE of the model's; Refused
    when the counts or any triangle differ."""
    order = np.array(answer["order"], dtype=np.int64)
    middles = np.array(answer["middles"], dtype=np.float64)
    shining = np.isin(order, [index for index, (_, surface) in enumerate(answer["parts"]) if glows(surface)])
    built = [int((~shining).sum()), int(shining.sum())]
    if built != (list(counts) + [0])[:2]:
        raise Refused(f"built again it has {built[0]} triangles and {built[1]} glowing, the model's files "
                      f"{list(counts)}")
    sequence = np.concatenate([np.flatnonzero(~shining), np.flatnonzero(shining)])
    off = np.linalg.norm(middles[sequence] - np.asarray(points), axis=1)
    if off.max() > TOLERANCE:
        raise Refused(f"built again, {int((off > TOLERANCE).sum())} of its {len(off)} triangles lie off the model's "
                      f"(the farthest {off.max() * 1000:.2f} mm; {TOLERANCE * 1000:.1f} mm allowed)")
    taken = order[sequence]
    return [taken[:counts[0]], *([taken[counts[0]:]] if len(counts) > 1 else [])], float(off.max())


def looks_written(stage, root, parts, used, specs, surfaces):
    """`<root>/Looks/<variant>` for every variant the parts `used` name: a preview surface in the variant's colour,
    its recipe's spec, library surface, colour and variant marked on it; {variant: material}."""
    looks = {}
    UsdGeom.Scope.Define(stage, root.AppendChild("Looks"))
    for variant in sorted({parts[index][1] for index in used}):
        spec = specs[variant]
        material = UsdShade.Material.Define(stage, root.AppendPath(f"Looks/{variant}"))
        shader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("surface"))
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*spec["colour"]))
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        place_build.recipe_marked(material, spec)
        prim = material.GetPrim()
        prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(surfaces[spec["recipe"]])
        prim.CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(spec["hex"])
        prim.CreateAttribute("score:surface:variant", Sdf.ValueTypeNames.String).Set(variant)
        looks[variant] = material
    return looks


def subset_name(parts, index):
    """A part's subset name: its part, with its surface after it when the builder names that part in two surfaces."""
    part, surface = parts[index]
    return part if sum(1 for other, _ in parts if other == part) == 1 else f"{part}_{surface}"


def refinished(stage, parts, faces, specs, surfaces):
    """The stage made over: its baked look and texture coordinates off, a materialBind subset a part bound to its
    variant's look; [{part, variant, surface, faces}]."""
    root = stage.GetDefaultPrim().GetPath()
    mesh = mesh_of(stage)
    stage.RemovePrim(root.AppendChild("Looks"))
    UsdShade.MaterialBindingAPI(mesh.GetPrim()).UnbindAllBindings()
    UsdGeom.PrimvarsAPI(mesh.GetPrim()).RemovePrimvar("st")
    used = sorted(set(faces.tolist()))
    looks = looks_written(stage, root, parts, used, specs, surfaces)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    listed = []
    for index in used:
        chosen = np.flatnonzero(faces == index)
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, subset_name(parts, index), UsdGeom.Tokens.face,
                                                 [int(face) for face in chosen], UsdShade.Tokens.materialBind,
                                                 UsdGeom.Tokens.partition)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(looks[parts[index][1]])
        listed.append({"part": subset_name(parts, index), "variant": parts[index][1],
                       "surface": surfaces[specs[parts[index][1]]["recipe"]], "faces": int(len(chosen))})
    return listed


def newest_surfaces(specs):
    """{recipe: the library's newest in-force surface of it} for every recipe the specs name."""
    found = {}
    for spec in specs.values():
        if spec["recipe"] not in found:
            try:
                found[spec["recipe"]] = place_build.resolved_address(f"surface/{spec['recipe']}",
                                                                     place_build.library_root())
            except place_build.Refused as why:
                raise Refused(f"recipe {spec['recipe']}: {why}") from why
            if place_build.entry_of(found[spec["recipe"]]).get("state") == "withdrawn":
                raise Refused(f"recipe {spec['recipe']}: the library holds it only withdrawn")
    return found


def mapped_parts(builder, parts):
    """Refused unless every part the builder made again is one map/parts.json lists for it."""
    listed = json.loads(MAP.read_text())["builders"].get(builder)
    if listed is None:
        raise Refused(f"builder {builder} is not in {MAP.name} (run recover)")
    strays = [part for part in parts if part not in listed]
    if strays:
        raise Refused(f"builder {builder} built {strays}, which {MAP.name} does not list for it")


def newer_in_force(record):
    """The address of a later version of the entry that is not withdrawn (another job's remake), or None."""
    folder = pathlib.Path(library_files.settings()["SCORE_LIB_ROOT"]) / "entries" / record["kind"] / record["id"]
    for path in sorted((path for path in folder.iterdir() if path.name.isdigit()), key=lambda path: int(path.name)):
        later = json.loads((path / "entry.json").read_text())
        if int(path.name) > record["version"] and later.get("state") != "withdrawn":
            return later["address"]
    return None


def next_version(record):
    """The version a take-in gives this entry's id next."""
    folder = pathlib.Path(library_files.settings()["SCORE_LIB_ROOT"]) / "entries" / record["kind"] / record["id"]
    return max(int(path.name) for path in folder.iterdir() if path.name.isdigit()) + 1


def remade(address, record, model, answer, library, tree, into):
    """One entry's files made over in `into`: (the take-in list's entry, its parts)."""
    if "error" in answer:
        raise Refused(f"its builder failed at OLD_COMMIT: {answer['error']}")
    held = [name for name in FILES if name in record["files"]]
    stages = [Usd.Stage.Open(str(file_path(address, name))) for name in held]
    counts = [len(mesh_of(stage).GetFaceVertexCountsAttr().Get()) for stage in stages]
    points = np.vstack([triangle_middles(mesh_of(stage)) for stage in stages])
    parts = [tuple(part) for part in answer["parts"]]
    builder = builder_of(model["kind"], record["provenance"].get("place", ""))
    mapped_parts(builder, [list(part) for part in parts])
    by_file, farthest = parts_by_order(answer, counts, lambda surface: glowing(library, surface), points)
    place = record["provenance"]["place"]
    specs = {surface: variant_spec(library, tree, place, surface) for _, surface in parts}
    surfaces = newest_surfaces(specs)
    into.mkdir(parents=True, exist_ok=True)
    listed = []
    for name, stage, faces in zip(held, stages, by_file):
        listed += [dict(part, file=name) for part in refinished(stage, parts, faces, specs, surfaces)]
        stage.GetRootLayer().Export(str(into / name))
    (into / RECORD).write_text(json.dumps(dict(model, parts=listed), indent=2, sort_keys=True) + "\n")
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    files = {name: {"path": str(into / name), "from": f"{address}/{name}, remade"} for name in held}
    files[RECORD] = {"path": str(into / RECORD), "from": f"{address}/{RECORD}, with its parts"}
    entry = {"kind": "model", "id": record["id"], "title": record["title"], "files": files,
             "made_with": [{"what": STEP.format(old=OLD_COMMIT[:9], commit=commit[:9]), "source": "score"}],
             "tags": record.get("tags", {}), "usd": record.get("usd"), "requires": sorted(surfaces.values())}
    return entry, {"parts": listed, "farthest_mm": round(farthest * 1000, 6), "size": answer["size"]}


def addresses_of(arguments):
    found = list(arguments.address)
    if arguments.list:
        for line in pathlib.Path(arguments.list).read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                found.append(line)
    if not found:
        raise SystemExit("give addresses (model/<id>@<version>) or --list FILE")
    return list(dict.fromkeys(found))


def previewed(address, record, folder, previews, when):
    """The library's own per-pixel preview (score_lib.preview.mesh, its own process) of the model's files together,
    as `<id>-<when>.png` in `previews`."""
    held = [name for name in FILES if name in record["files"]]
    paths = [str(folder / name) if folder else str(file_path(address, name)) for name in held]
    with tempfile.TemporaryDirectory(prefix="part-looks-preview-") as scratch:
        together = pathlib.Path(scratch) / "together.usda"
        layer = Sdf.Layer.CreateNew(str(together))
        layer.subLayerPaths = paths
        layer.Save()
        python = pathlib.Path(library_files.settings().get("SCORE_LIB_COMMAND", "")).parent / "python"
        target = pathlib.Path(previews) / f"{record['id']}-{when}.png"
        subprocess.run([str(python), "-c", "import sys; from score_lib.preview import mesh; "
                        "mesh.render(sys.argv[1], sys.argv[2], int(sys.argv[3]))", str(together), str(target),
                        str(PREVIEW_SIZE)], check=True, capture_output=True)
    return str(target)


def make(arguments):
    """Every address remade into --into; one line."""
    into = pathlib.Path(arguments.into)
    into.mkdir(parents=True, exist_ok=True)
    report, entries, replaced, jobs, held = {}, [], [], [], {}
    with tempfile.TemporaryDirectory(prefix="part-looks-") as scratch:
        scratch = pathlib.Path(scratch)
        tree = old_tree(scratch)
        library = old_library(tree)
        for address in addresses_of(arguments):
            try:
                record, model = checked_record(address)
                stages = [Usd.Stage.Open(str(file_path(address, name))) for name in FILES if name in record["files"]]
                jobs.append(job_of(address, builder_of(model["kind"], record["provenance"].get("place", "")),
                                   model.get("laid", {}), stages))
                held[address] = (record, model)
            except (Refused, library_files.LibraryUnreachable) as why:
                report[address] = {"refused": str(why)}
        answers = rebuilt(tree, jobs, scratch) if jobs else {}
        for address, (record, model) in held.items():
            try:
                entry, found = remade(address, record, model, answers[address], library, tree,
                                      into / "made" / record["id"])
            except Refused as why:
                report[address] = {"refused": str(why)}
                continue
            entries.append(entry)
            new = f"model/{record['id']}@{next_version(record)}"
            replaced.append({"old": address, "new": new})
            report[address] = dict(found, made=new)
            if arguments.previews:
                report[address]["previews"] = [previewed(address, record, None, arguments.previews, "before"),
                                               previewed(address, record, into / "made" / record["id"],
                                                         arguments.previews, "after")]
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    (into / "listing.json").write_text(json.dumps({
        "world": "world1", "commit": commit, "entries": entries,
        "taken_from": "score's part_looks: the October 2026 code-built models remade part by part in library "
                      "surfaces, the shared atlas off"}, indent=1) + "\n")
    (into / "replaced.json").write_text(json.dumps(replaced, indent=1) + "\n")
    (into / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    refused = sum(1 for found in report.values() if "refused" in found)
    print(f"part_looks make: {len(entries)} remade, {refused} refused; {into / 'report.json'}, "
          f"{into / 'listing.json'}")


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    actions = parser.add_subparsers(dest="action", required=True)
    making = actions.add_parser("make", help="remake library models part by part in library surfaces")
    making.add_argument("address", nargs="*")
    making.add_argument("--list", help="a file of addresses, one a line")
    making.add_argument("--into", required=True)
    making.add_argument("--previews", help="a folder for <id>-before.png and <id>-after.png")
    actions.add_parser("recover", help="write map/parts.json from every builder at the models' commit")
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse(argv)
    if arguments.action == "recover":
        recover()
    else:
        make(arguments)


if __name__ == "__main__":
    main()
