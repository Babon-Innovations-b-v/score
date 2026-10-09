"""The inventory box check: whether a scene inventory's boxes really sit on the things their rows name in the concept.

    .venv/bin/python tools/props/scene/box_check.py [<scene> ...]                    # the measurements, every scene
    .venv/bin/python tools/props/scene/box_check.py <scene> ... --judge <folder> [--dry-run]

A scene inventory is the concept partitioned: every row's box is where its thing stands in its view's picture
(`inventory.py`). Boxes guessed rather than drawn on the picture crowd into one corner and cover the wrong things
(the camp's, 2026-10-09: round numbers that reached only x 1900, y 900 of a 2752 x 1536 concept). Two halves:

  measured  plain Python on each view's picture: every box lies inside it; a box over WHOLE of the picture marks
            nothing and is allowed only for the room kit's pieces that run round the whole room (ROOM_WIDE: its
            walls, floor, ceiling and pipe runs); the boxes cover at least COVER_PER_ROW of the picture for each row, up to
            COVER_ENOUGH (from COVER_FROM boxes on); and they are not all in one corner (no more than FULLEST_QUADRANT of the covered area in
            one quarter of the picture, and spread over at least SPREAD of its width or of its height).
  judged    the open judge (../cloud/judge.py, the close-up check's model) sees the whole concept with the box drawn
            on it and the box's crop, and says whether the crop shows the row's thing; each question is asked with
            check.SEEDS and the majority decides (the third seed only where the first two disagree, since it cannot
            change an agreed majority). The questions and crops go under the --judge folder, the answers
            in its answers/ folder; a question already answered is not asked again.

A row the concept does not show carries `"box": null` and `"unseen": "<why>"` (inventory.py) and is not checked here.
"""
import argparse
import json
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
# The kit groups whose pieces run round the whole room, so the whole picture is their box. A kit's furniture,
# screens, lamps and doors are single things, boxed like any other row.
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
    if is_whole(box, size) and row.get("group") not in ROOM_WIDE:
        found.append(f"row {row['id']}: its box is the whole picture, which marks nothing; box the thing, or mark "
                     "the row unseen with why")
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
    if not boxes:
        return []
    wide, tall = size
    grid = covered(boxes, size)
    cover = sum(map(sum, grid)) / (len(grid) * len(grid[0]))
    found = []
    wanted = min(COVER_ENOUGH, COVER_PER_ROW * len(boxes))
    if len(boxes) >= COVER_FROM and cover < wanted:
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
    for view in found["plan"]["views"]:
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


def judge_all(scenes, folder, dry_run, cards):
    """Ask the judge about every box of the scenes (two seeds, then the third where they disagree), then print and
    write (folder/verdicts.json) each box's verdict."""
    import judge
    jobs = []
    for scene in scenes:
        found = json.loads(inventory.path_of(scene).read_text())
        jobs.extend(judge_jobs(scene, found, view_sizes(found), folder, SEEDS[:2]))
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("scenes", nargs="*")
    parser.add_argument("--judge", type=pathlib.Path, help="ask the open judge too, its work in this folder")
    parser.add_argument("--dry-run", action="store_true", help="price the judge's run, rent nothing")
    parser.add_argument("--cards", type=int, default=2, help="the judge's cards at most (each one's setup is paid)")
    options = parser.parse_args()
    scenes = options.scenes or sorted(inventory.every_inventory())
    failing = measure_all(scenes)
    if options.judge:
        judge_all(scenes, options.judge, options.dry_run, options.cards)
    raise SystemExit(1 if failing else 0)


if __name__ == "__main__":
    main()
