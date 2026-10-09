"""The close-up stage: one clean close-up for every generated row of a place, Qwen-Image-Edit first and Nano Banana
Pro only for the close-ups the shape check fails (the owner's decision, 2026-10-08).

    .venv/bin/python tools/props/closeup/stage.py <rows.json> <out folder> [--no-pro] [--dry-run]
    .venv/bin/python tools/props/closeup/stage.py --from-inventory data/inventory/<scene>.json <rows.json>

The rows are [{"id", "words", "size": [wide, deep, tall], "concept": <picture>, "box": [left, top, right, bottom]}]:
the object, its box in metres, and where it stands in the picked concept. --from-inventory writes them from an
approved scene inventory's generated rows (their name, size, view picture and box). Every step leaves its files in
the out folder and is skipped when they are there, so a run that stops is run again:

1. crops/<id>.jpg: the row's box in the concept with a fifth of margin, at least 512 pixels long.
2. qwen/<id>.png: every close-up from Qwen-Image-Edit-2511 in one batch (../cloud/pictures.py --model qwen-edit),
   the crop and the whole concept as references, spread over as many 80 GB cards as draw it in about one setup's
   time (../cloud/spread.py), each card taking the next share as it finishes one.
3. qwen/judge/<id>.txt: the judge's answer for each (../cloud/judge.py), and the shape check (check.py) on top.
4. pro/<id>.png, then pro-room/<id>.png: Nano Banana Pro for each close-up the check failed (pro.py), judged and
   checked the same way: first from the crop alone (CROP_ONLY), then, for what still fails, with the whole concept
   as its second reference (WORDING). Skipped with --no-pro.
5. closeups.json: per row the accepted picture and the model that made it (none when every take failed: those are
   left for the creator to look at), every take's faults and the row's cost; the batches' ledger entries and the
   totals.

Printed words on a close-up do not matter: labels and print are put on the model as decals later.
"""
import argparse
import json
import pathlib
import shutil
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "cloud"))

import check  # noqa: E402
import pro  # noqa: E402

# What every close-up is drawn as, by either model: the object alone, from three quarters, its parts and wear from
# the crop and its materials from the concept (the wording the lab's Pro close-ups were drawn with, job place-lab).
WORDING = ("Make one clean product picture of a single object for a 3D model maker: the object alone on a plain, "
           "even, light grey background that fills the whole frame (no room, no walls, no floor line, no other "
           "objects, no dimension lines, arrows, measurements or captions), seen from three quarters (turned about "
           "35 degrees, a little from above), the whole object with a margin round it, evenly lit by soft studio "
           "light with mild shadow, sharp fine detail. The object: {words}. Its size: {wide:.2f} m wide, {deep:.2f} m "
           "deep and {tall:.2f} m tall; keep those proportions exactly. Image 1 is this very object cut from a "
           "concept picture of its room: take its shape, parts, layout, colours, wear, labels, stickers and taped "
           "notes from it, drawn crisp and complete. Image 2 is the whole room, for its materials, paint and wear "
           "only: never draw the room.")
# Pro's first take: the crop alone, the object named exactly and the room named as what to leave out. Given the whole
# room, Pro drew it behind the object, as a miniature or with dimension lines on 7 of the lab's 14 (2026-10-08), and a
# model's surfaces come from the surface library, never from the picture, so the room adds little (the coordinator,
# 2026-10-08; the retake wording of job place-lab).
CROP_ONLY = ("Make one clean product picture of a single object for a 3D model maker. ONLY this object, alone, floating on "
             "a plain, even, light grey studio background that fills the whole frame: no room, no walls, no floor, no "
             "ground, no shadow pool, no other objects, no people, no dimension lines or captions. Seen from three "
             "quarters, a little from above, the whole object with a wide margin round it, soft even studio light, sharp "
             "fine detail. The object: {words}. Its size: {wide:.2f} m wide, {deep:.2f} m deep and {tall:.2f} m tall; keep "
             "those proportions exactly. Image 1 shows this object among other things: take its shape, parts, materials, "
             "paint, wear and colours from it and ignore everything around it.")
# Pro's takes in order, each judged before the next: its folder under the out folder and its wording. The room
# reference is the second take, for an object the crop alone does not make clear.
PRO_TAKES = {"pro": CROP_ONLY, "pro-room": WORDING}
MARGIN = 0.2
SHORTEST_CROP = 512


def wording(row, text=WORDING):
    """The words a row's close-up is drawn with."""
    wide, deep, tall = row["size"]
    return text.format(words=row["words"], wide=wide, deep=deep, tall=tall)


def crop(concept, box):
    """The box in the concept with a fifth of margin round it, scaled up to at least SHORTEST_CROP on its long side."""
    left, top, right, bottom = box
    margin = MARGIN * max(right - left, bottom - top)
    cut = concept.crop((max(0, left - margin), max(0, top - margin), min(concept.width, right + margin),
                        min(concept.height, bottom + margin)))
    if max(cut.size) < SHORTEST_CROP:
        scale = SHORTEST_CROP / max(cut.size)
        cut = cut.resize((round(cut.width * scale), round(cut.height * scale)), Image.LANCZOS)
    return cut.convert("RGB")


def rows_from_inventory(inventory):
    """The stage's rows from a scene inventory: every generated row with its name, size, view picture and box."""
    views = {view["id"]: view["picture"] for view in inventory["plan"]["views"]}
    return [{"id": row["id"], "words": row["name"], "size": row["size"], "concept": views[row["view"]],
             "box": row["box"]} for row in inventory["rows"] if row.get("kind") == "generate" and row.get("box")]


def make_crops(rows, out):
    """Step 1: every row's crop, as out/crops/<id>.jpg."""
    (out / "crops").mkdir(parents=True, exist_ok=True)
    for row in rows:
        path = out / "crops" / f"{row['id']}.jpg"
        if not path.exists():
            crop(Image.open(row["concept"]), row["box"]).save(path, quality=92)


def picture_jobs(rows, out):
    """The picture batch's list: every row not yet drawn by Qwen, with its wording and its two references."""
    return [{"name": f"closeup-{row['id']}", "wording": wording(row),
             "refs": [str(out / "crops" / f"{row['id']}.jpg"), str(row["concept"])]}
            for row in rows if not (out / "qwen" / f"{row['id']}.png").exists()]


def draw_with_qwen(rows, out, dry_run=False):
    """Step 2: every row's Qwen close-up into out/qwen/; the batch's ledger entry, or None when nothing was rented."""
    import pictures
    from paths import PICTURES

    (out / "qwen").mkdir(parents=True, exist_ok=True)
    jobs = picture_jobs(rows, out)
    if not jobs:
        return None
    listing = out / "qwen" / "jobs.json"
    listing.write_text(json.dumps(jobs, indent=1))
    entry = pictures.draw_list(listing, "qwen-edit", dry_run=dry_run)
    for job in jobs:
        drawn = PICTURES / f"{job['name']}.png"
        if drawn.exists():
            shutil.move(drawn, out / "qwen" / f"{job['name'].removeprefix('closeup-')}.png")
    return entry


def judge_questions(rows, out, take):
    """The judge's list: each row's picture of `take` beside its crop, asked once with each of check.SEEDS."""
    return [{"name": f"{row['id']}~{seed}", "seed": seed, "text": check.question(row["words"], row["size"]),
             "images": [str(out / "crops" / f"{row['id']}.jpg"), str(out / take / f"{row['id']}.png")]}
            for row in rows if (out / take / f"{row['id']}.png").exists() for seed in check.SEEDS]


def judge(rows, out, take, dry_run=False):
    """The judge's answers on `take`'s pictures into out/<take>/judge/; the batch's ledger entry, or None when nothing
    was rented."""
    import judge as judge_runner

    folder = out / take / "judge"
    folder.mkdir(parents=True, exist_ok=True)
    listing = folder / "questions.json"
    listing.write_text(json.dumps(judge_questions(rows, out, take), indent=1))
    return judge_runner.ask(listing, folder, dry_run)


def checked(row, out, take):
    """The shape check's faults on a row's picture of `take`; a missing picture is a fault of its own."""
    picture = out / take / f"{row['id']}.png"
    if not picture.exists():
        return [f"no {take} picture"]
    replies = [out / take / "judge" / f"{row['id']}~{seed}.txt" for seed in check.SEEDS]
    return check.faults(check.measure(picture, row["size"]),
                        [check.answer_of(reply.read_text()) if reply.exists() else None for reply in replies])


def draw_with_pro(rows, out, failed, take):
    """A Nano Banana Pro close-up into out/<take>/ for each failed row not drawn yet, worded as the take says (PRO_TAKES);
    the number of pictures Pro was asked for."""
    from secret_store import secret

    (out / take).mkdir(parents=True, exist_ok=True)
    todo = [row for row in rows if row["id"] in failed and not (out / take / f"{row['id']}.png").exists()]
    key = secret(pro.KEY_SECRET) if todo else None
    for row in todo:
        cut = Image.open(out / "crops" / f"{row['id']}.jpg")
        concept = Image.open(row["concept"]) if PRO_TAKES[take] is WORDING else None
        pro.draw(key, wording(row, PRO_TAKES[take]), cut, concept, out / take / f"{row['id']}.png")
    return len(todo)


def kept_entry(entry, path):
    """Every ledger entry of a step's batches kept at `path`, so a run that stops and is run again still knows what the
    step cost; their euros summed with the entries themselves, or None when the step never rented."""
    kept = json.loads(path.read_text()) if path.exists() else []
    if entry:
        kept.append(entry)
        path.write_text(json.dumps(kept, indent=1))
    return {"euros": sum(item["euros"] for item in kept), "runs": kept} if kept else None


def share(entry, count):
    """A batch's euros shared over the `count` pictures or answers it made."""
    return entry["euros"] / count if entry and count else 0.0


def model_of(take):
    """The picture model a take was drawn by."""
    return "qwen-edit" if take == "qwen" else "nano-banana-pro"


def accepted(row, out, faults, euros):
    """One row's record: every take's faults, the first take that passed (its picture and model; none when every take
    failed, left for the creator to look at), the cloud's euros and Pro's dollars for the row."""
    takes = [take for take in ("qwen", *PRO_TAKES) if take in faults]
    passed = next((take for take in takes if not faults[take]), None)
    pro_pictures = sum((out / take / f"{row['id']}.png").exists() for take in takes if take != "qwen")
    return {"id": row["id"], "accepted": model_of(passed) if passed else None,
            "picture": str(out / passed / f"{row['id']}.png") if passed else None,
            "take": passed, "faults": {take: faults[take] for take in takes}, "euros": euros,
            "pro_dollars": pro_pictures * pro.DOLLARS_A_PICTURE}


def summary(records, entries):
    """The run's totals: how many close-ups each model gave, how many are left for review, Pro's share and pictures,
    and the cost per accepted close-up."""
    made = [record for record in records if record["accepted"]]
    by_pro = [record for record in made if record["accepted"] == "nano-banana-pro"]
    euros = sum(entry["euros"] for entry in entries.values() if entry)
    dollars = sum(record["pro_dollars"] for record in records)
    return {"rows": len(records), "accepted": len(made), "by_qwen": len(made) - len(by_pro), "by_pro": len(by_pro),
            "for_review": len(records) - len(made), "pro_share": len(by_pro) / len(records) if records else 0.0,
            "pro_pictures": round(dollars / pro.DOLLARS_A_PICTURE), "cloud_euros": euros, "pro_dollars": dollars,
            "cloud_euros_per_accepted": euros / len(made) if made else None,
            "pro_dollars_per_accepted": dollars / len(made) if made else None}


def row_euros(row, out, entries):
    """The cloud's euros for one row: its share of the Qwen batch and of every judge batch that judged one of its
    pictures (one answer for each seed)."""
    euros = share(entries.get("qwen"), len(list((out / "qwen").glob("*.png"))))
    for take in ("qwen", *PRO_TAKES):
        if (out / take / "judge" / f"{row['id']}~{check.SEEDS[0]}.txt").exists():
            euros += share(entries.get(f"judge-{take}"), len(list((out / take / "judge").glob("*.txt")))) * len(check.SEEDS)
    return euros


def run(rows, out, use_pro=True, dry_run=False):
    """The whole stage for `rows` into `out`; the record written to out/closeups.json."""
    make_crops(rows, out)
    if dry_run:
        draw_with_qwen(rows, out, dry_run=True)
        judge(rows, out, "qwen", dry_run=True)
        return None
    entries = {"qwen": kept_entry(draw_with_qwen(rows, out), out / "qwen" / "batch.json")}
    entries["judge-qwen"] = kept_entry(judge(rows, out, "qwen"), out / "qwen" / "judge" / "batch.json")
    faults = {row["id"]: {"qwen": checked(row, out, "qwen")} for row in rows}
    failed = {row_id for row_id, found in faults.items() if found["qwen"]}
    for take in PRO_TAKES if use_pro else ():
        if not failed:
            break
        draw_with_pro(rows, out, failed, take)
        entries[f"judge-{take}"] = kept_entry(judge([row for row in rows if row["id"] in failed], out, take),
                                              out / take / "judge" / "batch.json")
        for row in rows:
            if row["id"] in failed:
                faults[row["id"]][take] = checked(row, out, take)
        failed = {row_id for row_id in failed if faults[row_id][take]}
    records = [accepted(row, out, faults[row["id"]], row_euros(row, out, entries)) for row in rows]
    result = {"rows": records, "batches": entries, "totals": summary(records, entries)}
    (out / "closeups.json").write_text(json.dumps(result, indent=1))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("rows", type=pathlib.Path, nargs="?")
    parser.add_argument("out", type=pathlib.Path, nargs="?")
    parser.add_argument("--from-inventory", type=pathlib.Path, help="write the rows from a scene inventory")
    parser.add_argument("--no-pro", action="store_true", help="leave the failures without a Pro close-up")
    parser.add_argument("--dry-run", action="store_true", help="make the crops and price the batches, rent nothing")
    options = parser.parse_args()
    if options.from_inventory:
        rows = rows_from_inventory(json.loads(options.from_inventory.read_text()))
        options.rows.write_text(json.dumps(rows, indent=1))
        return
    if not (options.rows and options.out):
        parser.error("give the rows and the out folder, or --from-inventory and the rows to write")
    result = run(json.loads(options.rows.read_text()), options.out, not options.no_pro, options.dry_run)
    if result:
        print(json.dumps(result["totals"], indent=1))


if __name__ == "__main__":
    main()
