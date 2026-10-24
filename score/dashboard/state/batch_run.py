"""The Buy's batch as it runs, for the run monitor (`/buy/run/`, pages/run_monitor.py): read on the store's machine from
the files the batch writes, read live locally and carried in the export as batch-run.json (sync/building.py).

    batch-run.json  {read_at, checkout, at, by, state, why, started, ended, rows, eta, money, scenes, pool, problems}
      state     starting (the checkout plans it), running, waiting (running, the warm pool holds no card yet and
                stock is short), stopped (a stop, a refusal or a run gone without its result line), finished
      rows      {total, done, failed, not_run, running, queued}: total every row the checkout's runs planned, done
                those whose standing accept in the store is newer than the checkout (this run's or an earlier
                run's of the checkout, so a relaunch goes on where it was), failed and not_run from this run's own lines, running and queued the last
                heartbeat's
      eta       {likely_minutes, high_minutes} the checkout's runner times; untimed the bought steps with no
                measured price (the ETA is then at least); elapsed
      money     {spent (the last heartbeat: the cloud ledger's euros for this run's rows; None before one), open
                (paid runs open), likely, high (pricing.cleared_high: the high with the guessed steps, what the
                runner clears), guessed, stop (this batch's own room under the stop line the Buy wrote: the line
                less the spend and the reservations it was written over, on the same scale as spent; None for a
                line written without them), line (the stop line itself, the environment's), closed (taken back)}
      scenes    [{place ("" the whole environment), total, done, failed, not_run, running [step labels], state}]
      pool      the warm pool the run opened ({run, open, until, cards, processors, stock}; None before one)
      problems  [{at, place, node, kind (failed, gaps, run), words, tip}], newest first

Read only. Every input is a file: the run's detached log (heartbeats, each finished row's line, the pool it opened,
its result line), the rows' own logs (a row started in this run has written its log since), each finished row's batch
gaps (`gaps_of`) and the pool's records ($PROPS_HOME/cloud/pools/<run>/). Nothing is priced or timed here: every
number is the runner's, the checkout's or the pool's. Imports nothing from the store or the stages (hosted-light)."""
import datetime
import json
import pathlib
import re

from score.dashboard.checkout import pricing
from score.dashboard.state import groups, plain

RUN_FILE = "batch-run.json"
HEARTBEAT = re.compile(r"^heartbeat (\S+): rows done (\d+), running (\d+), queued (\d+); (.*)$")
GAUGES = re.compile(r"paid runs open (\d+), EUR ([\d.]+) in the ledger")
POOL_OPENED = re.compile(r"pool of .+ opened for run (\S+)")
RESULT = re.compile(r"^detached: (ok|failed|stopped|refused)\b")
EXIT = re.compile(r"^exit: (.+)$")  # run_with_exit_line's last word: ok, stopped (lines stopped), error, exited
REFUSAL = re.compile(r"^refused: (.+)$")  # a `score run` that refused before it drove (sys.exit), its first line
LINES_STOPPED = "stopped, "  # the exit line of a drive that ended with some lines stopped (exit_status)
ROW_LINE = re.compile(r"^([A-Za-z0-9][\w.:-]*(?:@[\w.-]+)?): (.+)$")
FAULT = re.compile(r";?\s*fault report \S+")
MACHINE_CLASS = re.compile(r"\b(gpu|cpu)-(\d+)(gb|c)(?:-(\d+)gb)?(?:-x(\d+))?\b")
NO_STOCK = re.compile(r"none in stock|no \S+ in stock|no \S+ rented")
CARD_PREFIX = "gpu"  # a pool class of graphics cards; every other class is a processor machine
LIVE = ("starting", "running", "waiting")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(moment):
    return moment.isoformat(timespec="seconds") if moment else None


def parsed(text):
    """A timestamp in ISO words as an aware datetime, or None."""
    if not text:
        return None
    found = datetime.datetime.fromisoformat(text)
    return found if found.tzinfo else found.replace(tzinfo=datetime.timezone.utc)


def place_of(node):
    return node.partition("@")[2]


def stage_of(node):
    return node.partition("@")[0]


def row_state(did):
    """failed, not_run or done for a finished row's line (graph.Runner.drive's `<node>: <what it did>`)."""
    if did.startswith("not run:"):
        return "not_run"
    return "failed" if "fault report" in did else "done"


def log_lines(path):
    path = pathlib.Path(path) if path else None
    return path.read_text(errors="replace").splitlines() if path and path.is_file() else []


def read_log(lines, planned):
    """What the run's detached log says: {beat {at, done, running, queued, open, spent}, rows {node: (state, did,
    about)}, pool (its run id), result (ok, failed, stopped, refused or None), result_line, exit (its `exit:` line's
    status, "" without one), refusal (a `refused:` line's why, "" without one)}. `about` is the heartbeat time
    before the row's line (the log stamps only its beats)."""
    found = {"beat": None, "rows": {}, "pool": None, "result": None, "result_line": "", "exit": "", "refusal": ""}
    about = None
    for line in lines:
        beat = HEARTBEAT.match(line)
        if beat:
            about = beat.group(1)
            gauges = GAUGES.search(beat.group(5))
            found["beat"] = {"at": about, "done": int(beat.group(2)), "running": int(beat.group(3)),
                             "queued": int(beat.group(4)), "open": int(gauges.group(1)) if gauges else None,
                             "spent": float(gauges.group(2)) if gauges else None}
            continue
        opened = POOL_OPENED.search(line)
        if opened:
            found["pool"] = opened.group(1)
        ended = RESULT.match(line)
        if ended:
            found["result"], found["result_line"] = ended.group(1), line
            continue
        said = EXIT.match(line) or REFUSAL.match(line)
        if said:
            found["exit" if said.re is EXIT else "refusal"] = said.group(1)
            continue
        row = ROW_LINE.match(line)
        if row and row.group(1) in planned:
            found["rows"][row.group(1)] = (row_state(row.group(2)), row.group(2), about)
    return found


def started_since(node, logs_dir, since):
    """Whether a row's own log was written at or after `since` (epoch seconds): it started in this run."""
    path = pathlib.Path(logs_dir) / f"{node}.log"
    return path.is_file() and path.stat().st_mtime >= since


def scene_state(scene, live):
    """failed, done, working, waiting (while the batch lives) or left (it ended before the scene was done)."""
    if scene["failed"]:
        return "failed"
    if scene["done"] == scene["total"]:
        return "done"
    if not live:
        return "left"
    return "working" if scene["running"] else "waiting"


def row_states(planned, rows, accepted_at, since):
    """{node: done, failed or not_run} of the planned rows that have one: done when its standing accept is from
    `since` (the checkout's time) on, made by this run or an earlier run of the checkout (an older accept is the
    stale output the batch makes again), else this run's line's state."""
    found = {node: rows[node][0] for node in planned if node in rows}
    found.update((node, "done") for node in planned if (parsed(accepted_at(node)) or since) > since)
    return found


def scenes_of(planned, states, running, live):
    """[{place, total, done, failed, not_run, running, state}] a scene of the planned rows ("" the environment's own
    rows), in the order first planned; `states` row_states; `live` while the batch lives."""
    found = {}
    for node in planned:
        scene = found.setdefault(place_of(node), {"place": place_of(node), "total": 0, "done": 0, "failed": 0,
                                                  "not_run": 0, "running": []})
        scene["total"] += 1
        if node in states:
            scene[states[node]] += 1
        elif node in running:
            scene["running"].append(groups.label(stage_of(node)))
    for scene in found.values():
        scene["running"] = sorted(set(scene["running"]))
        scene["state"] = scene_state(scene, live)
    return list(found.values())


def counted(states, total, beat):
    """{total, done, failed, not_run, running, queued}: the finished rows counted from row_states, the running
    and queued from the last heartbeat (None before one)."""
    states = list(states.values())
    return {"total": total, "done": states.count("done"), "failed": states.count("failed"),
            "not_run": states.count("not_run"), "running": beat["running"] if beat else None,
            "queued": beat["queued"] if beat else None}


def plain_machines(text):
    """A pool class in words: gpu-24gb a 24 GB graphics card, cpu-16c-64gb a 16-core processor machine."""
    def said(found):
        if found.group(1) == "gpu":
            return f"{found.group(5) + ' x ' if found.group(5) else ''}{found.group(2)} GB graphics card"
        return f"{found.group(2)}-core processor machine"
    return MACHINE_CLASS.sub(said, text)


def failures(rows):
    """[problem] a row that stopped its line: its step and scene in one plain sentence, the later rows it held
    back counted in it."""
    held = {}
    for _, did, _ in rows.values():
        if did.startswith("not run:"):
            stopper = did.rsplit(" ", 1)[-1]
            held[stopper] = held.get(stopper, 0) + 1
    found = []
    for node, (state, did, about) in rows.items():
        if state != "failed":
            continue
        why = plain_machines(FAULT.sub("", did).strip().removeprefix("blocked: "))
        sentence = plain.stop_sentence(groups.label(stage_of(node)), why, place_of(node), 0)
        if held.get(node):
            sentence += f" {held[node]} later step{'s' if held[node] != 1 else ''} wait on it."
        found.append({"at": about, "place": place_of(node), "node": node, "kind": "failed", "words": sentence,
                      "tip": why})
    return found


def gap_problems(rows, gaps_of):
    """[problem] each finished row whose output carries batch gaps (takes it left out): how many, their names as
    hover text."""
    found = []
    for node, (state, _, about) in rows.items():
        if state != "done":
            continue
        gaps = gaps_of(node)
        if gaps:
            label = groups.label(stage_of(node))
            found.append({"at": about, "place": place_of(node), "node": node, "kind": "gaps",
                          "words": f"{plain.capital(label)} left {len(gaps)} thing{'s' if len(gaps) != 1 else ''} "
                                   "out as gaps.",
                          "tip": "; ".join(gap.get("name", "") for gap in gaps)})
    return found


def newest_first(problems):
    return sorted(problems, key=lambda problem: problem["at"] or "", reverse=True)


def pool_of(run_id, pools_dir, now):
    """The warm pool a run opened: {run, open, until, cards, processors, stock} where cards and processors are
    {size, warm, busy, idle, short}; stock the collector's last word when it found none; None without one."""
    folder = pathlib.Path(pools_dir) / run_id if run_id else None
    plan_path = folder / "plan.json" if folder else None
    if not plan_path or not plan_path.is_file():
        return None
    plan = json.loads(plan_path.read_text())
    members = [json.loads(path.read_text()) for path in sorted((folder / "cards").glob("*.json"))]
    is_open = not (folder / "closed").exists() and now.timestamp() < plan["deadline"]
    kinds = {"cards": {"size": 0, "warm": 0, "busy": 0, "idle": 0, "short": 0},
             "processors": {"size": 0, "warm": 0, "busy": 0, "idle": 0, "short": 0}}
    for machine_class, size in plan["sizes"].items():
        kind = kinds["cards" if machine_class.startswith(CARD_PREFIX) else "processors"]
        mine = [card for card in members if (card.get("for") or card.get("class")) == machine_class]
        kind["size"] += size
        kind["warm"] += len(mine)
        kind["busy"] += sum(1 for card in mine if card.get("holder"))
        kind["short"] += max(0, size - len(mine)) if is_open else 0
    for kind in kinds.values():
        kind["idle"] = kind["warm"] - kind["busy"]
    said = [line for line in log_lines(folder / "collector.log") if line.strip()]
    stock = is_open and bool(said) and bool(NO_STOCK.search(said[-1]))
    until = datetime.datetime.fromtimestamp(plan["deadline"], datetime.timezone.utc)
    return {"run": run_id, "open": is_open, "until": stamp(until), **kinds, "stock": stock}


def failed_run(found):
    """(state, why) of a run whose result line is `detached: failed`: finished when its drive ended with some lines
    stopped (its exit line), else stopped: a refusal before it drove, a crash or an exit with no drive's end."""
    if found["exit"].startswith(LINES_STOPPED):
        return "finished", "some scenes' lines stopped"
    if found["refusal"]:
        return "stopped", f"refused: {found['refusal']}"
    return "stopped", found["exit"] or "the run failed before it drove a line"


def overall(batch, found, alive, pool):
    """(state, why): the batch's one state from its checkout, its launch and its run's log (read_log)."""
    result = found["result"]
    if batch["state"] == "launching":
        return "starting", "the runner plans the batch"
    if batch["state"] in ("refused", "failed"):
        return "stopped", batch.get("detail") or batch["state"]
    if batch["state"] == "done" and not batch.get("launch"):
        return "finished", batch.get("detail") or "nothing to buy"
    if result == "ok":
        return "finished", "every scene's line done"
    if result == "failed":
        return failed_run(found)
    if result in ("stopped", "refused"):
        return "stopped", (batch.get("launch") or {}).get("result") or result
    if not alive:
        return "stopped", "the run ended without its result line"
    if pool and pool["open"] and not pool["cards"]["warm"] and pool["cards"]["short"]:
        return "waiting", "no graphics card is warm yet"
    return "running", ""


def ended_at(batch, result, log_path):
    """When the run ended: its log's last write once its result line is there, else None."""
    path = pathlib.Path(log_path) if log_path else None
    if result and path and path.is_file():
        return datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
    return None


def eta_of(totals, started, ended, now):
    """{likely_minutes, high_minutes, untimed, elapsed}: the checkout's runner times and the minutes gone."""
    elapsed = ((ended or now) - started).total_seconds() / 60 if started else None
    return {"likely_minutes": totals.get("likely_minutes"), "high_minutes": totals.get("high_minutes"),
            "untimed": len(totals.get("unmeasured") or []), "elapsed": elapsed}


def own_stop(stop_line):
    """This batch's room under the environment's stop line (flow.write_line: the spend so far, what was in flight
    and the batch's cleared high plus 10%): the line less the spend and the reservations it was written over, on the
    scale of this run's own spend; None for a line without them."""
    if stop_line.get("euros") is None or stop_line.get("spent") is None or stop_line.get("reserved") is None:
        return None
    return round(stop_line["euros"] - stop_line["spent"] - stop_line["reserved"], 2)


def money_of(totals, stop_line, beat):
    return {"spent": beat["spent"] if beat else None, "open": beat["open"] if beat else None,
            "likely": totals.get("likely_euros"),
            "high": pricing.cleared_high(totals) if totals.get("high_euros") is not None else None,
            "guessed": totals.get("guessed_euros"), "stop": own_stop(stop_line), "line": stop_line.get("euros"),
            "closed": bool(stop_line.get("closed"))}


def gathered(batch, props_home, store_root, gaps_of=lambda node: [], now=None, accepted_at=lambda node: None):
    """The monitor's record of `batch` (checkout/watched.newest: the newest checkout, its launch and the rows its
    runs plan), read from the files under `props_home` (the warm pools) and `store_root` (the rows' logs), a row
    done when `accepted_at(node)`, the time of its standing accept in the store, is after the checkout; None
    without a batch."""
    if batch is None:
        return None
    now = now or now_utc()
    props_home = pathlib.Path(props_home)
    launch = batch.get("launch") or {}
    log_path = (launch.get("logs") or [None])[0]
    planned = list(batch.get("nodes") or [])
    found = read_log(log_lines(log_path), set(planned))
    started = parsed(launch.get("at") or batch["at"])
    pool = pool_of(found["pool"], props_home / "cloud" / "pools", now)
    state, why = overall(batch, found, launch.get("state") == "running", pool)
    states = row_states(planned, found["rows"], accepted_at, parsed(batch["at"]))
    running = {node for node in planned if node not in states and state in LIVE
               and started_since(node, pathlib.Path(store_root) / "logs", started.timestamp())}
    ended = ended_at(batch, found["result"], log_path)
    problems = failures(found["rows"]) + gap_problems(found["rows"], gaps_of)
    if state == "stopped":
        ran = eta_of({}, started, ended, now)["elapsed"] or 0
        problems.append({"at": stamp(ended or now), "place": "", "node": "", "kind": "run",
                         "words": f"The batch stopped after {round(ran)} min, before every scene was done.",
                         "tip": why})
    return {"read_at": stamp(now), "checkout": batch["checkout"], "at": batch["at"], "by": batch.get("by"),
            "state": state, "why": why, "started": stamp(started), "ended": stamp(ended),
            "rows": counted(states, len(planned), found["beat"]),
            "eta": eta_of(batch.get("totals") or {}, started, ended, now),
            "money": money_of(batch.get("totals") or {}, batch.get("stop_line") or {}, found["beat"]),
            "scenes": scenes_of(planned, states, running, state in LIVE), "pool": pool,
            "problems": newest_first(problems)}
