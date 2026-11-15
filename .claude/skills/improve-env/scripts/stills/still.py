"""Plan a place's film as demo_film's make plans it (main 89540abae) and write the job for its first frame alone.

    python still.py <place> <stage folder (tree/<place>)> <work folder>

Writes <work>/still.json: {"place", "film", "camera", "view", "stage_usda", "listing", "frames", "people_in_stage",
"people_in_view", "design_people", "moves"}. Nothing rendered here.
"""
import json
import os
import pathlib
import shutil
import sys

os.environ.setdefault("PROPS_HOME", str(pathlib.Path("~/.score-this-pc").expanduser()))
REPO = pathlib.Path(os.environ["SCORE_REPO"])  # the score checkout the stills are planned with
sys.path[:0] = [str(REPO / "tools/review"), str(REPO / "tools/usd"), str(REPO)]
import demo  # noqa: E402

demo.planned_with = lambda: "89540abae"  # the scratch copy of main at 89540abae is no git checkout
from score.stages import demo_film  # noqa: E402
from score.stages.demo_film import final, shots  # noqa: E402


def film_record(place):
    """The place's own film as the locked scripts (else the starters in data/films) show it; {} with none."""
    starters = {path.stem: json.loads(path.read_text()) for path in sorted((REPO / "data/films").glob("*.json"))}
    locked = demo_film.films_of(final.scripts())
    if place in locked:
        return place, locked[place], "locked script " + locked[place]["script"]
    found = demo_film.films_of(starters)
    if place in found:
        return place, found[place], "starter script " + found[place]["script"] + " (not locked)"
    return place, {}, "no film script shows it: the scene record's first camera"


def linked_copy(stage_folder, place, under):
    """under/<place>: the root layer and scene.json copied, everything else linked; sibling places linked beside."""
    target = under / place
    shutil.rmtree(under, ignore_errors=True)
    target.mkdir(parents=True)
    for entry in stage_folder.iterdir():
        if entry.name in (f"{place}.usda", "scene.json"):
            shutil.copyfile(entry, target / entry.name)
        else:
            (target / entry.name).symlink_to(entry.resolve())
    for sibling in stage_folder.parent.iterdir():
        if sibling.name != place and sibling.is_dir():
            (under / sibling.name).symlink_to(sibling.resolve())
    return target


def main(place, stage_folder, work):
    work.mkdir(parents=True, exist_ok=True)
    name, film, source = film_record(place)
    copy = linked_copy(stage_folder, place, work / "stages")
    cameras = demo_film.own_cameras(copy / "scene.json", film)
    demo_film.leave_out(copy / f"{place}.usda", film)
    start = demo_film.film_start(film)
    given = f"{place}={','.join(cameras)}"
    jobs = demo.plan(work, work / "stages", [given], jobs_each=1, size=demo_film.SIZE, ink=False, shots=len(cameras),
                     seconds=demo_film.SECONDS, start=start)
    planned = json.loads((work / "views" / f"{name}.json").read_text())
    demo_film.motion_blurred(jobs, planned["views"], demo_film.SIZE[0])
    job = json.loads(pathlib.Path(jobs[0]).read_text())
    dealt = json.loads(pathlib.Path(job["args"][1]).read_text())
    first = planned["views"][0]["name"]
    view = next(item for item in dealt["views"] if item["name"] == first)
    listing = work / "first.json"
    listing.write_text(json.dumps({"size": dealt["size"], "views": [view]}, indent=1))
    stage = pathlib.Path(job["args"][0])
    seen = shots.people_seen(stage, [view])
    rows = REPO / "data/people/rows.json"
    found = {"place": place, "film": name, "film_source": source, "cameras": cameras, "start": start,
             "view": view, "stage_usda": str(stage), "listing": str(listing), "frames": str(work / "frames"),
             "script": job["script"], "people_in_stage": seen is not None,
             "people_in_view": bool(seen and any(seen.values())),
             "design_people": demo_film.cast_people(place, rows if rows.exists() else None),
             "moves": planned["moves"]}
    (work / "still.json").write_text(json.dumps(found, indent=1))
    print(json.dumps({key: found[key] for key in ("place", "film_source", "cameras", "people_in_stage",
                                                    "people_in_view", "design_people")}))


if __name__ == "__main__":
    main(sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]))
