"""The inventory box check: whether a scene inventory's boxes really sit on the things their rows name in the concept.

    .venv/bin/python tools/props/scene/box_check.py [<scene> ...]                    # the measurements, every scene
    .venv/bin/python tools/props/scene/box_check.py <scene> ... --judge <folder> [--dry-run]

A scene inventory is the concept partitioned: every row's box is where its thing stands in its view's picture
(`inventory.py`). Boxes guessed rather than drawn on the picture crowd into one corner and cover the wrong things
(the camp's, 2026-10-09: round numbers that reached only x 1900, y 900 of a 2752 x 1536 concept). Three
parts, the measured ones first and the judge only where they cannot tell:

  measured  plain Python on each view's picture: every box lies inside it; a box over WHOLE of the picture marks
            nothing and always fails (a row that repeats round the room, a wall panel or a pipe run, boxes one clear
            example and says so in `repeats`, the coordinator's rule of 2026-10-09); the boxes cover at least COVER_PER_ROW of the picture for each
            row, up to COVER_ENOUGH (from COVER_FROM boxes on); and they are not all in one corner (no more than
            FULLEST_QUADRANT of the covered area in one quarter of the picture, and spread over at least SPREAD of
            its width or of its height).
  masked    with --masks, SAM 3 on a rented card (box_masks.py) masks each row's noun on the picture, and code
            checks that one of the masks lies mostly inside the box and fills a fair share of it; a box far bigger
            than the thing inside it is loose, one with the thing only elsewhere is off, and where SAM 3 finds
            nothing that says anything (or takes the whole room for the thing), the judge decides.
  judged    the open judge (../cloud/judge.py, the close-up check's model) sees the whole concept with the box drawn
            on it and the box's crop, and says whether the crop shows the row's thing; each question is asked with
            check.SEEDS and the majority decides (the third seed only where the first two disagree, since it cannot
            change an agreed majority). The questions and crops go under the --judge folder, the answers
            in its answers/ folder; a question already answered is not asked again.

--tighten (with --masks) sets each loose box to the SAM 3 instance inside it, in the inventory itself.

gate(scene) is the box gate (pass, fail or unknown, unknown blocking) that the close-up stage and the completion gate
run: a box must come from partition.py's proposals and be grounded by SAM 3 or passed by the judge on that very box.

A row the concept does not show carries `"box": null` and `"unseen": "<why>"` (inventory.py) and is not checked here.
"""
import argparse
import json
import re
import pathlib
import sys

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "closeup"))
sys.path.insert(0, str(HERE.parent / "cloud"))
import check  # noqa: E402
import inventory  # noqa: E402
from paths import WORK  # noqa: E402

# A box over this share of its picture marks no place in it.
WHOLE = 0.8
# The kit groups whose pieces repeat round the whole room: each such row boxes one clear example and carries
# `"repeats": "across the room"`.
ROOM_WIDE = ("kit: wall", "kit: floor", "kit: ceiling", "kit: pipe")
# The share of the picture a view's boxes should cover for each row boxed on it, and the cover that is always enough
# (a picture with many rows is not expected to be covered whole). Set on the 17 world-1 places, 2026-10-09: the
# well-boxed views cover 0.09 (the hangar: 18 small things in a hall round its ship) to 0.89 of their picture.
COVER_PER_ROW = 0.004
COVER_ENOUGH = 0.06
# Fewer boxes than this on a view are not held to a cover: a few far things (the launch's ferry, pad, mast and lamp
# on a wide harbour view) are rightly small.
COVER_FROM = 5
# One corner: the share of the covered area in the fullest quarter of the picture (the camp's door dome 0.77, the
# well-boxed views 0.48 at most), and the share of the picture's width or height the boxes must span between them.
FULLEST_QUADRANT = 0.6
SPREAD = 0.6
# The covered area is measured on a grid of this many pixels a cell.
CELL = 8
# The judge's question about one box. Image 1 is the whole concept with the box drawn in red, image 2 the box's crop.
QUESTION = """You check where an object was marked on a concept painting of a place.
Image 1 is the whole painting, with one box drawn on it in red. Image 2 is what is inside that box, enlarged.
This is a quick check: think briefly.
The box should mark: {words}. Its real size is about {wide:.2f} m wide, {deep:.2f} m deep and {tall:.2f} m tall.

Decide:
1. shows: the thing named is clearly in the box (image 2), not only somewhere else in the painting.
2. main: it is the main thing in the box: the box is drawn round it, not round a neighbour or a stretch of
   wall or floor that happens to include a corner of it. A long or repeating thing (a pipe run, a row of lamps,
   cables) passes when the box covers a good part of it.
3. what: in a few words, what the box is mostly drawn round.

After your thinking, answer with one JSON object and nothing after it:
{{"shows": true, "main": true, "what": "a grey steel locker"}}"""
SEEDS = check.SEEDS
# A box is grounded by a SAM 3 instance of its noun with at least MASK_INSIDE of the mask inside the box, filling at
# least MASK_FILLS of it (a lamp's glow, a desk's shadow and the room round a thing keep the fill under a whole box).
MASK_INSIDE = 0.5
MASK_FILLS = 0.15
# An instance whose box covers more than this share of the picture is SAM 3 taking the room for the thing.
BROAD = 0.5
# The whole concept is sent this wide, the crop at least this long on its longer side.
OVERVIEW_WIDE = 1376
SHORTEST_CROP = 512
CROP_MARGIN = 0.1


def picture_path(written):
    """A view's picture as a real path: `WORK/...` under the framework's work folder, else as written."""
    return WORK / written.removeprefix("WORK/") if written.startswith("WORK/") else pathlib.Path(written)


def is_whole(box, size):
    wide, tall = size
    return (box[2] - box[0]) * (box[3] - box[1]) > WHOLE * wide * tall


def box_problems(row, size):
    """What is wrong with one row's box on a picture of `size` (wide, tall), one line each."""
    box, wide, tall = row["box"], *size
    found = []
    if not (0 <= box[0] < box[2] <= wide and 0 <= box[1] < box[3] <= tall):
        found.append(f"row {row['id']}: its box {box} is not inside the picture ({wide} x {tall})")
    if is_whole(box, size):
        found.append(f"row {row['id']}: its box is the whole picture, which marks nothing; box the thing (one clear "
                     "example of a row that repeats), or mark the row unseen with why")
    return found


def covered(boxes, size):
    """The grid of cells the boxes cover, as rows of booleans."""
    columns, lines = -(-size[0] // CELL), -(-size[1] // CELL)
    grid = [[False] * columns for _ in range(lines)]
    for left, top, right, bottom in boxes:
        for line in range(max(0, int(top) // CELL), min(lines, -(-int(bottom) // CELL))):
            for column in range(max(0, int(left) // CELL), min(columns, -(-int(right) // CELL))):
                grid[line][column] = True
    return grid


def quadrant_shares(grid):
    """The share of the covered cells in each quarter of the picture: top left, top right, bottom left, bottom
    right."""
    lines, columns = len(grid), len(grid[0])
    counts = [0, 0, 0, 0]
    for line, cells in enumerate(grid):
        for column, cell in enumerate(cells):
            if cell:
                counts[2 * (line >= lines // 2) + (column >= columns // 2)] += 1
    total = sum(counts)
    return [count / total for count in counts] if total else counts


def spread_problems(view, boxes, size):
    """What is wrong with how a view's boxes lie over its picture, one line each: too little covered for its rows, or
    all in one corner."""
    if len(boxes) < COVER_FROM:  # a few boxes are not judged for cover or corners
        return []
    wide, tall = size
    grid = covered(boxes, size)
    cover = sum(map(sum, grid)) / (len(grid) * len(grid[0]))
    found = []
    wanted = min(COVER_ENOUGH, COVER_PER_ROW * len(boxes))
    if cover < wanted:
        found.append(f"view {view}: its {len(boxes)} boxes cover {cover:.2f} of the picture, under the {wanted:.2f} "
                     "its rows suggest")
    fullest = max(quadrant_shares(grid))
    if fullest > FULLEST_QUADRANT:
        found.append(f"view {view}: {fullest:.2f} of what its boxes cover is in one quarter of the picture")
    across = (max(box[2] for box in boxes) - min(box[0] for box in boxes)) / wide
    down = (max(box[3] for box in boxes) - min(box[1] for box in boxes)) / tall
    if across < SPREAD and down < SPREAD:
        found.append(f"view {view}: its boxes span only {across:.2f} of the picture's width and {down:.2f} of its "
                     "height")
    return found


def boxed_rows(found, view):
    return [row for row in found["rows"] if row.get("view") == view and row.get("box")]


def measured_problems(found, sizes):
    """Every measured problem of an inventory's boxes, one line each; `sizes` is each view's picture size, None
    where the picture is missing."""
    problems = []
    for view, size in sizes.items():
        if size is None:
            problems.append(f"view {view}: its picture is missing")
            continue
        rows = boxed_rows(found, view)
        for row in rows:
            problems.extend(box_problems(row, size))
        problems.extend(spread_problems(view, [row["box"] for row in rows if not is_whole(row["box"], size)], size))
    return problems


def view_sizes(found):
    """Each view's picture size, None where the picture is missing."""
    sizes = {}
    for view in found.get("plan", {}).get("views", []):
        path = picture_path(view["picture"])
        sizes[view["id"]] = Image.open(path).size if path.exists() else None
    return sizes


# --- the judge -------------------------------------------------------------------------------------------------------

def question(row):
    wide, deep, tall = row["size"]
    return QUESTION.format(words=row["name"], wide=wide, deep=deep, tall=tall)


def overview(picture, box):
    """The whole concept, OVERVIEW_WIDE wide, with the box drawn on it in red."""
    scale = OVERVIEW_WIDE / picture.width
    shown = picture.convert("RGB").resize((OVERVIEW_WIDE, round(picture.height * scale)), Image.LANCZOS)
    ImageDraw.Draw(shown).rectangle([round(value * scale) for value in box], outline=(255, 0, 0), width=4)
    return shown


def crop(picture, box):
    """The box's crop with a little margin, at least SHORTEST_CROP long."""
    margin = CROP_MARGIN * max(box[2] - box[0], box[3] - box[1])
    cut = picture.convert("RGB").crop((max(0, box[0] - margin), max(0, box[1] - margin),
                                       min(picture.width, box[2] + margin), min(picture.height, box[3] + margin)))
    if max(cut.size) < SHORTEST_CROP:
        scale = SHORTEST_CROP / max(cut.size)
        cut = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.LANCZOS)
    return cut


def judge_rows(found, sizes):
    """The rows the judge looks at: every boxed row whose box marks a place (not a kit row's whole picture)."""
    return [row for view, size in sizes.items() if size for row in boxed_rows(found, view)
            if not is_whole(row["box"], size)]


def judge_jobs(scene, found, sizes, folder, seeds):
    """The judge's questions for one inventory, one for each of `seeds` a box, each row's two pictures written under
    folder/pictures/."""
    pictures = folder / "pictures"
    pictures.mkdir(parents=True, exist_ok=True)
    views = {view["id"]: picture_path(view["picture"]) for view in found["plan"]["views"]}
    jobs = []
    for row in judge_rows(found, sizes):
        key = f"{scene}.{row['id']}.{'-'.join(str(round(value)) for value in row['box'])}"
        whole, cut = pictures / f"{key}.whole.jpg", pictures / f"{key}.crop.jpg"
        if not cut.exists():
            picture = Image.open(views[row["view"]])
            overview(picture, row["box"]).save(whole, quality=88)
            crop(picture, row["box"]).save(cut, quality=90)
        jobs.extend({"name": f"{key}~{seed}", "seed": seed, "text": question(row), "images": [str(whole), str(cut)]}
                    for seed in seeds)
    return jobs


def deciding_jobs(jobs, answers):
    """The third seed's questions for the boxes whose first two answers disagree: when they agree, the third cannot
    change the majority of three, so it is not asked (it halves what the check costs)."""
    split = []
    for job in (job for job in jobs if job["seed"] == SEEDS[0]):
        key = job["name"].rpartition("~")[0]
        replies = [answers / f"{key}~{seed}.txt" for seed in SEEDS[:2]]
        if all(reply.exists() for reply in replies) and len({shown(reply.read_text()) for reply in replies}) > 1:
            split.append(dict(job, name=f"{key}~{SEEDS[2]}", seed=SEEDS[2]))
    return split


def shown(reply):
    """Whether one of the judge's replies says the box is drawn round the thing its row names."""
    answer = check.answer_of(reply)
    return bool(answer and answer.get("shows") and answer.get("main"))


def verdict(replies):
    """A box's verdict from the judge's replies: passes when most say the thing is shown and is the main thing in the
    box; with what the first failing answer says the box is drawn round."""
    failing = [reply for reply in replies if not shown(reply)]
    return {"passes": len(failing) * 2 < len(replies), "passed": len(replies) - len(failing), "of": len(replies),
            "what": next(((check.answer_of(reply) or {}).get("what", "no answer") for reply in failing), "")}


def verdicts(jobs, answers):
    """Each judged box's verdict by its key, from the answers folder: from all three seeds' answers, or from the first
    two when they agree; a box not answered that far is left out."""
    found = {}
    for key in sorted({job["name"].rpartition("~")[0] for job in jobs}):
        replies = [answers / f"{key}~{seed}.txt" for seed in SEEDS]
        first_two = [reply.read_text() for reply in replies[:2] if reply.exists()]
        if len(first_two) < 2:
            continue
        if replies[2].exists():
            found[key] = verdict(first_two + [replies[2].read_text()])
        elif len({shown(reply) for reply in first_two}) == 1:
            found[key] = verdict(first_two)
    return found


# --- the measurement: SAM 3's masks -----------------------------------------------------------------------------------

def noun(name):
    """The short name SAM 3 is asked for: a row's words up to their first colon, comma, bracket or qualifying
    phrase ("stainless galley counter: worktop with hob" asks for "stainless galley counter")."""
    short = re.split(r"[:,(;]| with | on a | on its | in a | for | from | of | over | beside | by ", name,
                     maxsplit=1)[0].strip()
    return re.sub(r"^(a|an|the|one|two|three|four|six) ", "", short, flags=re.I)


def nouns(name):
    """The words SAM 3 is asked for a row: its short name and, when that is longer, its last word alone (SAM 3 finds
    "panel" where it finds nothing for "plain lower wall panel")."""
    short = noun(name)
    head = short.split()[-1] if short.split() else short
    return [short] if head == short else [short, head]


def mask_jobs(scene, found, sizes):
    """box_masks.py's jobs for one inventory: each view's picture with its judged rows' words and boxes."""
    views = {view["id"]: picture_path(view["picture"]) for view in found["plan"]["views"]}
    rows = [row for view, size in sizes.items() if size for row in boxed_rows(found, view)]
    return [{"picture": str(views[view]), "rows": [{"key": f"{scene}.{row['id']}", "nouns": nouns(row["name"]),
                                                    "box": row["box"]} for row in rows if row["view"] == view]}
            for view in views if any(row["view"] == view for row in rows)]


def grounding(instances, size):
    """A box measured against SAM 3's instances of its row's noun on a picture of `size`. An instance over BROAD of
    the picture says nothing (SAM 3 took the whole room for "hygiene cubicle"). "grounded": an instance lies mostly
    inside the box (MASK_INSIDE) and fills a fair share of it (MASK_FILLS); "loose": the thing is inside the box but
    the box is far bigger than it (a keyboard's row boxed with its whole desk), with the instance's box as the
    measured one; "off": SAM 3 finds the thing only outside the box, with where its surest instance is; "not found"
    when it found none that says anything, which leaves the box to the judge."""
    wide, tall = size
    telling = [item for item in instances
               if (item["box"][2] - item["box"][0]) * (item["box"][3] - item["box"][1]) < BROAD * wide * tall]
    if not telling:
        return {"grounding": "not found"}
    if any(item["inside"] >= MASK_INSIDE and item["fills"] >= MASK_FILLS for item in telling):
        return {"grounding": "grounded"}
    within = [item for item in telling if item["inside"] >= MASK_INSIDE]
    if within:
        return {"grounding": "loose", "found_at": within[0]["box"]}
    return {"grounding": "off", "found_at": telling[0]["box"]}


# --- the gate: pass, fail or unknown for every box, before any close-up is drawn -----------------------------------

PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"
# Where a scene's partition (partition.py) and its box results live: WORK/partition/<scene>/.
PARTITION = WORK / "partition"
# A box with every corner on a multiple of this, and no proposal it came from, was typed.
ROUND = 10


def results_path(scene):
    return PARTITION / scene / "boxes.json"


def typed(row):
    """Whether a row's box was typed rather than measured: no proposal it came from and round numbers."""
    return not row.get("box_from") and all(value % ROUND == 0 for value in row["box"])


def from_proposals(row, proposals):
    """Whether a row's box is the box round the proposals it names."""
    by_id = {proposal["id"]: proposal for proposal in proposals}
    picked = [by_id[name] for name in row.get("box_from", []) if name in by_id]
    if not picked or len(picked) != len(row["box_from"]):
        return False
    union = [min(item["box"][0] for item in picked), min(item["box"][1] for item in picked),
             max(item["box"][2] for item in picked), max(item["box"][3] for item in picked)]
    return union == list(row["box"])


def row_verdict(row, size, proposals, recorded):
    """One row's gate verdict and why. Fail: a box outside its picture or the whole picture, a typed box, a box that
    is not the box round the proposals it names, or a box the measurement or the judge failed. Pass: a box from its
    proposals that SAM 3 grounded or the judge passed. Unknown, which blocks like a fail: anything not yet
    measured, or measured on a box that has changed since."""
    if row.get("box") is None:
        return (PASS, f"not in the concept: {row['unseen']}") if row.get("unseen") else (FAIL, "no box, no reason")
    problems = box_problems(row, size)
    if problems:
        return FAIL, "; ".join(problems)
    if typed(row):
        return FAIL, "typed: round numbers and no proposal it came from"
    if not row.get("box_from"):
        return UNKNOWN, "not measured: no proposal it came from (partition.py)"
    if proposals is None:
        return UNKNOWN, "its proposals are not on this machine"
    if not from_proposals(row, proposals):
        return FAIL, "its box is not the box round the proposals it names"
    found = recorded.get(row["id"])
    if not found or found.get("box") != list(row["box"]):
        return UNKNOWN, "not checked by SAM 3 or the judge on this box"
    return (PASS if found["passes"] else FAIL), found["by"]


def gate(scene, found=None):
    """The box gate for one scene: {"result", "rows": {row: {"result", "why"}}, "views": [problems]}. A view whose
    boxes crowd one corner fails the scene; any failing row fails it; any unknown row makes it unknown."""
    found = found if found is not None else json.loads(inventory.path_of(scene).read_text())
    sizes = view_sizes(found)
    proposals_file = PARTITION / scene / "proposals.json"
    proposals = json.loads(proposals_file.read_text()) if proposals_file.exists() else None
    recorded = json.loads(results_path(scene).read_text()) if results_path(scene).exists() else {}
    rows = {}
    for row in found["rows"]:
        size = sizes.get(row.get("view"))
        verdict, why = (UNKNOWN, "its view's picture is missing") if size is None and row.get("box") else \
            row_verdict(row, size, proposals, recorded)
        rows[row["id"]] = {"result": verdict, "why": why}
    views = [problem for problem in measured_problems(found, sizes) if problem.startswith("view ")]
    verdicts = {entry["result"] for entry in rows.values()}
    result = FAIL if views or FAIL in verdicts else UNKNOWN if UNKNOWN in verdicts else PASS
    return {"result": result, "rows": rows, "views": views}


def measured_boxes(folders):
    """The box each `<scene>.<row>` was measured or judged on, from the mask jobs and the judge's questions in the
    given work folders."""
    boxes = {}
    for folder in (folder for folder in folders if folder):
        jobs = folder / "mask-jobs.json"
        for job in json.loads(jobs.read_text()) if jobs.exists() else []:
            boxes.update({row["key"]: list(row["box"]) for row in job["rows"]})
        for listing in folder.glob("questions-*.json"):
            for question in json.loads(listing.read_text()):
                key, _, box = question["name"].rpartition("~")[0].rpartition(".")
                boxes.setdefault(key, [int(value) for value in box.split("-")])
    return boxes


def record_results(results, measured):
    """Write each scene's decided boxes (decided()) to WORK/partition/<scene>/boxes.json with the box each was decided
    on (`measured`), so a box changed since reads as unknown."""
    by_scene = {}
    for key, result in results.items():
        scene, row = key.split(".", 1)
        if result["passes"] is None or key not in measured:
            continue
        by_scene.setdefault(scene, {})[row] = {"passes": result["passes"], "by": result["by"], "box": measured[key]}
    for scene, rows in by_scene.items():
        path = results_path(scene)
        path.parent.mkdir(parents=True, exist_ok=True)
        kept = json.loads(path.read_text()) if path.exists() else {}
        kept.update(rows)
        path.write_text(json.dumps(kept, indent=1))


# --- the command -----------------------------------------------------------------------------------------------------

def measure_all(scenes):
    """Each scene's measured problems, printed; the scenes with any."""
    failing = []
    for scene in scenes:
        found = json.loads(inventory.path_of(scene).read_text())
        problems = measured_problems(found, view_sizes(found))
        print(f"{scene}: {'passes' if not problems else 'FAILS'}")
        for problem in problems:
            print(f"  {problem}")
        if problems:
            failing.append(scene)
    return failing


def judge_all(scenes, folder, dry_run, cards, unmeasured=None):
    """Ask the judge about every box of the scenes, or only those in `unmeasured` (`<scene>.<row>` keys SAM 3 could
    not measure), two seeds and then the third where they disagree; print and write (folder/verdicts.json) each box's
    verdict."""
    import judge
    jobs = []
    for scene in scenes:
        found = json.loads(inventory.path_of(scene).read_text())
        jobs.extend(job for job in judge_jobs(scene, found, view_sizes(found), folder, SEEDS[:2])
                    if unmeasured is None or job["name"].rpartition("~")[0].rsplit(".", 1)[0] in unmeasured)
    answers = folder / "answers"
    for round_number, listed in ((1, jobs), (2, None)):
        listed = listed if listed is not None else deciding_jobs(jobs, answers)
        if not listed:
            continue
        listing = folder / f"questions-{round_number}.json"
        listing.write_text(json.dumps(listed, indent=1))
        judge.ask(listing, answers, dry_run, cards)
    found = verdicts(jobs, answers)
    (folder / "verdicts.json").write_text(json.dumps(found, indent=1))
    for key, result in found.items():
        if not result["passes"]:
            print(f"{key}: {result['passed']} of {result['of']} answers passed; the box is round {result['what']}")
    return found


def mask_all(scenes, folder, dry_run):
    """Mask every box's noun with SAM 3 on a rented card, then print and write (folder/grounding.json) each box's
    grounding."""
    import box_masks_cloud
    jobs = []
    for scene in scenes:
        found = json.loads(inventory.path_of(scene).read_text())
        jobs.extend(mask_jobs(scene, found, view_sizes(found)))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mask-jobs.json").write_text(json.dumps(jobs, indent=1))
    if not (folder / "masks.json").exists():
        box_masks_cloud.mask(folder / "mask-jobs.json", folder / "masks.json", dry_run)
    if not (folder / "masks.json").exists():
        return {}
    measured = json.loads((folder / "masks.json").read_text())
    sizes = {job_row["key"]: Image.open(job["picture"]).size for job in jobs for job_row in job["rows"]}
    found = {key: grounding(instances, sizes[key]) for key, instances in measured.items()}
    (folder / "grounding.json").write_text(json.dumps(found, indent=1))
    for key, result in found.items():
        if result["grounding"] in ("off", "loose"):
            print(f"{key}: {result['grounding']}; SAM 3's instance at {result['found_at']}")
    return found


def tighten(scene, found, grounded):
    """Each loose box of an inventory set to the SAM 3 instance inside it (the thing the row names, measured; for a
    row that repeats, one clear example of it); the rows changed."""
    changed = []
    for row in found["rows"]:
        result = grounded.get(f"{scene}.{row['id']}", {})
        if result.get("grounding") == "loose":
            row["box"] = list(result["found_at"])
            changed.append(row["id"])
    return changed


def decided(grounded, judged):
    """Each box's result, the measurement first: a box SAM 3 grounds passes and one it finds loose or off fails,
    whatever the judge says (a model's judgement of geometry is near a coin flip, LEGO-Anything 2026, Sec. 5.1); the
    judge decides only the boxes SAM 3 could not measure. Keys are `<scene>.<row>`; a box neither measured nor
    judged is "unchecked"."""
    judged_rows = {key.rsplit(".", 1)[0]: result for key, result in judged.items()}
    results = {}
    for key in sorted(set(grounded) | set(judged_rows)):
        measure = grounded.get(key, {"grounding": "not found"})["grounding"]
        if measure != "not found":
            results[key] = {"passes": measure == "grounded", "by": f"SAM 3: {measure}"}
        elif key in judged_rows:
            results[key] = {"passes": judged_rows[key]["passes"], "by": "judge: " + (
                "shown" if judged_rows[key]["passes"] else f"round {judged_rows[key]['what']}")}
        else:
            results[key] = {"passes": None, "by": "unchecked"}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("scenes", nargs="*")
    parser.add_argument("--judge", type=pathlib.Path, help="ask the open judge too, its work in this folder")
    parser.add_argument("--masks", type=pathlib.Path, help="measure each box against SAM 3's masks, its work here")
    parser.add_argument("--tighten", action="store_true", help="set each loose box to SAM 3's instance inside it")
    parser.add_argument("--dry-run", action="store_true", help="price the cloud runs, rent nothing")
    parser.add_argument("--cards", type=int, default=2, help="the judge's cards at most (each one's setup is paid)")
    options = parser.parse_args()
    scenes = options.scenes or sorted(inventory.every_inventory())
    failing = measure_all(scenes)
    grounded = mask_all(scenes, options.masks, options.dry_run) if options.masks else {}
    if options.tighten:
        for scene in scenes:
            path = inventory.path_of(scene)
            text = path.read_text()
            found = json.loads(text)
            changed = tighten(scene, found, grounded)
            if changed:
                indent = re.match(r"\{\n(\s*)", text)
                path.write_text(json.dumps(found, indent=indent.group(1) if indent else None, ensure_ascii=False)
                                + ("\n" if text.endswith("\n") else ""))
                print(f"{scene}: boxes set to SAM 3's instance: {', '.join(changed)}")
    unmeasured = {key for key, result in grounded.items() if result["grounding"] == "not found"} if grounded else None
    judged = judge_all(scenes, options.judge, options.dry_run, options.cards, unmeasured) if options.judge else {}
    if (grounded or judged) and not options.dry_run:
        results = decided(grounded, judged)
        (options.masks or options.judge).joinpath("decided.json").write_text(json.dumps(results, indent=1))
        record_results(results, measured_boxes([options.masks, options.judge]))
        failing = sorted({key.split(".")[0] for key, result in results.items() if result["passes"] is False})
        print(f"boxes failing: {sum(result['passes'] is False for result in results.values())} of {len(results)}, "
              f"in {', '.join(failing) or 'no scene'}")
    raise SystemExit(1 if failing else 0)


if __name__ == "__main__":
    main()
