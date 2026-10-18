"""The place's own layout as its scene record and kit now give it, written over its round-three seed: shared by the
assembly, the motion stage and the light stage (each lays the place as the assembly does before its layers). A
stage that imports this module alone (`import score.stages.assembly.record as record`) hashes it and not the
assembly's __init__, so the assembly's own edits move none of its keys.

    take_record   the accepted scene record over the seed base's record prims, an entry waiting on its model laid
                  nowhere and named; the kit laid first
    take_ground   the terrain stage's made ground as layers/ground.usdc, held by the root (hold: its sublayers in ORDER)
    relay_kit     every kit piece at its kit spot now, where the seed laid it elsewhere (a kit edited after the
                  round-three export: the garage's fourth pressure gauge moved off the big door's leaf track)
"""
import json
import pathlib
import shutil

# The base's prims tools/usd/scene.py writes from the scene record, removed before the accepted record is written.
RECORD_ROOTS = ("Structure", "Terrain", "Water", "Fixtures", "Rocks", "Places", "Sky", "Lights", "Environment",
                "Shafts")
RECORD = "scene.json"
# The root prim's list of the record's entries that wait on a model (contents.py's `waiting` check reads it).
WAITING = "score:waiting"
BASE_LAYER = "./layers/base.usda"
GROUND_LAYER = "layers/ground.usdc"
# The root's sublayers, strongest first, by file name.
ORDER = ("edit", "characters", "sound", "light", "motion", "effects", "crops", "machines", "settle", "ground", "base")
# How far a piece's transform may differ from the kit's (any matrix entry) and still stand where it is.
SAME = 1e-4


def take_record(inputs, out, place):
    """Every kit piece laid where the place's kit now puts it (relay_kit), and the place's scene record, written
    beside the stage (RECORD): its accepted scene-record output's, written over
    the seed base's record prims (RECORD_ROOTS removed, tools/usd/scene.py's writer run again on the base with the
    place's kit and ground record, as export.py runs it); for a place with none, the seed's own record, unverified.
    An entry the record marks `waiting` (its model not made yet) lays nothing: the place's root prim names it in
    WAITING, which the completion gate reports as a gap. Where the record came from, for origin.json."""
    moved = relay_kit(inputs, out, place)
    if "scene-record" not in inputs and "scene" not in inputs:
        return f"none: the place has no scene record{moved}"
    if "scene-record" not in inputs:
        shutil.copy2(inputs["scene"], out / RECORD)
        return f"the seed's record ({pathlib.Path(inputs['scene']).name}), unverified: no scene-record row{moved}"
    import ground as grounds
    import scene
    from pxr import Sdf, Usd
    made = pathlib.Path(inputs["scene-record"]) / "record" / f"{place}.json"
    shutil.copy2(made, out / RECORD)
    record = json.loads(made.read_text())
    kit = json.loads(pathlib.Path(inputs["kit"]).read_text())
    base = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    edit = Sdf.BatchNamespaceEdit()
    for name in RECORD_ROOTS:
        if base.GetPrimAtPath(f"/{place}/{name}"):
            edit.Add(f"/{place}/{name}", Sdf.Path.emptyPath)
    if not base.Apply(edit):
        raise RuntimeError(f"{place}: the seed's record prims could not be removed from its base")
    ground = grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))  # as export.py's main: None for a room
    stage = Usd.Stage.Open(base)
    laid, waiting = without_waiting(record)
    scene.write(stage, place, laid, out, kit=kit, pieces=laid_pieces(kit, record), ground=ground,
                near=near_patch(stage, place), tiles=inputs.get("surface-tiles"))
    if waiting:
        stage.GetPrimAtPath(f"/{place}").CreateAttribute(WAITING, Sdf.ValueTypeNames.StringArray).Set(waiting)
    base.Save()
    return f"scene-record@{place}{moved}"


def near_patch(stage, place):
    """The box (across, along) of the near ground the seed's base keeps at /<place>/Ground (export.py's ground_mesh
    drew it), which the record's planned ground runs on past, as export.py hands it to the writer; None with no near
    ground (a room)."""
    import numpy as np
    from pxr import UsdGeom
    prim = stage.GetPrimAtPath(f"/{place}/Ground")
    points = UsdGeom.Mesh(prim).GetPointsAttr().Get() if prim and prim.IsA(UsdGeom.Mesh) else None
    if not points:
        return None
    flat = np.asarray(points, dtype=float)[:, [0, 2]]
    return flat.min(axis=0), flat.max(axis=0)


def without_waiting(record):
    """The record less every entry it marks `waiting`, and those entries in words (`<part> <name>: <why>`)."""
    laid, waiting = {}, []
    for key, value in record.items():
        if isinstance(value, list):
            waiting += [f"{key} {entry.get('name', '?')}: {entry['waiting']}" for entry in value
                        if isinstance(entry, dict) and entry.get("waiting")]
            value = [entry for entry in value if not (isinstance(entry, dict) and entry.get("waiting"))]
        laid[key] = value
    return laid, waiting


def laid_pieces(kit, record):
    """A kit's pieces as the record's writer reads them for its lamps (scene.kit_lights): a walkway tube's on every
    bay of its way, each with its spot (export.tube_spots, as export.kit_room_pieces lays them); another's as laid."""
    if "bay" not in kit or not record.get("tube_length"):
        return kit["pieces"]
    import export
    return [dict(laid, spot=spot.tolist()) for laid in kit["pieces"]
            for spot in export.tube_spots(laid, record["tube_length"], float(kit["bay"]))]


def laid_kit(kit, record, out, place):
    """The kit's pieces as the exporter lays them: a kit room's in frames (export.kit_room_pieces, each with its
    matrix, from the made models the seed's inputs.json names; a walkway tube's on every bay of the record's way),
    moved as the record moves them; another's as laid. A kit room piece whose model the seed never had (one added to
    the kit since) keeps its name and no matrix: the seed has no object for it."""
    import export
    import scene
    pieces = kit["pieces"]
    if pieces and "x" in pieces[0]:
        named = json.loads((out / "inputs.json").read_text()).get("models", {})
        folders = sorted({str(pathlib.Path(entry["file"]).parent) for entry in named.values()})
        pieces = [found for laid in pieces for found in (
            export.kit_room_pieces(dict(kit, pieces=[laid]), folders, record.get("tube_length"), place)
            if export.model_file(folders, laid["model"]).exists() else unmade(kit, laid, record, place))]
    if record.get("moved"):
        pieces = scene.moved_pieces(pieces, record["moved"])
    return pieces


def unmade(kit, laid, record, place):
    """A kit room piece the seed has no model for, named as export.kit_room_pieces names it (its row, a glowing
    part's own), once a bay of its way for a tube's piece."""
    import export
    own = laid.get("row", export.kind_row(laid["kind"], (kit.get("room", ""), place)))
    row = f"{own}_{laid['part']}" if "part" in laid else own
    count = len(export.tube_spots(laid, record["tube_length"], float(kit["bay"]))) \
        if "bay" in kit and record.get("tube_length") else 1
    return [dict(laid, row=row, unmade=True)] * count


def transform_of(piece, ground):
    """A piece's transform as export.laid_object writes it (its ops copied here: export.py is in paid rows' code):
    its matrix, and its ops as (name, type, value) in their order."""
    import export
    import numpy as np
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    xform = UsdGeom.Xform.Define(stage, "/piece")
    if "matrix" in piece:
        xform.AddTransformOp().Set(Gf.Matrix4d(np.asarray(piece["matrix"]).T.tolist()))
    else:
        export.stand_on(xform, piece["at"], ground)
        export.turn_in_seat(xform, piece)
        xform.AddScaleOp().Set(Gf.Vec3f(float(piece.get("scale", 1.0))))
    ops = [(op.GetName(), op.GetAttr().GetTypeName(), op.Get()) for op in xform.GetOrderedXformOps()]
    return xform.GetLocalTransformation(), ops


def taken_out(stage, place, record):
    """Every seed object of a row the record's coordinator_removed names (`rows`) made inactive; their names."""
    rows = {row for entry in record.get("coordinator_removed", []) if isinstance(entry, dict)
            for row in entry.get("rows", [])}
    objects = stage.GetPrimAtPath(f"/{place}/Objects")
    gone = sorted(child.GetName() for child in (objects.GetChildren() if objects and rows else [])
                  if child.GetAttribute("score:row").Get() in rows)
    for name in gone:
        stage.GetPrimAtPath(f"/{place}/Objects/{name}").SetActive(False)
    return gone


def relay_kit(inputs, out, place):
    """Every kit piece laid at its kit spot now where the seed's base laid it elsewhere: its transform ops written
    anew in the base; every seed object of a row the record's coordinator_removed names (`rows`: the old station's
    cables, which its concept does not show) taken out. How many moved, how many kit pieces the seed has no object
    for and how many seed objects were taken out, as words for origin.json."""
    import export
    import ground as grounds
    from pxr import Sdf, Usd, UsdGeom
    kit = json.loads(pathlib.Path(inputs["kit"]).read_text())
    record_path = inputs.get("scene-record")
    record = json.loads((pathlib.Path(record_path) / "record" / f"{place}.json").read_text()) if record_path else \
        json.loads(pathlib.Path(inputs["scene"]).read_text()) if "scene" in inputs else {}
    pieces = laid_kit(kit, record, out, place)
    ground = None if pieces and "matrix" in pieces[0] else grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))
    base = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    stage = Usd.Stage.Open(base)
    moved, missing = [], []
    gone = taken_out(stage, place, record)
    for name, piece in zip(export.object_names(pieces), pieces):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if not prim or piece.get("unmade"):
            missing.append(name)
            continue
        then, ops = transform_of(piece, ground)
        now = UsdGeom.Xformable(prim).GetLocalTransformation()
        if all(abs(now[row][column] - then[row][column]) <= SAME for row in range(4) for column in range(4)):
            continue
        spec = base.GetPrimAtPath(prim.GetPath())
        for attribute in [spec.properties[key] for key in spec.properties.keys() if key.startswith("xformOp")]:
            spec.RemoveProperty(attribute)
        for op_name, kind, value in ops:
            prim.CreateAttribute(op_name, kind).Set(value)
        prim.CreateAttribute("xformOpOrder", Sdf.ValueTypeNames.TokenArray).Set([op_name for op_name, _, _ in ops])
        moved.append(name)
    base.Save()
    return (f"; kit: {len(moved)} pieces laid at their kit spot ({', '.join(moved[:8])}"
            f"{', ...' if len(moved) > 8 else ''})" if moved else "") + \
        (f"; {len(missing)} kit pieces the seed has no object for" if missing else "") + \
        (f"; {len(gone)} seed objects of removed rows taken out ({', '.join(gone[:8])})" if gone else "")


def hold(root, layer):
    """The root holding `layer` among its sublayers, all in ORDER (strongest first, by file name); one ORDER does
    not name goes just over the base."""
    from pxr import Sdf
    found = Sdf.Layer.FindOrOpen(str(root))
    layers = [path for path in found.subLayerPaths if path != layer] + [layer]

    def rank(path):
        stem = pathlib.PurePosixPath(path).stem
        return ORDER.index(stem) if stem in ORDER else ORDER.index("base") - 0.5

    found.subLayerPaths = sorted(layers, key=rank)
    found.Save()


def take_ground(grounds, place, root):
    """The place's made ground, when the terrain stage made one for it, sublayered just over the seed's base."""
    made = sorted(pathlib.Path(grounds).glob(f"*/places/{place}.usdc"))
    if not made:
        return
    shutil.copy2(made[0], root.parent / GROUND_LAYER)
    hold(root, f"./{GROUND_LAYER}")
