"""Level 1's step report on a FIXED case set (#70, owner 2026-10-30: "this whipping between improve and regress is
happening a lot"). `changes` pairs two scorings case by case over every case named, tuning and check bodies apart; a
case either scoring could not fit is a failure of that scoring, counted, never dropped from the set. `floor` is the
noise floor: the same parameter point scored twice in fresh processes, each measure's spread of paired differences
(the 95th percentile of their absolute values). `verdict` counts a measure better or worse only when its median paired
change is past its floor; inside it, unchanged. `scales` turns the floor into level 1's residual units, so each kind's
weight is set once from its measured noise."""
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
