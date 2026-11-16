"""Invariant: the store gets only the owner's asks: a decision, figure or waiver applies only for the store's owner
and never in an agent's process, but for his decision made in chat, applied once by its quoted yes through the same
request code while its target stands; the store's upkeep pass does nothing from a checkout not clean and pushed or when
the runner's price fails, makes the basket a Buy buys from, and says what each step did.

Breaks that turn this red (each applied once and seen red, then reverted):
- applying.apply_decision: the owner check -> `if False:` -> the test
- applying.OWNER_FIGURES: a "month" kind added -> the test
- pages/actions.owner_figure_off_why: the agent check -> `if False:` -> the test
- pages/actions.set_books_figure: the amount check -> `if False:` -> the test
- pages/actions.scene_name: the name check -> `if False:`; or library_actions.carried_out: the refusal dropped ->
  the test
- client.step_run: `err` without "out of time after ..." -> the test
- client.sync_pass: the basket not made -> the test
- client.sync_pass: the tree refusal ignored -> the test
- client.tree_refusal: uncommitted changes ignored -> the test
- client.step_run: the group not ended -> the test
- review/web.as_owner_deciding: `with markers_lifted():` -> `with contextlib.nullcontext():` ->
  the test
- chat_decisions.refusal: the `now != yes["target"]` check -> `if False:` ->
  the test
- applying.OWNER_FIGURES: the "spend-override" line dropped (his spend override in chat has no request kind) ->
  the test
- chat_decisions.override_state: the `web.override_yes(...) is not None` check -> `if False:` ->
  the test
- chat_decisions.books_state: `"books": books` dropped from its target (a books month asked before the books were
  written since applies anyway) -> the test
- chat_decisions.request_of: the books month branch dropped (his books month in chat has no request kind) ->
  the test
- applying.OWNER_FIGURES: the "stop-line" line dropped (his stop line in chat has no request kind) ->
  the test
- applying.OWNER_FIGURES: the "cap-line" line dropped, or chat_decisions.cap_state's `"current"` set to None (a cap
  written since applies anyway) -> the test
- chat_decisions.stop_state: its `"line"` set to None (a stop line asked before another line was written applies
  anyway) -> the test
- chat_decisions.request_of: a reject's `takes` dropped (a retake of named takes remakes every take) ->
  the test
- chat_decisions.request_of: the film lock's script sent without `"size": given["size"]` (his re-lock at 1080p
  locks the old size) -> the test
- chat_decisions.apply: the `handed_back(store, yes_id, applied.detail)` after a refused apply dropped (a yes the
  cockpit refused stays used, 2026-11-05) -> the test
- chat_decisions.request_of: a spend's payload without its `cap` (his "Count it under the env1 cap" lost, C10 refuses
  the run; 2026-11-16) -> the test
"""
import json
import os
import pathlib
import re
import sys
import time
import types
from unittest.mock import ANY

import pytest

from score.dashboard.proposals import make, records
from score.dashboard.sync import applying, client
from score.dashboard.tests.fixture import FakeBackend

pytestmark = pytest.mark.django_db(transaction=True)
PRICED = "priced by the runner: EUR 1.00 to 2.00 measured, 3 paid steps with no measured price"


def offline(monkeypatch):
    """Prepare, the library's pictures, the parts and light read, the USD check, the frozen copies' sweep and the plans
    kept as lines, so no test pass reads the real library, hands to it, fetches a picture, asks a model, removes a copy
    or writes a plan where the plan stage reads it."""
    monkeypatch.setattr(client, "plans_kept", lambda: "plans for the plan stage: test")
    monkeypatch.setattr(client, "remake_prepared", lambda: "remake batch (estimate): test")
    monkeypatch.setattr(client, "library_pictures", lambda: "library pictures: test")
    monkeypatch.setattr(client, "library_demos", lambda: "library demos: test")
    monkeypatch.setattr(client, "library_handing", lambda world: "library handover: test")
    monkeypatch.setattr(client, "usd_sweep", lambda: "usd check: test")
    monkeypatch.setattr(client, "copies_swept", lambda: "sweep: test")


def fed(monkeypatch):
    """A clean checkout origin's main holds, and the runner's price made: [the environments priced]."""
    priced = []
    offline(monkeypatch)
    monkeypatch.setattr(client, "tree_refusal", lambda repo: None)
    monkeypatch.setattr(client, "runner_price", lambda repo, environment: priced.append(environment) or (PRICED, None))
    return priced


def test_the_store_gets_only_the_owners_asks(owner_books, tmp_path, settings, monkeypatch):
    """One request table applied on the store (a stranger's, an agent's process's, bad names and library addresses,
    kinds nothing sends, then the owner's own), a refused request writing nothing; then upkeep passes (two refused,
    one that makes the basket); then his decisions made in chat through one table of decision kinds (each with a twin
    asked before its target changed) and one of yeses never recorded; then the pass's own steps through tables (the
    parts and light asked, a step's leftovers and its time)."""
    from score.dashboard.pages import actions, library_actions
    world, home = owner_books, settings.SCORE_HOME
    unpushed = "commit 0123abcd is not on origin's main: push it first"
    # the store side applies one request table: a stranger's and an agent's process's refused, kinds nothing sends
    # refused, names with a path refused, then the owner's own applied
    from score.review import web as review_web
    agent_started = actions.agent_started
    settings.SCORE_MODE, settings.SCORE_LIB_ROOT = settings.LOCAL, tmp_path
    monkeypatch.setattr(library_actions, "library", lambda: types.SimpleNamespace(entry=lambda address: None))
    monkeypatch.setattr(library_actions, "run", lambda arguments: pytest.fail(f"ran {arguments}"))
    key = world.store.records("closeup@beta")[-1]["key"]
    decision = {"node": "closeup@alpha", "output": world.outputs["closeup@alpha waiting"], "decision": "accept"}
    figure, waiver = {"euros": 12.5}, {"node": "closeup@beta", "output": world.outputs["closeup@beta"],
                                       "check": "looks", "reason": "three faults are fine here"}
    requests = [  # in order: (what, kind, user, payload, in an agent's process, state, words in its detail or None)
        *[(f"a stranger's {kind}", kind, "mallory", payload, False, "refused", "not this store's owner")
          for kind, payload in (("decision", decision), ("books-figure", figure), ("waiver", waiver))],
        *[(f"his {kind} in an agent's process", kind, "joey", payload, True, "refused", None)
          for kind, payload in (("books-figure", figure), ("waiver", waiver))],
        *[(f"a {kind}, which no button sends", kind, "joey", {"euros": 40.0}, False, "refused", None)
          for kind in ("stop", "month")],
        *[(f"{kind} naming a path", kind, "joey", payload, False, "refused", "is not a scene name")
          for kind, payload in (("concept-pick", {"place": "../../accepts", "sha": None}),
                                ("plan-named", {"place": "a/b", "names": []}),
                                ("environment-save", {"world": "..", "concept": {}, "locked": False}))],
        ("a library address not in it", "library", "joey", {"action": "withdraw", "addresses": [
            "--upload-pack=touch x"]}, False, "refused", "is not in the library"),
        ("his books figure", "books-figure", "joey", figure, False, "done", None),
        ("his waiver", "waiver", "joey", waiver, False, "done", None),
        ("his change", "change", "joey", {"place": "alpha", "stage": "closeup", "words": "redder"}, False, "done",
         None),
    ]
    for what, kind, user, payload, agent, state, words in requests:
        monkeypatch.setattr(actions, "agent_started", lambda agent=agent: agent)
        applied = applying.apply({"kind": kind, "user": user, "payload": payload}, world.source)
        assert applied.state == state and (words is None or words in applied.detail), (what, applied.detail)
        if state == "refused":  # a refused request writes nothing: no books, no waiver, no inbox, no stop
            assert not world.books.exists() and not world.store.waivers("closeup@beta", key), what
            assert not list((home / "inbox").glob("*.json")), what
    assert review_web.stop_line(world.store, "world1") is None  # only his stop line made in chat sets a stop
    books = json.loads(world.books.read_text())
    assert books["google_before"] == 12.5 and books["google_by"] == "joey" and books["state"] == "known"
    assert world.store.waivers("closeup@beta", key)["looks"]["by"] == "joey"
    assert list((home / "inbox").glob("*.json"))


    # upkeep passes: from a checkout not clean and pushed, or when the runner's price fails, the pass stops and says
    # why; else it prices, makes the basket again from the runner's plan in this checkout (an agent worktree's basket
    # of yesterday replaced), tidies the checkouts and runs the USD check, each said in its one line
    refusals = [  # (the tree's refusal, the runner's price, the pattern of what the pass says)
        (unpushed, (PRICED, None), re.escape(f"REFUSED: nothing done: {unpushed}; sweep: test")),
        (None, (None, "the runner's price failed: exit 1"),
         re.escape("REFUSED: the runner's price failed: exit 1; ") + ".*gaps.*" + re.escape(
             "; remake batch (estimate): test; benchmarks: none listed; library pictures: test; library demos: test")),
    ]
    for tree, price, words in refusals:
        with monkeypatch.context() as patch:
            offline(patch)
            patch.setattr(client, "tree_refusal", lambda repo, tree=tree: tree)
            patch.setattr(client, "runner_price", lambda repo, environment, price=price: price)
            said = client.sync_pass(world.source, FakeBackend())
        assert re.fullmatch(words, said), said
    proposals = home / "proposals"
    records.put_index(proposals, {"made_at": "2026-10-20T17:45:33Z", "checkout": "/x/.claude/worktrees/agent-a",
                                  "items": [{"id": "navigation-pieces", "nodes": {"closeup@navigation": {}}}]})
    with monkeypatch.context() as patch:
        priced = fed(patch)
        patch.setattr(FakeBackend, "plan_buys", ["closeup@alpha", "pixal@beta"])
        said = client.sync_pass(world.source, FakeBackend())
    assert "library problems" in said, said  # the library sweep ran
    # and the gaps after it: with no store under PROPS_HOME they fail loudly, said in the pass's words
    assert "gaps failed: exit 1: no store at " in said, said
    assert said.startswith("checkouts: 0 left launching failed, 0 ended batches' lines taken back"), said
    assert "usd check: test" in said, said
    assert said.endswith(f"{PRICED}; plans for the plan stage: test; remake batch (estimate): test; benchmarks: none "
                         "listed; basket made: 2 items, 2 paid steps; library pictures: test; library demos: test"), said
    assert priced == [world.source.world.name]
    index = records.index(proposals)
    assert index["checkout"] == str(make.REPO) and index["made_at"] > "2026-10-20T17:45:33Z"
    assert index["commit"] == make.commit()
    assert sorted(node for item in index["items"] for node in item["nodes"]) == ["closeup@alpha", "pixal@beta"]

    # his decisions made in chat (sync/chat_decisions.py, owner 2026-10-27), each through one table: recorded quoted
    # by his name, a twin asked before its target changed; a cockpit refusal hands the yes back unused; applied once
    # through the request code of his click, the agent marks lifted only inside; the twin refused, nothing marked used
    from score.dashboard.films import script
    from score.dashboard.sync import chat_decisions
    from score.store import AGENT_MARKERS
    monkeypatch.setattr(actions, "agent_started", agent_started)
    mark, output, seen, real = AGENT_MARKERS[0], world.outputs["closeup@alpha waiting"], [], applying.apply
    monkeypatch.setenv(mark, "1")
    monkeypatch.setattr("score.adapters.compute.cap_baseline",
                        lambda: {"at": "t", "whole": 2127.39, "lines": {"ff|l4": 169.0}})
    world.books.unlink()  # his books figure above was this month's: the books month asks a month not written yet
    month = review_web.books_of("")[0]
    script.save(settings.SCORE_HOME, script.blank("chat-film", "Chat"))
    cap = {"euros": "300", "line": "255", "start": "2026-11-09T18:40:00+00:00", "month_cap": "2970",
           "finish": "2026-11-21T23:59:00+00:00", "standing": "15"}
    takes = {"reason": "stool: outline 0.392 under 0.5", "takes": ["stool_1"]}
    edited = lambda: script.save(settings.SCORE_HOME, script.blank("chat-film", "Chat, edited"))  # noqa: E731
    decided = [  # (decision, target, given, the twin: (its given, why it is refused, what changes after it is asked)
        #          or None, its target, the request his click makes, words of the applied detail, what it reads
        #          afterwards: (reader, the reading))
        ("accept", "closeup@alpha", {"output": output, "worse_reason": "one fault is fine"},
         ({"output": output, "reason": "red"}, "changed since he answered", None),  # a reject, then his accept
         {"node": "closeup@alpha", "output": output, "accepted": ANY},
         {"kind": "decision", "user": "joey", "payload": {"node": "closeup@alpha", "output": output,
                                                          "decision": "accept", "reason": "",
                                                          "worse_reason": "one fault is fine"}},
         "", (lambda: (world.store.accepted("closeup@alpha"),
                       world.store.current_accept("closeup@alpha")["by"]), (output, "joey"))),
        ("reject", "closeup@alpha", {"output": output, **takes}, None,  # its takes reach his reject record
         {"node": "closeup@alpha", "output": output, "accepted": output},
         {"kind": "decision", "user": "joey", "payload": {"node": "closeup@alpha", "output": output,
                                                          "decision": "reject", "worse_reason": "", **takes}},
         "", (lambda: world.store.rejects("closeup@alpha")[-1]["takes"], ["stool_1"])),
        ("spend", "relight-hangar", {"euros": "4", "purpose": "one relight", "under_cap": "env1"},
         ({"euros": "2", "purpose": "relight"}, "gone since the question", None),  # the name took a yes since
         {"override": "relight-hangar", "euros": 4.0, "purpose": "one relight", "cap": "env1"},
         {"kind": "spend-override", "user": "joey", "payload": {"name": "relight-hangar", "euros": 4.0,
                                                                "purpose": "one relight", "cap": "env1"}},
         'SCORE_SPEND_TICKET="override relight-hangar"',  # counted under the env1 cap, as he said
         (lambda: picked(world.store.spend_yes("override", "relight-hangar"), "euros", "by", "purpose", "cap"),
          (4.0, "joey", "one relight", "env1"))),
        ("stop", "chat-stop", {"euros": "10"}, ({"euros": "12"}, "changed since he answered", None),  # a line since
         {"world": "chat-stop", "euros": 10.0, "line": None},
         {"kind": "stop-line", "user": "joey", "payload": {"world": "chat-stop", "euros": 10.0,
                                                           "reason": "his yes in chat: Yes", "replaces": None}},
         "EUR 10.00", (lambda: picked(review_web.stop_line(world.store, "chat-stop"), "euros", "by", "baseline.bill"),
                       (10.0, "joey", 1.0))),
        ("cap", "env1", cap, ({**cap, "line": "200"}, "changed since he answered", None),  # a cap written since
         {"cap": "env1", "euros": 300.0, "line": 255.0, "start": cap["start"], "month_cap": 2970.0,
          "finish": cap["finish"], "standing_per_day": 15.0, "open": True, "current": None},
         {"kind": "cap-line", "user": "joey", "payload": {
             "cap": "env1", "euros": 300.0, "line": 255.0, "start": cap["start"], "month_cap": 2970.0,
             "finish": cap["finish"], "standing_per_day": 15.0, "open": True, "replaces": None,
             "words": "his yes in chat: Yes", "yes": ANY}},
         "paid work stops at EUR 255.00",
         (lambda: picked(review_web.cap_now("env1"), "by", "open", "baseline.whole", "line"),
          ("joey", True, 2127.39, 255.0))),
        ("cap", "env1", {"close": True}, None, {"cap": "env1", "open": False, "current": ANY},  # its film accepted
         {"kind": "cap-line", "user": "joey", "payload": {
             "cap": "env1", "euros": None, "line": None, "start": None, "month_cap": None, "finish": None,
             "standing_per_day": None, "open": False, "replaces": ANY, "words": "his yes in chat: Yes", "yes": ANY}},
         "", (lambda: review_web.cap_now("env1")["open"], False)),
        ("lock-film", "chat-film", {}, ({}, "changed since he answered", edited),  # the script edited since
         {"film": "chat-film", "script": ANY},
         {"kind": "film-lock", "user": "joey", "payload": {"film": "chat-film", "script": ANY}},
         "", (lambda: picked(script.locked(settings.SCORE_HOME, "chat-film"), "title"), ("Chat, edited",))),
        ("lock-film", "chat-film", {"size": "1920x1080"}, None,  # his re-lock at 1080p: the size alone moves
         {"film": "chat-film", "script": ANY},
         {"kind": "film-lock", "user": "joey", "payload": {"film": "chat-film", "script": ANY}},
         "", (lambda: picked(script.locked(settings.SCORE_HOME, "chat-film"), "title", "size"),
              ("Chat, edited", [1920, 1080]))),
        (review_web.BOOKS_MONTH, month, {"euros": "0"},
         ({"euros": "5"}, "changed since he answered", None),  # the books written since
         {"month": month, "euros": 0.0, "books": {}},
         {"kind": "books-figure", "user": "joey", "payload": {"euros": 0.0}}, f"books known for {month}",
         (lambda: picked(json.loads(world.books.read_text()), "month", "state", "google_before", "google_by"),
          (month, "known", 0.0, "joey"))),
    ]
    for decision, target, given, twin, then, item, words, (reads, reading) in decided:
        asked = f"{decision} {target}?"
        twin_yes = twin and chat_decisions.record(decision, target, "Yes", asked, **twin[0])
        if twin and twin[2]:
            twin[2]()
        yes = chat_decisions.record(decision, target, "Yes", asked, **given)
        assert (yes["target"], yes["by"], yes["question"]) == (then, "joey", asked), decision
        monkeypatch.setattr(applying, "apply", lambda request, source: applying.Applied("refused", "not now"))
        assert chat_decisions.apply(yes["id"]).state == "refused", decision  # handed back: the same yes applies later
        assert not review_web.decision_yes_used(world.store, yes["id"]) and found(reads) != reading, decision
        monkeypatch.setattr(applying, "apply", lambda request, source: seen.append(
            (request, mark in os.environ)) or real(request, source))
        applied = chat_decisions.apply(yes["id"])
        assert applied.state == "done" and words in applied.detail, (decision, applied.detail)
        assert seen[-1] == (item, False) and os.environ[mark] == "1", (decision, seen[-1])
        assert reads() == reading, decision
        assert "used already" in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, yes["id"]).value)
        if twin:
            assert twin[1] in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, twin_yes["id"]).value)
            assert not review_web.decision_yes_used(world.store, twin_yes["id"]) and reads() == reading, decision
    go = chat_decisions.record("go", "world1", "sure", "Let the run accept passing results on its own?")
    assert review_web.owners_go(world.store, go["id"], "world1") == go
    assert review_web.owners_go(world.store, go["id"], "w2") is None
    assert review_web.owners_go(world.store, yes["id"], "world1") is None  # only a go
    for yes_id, why in ((go["id"], "is a go"), ("20261027T000000000000Z", "is no quoted decision yes")):
        assert why in str(pytest.raises(chat_decisions.Refused, chat_decisions.apply, yes_id).value)
    unrecorded = [  # (decision, target, answer, question, given, words of the refusal)
        ("accept", "closeup@alpha", "", "Q?", {"output": output}, "quotes the owner's answer"),
        ("accept", "closeup@alpha", "Yes", "", {"output": output}, "quotes the owner's answer"),
        ("reject", "closeup@alpha", "Yes", "Q?", {"output": output}, "says why"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": "0" * 64}, "has no output"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": output, "euros": "4"}, "only a spend, a books month"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": output, "takes": ["stool_1"]}, "only a reject names takes"),
        *[("spend", name, "Yes", "Q?", {"euros": euros, "purpose": purpose}, why) for euros, purpose, name, why in (
            ("4", "", "a", "says what it is for"), ("0", "x", "a", "above 0"), ("four", "x", "a", "as an amount"),
            ("4", "x", "relight-hangar", "holds a yes already"))],
        ("spend", "a", "Yes", "Q?", {"euros": "4", "purpose": "x", "under_cap": "env2"}, "env1 cap or none"),
        ("accept", "closeup@alpha", "Yes", "Q?", {"output": output, "under_cap": "env1"}, "only a spend counts under"),
        *[(review_web.BOOKS_MONTH, target, "Yes", "Q?", {"euros": euros}, why) for euros, target, why in (
            ("-1", month, "finite figure"), ("nan", month, "finite figure"), ("zero", month, "as an amount"),
            ("", month, "as an amount"), ("0", "2020-01", "this month's provider figure only"))],
        (review_web.BOOKS_MONTH, month, "Yes", "Q?", {"euros": "0", "purpose": "x"}, "only a spend names a purpose"),
        *[("stop", "chat-stop", "Yes", "Q?", {"euros": euros}, why) for euros, why in (
            ("0", "finite amount above"), ("-1", "finite amount above"), ("nan", "finite amount above"),
            ("ten", "as an amount"), ("", "as an amount"))],
        ("stop", "chat-stop", "Yes", "Q?", {"euros": "10", "line": "5"}, "only a cap names a line"),
        ("cap", "env1", "Yes", "Q?", {"euros": "300", "line": "400", "start": "2026-11-09T18:40"}, "is within its"),
        ("cap", "env1", "Yes", "Q?", {"euros": "300", "line": "255"}, "names the time its count starts"),
        ("lock-film", "chat-film", "Yes", "Q?", {"size": "0x1080"}, "above 0 both ways"),
        ("go", "world1", "Yes", "Q?", {"size": "1920x1080"}, "only a film lock names a size"),
        ("cap", "env1", "Yes", "Q?", {"euros": "nan", "line": "255", "start": "2026-11-09T18:40"}, "finite amount"),
    ]
    for decision, target, answer, question, given, why in unrecorded:
        refused = pytest.raises(chat_decisions.Refused, chat_decisions.record, decision, target, answer, question,
                                **given)
        assert why in str(refused.value), (decision, target, given, str(refused.value))


    # the pass's own steps: a step's leftovers end with it, and a step out of time is ended and says so
    settings.SCORE_REPO = tmp_path
    # the leftover lets go of the step's output, so only the group's end can stop it
    leftover = ("import subprocess, time; print(subprocess.Popen(['sleep', '60'], stdout=subprocess.DEVNULL, "
                "stderr=subprocess.DEVNULL).pid, flush=True)")
    steps = [  # (what, the step's program, its limit, its exit is 0, its last error line or None)
        ("a step with a leftover", leftover, None, True, None),  # 2026-10-25: chrome-headless stayed after the pass
        ("a step out of its time", leftover + "; time.sleep(60)", 1, False, "out of time after 1 s"),
    ]
    for what, program, limit, ok, error in steps:
        done = client.step_run([sys.executable, "-c", program], grace=2, **({"limit": limit} if limit else {}))
        assert (done.returncode == 0) == ok and (error is None or done.stderr.strip().splitlines()[-1] == error), what
        stat = pathlib.Path(f"/proc/{int(done.stdout)}/stat")  # its output kept

        def ended(stat=stat):
            try:
                return stat.read_text().rpartition(")")[2].split()[0] == "Z"
            except FileNotFoundError:
                return True
        deadline = time.monotonic() + 2  # a kill lands a moment after it is sent: at most 2 s, never the minute
        while not ended() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ended(), what


def picked(record, *paths):
    """The values at the dotted `paths` of a record (a dict of dicts)."""
    found_values = []
    for path in paths:
        value = record
        for name in path.split("."):
            value = value[name]
        found_values.append(value)
    return tuple(found_values)


def found(reads):
    """What `reads` reads, None while what it reads is not written yet."""
    try:
        return reads()
    except (TypeError, KeyError, IndexError, OSError):
        return None


@pytest.fixture
def owner_books(world, monkeypatch, settings):
    """The fixture world with no agent marks and no books yet (under this run's temp PROPS_HOME), the stop's first
    books given."""
    from score.review import web
    from score.store import AGENT_MARKERS
    for name in AGENT_MARKERS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(web, "books_now", lambda: {"month": "2026-10", "bill": 1.0, "ledger": 1.0})
    world.books = settings.SCORE_PROPS_HOME / "cloud" / "books.json"
    world.books.unlink(missing_ok=True)
    yield world
    world.books.unlink(missing_ok=True)
