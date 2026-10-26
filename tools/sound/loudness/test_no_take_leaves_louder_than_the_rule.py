"""No take leaves loudness.py louder than the rule (the owner was blasted by loud takes while picking, 2026-10-06): a
take comes out at its category's target under the -3 dBTP true-peak ceiling and at most -19 LUFS, or it is dropped
and its file removed; silence is dropped; the same take levelled twice is the same bytes (#40: every place's copy of
one sound had bytes of its own).

The signals are ffmpeg's own sources (white noise at full scale, sines, silence), so the answers are the rule's
numbers, not the code's.

The break that turns each test red (applied once each, seen red, reverted):

- test_ebur128s_summary_is_read: summary_of's true-peak pattern reads `Sample peak:` instead of `True peak:`.
- test_a_full_scale_blast_comes_out_at_each_target_under_the_ceiling: the limiter's limit made 1.0 (no limit).
- test_a_take_too_short_to_level_is_kept_safe_or_dropped: the limiter's limit made 1.0 and normalise's
  `if not is_kept(after, target):` made `if False:`.
- test_silence_is_dropped: normalise's silent check made `if False:` and is_kept's floor
  `and measured["lufs"] >= target - UNDER_LU` dropped (nothing refuses a silent take then).
- test_the_same_take_levelled_twice_is_the_same_bytes: the `-fflags +bitexact -flags:a +bitexact` dropped.

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


def synthetic(path, source, seconds):
    """A test signal from ffmpeg's own sources, written as a WAV."""
    subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"{source}:d={seconds}", "-ar", "48000", "-ac", "1", str(path)], check=True)
    return path


def test_ebur128s_summary_is_read():
    shown = ("[Parsed_ebur128_0 @ 0x1] t: 0.1 M: -30.0\nSummary:\n\n  Integrated loudness:\n    I:         -23.4 LUFS\n"
             "  Loudness range:\n    LRA:         0.0 LU\n  Sample peak:\n    Peak:       -6.0 dBFS\n"
             "  True peak:\n    Peak:       -4.2 dBFS\n")
    assert loudness.summary_of(shown) == {"lufs": -23.4, "true_peak": -4.2}
    assert loudness.summary_of(shown.replace("-23.4", "-inf")) == {"lufs": -120.0, "true_peak": -4.2}
    with pytest.raises(ValueError):
        loudness.summary_of("no summary here")


# a quiet 220 Hz hum (a tenth of full scale) with a full-scale 1 ms tick each second: its peaks stand 24 dB over it
TICKING_HUM = "aevalsrc=exprs='if(lt(mod(t\\,1)\\,0.001)\\,1\\,0.1*sin(2*PI*220*t))':s=48000"


@pytest.mark.parametrize("category", sorted(TARGETS))
def test_a_full_scale_blast_comes_out_at_each_target_under_the_ceiling(tmp_path, category):
    for name, source in (("blast", "anoisesrc=color=white:amplitude=1.0"), ("ticking", TICKING_HUM)):
        take = synthetic(tmp_path / f"{name}.wav", source, 4)
        assert loudness.measure(take)["true_peak"] > -1.0  # it starts near full scale
        out = tmp_path / f"{name}.ogg"
        assert loudness.normalise(take, out, TARGETS[category]) is not None, name  # one that can come down is kept
        after = loudness.measure(out)
        assert after["true_peak"] <= CEILING and after["lufs"] <= LOUDEST, (name, after)
        assert abs(after["lufs"] - TARGETS[category]) <= 1.0, (name, after)


def test_a_take_too_short_to_level_is_kept_safe_or_dropped(tmp_path):
    """50 ms of the quiet hum with its full-scale tick in the middle (past the 8 ms fades): measured repeated to three
    seconds, then either kept under the rule or dropped with its file removed, never passed on loud."""
    middle_tick = "aevalsrc=exprs='if(lt(abs(t-0.025)\\,0.0005)\\,1\\,0.1*sin(2*PI*220*t))':s=48000"
    click = synthetic(tmp_path / "click.wav", middle_tick, 0.05)
    out = tmp_path / "click.ogg"
    measured = loudness.normalise(click, out, TARGETS["shot"])
    if measured is None:
        assert not out.exists()
    else:
        again = loudness.measure(out)
        assert again["true_peak"] <= CEILING and again["lufs"] <= LOUDEST, again


def test_silence_is_dropped(tmp_path):
    quiet = synthetic(tmp_path / "quiet.wav", "anullsrc=r=48000:cl=mono", 2)
    assert loudness.normalise(quiet, tmp_path / "quiet.ogg", TARGETS["room"]) is None
    assert not (tmp_path / "quiet.ogg").exists()


def test_the_same_take_levelled_twice_is_the_same_bytes(tmp_path):
    hum = synthetic(tmp_path / "hum.wav", "sine=frequency=220", 2)
    loudness.normalise(hum, tmp_path / "first.ogg", TARGETS["room"])
    loudness.normalise(hum, tmp_path / "second.ogg", TARGETS["room"])
    assert (tmp_path / "first.ogg").read_bytes() == (tmp_path / "second.ogg").read_bytes()
