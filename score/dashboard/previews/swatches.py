"""Swatches of the surfaces an output names: each surface's colour from the material library (its variant's palette
token) and its roughness, drawn as a lit ball with its name under it, the parts it is for when the output says so.
A surface the library does not hold is drawn grey and named so."""
import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BALL = 120
LABEL = 34
COLUMNS = 5
MOST = 20
BACKGROUND = np.array([238, 236, 230]) / 255.0
INK = (29, 32, 38)
UNKNOWN = (150, 150, 150)
LIGHT = np.array([-0.45, 0.6, 0.66]) / np.linalg.norm([-0.45, 0.6, 0.66])


def token_colours(tokens_file):
    """{token name: (r, g, b)} of the design tokens' colours (a themed token's own value)."""
    found = {}
    for entry in json.loads(pathlib.Path(tokens_file).read_text())["color"]["tokens"]:
        value = entry["value"]["ops"] if isinstance(entry["value"], dict) else entry["value"]
        found[entry["name"]] = tuple(int(value.lstrip("#")[at:at + 2], 16) for at in (0, 2, 4))
    return found


def library(materials_file, tokens_file):
    """{surface name: (rgb, roughness, metallic)} of every variant in the material library; empty for a world
    with no library."""
    if not (pathlib.Path(materials_file).is_file() and pathlib.Path(tokens_file).is_file()):
        return {}
    colours = token_colours(tokens_file)
    found = {}
    for family in json.loads(pathlib.Path(materials_file).read_text())["families"].values():
        for name, variant in (family.get("variants") or {}).items():
            rgb = colours.get(variant.get("token"), UNKNOWN)
            found[name] = (rgb, float(variant.get("roughness", 0.5)), 0.8 if "metal" in variant.get("recipe", "") else 0.0)
    return found


def named_surfaces(documents):
    """[(surface, parts)] each surface once, in the order the documents name them: a `finishes` list's entries
    (surface, and the parts it is for), or a list of plain names under `surfaces`."""
    found = {}
    for document in documents:
        for finish in document.get("finishes") or []:
            if isinstance(finish, dict) and finish.get("surface"):
                found.setdefault(finish["surface"], finish.get("parts") or finish.get("finish") or "")
        for name in document.get("surfaces") or []:
            if isinstance(name, str):
                found.setdefault(name, "")
    return list(found.items())


def ball(rgb, roughness, metallic):
    """An RGB array of a lit ball of the surface's colour on the background."""
    across = np.linspace(-1.1, 1.1, BALL)
    x, y = np.meshgrid(across, -across)
    inside = x ** 2 + y ** 2 <= 1.0
    normals = np.stack([x, y, np.sqrt(np.clip(1.0 - x ** 2 - y ** 2, 0, None))], axis=-1)
    diffuse = np.clip(normals @ LIGHT, 0, None)[..., None]
    halfway = (LIGHT + np.array([0, 0, 1.0])) / np.linalg.norm(LIGHT + np.array([0, 0, 1.0]))
    specular = (np.clip(normals @ halfway, 0, None) ** (2.0 / max(roughness, 0.03) ** 2))[..., None]
    base = np.array(rgb, dtype=float) / 255.0
    highlight = (1 - metallic) * np.ones(3) + metallic * base
    shaded = base * (0.18 + 0.82 * diffuse) * (1 - 0.6 * metallic) + 0.5 * specular * highlight
    return (np.where(inside[..., None], np.clip(shaded, 0, 1), BACKGROUND) * 255).astype(np.uint8)


def picture(surfaces, known, destination):
    """A grid of the named surfaces' swatches, each labelled; the path."""
    shown = surfaces[:MOST]
    rows = max(1, -(-len(shown) // COLUMNS))
    sheet = Image.new("RGB", (COLUMNS * BALL, rows * (BALL + LABEL)), tuple(int(v * 255) for v in BACKGROUND))
    pen = ImageDraw.Draw(sheet)
    small = ImageFont.load_default(size=11)
    for number, (name, parts) in enumerate(shown):
        left, top = (number % COLUMNS) * BALL, (number // COLUMNS) * (BALL + LABEL)
        rgb, roughness, metallic = known.get(name, (UNKNOWN, 0.6, 0.0))
        sheet.paste(Image.fromarray(ball(rgb, roughness, metallic)), (left, top))
        pen.text((left + 4, top + BALL), name[:19] + ("" if name in known else " ?"), fill=INK, font=small)
        pen.text((left + 4, top + BALL + 14), str(parts)[:19], fill=(110, 110, 110), font=small)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG")
    return destination
