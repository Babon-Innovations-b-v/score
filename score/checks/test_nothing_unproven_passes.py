"""The gate rules every stage shares: nothing unproven passes. Missing evidence answers unknown without asking the
check, unknown blocks like fail, nothing judged is unknown, a worse scorecard shows each way it got worse, and the grain
check fails a sparkling render by name and calls a picture with no flat area unknown.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/checks/test_nothing_unproven_passes.py

Each test turns red under the break written beside it (each applied once and seen red, 2026-10-26):
- missing evidence: in checks.judge drop the `check.evidence is not None and evidence is None` return.
- unknown blocks: in checks.combined return PASS when `not answers`, or test FAIL after UNKNOWN.
- refused verdicts: drop Verdict.__post_init__'s reason check.
- foreign verdict: drop judge's `found.check != check.name` test.
- regressions: in checks.measure_worse return `new < old` for "lower".
- waivers: in checks.standing ignore `waived`.
- grain: raise grain.GRAINY_PER_MILLE to 50 (the 2 % sparkle, about 20 per mille, then passes), or drop the
  `if flat.sum() < LEAST_FLAT: return None` in grain.specks.
- grain lines: in grain.isolated return `speck` unlined, or call a line nine long (`np.ones((9, 1), bool)`) (the
  fine lines test, 2026-10-30).
- guided smoothing (score/stages/light/mix, kept here: its only check, until the light stage's own file takes it):
  make mix.smoothed return its input.
"""
import numpy as np
import pytest
from PIL import Image

from score import checks
from score.checks import grain
from score.stages.light import mix


def a_check(answer=checks.PASS, evidence="a drop run", asked=None):
    def judge(output, inputs, found_evidence):
        if asked is not None:
            asked.append(found_evidence)
        return checks.Verdict("resting", answer, "judged")
    return checks.Check("resting", judge, evidence=evidence)


def test_missing_evidence_is_unknown_without_asking_the_check():
    """The fault this fixes: complete.py's resting check passed the square with no drop run."""
    asked = []
    found = checks.judge(a_check(asked=asked), "out", {}, None)
    assert found.answer == checks.UNKNOWN and asked == []
    assert checks.judge(a_check(asked=asked), "out", {}, "drop.json").answer == checks.PASS
    assert asked == ["drop.json"]
    assert checks.judge(a_check(evidence=None), "out", {}, None).answer == checks.PASS


@pytest.mark.parametrize("answers, expected", [
    ((), checks.UNKNOWN),
    ((checks.PASS, checks.PASS), checks.PASS),
    ((checks.PASS, checks.UNKNOWN), checks.UNKNOWN),
    ((checks.UNKNOWN, checks.FAIL, checks.PASS), checks.FAIL),
])
def test_unknown_blocks_like_fail_and_nothing_judged_is_unknown(answers, expected):
    verdicts = [checks.Verdict(f"c{index}", answer, "r") for index, answer in enumerate(answers)]
    assert checks.overall(verdicts) == expected
    assert checks.blocks(expected) == (expected != checks.PASS)


def test_a_waived_check_counts_as_a_pass_and_only_that_one():
    card = checks.scorecard([checks.Verdict("grain", checks.FAIL, "specks"),
                             checks.Verdict("resting", checks.UNKNOWN, "no drop run")])
    assert checks.standing(card, {"grain"}) == checks.UNKNOWN
    assert checks.standing(card, {"grain", "resting"}) == checks.PASS
    assert checks.standing(card, set()) == checks.FAIL


@pytest.mark.parametrize("answer, reason", [("pass", " "), ("maybe", "a reason")])
def test_a_verdict_without_a_reason_or_with_a_fourth_answer_is_refused(answer, reason):
    with pytest.raises(ValueError):
        checks.Verdict("a", answer, reason)


def test_a_check_returning_another_checks_verdict_is_an_error():
    wrong = checks.Check("placeholders", lambda *arguments: checks.Verdict("other", checks.PASS, "fine"))
    with pytest.raises(TypeError):
        checks.judge(wrong, "out", {}, None)


def card(answer, faults):
    return checks.scorecard([checks.Verdict("placeholders", answer, "r", {"faults": faults}, {"faults": "lower"})])


def test_a_worse_answer_or_measure_is_a_regression_and_an_equal_or_better_one_is_not():
    accepted = card(checks.PASS, 3)
    assert checks.regressions(card(checks.PASS, 3), accepted) == []
    assert checks.regressions(card(checks.PASS, 1), accepted) == []
    assert checks.regressions(card(checks.FAIL, 12), accepted) == [
        "placeholders: pass became fail",
        "placeholders: faults 3 became 12 (lower is better)"]
    assert checks.regressions({}, accepted) == ["placeholders: judged on the accepted output, not on this one"]


def wall(specks=0.0):
    """A 200 x 200 lit wall (a soft ramp, a hard edge down its middle), `specks` of its pixels sparkling, seeded."""
    rows = np.linspace(60.0, 140.0, 200)[:, None] * np.ones((1, 200))
    rows[:, 100:] += 60.0
    rows[np.random.default_rng(1).random(rows.shape) < specks] = 255.0
    return Image.fromarray(rows.astype(np.uint8)).convert("RGB")


def saved(folder, name, picture):
    picture.save(folder / name)
    return folder / name


def test_a_clean_render_passes_and_a_sparkling_one_fails_by_name(tmp_path):
    """The owner, 2026-10-20: the Library's Camp picture full of fireflies and grain. 2 % sparkling pixels is about
    20 per mille of the flat area, far over the 3 per mille line; a clean ramp has none."""
    clean, grainy = saved(tmp_path, "clean.png", wall()), saved(tmp_path, "camp.png", wall(0.02))
    assert grain.specks(clean) == 0.0
    assert 10.0 < grain.specks(grainy) < 30.0
    assert grain.verdict("grain", [clean], tmp_path).answer == checks.PASS
    failed = grain.verdict("grain", [clean, grainy], tmp_path)
    assert failed.answer == checks.FAIL and failed.measures["grainy"] == 1
    assert len(failed.findings) == 1 and failed.findings[0].startswith("grainy picture camp.png:")
    assert "unmeasured" in failed.reason


def test_a_pattern_of_fine_lines_is_no_grain_and_a_mix_is_judged_by_its_isolated_specks(tmp_path):
    """2026-10-30: habitat's from-door-3 read 5.7 per mille, 93-96% of it vertical streaks of a curtain's fine pleats.
    Lines one pixel wide, eight long, every fifth column, are no specks; the 2 % sparkle over them still fails, and
    counts as on the bare wall."""
    pleats = np.asarray(wall().convert("L"), dtype=np.float64)
    for column in range(2, 200, 5):
        pleats[(np.arange(200) // 8 + column) % 3 == 0, column] += 20.0
    pleated = saved(tmp_path, "pleats.png", Image.fromarray(pleats.astype(np.uint8)).convert("RGB"))
    sparkle = np.asarray(wall(0.02).convert("L")) == 255
    mixed = saved(tmp_path, "mixed.png", Image.fromarray(np.where(sparkle, 255, pleats).astype(np.uint8)))
    assert grain.specks(pleated) < 0.5
    assert grain.verdict("grain", [pleated], tmp_path).answer == checks.PASS
    assert abs(grain.specks(mixed) - grain.specks(saved(tmp_path, "camp.png", wall(0.02)))) < 3.0
    assert grain.verdict("grain", [mixed], tmp_path).answer == checks.FAIL


def test_a_picture_with_no_flat_area_or_no_picture_is_unknown(tmp_path):
    noise = np.random.default_rng(2).integers(0, 255, (200, 200), dtype=np.uint8)
    busy = saved(tmp_path, "busy.png", Image.fromarray(noise))
    assert grain.specks(busy) is None
    assert grain.verdict("grain", [busy]).answer == checks.UNKNOWN
    assert grain.verdict("grain", []).answer == checks.UNKNOWN


def test_the_guided_smoothing_keeps_the_edge_and_takes_out_the_specks():
    guide = np.full((80, 80), 0.3)
    guide[:, 40:] = 0.7
    ratio = np.where(guide > 0.5, 1.5, 1.0)
    noisy = ratio + np.random.default_rng(3).normal(0.0, 0.2, ratio.shape)
    smooth = mix.smoothed(noisy, guide)
    assert np.abs(smooth - ratio)[:, 2:-2].std() < 0.25 * np.abs(noisy - ratio).std()
    assert abs(smooth[:, 30:38].mean() - 1.0) < 0.05 and abs(smooth[:, 42:50].mean() - 1.5) < 0.05
