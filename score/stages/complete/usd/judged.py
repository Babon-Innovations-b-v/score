"""One composed stage judged by SCORE's rule set (rules.py), its issues grouped as the cockpit lists them: one finding
a rule and message (107 dangling overs are one problem, not 107).

    stage = judged.opened(path)          # the stage opened in SCORE's resolver context (anchored at its root file)
    found = judged.issues(stage)         # [{"rule", "severity", "message", "prim"}], successes and notes left out
    groups = judged.grouped(found)       # [{"rule", "severity", "prim", "prims", "count", "sentence", "kind"}]
"""
import collections

import usd_validation_nvidia as validation
from pxr import Ar, Usd

from score.stages.complete.usd import rules

SAMPLES = 24  # the prims a finding keeps
TOLD = (validation.IssueSeverity.FAILURE, validation.IssueSeverity.ERROR, validation.IssueSeverity.WARNING)


def opened(path):
    """The stage at `path` opened in the resolver context the runner's stages resolve in: the default resolver
    anchored at the root file, so every relative asset path resolves against its own layer."""
    context = Ar.GetResolver().CreateDefaultContextForAsset(str(path))
    return Usd.Stage.Open(str(path), context)


def where(at):
    """The prim path an issue is at ('' for the stage or a layer as a whole)."""
    if isinstance(at, (list, tuple)):
        at = at[0] if at else None
    path = getattr(at, "path", None)
    return str(path.GetPrimPath()) if path is not None else ""


def issues(stage):
    """Every failure, error and warning SCORE's rules find on the stage, each said by rule, severity and prim."""
    results = rules.engine().validate(stage)
    return [{"rule": issue.rule.__name__ if issue.rule else "usd", "severity": rules.severity(issue),
             "message": (issue.message or "").strip(), "prim": where(issue.at)}
            for issue in results.issues() if issue.severity in TOLD]


def grouped(found):
    """The issues grouped by rule and message, errors first, the largest group first."""
    groups = collections.defaultdict(list)
    for issue in found:
        groups[(issue["severity"], issue["rule"], issue["message"])].append(issue["prim"])
    listed = [{"rule": rule, "severity": severity, "prim": prims[0], "prims": sorted(set(prims))[:SAMPLES],
               "count": len(prims), "kind": "usd", "sentence": said(rule, message, len(prims))}
              for (severity, rule, message), prims in groups.items()]
    return sorted(listed, key=lambda item: (item["severity"] != "error", -item["count"], item["rule"]))


def said(rule, message, count):
    """A finding in words: how many, which rule, and the rule's own message."""
    return f"{count} x {rule}: {message}" if count > 1 else f"{rule}: {message}"
