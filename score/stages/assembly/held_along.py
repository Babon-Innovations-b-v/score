"""A thing laid on or within a holder nothing holds moved with that holder when the fitting moves the holder (parted,
moved out of a deck or wall, off a rug's edge, apart; fitting.fitted, before the held things are fitted): on_holder
keeps a top or within thing at its plan spot within its holder's box, so one whose holder was moved stood where the
holder's edge now is. Greenhouse's desk_6 was parted 1.07 m, and computer_4 laid on it was left at its edge
(settle@greenhouse, 2026-11-11).

    boxes(stage, place, loose)          {name: its world box (low, high)} of the things nothing holds, as laid
    carried(stage, place, entries, before)   the fits [{name, how "carried", ...}] of the held things moved with theirs
"""
import numpy as np

from score.stages.assembly import fitting


def boxes(stage, place, loose):
    """{name: world box (low, high)} of each thing nothing holds (`loose`, record entries) on the stage, as laid."""
    return {entry["name"]: fitting.world_box(stage, f"/{place}/Objects/{entry['name']}") for entry in loose
            if stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}")}


def holder_of(entry, before, stage, place):
    """The one holder an entry laid on or within a holder rides with: of its holders that are objects, the nearest to
    it on the floor plan by the boxes `before` (its holders that were loose then) or as laid; None with none."""
    on = entry.get("on") or {}
    if on.get("how") not in ("top", "within") or on.get("holder scope", "Objects") != "Objects":
        return None
    found = {holder: before.get(holder) or fitting.world_box(stage, f"/{place}/Objects/{holder}")
             for holder in on.get("holder") or [] if stage.GetPrimAtPath(f"/{place}/Objects/{holder}")}
    if not found:
        return None
    box = fitting.nearest(list(found.values()), *fitting.world_box(stage, f"/{place}/Objects/{entry['name']}"))
    return next(holder for holder, held in found.items() if held is box)


def carried(stage, place, entries, before):
    """Each thing laid on or within a holder (`entries`, record entries) whose holder nothing holds was moved since
    `before` (boxes) by more than fitting.MOVE_LEAST moved by the same shift, and what is laid on or within it with it
    (fitting.carry); the fits [{name, how "carried", holder, moved, ...}] of those moved, the stage left unsaved."""
    by_name = {entry["name"]: entry for entry in entries if stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}")}
    riding = {}  # {holder: [what rides on it]}
    for name, entry in by_name.items():
        if (holder := holder_of(entry, before, stage, place)) is not None:
            riding.setdefault(holder, []).append(name)
    fits = []
    for holder, (low, high) in before.items():
        if holder not in riding or not stage.GetPrimAtPath(f"/{place}/Objects/{holder}").IsActive():
            continue
        shift = fitting.foot_middle(*fitting.world_box(stage, f"/{place}/Objects/{holder}")) - fitting.foot_middle(
            low, high)
        if float(np.linalg.norm(shift)) <= fitting.MOVE_LEAST:
            continue
        starts = {name: fitting.world_box(stage, f"/{place}/Objects/{name}") for name in by_name}
        fitting.carry(stage, place, riding, holder, shift)
        for name in by_name:
            now = fitting.world_box(stage, f"/{place}/Objects/{name}")
            if not np.allclose(now[0], starts[name][0]):
                fits.append(fitting.laid_fit(stage, f"/{place}/Objects/{name}", by_name[name], "carried", [holder],
                                             np.linalg.norm(shift), 1.0,
                                             f"carried {np.linalg.norm(shift):.2f} m with {holder}, moved by the fitting"))
    return fits
