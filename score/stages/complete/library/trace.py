"""Trace everything a place's assembled OpenUSD stage shows to the library, or to a written exception (pxr, read
only; no store, no library code).

    things = trace.things(stage)                 # [(prim, kind)]: what the place shows, one prim a thing
    rows = trace.rows(stage, context)            # one row an aspect a thing: where it comes from, and its finishes

A thing is a model (`score:model`, or a reference to a model file), a neighbour place, ground, sky, a code-built
structure, a character, an effect's emitter, a light, a sound source, or loose geometry no thing holds. Its source
traces, in this order, by the provenance attribute the export writes (`score:library`, an entry's address), a place
by its name, a model by the gltf it was built from (`score:model_sha256`, an entry's `model_sha256`), by the prim
its entry's provenance names, or by the content hash of a file it is made of (its layers, references, payloads and
asset paths) held by an entry of its kind. Its finishes trace, each bound material once, by `score:library`, by the
library surface it names (`score:surface` on the material or the bound part, else a material of the place's
`Library` scope by its name), or by its model's finish record (a bake of the surface stage, the crops or a ship kit,
which paints every part from the library: `context.baked`). A thing that traces neither way is under a written
exception or is a finding; a part with no material is a default grey, and a finding.
"""
import dataclasses
import datetime
import os
import posixpath

from pxr import Sdf, Usd, UsdGeom, UsdLux, UsdShade

from score.stages.complete.library import exceptions as written

LIBRARY_ATTR = "score:library"
KIND_ATTR = "score:kind"
# ground: a terrain piece is a model (the ground kind is retired, #47)
LIBRARY_KINDS = {"model": ("model",), "place": ("place",), "ground": ("model",), "structure": ("model", "kit"),
                 "character": ("character",), "effect": ("effect",), "light": ("light",), "sky": ("light",),
                 "sound": ("sound",), "geometry": ("model", "light")}
PRUNED = ("model", "place", "character", "effect", "light", "sound")  # their prims below are theirs
FINISHED = ("model", "structure", "ground", "character", "geometry", "sky")  # the things whose finishes are judged
SHOWN_PURPOSES = (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)
LIBRARY, EXCEPTION, NEITHER = "library", "exception", "neither"
DEFAULT_GREY = "no material: a default grey"


@dataclasses.dataclass
class Context:
    place: str
    shelf: object  # entries.Shelf
    blobs: str = ""  # the folder whose files are named by their sha256 (the store's blobs)
    baked: dict = dataclasses.field(default_factory=dict)  # model gltf sha256: the bake node that painted it
    exceptions: list = dataclasses.field(default_factory=list)
    today: datetime.date = dataclasses.field(default_factory=datetime.date.today)


def authored(prim, name):
    """An attribute's authored value, or None."""
    attribute = prim.GetAttribute(name)
    return attribute.Get() if attribute and attribute.HasAuthoredValue() else None


def arcs(prim):
    """The asset paths of the prim's references and payloads, with the layer each was written in."""
    found = []
    for spec in prim.GetPrimStack():
        for item in [*spec.referenceList.GetAddedOrExplicitItems(), *spec.payloadList.GetAddedOrExplicitItems()]:
            if item.assetPath:
                found.append((spec.layer, item.assetPath))
    return found


def is_light(prim):
    return prim.HasAPI(UsdLux.LightAPI) or prim.GetTypeName().endswith("Light")


def thing_kind(prim):
    """What a prim is as a thing of the place, or None when it is not one."""
    kind = authored(prim, KIND_ATTR)
    if kind == "place" or authored(prim, "score:place"):
        return "place"
    if is_light(prim):
        return "light"
    if prim.GetTypeName() == "SpatialAudio":
        return "sound"
    if prim.HasAttribute("score:effect:kind"):
        return "effect"
    if kind in ("ground", "structure"):
        return kind
    if kind in ("sky", "stars"):
        return "sky"
    if authored(prim, "score:model") or arcs(prim):
        return "character" if "/Characters/" in str(prim.GetPath()) else "model"
    return "geometry" if prim.IsA(UsdGeom.Gprim) else None


def things(stage):
    """[(prim, kind)] of every thing the stage shows; a pruned thing's prims below are its own."""
    found = []
    walk = iter(Usd.PrimRange(stage.GetPseudoRoot()))
    for prim in walk:
        kind = thing_kind(prim)
        if not kind:
            continue
        found.append((prim, kind))
        if kind in PRUNED:
            walk.PruneChildren()
    return found


# --- where a thing comes from ----------------------------------------------------------------------------------

def sha_of(path, context):
    """The sha256 of a stored file, from its path: a store blob is named by it."""
    real = os.path.realpath(path) if path else ""
    folder, name = os.path.split(real)
    return name if context.blobs and folder == context.blobs else None


def resolved(layer, asset_path):
    return layer.ComputeAbsolutePath(asset_path) if layer else asset_path


def asset_values(prim):
    """The resolved paths of the prim's asset-valued attributes (texture files, sound files, clips)."""
    found = []
    for attribute in prim.GetAuthoredAttributes():
        value_type = attribute.GetTypeName()
        if value_type not in (Sdf.ValueTypeNames.Asset, Sdf.ValueTypeNames.AssetArray):
            continue
        value = attribute.Get()
        items = [value] if value_type == Sdf.ValueTypeNames.Asset else list(value or [])
        found += [item.resolvedPath or item.path for item in items if item and item.path]
    return found


def made_of(prim, context):
    """The sha256 of every stored file the thing is made of: the layers it is written in, what it references, and its
    asset paths, through every prim below it."""
    found = []
    for part in Usd.PrimRange(prim):
        for spec in part.GetPrimStack():
            found.append(sha_of(spec.layer.realPath, context))
        found += [sha_of(resolved(layer, path), context) for layer, path in arcs(part)]
        found += [sha_of(path, context) for path in asset_values(part)]
    return [sha for sha in dict.fromkeys(found) if sha]


def traced_source(prim, kind, context):
    """(address, how) of the library entry the thing comes from, or (None, None)."""
    shelf, kinds, path = context.shelf, LIBRARY_KINDS[kind], str(prim.GetPath())
    named = authored(prim, LIBRARY_ATTR)
    if named and shelf.has(named):
        return named, "its score:library attribute"
    if kind == "place":
        address = shelf.of_id("place", authored(prim, "score:place") or prim.GetName())
        return (address, "the place by name") if address else (None, None)
    model_sha = authored(prim, "score:model_sha256")
    if model_sha and shelf.of_model(model_sha):
        return shelf.of_model(model_sha), "the gltf it was built from"
    address = shelf.of_prim(context.place, path, kinds)
    if address:
        return address, "the prim its entry names"
    for sha in made_of(prim, context):
        address = shelf.of_sha(sha, kinds)
        if address:
            return address, "the content hash of a file it is made of"
    return None, None


def source_instead(prim, kind):
    """What the thing is instead of a library entry, in words."""
    said = authored(prim, "score:from") or authored(prim, "score:sound:from") or authored(prim, "score:effect:from")
    files = [posixpath.basename(path) for _, path in arcs(prim)]
    if files:
        return f"a {kind} from {', '.join(files[:2])}, a file no library {kind} entry holds"
    if said:
        return f"a {kind} made from {str(said)[:120]}, with no library entry"
    return f"a {kind} with no library entry"


def group_of(prim, kind):
    """The name the cockpit groups a thing's findings under: its kind of piece, else its kind."""
    return str(authored(prim, KIND_ATTR) or authored(prim, "score:model") or authored(prim, "score:sound:name")
               or authored(prim, "score:effect:kind") or kind)


def judged(row, prim_paths, context):
    """The row answered: the library when it traced, else the first exception covering one of the paths, else
    neither."""
    if row["by"]:
        return dict(row, answer=LIBRARY)
    for path in prim_paths:
        exception = written.matching(context.exceptions, context.place, path, row["aspect"], context.today)
        if exception:
            return dict(row, answer=EXCEPTION, by=exception["why"],
                        how=f"an exception allowed by {exception['allowed_by']} on {exception['allowed_on']}")
    return dict(row, answer=NEITHER)


def source_row(prim, kind, context):
    address, how = traced_source(prim, kind, context)
    path = str(prim.GetPath())
    row = {"aspect": "source", "kind": kind, "prim": path, "group": group_of(prim, kind), "by": address, "how": how,
           "instead": None if address else source_instead(prim, kind)}
    return judged(row, [path], context)


# --- a thing's finishes ----------------------------------------------------------------------------------------

def shown(prim):
    imageable = UsdGeom.Imageable(prim)
    return (imageable.ComputeVisibility() != UsdGeom.Tokens.invisible
            and imageable.ComputePurpose() in SHOWN_PURPOSES)


def bound_parts(gprim):
    """[(material or None, part)]: each material-bound subset of the gprim with its material, else the gprim's own."""
    subsets = UsdShade.MaterialBindingAPI(gprim).GetMaterialBindSubsets()
    parts = [subset.GetPrim() for subset in subsets] or [gprim]
    found = []
    for part in parts:
        material, _ = UsdShade.MaterialBindingAPI(part).ComputeBoundMaterial()
        found.append((material.GetPrim() if material else None, part))
    return found


def finishes(prim):
    """{material path ("" for none): (material prim or None, [parts bound to it])} of the shown gprims of a thing."""
    found = {}
    for part in Usd.PrimRange(prim):
        if part.IsA(UsdGeom.Gprim) and shown(part):
            for material, piece in bound_parts(part):
                key = str(material.GetPath()) if material else ""
                found.setdefault(key, (material, []))[1].append(piece)
    return found


def traced_finish(material, pieces, thing, context):
    """(address or bake node, how) the finish traces to, or (None, None)."""
    if material is None:
        return None, None
    named = authored(material, LIBRARY_ATTR)
    if named and context.shelf.has(named):
        return named, "its score:library attribute"
    surface = authored(material, "score:surface") or next(
        (authored(piece, "score:surface") for piece in pieces if authored(piece, "score:surface")), None)
    if surface and context.shelf.surface(surface, context.place):
        return context.shelf.surface(surface, context.place), "the library surface it names"
    if material.GetParent().GetName() == "Library" and context.shelf.surface(material.GetName(), context.place):
        return context.shelf.surface(material.GetName(), context.place), "the place's library material by name"
    node = context.baked.get(authored(thing, "score:model_sha256"))
    if node:
        return node, "its model's finish record (every part painted from the library)"
    return None, None


def texture_files(material):
    """The file names of the textures the material's shaders read."""
    found = []
    for shader in Usd.PrimRange(material):
        for attribute in shader.GetAuthoredAttributes():
            value = attribute.Get()
            if isinstance(value, Sdf.AssetPath) and value.path:
                found.append(posixpath.basename(value.path))
    return list(dict.fromkeys(found))


def constant_colour(material):
    """The diffuse colour a material's preview surface holds, or None."""
    for shader in Usd.PrimRange(material):
        colour = authored(shader, "inputs:diffuseColor")
        if colour is not None:
            return tuple(round(float(channel), 3) for channel in colour)
    return None


def finish_instead(material, pieces, context):
    """What the finish is instead of a library surface, in words."""
    if material is None:
        return DEFAULT_GREY
    surface = authored(material, "score:surface")
    if surface:
        return f"material {material.GetName()} names surface {surface}, which the library does not hold"
    files = texture_files(material)
    if files:
        more = f" and {len(files) - 3} more" if len(files) > 3 else ""
        return (f"material {material.GetName()}: texture files {', '.join(files[:3])}{more}, which no library "
                "surface or finish record names")
    colour = constant_colour(material)
    return f"material {material.GetName()}, " + (f"a constant colour {colour}" if colour else "with no colour set")


def finish_rows(prim, kind, context):
    """One row a material the thing's shown parts are bound to (and one for its parts with none)."""
    rows = []
    thing_path, group = str(prim.GetPath()), group_of(prim, kind)
    for key, (material, pieces) in sorted(finishes(prim).items()):
        address, how = traced_finish(material, pieces, prim, context)
        name = material.GetName() if material else "no material"
        row = {"aspect": "finish", "kind": kind, "prim": thing_path, "material": key or None,
               "group": f"{group}: {name}", "parts": len(pieces), "by": address, "how": how,
               "instead": None if address else finish_instead(material, pieces, context)}
        rows.append(judged(row, [thing_path] + ([key] if key else []), context))
    return rows


def rows(stage, context):
    """Every row of the stage: one for each thing's source, one for each of its finishes."""
    found = []
    for prim, kind in things(stage):
        found.append(source_row(prim, kind, context))
        if kind in FINISHED:
            found += finish_rows(prim, kind, context)
    return found
