"""The with/without comparison of the parts check's order on one place: prop-first (the owner's decision of 2026-10-12)
against code-first (the parts check as it was: code when a kind's code build shows every part, else the prop route).

    .venv/bin/python -m score.stages.props.compare prepare <place> prop-first [--sample a,b,...]   # free
    .venv/bin/python -m score.stages.props.compare run <place> prop-first [--detach]               # paid
    .venv/bin/python -m score.stages.props.compare prepare <place> code-builds [--code-builds <folder>]   # free
    .venv/bin/python -m score.stages.props.compare run <place> code-builds [--detach]              # DINOv2 only
    .venv/bin/python -m score.stages.props.compare table <place>                                   # free

Two runs, each an environment of its own under $PROPS_HOME/compare/<place>/<run>/: a copy of the repository's data with the
run's prop data (data/props/<place>.json) and surface data, and a store of its own, so neither touches environment 1's store
or data. `run` drives the place's line up to the likeness row with the stage table as it is (score.stages):
props-inputs, closeup, pixal, the surface line, likeness-calibration, likeness, each paid row cleared by the runner as
in world 1, and every ledger line it and its children write tagged compare-<place>-<run> (ledger_tag/sitecustomize.py),
so its euros count apart from world 1's lines running beside it.

- prop-first: every object of the place (or of the sample) with a box the box gate passes or an accepted close-up
  goes the prop route: the prop results. Its inventory copy marks every such row `generate` (the batch builds only
  generated rows). An object every Pro close-up fails has failed the prop route there.
- code-builds: each of those objects that has a code build (`--code-builds`, <row>_1.gltf), held to the same gate
  with prop-first's accepted close-up: the code results. It generates nothing.

Both orders are derived from the two result sets, so neither pays twice: prop-first tries the prop route, then the
code build; code-first follows the parts check (sorter.route): the code build first where it says code, else the
prop route first; an object neither passes needs a builder an agent writes. `table` writes table.json and page.html in
$PROPS_HOME/compare/<place>/: per order the objects passing by each route, those needing a builder, those a check could
not tell, the euros and the agent hours (agent-hours-<order>.json, {row: hours}, written by the session that writes a
builder; none recorded shows as such), and per object both orders' route, for the owner's pick.
"""
import argparse
import html
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.store import PROPS_HOME, Store  # noqa: E402
import score.stages.props.calibration_row as calibration_row  # noqa: E402
import score.stages.props.likeness_row as likeness_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402

FOLDER = PROPS_HOME / "compare"
LEDGER_TAG = pathlib.Path(__file__).resolve().parent / "ledger_tag"
TAG_VARIABLE = "SCORE_LEDGER_TAG"
ORDERS = ("prop-first", "code-first")
RUNS = ("prop-first", "code-builds")
NODE = "likeness@{place}"


def order_folder(place, order):
    return FOLDER / place / order


def default_code_builds(place):
    return PROPS_HOME / "work/place" / f"{place}-round6/objects"


def accepted_models(place):
    """{model: close-up pattern} of the place's accepted takes (its surface data's models and claims elsewhere): the
    close-up each take was made from (WORK/pixal/<take>.svviews/input.png)."""
    record = json.loads((REPO / "data/surfaces" / f"{place}.json").read_text())
    takes = {**record.get("bake", {}).get("models", {}),
             **{model: claim["take"] for model, claim in record.get("elsewhere", {}).items()}}
    found = {}
    for model, take in sorted(takes.items()):
        picture = PROPS_HOME / "work/pixal" / f"{take}.svviews/input.png"
        if picture.exists():
            found[model] = "{home}/" + picture.relative_to(PROPS_HOME).as_posix()
    return found


def accepted_closeups(place):
    """{row: close-up pattern} of the place's accepted takes."""
    found = {}
    for model, closeup in accepted_models(place).items():
        found.setdefault(model.rsplit("_", 1)[0], closeup)
    return found


def calibration_set(place, code_builds):
    """{model: {"model", "closeup"}} the DINOv2 calibration scores: each accepted generated model the owner accepted
    (its made .gltf in the code builds' folder, the place's round's objects) with its close-up."""
    found = {}
    for model, closeup in accepted_models(place).items():
        made = pathlib.Path(code_builds) / f"{model}.gltf"
        if made.exists():
            found[model] = {"model": "{home}/" + made.relative_to(PROPS_HOME).as_posix(), "closeup": closeup}
    return found


def box_verdicts(scene):
    """The close-up stage's box gate on a scene's rows: {row: (result, why)}."""
    with prop_data.tools("props/scene", "props/closeup", "props", "props/cloud"):
        import box_check
        rows = box_check.gate(scene)["rows"]
        return {row: (found["result"] == box_check.PASS, found.get("why", "")) for row, found in rows.items()}


def code_build(row, code_builds):
    """A row's code build as a pattern, or None."""
    path = pathlib.Path(code_builds) / f"{row}_1.gltf"
    return "{home}/" + path.relative_to(PROPS_HOME).as_posix() if path.exists() else None


def parts_check_route(place, row):
    """The parts check as it was (method B, the comparison's fixed arm, never the sorter's route since #19): "code" for
    a plain kind or a listed fitting whose code build shows every part, else "model"."""
    with prop_data.tools("props/library"):
        import sorter
    kind = f"{place}_{row}"
    entry = sorter.fittings().get(kind.split("_", 1)[-1])
    plain = sorter.own_name(kind) in sorter.PLAIN
    return "code" if plain or (entry is not None and not sorter.missing_parts(entry)) else "model"


def prop_first_objects(place, inventory):
    """Every row with an accepted close-up (taken as it is) or a box the box gate passes (drawn by Pro), by the prop
    route; {row: entry}, and the rows left out with why."""
    drawn, boxes = accepted_closeups(place), box_verdicts(inventory["scene"])
    found, left = {}, {}
    for row in inventory["rows"]:
        passed, why = boxes.get(row["id"], (False, "no verdict"))
        if row["id"] in drawn or (row.get("box") and passed):
            found[row["id"]] = {"route": "prop", "take": f"{row['id']}-pf",
                                **({"closeup": drawn[row["id"]]} if row["id"] in drawn else {})}
        else:
            left[row["id"]] = f"no accepted close-up, and the box gate fails its box: {why}" if row.get("box") \
                else "no accepted close-up and no box"
    return found, left


def code_build_objects(place, objects, code_builds, closeups):
    """Every one of prop-first's objects that has a code build and a close-up, by its code build, with prop-first's
    accepted close-up: the code results both orders are derived from."""
    found = {}
    for row in objects:
        # the round's folder holds every model of the place; only a row the parts check builds in code has a code build
        build = code_build(row, code_builds) if parts_check_route(place, row) == "code" else None
        picture = closeups / f"{row}.png"
        if build and picture.exists():
            found[row] = {"route": "code", "code_model": build,
                          "closeup": "{home}/" + picture.relative_to(PROPS_HOME).as_posix()}
    return found


def bake_entry(place, row, details):
    """A make_chunky entry for a new take, as route.py plans one: the kind's turn, its size in the kit frame (x wide, y
    tall, z deep), its screens, cuts and decals, near density, its faces by size; its foot as high as its lowest laid
    spot stands (route.foot_of), so the kick wear reaches only what stands low. Foot 0 for every model made the ship's
    lamp, gauges and ceiling pieces, laid 0.75 to 2.15 m up, wear bare in boot scuffs (corner lamp dark_panel baked
    L* 51.7 against 19.2, 2026-10-15)."""
    with prop_data.tools("props/library", "props/gates", "props"):
        import route
    own = details.get(f"{place}_{row['id']}", {})
    size = [row["size"][0], row["size"][2], row["size"][1]]
    foot = min((route.foot_of(spot["y"]) for spot in row.get("at", [])), default=0.0)
    return {"base": own.get("turn", [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]), "size": size,
            "screens": own.get("screens", []), "cuts": own.get("cuts", []), "density": route.NEAR,
            "decals": own.get("decals", []), "foot": foot, "faces": route.faces_for(size)}


def surface_record(place, objects, rows, details):
    """The place's surface data for the order: its prop objects' takes, each baked as <row>_1 with its entry written
    out (the job is written in the bake, bake_job.py); no claims on other places."""
    record = json.loads((REPO / "data/surfaces" / f"{place}.json").read_text())
    by_id = {row["id"]: row for row in rows}
    prop = {row: entry for row, entry in objects.items() if entry["route"] == "prop"}
    takes = {entry["take"]: {"places": [place], "library_places": [place], "place": place, "kind": f"{place}_{row}",
                             "object": by_id[row]["name"]} for row, entry in prop.items()}
    bake = {"models": {f"{row}_1": entry["take"] for row, entry in prop.items()},
            "entries": {f"{row}_1": bake_entry(place, by_id[row], details) for row in prop}}
    return {"place": place, "library": record["library"], "takes": takes, "bake": bake, "elsewhere": {}}


def prop_first_closeups(place):
    """prop-first's accepted close-ups, copied out of its store into its folder; that folder."""
    store = Store.in_folder(order_folder(place, "prop-first") / "store")
    output = store.accepted(f"closeup@{place}")
    if output is None:
        raise SystemExit("prop-first's close-ups are not accepted yet: run prop-first first")
    target = order_folder(place, "prop-first") / "closeups"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(store.checkout(output) / "closeups", target)
    return target


def prepare(place, order, code_builds, sample=None):
    """The run's environment data: a copy of the repository's, with its prop data, surface data and inventory; with a
    sample, only those objects."""
    data = order_folder(place, order) / "data"
    if data.exists():
        raise SystemExit(f"{data} exists: a run is prepared once (remove its data folder to prepare it again)")
    shutil.copytree(REPO / "data", data)
    inventory = json.loads((data / "inventory" / f"{place}.json").read_text())
    objects, left = prop_first_objects(place, inventory)
    if sample:
        left.update({row: "outside the sample" for row in objects if row not in sample})
        objects = {row: entry for row, entry in objects.items() if row in sample}
    if order == "code-builds":
        objects = code_build_objects(place, objects, code_builds, prop_first_closeups(place))
    for row in inventory["rows"]:
        if objects.get(row["id"], {}).get("route") == "prop" and row["kind"] == "code":
            row["was"], row["kind"] = row["kind"], "generate"  # prop-first: the batch builds only generated rows
    (data / "inventory" / f"{place}.json").write_text(json.dumps(inventory, indent="\t") + "\n")
    (data / "props").mkdir(exist_ok=True)
    (data / "props" / f"{place}.json").write_text(json.dumps(
        {"place": place, "order": order, "objects": objects, "fallback": {}, "left_out": left,
         "accepted": calibration_set(place, code_builds)}, indent=1) + "\n")
    details = json.loads((data / "library/details.json").read_text())
    (data / "surfaces" / f"{place}.json").write_text(
        json.dumps(surface_record(place, objects, inventory["rows"], details), indent=1) + "\n")
    print(f"{order}: {sum(entry['route'] == 'prop' for entry in objects.values())} prop, "
          f"{sum(entry['route'] == 'code' for entry in objects.values())} code, {len(left)} left out; {data}")


def use_data(place, order):
    """Point the prop route's and the surface stage's environment data at the order's copy (their FOLDERs), in this
    process and the nodes it forks."""
    data = order_folder(place, order) / "data"
    prop_data.FOLDER, prop_data.DESIGN = data / "props", data / "props" / "no design"
    stages.surfaces.data.FOLDER, stages.surfaces.data.DESIGN = data / "surfaces", data / "surfaces" / "no design"
    return data


def runner_for(place, order):
    """The runner on the order's environment (its data, environment 1's seeds, home and repository) and its own store."""
    data = use_data(place, order)
    roots = {**stages.world1().roots, "data": str(data)}
    world = graph.Environment.from_file(stages.WORLD1, **roots)
    return graph.Runner(stages.STAGES, world, Store.in_folder(order_folder(place, order) / "store"))


def tag_of(place, order):
    return f"compare-{place}-{order}"


def tagging(place, order):
    """Tag every ledger line this run and its children write with the order's tag (ledger_tag/sitecustomize.py:
    in this process now, in every process it starts through PYTHONPATH)."""
    os.environ[TAG_VARIABLE] = tag_of(place, order)
    os.environ["PYTHONPATH"] = os.pathsep.join(filter(None, [str(LEDGER_TAG), os.environ.get("PYTHONPATH")]))
    spec = importlib.util.spec_from_file_location("ledger_tagging", LEDGER_TAG / "sitecustomize.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def without_closeup_failures(place, order, store):
    """The order's surface data less the takes of objects every Pro take failed (their prop route failed at the
    close-up; they go to code): set between the close-ups and Pixal3D, which reads it. The names dropped."""
    output = store.accepted(f"closeup@{place}")
    if output is None:
        return []
    kept = {path.stem for path in (store.checkout(output) / "closeups").glob("*.png")}
    path = order_folder(place, order) / "data/surfaces" / f"{place}.json"
    record = json.loads(path.read_text())
    dropped = sorted(model for model, take in record["bake"]["models"].items() if model.rsplit("_", 1)[0] not in kept)
    for model in dropped:
        record["takes"].pop(record["bake"]["models"].pop(model), None)
        record["bake"]["entries"].pop(model, None)
    if dropped:
        path.write_text(json.dumps(record, indent=1) + "\n")
    return dropped


def run(place, order, jobs):
    """Drive the place's line up to its likeness row, every ledger line it writes tagged with the order's tag: first to
    its close-ups, then, the takes of objects with none dropped from its surface data, the rest."""
    tagging(place, order)
    runner = runner_for(place, order)
    runner.drive([place], jobs=jobs, whole=False, only=["closeup", "likeness-calibration"])
    print(f"close-ups failed, to code: {without_closeup_failures(place, order, runner.store)}", flush=True)
    runner_for(place, order).drive([place], jobs=jobs, whole=False, only=["likeness"])


def likeness_output(place, order):
    """(the order's store, its likeness output, that output's folder): its accepted one, else its latest made; the
    output and folder None when it has none."""
    store = Store.in_folder(order_folder(place, order) / "store")
    node = NODE.format(place=place)
    output = store.accepted(node) or next((record["output"] for record in reversed(store.records(node))), None)
    return store, output, output and store.checkout(output)


def dinov2_scores(store, output):
    """The gathered DINOv2 scores of an output ({row: likeness}), or {}."""
    evidence = store.evidence_file("likeness", output) if output else None
    return json.loads(pathlib.Path(evidence).read_text()) if evidence else {}


def ledger_euros(tag):
    """Every cloud and Google ledger line tagged `tag`, in euros: a Google call started with no finished line (failed,
    killed) at its model's estimate, as google_spend counts the month."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import google_spend
    import ledger
    cloud = sum(entry.get("euros", 0) for entry in ledger.entries() if entry.get("tag") == tag)
    google = google_spend.LEDGER.read_text().splitlines() if google_spend.LEDGER.exists() else []
    calls = [json.loads(line) for line in google if line.strip()]
    calls = [call for call in calls if call.get("tag") == tag]
    finished = {call.get("call") for call in calls if call.get("state", "finished") == "finished"}
    pictures = sum(google_spend.estimate(call["model"]) if call.get("euros") is None else call["euros"]
                   for call in calls if call.get("state", "finished") == "finished")
    pictures += sum(call.get("estimate", 0) for call in calls
                    if call.get("state") == "started" and call.get("call") not in finished)
    return round(cloud + pictures, 2)


def least_likeness(store, place):
    """The DINOv2 least the order's accepted calibration set, or None."""
    output = store.accepted(f"likeness-calibration@{place}")
    return calibration_row.least(store.checkout(output)) if output else None


def results(place, run):
    """{row: route} of one run's likeness (prop-first: "prop" passed, "code" failed; code-builds: "code" passed,
    "builder" failed; "unknown" where a check could not tell), and its objects' records; None when it has no output."""
    store, output, made = likeness_output(place, run)
    if made is None:
        return None, {}
    return likeness_row.routes(made, dinov2_scores(store, output), least_likeness(store, place)), \
        likeness_row.objects(made)


def order_route(first, second):
    """An object's route in an order trying `first` then `second`, each (route it stands on when it passes, its result
    or None when that route has nothing for it): the first that passed, "unknown" when one before it could not tell,
    else "builder" (an agent writes one)."""
    for route, result in (first, second):
        if result == "unknown":
            return "unknown"
        if result == route:
            return route
    return "builder"


def derived(place, prop, code):
    """{row: {"prop-first", "code-first", "parts check"}} from the prop results and the code results: prop-first tries
    the prop route, then the object's code build; code-first follows the parts check (sorter.route): its code build
    first where the check says code, else the prop route first."""
    found = {}
    for row in sorted(prop):
        check = parts_check_route(place, row)
        prop_try, code_try = ("prop", prop[row]), ("code", code.get(row))
        first = (code_try, prop_try) if check == "code" and row in code else (prop_try, code_try)
        found[row] = {"prop-first": order_route(prop_try, code_try), "code-first": order_route(*first),
                      "parts check": check}
    return found


def sample_euros(place):
    """{what: euros} of the sample's runs from the tagged ledger lines: Pro's close-ups, the rest of prop-first
    (Pixal3D, the surface line, DINOv2) and the code-builds run (DINOv2)."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import google_spend
    tag = tag_of(place, "prop-first")
    calls = [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines() if line.strip()]
    closeups = sum(call.get("euros") or 0 for call in calls
                   if call.get("tag") == tag and call.get("caller") == "pro" and call.get("state") == "finished")
    total = ledger_euros(tag)
    return {"close-ups": round(closeups, 2), "generation": round(total - closeups, 2),
            "code checks": ledger_euros(tag_of(place, "code-builds"))}


def order_rows(place, routes, euros):
    """The table's line per order: objects passing by each route, needing a builder, untold; euros (the close-ups,
    which both orders need for their checks, the code checks, and generation shared over the objects each order sends
    the prop route); agent hours (agent-hours-<order>.json, {row: hours}; none recorded shows as such)."""
    rows = []
    for order in ORDERS:
        chosen = [entry[order] for entry in routes.values()]
        generated = sum(1 for entry in routes.values() if order == "prop-first" or entry["parts check"] != "code")
        hours_file = FOLDER / place / f"agent-hours-{order}.json"
        hours = json.loads(hours_file.read_text()) if hours_file.exists() else {}
        rows.append({"order": order, "objects": len(chosen), "passing prop route": chosen.count("prop"),
                     "passing code route": chosen.count("code"), "need a builder": chosen.count("builder"),
                     "cannot tell": chosen.count("unknown"),
                     "euros": round(euros["close-ups"] + euros["code checks"]
                                    + euros["generation"] * generated / max(1, len(routes)), 2),
                     "agent hours": round(sum(hours.values()), 2) if hours else "none recorded"})
    return rows


def page(place, rows, routes, prop_objects, euros):
    """The review page: the table, each object's route in both orders with its outline, the euros, the pick."""
    columns = list(rows[0])
    head = "".join(f"<th>{html.escape(name)}</th>" for name in columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row[name]))}</td>" for name in columns) + "</tr>"
                   for row in rows)
    detail = "".join(
        f"<tr><td>{html.escape(row)}</td><td>{html.escape(entry['parts check'])}</td>"
        f"<td>{html.escape(entry['prop-first'])}</td><td>{html.escape(entry['code-first'])}</td>"
        f"<td>{prop_objects[row].get('outline', prop_objects[row].get('missing', '-'))}</td></tr>"
        for row, entry in sorted(routes.items()))
    return (f"<title>Parts check order: {html.escape(place)}</title>"
            "<style>body{font:14px system-ui;margin:16px;background:#fff;color:#111}table{border-collapse:collapse}"
            "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}</style>"
            f"<h1>Prop-first or code-first: {html.escape(place)}, a sample of {len(routes)} objects</h1>"
            f"<table><tr>{head}</tr>{body}</table>"
            f"<p>Euros: {euros['close-ups']} close-ups (Pro), {euros['generation']} generation (Pixal3D, the "
            f"surface line, DINOv2), {euros['code checks']} code checks; generation is shared over the objects "
            "each order generates.</p><h2>Each object</h2><table><tr><th>object</th><th>parts check</th>"
            "<th>prop-first</th><th>code-first</th><th>prop model's outline</th></tr>" + detail + "</table>"
            + SAMPLE_NOTE +
            "<h2>Your pick</h2><p>Name the order you pick (prop-first or code-first) on the PRD's issue; the session "
            "that ran this records it there.</p>")


# What the hub's sample shows and does not (owner and captain, 2026-10-12: a sample for figure F3 and the paper, a
# EUR 12 + 5 budget, no remake of the 92 code-built objects this month).
SAMPLE_NOTE = (
    "<h2>What this sample shows, and what it does not</h2><ul>"
    "<li>It is a sample of the hub chosen to cover the kinds (thin, flat, round, boxy), cut by the budget: five "
    "objects went the whole prop route (close-up, Pixal3D, the surface line, the likeness gate) and eight more are "
    "the objects whose every Pro close-up failed the shape check, so their prop route failed at the close-up. It is "
    "not the hub's 54 objects and says nothing about the 20 objects with no close-up or box.</li>"
    "<li>Code builds are the hub's existing round-six builds; their checks (outline, DINOv2, parts, thin, lean) cost "
    "nothing new. Agent hours to write them were not recorded then, so none are shown.</li>"
    "<li>Both orders are derived from the same two result sets; neither was run separately.</li>"
    "<li>Moving world 1's 92 code-built objects to the prop route is not happening this month (owner): the prop route "
    "costs about EUR 2.2 an object (Pro close-up about 0.15, Pixal3D about 0.10 to 0.15, the surface line about 1.9 "
    "a take, DINOv2 about 0.001 a pair), about EUR 200 for 92.</li></ul>")


def table(place):
    """table.json and page.html from the prop-first and code-builds runs."""
    prop, prop_objects = results(place, "prop-first")
    code, _ = results(place, "code-builds")
    if prop is None:
        raise SystemExit("prop-first has no likeness output yet")
    routes = derived(place, prop, code or {})
    euros = sample_euros(place)
    rows = order_rows(place, routes, euros)
    out = FOLDER / place
    (out / "table.json").write_text(json.dumps({"rows": rows, "objects": routes, "euros": euros,
                                                "prop results": prop, "code results": code}, indent=1) + "\n")
    (out / "page.html").write_text(page(place, rows, routes, prop_objects, euros))
    for row in rows:
        print(json.dumps(row))
    print(f"wrote {out / 'table.json'} and {out / 'page.html'}")


def detach(argv, place, order):
    """This command again, less --detach, in a session of its own under detached.py; the log's path printed."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    log = detached.log_path_for(f"compare-{place}-{order}")
    command = [sys.executable, detached.__file__, "--log", str(log), "--outputs",
               str(order_folder(place, order) / "store/faults"), "--", sys.executable, "-m",
               "score.stages.props.compare", *[word for word in argv if word != "--detach"]]
    with open(log, "a") as result:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=result, stderr=subprocess.STDOUT,
                                   start_new_session=True, cwd=REPO)
    print(f"detached: started pid={process.pid} log={log}", flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("prepare", "run", "table"))
    parser.add_argument("place")
    parser.add_argument("order", nargs="?", choices=RUNS, help="the run: prop-first or code-builds")
    parser.add_argument("--sample", help="the objects, comma separated (prepare)")
    parser.add_argument("--code-builds", type=pathlib.Path)
    parser.add_argument("--jobs", type=int, default=graph.JOBS)
    parser.add_argument("--detach", action="store_true")
    options = parser.parse_args(argv)
    builds = options.code_builds or default_code_builds(options.place)
    if options.command in ("prepare", "run") and not options.order:
        parser.error(f"{options.command} needs a run")
    if options.command == "prepare":
        prepare(options.place, options.order, builds,
                set(options.sample.split(",")) if options.sample else None)
    elif options.command == "run" and options.detach:
        detach(argv, options.place, options.order)
    elif options.command == "run":
        run(options.place, options.order, options.jobs)
    else:
        table(options.place)


if __name__ == "__main__":
    main()
