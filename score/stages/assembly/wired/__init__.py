"""The assembly's make as the stage table runs it (score/stages/__init__.py's ASSEMBLY), kept out of the assembly
package's own import: the light, settle, screens, cast, motion and characters rows hash that package (__init__.py,
fitting.py, sounds.py and what they import), so a fix there makes their accepted outputs again; only the table reads
this one, so it moves the assembly's key alone (as held_apart.py does for the held gate).

    make     assembly.make_from_seed, then
             parted         each floor thing a wall's or face's thing was laid into moved to its nearest free spot
                            (assembly/parting.py, which the settle's grounded seed parts too: airlock's
                            control_pedestals_2 under its wall_pipes_1, 2026-11-10)
             stood          each floor thing at an open place's floor slid to a level spot beside it where its made
                            ground slopes (level_spot.py: wreck's tank in its dent) and stood on that ground
                            (on_ground.py), each thing on its holder's curved top laid again on its levelled model
                            (tops_levelled.py: wreck's open hatch), each roof piece on its holder's top let down onto
                            the holder it roofs (roof_tops.py: base's glass pyramid roof), then each face thing of a row the resting gate
                            judges standing by the seed's inventory let down onto what is under it (face_down.py:
                            wreck's solar_panels_5, 2026-11-12; tube's wall lamps on its ribs are mounted, so left)
             released       every stage the make left in a reference cycle collected (release): fitting.fitted's
                            recursive closure `one` holds the stage the design objects were laid on, so until a
                            collection ran its asset layers stayed loaded and screens.take's Sdf.Layer.CreateNew of
                            assets/<model>.usdc was refused, "A layer already exists" (assembly@lab, 2026-11-10,
                            whenever no automatic collection came first)
             silent voices  each voice of the sound layer (a use with `voice`) on a person the characters layer did
                            not lay (its characters.json names the person `missing`, or has no person of that name)
                            taken out of the unplaced sounds into origin.json's `silent voices`, and written as a gap
                            (score/stages/gaps.py's entry form, gaps.WRITTEN) that complete's accepted gaps gate fails
                            by name: a place goes into the film with what it has (owner, 2026-11-10), so a person not
                            laid is the people check's fault and the voice a named gap, never the whole assembly's
                            (lab's crew_talk on its person_1, base's helmet_radio_talk on its astronaut_left). A voice
                            on a person who was laid and still plays at nothing stays unplaced:
                            the layers gate fails it.
"""
import gc
import json
import pathlib

from score.stages import assembly
from score.stages.assembly import face_down, level_spot, on_ground, parting, roof_tops, tops_levelled

# gaps.WRITTEN, the file complete's accepted gaps gate reads; named here, not imported, so score/stages/gaps.py stays
# out of the assembly's code version (a gap's verdict moves complete alone; the test reads it back through gaps.py)
WRITTEN = "gaps.json"

ORIGIN = "origin.json"
SILENT = "silent voices"


def make(inputs, out, seed, params):
    """The assembly's make, its floor things parted from the wall things laid into them, its cycles released and its
    silent voices made gaps (module docstring)."""
    assembly.make_from_seed(inputs, out, seed, params)
    parting.parted(out, assembly.stage_file(out).stem)
    level_spot.slid(out, assembly.stage_file(out).stem)
    on_ground.stood(out, assembly.stage_file(out).stem)
    tops_levelled.laid(out, assembly.stage_file(out).stem)
    roof_tops.let_down(out, assembly.stage_file(out).stem, inventory_rows(inputs, out))
    face_down.let_down(out, assembly.stage_file(out).stem, inventory_rows(inputs, out))
    release()
    silence(inputs, out)


def inventory_rows(inputs, out):
    """The rows of the inventory the seed at `out` was laid from (assembly.declared_inventory, in the declared
    inventory folder), as the resting gate reads them; None where it names none there."""
    inventory = assembly.declared_inventory(out, inputs["inventories"]) if "inventories" in inputs else None
    return json.loads(inventory.read_text())["rows"] if inventory is not None and inventory.is_file() else None


def release():
    """Collect every object left only in a reference cycle, the stages among them, so their layers are let go."""
    gc.collect()


def looks_of(inputs):
    """The characters layer's people ({name: look}, its characters.json `looks`); None without a characters layer."""
    path = pathlib.Path(inputs["characters-layer"]) / "characters.json" if "characters-layer" in inputs else None
    return json.loads(path.read_text())["looks"] if path is not None and path.is_file() else None


def laid_people(looks):
    """The names of the people the characters layer laid: its `looks` without `missing`."""
    return {name for name, look in (looks or {}).items() if "missing" not in look}


def unplaced_words(use):
    """The words sounds.object_sounds gives an object use with no prim of its row or name on the stage."""
    return f"{use['sound']} (object): no prim of the row or name {use['on']} on the stage"


def why_unlaid(looks, person):
    """Why the characters layer did not lay `person`: its `missing`, else that its cast lays no one of that name."""
    if looks is None:
        return "the place has no characters layer"
    return looks[person]["missing"] if person in looks else "its cast lays no one of that name"


def voice_gap(use, words, why):
    """A silent voice as gaps.py's entry, for complete's accepted gaps gate to fail by name."""
    return {"name": f"{use['sound']}: {use['on']}'s voice, {use['on']} not laid", "row": "assembly", "check": "layers",
            "objects": [f"{use['sound']} (object)"], "contains": use["on"],
            "reason": f"{use['on']} is not laid ({why}), so its voice plays at nothing",
            "decided": "a place goes into the film with what it has (owner, 2026-11-10)", "faults": [words]}


def silence(inputs, out):
    """origin.json's unplaced voices on a person not laid moved into its `silent voices`, each a gap in gaps.json."""
    origin_path = pathlib.Path(out) / ORIGIN
    origin = json.loads(origin_path.read_text())
    if "sound" not in inputs or not origin["unplaced sounds"]:
        return
    record = json.loads((pathlib.Path(inputs["sound"]) / "sound.json").read_text())
    looks = looks_of(inputs)
    laid = laid_people(looks)
    found = {}
    for use in record["uses"]:
        words = unplaced_words(use) if use["role"] == "object" else None
        if use.get("voice") and use["on"] not in laid and words in origin["unplaced sounds"]:
            found[words] = voice_gap(use, words, why_unlaid(looks, use["on"]))
    if not found:
        return
    origin["unplaced sounds"] = [words for words in origin["unplaced sounds"] if words not in found]
    origin[SILENT] = sorted(found)
    origin_path.write_text(json.dumps(origin, indent=1))
    path = pathlib.Path(out) / WRITTEN
    kept = json.loads(path.read_text())["gaps"] if path.is_file() else []
    path.write_text(json.dumps({"gaps": kept + list(found.values())}, indent=1))
