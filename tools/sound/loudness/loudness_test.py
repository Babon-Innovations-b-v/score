"""Check the loudness rule (loudness.py): a blasting take comes out under the ceiling and at its target, a silent
one is dropped. (That the limits match the game's own test, and its files' measures, is checked in the game 2099.)

Plain python and ffmpeg, run by the gate: python3 tools/sound/loudness/loudness_test.py
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import loudness  # noqa: E402



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


def check_the_summary_is_read():
    shown = "Summary:\n\n  Integrated loudness:\n    I:         -23.4 LUFS\n  True peak:\n    Peak:       -4.2 dBFS\n"
    assert loudness.summary_of(shown) == {"lufs": -23.4, "true_peak": -4.2}


def main():
    check_the_summary_is_read()
    check_every_target_is_under_the_limit()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        check_a_full_scale_blast_is_brought_under_the_ceiling(folder)
        check_a_short_click_is_measured_and_kept_safe(folder)
        check_silence_is_dropped(folder)
    print("loudness: all checks passed")


if __name__ == "__main__":
    main()
