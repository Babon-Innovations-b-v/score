"""The two pictures of what has no place on a map: the waveforms of an output's sound files (the .wav ones, read
with the standard library), and, for any other output, a tile per thing it names, so a card is never empty."""
import pathlib
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WIDTH = 480
STRIP = 44
MOST_SOUNDS = 8
TILE = (156, 44)
COLUMNS = 3
MOST_TILES = 24
BACKGROUND = (238, 236, 230)
INK = (40, 52, 64)
MIDDLE = (190, 186, 178)
TILE_COLOURS = ((76, 106, 138), (180, 88, 58), (111, 143, 78), (138, 111, 158), (199, 154, 59), (63, 143, 138))


def samples(path):
    """A .wav file's samples, channels averaged, scaled to its peak; empty when it cannot be read."""
    try:
        with wave.open(str(path), "rb") as sound:
            width, channels = sound.getsampwidth(), sound.getnchannels()
            raw = sound.readframes(sound.getnframes())
    except (wave.Error, EOFError):
        return np.zeros(0)
    kinds = {1: np.uint8, 2: np.int16, 4: np.int32}
    if width not in kinds:
        return np.zeros(0)
    signal = np.frombuffer(raw, dtype=kinds[width]).astype(float).reshape(-1, channels).mean(axis=1)
    peak = float(np.abs(signal).max()) if len(signal) else 0.0
    return signal / peak if peak > 0 else signal


def waveforms(files, destination):
    """A strip per .wav sound, named; the path, or None when no .wav could be read."""
    sounds = [(name, samples(path)) for name, path in files if name.lower().endswith(".wav")][:MOST_SOUNDS]
    sounds = [(name, signal) for name, signal in sounds if len(signal)]
    if not sounds:
        return None
    sheet = Image.new("RGB", (WIDTH, STRIP * len(sounds)), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=10)
    for number, (name, signal) in enumerate(sounds):
        top, half = number * STRIP, STRIP / 2
        edges = np.linspace(0, len(signal), WIDTH + 1).astype(int)
        pen.line([(0, top + half), (WIDTH, top + half)], fill=MIDDLE)
        for column, (start, end) in enumerate(zip(edges[:-1], edges[1:])):
            chunk = signal[start:max(end, start + 1)]
            pen.line([(column, top + half - chunk.max() * (half - 4)), (column, top + half - chunk.min() * (half - 4))],
                     fill=INK)
        pen.text((4, top + 2), pathlib.PurePosixPath(name).stem[:40], fill=INK, font=small)
    return save(sheet, destination)


def tiles(names, words, destination):
    """A coloured tile per name the output holds, under a line saying what it is; the path."""
    shown = names[:MOST_TILES]
    rows = max(1, -(-len(shown) // COLUMNS))
    sheet = Image.new("RGB", (COLUMNS * TILE[0], 22 + rows * TILE[1]), BACKGROUND)
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=11)
    pen.text((6, 4), f"{words}: {len(names)}" + (f" (first {MOST_TILES})" if len(names) > MOST_TILES else ""),
             fill=INK, font=small)
    for number, name in enumerate(shown):
        left, top = (number % COLUMNS) * TILE[0], 22 + (number // COLUMNS) * TILE[1]
        pen.rounded_rectangle([left + 3, top + 3, left + TILE[0] - 3, top + TILE[1] - 3], radius=6,
                              fill=TILE_COLOURS[number % len(TILE_COLOURS)])
        pen.text((left + 9, top + 14), str(name)[:22], fill=(250, 250, 248), font=small)
    return save(sheet, destination)


def save(sheet, destination):
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
