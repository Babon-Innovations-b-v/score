"""The runner tests' toy table (score/graph/test_a_key_is_made_once_from_accepted_inputs.py): clean, a place's brief
upper-cased, gated on a word limit given as evidence; count after it; and the rows a pod makes. A module of its own,
importing only what the rows use, so a pod that imports the table and works its code version out cold reads a few
files, not the test file and every module it imports."""
import json

from score import checks, contracts, graph
from score.store import Store, file_hash

READS = ("toy-text", 1)


def make_clean(inputs, out, seed, params):
    print("cleaning", inputs["brief"])
    text = inputs["brief"].read_text()
    if "explode" in text:
        raise RuntimeError("the cleaner fell over")
    if "quit" in text:
        raise SystemExit("the cleaner quit: no such material")
    (out / "clean.txt").write_text(text.upper())


def judge_words(output, inputs, evidence):
    words = len((output / "clean.txt").read_text().split())
    limit = json.loads(evidence.read_text())["limit"]
    return checks.Verdict("words", checks.PASS if words <= limit else checks.FAIL, f"{words} words, limit {limit}",
                          {"words": words}, {"words": "lower"},
                          (f"{words - limit} words too many",) if words > limit else ())


def judge_shout(output, inputs, evidence):
    shouted = "!" in (output / "clean.txt").read_text()
    return checks.Verdict("shout", checks.FAIL if shouted else checks.PASS, "shouts" if shouted else "no shouting")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["clean"] / "clean.txt").read_text())))


def judge_passes(output, inputs, evidence):
    return checks.Verdict("counted", checks.PASS, "written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WORDS = checks.Check("words", judge_words, evidence="a word limit")
PASSES = (checks.Check("counted", judge_passes),)
CLEAN = graph.Stage("clean", "place", make_clean, TEXT, (WORDS,), files={"brief": "{data}/{place}/brief.txt"})
COUNT = graph.Stage("count", "place", make_count, TEXT, PASSES, after={"clean": READS})


def make_peek(inputs, out, seed, params):
    record = Store.default().record("clean@hangar", "any")  # a store read its key does not declare
    (out / "peek.txt").write_text(str(record))


PEEK = graph.Stage("peek", "place", make_peek, TEXT, PASSES, after={"clean": READS})


def make_kept(inputs, out, seed, params):
    (out / "kept.txt").write_text((inputs["clean"] / "clean.txt").read_text().lower())
    Store.default().put_blob(out / "kept.txt", file_hash(out / "kept.txt"))  # a kept take's file: a write, no read


def designed_files(place):
    """The brief where the home holds the place's locked plan, else a seed nothing makes: a row's files as the stage
    table reads them from the home's designs (score/stages earth_place: an earth place's seed from its plan)."""
    import score.store
    plan = score.store.PROPS_HOME / "design" / "plans" / f"{place}.json"
    return {"brief": "{data}/{place}/brief.txt"} if plan.is_file() else {"seed": "{data}/{place}/seed.txt"}


def recorded_files(place):
    """The brief once the place's clean output stands accepted, else a seed nothing makes: a row's files as the
    store's accepts and rejects decide them (score/stages/light light_files: the places its own place's accepted scene
    record shows)."""
    accepted = Store.default().accepted(f"clean@{place}")
    return {"brief": "{data}/{place}/brief.txt"} if accepted else {"seed": "{data}/{place}/seed.txt"}


KEPT = graph.Stage("kept", "place", make_kept, TEXT, PASSES, after={"clean": READS})
DESIGNED = graph.Stage("designed", "place", make_clean, TEXT, PASSES, files=designed_files)
RECORDED = graph.Stage("recorded", "place", make_clean, TEXT, PASSES, files=recorded_files)
POD_TABLE = (CLEAN, COUNT, PEEK, KEPT, DESIGNED, RECORDED)
