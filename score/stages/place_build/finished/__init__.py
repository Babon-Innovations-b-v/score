"""A place_build scene's finishes (#128, owner 2026-11-19 on a generator shown as plain clay: "i kinda see that finish
step being off more often"; his rule of 2026-10-18: every finish a library surface): each object's shown parts judged
against the library, and a model's own paint re-finished per part from the place's palette.

    faults(stage, place) -> {object: [fault]}       every object whose shown finish is not the library's
    paint(asset) -> Paint                            a model file's own paint: its faces' colours and its parts
    refinish(folder, name) -> answer                 the object's looks taken off; a paint that is not the library's
                                                     laid per part as the palette variants nearest its colours

A shown part wears the library's finish when it is bound to a look of the place (`/<place>/Looks`) naming a surface
the library holds (`score:surface`), or to its model's own paint when that paint is the library's: a model the surface
line painted from the library surfaces (LIBRARY_PAINT in its entry's provenance), or a character's dress under a
written exception (data/checks/library-exceptions.json, the player models' own texture: the library check's
exceptions, read at /<place>/Characters/<name>, the path that check gives a place's characters), or
to its model's own material when that names a surface the library holds (`score:surface`: an adopted set's model, its
materials taken in as library surfaces). A surface the library withdrew naming its replacement (`replaced_by`) is
judged by the end of that chain. Its faults:

- `no material`: a shown part bound to nothing, or to a placeholder (marked `score:placeholder`, or with no shader:
  a kit piece's part bound for a plain reader, score #156), so a plain grey and no finish;
- `own paint`: a shown part wearing its model's own paint that no library surface painted (a picture-made take, a
  TRELLIS.2 model's graded paint, a character no written exception covers, any entry the library has withdrawn);
- `unknown surface`: a look naming no surface, or one the library does not hold or has withdrawn;
- `one surface over its parts`: one look over the whole of a model whose own paint has PARTS or more parts
  (grade.parts: colour groups of at least grade.PART_SHARE, further than grade.PART_DELTA apart), every part then one
  flat paint, the clay the owner saw. A scan's own maps are not judged so (its colours are its stone's, not parts).
"""
import datetime
import json
import pathlib

import numpy as np
from PIL import Image
from pxr import Sdf, Usd, UsdGeom, UsdShade

from score.stages import place_build
from score.stages.complete.library import entries as library_entries
from score.stages.complete.library import exceptions as written
from score.stages.place_build.maker import grade

FAULT = "no library finish"
# The words of an entry's provenance that say the surface line painted every part of it from the library surfaces,
# the library check's own (complete/library/entries.py).
LIBRARY_PAINT = library_entries.LIBRARY_PAINT
EXCEPTED_KINDS = ("character",)  # a character's dress shows its own paint only under a written exception
PICTURE_MAKERS = ("pixal3d", "trellis2")  # the makers whose paint is a picture's, re-finished when laid
UNJUDGED_KINDS = ("light",)  # a sky dome laid as an object is light the renderer draws
PARTS = 2  # a model's own paint with this many parts or more is never one surface over its whole
SAMPLES = 4000  # faces drawn by area to find a paint's parts
SEED = 7
# The palette families a made prop's part may wear (a desk's top is never a cairn's stone, nor a ground's sand), a
# growing thing's among them where a place grows things (a sprout's leaf, stem and the soil in its pot: 2026-11-21, the
# greenhouse's crops wore hull paint for want of one), and the recipes it never takes from its colour alone (a glow,
# glass or print is laid by name).
PROP_FAMILIES = ("steel", "paint", "plastic", "fabric", "wood", "rubber", "copper", "leaf", "stem", "soil")
NOT_A_PAINT = ("glass", "glowing", "screen", "printed", "written")
PART = "paint"
GLOWS = ("glowing",)  # a look that gives off light, kept on its part when a library paint shows again  # the subsets a re-finish lays are paint0, paint1, ...


def text(prim, name):
    attribute = prim.GetAttribute(name)
    return attribute.Get() if attribute and attribute.HasAuthoredValue() else None


def record_of(prim):
    """The object's library entry record, or None."""
    address = text(prim, "score:library")
    if not address or "@" not in address:
        return None
    try:
        return place_build.entry_of(address)
    except place_build.Refused:
        return None


def excepted(prim, exceptions=None):
    """The written exception in force covering the character's finish (`exceptions`, else the file's), or None."""
    place = prim.GetPath().GetPrefixes()[0].name
    listed = written.read() if exceptions is None else exceptions
    return written.matching(listed, place, f"/{place}/Characters/{prim.GetName()}", "finish", datetime.date.today())


def withdrawn(record):
    """Whether the library withdrew the entry (a withdrawn entry is no library's: the library check's rule too)."""
    return (record or {}).get("state") == library_entries.WITHDRAWN


def library_painted(prim, record, exceptions=None):
    """Whether the object's own paint may show: LIBRARY_PAINT on an entry the library holds, or a character's dress
    under a written exception."""
    if withdrawn(record):
        return False
    if text(prim, "score:kind") in EXCEPTED_KINDS:
        return bool(excepted(prim, exceptions))
    told = json.dumps((record or {}).get("provenance", {}))
    return any(words in told for words in LIBRARY_PAINT)


def picture_made(record):
    """Whether the entry's shape and paint were made from a picture (a take, a Pixal3D or TRELLIS.2 model)."""
    record = record or {}
    makers = {step.get("by") for step in record.get("provenance", {}).get("made_with", [])}
    return record.get("kind") == "take" or bool(makers & set(PICTURE_MAKERS))


def is_scan(record):
    """Whether the entry is a scan whose own maps are its material's (Poly Haven, ambientCG)."""
    told = json.dumps((record or {}).get("provenance", {})).lower()
    return "polyhaven" in told or "ambientcg" in told


def shown(prim):
    imageable = UsdGeom.Imageable(prim)
    return (imageable.ComputeVisibility() != UsdGeom.Tokens.invisible
            and imageable.ComputePurpose() in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render))


def placeholder(material):
    """Whether a bound material is a placeholder, no finish: marked `score:placeholder` (dome_shell.placeholder and
    score_lib kit-parts: a part's plain grey, bound so a plain reader splits and draws it, #156), or with no shader."""
    return bool(text(material, "score:placeholder")) or not any(inside.IsA(UsdShade.Shader)
                                                                 for inside in Usd.PrimRange(material))


def bound_parts(gprim):
    """[(part, its bound material or None)]: each material-bound subset of the gprim, else the gprim."""
    subsets = UsdShade.MaterialBindingAPI(gprim).GetMaterialBindSubsets()
    found = []
    for part in [subset.GetPrim() for subset in subsets] or [gprim]:
        material, _ = UsdShade.MaterialBindingAPI(part).ComputeBoundMaterial()
        found.append((part, material.GetPrim() if material else None))
    return found


# --- a model's own paint ------------------------------------------------------------------------------------------

class Paint:
    """A model file's own paint: per shown mesh (its path under the file's default prim) its faces' CIELAB colours
    (None where a face has no colour) and areas; its parts (grade.parts) and each face's part."""

    def __init__(self, meshes):
        self.meshes = meshes  # {relative path: (colours (F, 3) or None, areas (F,))}
        coloured = [(colours, areas) for colours, areas in meshes.values() if colours is not None and areas.sum() > 0]
        self.parts = []
        if coloured:
            colours = np.concatenate([colours for colours, _ in coloured])
            areas = np.concatenate([areas for _, areas in coloured])
            drawn = np.random.default_rng(SEED).choice(len(colours), SAMPLES, p=areas / areas.sum())
            self.parts = grade.parts(colours[drawn])

    def part_of(self, relative):
        """Each face of the mesh: the index of the part nearest its colour."""
        colours, _ = self.meshes[relative]
        centres = np.array([centre for centre, _ in self.parts])
        return np.linalg.norm(colours[:, None] - centres[None], axis=-1).argmin(1)


PICTURES = {}  # {resolved path: its pixels as sRGB floats}


def picture(path):
    if path not in PICTURES:
        PICTURES[path] = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return PICTURES[path]


def colour_source(material):
    """(the base colour picture's path or None, the constant sRGB colour or None) of a material's preview surface."""
    for shader in Usd.PrimRange(material):
        colour = UsdShade.Shader(shader).GetInput("diffuseColor") if shader.IsA(UsdShade.Shader) else None
        if not colour:
            continue
        sources = colour.GetConnectedSources()[0]
        if sources:
            texture = UsdShade.Shader(sources[0].source.GetPrim()).GetInput("file")
            value = texture.Get() if texture else None
            return (value.resolvedPath or None) if value else None, None
        if colour.Get() is not None:
            return None, grade.encoded(np.array(colour.Get(), dtype=np.float64))
    return None, None


def face_areas(points, counts, indices):
    """Each face's area, fanned from its first corner."""
    areas = np.zeros(len(counts))
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    for corner in range(1, int(counts.max()) - 1):
        faces = np.nonzero(counts > corner + 1)[0]
        first = points[indices[starts[faces]]]
        second = points[indices[starts[faces] + corner]]
        third = points[indices[starts[faces] + corner + 1]]
        areas[faces] += 0.5 * np.linalg.norm(np.cross(second - first, third - first), axis=1)
    return areas


def face_uvs(mesh, counts, indices):
    """Each face's middle in its texture coordinates, or None when the mesh has none."""
    primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
    values = primvar.ComputeFlattened() if primvar else None
    if values is None or len(values) == 0:
        return None
    values = np.asarray(values, dtype=np.float64)
    corners = values if primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying else values[indices]
    face = np.repeat(np.arange(len(counts)), counts)
    middles = np.zeros((len(counts), 2))
    np.add.at(middles, face, corners)
    return middles / counts[:, None]


def texel_colours(path, uvs):
    pixels = picture(path)
    tall, wide = pixels.shape[:2]
    columns = np.clip((np.mod(uvs[:, 0], 1.0) * wide).astype(int), 0, wide - 1)
    rows = np.clip(((1.0 - np.mod(uvs[:, 1], 1.0)) * tall).astype(int), 0, tall - 1)
    return pixels[rows, columns].astype(np.float64)


def mesh_paint(mesh_prim):
    """(face CIELAB colours or None, face areas) of a mesh under its own materials."""
    mesh = UsdGeom.Mesh(mesh_prim)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=np.int64)
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=np.int64)
    points = np.asarray(mesh.GetPointsAttr().Get() or [], dtype=np.float64)
    if not len(counts) or not len(points):
        return None, np.zeros(len(counts))
    areas = face_areas(points, counts, indices)
    colours = np.full((len(counts), 3), np.nan)
    uvs = None
    for part, material in bound_parts(mesh_prim):
        faces = (np.asarray(UsdGeom.Subset(part).GetIndicesAttr().Get(), dtype=np.int64)
                 if part.IsA(UsdGeom.Subset) else np.arange(len(counts)))
        if material is None or not len(faces) or placeholder(material):
            continue
        path, constant = colour_source(material)
        if path:
            uvs = face_uvs(mesh, counts, indices) if uvs is None else uvs
            if uvs is not None:
                colours[faces] = texel_colours(path, uvs[faces])
        elif constant is not None:
            colours[faces] = constant
    known = ~np.isnan(colours[:, 0])
    if not known.any():
        return None, areas
    found = np.zeros_like(colours)
    found[known] = grade.lab(colours[known])
    return found, np.where(known, areas, 0.0)


PAINTS = {}  # {model file: its Paint}


def paint(asset):
    """The model file's own paint (cached by its path)."""
    asset = str(pathlib.Path(asset).resolve())
    if asset not in PAINTS:
        stage = Usd.Stage.Open(asset)
        top = stage.GetDefaultPrim() or next(iter(stage.GetPseudoRoot().GetChildren()), None)
        meshes = {}
        for inside in Usd.PrimRange(top, Usd.TraverseInstanceProxies()) if top else ():
            if inside.IsA(UsdGeom.Mesh) and shown(inside):
                meshes[str(inside.GetPath().MakeRelativePath(top.GetPath()))] = mesh_paint(inside)
        PAINTS[asset] = Paint(meshes)
    return PAINTS[asset]


def model_file(prim):
    """The model file the object references (its first reference), or None."""
    for spec in prim.GetPrimStack():
        for reference in spec.referenceList.GetAddedOrExplicitItems():
            if reference.assetPath:
                return pathlib.Path(Sdf.ComputeAssetPathRelativeToLayer(spec.layer, reference.assetPath))
    return None


# --- the judgement ------------------------------------------------------------------------------------------------

def held_surface(address, surfaces):
    """Whether the library holds the surface `address` names in force: it, or the end of the replacements a withdrawn
    one names (#155: a place laid before a surface was replaced still wears the library's); `surfaces` caches each
    answer."""
    if address not in surfaces:
        try:
            end = place_build.resolved_address(address, place_build.library_root())
            record = place_build.entry_of(end)
            surfaces[address] = record["kind"] == "surface" and not withdrawn(record)
        except (place_build.Refused, ValueError):
            surfaces[address] = False
    return surfaces[address]


def look_fault(look, surfaces):
    """Why a look of the place is no library surface, or None."""
    address = text(look, "score:surface")
    if not address:
        return f"look {look.GetName()} names no library surface"
    return None if held_surface(address, surfaces) else (f"look {look.GetName()} names {address}, which the library "
                                                         "does not hold (or has withdrawn)")


def provenance_words(record):
    made = (record or {}).get("provenance", {}).get("made_with", [])
    return ", ".join(sorted({step.get("by", "?") for step in made})) or "no provenance"


def own_surface(material, surfaces):
    """Whether a model's own material names a surface the library holds in force (`score:surface`: an adopted set's
    model, its materials taken in as library surfaces, #155)."""
    address = text(material, "score:surface")
    return bool(address) and held_surface(address, surfaces)


def own_paint_why(prim, record):
    """Why the object's own paint is a fault, and its mend."""
    if withdrawn(record):
        return f"lays {text(prim, 'score:library')}, which the library has withdrawn: lay an entry it holds"
    if text(prim, "score:kind") in EXCEPTED_KINDS:
        return ("a character wearing its own paint, which no written exception covers "
                "(data/checks/library-exceptions.json)")
    return (f"wears its model's own paint ({provenance_words(record)}), which no library surface painted: "
            "`refinish` it per part from the palette")


def object_faults(prim, place, surfaces, exceptions):
    """The object's finish faults: one a kind, with the parts it covers (its instances' parts too: an adopted model's
    shapes and materials stand under an instanceable prim, #155)."""
    record = record_of(prim)
    looks = f"/{place}/Looks"
    told = {}
    for inside in Usd.PrimRange(prim, Usd.TraverseInstanceProxies()):
        if not (inside.IsA(UsdGeom.Gprim) and shown(inside)):
            continue
        for part, material in bound_parts(inside):
            if material is None or placeholder(material):
                kind, why = "no material", "no material: a default grey"
            elif str(material.GetPath()).startswith(looks + "/"):
                why = look_fault(material, surfaces)
                kind = "unknown surface" if why else None
            elif library_painted(prim, record, exceptions) or (not withdrawn(record)
                                                                and own_surface(material, surfaces)):
                kind = None
            else:
                kind, why = "own paint", own_paint_why(prim, record)
            if kind:
                told.setdefault(kind, {"fault": FAULT, "kind": kind, "why": why, "parts": []})["parts"].append(
                    str(part.GetPath()))
    whole = prim.GetStage().GetPrimAtPath(f"{looks}/{prim.GetName()}")
    asset = model_file(prim)
    named = part_looks(prim.GetStage(), place, prim)
    if whole and not named and asset and asset.exists() and not is_scan(record):
        parts = paint(asset).parts
        if len(parts) >= PARTS:
            colours = ", ".join("#" + "".join(f"{round(value * 255):02x}" for value in grade.srgb(centre))
                                for centre, _ in parts)
            told["one surface over its parts"] = {
                "fault": FAULT, "kind": "one surface over its parts", "parts": [str(prim.GetPath())],
                "why": (f"one look ({text(whole, 'score:surface')}) over the whole of a model whose own paint has "
                        f"{len(parts)} parts ({colours}): every part one flat paint; `refinish` it")}
    for fault in told.values():
        fault["count"] = len(fault["parts"])
        fault["parts"] = fault["parts"][:5]
    return list(told.values())


def faults(stage, place, exceptions=None):
    """{object: [fault]} of every object of /<place>/Objects whose shown finish is not the library's; the written
    exceptions are `exceptions`, else the file's."""
    found, surfaces = {}, {}
    exceptions = written.read() if exceptions is None else exceptions
    objects = stage.GetPrimAtPath(f"/{place}/Objects")
    for prim in objects.GetChildren() if objects else ():
        if text(prim, "score:kind") in UNJUDGED_KINDS:
            continue
        told = object_faults(prim, place, surfaces, exceptions)
        if told:
            found[prim.GetName()] = told
    return found


# --- the re-finish ------------------------------------------------------------------------------------------------

def layers_of(prim):
    """The names of the model's own extra layers laid with it (a monitor's lit screen), which keep their looks."""
    return {child.GetName() for child in prim.GetChildren() if place_build.is_layer(child)}


def part_looks(stage, place, prim):
    """The looks of the object's parts (`<object>__<part>`), its laid layers' left out."""
    looks = stage.GetPrimAtPath(f"/{place}/Looks")
    keep = {f"{prim.GetName()}__{layer}" for layer in layers_of(prim)}
    return [look for look in (looks.GetChildren() if looks else ())
            if look.GetName().startswith(prim.GetName() + "__") and look.GetName() not in keep]


def taken_off(stage, place, prim):
    """The object's looks (its laid layers' kept), its laid surface marks, its bindings and an earlier re-finish's
    parts taken off, so its model's own paint shows."""
    whole = stage.GetPrimAtPath(f"/{place}/Looks/{prim.GetName()}")
    for look in part_looks(stage, place, prim) + ([whole] if whole else []):
        stage.RemovePrim(look.GetPath())
    for name in ("score:surface", "score:surface:colour"):
        prim.RemoveProperty(name)
    layers = layers_of(prim)
    for inside in list(Usd.PrimRange(prim, Usd.PrimAllPrimsPredicate)):
        if any(inside.GetPath().HasPrefix(prim.GetPath().AppendChild(layer)) for layer in layers):
            continue
        if is_refinish_part(inside):
            stage.RemovePrim(inside.GetPath())
            continue
        inside.RemoveProperty(UsdShade.Tokens.materialBinding)
        if inside.IsA(UsdGeom.Subset) and not inside.IsActive():
            inside.ClearActive()


def instances_opened(prim):
    """Every instanceable prim inside the object made plain in the place's own layer (a SimReady model's parts each
    stand as an instance of a shared prototype, and USD refuses an edit under an instance proxy, #156), nested ones
    too, so a re-finish's subsets and bindings are laid on the object's own copy of each part; the model file is never
    changed."""
    while True:
        instances = [inside for inside in Usd.PrimRange(prim) if inside.IsInstance()]
        if not instances:
            return
        for instance in instances:
            instance.SetInstanceable(False)


def is_refinish_part(prim):
    return prim.IsA(UsdGeom.Subset) and prim.GetName().startswith(PART) and prim.GetName()[len(PART):].isdigit()


def refinish_undone(stage, place, prim):
    """An earlier re-finish taken off the object (its parts' looks and subsets, its model's own subsets active
    again), so a surface laid over its whole replaces it; any other part's look is kept."""
    for look in part_looks(stage, place, prim):
        part = look.GetName()[len(prim.GetName()) + 2:]
        if part.startswith(PART) and part[len(PART):].isdigit():
            stage.RemovePrim(look.GetPath())
    for inside in list(Usd.PrimRange(prim, Usd.PrimAllPrimsPredicate)):
        if is_refinish_part(inside):
            stage.RemovePrim(inside.GetPath())
        elif inside.IsA(UsdGeom.Subset) and not inside.IsActive():
            inside.ClearActive()


def variant_colours(folder):
    """{palette variant: its token's CIELAB colour} of the place's palette, the variants a made prop's part may wear
    (PROP_FAMILIES, no NOT_A_PAINT recipe)."""
    path = pathlib.Path(folder) / place_build.PALETTE
    if not path.exists():
        raise place_build.Refused("no palette: lay the place's surface library first (palette <folder> <materials.json>)")
    taken = json.loads(path.read_text())
    every = place_build.surface_library.variants(taken)
    return {name: grade.hex_lab(taken["tokens"][variant["token"]]) for name, variant in every.items()
            if variant.get("family") in PROP_FAMILIES and variant.get("recipe") not in NOT_A_PAINT
            and variant.get("token") in taken["tokens"]}


def nearest_variant(centre, colours):
    return min(colours, key=lambda name: float(np.linalg.norm(colours[name] - centre)))


def own_materials(mesh, count):
    """Each face's own material (the model's binding before any re-finish), or None."""
    owned = [None] * count
    for part, material in bound_parts(mesh):
        faces = (UsdGeom.Subset(part).GetIndicesAttr().Get() if part.IsA(UsdGeom.Subset) else range(count)) or ()
        for face in faces:
            owned[face] = material
    return owned


def parts_laid(stage, prim, painted):
    """The model's paint parts laid as face subsets paint<k> on its meshes in the scene (one face, one part), each
    bound to the model's own material most of its faces wore and the model's own colour subsets deactivated, so a
    part no look is laid on still shows the model's own paint; the parts with faces."""
    laid = set()
    for relative in painted.meshes:
        mesh = stage.GetPrimAtPath(prim.GetPath().AppendPath(relative))
        if not mesh or painted.meshes[relative][0] is None:
            continue
        owners = painted.part_of(relative)
        owned = own_materials(mesh, len(owners))
        for own in UsdShade.MaterialBindingAPI(mesh).GetMaterialBindSubsets():
            own.GetPrim().SetActive(False)
        for number in range(len(painted.parts)):
            faces = np.nonzero(owners == number)[0]
            if not len(faces):
                continue
            subset = UsdGeom.Subset.Define(stage, mesh.GetPath().AppendChild(f"{PART}{number}"))
            subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
            subset.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
            subset.CreateIndicesAttr([int(face) for face in faces])
            materials = [owned[face] for face in faces if owned[face] is not None]
            if materials:
                most = max(set(materials), key=materials.count)
                UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(UsdShade.Material(most))
            laid.add(number)
    return sorted(laid)


def earlier_look(stage, place, prim, library):
    """The look the object wore over its whole before the re-finish, to keep on one part: {"address", "hex", "colour"
    (CIELAB)}, its palette variant's address when it was one; None when it wore none, or when its model's paint is
    the library's and the look gives off no light (that paint then shows whole; a lantern's glow is kept)."""
    look = stage.GetPrimAtPath(f"/{place}/Looks/{prim.GetName()}")
    if not look:
        return None
    spec = json.loads(text(look, "score:recipe:spec") or "null")
    address = text(prim, "score:surface") or ""
    recipe = spec["recipe"] if spec else address.split("/")[-1].split("@")[0]
    hexed = text(prim, "score:surface:colour") or (spec.get("hex") if spec else None)
    if not hexed or (library and recipe not in GLOWS):
        return None
    variant = spec.get("library") if spec else None
    return {"address": f"palette/{variant}" if variant else address, "hex": None if variant else hexed,
            "colour": grade.hex_lab(hexed)}


def nearest_part(painted, laid, colour):
    return min(laid, key=lambda number: float(np.linalg.norm(painted.parts[number][0] - colour)))


def refinish(folder, name):
    """The object re-finished per part: its looks taken off; a paint the library made shows whole, but for the part
    nearest a glowing look it wore (a lantern's paper), which keeps that glow; a paint no library surface made is
    split into its parts, the one nearest the look it wore keeping that look and every other wearing the place's
    palette variant nearest its colour (`surface --part`)."""
    stage, place = place_build.opened(folder)
    path = str(place_build.scene_path(folder).resolve())
    held = path in place_build.HELD
    place_build.HELD[path] = stage
    try:
        prim = place_build.object_prim(stage, place, name)
        asset = model_file(prim)
        if asset is None or not asset.exists():
            raise place_build.Refused(f"{name} lays no model file to re-finish")
        library = library_painted(prim, record_of(prim))
        painted = paint(asset)
        earlier = earlier_look(stage, place, prim, library)
        if not library and not painted.parts:
            raise place_build.Refused(f"{name}'s model has no paint to read parts from: lay a surface on it")
        colours = None if library else variant_colours(folder)
        instances_opened(prim)
        taken_off(stage, place, prim)
        if library and earlier is None:
            return {"name": name, "finish": "its model's own library paint", "parts": len(painted.parts)}
        laid = parts_laid(stage, prim, painted)
        kept = nearest_part(painted, laid, earlier["colour"]) if earlier and laid else None
        chosen = {}
        for number in laid:
            part = f"{PART}{number}"
            if number == kept:
                place_build.surface(folder, name, earlier["address"], colour=earlier["hex"], part=part)
                chosen[part] = earlier["address"]
            elif not library:
                variant = nearest_variant(painted.parts[number][0], colours)
                place_build.surface(folder, name, f"palette/{variant}", part=part)
                chosen[part] = f"palette/{variant}"
            else:
                chosen[part] = "its model's own library paint"
        return {"name": name, "finish": "per part", "parts": chosen}
    finally:
        if not held:
            place_build.HELD.pop(path, None)
            stage.GetRootLayer().Save()
