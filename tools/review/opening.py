"""The demo film's opening (#128): the title, then the environment's style and its physics shown, not told, each read
from the places' own records; the cards and their clip, ready to be joined before the place films.

    .venv/bin/python tools/review/opening.py <out> --scenes <folder> --films <folder> \
        --sim-body camp=<sim_bodies.json> --sim-body campgrounds=<...> ... [--places camp,campgrounds,stairwell,street]
        [--settle camp:table,mug_t0,pizza] [--sim-body-at stairwell=17] [--step facts|swatches|settle|cards|clip]

<scenes>/<place>/ holds what the place's stage folder holds: concept.png, palette.json (its scene's surface library:
its tokens), scene.usda (the stage, whose Looks carry each laid library surface's resolved recipe,
`score:recipe:spec`), ready-settle.json and ready-settle.npz (the settle check's record and job). <films>/<place>.mp4
is the place's film (its sim body shown near its end). Each --sim-body is the place's sim body record (sim_bodies.json,
or the run's job.json), which names the gravity the people were solved under.

The cards (owner, 2026-11-19: "the only actual only text intro needs to be title ... style u need visualized aswell,
and the difference in grafity, is not true"):
- **title**: SCORE and its long name, the one text card.
- **style**: each place's locked concept with its scene palette's tokens as swatches below it, the tokens its laid
  surfaces use first.
- **surfaces**: each place's most used library surfaces (by the prims bound to them; no glow, one per recipe), drawn
  by the library's own swatch renderer (tools/props/library/inside/swatch.py) in the place's resolved recipe.
- **physics**: what was applied, nothing more: the settle check as MuJoCo saw it (one place's objects' hulls at rest
  on what is near them, ../blender/inside/settle_view.py) under the settle's one gravity (settle_mujoco.GRAVITY, the
  same in every place, read from its source), beside each place's sim body under the gravity its record names.

Blender runs on the cluster's cards (the swatches through tools/cloud/library_bake.py, the settle view through
tools/cloud/blender_cloud.py; set SCORE_CLOUD=k8s and the cluster's SCORE_K8S_*, and the run's SCORE_SPEND_TICKET
with PROPS_HOME the home holding its yes). Every step writes into <out> and the next reads it there, so a step can be
run again alone; `facts.json` holds every number the cards show.
"""
import argparse
import ast
import collections
import json
import os
import pathlib
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = pathlib.Path(__file__).resolve().parents[2]
SETTLE_SCRIPT = REPO / "score/stages/place_build/ready/settle_mujoco.py"  # imports MuJoCo: read, never imported

WIDTH, HEIGHT = 1920, 1080
RATE = 24
GROUND = (17, 19, 23)
INK = (237, 235, 230)
SOFT = (150, 152, 156)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAMES = {"camp": "Camp", "campgrounds": "Campgrounds", "stairwell": "Stairwell", "street": "Street"}
SECONDS = {"title": 4.0, "style": 7.0, "surfaces": 7.0, "physics": 8.0}
FADE = 0.5
SURFACES_A_PLACE = 4
TOKENS_A_PLACE = 12
UNSHOWN_RECIPES = {"glowing", "clear_glass", "glass"}  # light or see-through: a swatch shows neither
SWATCH = {"size": 360, "samples": 48, "seed": 7}
SETTLE = {"size": [1100, 860], "samples": 96, "reach": 0.5}
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
CLOUD_PYTHON = PROPS_HOME / "env/bin/python"
CLASSES = "gpu-24gb"  # an L4: Cycles on its card
SIM_BODY_FROM_END = 3.0  # seconds before a film's end its sim body is shown (every place's film ends on it)


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


def sim_body_gravity(record):
    """(the body the people stand on, its gravity m/s²) from a sim body record or its run's job; None when it says
    neither."""
    found = json.loads(pathlib.Path(record).read_text())
    if "gravity" not in found:
        return None
    return found.get("on"), float(found["gravity"])


def settle_gravity(script=SETTLE_SCRIPT):
    """The settle check's GRAVITY (m/s²), read from its script's source: it imports MuJoCo, which only its own
    environment has."""
    for node in ast.parse(script.read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "GRAVITY" for target in node.targets):
            return float(ast.literal_eval(node.value))
    raise SystemExit(f"{script} sets no GRAVITY")


def facts(options):
    """Every number and name the cards show, from the records."""
    places = {}
    for place in options.places:
        folder = options.scenes / place
        stage = (folder / "scene.usda").read_text()
        laid = laid_surfaces(stage, place)
        settled = json.loads((folder / "ready-settle.json").read_text())
        moved = [entry["moved"] for entry in settled["objects"].values()]
        places[place] = {
            "name": NAMES.get(place, place.replace("_", " ").title()),
            "tokens": palette_tokens(json.loads((folder / "palette.json").read_text())["tokens"], laid),
            "surfaces": shown_surfaces(laid),
            "settle": {"engine": settled["engine"], "objects": len(moved), "most_moved_m": max(moved, default=0.0)},
            "sim_body": sim_body_gravity(options.sim_body[place]) if place in options.sim_body else None,
        }
    return {"settle_gravity": settle_gravity(), "places": places}


# --- Blender steps, on the cluster --------------------------------------------------------------------------------

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


def settle_view(options, out, who):
    """The settle check of one place's chosen objects, drawn: <out>/settle.png."""
    place, objects = options.settle.split(":")
    npz = options.scenes / place / "ready-settle.npz"
    view = out / "settle_view.json"
    view.write_text(json.dumps({"npz": str(npz), "objects": objects.split(","), "out": str(out / "settle.png"),
                                **SETTLE}, indent=1))
    job = out / "settle-job.json"
    job.write_text(json.dumps({"script": "tools/blender/inside/settle_view.py", "args": [str(view)],
                               "inputs": [str(view), str(npz)], "outputs": [str(out / "settle.png")], "minutes": 5}))
    cloud("blender_cloud.py", [job], who, "--detach")


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


def film_frame(film, out, place, at=None):
    """The film's frame at `at` seconds, else SIM_BODY_FROM_END seconds before its end (its sim body), as a picture."""
    if at is None:
        length = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                                "csv=p=0", str(film)]).decode())
        at = max(0.0, length - SIM_BODY_FROM_END)
    path = out / f"sim-body-{place}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i",
                    str(film), "-frames:v", "1", str(path)], check=True)
    return Image.open(path).convert("RGB")


def gravity_words(gravity):
    return f"{gravity:.3f}".rstrip("0").rstrip(".") + " m/s²"


def physics_card(found, films, out, at=None):
    """The settle check at its one gravity, beside each place's sim body at the gravity it was solved under."""
    image = blank()
    draw = ImageDraw.Draw(image)
    left, top = 90, 260
    tile_w, tile_h, gap = 460, 259, 20
    right = WIDTH - left - 2 * tile_w - gap
    heading(draw, "Physics", left, 40)
    settle = filled(on_ground(Image.open(out / "settle.png")), right - 50 - left, 2 * tile_h + gap)
    image.paste(settle, (left, top))
    below = top + 2 * tile_h + gap + 40
    draw.text((left, top - 50), "Objects settled · MuJoCo", font=font(34, True), fill=INK)
    draw.text((left, below), f"{gravity_words(found['settle_gravity'])} in every place", font=font(34), fill=INK)
    draw.text((right, top - 50), "Sim bodies", font=font(34, True), fill=INK)
    for index, (place, held) in enumerate(found["places"].items()):
        x = right + (index % 2) * (tile_w + gap)
        y = top + (index // 2) * (tile_h + gap)
        picture = filled(film_frame(films / f"{place}.mp4", out, place, (at or {}).get(place)), tile_w, tile_h)
        if held["sim_body"] is None:
            raise SystemExit(f"{place}: its sim body record names no gravity")
        body, gravity = held["sim_body"]
        picture = shaded_label(picture, held["name"], 28, 16)
        ImageDraw.Draw(picture).text((16, tile_h - 52), f"{(body or '').title()} {gravity_words(gravity)}",
                                     font=font(26), fill=INK, anchor="ls")
        image.paste(picture, (x, y))
    return image


def cards(found, options, out):
    made = {"title": title_card(), "style": style_card(found, options.scenes), "surfaces": surfaces_card(found, out),
            "physics": physics_card(found, options.films, out, options.sim_body_at)}
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
    parser.add_argument("--sim-body", action="append", default=[], help="place=record")
    parser.add_argument("--sim-body-at", action="append", default=[],
                        help="place=seconds: the film's moment its sim body is shown (default: near its end)")
    parser.add_argument("--places", default="camp,campgrounds,stairwell,street")
    parser.add_argument("--settle", default="camp:table,mug_t0,mug_t1,mug_t2,pizza,stool0,stool1,stool2,stool3")
    parser.add_argument("--who", default="opening.py", help="the session asking, for the cluster's runs")
    parser.add_argument("--step", choices=["facts", "swatches", "settle", "cards", "clip"])
    options = parser.parse_args(given)
    options.places = options.places.split(",")
    options.sim_body = dict(entry.split("=", 1) for entry in options.sim_body)
    options.sim_body_at = {place: float(seconds) for place, seconds in
                           (entry.split("=", 1) for entry in options.sim_body_at)}
    return options


def main():
    options = arguments()
    out = options.out
    out.mkdir(parents=True, exist_ok=True)
    steps = [options.step] if options.step else ["facts", "swatches", "settle", "cards", "clip"]
    if "facts" in steps:
        (out / "facts.json").write_text(json.dumps(facts(options), indent=1))
    found = json.loads((out / "facts.json").read_text())
    if "swatches" in steps:
        swatches(found, out, options.who)
    if "settle" in steps:
        settle_view(options, out, options.who)
    if "cards" in steps:
        cards(found, options, out)
    if "clip" in steps:
        plan = clip(list(SECONDS), out)
        print(json.dumps({"opening": str(out / "opening.mp4"), "cards": plan}))


if __name__ == "__main__":
    main()
