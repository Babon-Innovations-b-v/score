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
        [--plain]                                   # debug: the scene in one plain grey instead of its materials
        [--cloud]                                   # render on rented cards (tools/props/cloud/blender_cloud.py)

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
import characters  # noqa: E402
import complete  # noqa: E402  (tools/usd, on the path renders puts it)
import records  # noqa: E402
import renders  # noqa: E402
import placeholders  # noqa: E402  (tools/usd, on the path renders puts it)
import resting  # noqa: E402  (tools/usd, on the path renders puts it)
import scene as scene_record  # noqa: E402  (tools/usd)
from model import SPREAD_LIMIT, THINNEST_LIMIT  # noqa: E402
from sweep import ON_PALETTE  # noqa: E402

TEMPLATE = HERE / "page.html"
LARGEST_SIDE = 1400
# A scene view darker than this share of the game's own shot's mean brightness fails the brightness check.
DARK_SHARE = 0.5


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


# The columns of a dimensioned plan's lists that hold rows of plain values (the concept step's plan.json).
PLAN_COLUMNS = {"items": ("what", "x", "z", "wide", "deep", "wall", "kind"), "doors": ("wall", "at", "wide", "what"),
                "people": ("x", "z"), "stools": ("x", "z")}


def plan_cell(value):
    if isinstance(value, dict):
        return "; ".join(f"{key} {plan_cell(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " × ".join(plan_cell(item) for item in value)
    return f"{value:g}" if isinstance(value, float) else "" if value is None else str(value)


def plan_table(name, entries):
    """One list of a dimensioned plan as a table: rows of values under PLAN_COLUMNS' heads, or records under their
    keys."""
    if all(isinstance(entry, dict) for entry in entries):
        heads = list(dict.fromkeys(key for entry in entries for key in entry))
        cells = [[entry.get(key) for key in heads] for entry in entries]
    else:
        cells = [entry if isinstance(entry, list) else [entry] for entry in entries]
        heads = list(PLAN_COLUMNS.get(name, ()))[:max(len(row) for row in cells)]
    head = "".join(f"<th>{escaped(key)}</th>" for key in heads)
    body = "".join("<tr>" + "".join(f"<td>{escaped(plan_cell(value))}</td>" for value in row) + "</tr>" for row in cells)
    return (f"<h4>{escaped(name)}</h4><div class=\"scroll\"><table>{f'<thead><tr>{head}</tr></thead>' if head else ''}"
            f"<tbody>{body}</tbody></table></div>")


def dimensioned_block(found, pictures, number):
    """One dimensioned plan the inventory names: its picture, its sizes, every list it holds and its notes."""
    where = f"<small>{escaped(found['path'])}</small>"
    if not found["found"]:
        return f"<h3>Plan {number}</h3>" + missing(f"the plan the inventory names is not on disk ({escaped(found['path'])})")
    picture = figure(pictures.add(found["picture"], f"dimensioned-{number}"), f"the dimensioned plan {number}") \
        if found["picture"] else missing("its plan.png")
    plan = found["plan"]
    if plan is None:
        return (f"<h3>Plan {number}</h3><p>{where}</p>{picture}<p>Drawn as a picture only: this plan has no plan.json, "
                "so its numbers are not listed here.</p>")
    sizes = [(key, escaped(plan_cell(value))) for key, value in plan.items()
             if key not in ("notes", "title") and not isinstance(value, list)]
    tables = "".join(plan_table(key, value) for key, value in plan.items()
                     if isinstance(value, list) and value and key != "notes")
    notes = "".join(f"<li>{escaped(note)}</li>" for note in plan.get("notes", []))
    folder = found["path"].parent
    name = plan.get("title") or (folder.parent.name if folder.name == "plan" else folder.name)
    return (f"<h3>Plan {number}: {escaped(name)}</h3><p>{where}</p>{picture}"
            + facts(sizes) + tables + (f"<ul>{notes}</ul>" if notes else ""))


def plan_section(concept, runs, pictures, dimensioned):
    """The dimensioned plans the place was drawn to (named in its inventory) and the plan's elements a run or the
    concept folder wrote; said plainly when the place has neither."""
    planned = next((run["plan"] for run in reversed(list(runs.values())) if run and run["plan"]), None)
    elements = (planned or {}).get("elements") or (concept or {}).get("elements")
    plans = "".join(dimensioned_block(found, pictures, number) for number, found in enumerate(dimensioned, 1))
    if not elements and not plans:
        return section("plan", "Dimensioned plan", "<p class=\"missing\">This place has no dimensioned plan: its "
                       "inventory names none, and no run or concept folder holds a plan.json with elements.</p>")
    if not elements:
        return section("plan", "Dimensioned plan", plans)
    rows = "".join(
        f"<tr><td>{escaped(element['id'])}</td><td>{escaped(element['name'])}</td><td>{escaped(element['route'])}</td>"
        f"<td class=\"num\">{' × '.join(f'{value:g}' for value in element['size'])}</td>"
        f"<td class=\"num\">{len(element['at'])}</td></tr>" for element in elements)
    picture = figure(pictures.add(concept["plan_picture"], "plan"), "the plan, 1 m grid, with its side elevation") \
        if concept and concept["plan_picture"] else "" if plans else missing("plan.png")
    body = (plans + f"<h3>The plan's elements</h3><p>{escaped((planned or {}).get('frame', ''))}</p>{picture}"
            f"<div class=\"scroll\"><table><thead><tr><th>element</th><th>what</th><th>route</th><th>size, m</th>"
            f"<th>spots</th></tr></thead><tbody>{rows}</tbody></table></div>")
    return section("plan", "Dimensioned plan", body)


def unseen_note(row):
    """A row the concept does not show, said so with why (inventory.py's `unseen`), or one boxed on one example of
    many (`repeats`)."""
    if row.get("unseen"):
        return f"<br><small>not in the concept: {escaped(row['unseen'])}</small>"
    return f"<br><small>boxed on one example; repeats {escaped(row['repeats'])}</small>" if row.get("repeats") else ""


def box_verdict(verdict):
    """One row's box gate verdict as a pill with why."""
    if not verdict:
        return ""
    pill = {"pass": "ok", "fail": "bad"}.get(verdict["result"], "")
    return f'<span class="pill {pill}">{escaped(verdict["result"])}</span><br><small>{escaped(verdict["why"])}</small>'


def gate_summary(gate):
    """The box gate's count for the place: every box measured from SAM's proposals and checked on that box."""
    if not gate:
        return ""
    counts = {name: sum(entry["result"] == name for entry in gate["rows"].values()) for name in ("pass", "fail", "unknown")}
    return (f"<p>Box gate: <b>{escaped(gate['result'])}</b>, {counts['pass']} boxes pass, {counts['fail']} fail, "
            f"{counts['unknown']} unknown (a box comes from SAM 2.1's proposals on the concept's tiles and passes when SAM 3 "
            "grounds it or the open judge says it shows its row; unknown blocks the close-ups like a fail).</p>")


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
    gate = (inventory.get("gate") or {}).get("rows", {})
    table = "".join(
        f"<tr><td>{escaped(row['id'])}</td><td>{box_verdict(gate.get(row['id']))}</td><td>{escaped(row.get('kind', ''))}</td>"
        f"<td class=\"num\">{' × '.join(f'{value:g}' for value in row.get('size', []))}</td>"
        f"<td class=\"num\">{row.get('count', len(row.get('at', [])))}</td><td>{escaped(row.get('thing', ''))}</td>"
        f"<td>{escaped(row['name'])}{unseen_note(row)}</td></tr>" for row in inventory["rows"])
    body = ("".join(blocks) + f"<p><small>Approved: {escaped(inventory['approved'])}</small></p>"
            + gate_summary(inventory.get("gate"))
            + "<div class=\"scroll\"><table><thead><tr><th>row</th><th>box</th><th>kind</th><th>size, m</th><th>count</th>"
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


def pair(before, after, caption, tags=("before", "after")):
    return (f'<figure class="pair"><div class="two"><div><img loading="lazy" src="{escaped(before)}" alt="{tags[0]}">'
            f'<span class="tag">{tags[0]}</span></div><div><img loading="lazy" src="{escaped(after)}" alt="{tags[1]}">'
            f'<span class="tag">{tags[1]}</span></div></div><figcaption>{caption}</figcaption></figure>')


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


def shown_models(planned, kit_run):
    """The models the page shows one by one: every one of an outdoor place's; a kit room's generated ones (its code
    pieces, walls to wiring, are counted, not shown one by one)."""
    return {model: entry for model, entry in planned["models"].items() if not kit_run or entry["route"] == "model"}


def closeup_of(closeups, model, entry):
    """A model's close-up: under its own name (an outdoor place's model is its row), else its kind's row."""
    if model in closeups:
        return closeups[model]
    own = entry["kind"].split("_", 1)[1] if "_" in entry["kind"] else entry["kind"]
    return next((closeups[row] for row in (own, entry["kind"]) if row in closeups), None)


def models_section(runs, shots, out, closeups):
    newest = [run for run in runs.values() if run]
    planned = next((run["planned"] for run in reversed(newest) if run["planned"]), None)
    if planned is None:
        return section("models", "Made models", missing("no plan-route.json in any run"))
    kit_run = any(run.get("kit") for run in newest)
    labels = list(runs)
    blocks = []
    if kit_run:
        code = [model for model, entry in planned["models"].items() if entry["route"] == "code"]
        blocks.append(f"<p>{len(code)} models of the room are code builds (walls, floor, roof, doors, pipes, cables, "
                      f"fittings), baked in shared picture sets; the {len(planned['models']) - len(code)} generated ones "
                      "follow, each from its close-up.</p>")
    for model, entry in shown_models(planned, kit_run).items():
        closeup = closeup_of(closeups, model, entry)
        take = next((run["takes"][model] for run in reversed(newest) if model in run["takes"]), None)
        route = ("code: a plain builder" if entry["route"] == "code" else "pipeline: picture, Pixal3D, labelled "
                 "parts, bake")
        cells = [f'<div class="cell">{figure(closeup, "close-up")}</div>' if closeup else
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


def mean_brightness(path):
    """A picture's mean brightness, 0 to 1 (its grey's mean)."""
    picture = Image.open(path).convert("L")
    picture.thumbnail((320, 320))
    return sum(value * count for value, count in enumerate(picture.histogram())) / (255.0 * picture.width *
                                                                                 picture.height)


def beside_tile(view, game_file, caption, before):
    """One view's tile beside the game: the scene, its before stage's render first when the page has one
    (--before-stage, scene/before), and the game's shot."""
    cells = ([("before", f"scene/before/{view}-look.png")] if before else []) + [("scene", f"scene/now/{view}-look.png"),
                                                                                   ("game", game_file)]
    inner = "".join(f'<div><img loading="lazy" src="{escaped(path)}" alt="{tag}"><span class="tag">{tag}</span></div>'
                    for tag, path in cells)
    return (f'<figure class="pair"><div class="two{" three" if before else ""}">{inner}</div>'
            f'<figcaption>{caption}</figcaption></figure>')


def game_beside(scene, out, games, pictures):
    """Each view beside the game's own shot from about the same place (and after its earlier render, when the page has
    one), with both pictures' mean brightness: a render far darker than the game's shot (under DARK_SHARE of its
    brightness) fails. The tiles and (views judged, views passed)."""
    tiles, judged, passed = [], 0, 0
    for view, game in scene.get("games", {}).items():
        render = out / "scene/now" / f"{view}-look.png"
        shot = pathlib.Path(games) / game if games else None
        if not render.exists():
            continue
        if shot is None or not shot.exists():
            tiles.append(figure(f"scene/now/{view}-look.png", escaped(f"{view}: the game's shot is not recorded")))
            continue
        ours, theirs = mean_brightness(render), mean_brightness(shot)
        judged += 1
        bright = ours >= DARK_SHARE * theirs
        passed += bright
        game_file = pictures.add(shot, f"game-{view}")
        caption = escaped(f"{view}: scene {ours:.2f}, game {theirs:.2f} mean brightness, "
                          f"{'bright enough' if bright else 'far darker than the game'}")
        before = (out / "scene/before" / f"{view}-look.png").exists()
        tiles.append(beside_tile(view, game_file, f"{verdict(bright)} {caption}", before))
    return tiles, judged, passed


def complete_line(place, scene, judged, passed):
    """The place's 'scene vs game' line: what of what the game draws the scene carries (its people too, from its cast),
    what is still missing against the game's shots, what the owner chose to leave out (`owner_rejected`), and how many
    views are as bright as the game's."""
    record = scene_record.record(place)
    if record is None:
        return "<p><b>Scene vs game:</b> no scene record yet: only the made pieces are in the scene.</p>"
    carried = [f"{word} ({len(record.get(key, []))})" for key, word in
               (("structure", "structure built in code"), ("ground", "ground"), ("water", "water"),
                ("objects", "gameplay objects"), ("backdrop", "backdrop arcs"), ("places", "other places seen from it"),
                ("lights", "lights of its own")) if record.get(key)]
    if record.get("planned_ground"):
        carried.append("the planned ground out to the horizon")
    if record.get("environment"):
        carried.append("the game's sky, ambient light and exposure")
    if record.get("kit_lights", True):
        carried.append("the kit's lamps as lights")
    cast = HERE.parents[1] / "data/characters" / f"{place}.json"
    if cast.exists():
        people = json.loads(cast.read_text())
        count = len(people.get("people", [])) + sum(int(group.get("count", 0)) for group in people.get("groups", []))
        crowd = int(people.get("crowd", {}).get("count", 0)) if people.get("crowd") else 0
        if count or crowd:
            carried.append(f"its people ({count}" + (f", and a crowd of {crowd}" if crowd else "") + ")")
    missing_now = record.get("game_only", [])
    light = (f"{passed} of {judged} views at least {DARK_SHARE:.0%} as bright as the game's shot" if judged else
             "no game shot to compare brightness with")
    return (f"<p><b>Scene vs game:</b> the scene carries {escaped(', '.join(carried))}. "
            f"Still missing against the game's shots: "
            f"{escaped('; '.join(missing_now)) if missing_now else 'nothing found yet'}. "
            f"{rejected_sentence(record)}"
            f"Brightness: {escaped(light)}.</p>")


def rejected_sentence(record):
    """What the game draws that the owner chose to leave out of the scene, said apart from what is missing."""
    rejected = record.get("owner_rejected", [])
    return f"Left out by the owner: {escaped('; '.join(rejected))}. " if rejected else ""


def scene_section(scene, out, place=None, games=None, pictures=None):
    if scene is None:
        return section("scene", "The assembled scene", missing("no OpenUSD stage given"))
    labels = [path.name for path in sorted((out / "scene").iterdir()) if path.is_dir() and path.name != "walk"]
    beside, judged, passed = game_beside(scene, out, games, pictures) if pictures is not None else ([], 0, 0)
    complete = complete_line(place, scene, judged, passed) if place else ""
    tiles = []
    for view in scene["views"]:
        paths = [f"scene/{label}/{view}-look.png" for label in labels if (out / "scene" / label / f"{view}-look.png")
                 .exists()]
        tiles.append(pair(paths[0], paths[-1], escaped(view)) if len(paths) > 1 else figure(paths[-1], escaped(view)))
    inked = [pair(f"scene/{labels[-1]}/{view}-look.png", f"scene/{labels[-1]}/{view}-ink.png",
                  escaped(f"{view}: the look, and the same with the game's ink lines over it"), ("look", "ink"))
             for view in scene["views"] if labels and (out / "scene" / labels[-1] / f"{view}-ink.png").exists()]
    report = scene["report"]
    lit = ("in its baked materials with everything the game draws in its own code that its scene record carries "
           "(structure, ground, water, backdrop, gameplay objects), lit by the stage's own lights and sky as the game "
           "sets them, from the player's own spots" + (" and from a cutaway above with the roof left out"
                                                         if "cutaway" in scene["views"] else "")
           if scene.get("recorded") else
           f"inside the room in its baked materials, lit by its own {scene.get('lamps', 0)} lamps where the game hangs "
           "their lights, from each wall across the room and from high in a corner with the roof left out"
           if scene.get("room") else
           "the place in its baked materials on its own ground (the planned Moon ground round it, in the plan's skin, "
           "where the stage has it) under a low sun, with a weak fill from the other side so no side is black")
    body = (f"<p>Rendered by Blender from the place's OpenUSD stage, no game engine: {lit}.</p>"
            + facts([("layers", escaped(" over ".join(report["layers"]))), ("objects", report["objects"]),
                      ("triangles", f"{report['triangles']:,}"), ("materials", len(report["materials"])),
                      ("extent, m", escaped(f"{scene['extent'][0]} to {scene['extent'][1]}"))])
            + "<h3>A walk round it</h3><video src=\"scene/walk.mp4\" controls loop playsinline "
              "poster=\"scene/walk-strip.jpg\"></video>"
            + figure("scene/walk-strip.jpg", "the walk, every tenth frame")
            + (f'<h3>Beside the game</h3>{complete}<div class="grid pairs">{"".join(beside)}</div>' if complete else "")
            + f'<h3>Fixed cameras</h3><div class="grid {"pairs" if len(labels) > 1 else "wide"}">{"".join(tiles)}</div>'
            + (f'<h3>Ink lines</h3><p>An option of the render, never part of the stage: the game\'s full-screen ink '
               f'pass (ink_edges.gdshader: its depth and crease rule, its line widths and its fade with distance) '
               f'worked out on the render\'s own depth and facing, laid over the look.</p>'
               f'<div class="grid pairs">{"".join(inked)}</div>' if inked else ""))
    return section("scene", "The assembled scene", body)


def characters_section(cast):
    """The place's characters: why each entry of its cast is there, each one close, each group and the crowd wide, and
    a moving shot of each named person, group and crowd view."""
    if cast is None:
        return section("characters", "Characters", missing("no cast in data/characters, or no stage to draw it in"))
    if not cast["who"] and not cast["crowd"]:
        return section("characters", "Characters", f"<p>Nobody. {escaped(cast['note'])}</p>")
    rows = "".join(f"<tr><td>{escaped(entry['name'])}</td><td>{escaped(entry['why'])}</td></tr>" for entry in cast["why"])
    doing = {person["name"]: f"{person['character']}, {person['doing']}" for person in cast["who"]}
    closes = "".join(figure(f"characters/close/{view}-look.png", escaped(f"{view.removeprefix('close-')}: "
                                                                          f"{doing[view.removeprefix('close-')]}"))
                     for view in cast["closes"])
    wides = "".join(figure(f"characters/wide/{view}-look.png", escaped(view)) for view in cast["wides"])
    moves = "".join(f'<figure><video src="characters/{escaped(view)}.mp4" controls loop muted playsinline></video>'
                    f"<figcaption>{escaped(view)}</figcaption></figure>" for view in cast["moves"])
    body = (f"<p>Skinned characters from the place's cast (data/characters), each playing its clip in the OpenUSD "
            f"stage's characters layer; {len(cast['who'])} placed one by one and {cast['crowd']:,} in the crowd.</p>"
            f"<table><tr><th>who</th><th>why they are there</th></tr>{rows}</table>"
            f'<h3>Moving</h3><div class="grid">{moves}</div>'
            f'<h3>Groups and the crowd</h3><div class="grid wide">{wides}</div>'
            f'<h3>Each one close</h3><div class="grid">{closes}</div>')
    return section("characters", "Characters", body)


# --- checks -------------------------------------------------------------------------------------------------------

def gate_rows(label, checks):
    rows = []
    for model, found in sorted(checks.items()):
        if found.get("missing"):  # a screen the route writes at install, not made by the bake: nothing to gate
            rows.append(f"<tr><td>{escaped(label)}</td><td>{escaped(model)}</td><td colspan=\"5\">written by the "
                        "route, not baked</td><td>not checked</td><td></td></tr>")
            continue
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


def resting_rows(label, judged):
    rows = []
    for found in judged:
        if found.get("passed") is not False:
            continue
        # A hung object is not judged for floating or sinking, only for lying inside another: no gap, no depth.
        gap = "" if found.get("gap") is None else f"{found['gap'] * 100:.1f}"
        depth = "" if found.get("depth") is None else f"{found['depth'] * 100:.1f}"
        rows.append(f"<tr><td>{escaped(label)}</td><td>{escaped(found['object'])}</td><td class=\"num\">{gap}</td>"
                    f"<td class=\"num\">{depth}</td><td>{verdict(False)}</td>"
                    f"<td>{escaped(found['result'])}</td></tr>")
    return rows


def resting_block(stages):
    """The resting check (tools/usd/resting.py) on every stage ({label: its verdicts}): each object that floats,
    tips or is sunk, and why; None when the page was built without it (--no-resting)."""
    if stages is None:
        return missing("the resting check, left out of this page (--no-resting) because it ran out of memory on the "
                       "machine that built it")
    if not stages:
        return missing("no OpenUSD stage given")
    counts = [f"{escaped(label)}: {sum(found.get('passed') is not False for found in judged)} of {len(judged)} "
              f"objects rest" for label, judged in stages.items()]
    rows = [row for label, judged in stages.items() for row in resting_rows(label, judged)]
    return (f"<p>Every object of the stage looked at straight down, on the stage's own ground (tools/usd/resting.py): "
            f"one floating over what is under it, one whose weight stands outside what it touches (it tips, one end "
            f"in the air), or one sunk into the ground below its own contact points, each by more than "
            f"{resting.TOLERANCE * 100:.0f} cm, fails; a hung object is not checked, and a fixed one (a building, a "
            f"mast) is not judged for tipping. {'; '.join(counts)}.</p>"
            + table(["stage", "object", "gap, cm", "depth, cm", "result", "caught"], rows, "Every object rests."))


def placeholder_block(stages):
    """The placeholder check (tools/usd/placeholders.py) on every stage ({label: its faults}): each visible thing that
    stands in for a made piece, and the rule it breaks."""
    if not stages:
        return missing("no OpenUSD stage given")
    counts = [f"{escaped(label)}: {'no placeholder' if not faults else f'{len(faults)} placeholders'}"
              for label, faults in stages.items()]
    rows = [f"<tr><td>{escaped(label)}</td><td>{escaped(fault['prim'])}</td><td>{escaped(fault['rule'])}</td>"
            f"<td>{verdict(False)}</td><td>{escaped(fault['why'])}</td></tr>"
            for label, faults in stages.items() for fault in faults]
    return (f"<p>Everything visible on the stage is a made piece, the game's own model placed or a plain plate, pipe "
            f"or trim (tools/usd/placeholders.py): a box, quad, disc, lathe, sphere or torus of the scene record that "
            f"does not say which plain thing it is, a kit piece built in code that the sorter sends to the prop "
            f"pipeline, a mesh with no material or in the default grey, and a proxy each fail. {'; '.join(counts)}."
            f"</p>" + table(["stage", "prim", "rule", "result", "caught"], rows, "Nothing stands in for a made piece."))


def table(head, rows, empty):
    if not rows:
        return f"<p>{empty}</p>"
    return (f'<div class="scroll"><table><thead><tr>{"".join(f"<th>{name}</th>" for name in head)}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def checks_section(runs, agreement, rests, stand_ins):
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
            + "<h3>Resting on the ground</h3>" + resting_block(rests)
            + "<h3>Placeholders</h3>" + placeholder_block(stand_ins)
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
    parser.add_argument("--game-shots", type=pathlib.Path, help="the folder the scene record's views name the game's "
                        "own shots in, laid beside the scene's")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--no-resting", action="store_true", help="leave the resting check out (a stage too big for "
                        "this machine's memory)")
    parser.add_argument("--cloud", action="store_true", help="render on rented cards, not this PC's Blender")
    return parser.parse_args()


def render_all(options, runs, out):
    """The Blender pictures, or the ones a previous build left when --no-render; what they hold."""
    planned = next((run["planned"] for run in reversed(list(runs.values())) if run and run["planned"]), None)
    kit_run = any(run.get("kit") for run in runs.values() if run)
    names = list(shown_models(planned, kit_run)) if planned else []
    stages = {label: stage for label, stage in (("before", options.before_stage), ("now", options.stage)) if stage}
    if options.no_render:
        found = json.loads((out / "renders.json").read_text())
        return found["shots"], found["scene"], found.get("characters")
    shots = renders.model_shots(names, runs, records.surfaces(options.place), out)
    layout = records.kit(options.place)
    # A kit room with a roof (draw layer 2) is drawn from inside; a kit laid outdoors (the prologue's street) from round it.
    room = layout if layout and any(piece.get("layer") == renders.ROOF_LAYER for piece in layout.get("pieces", [])) \
        else None
    outdoor_kit = room is None and bool(layout and layout.get("pieces") and "x" in layout["pieces"][0])
    scene = renders.scene_shots(options.place, stages, out, options.plain, room, outdoor_kit,
                                scene_record.record(options.place)) if stages else None
    cast = characters.shots(options.place, options.stage, out) if options.stage else None
    (out / "renders.json").write_text(json.dumps({"shots": shots, "scene": scene, "characters": cast}, indent=1))
    return shots, scene, cast


def build(options):
    out = options.out
    out.mkdir(parents=True, exist_ok=True)
    runs = {"before": records.run(options.before), "now": records.run(options.run)}
    if runs["before"] is None:
        del runs["before"]
    pictures = Pictures(out)
    if getattr(options, "cloud", False) and not options.no_render:  # one rented machine for every render of the page
        sys.path.insert(0, str(HERE.parents[1] / "tools/props/cloud"))
        import blender_cloud
        with blender_cloud.Machine(renders.CLOUD_CLASSES, "review page") as machine:
            renders.CLOUD = machine
            shots, scene, cast = render_all(options, runs, out)
        renders.CLOUD = None
    else:
        shots, scene, cast = render_all(options, runs, out)
    if cast is not None:
        cast = dict(cast, **characters.words(options.place))
    copy_agreement(options.agreement, out)
    style = records.place_style(options.place)
    concept = records.concept(options.concept)
    closeups = {row: pictures.add(path, f"closeup-{row}") for run in runs.values() if run
                for row, path in run["closeups"].items()}
    inventory = records.inventory(options.place)
    stages = [(label, stage) for label, stage in (("before", options.before_stage), ("now", options.stage)) if stage]
    sections = [
        concept_section(concept, style, options.references, pictures),
        plan_section(concept, runs, pictures, (inventory or {}).get("dimensioned", [])),
        inventory_section(inventory, pictures),
        closeups_section(runs, pictures),
        models_section(runs, shots, out, closeups),
        surfaces_section(options.place, runs),
        scene_section(scene, out, options.place, getattr(options, "game_shots", None), pictures),
        characters_section(cast),
        checks_section(runs, options.agreement, None if getattr(options, "no_resting", False) else {label: resting.check(stage) for label, stage in stages},
                       {label: placeholders.check(stage) for label, stage in stages}),
    ]
    sources = facts([(label, escaped(run["folder"])) for label, run in runs.items() if run])
    # Each word capitalised by its first letter only: str.title() wrote "Player'S Flat".
    title = " ".join(word[:1].upper() + word[1:] for word in style["name"].removeprefix("the ").split())
    page = (TEMPLATE.read_text().replace("{{TITLE}}", escaped(f"{title} review"))
            .replace("{{PLACE}}", escaped(style["name"])).replace("{{SOURCES}}", sources)
            .replace("{{SECTIONS}}", "\n".join(sections)))
    (out / "index.html").write_text(page)
    stamp(out, options.stage, rendered=not options.no_render)
    return out / "index.html"


def stamp(out, stage, rendered):
    """Write which stage the page was built from (review.json), for the completion gate (tools/usd/complete.py): the
    stage's fingerprint now, and the one its scene was last rendered from (kept from the last stamp on --no-render)."""
    if stage is None:
        return
    path = out / complete.REVIEW_STAMP
    before = json.loads(path.read_text()) if path.exists() else {}
    current = complete.fingerprint(stage)
    path.write_text(json.dumps({"stage": str(stage), "fingerprint": current, "at": complete.now(),
                                "rendered": current if rendered else before.get("rendered")}, indent=1) + "\n")


def main():
    print(build(arguments()))


if __name__ == "__main__":
    main()
