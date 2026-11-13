"""The gate rules every stage shares: nothing unproven passes. Missing evidence answers unknown without asking the
check, unknown blocks like fail, nothing judged is unknown, a worse scorecard shows each way it got worse, and the grain
check fails a sparkling render by name and calls a picture with no flat area unknown.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/checks/test_nothing_unproven_passes.py

One world: five pictures (a clean lit wall, the same wall sparkling, a curtain of fine pleats, the pleats sparkling,
a picture of noise with no flat area) and four checks (grain over renders, resting over a drop run, placeholders
needing nothing, a stray one answering for another check). Each row of the judge table is one output put to one check;
the verdicts are then combined, scored, waived and compared as a node's gate does.

The test turns red under each break written below (each applied once and seen red, 2026-10-26; the fold into one
test function re-proved each, 2026-11-13):
- missing evidence: in checks.judge drop the `check.evidence is not None and evidence is None` return.
- unknown blocks: in checks.combined return PASS when `not answers`, or test FAIL after UNKNOWN.
- refused verdicts: drop Verdict.__post_init__'s reason check.
- foreign verdict: drop judge's `found.check != check.name` test.
- regressions: in checks.measure_worse return `new < old` for "lower".
- waivers: in checks.standing ignore `waived`.
- grain: raise grain.GRAINY_PER_MILLE to 50 (the 2 % sparkle, about 20 per mille, then passes), or drop the
  `if flat.sum() < LEAST_FLAT: return None` in grain.specks.
- grain lines: in grain.isolated return `speck` unlined, or call a line nine long (`np.ones((9, 1), bool)`) (the
  fine lines rows, 2026-10-30).
- guided smoothing (score/stages/light/mix, kept here: its only check, until the light stage's own file takes it):
  make mix.smoothed return its input.
"""
import numpy as np
import pytest
from PIL import Image

from score import checks
from score.checks import grain
from score.stages.light import mix


def wall(specks=0.0):
    """A 200 x 200 lit wall (a soft ramp, a hard edge down its middle), `specks` of its pixels sparkling, seeded."""
    rows = np.linspace(60.0, 140.0, 200)[:, None] * np.ones((1, 200))
    rows[:, 100:] += 60.0
    rows[np.random.default_rng(1).random(rows.shape) < specks] = 255.0
    return Image.fromarray(rows.astype(np.uint8)).convert("RGB")


def pictures(folder):
    """The world's pictures by name, saved in `folder`. The Camp picture (the owner, 2026-10-20: the Library's Camp
    full of fireflies and grain) is the wall with 2 % sparkling pixels, about 20 per mille of the flat area, far over
    the 3 per mille line. The pleats (2026-10-30: habitat's from-door-3 read 5.7 per mille, 93-96 % of it a curtain's
    vertical streaks) are lines one pixel wide, eight long, every fifth column; the mix is the same sparkle over them."""
    pleats = np.asarray(wall().convert("L"), dtype=np.float64)
    for column in range(2, 200, 5):
        pleats[(np.arange(200) // 8 + column) % 3 == 0, column] += 20.0
    sparkle = np.asarray(wall(0.02).convert("L")) == 255
    noise = np.random.default_rng(2).integers(0, 255, (200, 200), dtype=np.uint8)
    made = {"clean.png": wall(), "camp.png": wall(0.02),
            "pleats.png": Image.fromarray(pleats.astype(np.uint8)).convert("RGB"),
            "mixed.png": Image.fromarray(np.where(sparkle, 255, pleats).astype(np.uint8)),
            "busy.png": Image.fromarray(noise)}
    for name, picture in made.items():
        picture.save(folder / name)
    return {name.removesuffix(".png"): folder / name for name in made}


def test_nothing_unproven_passes(tmp_path):
    shot = pictures(tmp_path)
    asked = []

    def resting(output, inputs, evidence):
        asked.append(evidence)
        return checks.Verdict("resting", checks.PASS, "judged")

    grain_check = checks.Check("grain", lambda output, inputs, renders: grain.verdict("grain", renders, tmp_path),
                               evidence="renders")
    resting_check = checks.Check("resting", resting, evidence="a drop run")
    placeholders = checks.Check("placeholders", lambda *arguments: checks.Verdict("placeholders", checks.PASS, "fine"))
    stray = checks.Check("stray", lambda *arguments: checks.Verdict("other", checks.PASS, "fine"))

    # (row, check, evidence, the answer, or the error judge raises). The resting fault this fixes: complete.py's
    # resting check passed the square with no drop run.
    judged = [
        ("no drop run", resting_check, None, checks.UNKNOWN),
        ("a drop run", resting_check, "drop.json", checks.PASS),
        ("needs no evidence", placeholders, None, checks.PASS),
        ("another check's verdict", stray, None, TypeError),
        ("no renders", grain_check, None, checks.UNKNOWN),
        ("clean", grain_check, [shot["clean"]], checks.PASS),
        ("clean and camp", grain_check, [shot["clean"], shot["camp"]], checks.FAIL),
        ("fine pleats", grain_check, [shot["pleats"]], checks.PASS),
        ("sparkle over pleats", grain_check, [shot["mixed"]], checks.FAIL),
        ("no flat area", grain_check, [shot["busy"]], checks.UNKNOWN),
        ("no picture", grain_check, [], checks.UNKNOWN),
    ]
    verdict = {}
    for row, check, evidence, expected in judged:
        before = len(asked)
        if isinstance(expected, type):
            with pytest.raises(expected):
                checks.judge(check, "out", {}, evidence)
            continue
        verdict[row] = checks.judge(check, "out", {}, evidence)
        assert verdict[row].answer == expected, f"{row}: {verdict[row]}"
        assert evidence is not None or len(asked) == before, f"{row}: asked the check without its evidence"
    assert asked == ["drop.json"]

    # The grain measure under the verdicts: a clean ramp has no specks, the sparkle 10 to 30 per mille, the pleats
    # none, the sparkle over pleats counts as on the bare wall, and noise has no flat area to measure.
    specks = {name: grain.specks(path) for name, path in shot.items()}
    assert specks["clean"] == 0.0 and 10.0 < specks["camp"] < 30.0 and specks["pleats"] < 0.5
    assert abs(specks["mixed"] - specks["camp"]) < 3.0 and specks["busy"] is None
    failed = verdict["clean and camp"]
    assert failed.measures["grainy"] == 1 and "unmeasured" in failed.reason
    assert len(failed.findings) == 1 and failed.findings[0].startswith("grainy picture camp.png:")

    # A node's answer over its verdicts: unknown blocks like fail, and nothing judged is unknown.
    for rows, expected in [((), checks.UNKNOWN), (("clean", "needs no evidence"), checks.PASS),
                           (("clean", "no drop run"), checks.UNKNOWN),
                           (("no drop run", "clean and camp", "clean"), checks.FAIL)]:
        assert checks.overall([verdict[row] for row in rows]) == expected, rows
        assert checks.blocks(expected) == (expected != checks.PASS)

    # A waived check counts as a pass, and only that one.
    card = checks.scorecard([verdict["clean and camp"], verdict["no drop run"]])
    for waived, expected in [(set(), checks.FAIL), ({"grain"}, checks.UNKNOWN), ({"grain", "resting"}, checks.PASS)]:
        assert checks.standing(card, waived) == expected, waived

    # A worse answer or measure is a regression; an equal or better one is not.
    clean_card, camp_card = checks.scorecard([verdict["clean"]]), checks.scorecard([verdict["clean and camp"]])
    worst = failed.measures["worst_per_mille"]
    assert checks.regressions(camp_card, camp_card) == [] and checks.regressions(clean_card, camp_card) == []
    assert checks.regressions(camp_card, clean_card) == [
        "grain: pass became fail", "grain: grainy 0 became 1 (lower is better)",
        f"grain: worst_per_mille 0.0 became {worst} (lower is better)"]
    assert checks.regressions({}, clean_card) == ["grain: judged on the accepted output, not on this one"]

    # A verdict without a reason, or with a fourth answer, is refused.
    for answer, reason in [("pass", " "), ("maybe", "a reason")]:
        with pytest.raises(ValueError):
            checks.Verdict("a", answer, reason)

    # The light stage's guided smoothing keeps the edge and takes out the specks.
    guide = np.full((80, 80), 0.3)
    guide[:, 40:] = 0.7
    ratio = np.where(guide > 0.5, 1.5, 1.0)
    noisy = ratio + np.random.default_rng(3).normal(0.0, 0.2, ratio.shape)
    smooth = mix.smoothed(noisy, guide)
    assert np.abs(smooth - ratio)[:, 2:-2].std() < 0.25 * np.abs(noisy - ratio).std()
    assert abs(smooth[:, 30:38].mean() - 1.0) < 0.05 and abs(smooth[:, 42:50].mean() - 1.5) < 0.05
