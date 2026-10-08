"""What the stages wrote for one place, read back for its review page. Nothing here makes or changes a record: a stage
that wrote nothing reads as None, and the page says so.

The records of a place live in four kinds of folder, each written by its own stage:

    the repo           data/definitions/place.json (the style), data/inventory/<place>.json (the inventory, its boxes
                       on the concept's picture), data/kit/<place>.json (the layout), the library and its tokens
    a concept folder   plan.json (the concept's pick and the dimensioned plan's elements), plan.png, refs.json (the
                       creator's references), ledger.json (every concept take's prompt and cost), C<n>.png (the takes)
    a references folder the reference pictures as downloaded, named as in their URL
    a run folder       the route's work (tools/props/library/place_route.py): plan.json (the plan's elements),
                       closeups/<row>.png, pixal-list.txt (each take and the picture it was made from),
                       parts/<row>-<take>/ (labels.json and one .ply per library surface), plan-route.json, made/
                       (the baked models and the bake reports), checks.json, sweep.json
"""
import json
import pathlib
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools/props"))
sys.path.insert(0, str(REPO / "tools/props/library"))
import library  # noqa: E402
from paths import WORK  # noqa: E402

PLACES = REPO / "data/definitions/place.json"
INVENTORIES = REPO / "data/inventory"
KITS = REPO / "data/kit"


def json_or_none(path):
    return json.loads(path.read_text()) if path and path.exists() else None


def place_key(place):
    """The place.json entry a place is under: its own name, or a room's place as its inventory names it (the
    prologue's street is a room of the place `prologue_street`)."""
    places = json.loads(PLACES.read_text())
    if place in places:
        return place
    found = json_or_none(INVENTORIES / f"{place}.json") or {}
    return found.get("place", place)


def place_style(place):
    """The place's name and its style text, as the concept step left them in place.json."""
    entry = json.loads(PLACES.read_text())[place_key(place)]
    return {"name": entry.get("name", place), "style": entry["style"]["text"], "from": entry["style"].get("from", ""),
            "picked": entry["style"].get("picked", "")}


def work_path(written):
    """A path a record wrote under the framework's work folder (`WORK/...`) as a real path."""
    return WORK / written.removeprefix("WORK/") if written.startswith("WORK/") else pathlib.Path(written)


def inventory(place):
    """The approved inventory: its rows, and the picture each row's box is drawn on."""
    found = json_or_none(INVENTORIES / f"{place}.json")
    if found is None:
        return None
    views = {view["id"]: work_path(view["picture"]) for view in found["plan"]["views"]}
    return {"approved": found.get("approved", ""), "views": views, "rows": found["rows"]}


def kit(place):
    return json_or_none(KITS / f"{place}.json")


def concept(folder):
    """The concept step's records: the pick and why, the plan's elements, the takes and what each cost."""
    if folder is None:
        return None
    plan = json_or_none(folder / "plan.json") or {}
    ledger = json_or_none(folder / "ledger.json") or []
    takes = {entry["name"]: entry for entry in ledger}
    pictures = sorted(folder.glob("C*.png"), key=lambda path: int(path.stem[1:]) if path.stem[1:].isdigit() else 0)
    return {"pick": plan.get("concept", {}), "elements": plan.get("elements", []), "frame": plan.get("frame", ""),
            "plan_picture": folder / "plan.png" if (folder / "plan.png").exists() else None,
            "takes": [{"name": path.stem, "picture": path, "ledger": takes.get(path.stem)} for path in pictures],
            "references": json_or_none(folder / "refs.json") or []}


def reference_picture(reference, folder):
    """A reference's downloaded picture: the file named as the last part of its URL, None when not downloaded."""
    if folder is None:
        return None
    name = urllib.parse.unquote(reference["url"].rstrip("/").rsplit("/", 1)[-1]).removeprefix("File:")
    found = folder / name
    return found if found.exists() else None


def closeups(folder):
    """Each row's close-up: closeups/<row>.png, and a take made from another row's picture (pixal-list.txt: `<row>-<take>
    <picture> [flags]`, a torn leg's picture made into its strut and its foot) under its own row."""
    found = {path.stem: path for path in sorted((folder / "closeups").glob("*.png"))}
    listed = folder / "pixal-list.txt"
    for line in (listed.read_text().splitlines() if listed.exists() else []):
        fields = line.split()
        if len(fields) >= 2 and pathlib.Path(fields[1]).exists():
            found.setdefault(fields[0].rpartition("-")[0], pathlib.Path(fields[1]))
    return found


def latest_takes(parts):
    """Each row's newest labelled take: parts/<row>-<take>/ with a labels.json, the latest written per row."""
    found = {}
    for folder in sorted(parts.glob("*/labels.json"), key=lambda path: path.stat().st_mtime):
        row, _, take = folder.parent.name.rpartition("-")
        found[row] = {"take": take, "folder": folder.parent, "labels": json.loads(folder.read_text()),
                      "surfaces": sorted(folder.parent.glob("*.ply"))}
    return found


def kit_takes(folder):
    """A kit room's run (route.py): each generated model's labelled take where its bake job (job-chunky*.json) read
    it, by model name."""
    found = {}
    for job in sorted(folder.glob("job-chunky*.json")):
        for entry in json.loads(job.read_text()).get("chunky", []):
            take = pathlib.Path(entry["parts"])
            if (take / "labels.json").exists():
                found[entry["name"]] = {"take": take.name.rpartition("-")[2], "folder": take,
                                        "labels": json.loads((take / "labels.json").read_text()),
                                        "surfaces": sorted(take.glob("*.ply"))}
    return found


def bake_reports(made):
    """Every bake report in made/, oldest first: which models each bake wrote, so a rebake shows as a second entry."""
    return [{"name": path.stem.removeprefix("report-"), "models": json.loads(path.read_text())}
            for path in sorted(made.glob("report-*.json"), key=lambda path: path.stat().st_mtime)]


def run(folder):
    """One run of the route over the place: what each of its stages wrote, None where a stage has not run."""
    if folder is None:
        return None
    made = (folder / "made").resolve()  # a run folder may link its made models from the route's work folder
    plan = json_or_none(folder / "plan.json") or {}
    # A kit room's run (route.py) writes its route's plan as plan.json, its models and pieces; an outdoor place's
    # (place_route.py) writes plan-route.json, and plan.json is the dimensioned plan's elements.
    kit_run = "models" in plan and not (folder / "plan-route.json").exists()
    takes = kit_takes(folder) if kit_run else latest_takes(folder / "parts") if (folder / "parts").exists() else {}
    return {
        "folder": folder,
        "kit": kit_run,
        "plan": None if kit_run else plan or None,
        "closeups": closeups(folder),
        "takes": takes,
        "planned": plan if kit_run else json_or_none(folder / "plan-route.json"),
        "models": {path.stem: path for path in sorted(made.glob("*.gltf"))} if made.exists() else {},
        "bakes": bake_reports(made) if made.exists() else [],
        "checks": json_or_none(folder / "checks.json"),
        "sweep": json_or_none(folder / "sweep.json"),
    }


def surfaces(place):
    """Every library surface as the place paints it: family, recipe, token and colour (linear RGB)."""
    return library.by_library(place_key(place))
