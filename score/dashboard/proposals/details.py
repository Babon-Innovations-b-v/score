"""A place's basket details on the store's machine, free: its free after (assemble.py's stage) as a 3D web copy, and
what changes between the place as it stands accepted and that after, read from the two OpenUSD stages: objects added,
removed, moved, reshaped and refinished, lamps, sounds and cameras, each change with its OpenUSD layer and its box
(the viewer marks it). Read with usd-core from linked stages; nothing in the store is written.

The before is the same stage row's accepted output (the place, with its neighbours when the after shows them), linked
as web3d/convert.py links it, so both sides compose the same way; a before's fingerprint is kept per output in the
basket's scratch folder (FINGERPRINTS), since it changes only when the accepted output does.
"""
import json
import os
import pathlib
import shutil
import tempfile

from score.dashboard.web3d import convert, facts

FINGERPRINTS = "fingerprints"
FINGERPRINT_VERSION = 2  # moves when what a fingerprint holds or how its stage is linked changes
MOVED_METRES = 0.01  # a box corner moved more than this: the object moved
LAMP_SHARE = 0.01  # a lamp's strength or colour moved more than this share: the lamp changed
MOST_LISTED = 400  # changes of one kind kept with their boxes; the count is kept whole


def blob_of(roots, sha):
    return next(path for path in (pathlib.Path(root) / "objects" / "blobs" / sha for root in roots) if path.is_file())


def listing_of(roots, output):
    return next(json.loads(path.read_text()) for path in (pathlib.Path(root) / "objects" / "outputs" / f"{output}.json"
                                                          for root in roots) if path.is_file())


def linked_output(roots, output, place, work):
    """The output's files linked into work/<place>/ as they are stored (a neighbours output keeps the places it shows
    under places/<other>/, where its own references find them); the names of the places it shows."""
    shown = set()
    for name, sha in listing_of(roots, output).items():
        parts = name.split("/")
        if parts[0] == facts.NEIGHBOURS and len(parts) > 2:
            shown.add(parts[1])
        target = work / place / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(blob_of(roots, sha))
    return sorted(shown)


def linked_stage(roots, store_root, target, output, place, work):
    """The stage of `output` (of the row `target`) linked into `work`, with the accepted neighbours beside an
    assembly as the web copy shows it: (its stage file, the shown places that have a web copy of their own)."""
    shown = linked_output(roots, output, place, work)
    if target != "neighbours":
        shown = convert.linked_neighbours(pathlib.Path(store_root), place, work)
    copied = {other for other in shown if convert.accepted_assembly(pathlib.Path(store_root), other)}
    return work / place / f"{place}.usda", copied


def before_output(store_root, target, place):
    """The output the place stands on now for the row `target`, or None when nothing is accepted."""
    accept = convert.standing_accept(pathlib.Path(store_root), f"{target or 'assembly'}@{place}")
    return accept["output"] if accept else None


def steady(value):
    """A surface input with every file path as the name of the blob it links to, so the two sides compare."""
    if isinstance(value, (list, tuple)):
        return [steady(each) for each in value]
    if isinstance(value, str) and os.path.isfile(value):
        return os.path.basename(os.path.realpath(value))
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)


def surface_of(export, prim, known):
    """What paints a drawn mesh: each material bound to it or its parts, with its inputs, as plain data."""
    from pxr import UsdGeom
    found = []
    for each in [prim, *(subset.GetPrim() for subset in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim)))]:
        material = export.bound_material(each)
        path = str(material.GetPath()) if material else ""
        if path not in known:
            known[path] = steady(sorted((export.surface_inputs(material) if material else {}).items()))
        found.append([each.GetName(), path.rsplit("/", 1)[-1], known[path]])
    return found


def shape_of(prim, time):
    """A drawn mesh's point count (0 for a sphere)."""
    from pxr import UsdGeom
    points = UsdGeom.Mesh(prim).GetPointsAttr().Get(time) if prim.IsA(UsdGeom.Mesh) else None
    return len(points) if points is not None else 0


def object_entries(export, stage, time):
    """{object name as the viewer names it: {layer, low, high, surface, shape}} of every drawn mesh, an object's
    meshes joined."""
    from pxr import Usd, UsdGeom
    boxes = UsdGeom.BBoxCache(time, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found, known = {}, {}
    for prim in Usd.PrimRange(stage.GetDefaultPrim()):
        if not export.drawn(prim, time):
            continue
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        low, high = [list(box.GetMin()), list(box.GetMax())] if not box.IsEmpty() else [[0.0] * 3, [0.0] * 3]
        entry = found.setdefault(export.object_name(prim), {"layer": facts.layer_of(prim), "low": low, "high": high,
                                                            "surface": [], "shape": 0})
        entry["low"] = [round(min(old, new), 4) for old, new in zip(entry["low"], low)]
        entry["high"] = [round(max(old, new), 4) for old, new in zip(entry["high"], high)]
        entry["surface"] += surface_of(export, prim, known)
        entry["shape"] += shape_of(prim, time)
    return found


def sound_entries(stage):
    """{sound's path: {at, file}} of every placed sound (UsdMedia SpatialAudio), its file as its blob's name."""
    from pxr import Usd, UsdGeom
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    found = {}
    for prim in stage.Traverse():
        if prim.GetTypeName() != "SpatialAudio":
            continue
        asset = prim.GetAttribute("filePath").Get() if prim.GetAttribute("filePath") else None
        file = steady(asset.resolvedPath) if asset is not None and asset.resolvedPath else str(asset or "")
        at = list(cache.GetLocalToWorldTransform(prim).ExtractTranslation())
        found[str(prim.GetPath())] = {"at": [round(each, 3) for each in at], "file": file,
                                      "layer": facts.layer_of(prim)}
    return found


def fingerprint(stage_file):
    """{objects, lamps, sounds, cameras} of a linked stage: what the difference compares."""
    from pxr import Usd
    export = convert.exporter()
    stage = Usd.Stage.Open(str(stage_file))
    if stage is None:
        raise RuntimeError(f"OpenUSD could not open {stage_file}")
    time = Usd.TimeCode(stage.GetStartTimeCode())
    lamps = {entry["name"]: entry for entry in facts.lamps(export, stage, time)}
    scene = pathlib.Path(stage_file).parent / "scene.json"
    views = json.loads(scene.read_text()).get("views", []) if scene.is_file() else []
    return {"objects": object_entries(export, stage, time), "lamps": steady_lamps(lamps),
            "sounds": sound_entries(stage),
            "cameras": {view["name"]: {key: view.get(key) for key in ("eye", "aim", "fov")} for view in views}}


def steady_lamps(lamps):
    return {name: {key: steady(value) for key, value in entry.items()} for name, entry in lamps.items()}


def kept_fingerprint(work, output, stage_file):
    """The before's fingerprint, read from the scratch folder when this output's was worked out already."""
    path = pathlib.Path(work) / FINGERPRINTS / f"{output}-{FINGERPRINT_VERSION}.json"
    if path.is_file():
        return json.loads(path.read_text())
    found = fingerprint(stage_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found))
    return found


def moved_box(old, new):
    return any(abs(first - second) > MOVED_METRES for side in ("low", "high")
               for first, second in zip(old[side], new[side]))


def object_kind(old, new):
    """How one object changed between the sides: "moved", "reshaped", "refinished", or None."""
    if moved_box(old, new):
        return "moved"
    if old["shape"] != new["shape"]:
        return "reshaped"
    return "refinished" if old["surface"] != new["surface"] else None


def thing_of(name):
    """The thing an object belongs to, as the owner counts them: a person or a fixture whole (Characters/bram, not
    each of its meshes), a shown place's part (Places/camp/Outside), else the object itself (Objects/crate_1)."""
    parts = name.split("/")
    if parts[0] == "Places" and len(parts) > 3:
        return "/".join(parts[:3])
    return "/".join(parts[:2]) if len(parts) > 2 else name


def entry(name, found):
    return {"name": name, "layer": found.get("layer"), "low": found.get("low"), "high": found.get("high")}


def joined_things(entries):
    """The entries joined by thing (thing_of): one each, its box around all of its objects', `parts` how many."""
    found = {}
    for each in entries:
        key = thing_of(each["name"])
        if key not in found:
            found[key] = {**each, "name": key, "parts": 0}
        thing = found[key]
        thing["parts"] += 1
        if each.get("low") and thing.get("low"):
            thing["low"] = [min(old, new) for old, new in zip(thing["low"], each["low"])]
            thing["high"] = [max(old, new) for old, new in zip(thing["high"], each["high"])]
    return list(found.values())


def object_changes(before, after):
    """{added, removed, moved, reshaped, refinished}: [{name, layer, low, high, parts}] a thing (joined_things; the
    after's box, the before's for a removed one)."""
    found = {kind: [] for kind in ("added", "removed", "moved", "reshaped", "refinished")}
    for name in sorted(set(before) | set(after)):
        if name not in before:
            found["added"].append(entry(name, after[name]))
        elif name not in after:
            found["removed"].append(entry(name, before[name]))
        else:
            kind = object_kind(before[name], after[name])
            if kind:
                found[kind].append(entry(name, after[name]))
    return {kind: joined_things(entries) for kind, entries in found.items()}


def lamp_changed(old, new):
    """True when a lamp moved, or its strength or colour moved by more than LAMP_SHARE."""
    if any(abs(first - second) > MOVED_METRES for first, second in zip(old.get("at") or [], new.get("at") or [])):
        return True
    numbers = [(old.get(key), new.get(key)) for key in ("intensity", "exposure")]
    numbers += list(zip(old.get("colour") or [], new.get("colour") or []))
    return any(isinstance(first, (int, float)) and isinstance(second, (int, float)) and
               abs(first - second) > LAMP_SHARE * max(abs(first), abs(second), 1e-6) for first, second in numbers)


def keyed_changes(before, after, changed):
    """{added, removed, changed}: [names] between two {name: entry}, `changed` judging the ones on both sides."""
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "changed": sorted(name for name in set(before) & set(after) if changed(before[name], after[name]))}


def lamp_box(lamp):
    at = lamp.get("at") or [0.0, 0.0, 0.0]
    return {"name": lamp["name"], "layer": lamp.get("layer"), "low": [value - 0.15 for value in at],
            "high": [value + 0.15 for value in at]}


def counted(found):
    """Each list of changes kept to MOST_LISTED, with its whole count."""
    return {kind: {"count": len(listed), "listed": listed[:MOST_LISTED]} for kind, listed in found.items()}


def difference(before, after):
    """What changes from the before's fingerprint to the after's: {objects, lamps, sounds, cameras}, each kind with
    its count and its entries (lamps with a box around each, for the viewer's marks)."""
    lamps = keyed_changes(before["lamps"], after["lamps"], lamp_changed)
    lamp_entries = {kind: [lamp_box((after if kind != "removed" else before)["lamps"][name]) for name in names]
                    for kind, names in lamps.items()}
    return {"objects": counted(object_changes(before["objects"], after["objects"])),
            "lamps": counted(lamp_entries),
            "sounds": keyed_changes(before["sounds"], after["sounds"], lambda old, new: old != new),
            "cameras": keyed_changes(before["cameras"], after["cameras"], lambda old, new: old != new)}


def after_copy(place, stage_file, copied, store_root, out, origin):
    """The after's 3D web copy into `out` (web3d/), from the cameras the place's own copy offers; its facts, or
    {"error": why} when it cannot be made (a place with its neighbours can pass glTF's 2 GB)."""
    holder = pathlib.Path(tempfile.mkdtemp(prefix=f"basket-copy-{place}-"))
    try:
        sidecar = convert.write_copies(place, pathlib.Path(stage_file).parent, holder, origin,
                                       convert.place_cameras(pathlib.Path(store_root), place), copied)
        shutil.move(str(holder / place), str(out))
    except (RuntimeError, ValueError, OverflowError) as failed:
        return {"error": str(failed)[-1000:]}
    finally:
        shutil.rmtree(holder, ignore_errors=True)
    return {"triangles": sidecar["triangles"], "bytes": sidecar["bytes"], "light_bytes": sidecar["light_bytes"]}


def place_after(place, assembled, roots, store_root, partial, work):
    """The place's free after into `partial` (its web3d/ copy) and what changes against the before:
    {before, after, target, copy, changes}; `changes` None when the after is the before (nothing free changes)."""
    target = assembled.get("target") or "assembly"
    before = before_output(store_root, target, place)
    found = {"before": before, "after": assembled.get("assembly"), "target": target, "copy": None, "changes": None}
    if not found["after"] or found["after"] == before:
        return found
    linked = pathlib.Path(tempfile.mkdtemp(prefix=f"basket-after-{place}-", dir=work))
    try:
        stage_file, copied = linked_stage(roots, store_root, target, found["after"], place, linked / "after")
        found["copy"] = after_copy(place, stage_file, copied, store_root, partial / "web3d",
                                   {"from_output": found["after"], "basket": True})
        after_print = fingerprint(stage_file)
        if before:
            before_file, _ = linked_stage([store_root], store_root, target, before, place, linked / "before")
            found["changes"] = difference(kept_fingerprint(work, before, before_file), after_print)
        else:
            found["changes"] = difference({"objects": {}, "lamps": {}, "sounds": {}, "cameras": {}}, after_print)
    finally:
        shutil.rmtree(linked, ignore_errors=True)
    return found
