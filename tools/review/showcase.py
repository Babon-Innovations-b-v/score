"""The showcase video of SCORE (world 1): the framework's story on one reviewed place (the wreck), from its real stage
outputs, then every place of world 1 in story order from its film (tools/review/demo.py), then the repository; and
the candidate figure of the paper, one frame of each film. Cut here with ffmpeg; every picture and sound comes from a
stage, a review page or a film made on the cloud.

    .venv/bin/python tools/review/showcase.py cut <films out> --page <the wreck's review page> \
        --stage <the wreck's stage .usda> --concept <the concept picked>
    .venv/bin/python tools/review/showcase.py figure <films out> <figure .jpg>
    .venv/bin/python tools/review/showcase.py world <out> [<figure .jpg>] [--draft]

`cut` reads the films (<out>/videos/<film>.mp4 and their views) and the stills rendered for it on the cloud from the
job files kept beside them (<out>/showcase/jobs/: the aft section's turntables by ../blender/inside/review_models.py
into <out>/showcase/models/out, and the stage before an edit, after it and after the base was written again by
../blender/inside/usd_views.py into <out>/showcase/edit/out/<take>/, each with its ink lines); it writes
<out>/showcase/showcase.mp4 and each part as made in <out>/showcase/parts/. The numbers on its cards are measured
here: the inventory's rows (data/inventory/wreck.json), each surface's share of the aft section's parts by area, and
the completion gate's own results (the stage's manifest.json). `figure` writes the figure and its frame list beside
it (<figure>.json): the middle frame, with its ink, of each film's first walking shot (else its second).

`world` is the world 1 video (demo K9): the world's title, then the framework's chain shown once on one hero place
(references and style, concept, plan, pieces: one card each with a large title, a progress bar of the chain and at most
CHAIN_MOST cards, each held STEP_SECONDS and pushed in over the one before; then the hero's own film as the chain's last
step, the place), then every other place's own film as the runner accepted it (demo-film@<place>, PLACE_MOST at most
from its title card's end, with its sound and caption) in story order, the ship's hull film through the hangar
(demo-film-extra@hangar, its hull/) after the hangar's, then the ending's clips, joined by cross-fades into
<out>/world1.mp4. The cards and the ending stand on a bed of the nearest film's own sound, so the sound never drops.
With it the figure of the middle frame of each film's shot (default <out>/fig-k9.jpg) and <out>/world1.json, each
film's store output. It stops on any film the store does not hold; `--draft` cuts the ones it holds and names the rest.
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import demo  # noqa: E402  (its joined, encode, inked and SIZE; puts tools/usd on the path)
import hearing  # noqa: E402  (tools/usd)
import sound  # noqa: E402  (tools/usd)
sys.path.insert(0, str(REPO / "tools/props"))
from paths import WORK  # noqa: E402
sys.path.insert(0, str(REPO))
from score.stages import demo_film  # noqa: E402
from score.store import Store  # noqa: E402

W, H = demo.SIZE
RATE = demo.RATE
FONT = "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf"
REPO_LINK = "github.com/Babon-Innovations-b-v/score"
FADE = demo.FADE_SECONDS
DIM = 0.55
# The edit's takes, in the order shown, and the one camera they are drawn from (its views.json name).
TAKES = ("wreck-base", "wreck-edited", "wreck-regenerated")
EDIT_VIEW = "edit"
# The figure: its tiles' size, how many a row, and its labels' font.
TILE = (640, 360)
COLUMNS = 4
LABEL_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Story order (the handoff's), each film's caption (the part of the world, then the place) and its label in the figure.
PLACES = [("flat", "Prologue, Hong Kong 2099", "The flat", "Flat"),
          ("stairwell", "Prologue", "The stairwell", "Stairwell"), ("street", "Prologue", "The street", "Street"),
          ("square", "Prologue", "The square", "Square"), ("launch", "Prologue", "The launch view", "Launch view"),
          ("hub", "The Moon base", "The hub", "Hub"), ("lab", "The Moon base", "The lab", "Lab"),
          ("greenhouse", "The Moon base", "The greenhouse", "Greenhouse"),
          ("workshop", "The Moon base", "The workshop", "Workshop"),
          ("habitat", "The Moon base", "The habitat", "Habitat"),
          ("airlock", "The Moon base", "The airlock", "Airlock"),
          ("tube", "The Moon base", "The walkway tube", "Walkway tube"),
          ("garage", "The Moon base", "The garage", "Garage"), ("hangar", "The Moon base", "The hangar", "Hangar"),
          ("wreck", "The Moon", "The wreck", "Wreck"), ("old_station", "The Moon", "The old station", "Old station"),
          ("shiplock", "The ship", "The ship's lock", "Ship's lock"), ("walkway", "The ship", "The walkway", "Walkway"),
          ("cockpit", "The ship", "The cockpit", "Cockpit"),
          ("galley", "The ship", "The galley", "Galley"), ("quarters", "The ship", "The quarters", "Quarters"),
          ("storage", "The ship", "The storage room", "Storage"),
          ("engineroom", "The ship", "The engine room", "Engine room"),
          ("camp", "Mars", "The camp", "Mars camp"), ("campgrounds", "Mars", "The camp grounds", "Mars camp grounds")]
PLACE_SECONDS = 5.5
# The world video's other films, each after its place's own (the paper's K9: every place film and the ship).
EXTRAS = {"hangar": [("hull", "The ship")]}
# The world video (the owner's cut of 18 Oct, at most WORLD_MOST): the finished places get most of the time, and the
# framework's chain is shown once, on one hero place. The chain's steps in order, the last one the hero's own film; each
# step's pictures held STEP_SECONDS on a card (one picture large, several side by side), at most CHAIN_MOST cards, each
# pushed in over MOVE_SECONDS; the opening's title OPENING_SECONDS; each place's film from its title card's end, at most
# PLACE_MOST of it; under the cards and the ending a bed of the nearest film's own sound, looped with BED_SEAM
# cross-fades, so the sound never drops between parts.
CHAIN = ("References and style", "Concept", "Plan", "Pieces", "Place")
STEP_SECONDS = 6.0
MOVE_SECONDS = 0.9
CHAIN_MOST = 8
OPENING_SECONDS = 4.5
PLACE_MOST = 7.0
WORLD_MOST = 240.0
BED_SEAM = 1.0
BED_RISE = 1.5
BED_FALL = 4.0
# A card's layout: the chain's bar at the top, the step's title and line under it, the pictures below.
MARGIN = 96
BAR_TOP = 56
TITLE_TOP = 128
LINE_TOP = 232
PICTURES_BOX = (MARGIN, 318, W - MARGIN, H - 56)
BOARD_COLUMNS = 3
BACK = (17, 18, 21)
INK = (236, 236, 232)
DIM_INK = (120, 122, 128)
ACCENT = (232, 170, 90)
ENDING = WORK / "k9-ending"
# The ending's clips in order (that folder also keeps the parts layers3d joined into the first).
ENDING_CLIPS = ("built-in-layers.mp4", "ready-for-score-lib.mp4")
# A store film's shown frame: the middle of its one shot, after the title card and its fade.
FILM_MIDDLE = demo.TITLE_SECONDS - FADE + demo_film.SECONDS / 2


def font(size, weight="Regular"):
    face = ImageFont.truetype(FONT, size)
    face.set_variation_by_name(weight)
    return face


def caption_layer(lines):
    """A transparent picture with the lines low on the left over a soft dark band: (first line small, the rest)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band = np.zeros((H, W, 4), dtype=np.uint8)
    rows = np.clip((np.arange(H) - H * 0.62) / (H * 0.38), 0, 1) ** 1.5
    band[..., 3] = (rows[:, None] * 205).astype(np.uint8)
    layer = Image.alpha_composite(layer, Image.fromarray(band, "RGBA"))
    draw = ImageDraw.Draw(layer)
    small, large = font(34, "Medium"), font(46, "Medium")
    y = H - 70
    for index, line in reversed(list(enumerate(lines))):
        face = small if index == 0 and len(lines) > 1 else large
        box = draw.textbbox((0, 0), line, font=face)
        y -= box[3] - box[1] + (16 if face is large else 12)
        draw.text((96, y), line, font=face, fill=(240, 240, 236, 255) if face is large else (214, 206, 186, 255))
    return layer


def fitted(picture, scale):
    """A picture fitted inside the frame at `scale` of its fitted size, centred on black."""
    picture = picture.convert("RGB")
    ratio = min(W / picture.width, H / picture.height) * scale
    size = (round(picture.width * ratio), round(picture.height * ratio))
    frame = Image.new("RGB", (W, H), (0, 0, 0))
    frame.paste(picture.resize(size, Image.LANCZOS), ((W - size[0]) // 2, (H - size[1]) // 2))
    return frame


def credited(picture, credit):
    """A frame with its maker's credit small at the bottom right (World Labs' terms ask "Generated using World Labs"
    wherever its output is shown); unchanged when `credit` is None."""
    if not credit:
        return picture
    draw = ImageDraw.Draw(picture)
    small = font(22, "Medium")
    width = draw.textlength(credit, font=small)
    draw.rounded_rectangle((W - width - 72, H - 76, W - 32, H - 32), radius=8, fill=(0, 0, 0))
    draw.text((W - width - 52, H - 68), credit, font=small, fill=(240, 240, 236))
    return picture


def write_frames(frames, seconds, out):
    """Frames (a function of the frame number giving an RGB picture) piped to ffmpeg as a silent clip."""
    count = round(seconds * RATE)
    process = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt",
                                "rgb24", "-s", f"{W}x{H}", "-r", str(RATE), "-i", "-", *demo.encode(out)[:-1],
                                str(out)], stdin=subprocess.PIPE)
    for number in range(count):
        process.stdin.write(np.asarray(frames(number, count), dtype=np.uint8).tobytes())
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on {out}")


def still_clip(picture, seconds, out, lines=(), zoom=(1.0, 1.05), scale=0.92):
    """A still, slowly closing in, with its caption."""
    still = fitted(picture, scale)
    layer_cache = {}

    def frame(number, count):
        share = number / max(count - 1, 1)
        eased = 0.5 - 0.5 * math.cos(math.pi * share)
        grow = zoom[0] + (zoom[1] - zoom[0]) * eased
        crop = (W * (1 - 1 / grow) / 2, H * (1 - 1 / grow) / 2)
        moved = still.transform((W, H), Image.EXTENT, (crop[0], crop[1], W - crop[0], H - crop[1]), Image.BICUBIC)
        if "layer" not in layer_cache and lines:
            layer_cache["layer"] = caption_layer(lines)
        return with_caption_cached(moved, layer_cache.get("layer"), number, count)

    write_frames(frame, seconds, out)


def with_caption_cached(base, layer, number, count):
    if layer is None:
        return np.asarray(base)
    shown = min(1.0, max(0.0, (number / RATE - 0.4) / 0.5), max(0.0, (count - number) / RATE / 0.5))
    alpha = np.asarray(layer)[..., 3:4].astype(float) / 255.0 * shown
    return np.asarray(base, dtype=float) * (1 - alpha) + np.asarray(layer)[..., :3] * alpha


def backdrop(picture):
    """The wreck's stage as Blender draws it (a picture of it), blurred and dimmed, for words to stand on."""
    from PIL import ImageFilter
    picture = Image.open(picture).convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5))
    return Image.fromarray((np.asarray(picture, dtype=float) * DIM).astype(np.uint8))


def drifting(picture, seconds, out, zoom=(1.0, 1.04)):
    """A still drifting slowly closer, so a held card still moves."""
    still_clip(picture, seconds, out, zoom=zoom, scale=1.0)


def card(lines, sizes, seconds, out, behind):
    """Words centred on the backdrop (made from the picture `behind`), each line in its size."""
    picture = backdrop(behind)
    draw = ImageDraw.Draw(picture)
    faces = [font(size, weight) for size, weight in sizes]
    heights = [draw.textbbox((0, 0), line, font=face)[3] for line, face in zip(lines, faces)]
    y = (H - sum(heights) - 28 * (len(lines) - 1)) / 2
    for line, face, height in zip(lines, faces, heights):
        width = draw.textlength(line, font=face)
        draw.text(((W - width) / 2, y), line, font=face, fill=(236, 236, 232))
        y += height + 28
    drifting(picture, seconds, out)


def linear_to_srgb(colour):
    colour = np.clip(np.asarray(colour[:3], dtype=float), 0, 1)
    return tuple(int(round(255 * value)) for value in
                 np.where(colour <= 0.0031308, colour * 12.92, 1.055 * colour ** (1 / 2.4) - 0.055))


def surfaces_legend(shots):
    """The aft section's surfaces with their colours (the place's library colours from the review page's shots) and
    each one's share of the parts by area, as words: [(surface, colour, share)]."""
    group = next(group for group in shots["groups"] if group["name"] == "aft_section-parts")
    files = group["members"][0]["files"]
    areas = [trimesh.load(entry["path"], force="mesh").area for entry in files]
    return [(pathlib.Path(entry["path"]).stem, linear_to_srgb(entry["colour"]), f"{100 * area / sum(areas):.0f}%")
            for entry, area in zip(files, areas)]


def legend_layer(legend):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    face = font(30, "Regular")
    y = 120
    for name, colour, share in legend:
        draw.rectangle((W - 560, y, W - 516, y + 44), fill=colour + (255,), outline=(220, 220, 216, 255))
        draw.text((W - 496, y + 4), f"{name.replace('_', ' ')}  {share}", font=face,
                  fill=(236, 236, 232, 255))
        y += 64
    return layer


def sequence_clip(paths, seconds, out, lines=(), extra=None, scale=0.95):
    """Pictures in turn (a turntable's frames), spread over `seconds`, with a caption and an optional layer."""
    stills = [fitted(Image.open(path), scale) for path in paths]
    caption = caption_layer(lines) if lines else None

    def frame(number, count):
        picture = stills[min(len(stills) - 1, number * len(stills) // count)]
        if extra is not None:
            picture = Image.alpha_composite(picture.convert("RGBA"), extra).convert("RGB")
        return with_caption_cached(picture, caption, number, count)

    write_frames(frame, seconds, out)


def checks_card(manifest, seconds, out, behind):
    """The completion gate's requirements on the wreck's stage, each with its result and why, as the gate wrote them."""
    picture = backdrop(behind)
    draw = ImageDraw.Draw(picture)
    draw.text((140, 90), "Checks before every paid step", font=font(50, "Medium"), fill=(236, 236, 232))
    draw.text((140, 160), "The completion gate on the wreck's stage: measured, never judged by eye",
              font=font(30, "Light"), fill=(200, 200, 196))
    face, bold = font(30, "Regular"), font(30, "SemiBold")
    y = 250
    colours = {"pass": (140, 200, 150), "fail": (230, 130, 110), "unknown": (220, 190, 110)}
    for requirement in manifest["requirements"]:
        draw.text((140, y), requirement["name"].replace("_", " "), font=face, fill=(236, 236, 232))
        draw.text((420, y), requirement["result"], font=bold, fill=colours.get(requirement["result"], (236, 236, 232)))
        draw.text((560, y), requirement["why"][:80], font=face, fill=(190, 190, 186))
        y += 56
    draw.text((140, y + 24), f"verdict: {manifest['verdict']}; the place is not done until every check passes",
              font=bold, fill=colours.get(manifest["verdict"], (236, 236, 232)))
    drifting(picture, seconds, out, zoom=(1.0, 1.02))


def soundtrack_under(stage, video, seconds, out):
    """The video with what a still camera at the wreck's first record spot hears over its length
    (hearing.soundtrack)."""
    record = json.loads((REPO / "data/scene/wreck.json").read_text())
    view = next(view for view in record["views"] if view["name"] == "wreck-home")
    count = round(seconds * RATE)
    moments = [{"eye": view["eye"], "aim": view["aim"], "time": number / RATE} for number in range(count)]
    track = pathlib.Path(out).with_suffix(".wav")
    hearing.soundtrack(stage, moments, RATE, track)
    sound.with_sound(video, track, out)


def shown_shot(folder, film):
    """The shot a film is shown by: its first walking shot, else its second."""
    moves = [move["move"] for move in json.loads((folder / "views" / f"{film}.json").read_text())["moves"]]
    return moves.index("walk") if "walk" in moves else min(1, len(moves) - 1)


def place_clip(folder, film, part, place, out):
    """PLACE_SECONDS of a place's film, from inside its first walking shot (else its second shot), with a caption."""
    shot = shown_shot(folder, film)
    start = demo.TITLE_SECONDS - FADE + shot * (demo.SHOT_SECONDS - FADE) + 1.25
    caption = folder / "showcase/parts" / f"caption-{film}.png"
    caption_layer([part, place]).save(caption)
    fade_out = PLACE_SECONDS - 0.6
    graph = (f"[1:v]format=rgba,fade=t=in:st=0.4:d=0.5:alpha=1,fade=t=out:st={fade_out}:d=0.5:alpha=1[c];"
             f"[0:v][c]overlay=format=auto[v]")
    demo.ffmpeg("-ss", f"{start:.3f}", "-t", PLACE_SECONDS, "-i", folder / "videos" / f"{film}.mp4", "-loop", "1",
                "-t", PLACE_SECONDS, "-i", caption, "-filter_complex", graph, "-map", "[v]", "-map", "0:a", "-c:a",
                "aac", "-b:a", "160k", *demo.encode(out))
    return PLACE_SECONDS


def silence_under(video, seconds, out):
    demo.ffmpeg("-i", video, "-f", "lavfi", "-t", seconds, "-i", f"anullsrc=r={demo.SAMPLE_RATE}:cl=stereo", "-map",
                "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", out)


def edit_clip(steps, each, out):
    """The edit's pictures in turn under one slow continuous zoom, each with its caption, cut in a short dissolve, so
    the same place is seen before the edit, after it and after the regeneration from the very same view."""
    pictures = [np.asarray(fitted(Image.open(path), 1.0), dtype=float) for path, _ in steps]
    captions = [caption_layer(lines) for _, lines in steps]
    dissolve = round(0.4 * RATE)
    per = round(each * RATE)

    def frame(number, count):
        step = min(number // per, len(steps) - 1)
        local = number - step * per
        picture = pictures[step]
        if step > 0 and local < dissolve:
            share = local / dissolve
            picture = pictures[step - 1] * (1 - share) + picture * share
        share = number / max(count - 1, 1)
        grow = 1.0 + 0.06 * share
        crop = (W * (1 - 1 / grow) / 2, H * (1 - 1 / grow) / 2)
        moved = Image.fromarray(picture.astype(np.uint8)).transform(
            (W, H), Image.EXTENT, (crop[0], crop[1], W - crop[0], H - crop[1]), Image.BICUBIC)
        return with_caption_cached(moved, captions[step], local, per)

    write_frames(frame, each * len(steps), out)


def edit_still(folder, take):
    """The edit's still of one take with its ink lines (demo.inked), as the films are drawn."""
    return demo.inked(folder / "showcase/edit/out" / take, EDIT_VIEW)


def inventory_rows(place):
    """How many rows the place's inventory has (data/inventory/<place>.json)."""
    return len(json.loads((REPO / "data/inventory" / f"{place}.json").read_text())["rows"])


def framework_part(folder, parts, page, stage, concept):
    """The framework's story on the wreck, as silent clips: (clips, their lengths)."""
    shots = json.loads((page / "models/shots.json").read_text())
    models = folder / "showcase/models/out"
    manifest = json.loads((stage.parent / "manifest.json").read_text())
    behind = edit_still(folder, TAKES[0])
    plan = []
    card(["SCORE", "A world generation framework"], [(120, "Medium"), (46, "Light")], 5.0, parts / "00-title.mp4",
         behind)
    plan.append((parts / "00-title.mp4", 5.0))
    still_clip(Image.open(concept), 8.0, parts / "01-pick.mp4",
               ["The creator's picks", f"A concept for each place: the wreck, take {concept.stem}"])
    plan.append((parts / "01-pick.mp4", 8.0))
    still_clip(Image.open(page / "img/inventory-v1.jpg"), 8.0, parts / "02-inventory.mp4",
               ["Inventory", f"Every thing in the concept gets a measured box: {inventory_rows('wreck')} rows"])
    plan.append((parts / "02-inventory.mp4", 8.0))
    still_clip(Image.open(page / "img/closeup-aft_section.jpg"), 6.0, parts / "03-closeup.mp4",
               ["Close-ups", "A close-up of each thing: the aft section"])
    plan.append((parts / "03-closeup.mp4", 6.0))
    sequence_clip(sorted(models.glob("aft_section-parts-*.png")), 4.5, parts / "04-parts.mp4",
                  ["The model and its parts", "Made in 3D and split into parts, each labelled with a library surface"],
                  extra=legend_layer(surfaces_legend(shots)))
    plan.append((parts / "04-parts.mp4", 4.5))
    sequence_clip(sorted(models.glob("aft_section-made-*.png")), 4.5, parts / "05-paint.mp4",
                  ["Paint", "Painted from the shared surface library, never from the picture's colours"])
    plan.append((parts / "05-paint.mp4", 4.5))
    checks_card(manifest, 7.0, parts / "06-checks.mp4", behind)
    plan.append((parts / "06-checks.mp4", 7.0))
    steps = [(edit_still(folder, TAKES[0]), ["The stage", "The place as one OpenUSD stage, drawn here by Blender"]),
             (edit_still(folder, TAKES[1]), ["An edit", "The creator moves a pressure sphere in the edit layer"]),
             (edit_still(folder, TAKES[2]),
              ["A regeneration", "The framework writes its base layer again; the edit stays"])]
    edit_clip(steps, 4.5, parts / "07-edit.mp4")
    plan.append((parts / "07-edit.mp4", 4.5 * len(steps)))
    card(["World 1: 2099", "A prologue in Hong Kong, the Moon base, the Mars camp",
          "Every place walked through at eye height, with its own sound"],
         [(64, "Medium"), (36, "Light"), (36, "Light")], 5.0, parts / "08-world.mp4", behind)
    plan.append((parts / "08-world.mp4", 5.0))
    return plan


def cut(folder, page, stage, concept):
    """The showcase: the framework's part over the wreck's sound, each place's part of its film, the end card."""
    parts = folder / "showcase/parts"
    parts.mkdir(parents=True, exist_ok=True)
    plan = framework_part(folder, parts, page, stage, concept)
    silent = parts / "framework-silent.mp4"
    demo.joined([clip for clip, _ in plan], [seconds for _, seconds in plan], silent)
    framework_seconds = sum(seconds for _, seconds in plan) - FADE * (len(plan) - 1)
    framework = parts / "framework.mp4"
    soundtrack_under(stage, silent, framework_seconds, framework)
    clips, lengths = [framework], [framework_seconds]
    for film, part, place, _ in PLACES:
        clips.append(parts / f"place-{film}.mp4")
        lengths.append(place_clip(folder, film, part, place, clips[-1]))
    card(["SCORE", REPO_LINK, "(MIT license)"], [(96, "Medium"), (44, "Regular"), (36, "Light")], 6.0,
         parts / "09-end-silent.mp4", edit_still(folder, TAKES[0]))
    silence_under(parts / "09-end-silent.mp4", 6.0, parts / "09-end.mp4")
    clips.append(parts / "09-end.mp4")
    lengths.append(6.0)
    out = folder / "showcase/showcase.mp4"
    demo.joined(clips, lengths, out)
    print(f"{out}: {sum(lengths) - FADE * (len(lengths) - 1):.1f} s planned")


def labelled(picture, text, face):
    """A tile with its name low on the left on a black band, large enough to read at a quarter of a page's width."""
    draw = ImageDraw.Draw(picture)
    width = draw.textlength(text, font=face)
    draw.rectangle([0, picture.height - 52, width + 16, picture.height], fill=(0, 0, 0))
    draw.text((8, picture.height - 47), text, font=face, fill=(240, 240, 240))
    return picture


def sheet(tiles, out):
    """The tiles, (name, title, picture path), COLUMNS a row, each with its title; their list beside it (<out>.json)."""
    face = ImageFont.truetype(LABEL_FONT, 36)
    rows = -(-len(tiles) // COLUMNS)
    picture = Image.new("RGB", (COLUMNS * TILE[0] + (COLUMNS - 1) * 8, rows * TILE[1] + (rows - 1) * 8), "white")
    for number, (_, title, path) in enumerate(tiles):
        tile = Image.open(path).convert("RGB").resize(TILE, Image.LANCZOS)
        spot = ((number % COLUMNS) * (TILE[0] + 8), (number // COLUMNS) * (TILE[1] + 8))
        picture.paste(labelled(tile, title, face), spot)
    picture.save(out, quality=86)
    pathlib.Path(out).with_suffix(".json").write_text(json.dumps([[*map(str, tile)] for tile in tiles], indent=1))
    print(f"{out}: {len(tiles)} frames")


def figure(folder, out):
    """One frame of each film in story order, COLUMNS a row, each with its place's name; the frames used beside it."""
    tiles = []
    for film, _, _, title in PLACES:
        frames = folder / "frames" / film
        tiles.append((film, title, demo.inked(
            frames, f"shot{shown_shot(folder, film)}-{round(demo.SHOT_SECONDS * RATE) // 2:03d}")))
    sheet(tiles, out)


def store_films(store):
    """Every film of the world video in its order: (name, title, its film.mp4 or None, its store output or None)."""
    found = []
    for place, *_, title in PLACES:
        output = store.accepted(f"demo-film@{place}")
        found.append((place, title, output and store.checkout(output) / "film.mp4", output))
        for name, extra_title in EXTRAS.get(place, ()):
            output = store.accepted(f"demo-film-extra@{place}")
            path = output and store.checkout(output) / name / "film.mp4"
            found.append((name, extra_title, path if path and path.exists() else None, output if path else None))
    return found


def length(video):
    """A video's length in seconds (ffprobe)."""
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(video)], capture_output=True, text=True, check=True).stdout)


def middle_frame(video, out):
    """The middle frame of a store film's shot, as a picture."""
    demo.ffmpeg("-ss", f"{FILM_MIDDLE:.3f}", "-i", video, "-frames:v", "1", out)
    return out


def chain_cards(chosen):
    """The chain's cards from the assets, in order: [(step, line, [picture paths])]. Stops on a step the chain does not
    have (the last step, the place, is the hero's film, never a card), on steps out of the chain's order, and on more
    than CHAIN_MOST cards."""
    cards = [(entry["step"], entry.get("line", ""), list(entry["pictures"])) for entry in chosen.get("steps", [])]
    order = [CHAIN.index(step) if step in CHAIN[:-1] else -1 for step, _, _ in cards]
    if -1 in order or order != sorted(order):
        raise SystemExit(f"world: the chain's steps must come from {', '.join(CHAIN[:-1])} in that order: "
                         f"{[step for step, _, _ in cards]}")
    if len(cards) > CHAIN_MOST:
        raise SystemExit(f"world: {len(cards)} chain cards, at most {CHAIN_MOST}")
    return cards


def board(paths):
    """The card's pictures laid on the card's dark ground inside PICTURES_BOX: one picture as large as fits, several
    side by side, at most BOARD_COLUMNS a row, each fitted whole into its cell."""
    wide, tall = PICTURES_BOX[2] - PICTURES_BOX[0], PICTURES_BOX[3] - PICTURES_BOX[1]
    columns = min(len(paths), BOARD_COLUMNS)
    rows = math.ceil(len(paths) / columns)
    gap = 24
    cell = ((wide - gap * (columns - 1)) / columns, (tall - gap * (rows - 1)) / rows)
    laid = Image.new("RGB", (wide, tall), BACK)
    for number, path in enumerate(paths):
        picture = Image.open(path).convert("RGB")
        ratio = min(cell[0] / picture.width, cell[1] / picture.height)
        size = (round(picture.width * ratio), round(picture.height * ratio))
        column, row = number % columns, number // columns
        spot = (column * (cell[0] + gap) + (cell[0] - size[0]) / 2, row * (cell[1] + gap) + (cell[1] - size[1]) / 2)
        laid.paste(picture.resize(size, Image.LANCZOS), (round(spot[0]), round(spot[1])))
    return laid


def words_layer(step, line):
    """The step's title, large, and its one line under it, on the left under the chain's bar."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text((MARGIN, TITLE_TOP), step, font=font(84, "SemiBold"), fill=INK + (255,))
    draw.text((MARGIN, LINE_TOP), line, font=font(40, "Light"), fill=(206, 204, 196, 255))
    return layer


def bar_layer(current, share):
    """The chain's progress bar: every step's name over its track, the steps before `current` filled, `current` filled
    to `share` (0 to 1) and lit, the steps after it dim."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    face = font(30, "Medium")
    gap = 24
    each = (W - 2 * MARGIN - gap * (len(CHAIN) - 1)) / len(CHAIN)
    for number, step in enumerate(CHAIN):
        left = MARGIN + number * (each + gap)
        filled = 1.0 if number < current else share if number == current else 0.0
        colour = INK if number == current else (176, 176, 172) if number < current else DIM_INK
        draw.text((left, BAR_TOP), f"{number + 1}  {step}", font=face, fill=colour + (255,))
        draw.rectangle((left, BAR_TOP + 46, left + each, BAR_TOP + 52), fill=(58, 60, 66, 255))
        if filled > 0:
            draw.rectangle((left, BAR_TOP + 46, left + each * filled, BAR_TOP + 52), fill=ACCENT + (255,))
    return layer


def faded(layer, share):
    """An RGBA layer with its opacity scaled by `share` (0 to 1)."""
    if share >= 1.0:
        return layer
    shown = layer.copy()
    shown.putalpha(layer.getchannel("A").point(lambda alpha: round(alpha * share)))
    return shown


def eased(share):
    """0 to 1, slow at both ends."""
    share = min(1.0, max(0.0, share))
    return 0.5 - 0.5 * math.cos(math.pi * share)


def credit_layer(credit):
    """The credit a card's picture carries (credited's), alone on a clear layer."""
    return credited(Image.new("RGBA", (W, H), (0, 0, 0, 0)), credit)


def placed(canvas, laid, shift, grow, share):
    """A card's board laid into its box on `canvas`, moved `shift` pixels sideways, grown by `grow` about its middle and
    shown at `share` opacity."""
    size = (round(laid.width * grow), round(laid.height * grow))
    picture = laid.resize(size, Image.BICUBIC).convert("RGBA")
    picture.putalpha(round(255 * share))
    left = PICTURES_BOX[0] + (laid.width - size[0]) / 2 + shift
    top = PICTURES_BOX[1] + (laid.height - size[1]) / 2
    canvas.alpha_composite(picture, (round(left), round(top)))


def opening_look(picture, share):
    """The opening at `share` of its time: the title over the opening picture, closing in slowly."""
    grow = 1.0 + 0.05 * eased(share)
    crop = (W * (1 - 1 / grow) / 2, H * (1 - 1 / grow) / 2)
    return picture.transform((W, H), Image.EXTENT, (crop[0], crop[1], W - crop[0], H - crop[1]), Image.BICUBIC)


def title_still(behind):
    """The world's title over its picture (backdrop's blur and dim)."""
    picture = backdrop(behind)
    draw = ImageDraw.Draw(picture)
    lines = [("World 1: 2099", font(96, "Medium")), ("From the creator's picks to a walkable world", font(44, "Light"))]
    y = H / 2 - 90
    for line, face in lines:
        draw.text(((W - draw.textlength(line, font=face)) / 2, y), line, font=face, fill=INK)
        y += 130
    return picture


def card_look(cards, number, local):
    """Chain card `number`, `local` seconds into its time, on its own: its board closing in, its words, its credit and
    the bar; while it moves in, the card before it moves out to the left and fades first, and the words change over
    one after the other, never laid over each other (the opening fades under the first card instead)."""
    laids, words, credits, steps = cards
    move = eased(local / MOVE_SECONDS)
    canvas = Image.new("RGBA", (W, H), BACK + (255,))
    push = W * 0.3
    leaving, coming = (1 - min(1.0, move / 0.6), max(0.0, (move - 0.4) / 0.6)) if number else (0.0, 1.0)
    if leaving > 0:
        placed(canvas, laids[number - 1], -push * move, 1.03, leaving)
        canvas.alpha_composite(faded(words[number - 1], max(0.0, 1 - 2 * move)))
    placed(canvas, laids[number], push * (1 - move), 1.0 + 0.03 * eased(local / STEP_SECONDS), coming)
    canvas.alpha_composite(faded(words[number], max(0.0, 2 * move - 1) if number else 1.0))
    canvas.alpha_composite(faded(credits[number], coming))
    step = CHAIN.index(steps[number])
    same = [index for index, name in enumerate(steps) if name == steps[number]]
    share = (same.index(number) + local / STEP_SECONDS) / len(same)
    canvas.alpha_composite(bar_layer(step, share))
    return canvas.convert("RGB")


def chain_clip(opening, cards, credits, out):
    """The opening's title (OPENING_SECONDS), then the chain's cards (chain_cards), STEP_SECONDS each, each pushed in
    over the one before, as one silent clip; its length."""
    title = title_still(opening)
    loaded = ([board(paths) for _, _, paths in cards], [words_layer(step, line) for step, line, _ in cards],
              [credit_layer(next((credits[str(path)] for path in paths if str(path) in credits), None))
               for _, _, paths in cards], [step for step, _, _ in cards])
    seconds = OPENING_SECONDS + STEP_SECONDS * len(cards)

    def frame(number, count):
        moment = number / RATE
        if moment < OPENING_SECONDS:
            return np.asarray(opening_look(title, moment / OPENING_SECONDS))
        card, local = divmod(moment - OPENING_SECONDS, STEP_SECONDS)
        look = card_look(loaded, int(card), local)
        if card == 0 and local < MOVE_SECONDS:
            look = Image.blend(opening_look(title, 1.0), look, eased(local / MOVE_SECONDS))
        return np.asarray(look)

    write_frames(frame, seconds, out)
    return seconds


def hero_layer(line):
    """The hero's film as the chain's last step: a dark band at the top, the bar with every step done, the step's
    title and line."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band = np.zeros((H, W, 4), dtype=np.uint8)
    rows = np.clip(1 - np.arange(H) / (H * 0.36), 0, 1) ** 1.3
    band[..., 3] = (rows[:, None] * 215).astype(np.uint8)
    layer = Image.alpha_composite(layer, Image.fromarray(band, "RGBA"))
    layer = Image.alpha_composite(layer, bar_layer(len(CHAIN) - 1, 1.0))
    return Image.alpha_composite(layer, words_layer(CHAIN[-1], line))


def shown_seconds(film):
    """How much of a store film is shown: from its title card's end, at most PLACE_MOST."""
    return min(length(film) - demo.TITLE_SECONDS, PLACE_MOST)


def result_clip(film, seconds, layer, out, fades=True):
    """`seconds` of a place's film from its title card's end, with its own sound, under `layer` (an RGBA picture), the
    layer fading in and out when `fades` (a place's caption), else held throughout (the hero's chain layer)."""
    still = pathlib.Path(out).with_suffix(".layer.png")
    layer.save(still)
    shown = (f"fade=t=in:st=0.3:d=0.6:alpha=1,fade=t=out:st={seconds - 0.9:.3f}:d=0.6:alpha=1," if fades else "")
    graph = f"[0:v]scale={W}:{H}[f];[1:v]format=rgba,{shown}null[l];[f][l]overlay=format=auto[v]"
    demo.ffmpeg("-ss", f"{demo.TITLE_SECONDS:.3f}", "-t", f"{seconds:.3f}", "-i", film, "-loop", "1", "-t",
                f"{seconds:.3f}", "-i", still, "-filter_complex", graph, "-map", "[v]", "-map", "0:a", "-c:a", "aac",
                "-b:a", "160k", *demo.encode(out))
    still.unlink()


def bed_of(film):
    """A store film's bed (demo_film's bed.wav beside its film.mp4), or None (a film made before beds)."""
    bed = pathlib.Path(film).parent / "bed.wav"
    return bed if bed.exists() else None


def bed_track(film, seconds, out, rise=0.0, fall=0.0):
    """A sound bed `seconds` long from the film's bed (bed_of: what its camera hears before it walks), else from its
    own sound after its title card, looped with BED_SEAM cross-fades so no seam clicks, rising over `rise` seconds at
    its start and falling over `fall` at its end."""
    bed = bed_of(film)
    piece = length(bed) if bed else length(film) - demo.TITLE_SECONDS
    copies = max(1, math.ceil((seconds - BED_SEAM) / (piece - BED_SEAM)) + 1)
    one = ("-i", bed) if bed else ("-ss", f"{demo.TITLE_SECONDS:.3f}", "-i", film)
    inputs = [part for _ in range(copies) for part in one]
    chain, previous = [], "[0:a]"
    for number in range(1, copies):
        chain.append(f"{previous}[{number}:a]acrossfade=d={BED_SEAM}[b{number}]")
        previous = f"[b{number}]"
    shaped = f"atrim=0:{seconds:.3f},asetpts=N/SR/TB"
    if rise:
        shaped += f",afade=t=in:d={rise}"
    if fall:
        shaped += f",afade=t=out:st={max(0.0, seconds - fall):.3f}:d={fall}"
    chain.append(f"{previous}{shaped}[bed]")
    demo.ffmpeg(*inputs, "-filter_complex", ";".join(chain), "-map", "[bed]", "-c:a", "aac", "-b:a", "160k",
                "-ar", demo.SAMPLE_RATE, out)


def ending_part(endings, film, parts):
    """The ending's clips joined into one, under a bed of `film`'s sound falling away to silence; its length."""
    clips = [parts / f"ending-{ending.name}" for ending in endings]
    lengths = [ending_clip(ending, clip) for ending, clip in zip(endings, clips)]
    seconds = sum(lengths) - FADE * (len(lengths) - 1)
    picture, bed, out = parts / "ending-picture.mp4", parts / "ending-bed.m4a", parts / "ending.mp4"
    demo.joined(clips, lengths, picture)
    bed_track(film, seconds, bed, fall=BED_FALL)
    sound.with_sound(picture, bed, out)
    return out, seconds


def timeline(cards, shown, ending):
    """The world video's parts and lengths in order: the opening with the chain's `cards` (a number), each film's
    shown length (`shown` [(film, seconds)]), then the ending's length (0: none). Every part after the first starts
    FADE before the one before it ends."""
    parts = [("chain", OPENING_SECONDS + STEP_SECONDS * cards)] + list(shown)
    return parts + ([("ending", ending)] if ending else [])


def total(parts):
    """The length of the parts joined by cross-fades."""
    return sum(seconds for _, seconds in parts) - FADE * (len(parts) - 1)


def captions():
    """Each film's caption, [part of the world, the place]: the places', and every extra film's under its place's part."""
    found = {film: [part, place] for film, part, place, _ in PLACES}
    for place, extras in EXTRAS.items():
        found.update({name: [found[place][0], title] for name, title in extras})
    return found


def ending_clip(clip, out):
    """An ending clip made elsewhere, brought to the video's size and rate with a sound track (silence when it has
    none); its length."""
    seconds = length(clip)
    sound = [] if demo.has_sound(clip) else ["-f", "lavfi", "-t", seconds, "-i",
                                             f"anullsrc=r={demo.SAMPLE_RATE}:cl=stereo"]
    demo.ffmpeg("-i", clip, *sound, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                 f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2", "-map", "0:v", "-map", "1:a" if sound else "0:a", "-c:a", "aac",
                 "-ar", demo.SAMPLE_RATE, "-shortest", *demo.encode(out))
    return seconds


# Clips one ffmpeg graph joins at most: 57 cross-faded in one graph left ffmpeg stalled with 12.7 GB held, 2026-10-18.
JOIN_GROUP = 8


def joined_in_groups(clips, lengths, out, parts):
    """demo.joined over many clips: each group of JOIN_GROUP joined first, then the groups, with the same cross-fades
    between every two clips, so the video is as long as one join of them all."""
    if len(clips) <= JOIN_GROUP:
        joined_apart(clips, lengths, out, parts)
        return
    groups, group_lengths = [], []
    for start in range(0, len(clips), JOIN_GROUP):
        part = parts / f"group-{start // JOIN_GROUP:02d}.mp4"
        joined_apart(clips[start:start + JOIN_GROUP], lengths[start:start + JOIN_GROUP], part, parts)
        groups.append(part)
        chunk = lengths[start:start + JOIN_GROUP]
        group_lengths.append(sum(chunk) - demo.FADE_SECONDS * (len(chunk) - 1))
    joined_in_groups(groups, group_lengths, out, parts)


def joined_apart(clips, lengths, out, parts):
    """demo.joined's cross-fades with the picture and the sound each joined by its own ffmpeg and laid together
    after: in one graph the sound starved while the picture's fades buffered (a film clip's picture runs 3.54 s, its
    sound 3.5 s; 8 such clips in one graph wrote nothing, 2026-10-18)."""
    if len(clips) == 1 or not all(demo.has_sound(clip) for clip in clips):
        demo.joined(clips, lengths, out)
        return
    inputs = [part for clip in clips for part in ("-i", clip)]
    picture, sound, offset = [], [], 0.0
    previous_picture, previous_sound = "[0:v]", "[0:a]"
    for number in range(1, len(clips)):
        offset += lengths[number - 1] - demo.FADE_SECONDS
        picture.append(f"{previous_picture}[{number}:v]xfade=transition=fade:duration={demo.FADE_SECONDS}:"
                       f"offset={offset:.3f}[v{number}]")
        sound.append(f"{previous_sound}[{number}:a]acrossfade=d={demo.FADE_SECONDS}[a{number}]")
        previous_picture, previous_sound = f"[v{number}]", f"[a{number}]"
    video, audio = parts / f"{out.stem}-picture.mp4", parts / f"{out.stem}-sound.m4a"
    demo.ffmpeg(*inputs, "-filter_complex", ";".join(picture), "-map", previous_picture, *demo.encode(video))
    demo.ffmpeg(*inputs, "-filter_complex", ";".join(sound), "-map", previous_sound, "-c:a", "aac", "-b:a", "160k",
                audio)
    demo.ffmpeg("-i", video, "-i", audio, "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", out)


def world(folder, figure_out, films, assets, draft=False):
    """The world 1 video (demo K9) and its figure: the opening's title, the framework's chain shown once on the hero
    place (chain_clip, then the hero's own film as its last step), every other place's accepted film in story order
    with its caption, then the ending's clips where they exist, the sound never dropping between them; the films from
    store_films, the pictures from `assets` (a JSON file: {"hero": film, "hero_line", "opening": picture, "steps":
    [{"step", "line", "pictures"}], "credits": {path: credit shown on it}}). Stops on a missing film unless a draft."""
    missing = [name for name, _, path, _ in films if path is None]
    if missing and not draft:
        raise SystemExit(f"world: {len(missing)} of {len(films)} films not in the store: {', '.join(missing)}")
    made = [film for film in films if film[2] is not None]
    if not made:
        raise SystemExit("world: no film in the store")
    chosen = json.loads(pathlib.Path(assets).read_text())
    cards = chain_cards(chosen)
    hero = chosen["hero"]
    made.sort(key=lambda film: film[0] != hero)
    parts = folder / "parts"
    parts.mkdir(parents=True, exist_ok=True)
    silent, chain = parts / "chain-picture.mp4", parts / "chain.mp4"
    chain_seconds = chain_clip(chosen["opening"], cards, chosen.get("credits", {}), silent)
    bed_track(made[0][2], chain_seconds, parts / "chain-bed.m4a", rise=BED_RISE)
    sound.with_sound(silent, parts / "chain-bed.m4a", chain)
    clips, lengths, shown = [chain], [chain_seconds], []
    named = captions()
    for name, title, path, output in made:
        seconds = shown_seconds(path)
        clips.append(parts / f"{name}-result.mp4")
        if name == hero:
            result_clip(path, seconds, hero_layer(chosen.get("hero_line", "")), clips[-1], fades=False)
        else:
            result_clip(path, seconds, caption_layer(named.get(name, [title])), clips[-1])
        lengths.append(seconds)
        shown.append({"film": name, "title": title, "output": output, "seconds": round(seconds, 2)})
    endings = [ENDING / name for name in ENDING_CLIPS if (ENDING / name).exists()]
    if endings:
        ending, seconds = ending_part(endings, made[-1][2], parts)
        clips.append(ending)
        lengths.append(seconds)
    video = folder / "world1.mp4"
    joined_in_groups(clips, lengths, video, parts)
    (folder / "frames").mkdir(exist_ok=True)
    sheet([(name, title, middle_frame(path, folder / "frames" / f"{name}.png")) for name, title, path, _ in made],
          figure_out)
    record = {"hero": hero, "steps": [step for step, _, _ in cards], "films": shown, "missing": missing,
              "ending": [str(clip) for clip in endings]}
    (folder / "world1.json").write_text(json.dumps(record, indent=1))
    print(f"{video}: {len(made)} of {len(films)} films, {length(video):.1f} s"
          + (f"; missing {', '.join(missing)}" if missing else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=["cut", "figure", "world"])
    parser.add_argument("folder", type=pathlib.Path, help="the films' out folder (demo.py's); world: where it goes")
    parser.add_argument("figure", type=pathlib.Path, nargs="?", help="figure, world: the picture to write")
    parser.add_argument("--draft", action="store_true", help="world: cut the films the store holds, name the rest")
    parser.add_argument("--assets", type=pathlib.Path, help="world: the pictures shown before each film (JSON)")
    parser.add_argument("--page", type=pathlib.Path, help="cut: the wreck's review page")
    parser.add_argument("--stage", type=pathlib.Path, help="cut: the wreck's stage")
    parser.add_argument("--concept", type=pathlib.Path, help="cut: the concept the owner picked")
    options = parser.parse_args()
    if options.step == "world":
        folder = options.folder.resolve()
        if not options.assets:
            parser.error("world needs --assets")
        world(folder, options.figure or folder / "fig-k9.jpg", store_films(Store.default()), options.assets,
              options.draft)
    elif options.step == "figure":
        if not options.figure:
            parser.error("figure needs the picture to write")
        figure(options.folder.resolve(), options.figure)
    elif not (options.page and options.stage and options.concept):
        parser.error("cut needs --page, --stage and --concept")
    else:
        cut(options.folder.resolve(), options.page.resolve(), options.stage.resolve(), options.concept.resolve())


if __name__ == "__main__":
    main()
