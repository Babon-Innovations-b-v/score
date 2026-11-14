"""No take leaves loudness.py louder than the rule (the owner was blasted by loud takes while picking, 2026-10-06): a
take comes out at its category's target under the -3 dBTP true-peak ceiling and at most -19 LUFS, or it is dropped
and its file removed; silence is dropped; the same take levelled twice is the same bytes (#40: every place's copy of
one sound had bytes of its own).

One test, two tables fed through the code's own entry points: TAKES (a signal, its category, whether it starts near
full scale, whether it must be kept) each levelled twice by normalise and judged by the rule, and READINGS (ebur128's
printed text and the loudness and true peak it must read as) through summary_of. The signals are ffmpeg's own
sources (white noise at full scale, sines, silence), so the answers are the rule's numbers, not the code's.

The break that turns the test red (applied once each, seen red, reverted):

- summary_of's true-peak pattern reads `Sample peak:` instead of `True peak:` (the READINGS rows).
- the limiter's limit made 1.0 (no limit) (the blast and ticking rows).
- the limiter's limit made 1.0 and normalise's `if not is_kept(after, target):` made `if False:` (the click row).
- normalise's silent check made `if False:` and is_kept's floor `and measured["lufs"] >= target - UNDER_LU`
  dropped (nothing refuses a silent take then) (the silence row).
- the `-fflags +bitexact -flags:a +bitexact` dropped (every kept row's second levelling).

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest tools/sound/loudness/test_no_take_leaves_louder_than_the_rule.py
"""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import loudness  # noqa: E402

CEILING = -3.0  # dBTP, the rule's ceiling
LOUDEST = -19.0  # LUFS, the rule's loudest level for any file
TARGETS = {"room": -26.0, "loop": -24.0, "shot": -20.0}  # the rule's targets, LUFS

BLAST = "anoisesrc=color=white:amplitude=1.0"
# a quiet 220 Hz hum (a tenth of full scale) with a full-scale 1 ms tick each second: its peaks stand 24 dB over it
TICKING_HUM = "aevalsrc=exprs='if(lt(mod(t\\,1)\\,0.001)\\,1\\,0.1*sin(2*PI*220*t))':s=48000"
# 50 ms of the quiet hum with its full-scale tick in the middle (past the 8 ms fades): too short to level, so it is
# measured repeated to three seconds, then either kept under the rule or dropped, never passed on loud
MIDDLE_TICK = "aevalsrc=exprs='if(lt(abs(t-0.025)\\,0.0005)\\,1\\,0.1*sin(2*PI*220*t))':s=48000"

# (row id, ffmpeg source, seconds, category, starts near full scale, kept: True must, False must not, None either)
TAKES = [
    *[(f"blast-{category}", BLAST, 4, category, True, True) for category in sorted(TARGETS)],
    *[(f"ticking-{category}", TICKING_HUM, 4, category, True, True) for category in sorted(TARGETS)],
    ("click-too-short", MIDDLE_TICK, 0.05, "shot", False, None),
    ("silence", "anullsrc=r=48000:cl=mono", 2, "room", False, False),
    ("hum", "sine=frequency=220", 2, "room", False, True),
]

SHOWN = ("[Parsed_ebur128_0 @ 0x1] t: 0.1 M: -30.0\nSummary:\n\n  Integrated loudness:\n    I:         -23.4 LUFS\n"
         "  Loudness range:\n    LRA:         0.0 LU\n  Sample peak:\n    Peak:       -6.0 dBFS\n"
         "  True peak:\n    Peak:       -4.2 dBFS\n")
# (row id, ebur128's printed text, what it reads as: a measure, or ValueError)
READINGS = [
    ("summary", SHOWN, {"lufs": -23.4, "true_peak": -4.2}),
    ("silent-summary", SHOWN.replace("-23.4", "-inf"), {"lufs": -120.0, "true_peak": -4.2}),
    ("no-summary", "no summary here", ValueError),
]


def synthetic(path, source, seconds):
    """A test signal from ffmpeg's own sources, written as a WAV."""
    subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"{source}:d={seconds}", "-ar", "48000", "-ac", "1", str(path)], check=True)
    return path


def test_no_take_leaves_louder_than_the_rule(tmp_path):
    for row, shown, expected in READINGS:
        if expected is ValueError:
            with pytest.raises(ValueError):
                loudness.summary_of(shown)
        else:
            assert loudness.summary_of(shown) == expected, row

    for row, source, seconds, category, starts_loud, must_keep in TAKES:
        take = synthetic(tmp_path / f"{row}.wav", source, seconds)
        if starts_loud:
            assert loudness.measure(take)["true_peak"] > -1.0, row  # it starts near full scale
        first, second = tmp_path / f"{row}-first.ogg", tmp_path / f"{row}-second.ogg"
        measured = loudness.normalise(take, first, TARGETS[category])
        if must_keep is not None:
            assert (measured is not None) == must_keep, (row, measured)
        if measured is None:
            assert not first.exists(), row  # a dropped take leaves no file behind
            continue
        after = loudness.measure(first)
        assert after["true_peak"] <= CEILING and after["lufs"] <= LOUDEST, (row, after)
        if must_keep:
            assert abs(after["lufs"] - TARGETS[category]) <= 1.0, (row, after)
        loudness.normalise(take, second, TARGETS[category])
        assert first.read_bytes() == second.read_bytes(), row  # the same take levelled twice is the same bytes
