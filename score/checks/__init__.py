"""The gate rules every stage shares: a check answers pass, fail or unknown, with its measures and a reason.

    verdict = checks.judge(check, output_folder, inputs, evidence_file_or_None)
    checks.overall([verdict, ...])          # "fail" if any failed, else "unknown" if any is unknown or none ran
    checks.regressions(new_card, accepted_card)   # what got worse, as lines; empty when nothing did

Unknown blocks like fail. A check that needs evidence (a drop run, a render) and has none answers unknown without
being asked, so missing evidence can never pass (the fault this fixes: complete.py's resting check passed the square
with no drop run). A list of no verdicts is unknown too: nothing judged proves nothing.

A scorecard is {check name: verdict as a dict}. A new output is worse than the accepted one when any check's answer
drops (pass, then unknown, then fail) or a measure the check marks in `better` moves the wrong way.
"""
from dataclasses import asdict, dataclass, field
from typing import Callable

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
ANSWERS = (PASS, UNKNOWN, FAIL)  # best first


@dataclass(frozen=True)
class Verdict:
    check: str
    answer: str
    reason: str
    measures: dict = field(default_factory=dict)
    better: dict = field(default_factory=dict)  # {measure: "lower" or "higher"}: the measures compared on accept
    findings: tuple = ()  # each fault in words, for the review page

    def __post_init__(self):
        if self.answer not in ANSWERS:
            raise ValueError(f"{self.check}: answer {self.answer!r} is not one of {ANSWERS}")
        if not self.reason.strip():
            raise ValueError(f"{self.check}: a verdict needs a reason")
        unknown_sides = {side for side in self.better.values()} - {"lower", "higher"}
        if unknown_sides or set(self.better) - set(self.measures):
            raise ValueError(f"{self.check}: `better` names a measure it lacks or a side other than lower/higher")


@dataclass(frozen=True)
class Check:
    """One gate of a stage. `judge(output, inputs, evidence)` returns a Verdict; `evidence` names the evidence it
    needs (None: it reads the output and the inputs alone)."""
    name: str
    judge: Callable
    evidence: str | None = None


def missing_evidence(check):
    """The unknown a check answers when the evidence it needs is not there."""
    return Verdict(check.name, UNKNOWN, f"no evidence: {check.evidence} for this output is missing")


def judge(check, output, inputs, evidence):
    """The check's verdict on a stored output; unknown without asking when its evidence is missing."""
    if check.evidence is not None and evidence is None:
        return missing_evidence(check)
    found = check.judge(output, inputs, evidence)
    if not isinstance(found, Verdict) or found.check != check.name:
        raise TypeError(f"check {check.name} returned {found!r}, not its own Verdict")
    return found


def overall(verdicts):
    """The node's answer: fail if any check failed, else unknown if any is unknown or none ran, else pass."""
    return combined({verdict.answer for verdict in verdicts})


def standing(scorecard, waived):
    """A judgement's answer once the owner's waivers count: a waived check's verdict counts as a pass."""
    return combined({PASS if name in waived else verdict["answer"] for name, verdict in scorecard.items()})


def combined(answers):
    """Fail if any answer is fail, else unknown if any is unknown or there are none, else pass."""
    if FAIL in answers:
        return FAIL
    if UNKNOWN in answers or not answers:
        return UNKNOWN
    return PASS


def blocks(answer):
    """True for every answer but pass: unknown blocks like fail."""
    return answer != PASS


def scorecard(verdicts):
    """{check: verdict as a dict}, as records and judgements store it."""
    return {verdict.check: {**asdict(verdict), "findings": list(verdict.findings)} for verdict in verdicts}


def measure_worse(name, side, new, old):
    """True when a measure moved the wrong way for its side."""
    return new > old if side == "lower" else new < old


def regressions(new_card, accepted_card):
    """Each way the new scorecard is worse than the accepted one, as a line; a check the accepted one had and the new
    one lacks counts as worse."""
    worse = []
    for name, old in accepted_card.items():
        new = new_card.get(name)
        if new is None:
            worse.append(f"{name}: judged on the accepted output, not on this one")
            continue
        if ANSWERS.index(new["answer"]) > ANSWERS.index(old["answer"]):
            worse.append(f"{name}: {old['answer']} became {new['answer']}")
        for measure, side in old.get("better", {}).items():
            if measure in new["measures"] and measure_worse(measure, side, new["measures"][measure],
                                                            old["measures"][measure]):
                worse.append(f"{name}: {measure} {old['measures'][measure]} became {new['measures'][measure]} "
                             f"({side} is better)")
    return worse
