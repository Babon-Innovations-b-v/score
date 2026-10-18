"""Run the materials checks over places and write what they found, with pictures:

    .venv/bin/python -m score.stages.complete.materials [--place P ...] [--out FOLDER] [--judge-only]

For each place, <out>/<place>/: evidence.json (measure.py), findings.json ({"place", "answer", "reason", "outputs":
{node: the output judged}, "findings": [{"rule", "prim", "sentence", "picture", ...}]}) and
marks/<place>-<rule>-<n>.png, a picture a finding; then <out>/summary.json and <out>/contact_sheet.png. The accepted
assemblies are linked under <out>/linked/ (read-only links to the store's files). `--judge-only` judges evidence
measured before. The environment's kit (texel.py) is read from every place's evidence in <out>, so a run of a few places
judges them as a run of all would. The default out is WORK/checks/materials, where the cockpit reads it. Prints one
line a place and one summary line.
"""
import argparse
import json
import pathlib

from PIL import Image, ImageDraw

from score.stages.complete.materials import assets, borders, judge, measure, meshes, pictures, texel
from score.store import PROPS_HOME, Store

OUT = PROPS_HOME / "work/checks/materials"
FINDINGS = "findings.json"
THUMB = 260


def kit_sample(evidences, reference):
    """(linked folder, model, density) of the code-built kit piece whose density lies nearest `reference`."""
    found = [(abs(entry["px_per_m"] - reference), evidence["linked"], entry["model"], entry["px_per_m"])
             for evidence in evidences for entry in evidence["objects"] if texel.is_kit(entry)]
    return min(found)[1:] if found else None


def drawn_model(linked, model):
    """A model's drawn meshes from a linked assembly, none when it has no asset."""
    asset = assets.asset_file(linked, model)
    return meshes.drawn(asset) if asset else []


def soft_picture(item, evidence, sample):
    """A soft-texture finding's picture."""
    linked, kit_model, kit_density = sample
    return pictures.soft_texture(item, drawn_model(evidence["linked"], item["model"]), kit_model,
                                 drawn_model(linked, kit_model), kit_density)


def kit_picture(item, evidence):
    """A kit-age finding's picture."""
    density = {entry["model"]: entry["px_per_m"] for entry in evidence["objects"]}
    drawn = {model: drawn_model(evidence["linked"], model) for model in item["models"][:4]}
    commits = [commit for commit in evidence["bake_code"][item["route"]] if commit["commit"] in item["commits"]]
    return pictures.kit_age(item, drawn, density, commits)


def picture_of(item, evidence, sample):
    """The picture of one finding, or None when it cannot be drawn."""
    if item["rule"] == texel.RULE:
        return soft_picture(item, evidence, sample) if sample else None
    if item["rule"] == borders.RULE:
        return pictures.ragged_border(item, drawn_model(evidence["linked"], item["model"]))
    return kit_picture(item, evidence)


def marked(place, found, evidence, folder, samples):
    """Each finding with its picture written under marks/ (None when it could not be drawn)."""
    listed = []
    for number, item in enumerate(found):
        name = f"marks/{place}-{item['rule'].replace(' ', '-')}-{number}.png"
        picture = picture_of(item, evidence, samples.get(item.get("kit_px_per_m")))
        if picture is not None:
            (folder / "marks").mkdir(parents=True, exist_ok=True)
            picture.save(folder / name)
        listed.append(dict(item, picture=name if picture is not None else None))
    return listed


def judged(place, folder, world, samples):
    """Judge a place's evidence folder and write its findings.json; the findings as written."""
    evidence = judge.read(folder)
    found = judge.findings(evidence, world)
    written = {"place": place, "answer": judge.verdict(found), "reason": judge.reason(evidence, found),
               "outputs": evidence["outputs"], "findings": marked(place, found, evidence, folder, samples)}
    (folder / FINDINGS).write_text(json.dumps(written, indent=1))
    return written


def thumbnail(path):
    """A picture fitted into THUMB pixels square."""
    with Image.open(path) as source:
        picture = source.convert("RGB")
    picture.thumbnail((THUMB * 2, THUMB))
    return picture


def sheet(rows, path):
    """A contact sheet: a row a place, its answer and reason, then up to three of its findings' pictures."""
    height = THUMB + 40
    out = Image.new("RGB", (THUMB * 2 * 3 + 40, height * max(len(rows), 1)), pictures.PAPER)
    draw = ImageDraw.Draw(out)
    for number, (written, folder) in enumerate(rows):
        top = number * height
        colour = pictures.RED if written["answer"] == "fail" else (40, 140, 60)
        draw.text((8, top + 6), f"{written['place']}: {written['answer']}  {written['reason'][:150]}", fill=colour,
                  font=pictures.font(15))
        left = 8
        for item in [item for item in written["findings"] if item["picture"]][:3]:
            picture = thumbnail(folder / item["picture"])
            out.paste(picture, (left, top + 30))
            left += picture.width + 8
    out.save(path)
    return path


def places_of(chosen):
    """The places asked for, else every place of environment 1."""
    if chosen:
        return chosen
    from score import stages
    return stages.places(stages.runner(world=stages.WORLDS["world1"]()).world)


def measured(places, out, store):
    """Measure each place (when a store is given); the places that have evidence."""
    found = []
    for place in places:
        if store is not None and measure.gather(store, place, out / place, out / "linked") is None:
            print(f"{place}: unknown (no accepted assembly)", flush=True)
            continue
        if (out / place / measure.EVIDENCE).exists():
            found.append(place)
    return found


def kit_samples(evidences, world):
    """{reference density: kit sample} for each place's own kit reference and the environment's."""
    samples = {}
    for evidence in evidences:
        reference = texel.kit_reference(evidence["objects"])
        if reference is not None:
            samples[round(reference, 1)] = kit_sample([evidence], reference)
    if world is not None:
        samples[round(world, 1)] = kit_sample(evidences, world)
    return samples


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", action="append", default=[])
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--judge-only", action="store_true", help="judge evidence measured before")
    options = parser.parse_args(argv)
    places = measured(places_of(options.place), options.out, None if options.judge_only else Store.default())
    evidences = [judge.read(path.parent) for path in sorted(options.out.glob(f"*/{measure.EVIDENCE}"))]
    world = texel.world_reference(evidences)
    samples = kit_samples(evidences, world)
    rows, summary = [], {}
    for place in places:
        written = judged(place, options.out / place, world, samples)
        summary[place] = {"answer": written["answer"], "findings": len(written["findings"])}
        rows.append((written, options.out / place))
        print(f"{place}: {written['answer']} ({written['reason']})", flush=True)
    (options.out / "summary.json").write_text(json.dumps(summary, indent=1))
    sheet(rows, options.out / "contact_sheet.png")
    failed = sorted(place for place, entry in summary.items() if entry["answer"] == "fail")
    print(f"{len(summary)} places, {len(failed)} fail, {sum(entry['findings'] for entry in summary.values())} findings;"
          f" world kit {world and round(world)} px/m; contact sheet {options.out / 'contact_sheet.png'}")


if __name__ == "__main__":
    main()
