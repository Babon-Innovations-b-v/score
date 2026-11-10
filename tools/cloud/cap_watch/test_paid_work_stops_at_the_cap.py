"""Paid work stops at the env1 cap: the watcher counts the larger of the whole bill's growth and its own meter, takes
off the shared lines only what it proved babon's, and stops paid work at the line, or once the bill or the machines
cannot be read for 15 minutes. No cloud: a folder book, the bill and the machines faked.

Breaks (each applied once, seen red, reverted), in tools/cloud/cap_watch/watch.py unless named:
- unreadable bill: one_pass's unread reading carries `"good_at": iso(now)` (an unread pass reads as fresh).
- scw [] while the cluster shows 3 L4: tools/cloud/backends/scaleway.py live_rate's `if missing:` becomes `if False:`.
- the meter: counter_of returns `billed` for the counter (the bill's card lag hides 10 L4 for 3 h).
- under the line: guard.cap_refusal's `if counter >= line:` becomes `if counter >= 0:`.
- babon's share: babon_proven ignores LAG_HOURS (`>= 0`), or counter_of takes the proven euros off uncapped.
- the meter's addresses (2026-11-10: 1,027 node addresses, half IPv6, each counted from the cap's start, EUR 111
  against the bill's EUR 4): scaleway.live_rate's `born = created_at(machine[0]) ...` becomes `born = 0.0`, or its skip of
  `"ipv6"` types is dropped.
- the stop (plan B4): stop_paid_work drops its `stop_runner_servers()` call (the runner's machines keep billing), or
  one_pass drops its `cleaner` call (leftovers never cleaned).
- the sweep (2026-11-10: checkout 75's stopped runs kept 4 L4 workers for hours): dead_jobs ignores the mark's age
  (a live run's Jobs deleted), or takes a Job with no mark, or a finished one; or one_pass drops its `sweeper` call,
  or makes it only under an open cap.
"""
import datetime
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backends"))
sys.path.insert(0, str(HERE.parent))

import scaleway  # noqa: E402
import watch  # noqa: E402
from score.adapters.compute import guard  # noqa: E402

START = datetime.datetime(2026, 11, 9, 18, 40, tzinfo=datetime.timezone.utc).timestamp()
L4 = "babon-platform|/instance/server/l4_1_24g/fr-par-2"
CPU = "farm-factory|/instance/server/pop2_hc_64c_128g/nl-ams-2"
NAMES = {"farm-factory": "ff-id", "babon-platform": "bp-id"}


def bill(lines, whole=2000.0):
    return {"whole": whole, "lines": lines, "projects": NAMES}


def l4s(count, hours, owner="score"):
    return {f"{owner}-l4-{index}": {"owner": owner, "kind": "machine", "line": L4, "per_hour": 0.79,
                                    "euros": round(0.79 * hours, 4)} for index in range(count)}


def test_paid_work_stops_at_the_line_or_when_the_bill_is_blind_and_never_under_it(tmp_path, monkeypatch):
    book = guard.FolderBook(tmp_path / "book")
    monkeypatch.setattr(guard, "running_under_agent", lambda: False)
    guard.set_cap(book, {"euros": 300.0, "line": 255.0, "start": watch.iso(START), "by": "joey",
                         "at": watch.iso(START), "baseline": {"whole": 2000.0, "lines": {L4: 400.0, CPU: 100.0}}})
    stops, cleaned = [], []
    monkeypatch.setattr(watch, "clean", lambda: cleaned.append(1) or {"machines": [], "disks": []})
    swept, sweep = [], watch.sweep  # the real one is checked at the end
    monkeypatch.setattr(watch, "sweep", lambda now: swept.append(now) or {"deleted": []})

    def stop(book_, name, why, now):
        stops.append(why)

    def passes(at_hours, bill_read, live=None, unread=False):
        def bill_reader(last):
            if unread:
                raise scaleway.Unread("no line")
            return bill_read
        return watch.one_pass(book, bill_reader, lambda start, now, names: live or {}, stop,
                              now=START + at_hours * 3600)

    # under the line: nothing stops, the counter the bill's growth
    first = passes(1, bill({L4: 400.0, CPU: 140.0}))
    assert (first["counter"], first["stopped"], stops) == (40.0, None, [])
    assert cleaned == [1] and first["cleaned"] == {"machines": [], "disks": []}  # every pass cleans leftovers
    assert swept == [START + 3600] and first["swept"] == {"deleted": []}  # and sweeps dead runs' Jobs
    assert watch.one_pass(guard.FolderBook(tmp_path / "no-cap"), now=START) is None and swept[-1] == START  # cap or none
    # unreadable bill: 5 minutes after a good read still the good counter, past 15 minutes paid work stops
    assert passes(1 + 5 / 60, None, unread=True)["stopped"] is None
    assert "fails closed" in passes(1 + 20 / 60, None, unread=True)["stopped"] and len(stops) == 1
    assert passes(1.5, bill({L4: 400.0, CPU: 150.0}))["stopped"] is None  # read again: no latch
    # the meter: the CPU line fresh, the L4 line flat for 3 h while 10 SCORE L4s run: counted, and over the line stops
    metered = passes(4.5, bill({L4: 400.0, CPU: 160.0}), live=l4s(10, 3.0))
    assert (metered["bill"], metered["meter"]) == (60.0, 23.7) and metered["counter"] == 60.0
    later = passes(36, bill({L4: 400.0, CPU: 160.0}), live=l4s(10, 34.5))
    assert later["counter"] == later["meter"] == 272.55 and "stop line" in later["stopped"] and len(stops) == 2
    # babon's share: a babon L4 seen 8 h is taken off the shared line once its reading is LAG_HOURS old, capped there
    fresh = guard.FolderBook(tmp_path / "split")
    guard.set_cap(fresh, {"euros": 300.0, "line": 255.0, "start": watch.iso(START), "by": "joey",
                          "at": watch.iso(START), "baseline": {"whole": 2000.0, "lines": {L4: 400.0}}})
    split = [watch.one_pass(fresh, lambda last: bill({L4: 400.0 + grown}),
                            lambda start, now, names, h=hours: l4s(1, h, "babon"), stop, now=START + hours * 3600)
             for hours, grown in ((2.0, 1.0), (8.0, 10.0), (9.0, 3.0))]
    assert [reading["bill"] for reading in split] == [1.0, 8.42, 1.42]  # less the 1.58 the 2 h pass proved
    assert watch.counter_of({"baseline": {"lines": {L4: 0.0}}}, bill({L4: 5.0}), {}, {L4: 50.0})[0] == 0.0
    # scw lists no machine while the cluster shows 3 L4 nodes: the meter refuses to read, and a blind first pass stops
    monkeypatch.setattr(scaleway, "scw", lambda *words: [])
    try:
        scaleway.live_rate(START, START + 60, {"bp-id": "babon-platform"}, nodes={"n1", "n2", "n3"})
        raise AssertionError("a meter blind to three running nodes read")
    except scaleway.Unread as unread:
        assert "3 cluster node" in str(unread)
    blind = guard.FolderBook(tmp_path / "blind")
    guard.set_cap(blind, {"euros": 300.0, "line": 255.0, "start": watch.iso(START), "by": "joey",
                          "at": watch.iso(START), "baseline": {"whole": 0.0, "lines": {}}})
    reading = watch.one_pass(blind, lambda last: bill({}), lambda start, now, names: scaleway.live_rate(
        start, now, names, nodes={"n1", "n2", "n3"}), stop, now=START + 60)
    assert reading["unread"].startswith("Unread") and "fails closed" in reading["stopped"] and len(stops) == 3
    # the meter's addresses: an IPv4 by its machine's life (a node's made 20 h after the start costs one started hour
    # at 20 h 20 min), never the free IPv6 beside it; a loose one from the cap's start (it fails closed)
    born = watch.iso(START + 20 * 3600).replace("+00:00", "Z")
    node = {"id": "n1", "project": "bp-id", "tags": ["pool-name=gate-pro2"], "state": "running",
            "commercial_type": "PRO2-S", "creation_date": born}
    cloud = {("instance", "server", "list", "zone=fr-par-1"): [node],
             ("instance", "ip", "list", "zone=fr-par-1"): [
                 {"id": "v4", "type": "routed_ipv4", "project": "bp-id", "server": {"id": "n1"}},
                 {"id": "v6", "type": "routed_ipv6", "project": "bp-id", "server": {"id": "n1"}},
                 {"id": "lost", "type": "routed_ipv4", "project": "bp-id", "server": None}]}
    monkeypatch.setattr(scaleway, "scw", lambda *words: cloud.get(words, []))
    monkeypatch.setattr(scaleway, "price", lambda kind, zone: (0.001, 1))
    metered = scaleway.live_rate(START, START + 20 * 3600 + 20 * 60, {"bp-id": "babon-platform"}, nodes={"n1"})
    addresses = {key: item["euros"] for key, item in metered.items() if item["kind"] == "address"}
    assert addresses == {"v4": 0.005, "lost": 21 * 0.005}
    assert metered["v4"]["line"] == "babon-platform|/network/ipam/ipv4/fr-par-1" and metered["v4"]["owner"] == "score"
    # the stop itself: every box's Jobs and every runner machine, a failed machine stop named, never swallowed
    class Done:
        returncode, stdout, stderr = 0, 'job.batch "score-r-a-g0" deleted', ""

    class Cloud:
        def stop_runner_servers(self):
            return ["r-1", "r-2"]
    asked = []
    record = watch.stop_paid_work(book, guard.CAP, "past the stop line", START, run=lambda words, **_: asked.append(
        words) or Done(), cloud=Cloud())
    assert asked[0][-5:] == ["-l", "score.dev/run", "--ignore-not-found", "--wait=false", "--cascade=background"]
    assert record["machines"] == ["r-1", "r-2"] and "score-r-a-g0" in record["jobs"]

    class Refused:
        def stop_runner_servers(self):
            raise RuntimeError("no right")
    assert "no right" in watch.stop_paid_work(book, guard.CAP, "x", START + 1, run=lambda words, **_: Done(),
                                              cloud=Refused())["machines_error"]
    # the sweep: an unfinished score Job whose owner's alive mark is past ALIVE_STALE_MINUTES is deleted, whatever box
    # made it; a fresh mark, no mark (made before the beat, or its beat refused) or a finished Job is left
    stale, fresh_mark = str(int(START - watch.ALIVE_STALE_MINUTES * 60 - 1)), str(int(START - 60))

    def job(name, mark=None, finished=False):
        return {"metadata": {"name": name, "annotations": {watch.ALIVE_NOTE: mark} if mark else {}},
                "status": {"conditions": [{"type": "Complete", "status": "True"}]} if finished else {"active": 1}}
    items = [job("score-w-conductor-meshparts-card-1", stale), job("score-r-live-0-g0", fresh_mark),
             job("score-r-old-0-g0"), job("score-r-done-0-g0", stale, finished=True), job("score-r-dead-1-g0", stale)]
    assert watch.dead_jobs(items, START) == ["score-r-dead-1-g0", "score-w-conductor-meshparts-card-1"]
    import json

    class Answer:
        def __init__(self, stdout="", returncode=0, stderr=""):
            self.stdout, self.returncode, self.stderr = stdout, returncode, stderr
    calls = []

    def kubectl(words, **_):
        calls.append(words)
        return Answer(json.dumps({"items": items})) if words[1] == "get" else Answer("deleted")
    assert sweep(START, run=kubectl) == {"deleted": ["score-r-dead-1-g0", "score-w-conductor-meshparts-card-1"]}
    assert calls[0][:6] == ["kubectl", "get", "jobs", "-n", "score-jobs", "-l"] and calls[1][:6] == [
        "kubectl", "delete", "jobs", "-n", "score-jobs", "score-r-dead-1-g0"]
    assert "error" in sweep(START, run=lambda words, **_: Answer(returncode=1, stderr="forbidden"))
