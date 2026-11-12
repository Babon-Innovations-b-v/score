"""A thing laid on its holder's curved top laid there again once the models' feet are levelled (even_feet, in the
assembly's take of the bakes) and the place stood on its made ground (on_ground.stood): crest_tops.laid_on runs in
the fitting, on the models as baked, and a thing it found no spot for then is left at its holder's box top.

assembly@wreck, 2026-11-12: its open hatch, on the top of the crashed rocket's front half (a hull lying on its side,
its crest 4.4 m up), was left at the hull's box top, 5.16 m, and floated 1.74 m over the hull under it. In the
fitting the hatch's own model had a foot 5 cm off (no spot on the crest passed the triage's measure); even_feet then
brought that foot down, and on the levelled model the crest holds it.

    laid(folder, place)   each thing of the place at `folder` on its holders' top or within them (built_tops.held_on)
                          that does not rest where it is laid on the nearest spot of their top where it rests
                          (crest_tops.laid_on); the fits, the base layer saved and laid.json written again, [] and
                          nothing written when none moves
"""
import json
import pathlib

from score.stages.assembly import BASE_LAYER, RECORD, built_tops, crest_tops, fitting, flush_tops, made_waiting


def laid(folder, place):
    """Each thing of the place at `folder` on its holders' top laid again where it rests (module docstring)."""
    from pxr import Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    record = json.loads(record_path.read_text())
    entries = [entry for entry in record.get("objects") or [] if built_tops.held_on(entry)]
    if not entries:
        return []
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    entries = [entry for entry in entries if stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}")]
    fits = crest_tops.laid_on(stage, place, entries)
    fits += flush_tops.laid(stage, place, entries)  # one over a sloping plane no spot of which holds it, flush on it
    if not fits:
        return []
    layer.Save()
    laid_record = json.loads(laid_path.read_text())
    names = {fit["name"] for fit in fits}
    holding = fitting.holders_of(record)  # what a moved thing carries on its top moved with it (fitting.carry)
    moved = {name for name in holding if name in names or holding[name] & names}
    laid_record["objects"] = [{**entry, **boxed(stage, place, entry["name"])} if entry["name"] in moved else entry
                              for entry in laid_record.get("objects", [])]
    laid_record["fitted"] = [*laid_record.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid_record, indent=1))
    return fits


def boxed(stage, place, name):
    """{low, high} of a thing's world box as laid, rounded as laid.json keeps them."""
    low, high = fitting.world_box(stage, f"/{place}/Objects/{name}")
    return {"low": [round(float(value), 4) for value in low], "high": [round(float(value), 4) for value in high]}
