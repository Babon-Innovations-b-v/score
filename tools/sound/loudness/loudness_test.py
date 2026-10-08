"""Check the loudness rule (loudness.py): a blasting take comes out under the ceiling and at its target, a silent
one is dropped, the limits match the game's own test, and every game sound file's measure is current.

Plain python and ffmpeg, run by the gate: python3 tools/sound/loudness/loudness_test.py
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import loudness  # noqa: E402

GAME_RULE = loudness.GAME_SOUND / "loudness" / "sound_loudness.gd"


def synthetic(path, source, seconds):
    """A test signal from ffmpeg's own sources, written as a WAV."""
    subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"{source}:d={seconds}", "-ar", "48000", "-ac", "1", str(path)], check=True)
    return path


def check_a_full_scale_blast_is_brought_under_the_ceiling(folder):
    blast = synthetic(folder / "blast.wav", "anoisesrc=color=white:amplitude=1.0", 4)
    assert loudness.measure(blast)["true_peak"] > -1.0, "the test blast should start near full scale"
    measured = loudness.normalise(blast, folder / "blast.ogg", loudness.TARGETS["shot"])
    assert measured is not None, "a loud take that can be brought down is kept"
    again = loudness.measure(folder / "blast.ogg")
    assert again["true_peak"] <= loudness.CEILING_DBTP, again
    assert abs(again["lufs"] - loudness.TARGETS["shot"]) <= 1.0, again


def check_a_short_click_is_measured_and_kept_safe(folder):
    click = synthetic(folder / "click.wav", "sine=frequency=2000", 0.05)
    measured = loudness.normalise(click, folder / "click.ogg", loudness.TARGETS["shot"])
    if measured is not None:
        assert measured["true_peak"] <= loudness.CEILING_DBTP, measured


def check_silence_is_dropped(folder):
    quiet = synthetic(folder / "quiet.wav", "anullsrc=r=48000:cl=mono", 2)
    assert loudness.normalise(quiet, folder / "quiet.ogg", loudness.TARGETS["room"]) is None
    assert not (folder / "quiet.ogg").exists()


def check_every_target_is_under_the_limit():
    for category, target in loudness.TARGETS.items():
        assert target <= loudness.LIMIT_LUFS, category


def check_the_game_holds_the_same_limits():
    text = GAME_RULE.read_text()
    ceiling = float(re.search(r"CEILING_DBTP := (-?[\d.]+)", text).group(1))
    limit = float(re.search(r"LIMIT_LUFS := (-?[\d.]+)", text).group(1))
    assert ceiling == loudness.CEILING_DBTP and limit == loudness.LIMIT_LUFS, (ceiling, limit)


def check_every_game_sound_is_measured_as_it_is():
    measured = json.loads(loudness.MANIFEST.read_text())
    for res_path, path in loudness.game_files().items():
        assert res_path in measured, f"{res_path}: not measured; run bash tools/sound/run.sh loudness"
        assert measured[res_path]["sha256"] == loudness.sha256_of(path), f"{res_path}: changed since measured"


def check_the_summary_is_read():
    shown = "Summary:\n\n  Integrated loudness:\n    I:         -23.4 LUFS\n  True peak:\n    Peak:       -4.2 dBFS\n"
    assert loudness.summary_of(shown) == {"lufs": -23.4, "true_peak": -4.2}


def main():
    check_the_summary_is_read()
    check_every_target_is_under_the_limit()
    check_the_game_holds_the_same_limits()
    check_every_game_sound_is_measured_as_it_is()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        check_a_full_scale_blast_is_brought_under_the_ceiling(folder)
        check_a_short_click_is_measured_and_kept_safe(folder)
        check_silence_is_dropped(folder)
    print("loudness: all checks passed")


if __name__ == "__main__":
    main()
