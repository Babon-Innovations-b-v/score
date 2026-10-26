"""The Buy's batch as it runs, for the run monitor (`/buy/run/`, pages/run_monitor.py): read on the store's machine from
the files the batch writes, read live locally and carried in the export as batch-run.json (sync/building.py).

    batch-run.json  {read_at, checkout, at, by, yes (his Buy approved in chat: {at, answer, question, high, stop};
                     None for his click), batch, tries, design_at, state, why, started, try_started, ended, rows,
                     eta, money, scenes, pool, nodes, problems}
      batch     the batch's number and `tries` how many checkouts tried it (checkout/watched.batch_of: a Buy while the
                batch before is unfinished and the design unchanged retries it); started the first try's, try_started
                this try's; design_at when the design last changed
      state     starting (the checkout plans it), running, waiting (running, the warm pool holds no card yet and
                stock is short), stopped (a stop, a refusal or a run gone without its result line), finished
      rows      {total, done, failed, not_run, running, queued}: total every row the checkout's runs planned, done
                those whose standing accept in the store is newer than the checkout (this run's or an earlier
                run's of the checkout, so a relaunch goes on where it was), failed and not_run from this run's own lines, running and queued the last
                heartbeat's
      eta       {likely_minutes, high_minutes} the checkout's runner times; untimed the bought steps with no
                measured price (the ETA is then at least); elapsed since the checkout's first run started (a relaunch
                goes on the batch's clock)
      money     {spent (the batch's, every try: the last heartbeat of each of its runs, each the euros its rows, its
                warm pool (every minute of its machines) and its model calls cost; None before any), try_spent
                (the same of this try's runs alone), open
                (paid runs open), likely, high (pricing.cleared_high: the high with the guessed steps, what the
                runner clears), guessed, stop (this batch's own room under the stop line the Buy wrote: the line
                less the spend and the reservations it was written over, on the same scale as spent; None for a
                line written without them), line (the stop line itself, the environment's), closed (taken back)}
      scenes    [{place ("" the whole environment), total, done, failed, not_run, running [step labels], state}]
      pool      the warm pool the run opened ({run, open, until, cards, processors, stock, renting}; None before one):
                renting the machines its pools (this run's and the checkout's earlier runs') hold parked now, which
                bill whether the pool is open or released
      nodes     {planned, made, failed} the rows by name (nodes_of)
      problems  [{at, place, node, kind (failed, gaps, run), words, tip}], newest first; a failed one's places
                and raw (each row's own fault text) too; an earlier try's failure of a row this try makes again
                (its try_nodes) is none: the row waits for this try, and while it lives `retried` counts those
                problems

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
BUFFER = 1.10  # a batch's stop: its high plus 10% (checkout/flow.BUFFER writes it)


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


def report_text(did):
    """The text of the fault report a row's line names, "" when it names none or it is gone."""
    named = FAULT.search(did)
    path = pathlib.Path(named.group(0).split("fault report ", 1)[1]) if named else None
    return path.read_text(errors="replace") if path and path.is_file() else ""


def held_back(rows):
    """{node: how many later rows its stop held back (their `not run:` lines name it)}."""
    held = {}
    for _, did, _ in rows.values():
        if did.startswith("not run:"):
            stopper = did.rsplit(" ", 1)[-1]
            held[stopper] = held.get(stopper, 0) + 1
    return held


def failures(rows):
    """[problem] the rows that stopped their lines, one per step and plain cause (plain.step_cause): the step, the
    scene or how many places share that cause, the later rows they held back; `raw` each row's own fault text."""
    held, found = held_back(rows), {}
    for node, (state, did, about) in rows.items():
        if state != "failed":
            continue
        why = plain_machines(FAULT.sub("", did).strip())
        label = groups.label(stage_of(node))
        group = found.setdefault((label, plain.step_cause(why, report_text(did))), [])
        group.append({"node": node, "place": place_of(node), "about": about, "why": why})
    return [failure_problem(label, cause, group, held) for (label, cause), group in found.items()]


def failure_problem(label, cause, group, held):
    """[problem] one step's stopped rows that share one plain cause, in one sentence."""
    places = sorted({row["place"] for row in group})
    where = f" in {len(places)} places" if len(places) > 1 else ""
    sentence = f"The {label} step stopped{where}: {cause}."
    waiting = sum(held.get(row["node"], 0) for row in group)
    if waiting:
        sentence += f" {waiting} later step{'s wait' if waiting != 1 else ' waits'} on {'them' if len(group) > 1 else 'it'}."
    return {"at": max((row["about"] or "" for row in group), default="") or None,
            "place": places[0] if len(places) == 1 else "", "places": places, "node": group[0]["node"],
            "kind": "failed", "words": sentence, "tip": group[0]["why"],
            "raw": [f"{row['node']}: {row['why']}" for row in group]}


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


def nodes_of(planned, states):
    """{planned, made, failed}: the batch's rows by name, for the next Buy to say what it makes again and keeps."""
    return {"planned": sorted(planned), "made": sorted(node for node in planned if states.get(node) == "done"),
            "failed": sorted(node for node in planned if states.get(node) == "failed")}


def steps(count):
    return f"{count} step{'s' if count != 1 else ''}"


def retries(run):
    """Whether the next Buy is another try of the batch `run` (watched.batch_of): some row of it not made and the
    design unchanged since its newest try."""
    rows = run["nodes"]
    unmade = set(rows["planned"]) - set(rows["made"])
    return bool(unmade) and not (run.get("design_at") and parsed(run["design_at"]) > parsed(run["at"]))


def next_buy(run, buying):
    """What a Buy of the nodes `buying` does beside the last batch (`run`, gathered's record) in one sentence: a retry
    of it (retries) or the next batch; the rows it makes again because they failed or never ran there, those it
    makes for the first time, the made ones it keeps and does not pay for again; None with no ended batch of named
    rows (an older record) or nothing to buy."""
    rows = (run or {}).get("nodes") or {}
    if not rows.get("planned") or run["state"] in LIVE or not buying:
        return None
    number, buying = run.get("batch") or run["checkout"], set(buying)
    planned, made, failed = set(rows["planned"]), set(rows["made"]), set(rows["failed"])
    unrun = planned - made - failed
    again = [f"the {steps(len(buying & failed))} that failed" if buying & failed else "",
             f"the {len(buying & unrun)} that never ran" if buying & unrun else "",
             f"the {len(buying & made)} made that changed since" if buying & made else ""]
    again = [part for part in again if part]
    said = [f"makes again {' and '.join(again)}" if again else "",
            f"makes {steps(len(buying - planned))} for the first time" if buying - planned else "",
            f"keeps the {len(made - buying)} already made" if made - buying else ""]
    head = f"Retry Batch {number}" if retries(run) else f"Batch {number + 1}, after Batch {number}"
    return f"{head}: " + "; ".join(part for part in said if part) + "."


def newest_first(problems):
    return sorted(problems, key=lambda problem: problem["at"] or "", reverse=True)


def parked_of(pools, parked_dir):
    """How many machines `pools` (run ids) hold parked now ($PROPS_HOME/cloud/parked/<id>.json, each naming its pool):
    each bills until it is deleted, whether its pool is open or released."""
    folder = pathlib.Path(parked_dir)
    records = [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))] if folder.is_dir() else []
    return sum(1 for record in records if record.get("pool") in pools)


def pool_of(run_id, pools_dir, now, renting=0):
    """The warm pool a run opened: {run, open, until, cards, processors, stock, renting} where cards and processors
    are {size, warm, busy, idle, short}; stock the collector's last word when it found none; renting the machines its
    pools hold parked now (parked_of); None without one."""
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
    return {"run": run_id, "open": is_open, "until": stamp(until), **kinds, "stock": stock, "renting": renting}


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


def spent_before(runs, newest_logs, planned):
    """What the checkout's earlier runs spent (`runs`, checkout/watched.checkout_runs, less the newest launch's
    `newest_logs`): the last heartbeat's euros of each; None when none has one."""
    found = [read_log(log_lines(path), planned)["beat"] for run in runs if run["logs"] != newest_logs
             for path in run["logs"]]
    spent = [beat["spent"] for beat in found if beat and beat["spent"] is not None]
    return round(sum(spent), 2) if spent else None


def checkout_spent(before, beat):
    """The checkout's spend: its earlier runs' (`before`) and this run's last heartbeat's; None when neither has one."""
    now = beat["spent"] if beat and beat["spent"] is not None else None
    if before is None and now is None:
        return None
    return round((before or 0.0) + (now or 0.0), 2)


def pools_of(runs, newest_pool, planned):
    """Every warm pool the checkout's runs opened (run ids), the newest run's among them."""
    found = {read_log(log_lines(path), planned)["pool"] for run in runs for path in run["logs"]}
    return {pool for pool in found | {newest_pool} if pool}


def money_of(totals, stop_line, beat, spent, launching=False, budget=None, try_spent=None):
    """The batch's money: what every try spent and what this try alone spent (`try_spent`), this try's likely, high
    and stop (its own room under the stop line; while it launches and has written no line yet, the stop its Buy
    writes: its high plus BUFFER), the batch's one budget across its tries (flow.batch_budget, None before a try
    wrote one) and what is left of it."""
    high = pricing.cleared_high(totals) if totals.get("high_euros") is not None else None
    stop = own_stop(stop_line)
    if stop is None and launching and high is not None:
        stop = round(high * BUFFER, 2)
    return {"spent": spent, "try_spent": try_spent, "open": beat["open"] if beat else None,
            "likely": totals.get("likely_euros"), "high": high,
            "guessed": totals.get("guessed_euros"), "stop": stop, "line": stop_line.get("euros"),
            "closed": bool(stop_line.get("closed")), "budget": budget,
            "left": None if budget is None or spent is None else round(budget - spent, 2)}


def tried_rows(runs, newest_rows, planned):
    """{node: (state, did, about)} of `runs`, oldest first, a later line of a row over an earlier one and the newest
    run's (`newest_rows`) last."""
    found = {}
    for run in runs:
        for path in run["logs"]:
            found.update(read_log(log_lines(path), planned)["rows"])
    return {**found, **newest_rows}


def gathered(batch, props_home, store_root, gaps_of=lambda node: [], now=None, accepted_at=lambda node: None,
             design_at=None):
    """The monitor's record of `batch` (checkout/watched.newest: the newest checkout, a try of its batch, its launch
    and the rows every try's runs plan), read from the files under `props_home` (the warm pools) and `store_root`
    (the rows' logs), a row done when `accepted_at(node)`, the time of its standing accept in the store, is after the
    batch's first try: rows, spend and problems across its tries, a problem gone once a later try made its row or makes it again, the
    ETA and stop this try's; `design_at` when the design last changed (the next Buy is a new batch past it); None
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
    runs = batch.get("runs") or []
    tried = batch.get("try_runs", runs) or []
    first = parsed(runs[0]["at"]) if runs else started  # the batch's clock: its first try's first run
    this_try = parsed(tried[0]["at"]) if tried else started  # this try's clock: its ETA
    renting = parked_of(pools_of(runs, found["pool"], set(planned)), props_home / "cloud" / "parked")
    pool = pool_of(found["pool"], props_home / "cloud" / "pools", now, renting)
    state, why = overall(batch, found, launch.get("state") == "running", pool)
    # an earlier try's line of a row this try makes again is no longer its state (owner, 2026-10-25: "it still
    # shows all failed"); one this try does not make again still shows
    redo = set(batch.get("try_nodes") or planned)
    earlier = tried_rows([run for run in runs if run not in tried], {}, set(planned))
    current = tried_rows(tried, found["rows"], set(planned))
    rows = {**{node: row for node, row in earlier.items() if node not in redo}, **current}
    states = row_states(planned, rows, accepted_at, parsed(batch.get("first_at") or batch["at"]))
    running = {node for node in planned if node not in states and state in LIVE
               and started_since(node, pathlib.Path(store_root) / "logs", started.timestamp())}
    ended = ended_at(batch, found["result"], log_path)
    standing = {node: row for node, row in rows.items() if states.get(node) != "done"}
    problems = failures(standing) + gap_problems(found["rows"], gaps_of)
    redone = {node: row for node, row in earlier.items() if node in redo and node not in current}
    retried = len(failures(redone)) if state in LIVE else 0
    if state == "stopped":
        ran = eta_of({}, this_try, ended, now)["elapsed"] or 0
        tries = batch.get("tries") or 1
        who = f"Try {tries}" if tries > 1 else "The batch"
        problems.append({"at": stamp(ended or now), "place": "", "node": "", "kind": "run",
                         "words": f"{who} stopped after {round(ran)} min, before every scene was done.",
                         "tip": why})
    spent = checkout_spent(spent_before(runs, launch.get("logs") or [], set(planned)), found["beat"])
    try_spent = checkout_spent(spent_before(tried, launch.get("logs") or [], set(planned)), found["beat"])
    return {"read_at": stamp(now), "checkout": batch["checkout"], "at": batch["at"], "by": batch.get("by"),
            "yes": batch.get("yes"),
            "batch": batch.get("batch") or batch["checkout"], "tries": batch.get("tries") or 1,
            "design_at": design_at, "state": state, "why": why, "started": stamp(first),
            "try_started": stamp(this_try), "ended": stamp(ended),
            "rows": counted(states, len(planned), found["beat"]),
            "eta": eta_of(batch.get("totals") or {}, this_try, ended, now),
            "money": money_of(batch.get("totals") or {}, batch.get("stop_line") or {}, found["beat"],
                              0.0 if spent is None and state in LIVE else spent, batch["state"] == "launching",
                              batch.get("budget"), try_spent),
            "scenes": scenes_of(planned, states, running, state in LIVE), "pool": pool,
            "problems": newest_first(problems), "retried": retried, "nodes": nodes_of(planned, states)}
