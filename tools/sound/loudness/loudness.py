"""How loud a sound file is, and bringing one to a safe level: the picker's hard rule against blasts.

The owner was blasted by loud takes while picking (2026-10-06), so nothing reaches the picking page or
the game without passing through here:

- **One loudness target a category** (integrated loudness, EBU R128 / ITU-R BS.1770, in LUFS): a room
  tone sits low, a hum a little higher, a short one-shot (a step, a clunk) highest, all at or under
  -20 LUFS.
- **A true-peak ceiling** of -3 dBTP on everything, held by a limiter run four times oversampled so
  the peaks between samples are caught too.
- **A take that cannot be brought in safely is dropped**, never passed on: over the ceiling after the
  limiter, or far off its target.

The measuring is ffmpeg's `ebur128` filter with `peak=true`. A short take (under three seconds, where
integrated loudness has too little to gate on) is measured repeated to three seconds, which is the
loudness of the take itself played over and over: a step heard as steps.

    python3 tools/sound/loudness/loudness.py measure <file>...
    python3 tools/sound/loudness/loudness.py manifest   # re-measure every game sound into its manifest
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
GAME_SOUND = REPO / "game" / "sound"
MANIFEST = GAME_SOUND / "loudness" / "loudness.json"
AUDIO_ENDINGS = (".ogg", ".wav", ".mp3")

## The true-peak ceiling every file keeps under, in dBTP.
CEILING_DBTP = -3.0
## The limiter's own ceiling, a little under the true-peak ceiling: the encoder adds a few tenths.
LIMITER_DBFS = -3.8
## The loudest any file may be, in LUFS: the loudest category's target and a little room.
LIMIT_LUFS = -19.0
## How far over its target a normalised take may land, and how far under, in LU, before it is dropped.
OVER_LU = 1.0
UNDER_LU = 6.0
## The loudness target a category's takes are brought to, in LUFS.
TARGETS = {
    "room": -26.0,   # a room's tone, a place's ambience
    "loop": -24.0,   # a hum, a buzz, a whir: a thing that goes on
    "shot": -20.0,   # a step, an impact, a hatch: short, over quickly
}
## How a file is written, by its ending: Ogg Vorbis for a one-shot, plain 16-bit PCM for a loop the game plays
## (Vorbis smears a file's first and last milliseconds, which clicks at a loop's join), FLAC for a loop's preview.
CODECS = {".ogg": ["-c:a", "libvorbis", "-q:a", "6"], ".wav": ["-c:a", "pcm_s16le"], ".flac": ["-c:a", "flac"]}
## Under this many seconds a take is measured repeated to it.
SHORT_SECONDS = 3.0
SILENT_LUFS = -70.0


def ffmpeg():
    """The ffmpeg on the path; a missing one is a broken box, said plainly."""
    found = shutil.which("ffmpeg")
    if not found:
        raise SystemExit("loudness: ffmpeg is not on the path; it measures every sound")
    return found


def seconds_of(path):
    """How long an audio file plays, in seconds."""
    shown = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    found = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", shown)
    if not found:
        raise ValueError(f"loudness: {path} has no duration ffmpeg can read")
    hours, minutes, rest = found.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(rest)


def measure(path):
    """A file's integrated loudness (LUFS) and true peak (dBTP), as {"lufs", "true_peak"}."""
    repeat = ["-stream_loop", "-1"] if seconds_of(path) < SHORT_SECONDS else []
    until = ["-t", str(SHORT_SECONDS)] if repeat else []
    command = [ffmpeg(), "-hide_banner", "-nostats", *repeat, "-i", str(path), *until,
               "-af", "ebur128=peak=true", "-f", "null", "-"]
    shown = subprocess.run(command, capture_output=True, text=True).stderr
    return summary_of(shown)


def summary_of(shown):
    """The loudness and true peak out of ebur128's printed summary."""
    summary = shown[shown.rfind("Summary:"):]
    loudness = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    peak = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not loudness or not peak:
        raise ValueError("loudness: ebur128 printed no summary")
    return {"lufs": _number(loudness.group(1)), "true_peak": _number(peak.group(1))}


def _number(text):
    return -120.0 if text == "-inf" else float(text)


def is_safe(measured, target):
    """Whether a measured take is safe to play at its category's target: under the true-peak ceiling and no
    louder than its target allows."""
    return measured["true_peak"] <= CEILING_DBTP and measured["lufs"] <= min(target + OVER_LU, LIMIT_LUFS)


def is_kept(measured, target):
    """Whether a normalised take is kept: safe, and not so far under its target that it is useless."""
    return is_safe(measured, target) and measured["lufs"] >= target - UNDER_LU


def normalise(source, out, target, fade_ms=8):
    """Bring a take to `target` LUFS under the true-peak ceiling, with a short fade in and out so it never
    starts or stops with a click (none for a loop, `fade_ms` 0: a fade would dip at its join every time round), and
    write it at `out` in the format its ending names (CODECS). The limiter's delay is taken back out, so a loop's join stays where it was.
    Gives back its measure afterwards, or None when it could not be brought in safely (the file is then removed)."""
    before = measure(source)
    if before["lufs"] <= SILENT_LUFS:
        return None
    gain = target - before["lufs"]
    length = seconds_of(source)
    fade = fade_ms / 1000.0
    chain = (f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={10 ** (LIMITER_DBFS / 20):.4f}:level=false"
             f":attack=1:release=50:latency=1,aresample=48000")
    if fade_ms > 0:
        chain += f",afade=t=in:d={fade},afade=t=out:st={max(length - fade, 0):.3f}:d={fade}"
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source), "-af", chain,
                    *CODECS[pathlib.Path(out).suffix.lower()], str(out)], check=True)
    after = measure(out)
    if not is_kept(after, target):
        pathlib.Path(out).unlink()
        return None
    return after


def sha256_of(path):
    """A file's SHA-256, the way Godot's FileAccess.get_sha256 gives it."""
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def game_files(folder=GAME_SOUND):
    """Every audio file under the game's sound folder, as res:// paths against their local paths."""
    found = {}
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() in AUDIO_ENDINGS:
            found["res://" + path.relative_to(REPO).as_posix()] = path
    return found


def manifest_for(files):
    """The loudness manifest for these files: each file's loudness, true peak and hash."""
    written = {}
    for res_path, path in files.items():
        written[res_path] = {**measure(path), "sha256": sha256_of(path)}
    return written


def write_manifest(path=MANIFEST):
    """Re-measure every game sound into the manifest the game's own test reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest_for(game_files()), indent="\t") + "\n")
    return path


def main(arguments):
    if arguments[:1] == ["measure"]:
        for path in arguments[1:]:
            print(json.dumps({"file": path, **measure(path)}))
        return 0
    if arguments[:1] == ["manifest"]:
        print(f"wrote {write_manifest()}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
