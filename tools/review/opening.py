"""The demo film's opening (#128): the title, the framework's whole route as a diagram, then the environment's style
shown, not told, each read from the places' own records; the cards and their clip, ready to be joined before the place
films.

    .venv/bin/python tools/review/opening.py <out> --scenes <folder> --films <folder> \
        [--places camp,campgrounds,stairwell,street] [--step facts|swatches|cards|clip]

<scenes>/<place>/ holds what the place's stage folder holds: concept.png, palette.json (its scene's surface library:
its tokens), scene.usda (the stage, whose Looks carry each laid library surface's resolved recipe,
`score:recipe:spec`) and render/concept-look.png (the laid place drawn from its concept's view). <films>/<place>.mp4 is
the place's film and <films>/<place>-short-peel.mp4 its peel.

The cards (owner, 2026-11-19: "the only actual only text intro needs to be title ... style u need visualized aswell";
2026-11-20: "the physics slide can go, and in place after score title, u need a slide that shows the full framework
as a diagram"):
- **title**: SCORE and its long name, the one text card.
- **framework**: the paper's Method as ten steps (FRAMEWORK), each with a picture of its real output for one place
  (FRAMEWORK_PLACE): the environment concept's record, the place's concept, Figure 1's panels
  (paper/score/figures/layers.jpg), the laid place's concept view, its library surfaces and palette, and its films'
  frames; score_lib drawn as the shared library the steps draw from.
- **style**: each place's locked concept with its scene palette's tokens as swatches below it, the tokens its laid
  surfaces use first.
- **surfaces**: each place's most used library surfaces (by the prims bound to them; no glow, one per recipe), drawn
  by the library's own swatch renderer (tools/props/library/inside/swatch.py) in the place's resolved recipe.

The swatches are drawn on the cluster's cards through tools/cloud/library_bake.py (set SCORE_CLOUD=k8s and the
cluster's SCORE_K8S_*, and the run's SCORE_SPEND_TICKET with PROPS_HOME the home holding its yes); the cards are drawn
here. Every step writes into <out> and the next reads it there, so a step can be run again alone; `facts.json` holds
every number the cards show.
"""
import argparse
import collections
import json
import os
import pathlib
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parents[2]

WIDTH, HEIGHT = 1920, 1080
RATE = 24
GROUND = (17, 19, 23)
INK = (237, 235, 230)
SOFT = (150, 152, 156)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAMES = {"camp": "Camp", "campgrounds": "Campgrounds", "stairwell": "Stairwell", "street": "Street"}
SECONDS = {"title": 4.0, "framework": 9.0, "style": 7.0, "surfaces": 7.0}
FADE = 0.5
ACCENT = (226, 132, 86)
BOX = (31, 34, 40)
EDGE = (62, 66, 74)
LIBRARY = (52, 38, 32)
SURFACES_A_PLACE = 4
TOKENS_A_PLACE = 12
UNSHOWN_RECIPES = {"glowing", "clear_glass", "glass"}  # light or see-through: a swatch shows neither
SWATCH = {"size": 360, "samples": 48, "seed": 7}
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
CLOUD_PYTHON = PROPS_HOME / "env/bin/python"
CLASSES = "gpu-24gb"  # an L4: Cycles on its card
FIGURE = REPO / "paper/score/figures/layers.jpg"  # Figure 1: camp through SCORE's layers, 3024 x 1132
FIGURE_PANELS = {  # its panels' pixel boxes, the panel labels left out
    "inventory": (1012, 60, 2012, 561),
    "trellis": ((2026, 333, 2516, 556), (2696, 333, 2850, 556)),  # (c)'s door: its object picture, its mesh
    "colliders": (1012, 630, 2012, 1132)}
FRAMEWORK_PLACE = "camp"
FRAMEWORK_FRAMES = {"people": 7.0, "sim body": 15.0, "stage": 9.0}  # seconds into the place's film (stage: its peel)
SIM_BODY_CROP = (760, 60, 1800, 645)  # the sim body's frame without its muscle-activation legend
FRAMEWORK = [  # (step, title, the line under it), the paper's Method in order
    ("concept", "Concept", ["locked by the creator"]),
    ("place concept", "Place concept", ["Nano Banana Pro,", "Google Gemini API"]),
    ("inventory", "Inventory", ["SAM 3"]),
    ("layout", "Layout", ["coding agent, Blender,", "compared to concept"]),
    ("missing", "Missing objects", ["TRELLIS.2"]),
    ("finish", "Library finish", ["one palette"]),
    ("colliders", "Colliders", ["MuJoCo check"]),
    ("people", "People", ["routed, animated", "by Kimodo"]),
    ("sim body", "Sim bodies", ["MOTOR, MyoFullBody"]),
    ("stage", "OpenUSD stage", ["owned by the creator"])]
FRAMEWORK_DRAWS = ["layout", "finish", "people"]  # the steps that take from score_lib


def font(size, bold=False):
    return ImageFont.truetype(SANS_BOLD if bold else SANS, size)


# --- facts: what the records say -----------------------------------------------------------------------------------

def laid_surfaces(stage_text, place):
    """[(spec, prims bound)] of the library surfaces the stage's Looks carry, most bound first."""
    specs = {}
    for found in re.finditer(r'def Material "([^"]+)"\s*\{\s*token outputs:surface\.connect = [^\n]*\n\s*'
                             r"custom string score:recipe:spec = '(\{.*?\})'", stage_text):
        specs[found.group(1)] = json.loads(found.group(2))
    bound = collections.Counter(re.findall(rf"material:binding = </{place}/Looks/([^>]+)>", stage_text))
    by_library = {}
    for look, spec in specs.items():
        held = by_library.setdefault(spec["library"], [spec, 0])
        held[1] += bound.get(look, 0)
    return sorted(((spec, count) for spec, count in by_library.values() if count), key=lambda item: -item[1])


def shown_surfaces(laid):
    """The surfaces a swatch can show, one per recipe, most bound first, at most SURFACES_A_PLACE."""
    chosen, recipes = [], set()
    for spec, count in laid:
        if spec["recipe"] in UNSHOWN_RECIPES or spec["recipe"] in recipes:
            continue
        recipes.add(spec["recipe"])
        chosen.append({"spec": spec, "prims": count})
    return chosen[:SURFACES_A_PLACE]


def palette_tokens(tokens, laid):
    """[(token, hex)] of the scene palette, the tokens the laid surfaces use first, at most TOKENS_A_PLACE."""
    used = [spec["token"] for spec, _ in laid if spec.get("token") in tokens]
    order = list(dict.fromkeys(used + list(tokens)))
    return [(token, tokens[token]) for token in order[:TOKENS_A_PLACE]]


def environment_facts():
    """What the environment concept locks, as the framework card's first step shows it: its setting's bodies and sites
    (data/physics/setting.json) and the first words of its style line (data/definitions/concept_views.json)."""
    setting = json.loads((REPO / "data/physics/setting.json").read_text())
    style = json.loads((REPO / "data/definitions/concept_views.json").read_text())["style"]
    return {"bodies": [entry["body"] for entry in setting["bodies"]], "sites": len(setting["sites"]),
            "style": style.split(",")[0]}


def facts(options):
    """Every number and name the cards show, from the records."""
    places = {}
    for place in options.places:
        folder = options.scenes / place
        stage = (folder / "scene.usda").read_text()
        laid = laid_surfaces(stage, place)
        places[place] = {
            "name": NAMES.get(place, place.replace("_", " ").title()),
            "tokens": palette_tokens(json.loads((folder / "palette.json").read_text())["tokens"], laid),
            "surfaces": shown_surfaces(laid),
        }
    return {"places": places, "environment": environment_facts()}


# --- the swatches, on the cluster --------------------------------------------------------------------------------

def cloud(tool, jobs, who, *extra):
    """`tool` (library_bake.py or blender_cloud.py) given the job files, run on the cluster's cards (SCORE_CLOUD, the
    cluster's SCORE_K8S_*, the run's SCORE_SPEND_TICKET and the home holding its yes as the caller set them)."""
    subprocess.run([str(CLOUD_PYTHON), str(REPO / "tools/cloud" / tool), *map(str, jobs), "--who", who,
                    "--classes", CLASSES, *extra], check=True)


def swatches(found, out, who):
    """Each shown surface drawn by the library's swatch renderer, a job a place (its own room wear and dirt):
    <out>/swatches/<place>/<place>-<library>-w<wear>.png."""
    jobs = []
    for place, held in found["places"].items():
        wears = {(float(shown["spec"].get("wear", 0.0)), float(shown["spec"].get("dirt", 0.0)))
                 for shown in held["surfaces"]}
        if len(wears) != 1:
            raise SystemExit(f"{place}: its surfaces carry more than one room wear: {sorted(wears)}")
        (wear, dirt), = wears
        materials = {f"{place}-{shown['spec']['library']}": shown["spec"] for shown in held["surfaces"]}
        job = out / f"swatch-{place}-job.json"
        job.write_text(json.dumps({"script": "swatch.py", "out": str(out / "swatches" / place), "materials": materials,
                                   "wears": [wear], "dirt": dirt, **SWATCH}, indent=1))
        jobs.append(job)
    cloud("library_bake.py", jobs, who)


def swatch_path(out, place, spec):
    return out / "swatches" / place / f"{place}-{spec['library']}-w{float(spec.get('wear', 0.0))}.png"


# --- cards ---------------------------------------------------------------------------------------------------------

def blank():
    return Image.new("RGB", (WIDTH, HEIGHT), GROUND)


def filled(picture, width, height):
    """`picture` scaled to cover width x height, centre-cropped."""
    scale = max(width / picture.width, height / picture.height)
    picture = picture.resize((round(picture.width * scale), round(picture.height * scale)), Image.LANCZOS)
    left, top = (picture.width - width) // 2, (picture.height - height) // 2
    return picture.crop((left, top, left + width, top + height))


def shaded_label(picture, text, size, pad):
    """`picture` with `text` low left over a soft dark shade."""
    width, height = picture.size
    band = int(height * 0.32)
    shade = Image.new("L", (width, height), 0)
    shade_draw = ImageDraw.Draw(shade)
    for row in range(height - band, height):
        shade_draw.line([(0, row), (width, row)], fill=int(190 * (row - (height - band)) / band))
    picture = Image.composite(Image.new("RGB", (width, height), (0, 0, 0)), picture, shade)
    ImageDraw.Draw(picture).text((pad, height - pad), text, font=font(size, True), fill=INK, anchor="ls")
    return picture


def heading(draw, text, left, top=70):
    draw.text((left, top), text, font=font(60, True), fill=INK)


def title_card():
    image = blank()
    draw = ImageDraw.Draw(image)
    draw.text((WIDTH / 2, 470), "SCORE", font=font(150, True), fill=INK, anchor="ms")
    draw.text((WIDTH / 2, 560), "Synthesising Complete, Owned, Responsive Environments for Simulation",
              font=font(40), fill=SOFT, anchor="ms")
    return image


def hex_colour(text):
    return tuple(int(text.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4))


def style_card(found, scenes):
    """Each place's concept, its palette's tokens as swatches below it; two by two."""
    image = blank()
    draw = ImageDraw.Draw(image)
    tile_w, tile_h, gap, strip = 740, 350, 40, 60
    left = (WIDTH - 2 * tile_w - gap) // 2
    heading(draw, "Style", left, 40)
    top = 140
    for index, (place, held) in enumerate(found["places"].items()):
        x = left + (index % 2) * (tile_w + gap)
        y = top + (index // 2) * (tile_h + strip + gap)
        concept = filled(Image.open(scenes / place / "concept.png").convert("RGB"), tile_w, tile_h)
        image.paste(shaded_label(concept, held["name"], 38, 22), (x, y))
        count = len(held["tokens"])
        side = (tile_w - (count - 1) * 8) / count
        for number, (_, colour) in enumerate(held["tokens"]):
            corner = x + number * (side + 8)
            draw.rounded_rectangle([corner, y + tile_h + 14, corner + side, y + tile_h + 14 + strip - 14],
                                   radius=8, fill=hex_colour(colour))
    return image


def on_ground(picture):
    """A transparent render laid on the card's ground."""
    laid = Image.new("RGBA", picture.size, GROUND + (255,))
    laid.alpha_composite(picture.convert("RGBA"))
    return laid.convert("RGB")


def surfaces_card(found, out):
    """Each place's library surfaces as swatch tiles in a row under its name, the places two by two."""
    image = blank()
    draw = ImageDraw.Draw(image)
    tile, gap, block_gap = 200, 12, 60
    block_w = SURFACES_A_PLACE * tile + (SURFACES_A_PLACE - 1) * gap
    left = (WIDTH - 2 * block_w - block_gap) // 2
    heading(draw, "Library surfaces", left, 40)
    for index, (place, held) in enumerate(found["places"].items()):
        x = left + (index % 2) * (block_w + block_gap)
        y = 230 + (index // 2) * (tile + 160)
        draw.text((x, y), held["name"], font=font(34, True), fill=INK)
        for number, shown in enumerate(held["surfaces"]):
            corner = x + number * (tile + gap)
            image.paste(filled(on_ground(Image.open(swatch_path(out, place, shown["spec"]))), tile, tile),
                        (corner, y + 54))
            draw.text((corner + tile / 2, y + 54 + tile + 34), shown["spec"]["recipe"].replace("_", " "),
                      font=font(24), fill=SOFT, anchor="ms")
    return image


def frame(film, at, path):
    """The film's frame at `at` seconds, saved to `path`, as a picture."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", str(film), "-frames:v", "1", str(path)],
                   check=True)
    return Image.open(path).convert("RGB")


def figure_panel(box):
    """A crop of the paper's Figure 1 (camp through SCORE's layers), its panel label left out."""
    return Image.open(FIGURE).convert("RGB").crop(box)


def side_by_side(left, right, width, height, gap=10):
    """Two pictures fitted into width x height on a light ground, an arrow between them."""
    ground = Image.new("RGB", (width, height), (228, 228, 226))
    arrow_w = 30
    half = (width - arrow_w - 2 * gap) // 2
    for index, picture in enumerate((left, right)):
        picture = picture.copy()
        picture.thumbnail((half, height - 2 * gap), Image.LANCZOS)
        x = gap + index * (half + arrow_w) + (half - picture.width) // 2
        ground.paste(picture, (x, (height - picture.height) // 2))
    middle_x, middle_y = width // 2, height // 2
    ImageDraw.Draw(ground).polygon([(middle_x - 9, middle_y - 11), (middle_x + 9, middle_y),
                                    (middle_x - 9, middle_y + 11)], fill=(90, 90, 92))
    return ground


def finish_picture(found, out, place, width, height):
    """The place's laid library surfaces (their swatches) above its palette's tokens."""
    ground = Image.new("RGB", (width, height), BOX)
    held = found["places"][place]
    strip, gap = 26, 6
    shown = held["surfaces"]
    tile_w = (width - (len(shown) - 1) * gap) // len(shown)
    for number, entry in enumerate(shown):
        swatch = on_ground(Image.open(swatch_path(out, place, entry["spec"])))
        ground.paste(filled(swatch, tile_w, height - strip - gap), (number * (tile_w + gap), 0))
    draw = ImageDraw.Draw(ground)
    tokens = held["tokens"]
    each = width / len(tokens)
    for number, (_, colour) in enumerate(tokens):
        draw.rectangle([round(number * each), height - strip, round((number + 1) * each) - 2, height - 1],
                       fill=hex_colour(colour))
    return ground


def environment_picture(environment, width, height):
    """The environment concept's record, the three things the creator locks, as short lines."""
    ground = Image.new("RGB", (width, height), (36, 40, 47))
    draw = ImageDraw.Draw(ground)
    rows = [("physics", ", ".join(body.title() for body in environment["bodies"])),
            ("setting", f"{environment['sites']} sites on them"),
            ("style", environment["style"])]
    size = 22
    while max(draw.textlength(value, font=font(size, True)) for _, value in rows) > width - 32:
        size -= 1
    for number, (key, value) in enumerate(rows):
        y = 8 + number * 52
        draw.text((16, y), key, font=font(20), fill=ACCENT)
        draw.text((16, y + 23), value, font=font(size, True), fill=INK)
    return ground


def step_pictures(found, options, out, width, height):
    """{step: its picture}, each from that step's real output for FRAMEWORK_PLACE."""
    place = FRAMEWORK_PLACE
    films = options.films
    door_picture, door_mesh = (figure_panel(box) for box in FIGURE_PANELS["trellis"])
    sim_body = frame(films / f"{place}.mp4", FRAMEWORK_FRAMES["sim body"], out / "framework-sim-body.png")
    pictures = {
        "concept": environment_picture(found["environment"], width, height),
        "place concept": Image.open(options.scenes / place / "concept.png").convert("RGB"),
        "inventory": figure_panel(FIGURE_PANELS["inventory"]),
        "layout": Image.open(options.scenes / place / "render/concept-look.png").convert("RGB"),
        "missing": side_by_side(door_picture, door_mesh, width, height),
        "finish": finish_picture(found, out, place, width, height),
        "colliders": figure_panel(FIGURE_PANELS["colliders"]),
        "people": frame(films / f"{place}.mp4", FRAMEWORK_FRAMES["people"], out / "framework-people.png"),
        "sim body": sim_body.crop(SIM_BODY_CROP),
        "stage": frame(films / f"{place}-short-peel.mp4", FRAMEWORK_FRAMES["stage"], out / "framework-stage.png"),
    }
    return {step: filled(picture, width, height) for step, picture in pictures.items()}


def arrow(draw, points, colour, width=5, dashed=False):
    """A line through `points`, an arrow head at its last point."""
    for start, end in zip(points, points[1:]):
        if not dashed:
            draw.line([start, end], fill=colour, width=width)
            continue
        length = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        for at in range(0, length, 16):
            stop = min(at + 9, length)
            draw.line([(start[0] + (end[0] - start[0]) * at / length, start[1] + (end[1] - start[1]) * at / length),
                       (start[0] + (end[0] - start[0]) * stop / length,
                        start[1] + (end[1] - start[1]) * stop / length)], fill=colour, width=width)
    (from_x, from_y), (to_x, to_y) = points[-2], points[-1]
    along_x, along_y = (to_x > from_x) - (to_x < from_x), (to_y > from_y) - (to_y < from_y)
    across_x, across_y = -along_y, along_x
    head, half = 18, 11
    draw.polygon([(to_x, to_y), (to_x - along_x * head + across_x * half, to_y - along_y * head + across_y * half),
                  (to_x - along_x * head - across_x * half, to_y - along_y * head - across_y * half)], fill=colour)


def framework_card(found, options, out):
    """SCORE's whole route as the paper's Method gives it: ten steps in two rows (the second read right to left), each
    with its real output for one place, and score_lib as the band the steps draw from."""
    image = blank()
    draw = ImageDraw.Draw(image)
    left, box_w, gap, box_h, pad = 60, 308, 55, 318, 12
    picture_w, picture_h = box_w - 2 * pad, 164
    rows_top, band_h, band_gap = 170, 104, 46
    band_top = rows_top + box_h + band_gap
    second_top = band_top + band_h + band_gap
    heading(draw, "From concept to an owned stage", left, 40)
    pictures = step_pictures(found, options, out, picture_w, picture_h)
    corners = []
    for number, (step, title, under) in enumerate(FRAMEWORK):
        column = number if number < 5 else 9 - number
        x, y = left + column * (box_w + gap), rows_top if number < 5 else second_top
        corners.append((x, y))
        draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=14, fill=BOX, outline=EDGE, width=2)
        image.paste(pictures[step], (x + pad, y + pad))
        title_y = y + pad + picture_h + 16
        draw.ellipse([x + pad, title_y, x + pad + 36, title_y + 36], fill=ACCENT)
        draw.text((x + pad + 18, title_y + 18), str(number + 1), font=font(22 if number < 9 else 18, True),
                  fill=GROUND, anchor="mm")
        draw.text((x + pad + 46, title_y + 1), title, font=font(27, True), fill=INK)
        for line_number, line in enumerate(under):
            draw.text((x + pad + 4, y + pad + picture_h + 60 + line_number * 30), line, font=font(23), fill=SOFT)
    for number in range(9):
        (x, y), (next_x, next_y) = corners[number], corners[number + 1]
        if number == 4:  # the turn: out of the last box of the first row, down the right margin, into the second row
            out_x = x + box_w + 30
            arrow(draw, [(x + box_w + 6, y + box_h // 2), (out_x, y + box_h // 2), (out_x, next_y + box_h // 2),
                         (x + box_w + 6, next_y + box_h // 2)], ACCENT)
        elif number < 4:
            arrow(draw, [(x + box_w + 6, y + box_h // 2), (next_x - 6, y + box_h // 2)], ACCENT)
        else:
            arrow(draw, [(x - 6, y + box_h // 2), (next_x + box_w + 6, y + box_h // 2)], ACCENT)
    right = left + 5 * box_w + 4 * gap
    draw.rounded_rectangle([left, band_top, right, band_top + band_h], radius=14, fill=LIBRARY, outline=ACCENT, width=2)
    draw.text((left + 26, band_top + 16), "score_lib", font=font(36, True), fill=INK)
    draw.text((left + 26, band_top + 64), "the shared library: pieces, surfaces, palettes, people",
              font=font(24), fill=INK)
    for step in FRAMEWORK_DRAWS:
        number = [entry[0] for entry in FRAMEWORK].index(step)
        x, y = corners[number]
        middle = x + box_w // 2
        if number < 5:
            arrow(draw, [(middle, band_top - 4), (middle, y + box_h + 6)], ACCENT, 4, dashed=True)
        else:
            arrow(draw, [(middle, band_top + band_h + 4), (middle, y - 6)], ACCENT, 4, dashed=True)
    return image


def cards(found, options, out):
    made = {"title": title_card(), "framework": framework_card(found, options, out),
            "style": style_card(found, options.scenes), "surfaces": surfaces_card(found, out)}
    for name, picture in made.items():
        picture.save(out / f"card-{name}.png")
    return list(made)


# --- the clip ------------------------------------------------------------------------------------------------------

def clip(names, out):
    """The cards one after another, each faded in from and out to the ground: <out>/opening.mp4, and plan.json."""
    arguments, chains, plan = ["ffmpeg", "-v", "error", "-y"], [], []
    for index, name in enumerate(names):
        seconds = SECONDS[name]
        arguments += ["-loop", "1", "-framerate", str(RATE), "-t", f"{seconds}", "-i", str(out / f"card-{name}.png")]
        chains.append(f"[{index}:v]format=yuv420p,fade=t=in:st=0:d={FADE},"
                      f"fade=t=out:st={seconds - FADE}:d={FADE}[c{index}]")
        plan.append({"card": name, "path": str(out / f"card-{name}.png"), "seconds": seconds})
    joined = "".join(f"[c{index}]" for index in range(len(names)))
    filters = ";".join(chains) + f";{joined}concat=n={len(names)}:v=1:a=0[v]"
    subprocess.run(arguments + ["-filter_complex", filters, "-map", "[v]", "-r", str(RATE), "-c:v", "libx264",
                                "-crf", "16", "-pix_fmt", "yuv420p", str(out / "opening.mp4")], check=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=1))
    return plan


def arguments(given=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--scenes", type=pathlib.Path, required=True)
    parser.add_argument("--films", type=pathlib.Path, required=True)
    parser.add_argument("--places", default="camp,campgrounds,stairwell,street")
    parser.add_argument("--who", default="opening.py", help="the session asking, for the cluster's runs")
    parser.add_argument("--step", choices=["facts", "swatches", "cards", "clip"])
    options = parser.parse_args(given)
    options.places = options.places.split(",")
    return options


def main():
    options = arguments()
    out = options.out
    out.mkdir(parents=True, exist_ok=True)
    steps = [options.step] if options.step else ["facts", "swatches", "cards", "clip"]
    if "facts" in steps:
        (out / "facts.json").write_text(json.dumps(facts(options), indent=1))
    found = json.loads((out / "facts.json").read_text())
    if "swatches" in steps:
        swatches(found, out, options.who)
    if "cards" in steps:
        cards(found, options, out)
    if "clip" in steps:
        plan = clip(list(SECONDS), out)
        print(json.dumps({"opening": str(out / "opening.mp4"), "cards": plan}))


if __name__ == "__main__":
    main()
