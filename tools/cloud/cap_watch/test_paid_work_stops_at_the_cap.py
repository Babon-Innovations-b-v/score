"""Paid work stops at the env1 cap: the watcher counts the larger of the whole bill's growth and its own meter, takes
off the shared lines only what it proved babon's, and stops paid work at the line, or once the bill or the machines
cannot be read for 15 minutes. No cloud: a folder book, the bill and the machines faked.

Breaks (each applied once, seen red, reverted), in tools/cloud/cap_watch/watch.py unless named:
- unreadable bill: one_pass's unread reading carries `"good_at": iso(now)` (an unread pass reads as fresh).
- scw [] while the cluster shows 3 L4: tools/cloud/backends/scaleway.py live_rate's `if missing:` becomes `if False:`.
- the meter: counter_of returns `billed` for the counter (the bill's card lag hides 10 L4 for 3 h).
- under the line: guard.cap_refusal's `if counter >= line:` becomes `if counter >= 0:`.
- babon's share: babon_proven ignores LAG_HOURS (`>= 0`), or counter_of takes the proven euros off uncapped.
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
    stops = []

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
