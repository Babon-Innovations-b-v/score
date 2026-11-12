"""A wall or ceiling thing on a structure row built into a wall mounted there too (mounted.mounted calls on_built_in).

    on_built_in(rows, holders, found, built_in)   {row id: kind} of the wall and ceiling things on such a row

Tube's wall lamps are anchored on its structural ribs, a structure row anchored on its curved wall panels: mounted
read the ribs as built into the wall, but the lamps, an object row, as standing on them, so the resting gate judged
them held up from under, leaning 66 degrees on the ribs' curve or floating 1.3 to 2 m over the floor (settle@tube,
2026-11-12). A thing whose own words make it a wall or ceiling thing (holders.holder_kind) is mounted on the piece it
is fixed to; a thing on a wall shelf (no such words: a cup) still stands on it.
"""


def on_built_in(rows, holders, found, built_in):
    """{row id: its holder's mounted kind} of the `rows` ({id: row}) not yet in `found` ({row id: "wall" or "ceiling"},
    mounted's) anchored on a structure row (`built_in`) that is (`holders`: {row id: its anchor's row id}) whose own
    kind is wall or ceiling."""
    from score.review.holders import holder_kind  # here: holders imports the stage table, which imports this module
    return {row_id: found[holder] for row_id, holder in holders.items()
            if row_id not in found and holder in built_in and holder in found
            and holder_kind(rows[row_id]) in ("wall", "ceiling")}
