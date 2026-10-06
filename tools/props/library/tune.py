"""Tune the library's materials to the owner's kept reference pictures: render, compare, adjust (job robust-exp,
2026-10-06; the coordinator: record each recipe's tuning rounds and its match score per round).

    ~/.farm-factory-props/env/bin/python tools/props/library/tune.py <work folder> [--rounds 4] [--write]

Each library material that names a `reference` in place.json (a picture under WORK and a box on it, a patch of the
same kind of surface in one of the owner's kept pictures) is rendered close up on the swatch piece (inside/swatch.py,
one cloud run a round, ../cloud/library_bake.py) and scored against its patch on what the material can change and
the palette cannot: how much the surface's lightness varies, how much fine detail it has and how much of it shines.
Colour is not scored: it is locked to the palette's token. A round turns one setting (roughness, relief height,
relief size) up and down and keeps the best; rounds go round the settings. The report (<work>/tune.json) holds
every round's settings and score; --write puts the winners into place.json.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import library  # noqa: E402
from paths import WORK  # noqa: E402

# Every render is a cloud run (one card a round): no bake or render runs on this PC (2026-10-06).
CLOUD = HERE.parent / "cloud" / "library_bake.py"
# The settings a round may turn, and how: multiplied for sizes, added for roughness; then held within bounds. The
# relief bounds are the ink look's, not the photos': the first unbounded run (2026-10-06) matched the references'
# photo grain by turning every paint into crinkled hammer-tone, which reads as mess under the ink pass. Relief finer
# than 1 cm cannot be baked cleanly at 1024 px/m either.
STEPS = {"roughness": ("add", 0.12, 0.05, 0.95), "bump": ("times", 1.8, 0.00002, 0.0006),
         "bump_size": ("times", 1.8, 0.01, 0.2)}
# The flat part of the swatch's close view (shares of the picture: left, top, right, bottom), compared with the patch.
FLAT = (0.45, 0.15, 0.95, 0.85)
SIDE = 96
WEAR = 0.4


def lightness(picture):
    """A picture's lightness as a SIDE x SIDE array, from sRGB."""
    rgb = np.asarray(picture.convert("RGB").resize((SIDE, SIDE)), dtype=np.float64) / 255
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def features(light):
    """What the score compares: relative contrast, fine-detail share and shine share of a lightness array."""
    mean = max(float(light.mean()), 1e-3)
    relative = light / mean
    second = np.abs(4 * relative[1:-1, 1:-1] - relative[:-2, 1:-1] - relative[2:, 1:-1] - relative[1:-1, :-2]
                    - relative[1:-1, 2:])
    return np.array([float(relative.std()), float((second > 0.04).mean()),
                     float((relative > 1.3 * np.median(relative)).mean())])


def match(swatch_features, reference_features):
    """1 for the same surface character, toward 0 as contrast, detail and shine part ways."""
    gaps = np.abs(swatch_features - reference_features) / (np.abs(swatch_features) + np.abs(reference_features) + 1e-3)
    return float(1.0 - gaps.mean())


def reference_features(reference):
    """The features of a material's reference patch (a picture under WORK, a box on it)."""
    picture = Image.open(str(reference["picture"]).replace("WORK", str(WORK), 1))
    return features(lightness(picture.crop(tuple(reference["box"]))))


def swatch_features(path):
    picture = Image.open(path).convert("RGB")
    width, height = picture.size
    box = (int(FLAT[0] * width), int(FLAT[1] * height), int(FLAT[2] * width), int(FLAT[3] * height))
    return features(lightness(picture.crop(box)))


def turned(spec, setting, direction):
    """A copy of a spec with one setting turned one step up (+1) or down (-1), within its bounds."""
    how, step, low, high = STEPS[setting]
    value = spec[setting] + direction * step if how == "add" else spec[setting] * step ** direction
    return dict(spec, **{setting: min(high, max(low, value))})


def render(folder, candidates):
    """Every candidate spec close up at the working wear, in one cloud run."""
    job = {"script": "swatch.py", "out": str(folder), "materials": candidates, "wears": [WEAR], "dirt": 0.4,
           "seed": 3, "size": 256, "samples": 24, "views": ["-close"], "settings": False}
    path = folder / "job.json"
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job))
    subprocess.run([sys.executable, str(CLOUD), str(path), "--who", "tune.py"], check=True,
                   stdout=subprocess.DEVNULL)


def tune(work, rounds):
    """Round by round, each material's best settings and score; the report."""
    specs = {name: spec for name, spec in library.library_specs().items() if spec.get("reference")}
    targets = {name: reference_features(spec["reference"]) for name, spec in specs.items()}
    order = list(STEPS)
    report = {name: [] for name in specs}
    for number in range(rounds + 1):
        setting = order[(number - 1) % len(order)] if number else None
        candidates = {}
        for name, spec in specs.items():
            candidates[f"{name}@0"] = spec
            if setting:
                candidates[f"{name}@up"] = turned(spec, setting, 1)
                candidates[f"{name}@down"] = turned(spec, setting, -1)
        folder = work / f"round{number}"
        render(folder, candidates)
        for name in specs:
            scored = {tag: match(swatch_features(folder / f"{name}@{tag}-w{WEAR}-close.png"), targets[name])
                      for tag in ("0", "up", "down") if f"{name}@{tag}" in candidates}
            best = max(scored, key=scored.get)
            specs[name] = candidates[f"{name}@{best}"]
            report[name].append({"round": number, "turned": setting, "scores": {tag: round(score, 4) for tag, score
                                                                                  in scored.items()},
                                 "kept": best, "score": round(scored[best], 4),
                                 "settings": {key: specs[name][key] for key in STEPS}})
            print(f"round {number} {name}: {setting or 'start'} -> {best} {scored[best]:.3f}", flush=True)
    (work / "tune.json").write_text(json.dumps(report, indent=1))
    return specs


def write_back(specs):
    """Put the tuned settings into the theme's library in place.json."""
    places = json.loads(library.PLACES.read_text())
    materials = places["shared"]["theme"]["library"]["materials"]
    for name, spec in specs.items():
        for key in STEPS:
            materials[name][key] = round(float(spec[key]), 5)
    library.PLACES.write_text(json.dumps(places, indent="\t", ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=pathlib.Path)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args()
    specs = tune(arguments.work, arguments.rounds)
    if arguments.write:
        write_back(specs)


if __name__ == "__main__":
    main()
