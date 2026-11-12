"""Complete's accepted gaps without the batch gaps of a designed place's own takes of its people rows.

A row the place's hand-in routes `people` (score/stages/complete/prepare/groups.py: its noun a person's) is the people
line's: people_rows.py maps it to a look of that line, the characters layer lays that look on the plan's person spot,
and complete's people check judges it by name (tools/usd/complete.py PEOPLE_ROUTE). The place's plan lays no item of
it, yet the place's own line still makes and finishes a take of the row (its `layer` people), finished from the
place's scene library, which holds no skin. Cockpit, 2026-11-12: its pilot and officer takes, nowhere in the place,
failed the recheck and the colour gate on "human skin" (dE 34.3 and 27.4 from seat leather) and counted as two of its
eleven gap objects, while their looks pilot-made and officer-made passed on the people line's skin_light (dE 11.3 and
9.4). A batch gap every object of which is such a take, its row or a model of its row (`<row>_<n>`: the bake's
pilot_1) is left out of the count, named in the verdict's reason; every other gap fails complete as gaps.py fails it.

Its own module, set on complete's gate in the table (`accepted_gaps`), so only complete's code version moves.
"""
import json
import pathlib

from score import checks
import score.stages.batch_gaps as batch_gaps
import score.stages.gaps as gaps

GATE = "accepted gaps"  # complete's gate (graph.GAPPED), as gaps.judge_accepted names it
PEOPLE_ROUTE = "people"  # a hand-in row's and take's route when the people line makes it (groups.route_of)


def people_items(handin):
    """(the place's rows its hand-in routes to the people line, the takes it makes of them) of a hand-in record."""
    rows = {row["id"] for row in handin.get("rows", []) if row.get("route") == PEOPLE_ROUTE}
    takes = {take for take, entry in handin.get("takes", {}).items() if entry.get("route") == PEOPLE_ROUTE}
    takes |= {entry["take"] for entry in handin.get("objects", {}).values()
              if entry.get("take") and entry.get("rows") and set(entry["rows"]) <= rows}
    return rows, takes


def of_people(item, rows, takes):
    """Whether a gap's object (a take, a row, a model `<row>_<n>`, or a prim path ending in one) is a people row's."""
    name = str(item).rstrip("/").rsplit("/", 1)[-1]
    row, _, number = name.rpartition("_")
    return name in takes or name in rows or (row in rows and number.isdigit())


def judge_accepted(output, inputs, evidence):
    """gaps.judge_accepted with the batch gaps of the place's people rows' own takes left out (of_people: every object
    one of them), each named in the reason."""
    handin = inputs.get("hand-in")
    rows, takes = people_items(json.loads(pathlib.Path(handin).read_text()) if handin else {})
    batch, people = [], []
    for entry in batch_gaps.of(inputs):
        whose = entry["objects"] and all(of_people(item, rows, takes) for item in entry["objects"])
        (people if whose else batch).append(entry)
    left = (f"; left out, the people line's (the characters layer lays their looks): "
            f"{', '.join(entry['name'] for entry in people)}") if people else ""
    found = gaps.entries(inputs) + gaps.written(inputs) + batch
    if not found:
        return checks.Verdict(GATE, checks.PASS, f"no accepted gap{left}",
                              {"gaps": 0, "people takes' gaps": len(people)}, {"gaps": "lower"})
    findings = tuple(f"{entry['name']}: {fault}" for entry in found for fault in entry["faults"])
    return checks.Verdict(GATE, checks.FAIL, "; ".join(f"{entry['name']} ({entry['reason']}; {entry['decided']})"
                                                            for entry in found) + left,
                          {"gaps": len(found), "batch gaps": len(batch), "people takes' gaps": len(people)},
                          {"gaps": "lower"}, findings)
