"""A row laid standing on its holder's top is held up from under, never mounted from it: holders.holder_kind reads a
holder by the words of its id and noun, so a dome module standing on the ground is a ceiling ("dome") and what is on
it was given the ceiling support (mounted.mounted) and judged by touching, as a lamp hung from a ceiling is.
assembly@base, 2026-11-12: its communications antenna, on top of its dome module, was judged a ceiling piece
touching nothing; laid on its holder's top (built_tops, crest_tops), it stands on it and is judged so.

    laid_on_tops(record)          {row ids} of the scene record's rows whose every object it lays on its holder's top
    standing(mounted, record)     the mounted rows ({row id: "wall" or "ceiling"}) less the ceiling ones laid on top
"""


def laid_on_tops(record):
    """The row ids of the scene `record` whose every object is laid on its holder's top (its relation `top`)."""
    rows = {}
    for entry in record.get("objects") or []:
        rows.setdefault(entry["row"], []).append((entry.get("on") or {}).get("how") == "top")
    return {row_id for row_id, topped in rows.items() if all(topped)}


def standing(mounted, record):
    """The `mounted` rows ({row id: kind}, mounted.mounted) less each ceiling one the scene `record` lays on its
    holder's top: it stands on that holder, never hangs from it."""
    topped = laid_on_tops(record or {})
    return {row_id: kind for row_id, kind in mounted.items() if kind != "ceiling" or row_id not in topped}
