"""The materials checks' findings of one place's evidence (measure.py), with no store: texture detail near cameras
(texel.py), finish-border raggedness (borders.py) and kit bakes older than their bake code (kit_age.py)."""
import json
import pathlib

from score.stages.complete.materials import borders, kit_age, measure, texel


def read(folder):
    """A place's evidence as measured."""
    return json.loads((pathlib.Path(folder) / measure.EVIDENCE).read_text())


def findings(evidence, world=None):
    """Every finding of the three checks, each check's in its own order."""
    return texel.findings(evidence, world) + borders.findings(evidence) + kit_age.findings(evidence)


def verdict(found):
    """fail on any finding, else pass."""
    return "fail" if found else "pass"


def reason(evidence, found):
    """The place's answer in words, with the kit pieces whose bake time is not known."""
    counts = {}
    for item in found:
        counts[item["rule"]] = counts.get(item["rule"], 0) + 1
    words = "; ".join(f"{rule}: {count}" for rule, count in counts.items()) or "no finding"
    unknown = [model["model"] for model in evidence["kit"] if not model["baked_by"]]
    if unknown:
        words += (f" ({len(unknown)} kit piece{'s' if len(unknown) > 1 else ''} not from the seed, with no bake time "
                  f"to compare: {', '.join(unknown[:4])}{' ...' if len(unknown) > 4 else ''})")
    return words
