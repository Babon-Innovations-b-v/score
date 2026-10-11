"""The surface stage's gate helpers: a verdict over a list of faults, and a judge that answers unknown, never crashes
and never passes, when what it reads is not there (missing evidence is unknown)."""
import functools
import json

from score import checks


def verdict(name, failing, total, what, measures=None):
    """Fail naming each fault (on its model), else pass; `failing` counted as a measure, lower is better."""
    return checks.Verdict(name, checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {total} {what}" if failing else f"all {total} pass",
                          {"failing": len(failing), **(measures or {})}, {"failing": "lower"}, tuple(failing[:40]))


def unknown(name, reason):
    return checks.Verdict(name, checks.UNKNOWN, reason)


def guarded(name, judge):
    """`judge` as a check named `name`: a file or entry it reads that is missing answers unknown with what was
    missing, so the node blocks with a reason instead of erroring."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        try:
            return judge(output, inputs, evidence)
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as missing:
            return unknown(name, f"cannot tell: {type(missing).__name__}: {missing}")
    return checks.Check(name, judged)
