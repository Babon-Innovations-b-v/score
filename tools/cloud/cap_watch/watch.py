"""The env1 cap's watcher (the plan of 2026-11-09, B3; K1, K2, R4): every 5 minutes, beside nothing, it reads the
whole bill of every project and every machine, disk and address standing now, keeps one reading in the SCORE object
store, and stops paid work once the counter reaches the cap's stop line or the November cap, or once the bill or the
machines cannot be read for 15 minutes (it fails closed).

    python tools/cloud/cap_watch/watch.py pass     # one pass (its CronJob's command); one summary line

The counter is the larger of two measures, both counted from the cap's start:

- the bill: each counted line's growth over the cap's baseline (tools/cloud/backends/scaleway.bill_all: SCORE's
  projects whole, babon's shared project but its own services), less what is proven babon's on the shared machine,
  disk and address lines (the babon-owned things this watcher saw, at their price, from the newest reading at least
  LAG_HOURS old, since the bill lags its machines; each line's share at most its growth). What is not proven
  babon's counts as env1's.
- the meter: every SCORE thing ever seen standing since the start (scaleway.live_rate), each at what it has cost up
  to the last pass that saw it, a processor machine by its started hours: the bill's hours-long card lag cannot hide a
  machine that runs.

A stop (stop_paid_work) writes its record under the cap (caps/<name>/stops/), the owner's line in it, and deletes
every score Job in the cluster's jobs namespace whatever box launched it; no latch: every cloud rent point
(compute.require_cloud) and every cluster poll (tools/cloud/k8s/submitter.over_limits) reads the same reading and
refuses while it stands, so the next pass under the line lets paid work start again.
"""
import argparse
import datetime
import os
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
for folder in (REPO, REPO / "tools" / "cloud", REPO / "tools" / "cloud" / "backends"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

from score.adapters.compute import guard  # noqa: E402

LAG_HOURS = 6.0  # babon's proven usage is taken off the shared lines only once this old: the bill lags by hours
JOBS_NAMESPACE = "score-jobs"
RUN_LABEL = "score.dev/run"  # tools/cloud/k8s/submitter.RUN_LABEL: every score Job carries it


def iso(seconds):
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).isoformat(timespec="seconds")


def seconds_of(stamp):
    return datetime.datetime.fromisoformat(stamp).timestamp()


def seen(previous, live, owner):
    """{id: {line, euros}} of every `owner` thing seen so far: each one's euros the larger of what the last reading
    kept and what it has cost now (a thing gone keeps its last figure)."""
    found = {key: dict(value) for key, value in (previous or {}).items()}
    for key, item in live.items():
        if item["owner"] == owner:
            before = found.get(key, {}).get("euros", 0.0)
            found[key] = {"line": item["line"], "euros": max(before, item["euros"])}
    return found


def growth(cap, lines):
    """{line: euros} each counted line has grown by since the cap's baseline, never below 0."""
    base = cap["baseline"]["lines"]
    return {key: max(0.0, euros - base.get(key, 0.0)) for key, euros in lines.items()}


def babon_proven(book, now, name):
    """{line: euros} proven babon's on the shared lines, as the newest reading at least LAG_HOURS old kept it."""
    for key in reversed(book.keys(f"{guard.CAPS}/{name}/readings/")):
        reading = book.read(key)
        if not reading.get("unread") and now - seconds_of(reading["at"]) >= LAG_HOURS * 3600:
            proven = {}
            for item in (reading.get("babon") or {}).values():
                proven[item["line"]] = proven.get(item["line"], 0.0) + item["euros"]
            return proven
    return {}


def counter_of(cap, bill, score_seen, proven):
    """(the bill's measure, the meter's, the counter: the larger)."""
    grown = growth(cap, bill["lines"])
    billed = sum(max(0.0, euros - min(euros, proven.get(key, 0.0))) for key, euros in grown.items())
    metered = sum(item["euros"] for item in score_seen.values())
    return round(billed, 2), round(metered, 2), round(max(billed, metered), 2)


def over(cap, reading):
    """Why paid work stops on this reading, or None (guard.cap_refusal with no start asked for)."""
    return guard.cap_refusal(cap, reading, seconds_of(reading["at"]))


def read_bill(last_whole):
    import scaleway
    return scaleway.bill_all(last_whole)


def read_live(start, now, names):
    import scaleway
    return scaleway.live_rate(start, now, names)


def unread_kinds():
    import scaleway
    return (scaleway.Unread, subprocess.CalledProcessError, OSError, ValueError, KeyError)


def stop_paid_work(book, name, why, now, run=subprocess.run):
    """Stop every paid run: the stop's record under the cap (the owner's line) and every score Job in the jobs
    namespace deleted, whatever box launched it; the record."""
    done = run(["kubectl", "delete", "jobs", "-n", JOBS_NAMESPACE, "-l", RUN_LABEL, "--ignore-not-found",
                "--wait=false", "--cascade=background"], capture_output=True, text=True)
    record = {"at": iso(now), "why": why, "jobs": (done.stdout or "").strip()[-2000:],
              "jobs_error": (done.stderr or "").strip()[-500:] if done.returncode else None,
              "owner_line": f"env1 cap: paid work stopped: {why}"}
    return guard.cap_write(book, "stops", record, name)


def one_pass(book, bill_reader=read_bill, live_reader=read_live, stop=stop_paid_work, now=None,
             unread=None, name=guard.CAP):
    """One watch pass (the module's docstring); its reading, or None when no cap is open."""
    now = time.time() if now is None else now
    cap = guard.current_cap(book, name)
    if not cap or not cap.get("open"):
        return None
    previous = guard.cap_newest(book, "readings", name)
    good = previous if previous and not previous.get("unread") else None
    good_at = good["at"] if good else (previous or {}).get("good_at")
    try:
        bill = bill_reader((good or {}).get("whole"))
        names = {project_id: project for project, project_id in bill["projects"].items()}
        live = live_reader(seconds_of(cap["start"]), now, names)
    except (unread or unread_kinds()) as error:
        reading = {"at": iso(now), "unread": f"{type(error).__name__}: {error}"[:500], "good_at": good_at,
                   "counter": (previous or {}).get("counter", 0.0), "whole": (previous or {}).get("whole"),
                   "score": (previous or {}).get("score"), "babon": (previous or {}).get("babon")}
    else:
        score_seen = seen((previous or {}).get("score"), live, "score")
        babon_seen = seen((previous or {}).get("babon"), live, "babon")
        billed, metered, counter = counter_of(cap, bill, score_seen, babon_proven(book, now, name))
        reading = {"at": iso(now), "unread": None, "counter": counter, "bill": billed, "meter": metered,
                   "whole": bill["whole"], "rate": round(sum(item["per_hour"] for item in live.values()
                                                             if item["owner"] == "score"), 3),
                   "score": score_seen, "babon": babon_seen}
    guard.cap_write(book, "readings", reading, name)
    why = over(cap, reading)
    if why:
        stop(book, name, why, now)
    return {**reading, "stopped": why}


def main():
    parser = argparse.ArgumentParser(description="the env1 cap's watcher: one pass")
    parser.add_argument("command", choices=("pass",))
    parser.parse_args()
    reading = one_pass(guard.cap_book())
    if reading is None:
        print("cap-watch: no open cap")
        return
    state = f"STOPPED: {reading['stopped']}" if reading["stopped"] else "under the line"
    print(f"cap-watch: counter EUR {reading['counter']:.2f} (bill {reading.get('bill')}, meter {reading.get('meter')}"
          f"{', unread: ' + reading['unread'] if reading['unread'] else ''}); {state}")


if __name__ == "__main__":
    os.environ.setdefault("SCORE_CLOUD", "scaleway")
    main()
