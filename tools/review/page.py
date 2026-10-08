"""The creator's review page for one place: every stage's output side by side in order, before and after where a stage
was rerun, and every check's result with what it caught. A static folder (index.html, its pictures and the walk's
video) built from the files the stages already wrote; it needs no server, opens from disk, and can be published as it
is.

    .venv/bin/python tools/review/page.py <place> --run <run folder> --out <folder>
        [--before <an earlier run folder>]          # a rerun's before: the same things drawn from the same cameras
        [--concept <concept folder>] [--references <folder of the reference pictures>]
        [--stage <stage.usda>] [--before-stage <the earlier run's stage.usda>]
        [--agreement <tools/usd/views.py's out folder>]
        [--no-render]                               # reuse the Blender renders already in <out>

What each folder holds is in records.py. The pictures no stage drew (each model and its parts, the assembled scene from
fixed cameras and a walk round it) are rendered by headless Blender (renders.py); the scene comes from the place's
OpenUSD stage, never from a game engine.
"""
import argparse
import hashlib
import html
import json
import pathlib
import shutil
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/props/gates"))
sys.path.insert(0, str(HERE.parents[1] / "tools/props/library"))
import records  # noqa: E402
import renders  # noqa: E402
from model import SPREAD_LIMIT, THINNEST_LIMIT  # noqa: E402
from sweep import ON_PALETTE  # noqa: E402

TEMPLATE = HERE / "page.html"
LARGEST_SIDE = 1400


def escaped(value):
    return html.escape(str(value))


# --- pictures -----------------------------------------------------------------------------------------------------

class Pictures:
    """Copies every picture the page shows into <out>/img as a JPEG no larger than LARGEST_SIDE, once."""

    def __init__(self, out):
        self.folder = out / "img"
        self.folder.mkdir(parents=True, exist_ok=True)

    def add(self, source, name):
        """The page's relative path to its copy of `source`."""
        target = self.folder / f"{name}.jpg"
        picture = Image.open(source).convert("RGB")
        picture.thumbnail((LARGEST_SIDE, LARGEST_SIDE))
        picture.save(target, quality=85)
        return f"img/{target.name}"


def same_file(first, second):
    return hashlib.sha1(first.read_bytes()).digest() == hashlib.sha1(second.read_bytes()).digest()


def figure(path, caption, extra=""):
    return (f'<figure {extra}><img loading="lazy" src="{escaped(path)}" alt="{escaped(caption)}">'
            f"<figcaption>{caption}</figcaption></figure>")


def missing(what):
    return f'<p class="missing">Not recorded: {what}.</p>'


def facts(pairs):
    return "<dl class=\"facts\">" + "".join(f"<div><dt>{escaped(key)}</dt><dd>{value}</dd></div>"
                                          for key, value in pairs) + "</dl>"


def verdict(passed):
    return '<span class="pill ok">pass</span>' if passed else '<span class="pill bad">caught</span>'


# --- the sections, in the order the stages run --------------------------------------------------------------------

def concept_section(concept, place_style, references_folder, pictures):
    if concept is None:
        return section("concept", "Concept and the creator's references", missing("no concept folder given"))
    pick = concept["pick"]
    takes = []
    for take in concept["takes"]:
        role = ("the pick" if take["name"] == pick.get("pick") else
                "runner-up" if take["name"] == pick.get("runner_up") else "take")
        cost = f", ${take['ledger']['dollars']:.3f}" if take["ledger"] and "dollars" in take["ledger"] else ""
        chosen = 'class="chosen"' if role == "the pick" else ""
        takes.append(figure(pictures.add(take["picture"], f"concept-{take['name']}"),
                            f"<b>{escaped(take['name'])}</b> {role}{cost}", chosen))
    refs = []
    for number, reference in enumerate(concept["references"]):
        if not reference.get("keep", True):
            continue
        found = records.reference_picture(reference, references_folder)
        body = (f"<b>{escaped(reference['title'])}</b><br>{escaped(reference.get('take', ''))}"
                f"<br><small>{escaped(reference.get('licence', ''))}</small>")
        refs.append(figure(pictures.add(found, f"reference-{number}"), body) if found else
                    f'<figure class="text"><figcaption>{body}<br><small>picture not downloaded</small>'
                    f"</figcaption></figure>")
    picked_take = next((take for take in concept["takes"] if take["name"] == pick.get("pick")), None)
    prompt = (f"<details><summary>The pick's prompt</summary><p class=\"prompt\">"
              f"{escaped(picked_take['ledger']['prompt'])}</p></details>"
              if picked_take and picked_take["ledger"] else "")
    body = (f'<p class="lead">{escaped(place_style["style"])}</p>'
            + facts([("pick", escaped(pick.get("pick", "?"))), ("why", escaped(pick.get("pick_why", ""))),
                     ("runner-up", escaped(pick.get("runner_up", ""))), ("status", escaped(pick.get("status", "")))])
            + f'<div class="grid wide">{"".join(takes)}</div>{prompt}'
            + "<h3>The creator's references</h3>"
            + (f'<div class="grid">{"".join(refs)}</div>' if refs else missing("no references kept")))
    return section("concept", "Concept and the creator's references", body)


def plan_section(concept, runs, pictures):
    planned = next((run["plan"] for run in reversed(list(runs.values())) if run and run["plan"]), None)
    elements = (planned or {}).get("elements") or (concept or {}).get("elements")
    if not elements:
        return section("plan", "Dimensioned plan", missing("no plan.json with elements in a run or the concept folder"))
    rows = "".join(
        f"<tr><td>{escaped(element['id'])}</td><td>{escaped(element['name'])}</td><td>{escaped(element['route'])}</td>"
        f"<td class=\"num\">{' × '.join(f'{value:g}' for value in element['size'])}</td>"
        f"<td class=\"num\">{len(element['at'])}</td></tr>" for element in elements)
    picture = figure(pictures.add(concept["plan_picture"], "plan"), "the plan, 1 m grid, with its side elevation") \
        if concept and concept["plan_picture"] else missing("plan.png")
    body = (f"<p>{escaped((planned or {}).get('frame', ''))}</p>{picture}<div class=\"scroll\"><table><thead><tr><th>element</th>"
            f"<th>what</th><th>route</th><th>size, m</th><th>spots</th></tr></thead><tbody>{rows}</tbody></table></div>")
    return section("plan", "Dimensioned plan", body)


def inventory_section(inventory, pictures):
    if inventory is None:
        return section("inventory", "Inventory", missing("no inventory in data/inventory"))
    blocks = []
    for view, path in inventory["views"].items():
        rows = [row for row in inventory["rows"] if row.get("view") == view and row.get("box")]
        if not path.exists():
            blocks.append(missing(f"the picture of view {view} ({path})"))
            continue
        wide, tall = Image.open(path).size
        boxes = "".join(
            f'<g><rect x="{row["box"][0]}" y="{row["box"][1]}" width="{row["box"][2] - row["box"][0]}" '
            f'height="{row["box"][3] - row["box"][1]}"/><text x="{row["box"][0] + 8}" y="{row["box"][1] + 34}">'
            f'{escaped(row["id"])}</text></g>' for row in rows)
        blocks.append(f'<figure class="partition"><div class="overlay"><img src="{pictures.add(path, "inventory-" + view)}"'
                      f' alt="the concept with the inventory boxes"><svg viewBox="0 0 {wide} {tall}" '
                      f'preserveAspectRatio="none">{boxes}</svg></div><figcaption>view {escaped(view)}: '
                      f"{len(rows)} rows boxed on the concept</figcaption></figure>")
    table = "".join(
        f"<tr><td>{escaped(row['id'])}</td><td>{escaped(row.get('kind', ''))}</td>"
        f"<td class=\"num\">{' × '.join(f'{value:g}' for value in row.get('size', []))}</td>"
        f"<td class=\"num\">{row.get('count', len(row.get('at', [])))}</td><td>{escaped(row.get('thing', ''))}</td>"
        f"<td>{escaped(row['name'])}</td></tr>" for row in inventory["rows"])
    body = ("".join(blocks) + f"<p><small>Approved: {escaped(inventory['approved'])}</small></p>"
            "<div class=\"scroll\"><table><thead><tr><th>row</th><th>kind</th><th>size, m</th><th>count</th>"
            f"<th>thing</th><th>what</th></tr></thead><tbody>{table}</tbody></table></div>")
    return section("inventory", "Inventory and its partition of the concept", body)


def closeups_section(runs, pictures):
    labels = [label for label, run in runs.items() if run and run["closeups"]]
    if not labels:
        return section("closeups", "Close-ups", missing("no closeups/ in any run"))
    now = runs[labels[-1]]["closeups"]
    tiles = []
    for row, path in now.items():
        earlier = [runs[label]["closeups"][row] for label in labels[:-1] if row in runs[label]["closeups"]]
        if earlier and not same_file(earlier[-1], path):
            tiles.append(pair(pictures.add(earlier[-1], f"closeup-{row}-before"),
                              pictures.add(path, f"closeup-{row}-now"), escaped(row)))
        else:
            tiles.append(figure(pictures.add(path, f"closeup-{row}"), escaped(row)))
    return section("closeups", "Close-ups", f'<div class="grid">{"".join(tiles)}</div>')


def pair(before, after, caption):
    return (f'<figure class="pair"><div class="two"><div><img loading="lazy" src="{escaped(before)}" alt="before">'
            f'<span class="tag">before</span></div><div><img loading="lazy" src="{escaped(after)}" alt="after">'
            f'<span class="tag">after</span></div></div><figcaption>{caption}</figcaption></figure>')


def shot_cell(shots, out, model, what, labels, caption):
    """A model's shot, or a before and after from one camera when two runs drew it."""
    names = [f"{model}--{what}--{label}" for label in labels if f"{model}--{what}--{label}" in shots]
    if not names:
        return f'<div class="cell">{missing(caption)}</div>'
    paths = [f"models/{name}.png" for name in names if (out / "models" / f"{name}.png").exists()]
    counted = shots[names[-1]]["triangles"]
    text = f"{caption}, {counted:,} triangles"
    if len(paths) > 1:
        return f'<div class="cell">{pair(paths[-2], paths[-1], text + " (after)")}</div>'
    return f'<div class="cell">{figure(paths[-1], text + " (" + names[-1].rsplit("--", 1)[1] + " run)")}</div>'


def labels_facts(take):
    if take is None:
        return missing("no labelled take")
    labels = take["labels"]
    shares = ", ".join(f"{name} {share:.0%}" for name, share in sorted(labels.get("shares", {}).items(),
                                                                         key=lambda item: -item[1]) if share >= 0.005)
    return facts([("take", escaped(take["take"])), ("labelled", escaped(labels.get("way", ""))),
                  ("surfaces", escaped(shares))])


def models_section(runs, shots, out, closeups):
    newest = [run for run in runs.values() if run]
    planned = next((run["planned"] for run in reversed(newest) if run["planned"]), None)
    if planned is None:
        return section("models", "Made models", missing("no plan-route.json in any run"))
    labels = list(runs)
    blocks = []
    for model, entry in planned["models"].items():
        take = next((run["takes"][model] for run in reversed(newest) if model in run["takes"]), None)
        route = ("code: a plain builder" if entry["route"] == "code" else "pipeline: picture, Pixal3D, labelled "
                 "parts, bake")
        cells = [f'<div class="cell">{figure(closeups[model], "close-up")}</div>' if model in closeups else
                 '<div class="cell"><p class="missing">Built in code: no close-up.</p></div>' if entry["route"] == "code"
                 else f'<div class="cell">{missing("close-up")}</div>']
        cells.append(shot_cell(shots, out, model, "parts", labels, "labelled parts, one colour per surface"))
        cells.append(shot_cell(shots, out, model, "made", labels, "made model, baked"))
        blocks.append(
            f'<article class="model"><h3>{escaped(model)} <small>{escaped(entry["kind"])}</small></h3>'
            + facts([("route", route), ("budget", f"{escaped(entry.get('budget', ''))}, {entry.get('faces', 0):,} "
                                                  "faces"),
                     ("laid size, m", " × ".join(f"{value:g}" for value in entry["size"]))])
            + (labels_facts(take) if entry["route"] == "model" else "")
            + f'<div class="cells">{"".join(cells)}</div></article>')
    return section("models", "Made models, their route and parts", "".join(blocks))


def surfaces_section(place, runs):
    library = records.surfaces(place)
    used = {}
    for run in (run for run in runs.values() if run):
        for model, take in run["takes"].items():
            for name, share in take["labels"].get("shares", {}).items():
                if share >= 0.005:
                    used.setdefault(name, {})[model] = share
    if not used:
        return section("surfaces", "Surfaces", missing("no labelled parts name a surface"))
    rows = []
    for name in sorted(used):
        entry = library.get(name, {})
        colour = "#" + "".join(f"{round(srgb(value) * 255):02x}" for value in entry.get("colour", [0.5, 0.5, 0.5]))
        carriers = ", ".join(f"{model} {share:.0%}" for model, share in sorted(used[name].items(),
                                                                              key=lambda item: -item[1]))
        rows.append(f'<tr><td><span class="swatch" style="background:{colour}"></span>{escaped(name)}</td>'
                    f"<td>{escaped(entry.get('family', ''))}</td><td>{escaped(entry.get('recipe', ''))}</td>"
                    f"<td>{escaped(entry.get('token', ''))}</td><td>{escaped(carriers)}</td></tr>")
    return section("surfaces", "Surfaces from the library",
                   "<p>Every surface the place's parts are labelled with, in the place's own colour, and the share of "
                   "each model it covers.</p><div class=\"scroll\"><table><thead><tr><th>surface</th><th>family</th>"
                   f"<th>recipe</th><th>token</th><th>on</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def srgb(linear):
    return linear * 12.92 if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055


def scene_section(scene, out):
    if scene is None:
        return section("scene", "The assembled scene", missing("no OpenUSD stage given"))
    labels = [path.name for path in sorted((out / "scene").iterdir()) if path.is_dir() and path.name != "walk"]
    tiles = []
    for view in scene["views"]:
        paths = [f"scene/{label}/{view}-look.png" for label in labels if (out / "scene" / label / f"{view}-look.png")
                 .exists()]
        tiles.append(pair(paths[0], paths[-1], escaped(view)) if len(paths) > 1 else figure(paths[-1], escaped(view)))
    report = scene["report"]
    body = ("<p>Rendered by Blender from the place's OpenUSD stage, no game engine: the place on a plain grey ground "
            "under a low sun.</p>"
            + facts([("layers", escaped(" over ".join(report["layers"]))), ("objects", report["objects"]),
                      ("triangles", f"{report['triangles']:,}"), ("materials", len(report["materials"])),
                      ("extent, m", escaped(f"{scene['extent'][0]} to {scene['extent'][1]}"))])
            + "<h3>A walk round it</h3><video src=\"scene/walk.mp4\" controls loop muted playsinline "
              "poster=\"scene/walk-strip.jpg\"></video>"
            + figure("scene/walk-strip.jpg", "the walk, every tenth frame")
            + f'<h3>Fixed cameras</h3><div class="grid wide">{"".join(tiles)}</div>')
    return section("scene", "The assembled scene", body)


# --- checks -------------------------------------------------------------------------------------------------------

def gate_rows(label, checks):
    rows = []
    for model, found in sorted(checks.items()):
        thin = found["thinnest"] < THINNEST_LIMIT
        spread = found["spread"] > SPREAD_LIMIT
        straight = found.get("straight")
        caught = ", ".join(word for word, hit in (("thinnest wall under 3 mm", thin),
                                                   ("proportions off by more than 20%", spread),
                                                   ("not straight", straight is False)) if hit)
        rows.append(f"<tr><td>{escaped(label)}</td><td>{escaped(model)}</td><td>{escaped(found['class'])}</td>"
                    f"<td class=\"num\">{found['faces']:,}</td><td class=\"num\">{found['spread']:.3f}</td>"
                    f"<td class=\"num\">{found['thinnest'] * 1000:.1f}</td><td class=\"num\">{found['pieces']}</td>"
                    f"<td>{verdict(found['pass'])}</td><td>{escaped(caught)}</td></tr>")
    return rows


def label_rows(runs):
    rows = []
    for label, run in runs.items():
        for model, take in sorted((run or {"takes": {}})["takes"].items()):
            labels = take["labels"]
            registration, patchy = labels.get("registration"), labels.get("patchy")
            caught = []
            if registration and not registration["registered"]:
                caught.append(f"split did not register (clear {registration['clear']:.0%}), painted whole")
            if patchy and not patchy["pass"]:
                caught.append("patchy: " + ", ".join(map(str, patchy["faults"])))
            passed = not caught
            rows.append(f"<tr><td>{escaped(label)}</td><td>{escaped(model)}-{escaped(take['take'])}</td>"
                        f"<td>{escaped(labels.get('way', ''))}</td>"
                        f"<td class=\"num\">{labels.get('upright_gap', 0):.4f}</td>"
                        f"<td>{verdict(passed) if registration or patchy else 'not checked'}</td>"
                        f"<td>{escaped('; '.join(caught))}</td></tr>")
    return rows


def sweep_rows(label, sweep):
    return [f"<tr><td>{escaped(label)}</td><td>{escaped(model)}</td><td class=\"num\">{found['on_palette']:.1%}</td>"
            f"<td class=\"num\">{found['lightness']:.0f}</td><td>{verdict(found['on_palette'] >= ON_PALETTE)}</td>"
            f"<td>{escaped(', '.join(map(str, found.get('outlier', []))))}</td></tr>"
            for model, found in sweep.items()]


def bake_rows(runs):
    rows = []
    for label, run in runs.items():
        bakes = (run or {"bakes": []})["bakes"]
        seen = {}
        for bake in bakes:
            for model in bake["models"].get("pieces", bake["models"]):
                if model in ("atlas",):
                    continue
                seen.setdefault(model, []).append(bake["name"])
        for model, names in sorted(seen.items()):
            if len(names) > 1:
                rows.append(f"<tr><td>{escaped(label)}</td><td>{escaped(model)}</td><td>{escaped(' then '.join(names))}"
                            "</td></tr>")
    return rows


def agreement_block(folder):
    if folder is None or not (folder / "agreement.json").exists():
        return missing("no comparison with the game's own shots given")
    found = json.loads((folder / "agreement.json").read_text())
    tiles = "".join(figure(f"agreement/{view}-side.png", f"{escaped(view)}: the game's shot, then Blender's; "
                           f"overlap {result['iou']:.2f}, held {result['held']:.2f}") for view, result in found.items())
    return (f"<p>The stage rendered from the game's own cameras beside the game's shots (tools/usd/views.py). The game "
            f"also draws the base and its ink lines, so a full match does not read 1.0.</p><div class=\"grid wide\">"
            f"{tiles}</div>")


def table(head, rows, empty):
    if not rows:
        return f"<p>{empty}</p>"
    return (f'<div class="scroll"><table><thead><tr>{"".join(f"<th>{name}</th>" for name in head)}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def checks_section(runs, agreement):
    gates = [row for label, run in runs.items() if run and run["checks"] for row in gate_rows(label, run["checks"])]
    sweeps = [row for label, run in runs.items() if run and run["sweep"] for row in sweep_rows(label, run["sweep"])]
    body = ("<h3>Model gate</h3><p>Every made model at its laid size: a wall under 3 mm or proportions more than 20% "
            "off fail it, and a failing model is remade, never placed.</p>"
            + (table(["run", "model", "shape", "faces", "spread", "thinnest, mm", "pieces", "result", "caught"],
                     gates, "") if gates else missing("no checks.json in any run"))
            + "<h3>Parts labelling</h3><p>Whether a take's split into parts registered against its picture, and "
              "whether its surfaces came out patchy.</p>"
            + table(["run", "take", "labelled", "upright gap", "result", "caught"], label_rows(runs),
                    "No labelled takes recorded.")
            + "<h3>Palette sweep</h3><p>The share of each model's colour that lies on the place's library palette; "
              "under 90% is an outlier.</p>"
            + (table(["run", "model", "on palette", "lightness", "result", "outliers"], sweeps, "")
               if sweeps else missing("no sweep.json in any run"))
            + "<h3>Rebakes</h3><p>Models a run baked more than once, in order (the bake reports in made/).</p>"
            + table(["run", "model", "bakes"], bake_rows(runs), "No model was baked twice.")
            + "<h3>Against the game</h3>" + agreement_block(agreement))
    return section("checks", "Checks and what they caught", body)


def section(anchor, title, body):
    return f'<section id="{anchor}"><h2>{escaped(title)}</h2>{body}</section>'


# --- the page -----------------------------------------------------------------------------------------------------

def copy_agreement(folder, out):
    if folder is None:
        return
    target = out / "agreement"
    target.mkdir(parents=True, exist_ok=True)
    for path in folder.glob("*-side.png"):
        shutil.copy(path, target / path.name)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("place")
    parser.add_argument("--run", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    for name in ("before", "concept", "references", "stage", "before-stage", "agreement"):
        parser.add_argument(f"--{name}", type=pathlib.Path)
    parser.add_argument("--no-render", action="store_true")
    return parser.parse_args()


def render_all(options, runs, out):
    """The Blender pictures, or the ones a previous build left when --no-render; what they hold."""
    planned = next((run["planned"] for run in reversed(list(runs.values())) if run and run["planned"]), None)
    names = list(planned["models"]) if planned else []
    stages = {label: stage for label, stage in (("before", options.before_stage), ("now", options.stage)) if stage}
    if options.no_render:
        found = json.loads((out / "renders.json").read_text())
        return found["shots"], found["scene"]
    shots = renders.model_shots(names, runs, records.surfaces(options.place), out)
    scene = renders.scene_shots(options.place, stages, out) if stages else None
    (out / "renders.json").write_text(json.dumps({"shots": shots, "scene": scene}, indent=1))
    return shots, scene


def build(options):
    out = options.out
    out.mkdir(parents=True, exist_ok=True)
    runs = {"before": records.run(options.before), "now": records.run(options.run)}
    if runs["before"] is None:
        del runs["before"]
    pictures = Pictures(out)
    shots, scene = render_all(options, runs, out)
    copy_agreement(options.agreement, out)
    style = records.place_style(options.place)
    concept = records.concept(options.concept)
    closeups = {row: pictures.add(path, f"closeup-{row}") for run in runs.values() if run
                for row, path in run["closeups"].items()}
    sections = [
        concept_section(concept, style, options.references, pictures),
        plan_section(concept, runs, pictures),
        inventory_section(records.inventory(options.place), pictures),
        closeups_section(runs, pictures),
        models_section(runs, shots, out, closeups),
        surfaces_section(options.place, runs),
        scene_section(scene, out),
        checks_section(runs, options.agreement),
    ]
    sources = facts([(label, escaped(run["folder"])) for label, run in runs.items() if run])
    page = (TEMPLATE.read_text().replace("{{TITLE}}", escaped(f"{style['name'].removeprefix('the ').title()} review"))
            .replace("{{PLACE}}", escaped(style["name"])).replace("{{SOURCES}}", sources)
            .replace("{{SECTIONS}}", "\n".join(sections)))
    (out / "index.html").write_text(page)
    return out / "index.html"


def main():
    print(build(arguments()))


if __name__ == "__main__":
    main()
