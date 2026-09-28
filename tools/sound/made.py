"""The sounds the game makes itself (#35): no recording, so no licence, and anyone can remake them.

    bash tools/sound/run.sh                 # every sound, into game/sound/made/
    bash tools/sound/run.sh base_hum        # just these
    bash tools/sound/run.sh --out /tmp/x    # somewhere else, to listen before replacing

Plain Python, nothing installed, like tools/kit: the math is slow in pure Python but every sound
here is a few seconds long, so a full run takes well under a minute.

Every sound is built from a fixed seed, so a run writes the same bytes every time. A loop is made
to join itself with no click in three ways, one per kind of material in it:

- **A tone** has a whole number of cycles in the file, so its last sample runs into its first.
- **Noise** is filtered around the buffer as a ring: the filter runs over it twice and keeps the
  second pass, so its state at the end is the state the start was filtered with.
- **Anything with gaps** (ticks, beeps) is silent at the join, or wraps its tail to the start.

A loop also carries a WAV `smpl` chunk marking the whole file as the loop, which Godot's importer
reads ("Detect From WAV"), so the engine loops it itself instead of restarting it when it ends.

Quiet by default: each sound is written to a peak level below the warning's, and the warning tone
is the only one written near full scale. The catalogue sets the final level on top of that.
"""
import argparse
import math
import pathlib
import random
import struct
import sys

RATE = 44100
REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "game" / "sound" / "made"
SEED = 35  # the issue number; any fixed number would do


# --- building blocks -------------------------------------------------------------------------


def silence(seconds):
    """A buffer of silence this long."""
    return [0.0] * round(seconds * RATE)


def white_noise(length, generator):
    """Uniform white noise, `length` samples, from a seeded generator."""
    return [generator.uniform(-1.0, 1.0) for _ in range(length)]


def lowpass(signal, cutoff, ring=False):
    """A one-pole low-pass. With `ring`, the buffer is filtered as a loop that joins itself."""
    factor = 1.0 - math.exp(-2.0 * math.pi * cutoff / RATE)
    state = 0.0
    passes = 2 if ring else 1
    out = [0.0] * len(signal)
    for _ in range(passes):
        for index, sample in enumerate(signal):
            state += factor * (sample - state)
            out[index] = state
    return out


def band(signal, low, high, ring=False):
    """Keep the part of a signal between two frequencies (two gentle one-pole slopes each side)."""
    under_high = lowpass(lowpass(signal, high, ring), high, ring)
    under_low = lowpass(lowpass(under_high, low, ring), low, ring)
    return [upper - lower for upper, lower in zip(under_high, under_low)]


def tone(frequency, seconds, level=1.0, phase=0.0):
    """A sine wave. For a loop, pick a frequency with a whole number of cycles in `seconds`."""
    length = round(seconds * RATE)
    step = 2.0 * math.pi * frequency / RATE
    return [level * math.sin(phase + step * index) for index in range(length)]


def mix(*signals):
    """Sum signals of the same length."""
    return [sum(samples) for samples in zip(*signals)]


def scaled(signal, gain):
    """Every sample times a gain."""
    return [sample * gain for sample in signal]


def shaped(signal, envelope):
    """A signal times an envelope of the same length."""
    return [sample * weight for sample, weight in zip(signal, envelope)]


def attack_decay(length, attack, decay):
    """An envelope rising linearly for `attack` seconds, then falling off exponentially."""
    rise = max(1, round(attack * RATE))
    return [
        index / rise if index < rise else math.exp(-(index - rise) / (decay * RATE))
        for index in range(length)
    ]


def faded(signal, fade_in, fade_out):
    """Short raised-cosine ramps on each end, so a one-shot starts and stops without a click."""
    out = list(signal)
    for index in range(min(round(fade_in * RATE), len(out))):
        out[index] *= 0.5 - 0.5 * math.cos(math.pi * index / round(fade_in * RATE))
    count = min(round(fade_out * RATE), len(out))
    for index in range(count):
        out[-1 - index] *= 0.5 - 0.5 * math.cos(math.pi * index / count)
    return out


def placed(into, signal, start):
    """Add a signal into a buffer from sample `start`, wrapping past the end back to the start."""
    for index, sample in enumerate(signal):
        into[(start + index) % len(into)] += sample


def to_peak(signal, decibels):
    """The signal scaled so its loudest sample sits at this level below full scale."""
    loudest = max(abs(sample) for sample in signal) or 1.0
    return scaled(signal, 10.0 ** (decibels / 20.0) / loudest)



# --- the sounds ------------------------------------------------------------------------------


def base_hum(generator):
    """The habitat's life support: a low steady mains hum over the soft rush of air handlers."""
    seconds = 8.0
    length = round(seconds * RATE)
    hum = mix(
        tone(60.0, seconds, 1.0),
        tone(120.0, seconds, 0.45, 0.7),
        tone(180.0, seconds, 0.12, 1.9),
        tone(240.0, seconds, 0.05, 0.3),
    )
    swell = [1.0 + 0.08 * math.sin(2.0 * math.pi * 0.25 * index / RATE) for index in range(length)]
    air = scaled(lowpass(lowpass(white_noise(length, generator), 400.0, True), 400.0, True), 6.0)
    return to_peak(mix(shaped(hum, swell), air), -12.0), True





def radio_squelch(generator):
    """A short burst of radio static: narrow-band hiss with crackle, cut off by the squelch."""
    seconds = 0.4
    length = round(seconds * RATE)
    hiss = band(white_noise(length, generator), 350.0, 2800.0)
    crackle = [generator.uniform(-1.0, 1.0) if generator.random() < 0.004 else 0.0 for _ in range(length)]
    crackle = band(crackle, 1000.0, 5000.0)
    grain = [0.7 + 0.3 * math.sin(2.0 * math.pi * 23.0 * index / RATE) for index in range(length)]
    body = mix(shaped(hiss, grain), scaled(crackle, 8.0))
    return to_peak(faded(body, 0.004, 0.05), -10.0), False






def warning_tone(generator):
    """The warning: two soft bell tones stepping down a fourth. The loudest sound, never shrill."""
    del generator  # nothing random in it
    length = round(1.6 * RATE)

    def note(frequency):
        partials = mix(tone(frequency, 0.9), tone(frequency * 2.0, 0.9, 0.18), tone(frequency * 3.0, 0.9, 0.05))
        return shaped(partials, attack_decay(len(partials), 0.012, 0.28))

    out = [0.0] * length
    placed(out, note(587.33), 0)
    placed(out, note(440.0), round(0.45 * RATE))
    return to_peak(faded(out, 0.001, 0.1), -1.0), False


def geiger_ticks(generator):
    """A counter in a solar storm: dry ticks at random, sometimes bunched, about seven a second."""
    seconds = 8.0
    out = silence(seconds)
    time = 0.0
    while True:
        time += generator.expovariate(7.0)
        if time >= seconds:
            break
        length = round(0.006 * RATE)
        ring = tone(generator.uniform(2600.0, 3400.0), 0.006, phase=generator.uniform(0.0, 6.28))
        snap = [generator.uniform(-1.0, 1.0) for _ in range(length)]
        tick = shaped(mix(ring, snap), attack_decay(length, 0.0001, 0.0009))
        placed(out, scaled(tick, generator.uniform(0.6, 1.0)), round(time * RATE))
    return to_peak(out, -6.0), True


def oxygen_low(generator):
    """Low oxygen: two short soft beeps, then quiet, so it can be played again and again."""
    del generator  # nothing random in it
    beep = faded(mix(tone(880.0, 0.13), tone(1760.0, 0.13, 0.1)), 0.008, 0.02)
    out = silence(1.0)
    placed(out, beep, 0)
    placed(out, beep, round(0.2 * RATE))
    return to_peak(out, -5.0), False


SOUNDS = {
    "base_hum": base_hum,
    "radio_squelch": radio_squelch,
    "warning_tone": warning_tone,
    "geiger_ticks": geiger_ticks,
    "oxygen_low": oxygen_low,
}


# --- writing ---------------------------------------------------------------------------------


def pcm16(signal):
    """Samples in -1..1 as little-endian 16-bit PCM bytes."""
    return b"".join(struct.pack("<h", max(-32767, min(32767, round(sample * 32767)))) for sample in signal)


def chunk(name, body):
    """One RIFF chunk: its four-letter name, its size and its body, padded to an even length."""
    return name + struct.pack("<I", len(body)) + body + (b"\0" if len(body) % 2 else b"")


def loop_chunk(length):
    """A `smpl` chunk marking the whole file as one forward loop.

    The end is written one past the last sample: Godot reads it as the sample it jumps back from,
    so this gives a loop exactly as long as the file (the spec's last-sample-inclusive end would
    drop one sample at every pass).
    """
    period = round(1e9 / RATE)
    header = struct.pack("<9I", 0, 0, period, 60, 0, 0, 0, 1, 0)
    loop = struct.pack("<6I", 0, 0, 0, length, 0, 0)
    return chunk(b"smpl", header + loop)


def wav_bytes(signal, loops):
    """A mono 16-bit 44.1 kHz WAV file, with a loop marker when it loops."""
    fmt = chunk(b"fmt ", struct.pack("<HHIIHH", 1, 1, RATE, RATE * 2, 2, 16))
    data = chunk(b"data", pcm16(signal))
    body = b"WAVE" + fmt + data + (loop_chunk(len(signal)) if loops else b"")
    return chunk(b"RIFF", body)


def made(sound_name):
    """Render one sound from its own seed, so each is the same whichever others are made."""
    generator = random.Random(f"{SEED}:{sound_name}")
    return SOUNDS[sound_name](generator)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", help="which sounds; all when none are named")
    parser.add_argument("--out", type=pathlib.Path, default=OUT, help="where to write them")
    arguments = parser.parse_args()
    unknown = [sound_name for sound_name in arguments.names if sound_name not in SOUNDS]
    if unknown:
        sys.exit(f"no such sound: {', '.join(unknown)} (there are: {', '.join(SOUNDS)})")
    arguments.out.mkdir(parents=True, exist_ok=True)
    for sound_name in arguments.names or SOUNDS:
        signal, loops = made(sound_name)
        target = arguments.out / f"{sound_name}.wav"
        target.write_bytes(wav_bytes(signal, loops))
        print(f"{target}  {len(signal) / RATE:.2f} s{'  loop' if loops else ''}")


if __name__ == "__main__":
    main()
