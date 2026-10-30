"""Level 1's step report on a FIXED case set (#70, owner 2026-10-30: "this whipping between improve and regress is
happening a lot"). `changes` pairs two scorings case by case over every case named, tuning and check bodies apart; a
case either scoring could not fit is a failure of that scoring, counted, never dropped from the set. `floor` is the
noise floor: the same parameter point scored twice in fresh processes, each measure's spread of paired differences
(the 95th percentile of their absolute values). `verdict` counts a measure better or worse only when its median paired
change is past its floor; inside it, unchanged. `scales` turns the floor into level 1's residual units, so each kind's
weight is set once from its measured noise. `flattened` names a case's honest measures (the frozen harness's m.json,
first column: the median over frames), `scored` reads a scoring's folder, `stepped` is one step's report, JSON-ready."""
import json

import numpy as np

SPREAD = 95  # percentile of absolute paired differences that is a measure's noise floor


def changes(before, after, sides):
    """Per side ('tuning', 'check'): each measure's paired changes (after minus before) over the cases both fitted,
    and the cases each could not fit. `before`/`after`: case -> {measure: value} or None (could not fit); `sides`:
    case -> side, the fixed set (a case missing from a scoring is a failure of it)."""
    report = {}
    for side in sorted(set(sides.values())):
        cases = sorted(case for case, named in sides.items() if named == side)
        failed = {"before": [case for case in cases if before.get(case) is None],
                  "after": [case for case in cases if after.get(case) is None]}
        both = [case for case in cases if before.get(case) is not None and after.get(case) is not None]
        measures = sorted(set.intersection(*(set(before[case]) & set(after[case]) for case in both))) if both else []
        paired = {measure: np.array([after[case][measure] - before[case][measure] for case in both])
                  for measure in measures}
        report[side] = {"cases": len(cases), "both": both, "failed": failed, "paired": paired}
    return report


def floor(first, second, sides):
    """Each measure's noise floor: the SPREAD percentile of |second - first| over all cases both scorings fitted,
    the same point scored twice in fresh processes."""
    pooled = {}
    for side in changes(first, second, sides).values():
        for measure, values in side["paired"].items():
            pooled.setdefault(measure, []).extend(np.abs(values))
    return {measure: float(np.percentile(values, SPREAD)) for measure, values in pooled.items()}


def verdict(paired, noise, lower_is_better=True):
    """Each measure: 'better', 'worse' or 'unchanged', by its median paired change against its noise floor."""
    found = {}
    for measure, values in paired.items():
        middle = float(np.median(values)) if len(values) else 0.0
        gain = -middle if lower_is_better else middle
        found[measure] = "better" if gain > noise[measure] else ("worse" if -gain > noise[measure] else "unchanged")
    return found


def scales(noise, kinds):
    """Level 1's residual unit per kind ('skin', 'turn', 'joint'): the median noise floor of that kind's measures,
    so one unit of each is one floor of noise. `kinds`: kind -> its measures."""
    return {kind: float(np.median([noise[measure] for measure in measures])) for kind, measures in kinds.items()}


def flattened(found):
    """One case's honest measures, flat: each joint's median error (mm), each group's median turn error (deg), each
    region's share of bones outside the skin (%), the share over all and the means of those over joints and groups."""
    flat = {f"joint {key} mm": value[0] for key, value in found["per joint mm"].items()}
    flat.update({f"turn {key} deg": value[0] for key, value in found["per group deg"].items()})
    flat.update({f"outside {key} %": value for key, value in found["bones outside skin %"].items()})
    flat["outside all %"] = found["bones outside all %"]
    flat["joints mean mm"] = float(np.mean([value[0] for value in found["per joint mm"].values()]))
    flat["turns mean deg"] = float(np.mean([value[0] for value in found["per group deg"].values()]))
    return flat


def scored(folder, cases):
    """{case: flattened measures, or None when folder/<case>/m.json is missing (that scoring could not fit it)}."""
    paths = {case: folder / case / "m.json" for case in cases}
    return {case: flattened(json.loads(path.read_text())) if path.exists() else None for case, path in paths.items()}


def stepped(before, after, sides, noise=None):
    """One step's report per side: cases, failures, and per measure the median paired change with its 5th and 95th
    percentiles and, given the noise floor, its verdict."""
    report = {}
    for side, found in changes(before, after, sides).items():
        rows = {measure: {"median": float(np.median(values)), "p5": float(np.percentile(values, 5)),
                          "p95": float(np.percentile(values, 95))} for measure, values in found["paired"].items()}
        if noise is not None:
            for measure, called in verdict(found["paired"], noise).items():
                rows[measure]["verdict"] = called
        report[side] = {"cases": found["cases"], "paired": len(found["both"]), "failed": found["failed"],
                        "measures": rows}
    return report
