"""A place's rows counted and grouped as the cockpit lists them: one finding a kind of piece and aspect that does not
trace (103 lower walls with one baked look are one problem, not 103).

    findings.counts(rows)     # {"library", "exception", "neither", "source": {...}, "finish": {...}}
    findings.grouped(rows)    # [{"rule", "aspect", "kind", "group", "count", "prims", "instead", "sentence"}]
"""
import collections

from score.stages.complete.library.trace import EXCEPTION, LIBRARY, NEITHER

RULES = {"source": "not from the library", "finish": "finish not from the library"}
ANSWERS = (LIBRARY, EXCEPTION, NEITHER)
SAMPLES = 24  # the prims a finding keeps to find its picture by


def tally(rows):
    found = collections.Counter(row["answer"] for row in rows)
    return {answer: found.get(answer, 0) for answer in ANSWERS}


def counts(rows):
    """The place's rows by answer, in all and by aspect."""
    return {**tally(rows), **{aspect: tally([row for row in rows if row["aspect"] == aspect]) for aspect in RULES}}


def sentence(group):
    """A finding in words: how many, what, and what it is instead."""
    many = group["count"]
    things = f"{many} {group['kind']}{'s' if many > 1 else ''}"
    said = f"{things} ({group['group']}) {RULES[group['aspect']]}: {group['instead']}"
    return said + (f" (and {group['others']} other ways)" if group["others"] else "")


def spread(prims):
    """At most SAMPLES of the prims, taken evenly through them (a group's first ones often stand together)."""
    return prims[::max(1, len(prims) // SAMPLES)][:SAMPLES]


def grouped(rows):
    """The rows that trace neither to the library nor to an exception, one finding a group and aspect, the largest
    first."""
    groups = {}
    for row in rows:
        if row["answer"] == NEITHER:
            groups.setdefault((row["aspect"], row["group"]), []).append(row)
    found = []
    for (aspect, group), members in groups.items():
        ways = collections.Counter(member["instead"] for member in members)
        found.append({"rule": RULES[aspect], "aspect": aspect, "kind": members[0]["kind"], "group": group,
                      "count": len(members), "prims": spread([member["prim"] for member in members]),
                      "instead": ways.most_common(1)[0][0], "others": len(ways) - 1})
    found.sort(key=lambda item: (-item["count"], item["aspect"], item["group"]))
    return [dict(item, sentence=sentence(item)) for item in found]


def answer(tallied):
    return "fail" if tallied[NEITHER] else "pass"


def reason(tallied, found):
    """The place's answer in words."""
    if not found:
        return f"all {tallied[LIBRARY] + tallied[EXCEPTION]} traced ({tallied[EXCEPTION]} under an exception)"
    return (f"{tallied[NEITHER]} of {sum(tallied[name] for name in ANSWERS)} not from the library; most: "
            + "; ".join(item["sentence"] for item in found[:2]))
