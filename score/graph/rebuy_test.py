"""Before a run starts paid work it lists what it would buy, and refuses to buy accepted outputs again for over EUR 5
without a reason, both ways: rows never made are plain buys and never refuse; a changed input re-buys every paid row
after it; a Google row asking what it asked before is cached at EUR 0 and moves nothing after it. A toy table (a free
draw, a paid render reading it, a paid bake reading the render) in a store of its own.

Fault (2026-10-12): one library change re-rendered every place and re-drew every view map, about EUR 50, with nothing
saying so before the run.

Run: .venv/bin/python score/graph/rebuy_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.graph import _code, rebuy  # noqa: E402
from score.store import Store  # noqa: E402

TEXT = contracts.Contract("toy-text", 1, lambda folder: [])
compute.books_refusal = lambda: None  # the month's books are compute_test's; not this one's
_code.git_commit = lambda: {"commit": "c0ffee", "uncommitted": False}  # the records' commit, for same_requests


def make_copy(inputs, out, seed, params):
    source = inputs.get("brief") or next(path for name, path in inputs.items() if name != "brief")
    found = source if source.is_file() else next(source.glob("*.txt"))
    (out / "text.txt").write_text(found.read_text())


def judge_said(output, inputs, evidence):
    return checks.Verdict("said", checks.PASS, "a text was written")


SAID = (checks.Check("said", judge_said),)
DRAW = graph.Stage("draw", "place", make_copy, TEXT, SAID, files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_copy, TEXT, SAID, after={"draw": ("toy-text", 1)}, paid=True, euros=4.0)
BAKE = graph.Stage("bake", "place", make_copy, TEXT, SAID, after={"render": ("toy-text", 1)}, paid=True, euros=3.0)


def a_runner():
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    return graph.Runner([DRAW, RENDER, BAKE], graph.Environment("toy", 1, {"data": data}),
                        Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {"kind": kind})


def made(runner):
    """Every node of the hangar made and accepted."""
    for stage in (DRAW, RENDER, BAKE):
        assert "accepted automatically" in runner.run_node(stage, "hangar"), stage.name
    return runner


def bought(runner):
    return rebuy.buys(runner, list(runner.nodes(["hangar"])))


def test_rows_never_made_are_buys_and_never_refuse():
    found = bought(a_runner())
    assert [(buy.node, buy.euros, buy.again) for buy in found] == [("render@hangar", 4.0, False),
                                                                   ("bake@hangar", 3.0, False)]
    assert rebuy.refusal(found, None) is None


def test_nothing_changed_buys_nothing():
    assert bought(made(a_runner())) == []


def test_a_changed_input_re_buys_every_paid_row_after_it_and_refuses_without_a_reason():
    runner = made(a_runner())
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    found = bought(runner)
    assert [(buy.node, buy.euros, buy.again) for buy in found] == [("render@hangar", 4.0, True),
                                                                   ("bake@hangar", 3.0, True)]
    assert "reads draw@hangar" in found[0].why and "EUR 7.00" in rebuy.refusal(found, None)
    assert rebuy.refusal(found, "the owner changed the hall's brief") is None
    entry = rebuy.ledger_entry(found, "the owner changed the hall's brief")
    assert entry["kind"] == "rebuy" and entry["euros"] == 0 and entry["estimate"] == 7.0


def test_rows_after_a_node_kept_by_a_proof_are_still_buys():
    """Fault (2026-10-24): the greenhouse's plan, kept under its new key by the narrowing proof, hid its whole prop
    route from the plan, so the Buy's figure and stop left out rows the drive then makes."""
    runner = a_runner()
    assert "accepted automatically" in runner.run_node(DRAW, "hangar")
    runner.code_versions["draw"] = "only narrowed"
    runner.narrowing_proof = lambda stage, place, keyed: stage is DRAW
    assert [buy.node for buy in bought(runner)] == ["render@hangar", "bake@hangar"]


def test_re_buys_under_five_euros_go_without_a_reason():
    runner = made(a_runner())
    runner.code_versions["bake"] = "a bake changed"
    found = bought(runner)
    assert [(buy.node, buy.euros) for buy in found] == [("bake@hangar", 3.0)] and "code changed" in found[0].why
    assert rebuy.refusal(found, None) is None


def test_a_google_row_asking_the_same_is_cached_and_moves_nothing_after_it():
    runner = made(a_runner())
    runner.code_versions["render"] = "a render changed"
    original, builders = rebuy.asks_google, rebuy.builders_changed
    rebuy.asks_google = lambda stage: stage is RENDER  # the toy render stands in for a row asking Google
    try:
        rebuy.builders_changed = lambda commit: False
        found = bought(runner)
        assert [(buy.node, buy.euros) for buy in found] == [("render@hangar", 0.0)] and "cached" in found[0].why
        runner.code_versions["bake"], runner.remembered = "a bake changed too", None  # behind the cached row
        found = bought(runner)
        assert [(buy.node, buy.euros) for buy in found] == [("render@hangar", 0.0), ("bake@hangar", 3.0)]
        assert "code changed" in found[1].why
        del runner.code_versions["bake"]
        rebuy.builders_changed = lambda commit: True  # its wording changed: asked and bought again
        assert [(buy.node, buy.euros) for buy in bought(runner)] == [("render@hangar", 4.0), ("bake@hangar", 3.0)]
    finally:
        rebuy.asks_google, rebuy.builders_changed = original, builders


def test_every_file_that_words_a_google_request_is_a_request_builder():
    """Audit (2026-10-22): the finish route's list, recheck, palette and library wordings were left out, so an edit
    there was priced as a cached ask at EUR 0 while the run asked and paid again, under a stop line written too low.
    A file that builds a request body (`def ..._body(`) and reaches Google through google_spend, google_batch or
    finish_ask is one, and so is the batch client itself."""
    import re
    reaches = re.compile(r"^\s*(import|from)\s+(\S+\.)?(google_spend|google_batch|finish_ask)\b", re.MULTILINE)
    wording = re.compile(r"^\s*def \w+_body\(", re.MULTILINE)
    found = set()
    for path in [*(_code.REPO / "score/stages").rglob("*.py"), *(_code.REPO / "tools/props").rglob("*.py")]:
        text = path.read_text(errors="replace")
        if not path.name.endswith("_test.py") and wording.search(text) and reaches.search(text):
            found.add(str(path.relative_to(_code.REPO)))
    assert found and found <= set(rebuy.REQUEST_BUILDERS), sorted(found - set(rebuy.REQUEST_BUILDERS))
    assert "tools/cloud/google_batch.py" in rebuy.REQUEST_BUILDERS
    assert all((_code.REPO / builder).is_file() for builder in rebuy.REQUEST_BUILDERS)


def test_score_run_refuses_before_it_starts_and_records_a_given_reason():
    import argparse
    import contextlib
    import io
    import json
    from score import __main__ as command
    books = compute.ledger()
    books.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    runner = made(a_runner())
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    options = argparse.Namespace(stage=None, rebuy_reason=None, detach=False)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            command.checked_buys(runner, ["hangar"], True, options)
    except SystemExit as refusal:
        assert "refused" in str(refusal.code) and "re-buy render@hangar: EUR 4.00" in printed.getvalue()
    else:
        raise AssertionError("a EUR 7 re-buy with no reason ran")
    assert not books.LEDGER.exists()
    options.rebuy_reason = "the owner changed the hall's brief"
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        command.checked_buys(runner, ["hangar"], True, options)
    assert "re-buy reason: the owner changed the hall's brief" in printed.getvalue()
    line = json.loads(books.LEDGER.read_text())
    assert line["reason"] == options.rebuy_reason and line["rebuys"] == {"render@hangar": 4.0, "bake@hangar": 3.0}


def test_score_plan_prices_each_buy_and_the_run_on_the_runners_numbers():
    """`score plan --json` keeps each buy's estimate and adds its price as `score price` gives it (unmeasured: no
    price, the estimate kept apart as the guess, no minutes), and the run's sums, the guesses apart; with every row's minutes measured, the run's time
    is its longest row or its minutes over --jobs, whichever is longer (C3)."""
    import argparse
    from score import __main__ as command
    books = compute.ledger()
    books.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    runner = made(a_runner())
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    options = argparse.Namespace(stage=None, rebuy_reason=None, jobs=2)
    planned = command.plan_json(runner, ["hangar"], True, options)
    assert [(buy["node"], buy["euros"], buy["price"]["likely_euros"], buy["price"]["high_euros"],
             buy["price"]["guess_euros"]) for buy in planned["buys"]] == [("render@hangar", 4.0, None, None, 4.0),
                                                                          ("bake@hangar", 3.0, None, None, 3.0)]
    assert planned["price"] == {"likely_euros": 0.0, "high_euros": 0.0, "guessed_euros": 7.0, "guessed": 2,
                                "likely_minutes": None, "high_minutes": None, "measured": 0, "rows": 2, "jobs": 2}
    timed = [{"likely_euros": 1.0, "high_euros": 2.0, "likely_minutes": minutes, "high_minutes": 2 * minutes,
              "runs": 3} for minutes in (10.0, 20.0, 30.0)]
    assert command.plan_price(timed, 2) == {"likely_euros": 3.0, "high_euros": 6.0, "guessed_euros": 0, "guessed": 0,
                                            "likely_minutes": 30.0, "high_minutes": 60.0, "measured": 3, "rows": 3,
                                            "jobs": 2}
    assert command.plan_price(timed, 1)["likely_minutes"] == 60.0


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print(f"ok {name}")
