"""The with/without comparison of the parts check's order on one place: prop-first (the owner's decision of 2026-10-12)
against code-first (the parts check as it was: code when a kind's code build shows every part, else the prop route).

    .venv/bin/python -m score.stages.props.compare prepare <place> prop-first [--code-builds <folder>]   # free
    .venv/bin/python -m score.stages.props.compare run <place> prop-first [--detach]                     # paid
    .venv/bin/python -m score.stages.props.compare fallback <place> [--code-builds <folder>]             # free
    .venv/bin/python -m score.stages.props.compare run <place> prop-first [--detach]                     # free: checks
    .venv/bin/python -m score.stages.props.compare prepare <place> code-first [--code-builds <folder>]   # free
    .venv/bin/python -m score.stages.props.compare run <place> code-first [--detach]                     # paid
    .venv/bin/python -m score.stages.props.compare table <place>                                         # free

Each order is a world of its own under $PROPS_HOME/compare/<place>/<order>/: a copy of the repository's data with the
order's prop data (data/props/<place>.json) and surface data, and a store of its own, so neither order touches world
1's store or data. `run` drives the place's line up to the likeness row with the stage table as it is (score.stages):
props-inputs, closeup, pixal, the surface line, likeness, each paid row cleared by the runner as in world 1.

- prop-first: every object of the place with a box or a close-up already drawn goes the prop route; its inventory
  copy marks every such row `generate` (the batch builds only generated rows). `fallback` then moves each prop object
  that failed its checks to code: to its code build (`--code-builds`, <row>_1.gltf) where one exists, else to none (a
  builder an agent must write), and `run` again checks them (the paid rows' keys do not move: they read only the prop
  objects' takes).
- code-first: the parts check routes each object (sorter.route): code where it says code and a code build exists,
  else the prop route. Its close-ups are prop-first's accepted ones, so both orders hold the same pictures; prepare it
  after prop-first's close-ups are accepted.

`table` writes table.json and page.html in $PROPS_HOME/compare/<place>/: per order the objects passing by each route,
those needing a builder, those a check could not tell, the euros (every cloud and Google ledger line tagged
compare-<place>-<order>: `run` tags every line it and its children write, ledger_tag/sitecustomize.py, so the
order's spend counts apart from world 1's lines running beside it) and the agent hours (agent-hours.json in
the order's folder, {row: hours}, written by the session that writes a builder; none recorded is shown as such),
and per object both orders' close-up, outline and route, for the owner's pick.
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
MARK = {"prop-first": "pf", "code-first": "cf"}
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
    """The parts check as it was (sorter.route): "code" or "model"."""
    with prop_data.tools("props/library"):
        import sorter
    return sorter.route(f"{place}_{row}")


def prop_first_objects(place, inventory):
    """Every row with an accepted close-up (taken as it is) or a box the box gate passes (drawn by Pro), by the prop
    route; {row: entry}, and the rows left out with why."""
    drawn, boxes = accepted_closeups(place), box_verdicts(inventory["scene"])
    found, left = {}, {}
    for row in inventory["rows"]:
        passed, why = boxes.get(row["id"], (False, "no verdict"))
        if row["id"] in drawn or (row.get("box") and passed):
            found[row["id"]] = {"route": "prop", "take": f"{row['id']}-{MARK['prop-first']}",
                                **({"closeup": drawn[row["id"]]} if row["id"] in drawn else {})}
        else:
            left[row["id"]] = f"no accepted close-up, and the box gate fails its box: {why}" if row.get("box") \
                else "no accepted close-up and no box"
    return found, left


def code_first_objects(place, objects, code_builds, closeups):
    """prop-first's objects routed by the parts check, each with prop-first's accepted close-up."""
    found = {}
    for row in objects:
        closeup = {"closeup": "{home}/" + (closeups / f"{row}.png").relative_to(PROPS_HOME).as_posix()}
        build = code_build(row, code_builds)
        if parts_check_route(place, row) == "code" and build:
            found[row] = {"route": "code", "code_model": build, **closeup}
        else:
            found[row] = {"route": "prop", "take": f"{row}-{MARK['code-first']}", **closeup}
    return found


def bake_entry(place, row, details):
    """A make_chunky entry for a new take, as route.py plans one: the kind's turn, its size in the kit frame (x wide, y
    tall, z deep), its screens, cuts and decals, near density, its faces by size; foot 0 (laid on its floor)."""
    with prop_data.tools("props/library", "props/gates", "props"):
        import route
    own = details.get(f"{place}_{row['id']}", {})
    size = [row["size"][0], row["size"][2], row["size"][1]]
    return {"base": own.get("turn", [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]), "size": size,
            "screens": own.get("screens", []), "cuts": own.get("cuts", []), "density": route.NEAR,
            "decals": own.get("decals", []), "foot": 0.0, "faces": route.faces_for(size)}


def surface_record(place, objects, rows, details):
    """The place's surface data for the order: its prop objects' takes, each baked as <row>_1 with its entry written
    out, on the place's own bake job; no claims on other places."""
    record = json.loads((REPO / "data/surfaces" / f"{place}.json").read_text())
    by_id = {row["id"]: row for row in rows}
    prop = {row: entry for row, entry in objects.items() if entry["route"] == "prop"}
    takes = {entry["take"]: {"places": [place], "library_places": [place], "place": place, "kind": f"{place}_{row}",
                             "object": by_id[row]["name"]} for row, entry in prop.items()}
    bake = {"job": record["bake"]["job"], "models": {f"{row}_1": entry["take"] for row, entry in prop.items()},
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


def prepare(place, order, code_builds):
    """The order's world data: a copy of the repository's, with its prop data, surface data and inventory."""
    data = order_folder(place, order) / "data"
    if data.exists():
        raise SystemExit(f"{data} exists: an order is prepared once (remove the folder to start it again)")
    shutil.copytree(REPO / "data", data)
    inventory = json.loads((data / "inventory" / f"{place}.json").read_text())
    objects, left = prop_first_objects(place, inventory)
    if order == "code-first":
        objects = code_first_objects(place, objects, code_builds, prop_first_closeups(place))
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
    """Point the prop route's and the surface stage's world data at the order's copy (their FOLDERs), in this
    process and the nodes it forks."""
    data = order_folder(place, order) / "data"
    prop_data.FOLDER = data / "props"
    stages.surfaces.data.FOLDER = data / "surfaces"
    return data


def runner_for(place, order):
    """The runner on the order's world (its data, world 1's seeds, home and repository) and its own store."""
    data = use_data(place, order)
    roots = {**stages.world1().roots, "data": str(data)}
    world = graph.World.from_file(stages.WORLD1, **roots)
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


def run(place, order, jobs):
    """Drive the place's line up to its likeness row, every ledger line it writes tagged with the order's tag."""
    tagging(place, order)
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


def fallback(place, code_builds):
    """prop-first's prop objects that failed their checks, moved to their code builds (none: a builder to write)."""
    store, output, folder = likeness_output(place, "prop-first")
    if folder is None:
        raise SystemExit("prop-first has no likeness output yet: run it first")
    path = order_folder(place, "prop-first") / "data/props" / f"{place}.json"
    record = json.loads(path.read_text())
    moved = {row: code_build(row, code_builds)
             for row, route in likeness_row.routes(folder, dinov2_scores(store, output)).items()
             if route == "code" and row not in record.get("fallback", {})}
    record["fallback"] = {**record.get("fallback", {}), **moved}
    path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"prop-first: {len(moved)} objects to code, {sum(build is None for build in moved.values())} without a "
          "builder")


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


def order_row(place, order):
    """One order's line of the table, and its objects' routes and outlines."""
    folder = order_folder(place, order)
    store, output, made = likeness_output(place, order)
    if made is None:
        return {"order": order, "ran": False}, {}
    record = json.loads((folder / "data/props" / f"{place}.json").read_text())
    found = likeness_row.routes(made, dinov2_scores(store, output), least_likeness(store, place))
    objects = likeness_row.objects(made)
    hours = json.loads((folder / "agent-hours.json").read_text()) if (folder / "agent-hours.json").exists() else {}
    def counted(route, made_by):
        return sum(1 for name, value in found.items() if value == route and objects[name]["route"] == made_by)
    row = {"order": order, "ran": True, "objects": len(found), "passing prop route": counted("prop", "prop"),
           "passing code route": counted("code", "code"), "failed prop, code not checked yet": counted("code", "prop"),
           "need a builder": counted("builder", "code"),
           "cannot tell": sum(value == "unknown" for value in found.values()), "euros": ledger_euros(tag_of(place, order)),
           "agent hours": round(sum(hours.values()), 2) if hours else None, "left out": len(record.get("left_out", {}))}
    return row, {name: {"route": found[name], "outline": entry.get("outline"), "made by": entry["route"]}
                 for name, entry in objects.items()}


def page(place, rows, per_object):
    """The review page: the table, then each object's route and outline in both orders, and how to give the pick."""
    columns = [key for key in rows[0] if key != "ran"] if rows and rows[0].get("ran") else ["order", "ran"]
    head = "".join(f"<th>{html.escape(name)}</th>" for name in columns)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(row.get(name, '')))}</td>" for name in columns) + "</tr>"
                   for row in rows)
    names = sorted({name for objects in per_object.values() for name in objects})
    detail = "".join(
        f"<tr><td>{html.escape(name)}</td>" + "".join(
            f"<td>{html.escape(str(per_object[order].get(name, {}).get('route', '-')))} "
            f"({per_object[order].get(name, {}).get('outline', '-')})</td>" for order in ORDERS) + "</tr>"
        for name in names)
    return (f"<title>Parts check order: {html.escape(place)}</title>"
            "<style>body{font:14px system-ui;margin:16px;background:#fff;color:#111}table{border-collapse:collapse}"
            "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}</style>"
            f"<h1>Prop-first or code-first: {html.escape(place)}</h1><table><tr>{head}</tr>{body}</table>"
            "<h2>Each object: route after its checks (best outline)</h2>"
            f"<table><tr><th>object</th>{''.join(f'<th>{order}</th>' for order in ORDERS)}</tr>{detail}</table>"
            "<h2>Your pick</h2><p>Name the order you pick (prop-first or code-first) on the PRD's issue; the session "
            "that ran this records it there.</p>")


def table(place):
    """table.json and page.html of both orders."""
    rows, per_object = [], {}
    for order in ORDERS:
        row, objects = order_row(place, order)
        rows.append(row)
        per_object[order] = objects
    out = FOLDER / place
    out.mkdir(parents=True, exist_ok=True)
    (out / "table.json").write_text(json.dumps({"rows": rows, "objects": per_object}, indent=1) + "\n")
    (out / "page.html").write_text(page(place, rows, per_object))
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
    parser.add_argument("command", choices=("prepare", "run", "fallback", "table"))
    parser.add_argument("place")
    parser.add_argument("order", nargs="?", choices=ORDERS)
    parser.add_argument("--code-builds", type=pathlib.Path)
    parser.add_argument("--jobs", type=int, default=graph.JOBS)
    parser.add_argument("--detach", action="store_true")
    options = parser.parse_args(argv)
    builds = options.code_builds or default_code_builds(options.place)
    if options.command in ("prepare", "run") and not options.order:
        parser.error(f"{options.command} needs an order")
    if options.command == "prepare":
        prepare(options.place, options.order, builds)
    elif options.command == "run" and options.detach:
        detach(argv, options.place, options.order)
    elif options.command == "run":
        run(options.place, options.order, options.jobs)
    elif options.command == "fallback":
        fallback(options.place, builds)
    else:
        table(options.place)


if __name__ == "__main__":
    main()
