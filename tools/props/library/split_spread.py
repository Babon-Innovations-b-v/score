"""How consistent a part splitter is across a world's models (job splits, 2026-10-10, after the owner found the split
better but inconsistent across models on 10-09): every model's split scored against its own close-up's finishes with
split_compare.py's scores, the spread over the models reported and the worst named, not only the mean. Measure only:
nothing here writes a take's labels, its stored parts or a place's stage.

    python tools/props/library/split_spread.py finishes <run folder> <takes.json>
    python tools/props/library/split_spread.py ask <run folder> <questions folder>
    python tools/props/library/split_spread.py answers <run folder> <answers folder>
    python tools/props/library/split_spread.py partcrafter <run folder> [<take> ...]
    python tools/props/library/split_spread.py geosam2 <run folder> [<take> ...]
    python tools/props/library/split_spread.py scores <run folder> [<take> ...]
    python tools/props/library/split_spread.py table <run folder>

The run folder is split_compare.py's (its `inputs` wrote each <take>/view.npz from the close-up's SAM 2.1 masks;
../cloud/meshparts.py and its `labels` gave <take>/parts_<method>.npy). <takes.json> names, per take, its place, its
kind, what the object is in words, the labels.json its paint came from and its PartCrafter folder (or null); it is
kept as <run>/takes.json.

- `finishes`: a take whose regions painting (labels.json `regions`) cut the close-up into these same regions (same
  count, each region's share within SHARE_SLACK) takes that painting's materials as its finishes (<take>/finishes.json);
  any other take is left for the judge.
- `ask` and `answers`: the judge names each region's material as the regions painting does (labels.paint_by_regions'
  questions and labels.region_materials), for the takes `finishes` left.
- `partcrafter`: PartCrafter's split laid on the raw model as the repaint lays it, where its folder is kept.
- `geosam2`: GeoSAM2's split brought back (<take>/down/geosam2.npz) laid on the raw model and cleaned as
  split_compare.py's `labels` does, for the takes not laid yet.
- `scores`: each take's every split scored (<run>/spread.json); `table`: the spread over the models (<run>/spread.txt).
"""
import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import labels  # noqa: E402
import part_judge  # noqa: E402
import regions  # noqa: E402
import split_compare  # noqa: E402

# A region's share of the close-up (labels.json rounds it to three places) may differ this much between the regions
# painting's masks and these and still be the same region.
SHARE_SLACK = 0.002
METHODS = ("geosam2_guided", "partcrafter")
# The table's worst list: this many models, lowest share of finishes owned first.
WORST = 12


def takes_of(run):
    return json.loads((run / "takes.json").read_text())


def view_of(run, take):
    return dict(np.load(run / take / "view.npz"))


def region_shares(pixels):
    """Each region's share of the close-up's object pixels."""
    inside = pixels >= 0
    return np.bincount(pixels[inside], minlength=int(pixels.max()) + 1) / inside.sum()


def same_regions(painted, pixels):
    """Whether the regions painting's regions (labels.json `regions`) are these pixels' regions."""
    shares = region_shares(pixels)
    return len(painted) == len(shares) and all(abs(entry["share"] - share) <= SHARE_SLACK
                                               for entry, share in zip(painted, shares))


def write_finishes(run, take, materials, source):
    """<take>/finishes.json: each region's material and where the materials came from."""
    (run / take / "finishes.json").write_text(json.dumps({"materials": materials, "source": source}, indent=1))


def finishes_from_labels(run, take, entry):
    """The take's finishes from its regions painting, when that painting's regions are these; whether it had them."""
    painted = json.loads(pathlib.Path(entry["labels"]).read_text()).get("regions") or []
    if not painted or not same_regions(painted, view_of(run, take)["pixels"]):
        return False
    write_finishes(run, take, [region["material"] for region in painted], entry["labels"])
    return True


def materials_of(entry):
    """The materials the take may take (labels.allowed_materials for its place and kind)."""
    return labels.allowed_materials(entry["place"], entry["kind"], [])


def ask(run, folder):
    """The judge's questions for every region of the takes with no finishes yet; the takes asked."""
    asked = []
    for take, entry in takes_of(run).items():
        if (run / take / "finishes.json").exists() or not (run / take / "view.npz").exists():
            continue
        pixels = view_of(run, take)["pixels"]
        part_judge.write_questions(folder, take, split_compare.picture(take), pixels,
                                   list(range(int(pixels.max()) + 1)), entry["object"], materials_of(entry))
        asked.append(take)
    return asked


def answered(run, take, entry, folder):
    """The take's region materials from the judge's answers, chosen as labels.paint_by_regions chooses them."""
    pixels = view_of(run, take)["pixels"]
    materials = materials_of(entry)
    colours = labels.picture_lab(split_compare.picture(take))
    count = int(pixels.max()) + 1
    judged = part_judge.judged(folder, take, count, list(materials))
    paint, _ = labels.region_materials(regions.medians(pixels, colours), regions.vivid(pixels, colours), judged,
                                       materials)
    names = list(materials)
    return [names[index] for index in paint]


def lay_partcrafter(run, take, entry):
    """PartCrafter's split of the take laid on its raw model (<take>/parts_partcrafter.npy) and its registration."""
    mesh = split_compare.raw_model(take)
    part_of, report = split_compare.partcrafter_parts(mesh, take, pathlib.Path(entry["parts"]))
    (run / take).mkdir(parents=True, exist_ok=True)
    np.save(run / take / "parts_partcrafter.npy", part_of.astype(np.int32))
    return report


def lay_geosam2(run, take):
    """GeoSAM2's split of the take on its raw model's faces, cleaned (<take>/parts_geosam2_guided.npy)."""
    mesh = split_compare.raw_model(take)
    part_of = split_compare.geosam2_parts(mesh, run / take, view_of(run, take))
    np.save(run / take / "parts_geosam2_guided.npy", split_compare.cleaned(mesh, part_of).astype(np.int32))


def finish_indices(run, take):
    """Each region's finish as an index into the take's finish names (regions of one material are one finish)."""
    materials = json.loads((run / take / "finishes.json").read_text())["materials"]
    names = sorted(set(materials))
    return np.array([names.index(name) for name in materials]), names


def score_take(run, take):
    """Every split of the take scored against its close-up (split_page.scores_of), with its finish names."""
    import split_page
    mesh = split_compare.raw_model(take)
    view = view_of(run, take)
    finish_of_region, names = finish_indices(run, take)
    front = split_page.views(take, mesh)["front"][0]
    found = {"finishes": names, "methods": {}}
    for method in METHODS:
        path = run / take / f"parts_{method}.npy"
        if path.exists():
            found["methods"][method] = split_page.scores_of(mesh, np.load(path), front, view, finish_of_region)
    return found


def owned_share(scores):
    """The share of the close-up's counted finishes that get parts of their own."""
    counted = len(scores["owned"]) + len(scores["missed"])
    return len(scores["owned"]) / counted if counted else None


def spread_line(name, values):
    """One line of a measure's spread over the models: count, mean, deviation, min, quartiles, max."""
    values = np.array([value for value in values if value is not None], dtype=float)
    if not len(values):
        return f"  {name:<22} none"
    low, quarter, middle, upper, high = np.percentile(values, [0, 25, 50, 75, 100])
    return (f"  {name:<22} n={len(values):<4} mean {values.mean():.3f}  sd {values.std():.3f}  min {low:.3f}  "
            f"q1 {quarter:.3f}  median {middle:.3f}  q3 {upper:.3f}  max {high:.3f}")


def table(run):
    """The spread of each method's scores over the models, the worst models named, and every model's row."""
    found = json.loads((run / "spread.json").read_text())
    takes = takes_of(run)
    lines = []
    for method in METHODS:
        rows = {take: entry["methods"][method] for take, entry in found.items() if method in entry["methods"]}
        several = {take: scores for take, scores in rows.items() if len(found[take]["finishes"]) > 1}
        lines += [f"{method}: {len(rows)} models scored, {len(several)} with two finishes or more (spread over these)",
                  spread_line("finishes owned", [owned_share(scores) for scores in several.values()]),
                  spread_line("parts pure", [scores["pure"] for scores in several.values()]),
                  spread_line("regions whole", [scores["whole"] for scores in several.values()]),
                  spread_line("needless cuts", [scores["needless"] for scores in several.values()]),
                  spread_line("parts", [scores["parts"] for scores in several.values()]),
                  f"  owned under half: {sum(owned_share(scores) < 0.5 for scores in several.values())} models; "
                  f"none owned: {sum(not scores['owned'] for scores in several.values())}",
                  "  worst (owned, pure):"]
        worst = sorted(several, key=lambda take: (owned_share(several[take]), several[take]["pure"]))[:WORST]
        lines += [f"    {take:<26} {owned_share(several[take]):.2f}  {several[take]['pure']:.2f}  "
                  f"{','.join(takes[take]['places'])}" for take in worst]
        lines.append("")
    lines.append(f"{'take':<26} {'places':<26} fin  geosam2 owned/pure/cuts/parts   partcrafter owned/pure/cuts/parts")
    for take in sorted(found):
        cells = []
        for method in METHODS:
            scores = found[take]["methods"].get(method)
            cells.append(f"{len(scores['owned'])}/{len(scores['owned']) + len(scores['missed'])} {scores['pure']:.2f} "
                         f"{scores['needless']:.2f} {scores['parts']:>3}" if scores else "-")
        lines.append(f"{take:<26} {','.join(takes[take]['places']):<26} {len(found[take]['finishes']):>3}  "
                     f"{cells[0]:<30} {cells[1]}")
    (run / "spread.txt").write_text("\n".join(lines) + "\n")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("finishes", "ask", "answers", "partcrafter", "geosam2", "scores", "table"))
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("more", nargs="*", help="finishes: takes.json; ask, answers: the judge's folder; else takes")
    arguments = parser.parse_args()
    run = arguments.run
    if arguments.step == "finishes":
        (run / "takes.json").write_text(pathlib.Path(arguments.more[0]).read_text())
        left = [take for take, entry in takes_of(run).items() if (run / take / "view.npz").exists()
                and not finishes_from_labels(run, take, entry)]
        print(f"finishes from labels: {len(takes_of(run)) - len(left)}; left for the judge: {len(left)}")
        (run / "for_judge.json").write_text(json.dumps(left))
    elif arguments.step == "ask":
        print(f"asked: {len(ask(run, pathlib.Path(arguments.more[0])))} takes")
    elif arguments.step == "answers":
        folder = pathlib.Path(arguments.more[0])
        for take in json.loads((run / "for_judge.json").read_text()):
            write_finishes(run, take, answered(run, take, takes_of(run)[take], folder), str(folder))
    elif arguments.step == "partcrafter":
        for take in arguments.more or [take for take, entry in takes_of(run).items() if entry.get("parts")]:
            print(take, json.dumps(lay_partcrafter(run, take, takes_of(run)[take]), default=str), flush=True)
    elif arguments.step == "geosam2":
        for take in arguments.more or sorted(path.parent.parent.name for path in run.glob("*/down/geosam2.npz")
                                             if not (path.parent.parent / "parts_geosam2_guided.npy").exists()):
            lay_geosam2(run, take)
            print(take, flush=True)
    elif arguments.step == "scores":
        stored = run / "spread.json"
        found = json.loads(stored.read_text()) if stored.exists() else {}
        for take in arguments.more or sorted(path.parent.name for path in run.glob("*/finishes.json")):
            found[take] = score_take(run, take)
            stored.write_text(json.dumps(found, indent=1))
            print(take, flush=True)
    else:
        print("\n".join(table(run)[:40]))


if __name__ == "__main__":
    main()
