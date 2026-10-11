"""The concept-people stage: how many people each place's concept shows, measured with SAM 3 on every view picture
its inventory names and each figure it finds put to the judge, run by the runner as one paid world node,
`concept_people`.

    .venv/bin/python -m score.stages.concept_people run
    .venv/bin/python -m score.stages.concept_people status

A place whose concept shows people needs a cast (the paper's 2.7, people); one that shows none needs none. Which is
which is measured here, never judged by eye: SAM 3 asked for "person" on each picture (tools/props/scene/box_masks.py,
on one rented card through tools/props/cloud/box_masks_cloud.py), each instance kept with its pixel box and score
(at most box_masks.KEEP a picture, surest first). SAM 3 also finds a person in a poster, a framed print, a
reflection in glass or an empty suit on its hook, so every figure is then put to the judge (tools/props/cloud/judge.py,
a vision-language model on rented cards): the figure ringed in red on the picture round it, beside its own crop,
asked what it is (QUESTION: a person there, a picture of one, a reflection, an empty suit or something else) and, for
a person, what they are doing, once with each of SEEDS and once more with each of MORE_SEEDS when those split; the
answer most seeds give is the figure's (a tie is unknown). The output is `people.json`: {place: {view: {"picture",
"size", "people", "instances"}}}, `people` counting the figures judged a person, each instance with its `judged`
answer and `answers`, and for a person `doing` (the majority of `doings`; None on a tie).

The gates: `measured` passes when every view of every place came back with its instances (a view with none returned
is unknown, never read as nobody); `judged` when every figure has a majority answer.
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw

from score import checks, contracts, graph
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/props/cloud"))
NOUN = "person"
# SAM 3 on one L4 (about 5 minutes) and the judge on one 48 or 80 GB card (its set-up about 20 minutes), rounded up.
EUROS = 3.0
SEEDS = (1, 2, 3)
# A figure the first seeds split on (its answer or what it is doing) is asked again with these, and the majority of
# all its answers taken.
MORE_SEEDS = (4, 5, 6, 7)
ANSWERS = ("person", "picture", "reflection", "suit", "other")
DOINGS = ("walking", "standing", "sitting", "crouching", "lying", "working")
# The picture round a figure: this many times its box each way, the figure ringed in red.
CONTEXT = 3.0
QUESTION = ("The first picture is part of a concept painting of a place; one figure is ringed in red. The second is "
            "that figure close up. What is the ringed figure? Answer person if it is a human being present in the "
            "place (standing, sitting, walking, working, near or far); picture if it is a person shown in a poster, "
            "photograph, painting, screen or print; reflection if it is a person's reflection or a ghostly see-through "
            "figure in glass, a window or a shiny surface; suit if it is an empty suit, garment, mannequin or statue; "
            "other if it is not a figure at all. If it is a person, also say what they are doing: walking, standing, "
            "sitting, crouching, lying, or working (standing at something with their hands on it). End with two "
            "lines: VERDICT: person, picture, reflection, suit or other; then DOING: walking, standing, sitting, "
            "crouching, lying, working or none.")


def place_views(inventory_folder):
    """{place: {view id: picture path pattern}} from every inventory's plan views (WORK is the seeds root)."""
    found = {}
    for path in sorted(pathlib.Path(inventory_folder).glob("*.json")):
        record = json.loads(path.read_text())
        views = (record.get("plan") or {}).get("views", [])
        found[path.stem] = {view["id"]: view["picture"].replace("WORK/", "{seeds}/") for view in views}
    return found


VIEWS = place_views(REPO / "data/inventory")
FILES = {"inventory": "{data}/inventory",
         **{f"{place}.{view}": picture for place, views in VIEWS.items() for view, picture in views.items()}}


def jobs_of(inputs):
    """box_masks.py's jobs: one a picture, one row asking for a person over the whole picture."""
    jobs = []
    for name, path in sorted(inputs.items()):
        if name == "inventory":
            continue
        wide, tall = Image.open(path).size
        jobs.append({"picture": str(path), "rows": [{"key": name, "nouns": [NOUN], "box": [0, 0, wide, tall]}]})
    return jobs


def make_counts(inputs, out, seed, params):
    """Ask SAM 3 for people on every view picture on one rented card and write `people.json` into `out`."""
    import box_masks_cloud
    jobs = jobs_of(inputs)
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
    box_masks_cloud.mask(out / "jobs.json", out / "instances.json")
    instances = json.loads((out / "instances.json").read_text())
    judged = judge_figures(jobs, instances, out)
    write_counts(jobs, instances, out / "people.json", judged)


def figure_pictures(picture, box, target):
    """The figure ringed in red on the picture round it (`<target>-around.jpg`) and its own crop (`-close.jpg`)."""
    image = Image.open(picture).convert("RGB")
    left, top, right, bottom = box
    wide, tall = right - left, bottom - top
    reach_x, reach_y = wide * (CONTEXT - 1) / 2, tall * (CONTEXT - 1) / 2
    around = image.crop((max(0, left - reach_x), max(0, top - reach_y), min(image.width, right + reach_x),
                         min(image.height, bottom + reach_y)))
    ringed = around.copy()
    offset = (max(0, left - reach_x), max(0, top - reach_y))
    ImageDraw.Draw(ringed).rectangle((left - offset[0], top - offset[1], right - offset[0], bottom - offset[1]),
                                     outline=(255, 0, 0), width=max(2, round(min(wide, tall) / 30)))
    ringed.save(f"{target}-around.jpg", quality=92)
    image.crop(box).save(f"{target}-close.jpg", quality=92)


def figure_questions(jobs, instances, folder):
    """The judge's list: every figure SAM 3 found, its two pictures written into `folder`, once with each seed."""
    folder.mkdir(parents=True, exist_ok=True)
    questions = []
    for job in jobs:
        key = job["rows"][0]["key"]
        for number, instance in enumerate(instances.get(key, [])):
            target = folder / f"{key}.{number}"
            figure_pictures(job["picture"], instance["box"], target)
            questions += asked(f"{key}.{number}", target, SEEDS)
    return questions


def asked(figure, target, seeds):
    """One figure's questions, once with each of `seeds`."""
    return [{"name": f"{figure}~{seed}", "seed": seed, "text": QUESTION,
             "images": [f"{target}-around.jpg", f"{target}-close.jpg"]} for seed in seeds]


def split(replies):
    """Whether a figure's replies disagree on what it is or on what it is doing."""
    return len({reply[0] for reply in replies}) > 1 or len({reply[1] for reply in replies}) > 1


def said(text, label, words):
    """The word a judge's reply gives on its last `label:` line, or None when it names none of `words`."""
    lines = [line for line in text.splitlines() if f"{label}:" in line.upper()]
    word = lines[-1].upper().split(f"{label}:")[-1].strip(" .*").lower() if lines else ""
    return word if word in words else None


def verdict_of(text):
    """The answer a judge's reply ends on, or None when it names none of ANSWERS."""
    return said(text, "VERDICT", ANSWERS)


def doing_of(text):
    """What the judge says the person is doing, or None."""
    return said(text, "DOING", DOINGS)


def majority(answers):
    """The answer most seeds gave, or None on a tie or with none."""
    given = [answer for answer in answers if answer]
    ranked = sorted({answer: given.count(answer) for answer in given}.items(), key=lambda pair: -pair[1])
    if not ranked or (len(ranked) > 1 and ranked[0][1] == ranked[1][1]):
        return None
    return ranked[0][0]


def judge_figures(jobs, instances, out):
    """{figure key: [(answer, doing) of each seed]} from the judge on every figure; a split figure asked again."""
    import judge
    folder = out / "figures"
    questions = figure_questions(jobs, instances, folder)
    (folder / "questions.json").write_text(json.dumps(questions, indent=1))
    if questions:
        judge.ask(folder / "questions.json", folder / "answers")
    found = replies_of(questions, folder)
    again = [question for figure, replies in found.items() if split(replies)
             for question in asked(figure, folder / figure, MORE_SEEDS)]
    if again:
        (folder / "again.json").write_text(json.dumps(again, indent=1))
        judge.ask(folder / "again.json", folder / "answers")
    return replies_of(questions + again, folder)


def replies_of(questions, folder):
    """{figure key: [(answer, doing) of each question asked of it]} from the answers folder."""
    found = {}
    for question in questions:
        figure = question["name"].split("~")[0]
        reply = folder / "answers" / f"{question['name']}.txt"
        text = reply.read_text() if reply.exists() else ""
        found.setdefault(figure, []).append((verdict_of(text), doing_of(text)))
    return found


def write_counts(jobs, instances, target, judged):
    """people.json from the jobs, SAM 3's instances and the judge's answers: a view absent from the instances is left
    out (unknown); a view's people are its figures the judge's majority calls a person."""
    counts = {}
    for job in jobs:
        key = job["rows"][0]["key"]
        if key not in instances:
            continue
        place, view = key.split(".", 1)
        figures = []
        for number, instance in enumerate(instances[key]):
            replies = judged.get(f"{key}.{number}", [])
            answer = majority([reply[0] for reply in replies])
            doing = majority([reply[1] for reply in replies]) if answer == "person" else None
            figures.append(dict(instance, answers=[reply[0] for reply in replies], judged=answer,
                                doings=[reply[1] for reply in replies], doing=doing))
        counts.setdefault(place, {})[view] = {"picture": job["picture"], "size": job["rows"][0]["box"][2:],
                                              "people": sum(figure["judged"] == "person" for figure in figures),
                                              "instances": figures}
    target.write_text(json.dumps(counts, indent=1))


def counts_faults(folder):
    """Why a folder is not a people count, or [] when it is."""
    return [] if (folder / "people.json").exists() else ["no people.json"]


CONCEPT_PEOPLE = contracts.Contract("concept-people", 1, counts_faults)


def judge_measured(output, inputs, evidence):
    """Every view of every place came back from SAM 3 with its instances."""
    counts = json.loads((output / "people.json").read_text())
    wanted = sorted(name for name in inputs if name != "inventory")
    missing = [name for name in wanted if name.split(".", 1)[1] not in counts.get(name.split(".", 1)[0], {})]
    shown = sum(1 for views in counts.values() if any(view["people"] for view in views.values()))
    answer = checks.UNKNOWN if missing else checks.PASS
    reason = (f"{len(missing)} of {len(wanted)} views not measured: {', '.join(missing)}" if missing
              else f"{len(wanted)} views measured; {shown} of {len(counts)} places show people")
    return checks.Verdict("measured", answer, reason, {"views": len(wanted), "missing": len(missing)})


def judge_judged(output, inputs, evidence):
    """Every figure SAM 3 found has the judge's majority answer."""
    counts = json.loads((output / "people.json").read_text())
    figures = [(f"{place}.{view}.{number}", figure) for place, views in counts.items()
               for view, found in views.items() for number, figure in enumerate(found["instances"])]
    open_figures = [name for name, figure in figures if figure["judged"] is None]
    answer = checks.UNKNOWN if open_figures else checks.PASS
    reason = (f"{len(open_figures)} of {len(figures)} figures without a majority: {', '.join(open_figures)}"
              if open_figures else f"{len(figures)} figures judged")
    return checks.Verdict("judged", answer, reason, {"figures": len(figures), "open": len(open_figures)})


STAGE = graph.Stage("concept_people", "world", make_counts, CONCEPT_PEOPLE,
                    (checks.Check("measured", judge_measured), checks.Check("judged", judge_judged)),
                    files=FILES, paid=True, euros=EUROS)


def runner(store=None):
    """The runner over this stage alone, on world 1."""
    from score.stages import world1
    return graph.Runner((STAGE,), world1(), store or Store.default())
