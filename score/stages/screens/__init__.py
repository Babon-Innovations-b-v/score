"""The screens stage, `screens@<place>` (free, this PC, no Blender; #88): what a screen row shows. A scene inventory
row whose kind shows (score/stages/row_kinds.py: a screen, a monitor, a billboard) has its take's display parts given
the library's screen picture (tools/props/screens/content.py: the place's plan or a dashboard, chosen and drawn from
the part's seed, in two of the scene's palette tokens) as the `screen` recipe paints it (tools/props/library/
recipes.py: dark glass, the picture lit from behind). The bake (surfaces-bake) stays as it baked; the assembly lays
each pictured model's own layer over its baked asset (take), so nothing before the assembly moves.

    make     for each model of the place's bake whose take's row shows: its faces named by surface as the assembly's
             asset names them (faces: tools/usd/export's own steps), its display parts (display: its lit surfaces,
             a glowing recipe or the screen family, that name a screen word, else its largest lit one), each one's
             picture (its base colour and its glow as PNGs, textures/), and screens/<model>.usda over the asset:
             a `screen_st` coordinate on the drawn mesh laid flat over each screen of a display part (screens_of:
             its pieces joined edge to edge, the crumbs in their nearest screen's frame; laid_flat), a material of
             the picture bound to the part's subset. screens.json: each model's take, parts, seed, layout and lit
             share. A screen take its bake made with no display part is a gap of this row (batch-gaps.json): the
             finish list gave it no screen to draw on.
    pictured (gate)  every screen take the bake made is pictured; one with no display part fails by name (the table
             moves it as the batch gap it is, stages.BATCH_GATES).
    take(made, out)  the assembly's side: each pictured asset made a stack of its picture's layer over its bake;
             `assembled` wraps the assembly's make with it in the stage table, so the assembly package (which the
             settle, the peels, the light passes, the scene clips and the sim body import) stays unedited.

The glass is the scene's darkest palette token (by relative luminance), the content the display part's own token
colour (its spec in the bake's specs.json), the seed the part's own (its list settings' seed, folded under SEED_FOLD).
row-kinds.json's `shows` stays null; data/checks/screens.json names this stage for it, which the motion row's
`covered` reads (score/stages/motion), so no row that reads row-kinds.json moves with this stage.
"""
import functools
import json
import pathlib
import shutil
import sys

from score import checks, contracts
import score.stages.row_kinds as row_kinds
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in ("tools/usd", "tools/props", "tools/props/screens", "score/stages/surfaces"):
    if str(REPO / folder) not in sys.path:
        sys.path.append(str(REPO / folder))

import content  # noqa: E402  tools/props/screens/content.py, the library's screen picture
import palette_library  # noqa: E402

ROW = "screens"
RECORD, LAYERS, TEXTURES = "screens.json", "screens", "textures"
# The recipe and family a lit part is (a glow the scene library made, or a surface of the screen family).
LIT_RECIPE, SCREEN_FAMILY = "glowing", "screen"
# A picture's seed is the part's own, kept under this (the list's seeds run to 10 digits).
SEED_FOLD = 100000
# A piece of a display part holding at least this share of its area is a screen of its own (screens_of).
SCREEN_LEAST = 0.03
# A design's surface data (surfaces/surface_data.DESIGN, spelled here so the surface package stays out of the key).
DESIGN_SURFACES = PROPS_HOME / "design" / "surfaces"
RULES = REPO / "data/checks/screens.json"


def rules(path=RULES):
    """This stage's data: the words that name a screen part, and `read_by` (the `does` value it makes)."""
    return json.loads(pathlib.Path(path).read_text())


def screen_takes(data, table):
    """The takes of a place's surface data whose row shows (the take's `kind` its reading noun, `object` its name),
    sorted."""
    return sorted(take for take, entry in data.get("takes", {}).items()
                  if "shows" in row_kinds.does(row_kinds.kind_of({"noun": entry.get("kind"),
                                                                  "name": entry.get("object")}, table), table))


def applies(place):
    """A place whose design's surface data bakes a model of a take whose row shows."""
    path = DESIGN_SURFACES / f"{place}.json"
    if not path.is_file():
        return False
    data = json.loads(path.read_text())
    baked = set((data.get("bake") or {}).get("models", {}).values())
    return bool(baked & set(screen_takes(data, row_kinds.table())))


def files(place):
    """The place's surface data, the row-kind rules, this stage's rules and the place's plan where it has one."""
    found = {"surfaces": f"{{home}}/design/surfaces/{place}.json", "row kinds": "{data}/checks/row-kinds.json",
             "screens": "{data}/checks/screens.json"}
    if (PROPS_HOME / "design" / "plans" / f"{place}.json").is_file():
        found["plan"] = f"{{home}}/design/plans/{place}.json"
    return found


def drawn_plan(plan):
    """The place's plan as the picture draws it: its outline, its openings and items, and each wall as straight
    lines {"from", "to"} (an arc wall in its pieces, earth_seed.design_shell.written_lines); None with no plan."""
    if plan is None:
        return None
    from score.stages.earth_seed import design_shell
    walls = [{"from": start, "to": end} for wall in plan.get("walls") or []
             for start, end in design_shell.written_lines(wall)]
    return {"outline": plan.get("outline") or [], "walls": walls, "openings": plan.get("openings") or [],
            "items": plan.get("items") or []}


def lit(spec):
    """Whether a spec gives off light: a glowing recipe, or the screen family."""
    return spec.get("recipe") == LIT_RECIPE or spec.get("family") == SCREEN_FAMILY


def display(surfaces, areas, specs, words):
    """The display parts among a model's surfaces (each face's surface name, `areas` each face's area): its lit
    surfaces whose library name holds a screen word, else its largest lit surface; [] with none lit."""
    names = sorted(set(surfaces))
    glowing = [name for name in names if lit(specs.get(name, {}))]
    said = [name for name in glowing
            if set(str(specs[name].get("library", name)).replace("-", "_").split("_")) & set(words)]
    if said or not glowing:
        return said
    return [max(glowing, key=lambda name: float(areas[surfaces == name].sum()))]


def darkest(colours):
    """The darkest of the palette's tokens by relative luminance (Rec. 709 weights on linear RGB)."""
    return min(colours, key=lambda token: sum(weight * value for weight, value
                                              in zip((0.2126, 0.7152, 0.0722), colours[token])))


def faces(made, model, labelled, entry):
    """The baked model's drawn mesh as the assembly's asset holds it: (positions, triangles, each face's surface
    name, each face's map), by tools/usd/export's own steps on the bake's gltf and the take's labelled parts."""
    import export
    from score.stages.assembly import baked
    geometry = export.model_geometry(made / f"{model}.gltf")
    parts, turn, size = baked.laid_parts(made, model, labelled, entry)
    points, names = export.part_points(export.labelled_take({model: parts}, model), turn, size)
    return geometry["positions"], geometry["triangles"], export.face_surfaces(geometry, points, names), \
        geometry["maps"]


def laid_flat(positions, triangles, framed, laid):
    """Each vertex's `screen_st` over the `laid` faces (0 elsewhere), in the frame of the `framed` faces: the plane of
    their two longest sides, filling 0 to 1 across them, up (+y) the picture's up when it is one of them, turned so
    the picture reads from the side they look to (make_chunky.laid_flat's rule, on the asset's own points)."""
    import numpy as np
    corners = triangles[framed]
    points = positions[np.unique(corners)]
    low, span = points.min(axis=0), np.ptp(points, axis=0)
    across, up = sorted(sorted(range(3), key=lambda axis: -span[axis])[:2], key=lambda axis: axis == 1)
    facing = 3 - across - up
    first, second, third = (positions[corners[:, at]] for at in range(3))
    mirrored = np.cross(second - first, third - first)[:, facing].sum() < 0
    used = np.unique(triangles[laid])
    found = np.zeros((len(positions), 2))
    u = (positions[used, across] - low[across]) / max(span[across], 1e-9)
    found[used, 0] = 1.0 - u if mirrored else u
    found[used, 1] = (positions[used, up] - low[up]) / max(span[up], 1e-9)
    return found


def screens_of(positions, triangles, chosen):
    """The chosen faces as the screens they are, [(framed, laid)] boolean masks over every face: each piece of them
    joined edge to edge (vertices welded by place) holding at least SCREEN_LEAST of their area is a screen framing
    itself (a console's two screens of one surface each take the whole picture); a smaller piece (the split's crumbs
    round a screen) is laid in the frame of the screen whose middle lies nearest its own; with no such piece (a
    screen the split left in crumbs) the faces together are one screen."""
    import numpy as np
    import trimesh
    welded = trimesh.Trimesh(positions, triangles, process=False)
    welded.merge_vertices()
    picked = np.flatnonzero(chosen)
    sub = welded.submesh([picked], append=True, repair=False)
    pieces = trimesh.graph.connected_components(sub.face_adjacency, nodes=np.arange(len(picked)), min_len=1)
    areas = sub.area_faces
    middles = sub.triangles_center
    big = [piece for piece in pieces if areas[piece].sum() >= SCREEN_LEAST * areas.sum()] or \
        [np.arange(len(picked))]
    centres = np.array([np.average(middles[piece], axis=0, weights=areas[piece] + 1e-12) for piece in big])
    owner = {index: index for index in range(len(big))}
    laid = [list(piece) for piece in big]
    kept = {int(face) for piece in big for face in piece}
    for piece in pieces:
        if int(piece[0]) in kept:
            continue
        middle = np.average(middles[piece], axis=0, weights=areas[piece] + 1e-12)
        laid[owner[int(np.argmin(np.linalg.norm(centres - middle, axis=1)))]] += list(piece)
    found = []
    for piece, faces_laid in zip(big, laid):
        framed, spread = np.zeros(len(triangles), dtype=bool), np.zeros(len(triangles), dtype=bool)
        framed[picked[piece]], spread[picked[faces_laid]] = True, True
        found.append((framed, spread))
    return found


def subset_name(surface, maps, number):
    """The asset's subset of a surface on one map (export.part_subsets)."""
    return surface if maps == 1 else f"{surface}_map{number + 1}"


def write_layer(path, model, coordinates, bound, roughness):
    """screens/<model>.usda over the asset's namespace: the `screen_st` coordinates on /<model>/geo and, for each
    subset in `bound` ({subset: (base PNG, glow PNG) relative to the layer}), a material of the picture
    (UsdPreviewSurface: diffuse the base, emissive the glow, the screen's roughness) bound to it."""
    from pxr import Sdf, Usd, UsdGeom, UsdShade, Vt
    import numpy as np
    stage = Usd.Stage.CreateNew(str(path))
    mesh = stage.OverridePrim(f"/{model}/geo")
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("screen_st", Sdf.ValueTypeNames.TexCoord2fArray,
                                            UsdGeom.Tokens.vertex).Set(
        Vt.Vec2fArray.FromNumpy(coordinates.astype(np.float32)))
    for subset, (base, glow) in sorted(bound.items()):
        where = f"/{model}/Looks/{subset}__screen"
        material = UsdShade.Material.Define(stage, where)
        shader = UsdShade.Shader.Define(stage, f"{where}/surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        reader = UsdShade.Shader.Define(stage, f"{where}/uv")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("screen_st")
        coordinates_out = reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
        for role, file, socket in (("base", base, "diffuseColor"), ("glow", glow, "emissiveColor")):
            texture = UsdShade.Shader.Define(stage, f"{where}/{role}")
            texture.CreateIdAttr("UsdUVTexture")
            texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(file)
            texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(coordinates_out)
            texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
            for wrap in ("wrapS", "wrapT"):  # a crumb laid past its screen's edge takes the edge, never a repeat
                texture.CreateInput(wrap, Sdf.ValueTypeNames.Token).Set("clamp")
            shader.CreateInput(socket, Sdf.ValueTypeNames.Color3f).ConnectToSource(
                texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        for name, value in (("score:surface", subset), ("score:recipe", "screen")):
            material.GetPrim().CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
        part = stage.OverridePrim(f"/{model}/geo/{subset}")
        UsdShade.MaterialBindingAPI.Apply(part).Bind(material)
    stage.GetRootLayer().Save()


def pictured(model, found, specs, colours, glass, recipes, plan, words, out):
    """One model's picture and layer: one picture for all its display parts together (a screen's glow and the text
    glowing on it are one screen), seeded and inked by its largest display part, in textures/, and
    screens/<model>.usda; its record ({"surfaces", "seed", "ink", "lit"}) or None with no display part."""
    import numpy as np
    positions, triangles, surfaces, maps = found
    corners = positions[triangles]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    shown = display(surfaces, areas, specs, words)
    if not shown:
        return None
    chosen = np.isin(surfaces, shown)
    coordinates = np.zeros((len(positions), 2))
    for framed, spread in screens_of(positions, triangles, chosen):
        laid = laid_flat(positions, triangles, framed, spread)
        used = np.unique(triangles[spread])
        coordinates[used] = laid[used]
    largest = max(shown, key=lambda surface: float(areas[surfaces == surface].sum()))
    spec = specs[largest]
    seed = int(spec.get("seed", 0)) % SEED_FOLD
    made = content.write(colours[glass], spec["colour"], seed, out / LAYERS / TEXTURES, model, content.SIZE, plan)
    files = tuple(f"./{TEXTURES}/{made[role].name}" for role in ("base", "glow"))
    count = int(maps.max()) + 1
    bound = {subset_name(surface, count, number): files for surface in shown for number in range(count)
             if ((surfaces == surface) & (maps == number)).any()}
    write_layer(out / LAYERS / f"{model}.usda", model, coordinates, bound, recipes["screen"]["roughness"])
    return {"surfaces": shown, "seed": seed, "ink": spec.get("token"), "lit": made["lit"]}


def make(inputs, out, seed, params):
    """Each screen take's baked models pictured (pictured): layers and textures under screens/, screens.json, and a
    batch gap for each screen take with no display part."""
    import score.stages.batch_gaps as batch_gaps
    bake, paint = pathlib.Path(inputs["surfaces-bake"]), pathlib.Path(inputs["surfaces-paint"])
    data = json.loads(pathlib.Path(inputs["surfaces"]).read_text())
    shown_takes = screen_takes(data, row_kinds.table(inputs["row kinds"]))
    words = rules(inputs["screens"])["words"]
    palette = palette_library.read(inputs)
    colours = palette_library.library_tokens(palette)
    recipes = palette_library.scene_library(palette)["recipes"]
    specs = json.loads((bake / "specs.json").read_text())
    plan = drawn_plan(json.loads(pathlib.Path(inputs["plan"]).read_text()) if "plan" in inputs else None)
    glass = darkest(colours)
    found, gaps = {}, []
    for model, entry in sorted(json.loads((bake / "baked.json").read_text()).items()):
        if entry["parts"] not in shown_takes:
            continue
        record = pictured(model, faces(bake / "made", model, paint / "labelled" / entry["parts"], entry), specs,
                          colours, glass, recipes, plan, words, out)
        if record is None:
            gaps.append(batch_gaps.gap(f"{model}: no screen to draw on", ROW, "pictured", (model, entry["parts"]),
                                       [f"{model}: its take {entry['parts']} shows, and its bake has no lit part"],
                                       "the finish list gave the take no glowing or screen part (surfaces-parts)"))
            continue
        found[model] = dict(record, take=entry["parts"], glass=glass)
    (out / RECORD).write_text(json.dumps({"models": found, "takes": shown_takes}, indent=1))
    batch_gaps.write(out, gaps)


def screens_faults(output):
    """The output's own faults: its record unread, or a pictured model with no layer."""
    path = pathlib.Path(output) / RECORD
    if not path.is_file():
        return [f"{RECORD} missing"]
    found = json.loads(path.read_text())["models"]
    return [f"{model}: no {LAYERS}/{model}.usda" for model in found
            if not (pathlib.Path(output) / LAYERS / f"{model}.usda").is_file()]


def judge_pictured(output, inputs, evidence):
    """Every model of a screen take the bake made is pictured; one with no display part fails by name."""
    found = json.loads((pathlib.Path(output) / RECORD).read_text())["models"]
    gaps = json.loads((pathlib.Path(output) / "batch-gaps.json").read_text())["gaps"]
    failing = tuple(fault for gap in gaps for fault in gap["faults"])
    reason = (f"{len(failing)} screen models have no screen to draw on" if failing else
              f"all {len(found)} screen models pictured")
    return checks.Verdict("pictured", checks.FAIL if failing else checks.PASS, reason,
                          {"pictured": len(found), "unpictured": len(failing)}, {"unpictured": "lower"}, failing)


CONTRACT = contracts.Contract(ROW, 1, screens_faults)
CHECKS = (checks.Check("pictured", judge_pictured),)


def take(made, out):
    """The assembly's side: each model the screens output pictured whose asset the assembly wrote (assets/<model>.usdc)
    made a stack, its picture's layer over its bake: the bake's asset kept as <model>_baked.usdc, its layers and
    textures copied into assets/screens/, and assets/<model>.usdc a layer of those two, the picture's strongest.
    The pictured models, sorted."""
    from pxr import Sdf
    made, assets = pathlib.Path(made), pathlib.Path(out) / "assets"
    record = json.loads((made / RECORD).read_text())["models"]
    taken = sorted(model for model in record if (assets / f"{model}.usdc").is_file())
    if taken:
        shutil.copytree(made / LAYERS, assets / LAYERS, dirs_exist_ok=True, copy_function=shutil.copyfile)
    for model in taken:
        (assets / f"{model}.usdc").rename(assets / f"{model}_baked.usdc")
        stack = Sdf.Layer.CreateNew(str(assets / f"{model}.usdc"))
        stack.subLayerPaths = [f"./{LAYERS}/{model}.usda", f"./{model}_baked.usdc"]
        stack.defaultPrim = model
        stack.pseudoRoot.SetInfo("upAxis", "Y")
        stack.pseudoRoot.SetInfo("metersPerUnit", 1.0)
        stack.Save()
    return taken


def assembled(make):
    """The assembly's make with each screen row's picture laid over its baked asset after it (take), where the place
    has a screens output among the assembly's inputs."""
    @functools.wraps(make)
    def made(inputs, out, seed, params):
        make(inputs, out, seed, params)
        if "screens" in inputs:
            take(inputs["screens"], out)
    return made
