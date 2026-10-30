"""Which rows rest mounted on a wall or ceiling row, read by the assembly's resting check and the settle's snap."""


def mounted(rows):
    """{row id: "wall" or "ceiling"} of the `rows` ({id: row}) anchored on a wall or ceiling row (`on:<row>`,
    holders.holder_kind): mounted there, not held up from under (the docking airlock's wall pipes and ceiling rails,
    judged as standing on their wall, leaned and tipped, round 32, 2026-10-30). Here, not in holders: holders is in
    the code of the scene record and every row after it; nor in settling/held.py, whose snap.py import would put a
    snap edit into the assembly's and every later row's code. A structure row (a door, a window: reading.PARTS) on a
    mounted row is built into it and mounted with it, its holder's kind (the docking airlock's door window in its
    door on the back wall, judged as standing on the door's frame, leaned 38 degrees, round 32); a thing on a mounted
    row (a cup on a wall shelf) still stands on it."""
    from score.review.holders import holder_kind  # here: holders imports the stage table, which imports this module
    holders = {row_id: str(row.get("anchor") or "").removeprefix("on:") for row_id, row in rows.items()
               if str(row.get("anchor") or "").startswith("on:")}
    found = {row_id: kind for row_id, kind in ((row_id, holder_kind(rows.get(holder, {"id": ""})))
                                               for row_id, holder in holders.items()) if kind in ("wall", "ceiling")}
    built_in = {row_id for row_id, row in rows.items() if row.get("part") == "structure"}
    # never through a shell row: the engine room's railing stands on its floor grating, laid on its hull
    pieces = {row_id: kind for row_id, kind in found.items() if holder_kind(rows[row_id]) is None}
    while more := {row_id: pieces[holders[row_id]] for row_id in built_in - pieces.keys()
                   if holders.get(row_id) in pieces}:
        pieces.update(more)
        found.update(more)
    return found
