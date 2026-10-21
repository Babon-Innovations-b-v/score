"""The environment film's words, in the cockpit's one typeface and colours (design/fonts/poppins,
design/tokens/colours.css), drawn as the free preview draws them so the final reads as the preview did: a title or
text card's frames on its clock (the FILM page's card, film.js drawWords: the title rising in as its letters close
up, a rule drawn out under it, the line after, all closing in slowly and fading before the card ends) and a lower
third over a place's film (recorder.mjs's caption: a small line over the words on a dark box with an accent edge).
Sizes are the preview's at 1280 x 720, scaled to the picture."""
import math
import pathlib
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parents[3]
FONTS = REPO / "design/fonts/poppins"
COLOURS = REPO / "design/tokens/colours.css"
# The type and colours the cut reads, as the environment-film row's declared files.
FILES = {"type colours": "{repo}/design/tokens/colours.css",
         **{f"type poppins {weight}": "{repo}/design/fonts/poppins/" + f"poppins-{weight}-latin.woff2"
            for weight in (400, 600)}}
PREVIEW_TALL = 720


def token(name):
    """A colour token of colours.css as (red, green, blue, alpha 0 to 255)."""
    found = re.search(rf"--{name}:\s*([^;]+);", COLOURS.read_text())
    if not found:
        raise ValueError(f"no colour token --{name} in {COLOURS}")
    value = found.group(1).strip()
    if value.startswith("#"):
        return (*(int(value[index:index + 2], 16) for index in (1, 3, 5)), 255)
    red, green, blue, alpha = (float(part) for part in re.findall(r"[\d.]+", value))
    return int(red), int(green), int(blue), round(alpha * 255)


def face(weight, pixels):
    return ImageFont.truetype(str(FONTS / f"poppins-{weight}-latin.woff2"), max(1, round(pixels)))


def eased(share):
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, share)))


def card_ground(size):
    """The card's ground: one flat title colour, no spotlight (owner 2026-10-21; film.css .film-words)."""
    return Image.new("RGB", size, tuple(int(part) for part in token("film-title-to")[:3]))

def spaced(draw, middle, top, words, font, tracking, fill):
    """`words` centred on `middle` with `tracking` pixels between letters; its height."""
    widths = [draw.textlength(letter, font=font) for letter in words]
    left = middle - (sum(widths) + tracking * (len(words) - 1)) / 2
    for letter, width in zip(words, widths):
        draw.text((left, top), letter, font=font, fill=fill)
        left += width + tracking
    return font.getbbox(words or " ")[3]


def card_frame(ground, title, line, local, seconds):
    """One frame of a title or text card at `local` seconds of its `seconds` on `ground`, an RGB picture."""
    wide, tall = ground.size
    scale = tall / PREVIEW_TALL
    words = Image.new("RGBA", ground.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(words)
    out, rising = eased((seconds - local) / 0.6), eased((local - 0.15) / 0.8)
    big, small = face(600, 60 * scale), face(400, 26 * scale)
    gap, rule_wide = 14 * scale, 84 * scale
    title_tall = big.getbbox(title or " ")[3]
    line_tall = small.getbbox(line)[3] if line else 0
    top = (tall - title_tall - 2 * gap - 2 * scale - line_tall) / 2 + (1 - rising) * 14 * scale
    ink = token("film-ink")
    spaced(draw, wide / 2, top, title, big, (0.09 - 0.1 * eased(local / 1.8)) * 60 * scale,
           (*ink[:3], round(255 * min(rising, out))))
    rule_top = top + title_tall + gap
    drawn = rule_wide * eased((local - 0.55) / 0.8) / 2
    if drawn > 0.5:
        draw.rectangle((wide / 2 - drawn, rule_top, wide / 2 + drawn, rule_top + 2 * scale),
                       fill=(*token("color-accent")[:3], round(255 * out)))
    if line:
        shown = eased((local - 0.8) / 0.7)
        draw.text((wide / 2, rule_top + 2 * scale + gap + (1 - shown) * 10 * scale), line, font=small, anchor="ma",
                  fill=(*token("film-card-words")[:3], round(255 * min(shown, out))))
    grow = 1 + 0.025 * local / seconds
    grown = words.resize((round(wide * grow), round(tall * grow)), Image.BICUBIC)
    left, upper = (grown.width - wide) // 2, (grown.height - tall) // 2
    return Image.alpha_composite(ground.convert("RGBA"), grown.crop((left, upper, left + wide, upper + tall)))


def wrapped(draw, words, font, most):
    """`words` broken into lines no wider than `most` pixels."""
    lines, current = [], ""
    for word in words.split():
        trial = f"{current} {word}".strip()
        if current and draw.textlength(trial, font=font) > most:
            lines.append(current)
            current = word
        else:
            current = trial
    return lines + ([current] if current else [])


def lower_third(size, small, words):
    """A lower third over a film, an RGBA picture of `size`: `small` (upper case, the accent) over `words` on a dark
    box with an accent edge, low on the left."""
    wide, tall = size
    scale = tall / PREVIEW_TALL
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    eyebrow, text = face(600, 13 * scale), face(600, 25 * scale)
    pad, edge = (22 * scale, 14 * scale), 4 * scale
    lines = wrapped(draw, words, text, wide * 0.62 - 2 * pad[0])
    small = small.upper()
    tracking = 0.14 * 13 * scale
    small_wide = sum(draw.textlength(letter, font=eyebrow) + tracking for letter in small) if small else 0.0
    small_tall = (eyebrow.getbbox(small)[3] + 4 * scale) if small else 0.0
    step = 25 * scale * 1.25
    box_wide = max([small_wide, *(draw.textlength(line, font=text) for line in lines)]) + 2 * pad[0] + edge
    box_tall = small_tall + step * len(lines) + 2 * pad[1]
    left, bottom = 48 * scale, tall - 44 * scale
    draw.rounded_rectangle((left, bottom - box_tall, left + box_wide, bottom), radius=10 * scale,
                           fill=(10, 11, 16, 209))
    draw.rounded_rectangle((left, bottom - box_tall, left + edge * 2, bottom), radius=edge,
                           fill=token("color-accent"))
    draw.rectangle((left + edge, bottom - box_tall, left + edge * 2, bottom), fill=(10, 11, 16, 209))
    x, y = left + edge + pad[0], bottom - box_tall + pad[1]
    for letter in small:
        draw.text((x, y), letter, font=eyebrow, fill=token("color-accent"))
        x += draw.textlength(letter, font=eyebrow) + tracking
    y += small_tall
    for line in lines:
        draw.text((left + edge + pad[0], y), line, font=text, fill=token("film-caption"))
        y += step
    return layer
