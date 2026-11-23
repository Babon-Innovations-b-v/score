"""The October 2026 code-built library models remade part by part in library surfaces (the atlas fix, 2026-11-23).

Those models (provenance `framework_models`, route code, score 4547b8c54) were baked into one shared picture set with
every face toward the kit's back at a twentieth of the texel density (bake.py's shrink_hidden), so on 1,137 of them a
median 37% of the surface draws the atlas's unpainted black. Their geometry is right; their finish is not. Each is
made again as its next version:

- its geometry kept exactly (the entry's `model.usdc`, and `model_glow.usdc` where it has one: points, faces,
  normals and collision hull as they are), the shared atlas's material, maps and texture coordinates taken off;
- every face told which part of its old builder it is: the builder at the models' commit (`OLD_COMMIT`, read with
  `git archive`) built again in Blender (rebuild.py), its size fitted to the model's box, and its triangles taken in
  the order the old join laid them (the glowing parts' into the glow file), each of the model's checked to lie on the
  corners of the face built in its place and the face's triangles to cover it, within TOLERANCE (how a face of more
  than three corners is cut into triangles is Blender's choice, and the old export cut some otherwise); an entry
  where any does not is refused, never guessed;
- each part a GeomSubset (`materialBind`) bound to a look of the library surface its builder named
  (map/parts.json, recovered by `recover`): the library's recipe entry (`score:surface`, surface/<recipe>@<newest>)
  in the variant's own settings and the colour of its token in its place, as the old library at OLD_COMMIT resolved it
  (`score:recipe:spec`, `score:surface:colour`, its variant in `score:surface:variant`), the preview surface set from
  it as place_build's palette looks are (place_build.recipe_marked), so place_build and the game's piece lists read
  per-part palette looks and no picture is shared.

    part_looks.py make <address> ... [--list FILE] --into DIR [--previews DIR]
    part_looks.py recover
    part_looks.py decals <report.json> ... --into DIR

`make` writes DIR/made/<id>/ (the files), DIR/listing.json (a `score-lib take-in` list, each entry its next version),
DIR/replaced.json ([{old, new}], for `score-lib withdraw <old> --replaced-by <new>`), DIR/report.json (per entry:
made or refused, and why) and, with --previews, `<id>-before.png` and `<id>-after.png` drawn per pixel by the
library's own preview (score_lib.preview.mesh, run as its own process); it prints one line. `--list FILE` reads
addresses one a line (`#` starts a note). `recover` builds every builder at OLD_COMMIT with every laid its rooms made
it with and writes map/parts.json. `decals` lists the old pictures make's reports wanted (NoDecal) as library decals,
DIR/decals.json for `score-lib take-in`, each at the widest size a remade part prints it. Blender runs once a call
(tools/blender/session.py batch, its lock and watchdog).

An entry whose old build cannot be recovered is finished from its atlas regions instead (regions_remade, below).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
import scipy.sparse
import scipy.sparse.csgraph
import scipy.spatial
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
TOLERANCE = 1e-4  # metres a model's triangle corner may lie from its face's built again
SAME_CORNER = 1e-6  # metres apart two built faces' corners are one corner (Blender's float rounding, two faces apart)
GLOWING_FAMILIES = ("screen", "light")  # the old library's families split into a glow file (build_only.GLOWING)
FILES = ("model.usdc", "model_glow.usdc")
RECORD = "model.json"
OLD_FILES = ("tools/props/library", "data/library/materials.json", "data/library/pictures",
             "data/definitions/place.json", "data/surfaces",
             "design/tokens/tokens.json", "data/kit")
NOT_IN_SPEC = ("reference",)  # the old variant's words about the picture it was matched to, no part of the finish
DEFAULT_SIZE = (0.5, 0.5, 0.5)  # a builder no room laid at OLD_COMMIT is listed at this size
PREVIEW_SIZE = 640
DECAL = "decal.png"  # a library decal's picture (score_lib decals.py)
MAPPED = 1e-12  # least picture area (twice over) of a part's largest triangle for its builder to have mapped it
STEP = ("remade part by part in library surfaces by score's part_looks (tools/library/part_looks): its geometry "
        "kept, each part of its old code builder (score {old}) bound to the library recipe its builder named, in the "
        "colour and settings the old library gave it in its place; the shared atlas (every face toward the kit's back "
        "at a twentieth of the texel density) taken off (score {commit})")


REGIONS_STEP = ("remade in library surfaces by score's part_looks (tools/library/part_looks) from its atlas regions: "
                "its old code build could not be recovered, so its geometry was kept, its faces split by the UV "
                "island of the shared atlas they lie in and each island worn in its room's library surface whose "
                "recipe colour is nearest the island's painted colour (score {old}); the shared atlas taken off "
                "(score {commit})")


class Refused(ValueError):
    """An entry this tool cannot remake as it stands, in words."""


class Unrecovered(Refused):
    """An entry whose old code build cannot be recovered (no code build, a builder that fails at OLD_COMMIT, parts
    the map does not list, or a build its triangles do not match): finished from its atlas regions instead."""


class NoDecal(Refused):
    """An entry printing an old picture the library holds no decal of; `wanted`: {picture: [wide, tall] metres, as
    the entry's part prints it}, for `decals` to take in."""

    def __init__(self, words, wanted):
        super().__init__(words)
        self.wanted = wanted


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


def library_place(tree, place):
    """The id the old library knew a place by, its models finished in: the place's surface data's `library`
    (data/surfaces/<place>.json at OLD_COMMIT: the flat is prologue_flat, the camp expedition_camp, the hangar's roof
    leaves hdoor the hangar); Refused for a place with no surface data."""
    path = tree / "data/surfaces" / f"{place}.json"
    if not path.is_file():
        raise Refused(f"place {place} has no surface data at OLD_COMMIT (data/surfaces), so its library place is "
                      "unknown")
    return json.loads(path.read_text())["library"]


def variant_spec(library, tree, place, variant):
    """The old library's finish of `variant` in `place` (by_library: the place's token where it names one), with
    its token's hex and the place's wear and dirt, and for a variant that prints a picture the library decal of it
    (`decal`, None when the library holds none: decal_of)."""
    found = library.by_library(place).get(variant)
    if found is None:
        raise Refused(f"surface {variant} is not in the old library")
    wear, dirt = library.wear_of(place)
    spec = {key: value for key, value in found.items() if key not in NOT_IN_SPEC}
    spec = dict(spec, hex=token_hex(tree, found["token"]), wear=wear, dirt=dirt)
    if "picture" in found:
        spec["decal"] = decal_of(found["picture"])
    return spec


def decal_of(picture):
    """The library's decal of an old picture in force (surface/<picture>, family decal, taken in by `decals`), or
    None."""
    try:
        address = place_build.resolved_address(f"surface/{picture}", place_build.library_root())
        entry = place_build.entry_of(address)
    except place_build.Refused:
        return None
    if entry.get("state") == "withdrawn" or "decal" not in entry.get("tags", {}).get("family", []):
        return None
    return address


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

# What a laid piece shows that its code-built model is made with (route.SHOWN at OLD_COMMIT): the kit rooms write it
# on the piece itself, beside its place; a composite's child carries it under `shows`.
SHOWN = ("taper", "treads", "openings", "arc", "material", "print", "frame", "dado", "rises_to", "label", "weather")
DOOR_LABELS = {0: "label_south_hatch", 90: "label_west_hatch", 180: "label_north_hatch", 270: "label_east_hatch",
               330: "label_airlock"}  # route.DOOR_LABELS at OLD_COMMIT: the hub's hatch surround's label by its wall


def shows(kind, piece):
    """What a room's piece shows that its model was made with, as route.shows read it at OLD_COMMIT (the plan's
    model `laid`)."""
    found = {key: piece[key] for key in SHOWN if key in piece}
    found.update(piece.get("shows", {}))
    if kind == "hub_hatch_wall_surround":
        back = np.asarray(piece["z"], dtype=np.float64)
        found["label"] = DOOR_LABELS[round(float(np.degrees(np.arctan2(back[0], -back[2]))) % 360)]
    return found


def room_pieces(tree, place):
    """The pieces the room `place` laid at OLD_COMMIT (data/kit/<place>.json), or [] for a place with no kit room."""
    path = tree / "data/kit" / f"{place}.json"
    return json.loads(path.read_text()).get("pieces", []) if path.is_file() else []


def laid_of(tree, place, stem):
    """The laid values its room made the model `stem` with (each piece the plan named it laid them alike); None when
    the room laid no piece as it."""
    for piece in room_pieces(tree, place):
        if piece.get("model") == stem:
            return shows(piece["kind"], piece)
    return None


def laid_every(tree):
    """{builder: [(size, laid)]} of every distinct laid each kind was made with in the rooms at OLD_COMMIT
    (data/kit/<room>.json), its first size with each, and none at its first size."""
    found = {}
    for path in sorted((tree / "data/kit").glob("*.json")):
        room = json.loads(path.read_text())
        for piece in room.get("pieces", []):
            if "size" not in piece or "part" in piece:
                continue
            builder = builder_of(piece.get("kind", ""), room.get("room", ""))
            laid = shows(piece["kind"], piece)
            if all(laid != other for _, other in found.get(builder, [])):
                found.setdefault(builder, []).append((piece["size"], laid))
    for builder, made in found.items():  # and as built showing nothing, as a remake with no laid builds it
        if all(other for _, other in made):
            made.append((made[0][0], {}))
    return found


def recover():
    """map/parts.json written from every builder at OLD_COMMIT, each built with every laid its rooms made it with (a
    builder's parts follow what it shows: a material, an arc, openings); one line."""
    with tempfile.TemporaryDirectory(prefix="part-looks-") as scratch:
        scratch = pathlib.Path(scratch)
        tree = old_tree(scratch)
        laid = laid_every(tree)
        names = rebuilt(tree, [{"name": "*", "kind": "*"}], scratch)["*"]["builders"]
        jobs = [{"name": f"{name}#{serial}", "kind": name, "size": size, "laid": shown}
                for name in names for serial, (size, shown) in enumerate(laid.get(name, [(DEFAULT_SIZE, {})]))]
        answers = rebuilt(tree, jobs, scratch)
    built, failed = {}, {}
    for job in jobs:
        answer = answers[job["name"]]
        if "parts" in answer:
            listed = built.setdefault(job["kind"], [])
            listed += [part for part in answer["parts"] if part not in listed]
        else:
            failed.setdefault(job["kind"], answer["error"])
    failed = {name: why for name, why in failed.items() if name not in built}
    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps({"commit": OLD_COMMIT, "made_by": "tools/library/part_looks/part_looks.py recover",
                               "how": "each builder built with every laid its rooms made it with (data/kit, "
                                      f"route.shows), else {list(DEFAULT_SIZE)} and none; its parts as [part, "
                                      "library surface]",
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
        raise Unrecovered(f"{address} is no code build (its kit route is {(model.get('kit') or {}).get('route')})")
    return record, model


def mesh_of(stage):
    """The stage's shown mesh (`<default prim>/geo`)."""
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(stage.GetDefaultPrim().GetPath().AppendChild("geo")))
    if not mesh:
        raise Refused(f"{stage.GetRootLayer().identifier}: no geo mesh under its default prim")
    return mesh


def triangle_corners(mesh):
    """Each face's three corners; Refused for a mesh not all triangles (the bake wrote triangles, one a face)."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    counts = np.array(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    indices = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
    if not (counts == 3).all():
        raise Refused(f"{mesh.GetPath()}: faces of {sorted(set(counts.tolist()) - {3})} corners, not the bake's "
                      "triangles")
    return points[indices.reshape(-1, 3)]


def laid_made_with(tree, record, model):
    """The laid values the model was made with: its record's, else what its room laid it showing at OLD_COMMIT
    (model.json kept none: a street face's weather, a dome gore's arc, a sign's openings)."""
    if "laid" in model:
        return model["laid"]
    provenance = record["provenance"]
    found = laid_of(tree, provenance.get("place", ""), provenance.get("source_name") or model.get("stem", ""))
    return {} if found is None else found


def job_of(name, builder, laid, stages):
    """rebuild.py's job for one model: its files' box together."""
    every = np.vstack([np.array(mesh_of(stage).GetPointsAttr().Get(), dtype=np.float64) for stage in stages])
    return {"name": name, "kind": builder, "laid": laid,
            "box": [every.min(axis=0).tolist(), every.max(axis=0).tolist()]}


def runs_of(parts):
    """Each triangle's run: the serial of the stretch of triangles in turn that one part laid."""
    parts = np.asarray(parts)
    return np.concatenate([[0], np.cumsum(parts[1:] != parts[:-1])]).astype(np.int64)


def on_a_face(triangles, faces, outlines):
    """(each triangle's farthest corner from the corners of the one of `faces` it lies on best, that face, and each
    of its corners' nearest corner of that face)."""
    best = np.full(len(triangles), np.inf)
    face = np.zeros(len(triangles), dtype=np.int64)
    nearest = np.zeros((len(triangles), 3), dtype=np.int64)
    for serial in faces:
        corners = np.asarray(outlines[serial], dtype=np.float64)
        apart = np.linalg.norm(triangles[:, :, None, :] - corners[None, None], axis=3)
        off = apart.min(axis=2).max(axis=1)
        better = off < best
        best[better], face[better], nearest[better] = off[better], serial, apart[better].argmin(axis=2)
    return best, face, nearest


def corner_ids(outlines, faces):
    """{(face, corner index): id} for the corners of `faces`, corners within SAME_CORNER of each other one id (the
    faces one part laid meet at corners Blender rounds a little differently face by face)."""
    keys = [(serial, index) for serial in faces for index in range(len(outlines[serial]))]
    corners = np.array([outlines[serial][index] for serial, index in keys], dtype=np.float64)
    pairs = scipy.spatial.cKDTree(corners).query_pairs(SAME_CORNER, output_type="ndarray")
    graph = scipy.sparse.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(keys), len(keys)))
    _, labels = scipy.sparse.csgraph.connected_components(graph, directed=False)
    return dict(zip(keys, labels.tolist()))


def edge_balance(loops):
    """{(low, high): count} of the edges round `loops` (each a list of corner ids in turn), one way counted +1 and
    the other -1, the edges a surface's own triangles share cancelling, so only its border stays."""
    found = {}
    for loop in loops:
        for start, end in zip(loop, loop[1:] + loop[:1]):
            if start != end:
                key = (min(start, end), max(start, end))
                found[key] = found.get(key, 0) + (1 if start < end else -1)
    return {key: count for key, count in found.items() if count}


def faces_off(triangles, polygons, parts, outlines):
    """(each triangle's farthest corner from the face it lies on, the runs whose faces the model's triangles do not
    cover once, and where each lies: (the built face, each of its corners' nearest corner of that face)): the model's
    triangles in place of the built ones, run by run, a run the triangles in turn one part laid. Blender cuts a face
    of more than three corners into triangles its own way, and the old export cut some of the old builders' n-gons
    otherwise than Blender does now (another cut of a ring's face, its triangles in another order), so a triangle is
    checked to lie on the corners of one of its run's faces within TOLERANCE, and a run's triangles to have the border
    its faces have (each face covered once, the same way round): which part a triangle is stays certain, the very
    triangle built is not asked for."""
    runs = runs_of(parts)
    near = np.zeros(len(triangles))
    lies_on, corners = np.zeros(len(triangles), dtype=np.int64), np.zeros((len(triangles), 3), dtype=np.int64)
    uncovered = []
    for run in range(int(runs.max()) + 1 if len(runs) else 0):
        inside = np.flatnonzero(runs == run)
        faces = np.unique(polygons[inside])
        near[inside], face, nearest = on_a_face(triangles[inside], faces, outlines)
        lies_on[inside], corners[inside] = face, nearest
        ids = corner_ids(outlines, faces)
        built = [[ids[(serial, index)] for index in range(len(outlines[serial]))] for serial in faces]
        laid = [[ids[(serial, index)] for index in corners] for serial, corners in zip(face.tolist(), nearest.tolist())]
        if edge_balance(built) != edge_balance(laid):
            uncovered.append(run)
    return near, uncovered, (lies_on, corners)


def parts_by_order(answer, counts, glows, triangles):
    """(each file's triangles' part index, the farthest a triangle lies off, and where each lies: faces_off): the
    built triangles in the old join's order, the glowing parts' after the rest (into the glow file, as the old bake
    split them), the model's lying on the corners of the faces the same
    part laid in their place and covering them (faces_off) within TOLERANCE; Unrecovered when the counts or any
    triangle differ."""
    order = np.array(answer["order"], dtype=np.int64)
    shining = np.isin(order, [index for index, (_, surface) in enumerate(answer["parts"]) if glows(surface)])
    built = [int((~shining).sum()), int(shining.sum())]
    if built != (list(counts) + [0])[:2]:
        raise Unrecovered(f"built again it has {built[0]} triangles and {built[1]} glowing, the model's files "
                      f"{list(counts)}")
    sequence = np.concatenate([np.flatnonzero(~shining), np.flatnonzero(shining)])
    off, uncovered, lies = faces_off(np.asarray(triangles, dtype=np.float64),
                               np.array(answer["polygons"], dtype=np.int64)[sequence], order[sequence],
                               answer["outlines"])
    if off.max() > TOLERANCE:
        raise Unrecovered(f"built again, {int((off > TOLERANCE).sum())} of its {len(off)} triangles lie off the "
                          "model's "
                      f"(the farthest {off.max() * 1000:.2f} mm; {TOLERANCE * 1000:.1f} mm allowed)")
    if uncovered:
        raise Unrecovered(f"built again, {len(uncovered)} of its parts' stretches of faces are not covered once by the "
                      "model's triangles in their place")
    taken = order[sequence]
    return [taken[:counts[0]], *([taken[counts[0]:]] if len(counts) > 1 else [])], float(off.max()), lies


def content_coordinates(contents, lies):
    """Each model triangle's corners' `content` texture coordinates (a printed plate's picture across its front, as
    its builder laid them): those of the built face's corner each lies on; zero on a face whose part has no picture."""
    lies_on, corners = lies
    found = np.zeros((len(lies_on), 3, 2), dtype=np.float64)
    for index, (face, nearest) in enumerate(zip(lies_on.tolist(), corners.tolist())):
        if contents[face] is not None:
            found[index] = [contents[face][corner] for corner in nearest]
    return found


def texture_area(coordinates):
    """Each triangle's area in the picture (its `content` coordinates), twice over."""
    one, two = coordinates[:, 1] - coordinates[:, 0], coordinates[:, 2] - coordinates[:, 0]
    return np.abs(one[:, 0] * two[:, 1] - one[:, 1] * two[:, 0])


def size_printed(triangles, coordinates):
    """[wide, tall] metres a picture spans as its plate prints it: the triangle of most texture area's corners'
    change across the picture's width and height."""
    best = int(texture_area(coordinates).argmax())
    one, two = coordinates[best, 1] - coordinates[best, 0], coordinates[best, 2] - coordinates[best, 0]
    across = np.linalg.solve(np.array([one, two]), np.array([triangles[best][1] - triangles[best][0],
                                                             triangles[best][2] - triangles[best][0]]))
    return [round(float(np.linalg.norm(across[0])), 4), round(float(np.linalg.norm(across[1])), 4)]


def undecalled(parts, specs, part_of, triangles, coordinates):
    """Unrecovered for an entry with a part printing an old picture its builder laid no picture map on (nothing
    says where its picture lies); NoDecal for one printing an old picture the library holds no decal of, each
    picture's printed size measured on its part."""
    wanted = {}
    for index, (part, variant) in enumerate(parts):
        spec = specs[variant]
        on = part_of == index
        if "picture" not in spec or not on.any():
            continue
        if texture_area(coordinates[on]).max() <= MAPPED:
            raise Unrecovered(f"its part {part} prints the old picture {spec['picture']}, but its builder laid no "
                              "picture map on it")
        if not spec["decal"] and spec["picture"] not in wanted:
            wanted[spec["picture"]] = size_printed(np.asarray(triangles)[on], coordinates[on])
    if wanted:
        raise NoDecal("prints the old pictures " + ", ".join(sorted(wanted)) + ", which the library holds no decal "
                      "of (take them in: part_looks.py decals)", wanted)


def picture_file(variant):
    """A printed variant's picture's name in the remade entry."""
    return f"textures/{variant}.png"


def printed_picture(decal, spec, target):
    """The library decal printed as its old recipe printed its picture: over the token's colour (a label, a sign), or
    over black, lit from behind (a screen, recipes.screen at OLD_COMMIT); written to `target`."""
    ground = (0, 0, 0) if spec["recipe"] == "screen" else tuple(int(spec["hex"][at:at + 2], 16) for at in (1, 3, 5))
    with Image.open(decal) as picture:
        printed = Image.alpha_composite(Image.new("RGBA", picture.size, ground + (255,)), picture.convert("RGBA"))
    target.parent.mkdir(parents=True, exist_ok=True)
    printed.convert("RGB").save(target)


def picture_wired(stage, material, shader, variant, spec):
    """The look's colour (and a screen's light) read from the printed picture through the mesh's `st`."""
    reader = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("st"))
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    texture = UsdShade.Shader.Define(stage, material.GetPath().AppendChild("print"))
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(picture_file(variant))
    texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), "result")
    texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    shader.GetInput("diffuseColor").ConnectToSource(texture.ConnectableAPI(), "rgb")
    if spec["recipe"] == "screen":
        shader.GetInput("emissiveColor").ConnectToSource(texture.ConnectableAPI(), "rgb")


def looks_written(stage, root, parts, used, specs, surfaces):
    """`<root>/Looks/<variant>` for every variant the parts `used` name: a preview surface in the variant's colour,
    its recipe's spec, library surface, colour and variant marked on it, a printed variant's picture (its library
    decal, `score:surface:decal`) read through `st`; {variant: material}."""
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
        if spec.get("decal"):
            picture_wired(stage, material, shader, variant, spec)
            prim.CreateAttribute("score:surface:decal", Sdf.ValueTypeNames.String).Set(spec["decal"])
        prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(surfaces[spec["recipe"]])
        prim.CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(spec["hex"])
        prim.CreateAttribute("score:surface:variant", Sdf.ValueTypeNames.String).Set(variant)
        looks[variant] = material
    return looks


def subset_name(parts, index):
    """A part's subset name: its part, with its surface after it when the builder names that part in two surfaces."""
    part, surface = parts[index]
    return part if sum(1 for other, _ in parts if other == part) == 1 else f"{part}_{surface}"


def refinished(stage, parts, faces, specs, surfaces, coordinates=None):
    """The stage made over: its baked look and texture coordinates off, a materialBind subset a part bound to its
    variant's look; where a part prints a picture, `st` again: each triangle's `coordinates` (content_coordinates);
    [{part, variant, surface, faces}]."""
    root = stage.GetDefaultPrim().GetPath()
    mesh = mesh_of(stage)
    stage.RemovePrim(root.AppendChild("Looks"))
    UsdShade.MaterialBindingAPI(mesh.GetPrim()).UnbindAllBindings()
    UsdGeom.PrimvarsAPI(mesh.GetPrim()).RemovePrimvar("st")
    used = sorted(set(faces.tolist()))
    if any(specs[parts[index][1]].get("decal") for index in used):
        UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar(
            "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying).Set(
            [Gf.Vec2f(*corner) for corner in np.asarray(coordinates).reshape(-1, 2).tolist()])
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
        raise Unrecovered(f"builder {builder} built {strays}, which {MAP.name} does not list for it")


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
        raise Unrecovered(f"its builder failed at OLD_COMMIT: {answer['error']}")
    held = [name for name in FILES if name in record["files"]]
    stages = [Usd.Stage.Open(str(file_path(address, name))) for name in held]
    counts = [len(mesh_of(stage).GetFaceVertexCountsAttr().Get()) for stage in stages]
    triangles = np.vstack([triangle_corners(mesh_of(stage)) for stage in stages])
    parts = [tuple(part) for part in answer["parts"]]
    builder = builder_of(model["kind"], record["provenance"].get("place", ""))
    mapped_parts(builder, [list(part) for part in parts])
    by_file, farthest, lies = parts_by_order(answer, counts, lambda surface: glowing(library, surface),
                                               triangles)
    place = library_place(tree, record["provenance"]["place"])
    specs = {surface: variant_spec(library, tree, place, surface) for _, surface in parts}
    coordinates = content_coordinates(answer["contents"], lies)
    undecalled(parts, specs, np.concatenate(by_file), triangles, coordinates)
    surfaces = newest_surfaces(specs)
    into.mkdir(parents=True, exist_ok=True)
    printed = {variant: spec for variant, spec in specs.items() if spec.get("decal")}
    for variant, spec in printed.items():
        printed_picture(file_path(spec["decal"], DECAL), spec, into / picture_file(variant))
    listed, first = [], 0
    for name, stage, faces in zip(held, stages, by_file):
        listed += [dict(part, file=name) for part in refinished(stage, parts, faces, specs, surfaces,
                                                                coordinates[first:first + len(faces)])]
        first += len(faces)
        stage.GetRootLayer().Export(str(into / name))
    entry = entry_written(address, record, model, listed, held, surfaces, printed, into, STEP)
    return entry, {"parts": listed, "farthest_mm": round(farthest * 1000, 6), "size": answer["size"],
                   "shift_mm": [round(value * 1000, 3) for value in answer["shift"]]}


def entry_written(address, record, model, listed, held, surfaces, printed, into, step):
    """The remade entry's record written in `into`, and its take-in list entry, its step in words `step`."""
    (into / RECORD).write_text(json.dumps(dict(model, parts=listed), indent=2, sort_keys=True) + "\n")
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                            check=True).stdout.strip()
    files = {name: {"path": str(into / name), "from": f"{address}/{name}, remade"} for name in held}
    files[RECORD] = {"path": str(into / RECORD), "from": f"{address}/{RECORD}, with its parts"}
    files.update({picture_file(variant): {"path": str(into / picture_file(variant)),
                                          "from": f"{spec['decal']}/{DECAL}, printed as its old recipe printed it"}
                  for variant, spec in printed.items()})
    return {"kind": "model", "id": record["id"], "title": record["title"], "files": files,
            "made_with": [{"what": step.format(old=OLD_COMMIT[:9], commit=commit[:9]), "source": "score"}],
            "tags": record.get("tags", {}), "usd": record.get("usd"),
            "requires": sorted({*surfaces.values(), *(spec["decal"] for spec in printed.values())})}


# --- the fallback: a finish from the atlas regions ---------------------------------------------------------------
# An entry whose old build cannot be recovered (no code build, a builder that fails or no longer matches) is finished
# from its own geometry and old atlas instead: its faces split by the UV island they lie in, each island's painted
# texels' colour read (the unpainted black left out), and each island worn in its room's library surface whose
# recipe colour is nearest; an island with no painted texel takes the surface of the nearest island that has one.

UNPAINTED = 0  # the old atlas's unpainted texels are black, all three channels 0
# A face's texels are read at these points of each of its triangles (corner 0 plus a and b times its two edges).
SAMPLES = ((1 / 3, 1 / 3), (0.1, 0.1), (0.8, 0.1), (0.1, 0.8), (0.45, 0.45), (0.45, 0.1), (0.1, 0.45))
SRGB_TO_XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.95047, 1.0, 1.08883])


def lab_of(srgb):
    """CIE Lab (D65) of sRGB values in 0..1, the last axis the channels."""
    srgb = np.asarray(srgb, dtype=np.float64)
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    xyz = (linear @ SRGB_TO_XYZ.T) / WHITE
    bend = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * bend[..., 1] - 16, 500 * (bend[..., 0] - bend[..., 1]),
                     200 * (bend[..., 1] - bend[..., 2])], axis=-1)


def srgb_of(linear):
    """sRGB (0..1) of linear values."""
    linear = np.clip(np.asarray(linear, dtype=np.float64), 0.0, 1.0)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def face_islands(mesh):
    """(each face's UV island, each face's texture corners, each face's corners' points): faces sharing a texture
    corner (a point, where `st` is given per point) are one island."""
    counts = np.array(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    indices = np.array(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    primvar = UsdGeom.PrimvarsAPI(mesh.GetPrim()).GetPrimvar("st")
    if not primvar or not primvar.HasValue():
        raise Refused(f"{mesh.GetPath()}: no texture coordinates to read its atlas by")
    flat = np.array(primvar.ComputeFlattened(), dtype=np.float64)
    per_corner = primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying
    uv = flat if per_corner else flat[indices]
    keys = np.unique(np.round(uv, 6), axis=0, return_inverse=True)[1].ravel() if per_corner else indices
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    owner = np.repeat(np.arange(len(counts)), counts)
    corner_count = int(keys.max()) + 1
    links = scipy.sparse.coo_matrix((np.ones(len(owner)), (owner, keys + len(counts))),
                                    shape=(len(counts) + corner_count,) * 2)
    _, labels = scipy.sparse.csgraph.connected_components(links, directed=False)
    return (labels[:len(counts)], [uv[start:start + count] for start, count in zip(starts, counts)],
            [points[indices[start:start + count]] for start, count in zip(starts, counts)])


def texels_at(atlas, corners):
    """The atlas's colours (sRGB, 0..1) at SAMPLES of a face's triangles (fanned from its first corner)."""
    high, wide = atlas.shape[:2]
    found = []
    for step in range(1, len(corners) - 1):
        first, one, two = corners[0], corners[step] - corners[0], corners[step + 1] - corners[0]
        for along, across in SAMPLES:
            u, v = (first + along * one + across * two) % 1.0
            found.append(atlas[min(high - 1, int((1 - v) * high)), min(wide - 1, int(u * wide))])
    return np.array(found, dtype=np.float64).reshape(-1, 3) / 255.0


def island_colours(atlas, islands, uvs):
    """{island: the median colour (sRGB) of its painted texels} of the islands that have any."""
    painted = {}
    for island, corners in zip(islands.tolist(), uvs):
        texels = texels_at(atlas, corners)
        painted.setdefault(island, []).extend(texels[(texels * 255).round().max(axis=1) > UNPAINTED])
    return {island: np.median(np.array(found), axis=0) for island, found in painted.items() if found}


def nearest_variants(colours, candidates):
    """{island: the candidate variant whose recipe colour (its `colour`, linear) is nearest its colour in Lab}."""
    names = sorted(candidates)
    labs = lab_of(srgb_of([candidates[name]["colour"] for name in names]))
    return {island: names[int(np.linalg.norm(labs - lab_of(colour), axis=1).argmin())]
            for island, colour in colours.items()}


def regions_worn(islands, points, chosen):
    """Each face's variant: its island's, or for an island with no painted texel the variant of the nearest face
    (by the middles of the faces) whose island has one."""
    middles = np.array([corners.mean(axis=0) for corners in points])
    known = np.array([island in chosen for island in islands.tolist()])
    if not known.any():
        raise Refused("no face of it lies on a painted texel of its atlas")
    taken = np.flatnonzero(known)
    _, nearest = scipy.spatial.cKDTree(middles[taken]).query(middles)
    return [chosen[island] if island in chosen else chosen[int(islands[taken[near]])]
            for island, near in zip(islands.tolist(), nearest.tolist())]


def atlas_of(address, stage):
    """The model's old base colour atlas (sRGB, 0..255), read from its baked look's base_color texture."""
    for prim in stage.Traverse():
        found = prim.GetAttribute("inputs:file")
        if found and found.Get() and found.Get().path.endswith("base_color.png"):
            with Image.open(file_path(address, found.Get().path.removeprefix("./"))) as picture:
                return np.asarray(picture.convert("RGB"))
    raise Refused(f"{address}: no baked base colour atlas to read its regions from")


def room_variants(tree, place):
    """The variants the room's own code builders name (map/parts.json, for the builders its kit pieces are): the
    room's own palette."""
    builders = json.loads(MAP.read_text())["builders"]
    return {surface for piece in room_pieces(tree, place)
            for _, surface in builders.get(builder_of(piece.get("kind", ""), place), [])}


def regions_remade(address, record, library, tree, into):
    """One entry's files finished from their atlas regions in `into`: (the take-in list's entry, its parts)."""
    held = [name for name in FILES if name in record["files"]]
    stages = [Usd.Stage.Open(str(file_path(address, name))) for name in held]
    place = library_place(tree, record["provenance"]["place"])
    shown = library.by_library(place)
    palette = room_variants(tree, record["provenance"]["place"])
    worn_by_file = []
    for name, stage in zip(held, stages):
        glow = name == "model_glow.usdc"
        candidates = {variant: shown[variant] for variant in palette if variant in shown
                      and "picture" not in shown[variant] and glowing(library, variant) == glow}
        if not candidates:
            raise Refused(f"its room {record['provenance']['place']} names no library surface for {name}")
        islands, uvs, points = face_islands(mesh_of(stage))
        chosen = nearest_variants(island_colours(atlas_of(address, stage), islands, uvs), candidates)
        worn_by_file.append(regions_worn(islands, points, chosen))
    used = sorted({variant for worn in worn_by_file for variant in worn})
    parts = [(f"region_{variant}", variant) for variant in used]
    specs = {variant: variant_spec(library, tree, place, variant) for variant in used}
    surfaces = newest_surfaces(specs)
    into.mkdir(parents=True, exist_ok=True)
    listed = []
    for name, stage, worn in zip(held, stages, worn_by_file):
        faces = np.array([used.index(variant) for variant in worn], dtype=np.int64)
        listed += [dict(part, file=name) for part in refinished(stage, parts, faces, specs, surfaces)]
        stage.GetRootLayer().Export(str(into / name))
    model = json.loads(file_path(address, RECORD).read_text())
    entry = entry_written(address, record, model, listed, held, surfaces, {}, into, REGIONS_STEP)
    return entry, {"parts": listed, "from": "atlas regions"}


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
    report, entries, replaced, jobs, held, unrecovered = {}, [], [], [], {}, {}
    with tempfile.TemporaryDirectory(prefix="part-looks-") as scratch:
        scratch = pathlib.Path(scratch)
        tree = old_tree(scratch)
        library = old_library(tree)
        for address in addresses_of(arguments):
            try:
                record, model = checked_record(address)
                stages = [Usd.Stage.Open(str(file_path(address, name))) for name in FILES if name in record["files"]]
                jobs.append(job_of(address, builder_of(model["kind"], record["provenance"].get("place", "")),
                                   laid_made_with(tree, record, model), stages))
                held[address] = (record, model)
            except Unrecovered as why:
                unrecovered[address] = str(why)
            except (Refused, library_files.LibraryUnreachable) as why:
                report[address] = {"refused": str(why)}
        answers = rebuilt(tree, jobs, scratch) if jobs else {}
        made = {}
        for address, (record, model) in held.items():
            try:
                made[address] = remade(address, record, model, answers[address], library, tree,
                                       into / "made" / record["id"])
            except Unrecovered as why:
                unrecovered[address] = str(why)
            except Refused as why:
                report[address] = {"refused": str(why), **({"decals_wanted": why.wanted}
                                                           if isinstance(why, NoDecal) else {})}
        for address, why in unrecovered.items():
            record = entry_record(address)
            try:
                entry, found = regions_remade(address, record, library, tree, into / "made" / record["id"])
                made[address] = entry, dict(found, unrecovered=why)
            except Refused as fallback:
                report[address] = {"refused": f"{why}; from its atlas regions: {fallback}"}
        for address, (entry, found) in made.items():
            record = entry_record(address)
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


# A picture's material class (score_lib decals.CLASSES) by the style the old library drew it in (materials.json
# `pictures`): a label or keypad legend on a plastic plate, a stencil sprayed on metal, sheets and posters on paper, a
# banner on cloth, a hanzi plate on enamelled metal, a screen's content behind glass; a drawn picture by what it hangs
# as (the toolboard's outlines painted on its wooden board).
PICTURE_CLASS = {"label": "plastic", "keypad": "plastic", "stripes": "plastic", "stencil": "metal", "note": "paper",
                 "sheet": "paper", "hanzi_sheets": "paper", "calendar": "paper", "plan": "paper", "status": "glass",
                 "readout": "glass", "lens": "glass"}
SHAPE_CLASS = {"banner": "fabric", "couplet": "paper", "poster": "paper", "plate": "metal"}  # a hanzi picture's, by shape
DRAWN_CLASS = {"toolboard_outlines": "wood"}
DECAL_WHAT = ("an old picture of score's library (data/library/pictures at score {old}, drawn from its materials.json "
              "`pictures` row) taken in as a decal, so the October code-built models remade by part_looks print it")


def words_of(drawn):
    """The words an old picture prints (its text, title, lines and table rows); a sheet's `lines` count of ruled
    lines prints none."""
    lines = drawn.get("lines", [])
    found = [drawn[key] for key in ("text", "title") if drawn.get(key)] + (lines if isinstance(lines, list) else [])
    return found + [" ".join(row) for row in drawn.get("rows", [])]


def decal_written(tree, library, picture, size, folder):
    """One picture's decal entry for the take-in list, its files in `folder`; Refused for a picture with no
    transparency (a library decal must have some: score_lib decals.decal_faults)."""
    source = tree / "data/library/pictures" / f"{picture}.png"
    with Image.open(source) as image:
        if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] == 255:
            raise Refused(f"its picture {picture} has no transparency, which a library decal needs")
    drawn = json.loads((tree / "data/library/materials.json").read_text())["pictures"][picture]
    variant = next(name for name, found in library.variants(library.theme_library()).items()
                  if found.get("picture") == picture)
    screen = library.variants(library.theme_library())[variant].get("family") == "screen"
    material = DRAWN_CLASS.get(picture) or PICTURE_CLASS.get(drawn.get("style")) or SHAPE_CLASS[drawn.get("shape")]
    record = {"variant": picture, "family": "decal", "recipe": "decal", "size_m": size, "class": material,
              "opacity": "emissive" if screen else "opaque", "ink": "many", "words": words_of(drawn),
              "from": {"picture": f"data/library/pictures/{picture}.png", "commit": OLD_COMMIT},
              "maps": {"decal": DECAL}, "source": "score"}
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "surface.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    (folder / DECAL).write_bytes(source.read_bytes())
    files = {DECAL: {"path": str(folder / DECAL),
                     "from": f"score {OLD_COMMIT[:9]}:data/library/pictures/{picture}.png"},
             "surface.json": {"path": str(folder / "surface.json"), "from": "written by score's part_looks decals"}}
    return {"kind": "surface", "id": picture, "title": f"{picture.replace('_', ' ').capitalize()} (decal)",
            "files": files, "made_with": [{"what": DECAL_WHAT.format(old=OLD_COMMIT[:9]), "source": "score"}],
            "tags": {"family": ["decal"], "class": [material], "ink": ["many"], "words": record["words"],
                     "size_m": ["{0:.3f}x{1:.3f}".format(*size)]}}


def wanted_sizes(reports):
    """{picture: [wide, tall]} the reports' entries wanted a decal of, each picture's widest print."""
    found = {}
    for path in reports:
        for row in json.loads(pathlib.Path(path).read_text()).values():
            for picture, size in row.get("decals_wanted", {}).items():
                if size and (picture not in found or size[0] * size[1] > found[picture][0] * found[picture][1]):
                    found[picture] = size
    return found


def decals(arguments):
    """The pictures `make` reports wanted taken in as library decals: DIR/decals.json (a `score-lib take-in` list)
    and DIR/decals-refused.json; one line."""
    into = pathlib.Path(arguments.into)
    entries, refused = [], {}
    with tempfile.TemporaryDirectory(prefix="part-looks-") as scratch:
        tree = old_tree(pathlib.Path(scratch))
        library = old_library(tree)
        for picture, size in sorted(wanted_sizes(arguments.reports).items()):
            try:
                entries.append(decal_written(tree, library, picture, size, into / "decals" / picture))
            except Refused as why:
                refused[picture] = str(why)
    (into / "decals.json").write_text(json.dumps({
        "world": "world1", "commit": OLD_COMMIT, "entries": entries,
        "taken_from": "score's part_looks decals: the old library's pictures the October code-built models print"},
        indent=1) + "\n")
    (into / "decals-refused.json").write_text(json.dumps(refused, indent=1, sort_keys=True) + "\n")
    print(f"part_looks decals: {len(entries)} decals listed, {len(refused)} refused; {into / 'decals.json'}")


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    actions = parser.add_subparsers(dest="action", required=True)
    making = actions.add_parser("make", help="remake library models part by part in library surfaces")
    making.add_argument("address", nargs="*")
    making.add_argument("--list", help="a file of addresses, one a line")
    making.add_argument("--into", required=True)
    making.add_argument("--previews", help="a folder for <id>-before.png and <id>-after.png")
    actions.add_parser("recover", help="write map/parts.json from every builder at the models' commit")
    taking = actions.add_parser("decals", help="list the pictures make's reports wanted as library decals")
    taking.add_argument("reports", nargs="+", help="make's report.json files")
    taking.add_argument("--into", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse(argv)
    if arguments.action == "recover":
        recover()
    elif arguments.action == "decals":
        decals(arguments)
    else:
        make(arguments)


if __name__ == "__main__":
    main()
