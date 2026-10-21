"""The materials checks' findings of one place's evidence (measure.py), with no store: texture detail near cameras
(texel.py) and finish-border raggedness (borders.py)."""
import json
import pathlib

from score.stages.complete.materials import borders, measure, texel


def read(folder):
    """A place's evidence as measured."""
    return json.loads((pathlib.Path(folder) / measure.EVIDENCE).read_text())


def findings(evidence, world=None):
    """Every finding of the two checks, each check's in its own order."""
    return texel.findings(evidence, world) + borders.findings(evidence)


def verdict(found):
    """fail on any finding, else pass."""
    return "fail" if found else "pass"


def reason(found):
    """The place's answer in words: each rule's count of findings."""
    counts = {}
    for item in found:
        counts[item["rule"]] = counts.get(item["rule"], 0) + 1
    return "; ".join(f"{rule}: {count}" for rule, count in counts.items()) or "no finding"
