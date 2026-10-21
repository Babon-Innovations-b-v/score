"""The surface line's bakes taken into a place's stage: its own bake's models over the seed's assets, the models of it
another place bakes (its surface data's `elsewhere`, read beside), each fixture laid from a released file re-pointed
at its bake, and each baked object stamped with its model's hash. The assembly takes them, and the settle stage
(score/stages/settling) drops the very models the assembly lays (2026-10-15: the settle dropped the seed's models, and
their rests, laid over the repainted bakes, tilted the hangar's control desk 2 degrees and left its keyboards on the
desk's sloping front, 3.5 to 18.7 degrees over). Its own module, so an edit of the assembly's other code moves no
settle key.
"""
import json
import pathlib
import shutil
import sys

from score.stages.assembly import made_waiting
from score.stages.assembly.record import BASE_LAYER
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))  # export, library and stage_inputs, read inside the functions
# A scene's surface data is its design's (surfaces/surface_data.DESIGN, named here so the surface package stays out
# of this code version); the old data/surfaces/<place>.json records were retired (owner, 2026-10-21).
DESIGN_SURFACES = PROPS_HOME / "design" / "surfaces"


def claiming_places(place):
    """The places whose surface line paints models this place lays (its design's surface data's `elsewhere`), read
    beside."""
    path = DESIGN_SURFACES / f"{place}.json"
    elsewhere = json.loads(path.read_text()).get("elsewhere", {}) if path.exists() else {}
    return sorted({claim["place"] for claim in elsewhere.values()})


def claimed_bakes(inputs, out):
    """(bake, paint, out, models) of each place whose bake holds models this place lays (its surface data's
    `elsewhere`, read beside: surfaces-bake@<place>), models as {the name this place lays: the name that place bakes
    it under} (`baked_as` in this place's own bake's elsewhere.json: the hangar lays parts_rack_1, old_station bakes
    the take as parts_rack), or the model's own name where that place bakes it under it with the claimed take (the
    hub's wrench_2: workshop bakes wrench_1 to wrench_4 from one take, each its own size; baked_as names wrench_1)."""
    found = []
    elsewhere = json.loads(pathlib.Path(inputs["surfaces"]).read_text()).get("elsewhere", {})
    claims = json.loads((pathlib.Path(inputs["surfaces-bake"]) / "elsewhere.json").read_text()) if elsewhere else {}
    for name, path in inputs.items():
        if name.startswith("surfaces-bake@"):
            other = name.split("@", 1)[1]
            baked = json.loads((pathlib.Path(path) / "baked.json").read_text())
            models = {model: model if baked.get(model, {}).get("parts") == claim["take"] else claims[model]["baked_as"]
                      for model, claim in elsewhere.items() if claim["place"] == other}
            found.append((pathlib.Path(path), pathlib.Path(inputs[f"surfaces-paint@{other}"]), out, models))
    return found


# How far a baked model's box may lie from the released file's it stands in for (metres): the same mesh, repainted.
BOX_TOLERANCE = 0.01


def take_bake(bake, paint, out, models=None):
    """The surface stage's baked models in place of the seed's: each model a place's bake made (or only `models` of
    it: {the name laid here: the name baked under}), written as the exporter writes an asset (tools/usd/export.
    write_asset: drawn mesh, collision, a subset per library surface from the paint's labelled parts) over the seed's
    assets/<model>.usdc and its maps."""
    import export
    import library
    variants = library.variants(library.theme_library())
    sounds = json.loads(export.SOUNDS.read_text())
    baked = json.loads((bake / "baked.json").read_text())
    models = models if models is not None else {model: model for model in baked}
    missing = [model for model, baked_as in models.items() if baked_as not in baked]
    if missing:
        raise FileNotFoundError(f"{bake}: its bake made none of {missing}, which this place lays by its claim")
    for model, baked_as in models.items():
        entry = baked[baked_as]
        (out / "assets" / f"{model}.usdc").unlink(missing_ok=True)
        parts, turn, size = laid_parts(bake / "made", baked_as, paint / "labelled" / entry["parts"], entry)
        export.write_asset(model, renamed_model(bake / "made", baked_as, model, out / "renamed"), {model: parts},
                           None, turn, size, out, variants, sounds)
        lay_fixtures_baked(out / BASE_LAYER, model)
        stamp_baked_hash(out / BASE_LAYER, model, bake / "made" / f"{baked_as}.gltf")
    shutil.rmtree(out / "renamed", ignore_errors=True)


def laid_parts(made, baked_as, labelled, entry):
    """What names a baked model's surfaces, as (parts folder, turn, size) for export.write_asset: the take's labelled
    parts laid with its bake entry's turn and size; for a model the bake built over a body (make_chunky.make_bodied)
    the parts it laid itself beside the model (`<model>.parts`, already in the kit frame: no turn, its own box)."""
    import numpy as np
    import trimesh
    laid = made / f"{baked_as}.parts"
    if not laid.is_dir():
        return labelled, entry["base"], entry["size"]
    points = np.vstack([trimesh.load(path, process=False).vertices for path in sorted(laid.glob("*.ply"))])
    return laid, [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0], (points.max(axis=0) - points.min(axis=0)).tolist()


def renamed_model(made, baked_as, model, scratch):
    """The folder holding `model`.gltf: the bake's own when it baked the model under that name, else `scratch` with
    a copy of its .gltf under the laid name, its buffer and pictures pointing back into the bake's folder."""
    if baked_as == model:
        return made
    document = json.loads((made / f"{baked_as}.gltf").read_text())
    for entry in document["buffers"] + document.get("images", []):
        entry["uri"] = str((made / entry["uri"]).resolve())
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / f"{model}.gltf").write_text(json.dumps(document))
    return scratch


def lay_fixtures_baked(base, model):
    """Every object of the base layer laid from a world file of `model` (score:model the released file, its stem the
    model's name: the launch's rocket, a plan object, laid the seed's paint until 2026-10-15) referencing the
    assembly's baked asset of it instead and named by it, so stamp_baked_hash stamps it. The bake keeps the released
    model's frame (the same mesh, repainted), so its placement stands; a baked box that differs from the laid one
    fails here rather than stand the object wrong."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(base))
    folder = pathlib.Path(base).parent
    baked = f"../assets/{model}.usdc"
    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        spec = layer.GetPrimAtPath(path) if path.IsPrimPath() else None
        named = spec.attributes["score:model"].default if spec and "score:model" in spec.attributes else None
        if named is None or named == model or pathlib.PurePosixPath(named).stem != model:
            continue
        new_box = made_waiting.asset_bounds(folder / baked)
        for laid in spec.referenceList.prependedItems:
            old_box = made_waiting.asset_bounds(folder / laid.assetPath)
            if any(abs(old_box[end][axis] - new_box[end][axis]) > BOX_TOLERANCE for end in (0, 1) for axis in range(3)):
                raise ValueError(f"{path}: the baked {model} spans {new_box}, the laid {laid.assetPath} {old_box}: "
                                 "the bake moved the model's frame")
        spec.referenceList.prependedItems = [Sdf.Reference(baked)]
        spec.attributes["score:model"].default = model
    layer.Save()


def stamp_baked_hash(base, model, gltf):
    """Every object of the base layer that lays `model` carries the baked file's hash (score:model_sha256,
    stage_inputs.model_hash, which the completion gate reads) in place of the seed's, and the seed's as the model the
    bake repainted (score:repaint_of, which the pick lock reads: a pick chooses the model, never its old paint)."""
    from pxr import Sdf
    import stage_inputs  # not complete.py: an edit to the gate re-makes no assembly
    layer = Sdf.Layer.FindOrOpen(str(base))
    sha256 = stage_inputs.model_hash(gltf)
    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        spec = layer.GetPrimAtPath(path) if path.IsPrimPath() else None
        if spec is None or "score:model" not in spec.attributes or spec.attributes["score:model"].default != model:
            continue
        before = {name: spec.attributes[name].default for name in ("score:model_sha256", "score:repaint_of")
                  if name in spec.attributes}
        for name, value in (("score:repaint_of", before.get("score:repaint_of") or before.get("score:model_sha256")),
                            ("score:model_sha256", sha256)):
            if value is None:
                continue
            attribute = spec.attributes[name] if name in spec.attributes else \
                Sdf.AttributeSpec(spec, name, Sdf.ValueTypeNames.String)
            attribute.default = value
    layer.Save()
