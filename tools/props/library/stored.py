"""How a kit room's baked pictures are kept in the repo, and what a room may cost (modules batch one, 2026-10-07).

    python=~/.farm-factory-props/env/bin/python
    $python tools/props/library/stored.py store game/base/models/hub_kit    # its pictures stored compressed
    $python tools/props/library/stored.py budget game/base/models/hub_kit   # what it costs on disk and on the card

Hub round four put 487 MB of models on disk (414 MB of it PNG pictures, 323 MB of that the normal maps), and the
repo is public: seven more rooms at that rate would be about 4 GB in git. The game never draws the stored file: Godot
imports every picture to BC7 on the card (route.py `picture_imports`), so how it is stored only has to give Godot the
same picture to compress. So a room's pictures are stored as WebP, each the way that keeps what the game draws:

- colour (`_base_color`): lossy, quality COLOUR_QUALITY: about 7 times smaller than PNG, a mean error of about one
  level in 255 (measured on the hub's comms desk and a floor set), far under what BC7 itself takes off;
- metal and roughness (`_metal_roughness`): lossless. Lossy WebP keeps colour at quarter resolution, which smears the
  metal (blue) and roughness (green) channels into each other at every region's edge (errors past 200 levels);
- normal maps (`_normal`): lossless over red and green rounded to NORMAL_STEP, the blue channel set full. The game's
  shader rebuilds a normal's blue from its red and green and never reads the stored one (Godot's scene shader:
  "always ignore Z"), and the import compresses a normal map from red and green alone; rounding to every second level
  is under one level of error and stores at about half a PNG.

A glTF points at its WebP pictures through EXT_texture_webp (Godot's importer reads it), and each picture's import
settings are carried over from its PNG's, so Godot compresses it the same way.

The budget per room (BUDGET) is what a room may cost, from the hub's measurements (round four: 608 MB of pictures on
the card as BC7, 412 MB of PNG on disk; 173 MB once stored this way, see the bible's build/performance): a room past
either number stops the install, loudly, rather than land in the repo.
"""
import json
import pathlib
import re
import sys
from concurrent.futures import ProcessPoolExecutor


COLOUR_QUALITY = 90
NORMAL_STEP = 2
# What one room's made models may cost: on disk in the repo (pictures and meshes) and the pictures' share of the
# card's memory as the game imports them (BC7, one byte a texel, a third more with mipmaps). From the hub, the biggest
# room so far: 245 MB stored (173 MB of it pictures, 73 MB meshes), 608 MB on the card.
BUDGET = {"disk_mb": 250, "card_mb": 640}
WORKERS = 6
KINDS = ("_base_color", "_metal_roughness", "_normal")


def kind_of(name):
    """Which map a baked picture is, by its name's end: `_base_color`, `_metal_roughness` or `_normal`; None else."""
    stem = pathlib.Path(name).stem
    return next((kind for kind in KINDS if stem.endswith(kind)), None)


def stored_picture(png):
    """A baked PNG written beside itself as WebP, the way its kind keeps what the game draws; the WebP's path."""
    import numpy as np
    from PIL import Image
    kind = kind_of(png.name)
    target = png.with_suffix(".webp")
    with Image.open(png) as opened:
        picture = opened.convert("RGB")
    if kind == "_base_color":
        picture.save(target, "WEBP", quality=COLOUR_QUALITY, method=6)
    elif kind == "_normal":
        values = np.asarray(picture).astype(np.int32)
        values[..., :2] = np.clip((values[..., :2] + NORMAL_STEP // 2) // NORMAL_STEP * NORMAL_STEP, 0, 255)
        values[..., 2] = 255
        Image.fromarray(values.astype(np.uint8)).save(target, "WEBP", lossless=True, quality=100, method=6)
    else:
        picture.save(target, "WEBP", lossless=True, quality=100, method=6)
    return target


def pointed_at_webp(gltf):
    """A glTF's pictures pointed at their WebP copies (EXT_texture_webp); how many it changed."""
    found = json.loads(gltf.read_text())
    changed = 0
    for image in found.get("images", []):
        uri = image.get("uri", "")
        if uri.endswith(".png") and kind_of(uri):
            image["uri"] = uri[:-4] + ".webp"
            image["mimeType"] = "image/webp"
            changed += 1
    if not changed:
        return 0
    webp = {index for index, image in enumerate(found["images"]) if image.get("mimeType") == "image/webp"}
    for texture in found.get("textures", []):
        source = texture.get("source", texture.get("extensions", {}).get("EXT_texture_webp", {}).get("source"))
        if source in webp:
            texture.pop("source", None)
            texture.setdefault("extensions", {})["EXT_texture_webp"] = {"source": source}
    for key in ("extensionsUsed", "extensionsRequired"):
        found[key] = sorted(set(found.get(key, [])) | {"EXT_texture_webp"})
    gltf.write_text(json.dumps(found, indent=1))
    return changed


def carried_import(png, webp):
    """The PNG's Godot import settings carried over to its WebP (same compression, normal-map flag, uid), so it is
    imported the same way; the remap Godot writes again on import."""
    settings = png.with_name(png.name + ".import")
    if not settings.exists():
        return
    text = settings.read_text().replace(png.name, webp.name)
    text = re.sub(r"\.png-[0-9a-f]{32}\.", ".webp-0.", text)
    webp.with_name(webp.name + ".import").write_text(text)
    settings.unlink()


def store(folder):
    """Every baked PNG of a room's models folder stored as WebP and every glTF pointed at it; the PNGs removed."""
    folder = pathlib.Path(folder)
    pictures = sorted(path for path in (folder / "textures").glob("*.png") if kind_of(path.name))
    # WebP's slowest, smallest setting takes about a minute a 4096 normal map: a few at once.
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        written = list(pool.map(stored_picture, pictures))
    for png, webp in zip(pictures, written):
        carried_import(png, webp)
        png.unlink()
    pointed = sum(pointed_at_webp(gltf) for gltf in sorted(folder.glob("*.gltf")))
    return len(pictures), pointed


def cost(folder):
    """What a room's models folder costs: {"disk_mb": pictures and meshes in the repo, "card_mb": its pictures on the
    card as imported (BC7)}."""
    from PIL import Image
    folder = pathlib.Path(folder)
    disk = card = 0.0
    for path in folder.rglob("*"):
        if path.suffix in (".png", ".webp", ".bin", ".gltf"):
            disk += path.stat().st_size
        if path.suffix in (".png", ".webp"):
            with Image.open(path) as opened:
                wide, tall = opened.size
            settings = path.with_name(path.name + ".import")
            mipmaps = settings.exists() and "mipmaps/generate=true" in settings.read_text()
            card += wide * tall * (4 / 3 if mipmaps else 1)
    return {"disk_mb": round(disk / 2 ** 20, 1), "card_mb": round(card / 2 ** 20, 1)}


def over_budget(found):
    """The budget lines a room's cost goes past, as words; empty when it is within."""
    return [f"{key} {found[key]} > {limit}" for key, limit in BUDGET.items() if found[key] > limit]


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("store", "budget"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "store":
        pictures, pointed = store(sys.argv[2])
        print(pictures, "pictures stored as WebP;", pointed, "glTF pictures pointed at them")
    found = cost(sys.argv[2])
    past = over_budget(found)
    print(found, "budget", BUDGET, "OVER: " + "; ".join(past) if past else "within")
    if past:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
