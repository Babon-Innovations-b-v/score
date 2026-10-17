"""The two closing clips of demo K9 (the world 1 video), made locally from the store with no cloud and no Blender:
`layers`, one place's accepted assembly (assembly@<place>) shown as its layer stack lifting off layer by layer, each
layer drawn from the prims it holds (top view, at their place in the composed stage), then every place's layer count;
and `ready`, what world 1 delivers for score_lib (not built yet), a card per count with its tiles, from a counts file
(a list of {label, count, how, tiles: [[source, caption], ...]}, counted from the store and repository).

    .venv/bin/python tools/review/ending.py layers <out.mp4> [--place garage]
    .venv/bin/python tools/review/ending.py ready <counts.json> <out.mp4>
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from showcase import FONT, RATE  # noqa: E402
import demo  # noqa: E402  (its encode)
sys.path.insert(0, str(REPO))
from score.store import PROPS_HOME, Store  # noqa: E402

W, H = 1280, 720
BACK = (17, 18, 21)
INK = (236, 236, 232)
DIM = (140, 142, 148)
CARD = (30, 32, 37)
# Each layer's colour and plain name; a layer not named here is drawn grey under its own file name.
LAYERS = {"ground": ((122, 104, 84), "ground (terrain)"), "base": ((150, 160, 172), "base: kit and props"),
          "settle": ((120, 170, 140), "settle (resting)"), "machines": ((210, 150, 90), "machines"),
          "crops": ((120, 190, 90), "crops"), "light": ((250, 214, 110), "light"),
          "motion": ((120, 170, 240), "motion"), "motion_keys": ((150, 130, 230), "motion keys"),
          "effects": ((240, 120, 110), "effects"), "sound": ((110, 210, 210), "sound"),
          "characters": ((235, 150, 200), "characters"), "edit": ((200, 200, 200), "edit (creator's changes)")}
FADE = 0.4
FLOOR = 640  # the bottom slab's middle on screen
CARD_FADE = 0.2  # a count card is on screen for 2 s


def write_frames(frames, seconds, out):
    """Frames (a function of the frame number giving an RGB picture) piped to ffmpeg as a silent 1280x720 clip."""
    count = round(seconds * RATE)
    process = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt",
                                "rgb24", "-s", f"{W}x{H}", "-r", str(RATE), "-i", "-", *demo.encode(out)[:-1],
                                str(out)], stdin=subprocess.PIPE)
    for number in range(count):
        process.stdin.write(np.asarray(frames(number, count), dtype=np.uint8).tobytes())
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on {out}")


def face(size):
    """The house font at `size` pixels."""
    return ImageFont.truetype(FONT, size)


def toward(colour, strength):
    """`colour` mixed with the background, `strength` of the way to full colour."""
    return tuple(round(BACK[index] + (colour[index] - BACK[index]) * strength) for index in range(3))


def layer_stack(stage_file):
    """The root layer's sublayers, bottom first (the stack as composed: the strongest is listed first)."""
    from pxr import Sdf
    root = Sdf.Layer.FindOrOpen(str(stage_file))
    return [pathlib.Path(path).stem for path in reversed(root.subLayerPaths)]


def layer_points(stage_file):
    """Per layer of the stack, bottom first, the (x, z) of every prim it specifies (a sample of a ground mesh's
    points), read from the composed stage, and the number of prims it specifies."""
    from pxr import Sdf, Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_file))
    cache = UsdGeom.XformCache()
    root = Sdf.Layer.FindOrOpen(str(stage_file))
    points, prims = {}, {}
    for path in reversed(root.subLayerPaths):
        name = pathlib.Path(path).stem
        layer = Sdf.Layer.FindOrOpen(root.ComputeAbsolutePath(path))
        found = []
        layer.Traverse(Sdf.Path.absoluteRootPath, lambda spec: found.append(spec) if spec.IsPrimPath() else None)
        coords = []
        for spec_path in found:
            prim = stage.GetPrimAtPath(spec_path)
            if prim and prim.IsA(UsdGeom.Mesh) and name == "ground":
                mesh_points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get() or [])
                world = cache.GetLocalToWorldTransform(prim)
                coords += [tuple(world.Transform(tuple(map(float, point))))[::2] for point in mesh_points[::40]]
            elif prim and prim.IsA(UsdGeom.Xformable):
                coords.append(tuple(cache.GetLocalToWorldTransform(prim).ExtractTranslation())[::2])
        points[name] = coords
        prims[name] = len(found)
    return points, prims


def projector(corners):
    """A function placing a stage (x, z) at a slab's level on screen, in an oblique view fitted to `corners`."""
    (low_x, low_z), (high_x, high_z) = corners
    middle_x, middle_z = (low_x + high_x) / 2, (low_z + high_z) / 2
    scale = 300 / max(high_x - low_x, high_z - low_z, 1e-3)

    def project(x, z, level):
        across, deep = (x - middle_x) * scale, (z - middle_z) * scale
        return 470 + (across - deep) * 0.82, FLOOR + (across + deep) * 0.24 - level

    return project


def draw_slab(draw, project, extent, points, colour, level, strength):
    """One layer: the place's outline plate and a dot per prim inside it, at `level` pixels up, `strength` of full
    colour."""
    (low_x, low_z), (high_x, high_z) = extent
    box = [(low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z)]
    draw.polygon([project(x, z, level) for x, z in box], outline=toward(colour, strength),
                 fill=toward(tuple(channel // 6 for channel in colour), strength))
    for x, z in points:
        if not (low_x <= x <= high_x and low_z <= z <= high_z):
            continue
        screen_x, screen_y = project(x, z, level)
        draw.ellipse((screen_x - 2.2, screen_y - 2.2, screen_x + 2.2, screen_y + 2.2), fill=toward(colour, strength))


def eased(value):
    """0..1 smoothed at both ends."""
    value = min(max(value, 0.0), 1.0)
    return value * value * (3 - 2 * value)


def stack_frames(place, stack, points, prims, seconds):
    """The exploded stack: every layer starts on the pile and lifts to its level in turn, labelled as it lifts."""
    everything = points.get("base") or [point for layer in stack for point in points[layer]]
    # the middle 96% of the base's prims: a place shown beside it (base's Places) would shrink the room to a dot
    low, high = np.percentile(np.asarray(everything), [2, 98], axis=0)
    extent = (tuple(low), tuple(high))
    project = projector(extent)
    gap = min(42, 400 / max(len(stack) - 1, 1))
    step = (seconds - 2.2) / len(stack)
    title, label, small = face(34), face(21), face(16)

    def frame(number, count):
        moment = number / RATE
        picture = Image.new("RGB", (W, H), BACK)
        draw = ImageDraw.Draw(picture)
        draw.text((60, 46), "Built in layers", font=title, fill=INK)
        draw.text((60, 92), f"{place}: the accepted assembly's own layer stack, {len(stack)} layers", font=small,
                  fill=DIM)
        for index, layer in enumerate(stack):
            lift = eased((moment - 0.6 - index * step) / (step * 0.9))
            colour, name = LAYERS.get(layer, ((170, 170, 170), layer))
            level = gap * index * lift
            draw_slab(draw, project, extent, points[layer], colour, level, 0.35 + 0.65 * max(lift, index == 0))
            if lift > 0:
                label_y = FLOOR - level
                draw.text((900, label_y - 12), name, font=label, fill=toward(colour, lift))
                draw.text((900, label_y + 12), f"layers/{layer}  {prims[layer]} prims", font=small,
                          fill=toward(DIM, lift))
        return faded(picture, moment, seconds)

    return frame


def faded(picture, moment, seconds, fade=FADE):
    """The picture faded in from and out to the background over `fade` seconds at the clip's ends."""
    strength = min(1.0, moment / fade, (seconds - moment) / fade)
    if strength >= 1:
        return picture
    return Image.blend(Image.new("RGB", (W, H), BACK), picture, max(strength, 0.0))


def place_counts(store):
    """Every place with an accepted assembly and its layer stack, from the store."""
    nodes = sorted(path.name for path in (PROPS_HOME / "store/objects/accepts").iterdir()
                   if path.name.startswith("assembly@"))
    counts = []
    for node in nodes:
        output = store.accepted(node)
        if output:
            place = node.split("@", 1)[1]
            counts.append((place, layer_stack(store.checkout(output) / f"{place}.usda")))
    return counts


def grid_frames(counts, seconds):
    """Every place's layer count as a grid of small cards, fading in row by row."""
    columns = 7
    rows = -(-len(counts) // columns)
    width, height = 160, min(118, 520 // rows)
    title, number_face, small = face(30), face(34), face(15)

    def frame(number, count):
        moment = number / RATE
        picture = Image.new("RGB", (W, H), BACK)
        draw = ImageDraw.Draw(picture)
        draw.text((60, 46), f"Every place, {len(counts)} assemblies: layers in each stack", font=title, fill=INK)
        for index, (place, stack) in enumerate(counts):
            row, column = divmod(index, columns)
            strength = eased((moment - 0.3 - row * 0.25) / 0.5)
            left, top = 60 + column * (width + 12), 120 + row * (height + 12)
            tone = toward(INK, strength)
            draw.rectangle((left, top, left + width, top + height), outline=toward(INK, strength / 3))
            draw.text((left + 12, top + 8), str(len(stack)), font=number_face, fill=tone)
            draw.text((left + 12, top + height - 26), place, font=small, fill=tone)
            for dot, layer in enumerate(stack):
                shade = toward(LAYERS.get(layer, ((170, 170, 170), layer))[0], strength)
                draw.rectangle((left + 70 + (dot % 6) * 13, top + 14 + (dot // 6) * 13,
                                left + 79 + (dot % 6) * 13, top + 23 + (dot // 6) * 13), fill=shade)
        return faded(picture, moment, seconds)

    return frame


def joined(parts):
    """Several (frames, seconds) parts as one frames function and its length."""
    total = sum(seconds for _, seconds in parts)

    def frame(number, count):
        moment = number / RATE
        for frames, seconds in parts:
            if moment < seconds:
                return frames(round(moment * RATE), round(seconds * RATE))
            moment -= seconds
        frames, seconds = parts[-1]
        return frames(round(seconds * RATE) - 1, round(seconds * RATE))

    return frame, total


def fitted(path, size):
    """A stored picture cropped to fill `size`."""
    picture = Image.open(path).convert("RGB")
    ratio = max(size[0] / picture.width, size[1] / picture.height)
    picture = picture.resize((round(picture.width * ratio), round(picture.height * ratio)))
    left, top = (picture.width - size[0]) // 2, (picture.height - size[1]) // 2
    return picture.crop((left, top, left + size[0], top + size[1]))


def stored(source):
    """A "store:<node>:<file>" source as the path of that file in the node's accepted output, checked out."""
    _, node, name = source.split(":", 2)
    store = Store.default()
    return str(store.checkout(store.accepted(node)) / name)


def tile(source, caption, size):
    """One example's tile: a stored picture or a sound's waveform ("store:<node>:<file>"), a library surface's swatch
    ("swatch:<family>/<variant>"), or, with no source, its name on a plain card."""
    if not source:
        return text_tile(caption, size)
    if source.startswith("swatch:"):
        return swatch_tile(source.split(":", 1)[1], caption, size)
    source = stored(source) if source.startswith("store:") else source
    if source.endswith((".ogg", ".wav")):
        return wave_tile(source, caption, size)
    return fitted(source, size)


def wave_tile(path, caption, size):
    """A sound's waveform, from its decoded samples, with its name."""
    samples = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f",
                                            "s16le", "-"], capture_output=True, check=True).stdout, dtype=np.int16)
    picture = Image.new("RGB", size, CARD)
    draw = ImageDraw.Draw(picture)
    loudness = np.abs(samples.astype(float))
    peak = max(1.0, float(loudness.max()))
    for index, column in enumerate(np.array_split(loudness, size[0] - 40)):
        height = (column.max() if len(column) else 0) / peak * size[1] * 0.3
        draw.line((20 + index, size[1] / 2 - height, 20 + index, size[1] / 2 + height), fill=(110, 210, 210))
    draw.text((20, size[1] - 44), caption, font=face(20), fill=INK)
    return picture


def swatch_tile(name, caption, size):
    """A library surface's swatch: its palette token's colour (design/tokens/tokens.json, the `ops` look) with its
    name and recipe."""
    family, variant = name.split("/")
    spec = json.loads((REPO / "data/library/materials.json").read_text())["families"][family]["variants"][variant]
    tokens = json.loads((REPO / "design/tokens/tokens.json").read_text())["color"]["tokens"]
    value = next(token["value"] for token in tokens if token["name"] == spec["token"])
    colour = (value["ops"] if isinstance(value, dict) else value).lstrip("#")
    picture = Image.new("RGB", size, tuple(int(colour[at:at + 2], 16) for at in (0, 2, 4)))
    draw = ImageDraw.Draw(picture)
    draw.rectangle((0, size[1] - 70, size[0], size[1]), fill=CARD)
    draw.text((16, size[1] - 60), caption, font=face(20), fill=INK)
    draw.text((16, size[1] - 32), f"{spec['recipe']}, token {spec['token']}", font=face(15), fill=DIM)
    return picture


def text_tile(caption, size):
    """A tile for an example with no stored picture (a motion, a gap): its name, written on a plain card."""
    picture = Image.new("RGB", size, CARD)
    ImageDraw.Draw(picture).multiline_text((24, 24), wrapped(caption, 18), font=face(26), fill=INK, spacing=8)
    return picture


def card_frames(entry, seconds):
    """One count: its number, its label, how it was counted and up to three of its tiles, faded in and out."""
    tiles = [(tile(source, caption, (254, 254)), source, caption) for source, caption in entry["tiles"][:3]]
    big, label, small = face(96), face(30), face(16)

    def frame(number, count):
        picture = Image.new("RGB", (W, H), BACK)
        draw = ImageDraw.Draw(picture)
        draw.text((60, 40), "Ready for score_lib", font=small, fill=DIM)
        draw.text((60, 120), str(entry["count"]), font=big, fill=INK)
        draw.text((60, 240), entry["label"], font=label, fill=INK)
        draw.multiline_text((60, 290), wrapped(entry["how"], 42), font=small, fill=DIM, spacing=6)
        for index, (shown, source, caption) in enumerate(tiles):
            left = 450 + index * 270
            picture.paste(shown, (left, 200))
            if source and not source.startswith("swatch:") and not source.endswith((".ogg", ".wav")):  # those carry it
                draw.text((left, 200 + shown.height + 10), caption[:30], font=small, fill=DIM)
        return faded(picture, number / RATE, seconds, CARD_FADE)

    return frame


def wrapped(text, width):
    """`text` broken into lines of at most about `width` characters."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return "\n".join([*lines, line])


def title_frames(heading, line, seconds):
    """A title card: a heading and one small line under it."""
    def frame(number, count):
        picture = Image.new("RGB", (W, H), BACK)
        draw = ImageDraw.Draw(picture)
        draw.text((W // 2, H // 2 - 20), heading, font=face(54), fill=INK, anchor="mm")
        draw.text((W // 2, H // 2 + 40), line, font=face(20), fill=DIM, anchor="mm")
        return faded(picture, number / RATE, seconds)

    return frame


def layers_clip(out, place):
    """The `layers` clip: the place's stack lifting off, then every place's layer count."""
    store = Store.default()
    stage = store.checkout(store.accepted(f"assembly@{place}")) / f"{place}.usda"
    stack, (points, prims) = layer_stack(stage), layer_points(stage)
    counts = place_counts(store)
    frames, seconds = joined([(stack_frames(place, stack, points, prims, 10.5), 10.5),
                              (grid_frames(counts, 4.5), 4.5)])
    write_frames(frames, seconds, out)
    return stack, counts


def ready_clip(counts_file, out):
    """The `ready` clip: a title, then one card of 2 s per count."""
    entries = json.loads(pathlib.Path(counts_file).read_text())
    parts = [(title_frames("Ready for score_lib", "what world 1 delivers, counted from the store", 2.0), 2.0),
             *[(card_frames(entry, 2.0), 2.0) for entry in entries]]
    frames, seconds = joined(parts)
    write_frames(frames, seconds, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    steps = parser.add_subparsers(dest="step", required=True)
    layers = steps.add_parser("layers")
    layers.add_argument("out", type=pathlib.Path)
    layers.add_argument("--place", default="garage")
    ready = steps.add_parser("ready")
    ready.add_argument("counts", type=pathlib.Path)
    ready.add_argument("out", type=pathlib.Path)
    arguments = parser.parse_args()
    if arguments.step == "layers":
        stack, counts = layers_clip(arguments.out, arguments.place)
        print(f"layers: {arguments.out} ({len(stack)} layers; {len(counts)} places)")
    else:
        ready_clip(arguments.counts, arguments.out)
        print(f"ready: {arguments.out}")


if __name__ == "__main__":
    main()
