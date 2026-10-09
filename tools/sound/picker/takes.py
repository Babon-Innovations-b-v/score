"""Turning a fetched candidate into takes the owner can hear safely: the same for every source.

1. **Trim** the silence off both ends.
2. **Shape it for its use**: a run of footsteps is cut into single steps at the gaps between them (the game plays
   one at random a step, up to eight); a loop keeps a stretch of its steady middle and has its end crossfaded into
   its start, so it joins itself with no click; a one-shot is kept whole, up to its length limit.
3. **The loudness rule** (tools/sound/loudness/): every take is brought to its category's target under the
   -3 dBTP true-peak ceiling and faded in and out over a few milliseconds. A take that cannot be is dropped.
4. **Its waveform**, as peaks for the page to draw.

Plain python and ffmpeg: samples go through ffmpeg as 16-bit PCM at 48 kHz.
"""
import array
import math
import pathlib
import struct
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "loudness"))
import loudness  # noqa: E402

RATE = 48000
## Below this level (dBFS) a stretch is silence, for trimming and for cutting steps apart.
SILENCE_DB = -45.0
## How short a step can be, in seconds.
STEP_SHORTEST_SECONDS = 0.08
STEPS_KEPT = 8
## A step lands where the level rises this many dB over the quietest of the 100 ms before it, within this many dB
## of the loudest step, at least 0.35 s after the last (a walk is about two steps a second); a step is kept up to this long.
STEP_RISE_DB = 9.0
STEP_LOOKBACK = 10
STEP_BELOW_PEAK_DB = 30.0
STEP_APART = 35
STEP_LONGEST_SECONDS = 0.6
## A loop keeps this much of its middle, in seconds, and crossfades this much of its end into its start.
LOOP_SECONDS = 16.0
LOOP_JOIN_SECONDS = 1.5
## What a loop leaves off each end before it is joined, in seconds: a generated take swells in and dies away there.
LOOP_EDGE_SECONDS = 1.0
## The longest a one-shot is kept, in seconds.
SHOT_SECONDS = 8.0
## The longest stretch of a fetched file that is read, in seconds.
READ_SECONDS = 120
## How much of a loop's other end its page preview carries on each side, in seconds.
LOOP_PREVIEW_PAD_SECONDS = 0.1
## The waveform's number of bars.
PEAKS = 160
## The loudness target each category of need is brought to (the loudness module's).
TARGET = {"steps": "shot", "shot": "shot", "loop": "loop", "room": "room"}
## The gap between steps in a walk's preview, in seconds.
WALK_GAP_SECONDS = 0.42


def decode(path, channels=1):
    """A file's samples as 16-bit integers at RATE, interleaved when `channels` is 2."""
    raw = subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-t", str(READ_SECONDS), "-f", "s16le",
                          "-ac", str(channels), "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    samples = array.array("h")
    samples.frombytes(raw)
    return samples


def write_wav(samples, path, channels=1):
    """Samples written as a 16-bit WAV at RATE."""
    subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "s16le", "-ac",
                    str(channels), "-ar", str(RATE), "-i", "-", str(path)], input=samples.tobytes(), check=True)
    return path


def level_of(sample):
    """How far a sample is from silence, as a share of full scale."""
    return abs(sample) / 32768.0


def loud_frames(samples, channels, window):
    """For each window of frames, whether its peak is over SILENCE_DB."""
    floor = 10 ** (SILENCE_DB / 20)
    starts = range(0, len(samples) // channels, window)
    chunks = (samples[start * channels:(start + window) * channels] for start in starts)
    return [bool(chunk) and max(level_of(value) for value in chunk) > floor for chunk in chunks]


def trimmed(samples, channels):
    """The samples with the silence off both ends (a whole silent take comes back empty)."""
    window = RATE // 100
    flags = loud_frames(samples, channels, window)
    if not any(flags):
        return array.array("h")
    first = flags.index(True)
    last = len(flags) - 1 - flags[::-1].index(True)
    return samples[first * window * channels:(last + 1) * window * channels]


def envelope_db(samples, window):
    """The loudness of each window of a mono take, as its RMS in dBFS (-100 for silence)."""
    found = []
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        power = sum(value * value for value in chunk) / max(1, len(chunk)) / (32768.0 * 32768.0)
        found.append(10 * math.log10(power) if power > 1e-10 else -100.0)
    return found


def onsets_in(levels):
    """The windows where a step lands: the level jumps STEP_RISE_DB over the quietest of the moment before it, near
    enough the loudest step, and far enough after the last one."""
    loudest = max(levels, default=-100.0)
    found = []
    for index, level in enumerate(levels):
        before = min(levels[max(0, index - STEP_LOOKBACK):index], default=-100.0)
        if level - before >= STEP_RISE_DB and level >= loudest - STEP_BELOW_PEAK_DB:
            if not found or index - found[-1] >= STEP_APART:
                found.append(index)
    return found


def steps_in(samples):
    """A mono run of footsteps cut into single steps at the moments each lands, at most STEPS_KEPT: each from just
    before it lands to just before the next, never longer than STEP_LONGEST_SECONDS. A walk recorded in a hall
    never falls silent between steps, so the cut is by where each step starts, not by gaps."""
    window = RATE // 100
    starts = onsets_in(envelope_db(samples, window))
    longest = int(STEP_LONGEST_SECONDS * RATE)
    found = []
    for index, onset in enumerate(starts):
        begin = max(0, (onset - 1) * window)
        following = starts[index + 1] * window - 2 * window if index + 1 < len(starts) else len(samples)
        end = min(following, begin + longest, len(samples))
        if end - begin >= int(STEP_SHORTEST_SECONDS * RATE):
            found.append(samples[begin:end])
    return found[:STEPS_KEPT]


def looped(samples, channels):
    """A stretch of a take's steady middle with its end crossfaded into its start: played over and over, it joins
    with no click and no jump. A take shorter than two joins is kept as it is."""
    frames = len(samples) // channels
    edge = min(int(LOOP_EDGE_SECONDS * RATE), frames // 10)
    keep = min(frames - 2 * edge, int(LOOP_SECONDS * RATE))
    join = int(LOOP_JOIN_SECONDS * RATE)
    if keep < 2 * join:
        return samples
    start = (frames - keep) // 2
    middle = samples[start * channels:(start + keep) * channels]
    body = array.array("h", middle[:(keep - join) * channels])
    for frame in range(join):
        share = frame / join
        for channel in range(channels):
            head = middle[frame * channels + channel]
            tail = middle[(keep - join + frame) * channels + channel]
            body[frame * channels + channel] = int(head * share + tail * (1.0 - share))
    return body


def peaks_of(samples, channels, bars=PEAKS):
    """The waveform as `bars` peak levels from 0 to 1, for the page to draw."""
    frames = max(1, len(samples) // channels)
    step = max(1, frames // bars)
    found = []
    for start in range(0, frames, step):
        chunk = samples[start * channels:(start + step) * channels]
        found.append(round(max((level_of(value) for value in chunk), default=0.0), 3))
    top = max(found) or 1.0
    return [round(value / top, 3) for value in found[:bars]]


def prepare(source, folder, category, seconds=SHOT_SECONDS):
    """The safe takes of one fetched candidate in `folder`: a dict with the files the page plays ("preview"), the
    files the game would get ("takes"), their measures and the waveform; None when nothing safe came of it. A
    one-shot is kept up to `seconds` (what its brief asked for), and never past SHOT_SECONDS unless asked."""
    folder.mkdir(parents=True, exist_ok=True)
    channels = 2 if category == "room" else 1
    samples = trimmed(decode(source, channels), channels)
    if not samples:
        return None
    if category == "steps":
        return _prepare_steps(steps_in(samples), folder)
    shaped = looped(samples, channels) if category in ("loop", "room") else samples[:int(max(seconds, 1.0) * RATE) * channels]
    return _prepare_whole(shaped, channels, folder, category)


def _prepare_whole(samples, channels, folder, category):
    """One take, kept whole, under the loudness rule. A loop is kept as a WAV that tells Godot it loops (Vorbis would
    click at its join) with a FLAC of it for the page; a one-shot as Ogg Vorbis."""
    raw = write_wav(samples, folder / "raw.wav", channels)
    loops = category in ("loop", "room")
    name = "take.wav" if loops else "take.ogg"
    measure = loudness.normalise(raw, folder / name, loudness.TARGETS[TARGET[category]], fade_ms=0 if loops else 8)
    raw.unlink()
    if measure is None:
        return None
    made = {"preview": name, "takes": [name], "measures": {name: measure},
            "peaks": peaks_of(samples, channels), "seconds": round(len(samples) / channels / RATE, 2)}
    if loops:
        mark_as_loop(folder / name, channels)
        made["preview"] = loop_preview(folder / name, folder / "preview.ogg", channels)
        made["measures"]["preview.ogg"] = loudness.measure(folder / "preview.ogg")
        made["loop_pad"] = LOOP_PREVIEW_PAD_SECONDS
    return made


def loop_preview(take, out, channels):
    """A loop's preview for the page as Ogg Vorbis (the page cannot serve WAV this size or FLAC at all): the loop with
    a little of its end before it and a little of its start after it, so the smear Vorbis leaves at a file's edges
    falls outside the stretch the page loops (from LOOP_PREVIEW_PAD_SECONDS to that much before the end). The name
    of the file written."""
    samples = decode(take, channels)
    pad = int(LOOP_PREVIEW_PAD_SECONDS * RATE) * channels
    padded = samples[-pad:] + samples + samples[:pad]
    raw = write_wav(padded, out.with_suffix(".raw.wav"), channels)
    subprocess.run([loudness.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
                    *loudness.CODECS[".ogg"], str(out)], check=True)
    raw.unlink()
    return out.name


def mark_as_loop(path, channels):
    """Rewrites a 16-bit WAV with a `smpl` chunk marking the whole file as one forward loop, which Godot's importer
    reads ("Detect From WAV"), so the engine loops it itself with no gap. The end is written one past the last
    frame: Godot reads it as the frame it jumps back from (tools/sound/made.py does the same)."""
    samples = decode(path, channels)
    frames = len(samples) // channels
    fmt = _chunk(b"fmt ", struct.pack("<HHIIHH", 1, channels, RATE, RATE * 2 * channels, 2 * channels, 16))
    data = _chunk(b"data", samples.tobytes())
    header = struct.pack("<9I", 0, 0, round(1e9 / RATE), 60, 0, 0, 0, 1, 0)
    loop = _chunk(b"smpl", header + struct.pack("<6I", 0, 0, 0, frames, 0, 0))
    path.write_bytes(_chunk(b"RIFF", b"WAVE" + fmt + data + loop))


def _chunk(name, body):
    """One RIFF chunk: its name, its size and its body, padded to an even length."""
    return name + struct.pack("<I", len(body)) + body + (b"\0" if len(body) % 2 else b"")


def _prepare_steps(steps, folder):
    """Single steps under the loudness rule, and a walk of them for the page to play."""
    kept, measures, walk = [], {}, array.array("h")
    for index, step in enumerate(steps):
        raw = write_wav(step, folder / f"raw_{index}.wav")
        name = f"step_{len(kept) + 1}.ogg"
        measure = loudness.normalise(raw, folder / name, loudness.TARGETS["shot"])
        raw.unlink()
        if measure is None:
            continue
        kept.append(name)
        measures[name] = measure
        walk.extend(decode(folder / name))
        walk.extend(array.array("h", bytes(int(WALK_GAP_SECONDS * RATE) * 2)))
    if len(kept) < 2:
        return None
    raw_walk = write_wav(walk, folder / "walk.wav")
    walk_measure = loudness.normalise(raw_walk, folder / "walk.ogg", loudness.TARGETS["shot"])
    raw_walk.unlink()
    if walk_measure is None:
        return None
    measures["walk.ogg"] = walk_measure
    return {"preview": "walk.ogg", "takes": kept, "measures": measures, "peaks": peaks_of(walk, 1),
            "seconds": round(len(walk) / RATE, 2)}
