"""The pick lock's rule, on rows and what they show (picks.py has the stage check, the recording and the command line).
Kept apart so the exporter, which refuses a broken pick, hashes this rule alone: an edit to how a stage is read for
the check moves no export's (nor effects', nor terrain's) code version.
"""


class PickBroken(ValueError):
    """An export that would replace a picked model without a written owner decision."""


def picked(row):
    """A row's pick, or None: only a row whose pick has a hash and no written replacement is locked."""
    pick = row.get("pick")
    if not pick or not pick_hashes(pick) or str(row.get("pick_replaced", "")).strip():
        return None
    return pick


def pick_hashes(pick):
    """The model hashes a pick allows: its one model's, or each of its several models'."""
    return set((pick.get("models") or {}).values()) or ({pick["sha256"]} if pick.get("sha256") else set())


def pick_sha256(pick, model):
    """The hash the pick holds for one model of its row: its several models' entry for it, else its one model's."""
    return (pick.get("models") or {}).get(model) if pick.get("models") else pick.get("sha256")


def pick_name(pick):
    """The picked model or models, named for a fault."""
    models = pick.get("models")
    return ", ".join(f"{name} ({sha256[:12]})" for name, sha256 in sorted(models.items())) if models else \
        f"{pick['model']} ({pick['sha256'][:12]})"


def faults(rows, shown):
    """Every way the shown objects break the picks: rows is the inventory's rows, shown {row: [(object, model,
    model sha256)]}. A fault is {row, object, why}."""
    found = []
    for row in rows:
        pick = picked(row)
        if pick is None:
            continue
        objects = shown.get(row["id"], [])
        if not objects:
            found.append({"row": row["id"], "object": None,
                          "why": f"the owner picked {pick_name(pick)}, and no object of this row "
                                 "is on the stage (something else stands in its place, or it was dropped)"})
        allowed = pick_hashes(pick)
        for name, model, sha256 in objects:
            if sha256 not in allowed:
                found.append({"row": row["id"], "object": name,
                              "why": f"shows {model} ({(sha256 or 'no hash')[:12]}), not the owner's pick "
                                     f"{pick_name(pick)}"})
    return found


def locked_count(rows):
    """How many rows are locked to an owner's pick."""
    return sum(1 for row in rows if picked(row) is not None)
