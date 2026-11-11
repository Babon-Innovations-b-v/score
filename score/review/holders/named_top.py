"""A thing anchored on a floor row whose `where` names the thing it stands on: on that thing's top.

The reading anchors a row on one holder and says where it is in words; the two can disagree. Airlock's open tool case
is anchored `on:floor_plates` (the floor) but its `where` says "on bench", and its plan stands it 0.49 m up, at its
bench's top: read as on the floor, it had no holder, the scene record laid it at its plan spot over the edge of the
bench's built top and it floated 0.42 m (settle@airlock, 2026-11-11). A row anchored on the floor itself is read so by
stood_on already; this reads a row anchored on a floor row (holder_kind "floor") the same way, only where its words
say it stands on a holder laid on the plan (ON_WORDS) and its plan stands it up off the floor.
"""
import numpy

# Where words that say a thing stands on what they name ("on bench"), not round it or by it (railings "around engines").
ON_WORDS = {"on", "atop", "onto", "upon"}


def named_top(found, item, row, rows, plan, items, laid, tied):
    """The relation `found` of a row anchored on a floor row (`on:<row>`, its holder a floor) and laid on the floor,
    as `top` of the nearest item of a row its where words say it is on (ON_WORDS, named_holders: "on bench") where
    its plan stands it more than half its height (and STAND_REACH) up; else `found` as it is."""
    from score.review import holders
    anchor = str(row.get("anchor") or "")
    floor_row = rows.get(anchor[3:]) if anchor.startswith("on:") else None
    if found.get("how") != "floor" or floor_row is None or holders.holder_kind(floor_row) != "floor" \
            or item[0] not in items or "spot" in found or "pieces" in found:
        return found
    base, tall = float(holders.shape_of(item[0], plan).get("base") or 0.0), holders.tall_of(item[0], row, plan)
    if base <= max(holders.STAND_REACH, tall / 2) or not holders.where_words(row) & ON_WORDS:
        return found
    named = [(float(numpy.linalg.norm(holders.middle(items[name]) - holders.middle(item))), name, other["id"])
             for other in holders.named_holders(row, rows, tied) for name in laid.get(other["id"], ()) if name in items]
    if not named:
        return found
    _, name, row_id = min(named)
    return {"how": "top", "holder": name, "holder row": row_id,
            "why": f"on {row_id}'s top: its words say {row.get('where')!r} (its anchor {anchor} the floor), its plan "
                   f"stands it {base:g} m up"}
