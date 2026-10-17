"""SCORE's one command: the runner drives an environment's lines to their end, with no agent in the loop.

    .venv/bin/python -m score run <environment> [--place P ...] [--stage S ...] [--jobs N] [--detach] [--rebuy-reason R]
    .venv/bin/python -m score status [<environment>] [--place P ...] [--stage S ...]                   # every line's state
    .venv/bin/python -m score images publish <kind>   # an accepted image proof's record into images.json
    .venv/bin/python -m score plan <environment> [--place P ...] [--stage S ...] [--rebuy-reason R] [--jobs N] --json
    .venv/bin/python -m score spend --json            # this month's spend, open reservations and the ceiling
    .venv/bin/python -m score price <environment> --node N [--node N ...] --json   # each paid node's likely and high price
    .venv/bin/python -m score moved [--pre-push]      # the paid rows this tree would buy again, every environment

`status --json` prints the same lines as one JSON object. `plan` works out what `run` would do with the same arguments,
running nothing: the missing inputs, the nodes it would make and why, the paid rows it would buy with their estimates
and the re-buy refusal (the dashboard's launch basket reads it, score/dashboard); each buy's `price` and the run's
(`price`: likely and high euros and minutes) are `price`'s numbers, so the basket and the clearance read the same.
`spend` reads the month's spend as the runner's clearance counts it. `price` gives each paid node its likely and high euros and minutes and the cards
its run is sized on, from the stage's measured runs in the cloud ledger (the numbers its clearance reserves), else
its estimate (the cockpit prices a fix branch's moved paid rows with it).

`run` drives the lines side by side (with --place, those places' lines and only the whole-environment nodes they read), each node in
a process of its own and at most --jobs at once (default score.graph.JOBS; --jobs 1 runs one node at a time); with
--stage, only those stages and the ones they read (a line's other rows, a paid surface row say, are left alone). It starts
each node the moment the nodes it reads stand accepted, gathers a gate's missing evidence itself (a paid step cleared by
the runner, waited on by the runner), and stops a line whose node fails, errors or is blocked, with a plain fault report
(faults/<node>.txt beside the store) to point an agent or the owner at; the other lines go on. It exits 1 when any line
stopped. --detach returns at once with the log's path: the run goes on in a session of its own
(tools/props/cloud/detached.py), its progress in that log and, when every line is done or stopped, one result line
(`detached: ok|failed exit=N minutes=M log=... outputs=<faults folder>`) as the log's last line; a run stopped by
SIGTERM, SIGINT or SIGHUP says `score run: stopped by signal N`, then `detached: stopped by signal N exit=128+N ...`.
Wait for that line with the Monitor tool, never a poll loop.

A run and everything it starts end together (2026-10-17: orphaned cloud machines and boxes billed by the started hour
after runs were stopped): `run` names itself SCORE_RUN_ID (every node, batch and cloud tool it starts inherits it; their
machines count against one cap for the whole run, tools/props/cloud/capacity.py) and leads a process group of its own.
Stopped by SIGTERM, SIGINT or SIGHUP, it sends SIGTERM to that whole group (each batch deletes its machines through its
own delete path), waits STOP_GRACE_SECONDS, sends SIGKILL to whatever is left, then releases the run's spend
reservations. A node process whose runner is gone sends the group SIGTERM itself (score.graph).

Before it starts, `run` lists every paid row it would buy with its estimate (score/graph/rebuy.py; a Google ask its
cache answers at EUR 0) and refuses, before detaching, when buying again rows that already have an accepted output
would cost over EUR 5, unless given --rebuy-reason, which goes into the run's log and the cloud ledger.

`moved` lists, read-only, every paid row with an accepted output this working tree would buy again over every
environment's places, each with its price and why, and the total (score/stages/moved.py); it exits 3 above EUR 0. With --pre-push
(.githooks/pre-push-moved, the push lines on stdin, run in a checkout of the commit pushed to main) it refuses the paid
rows that commit would buy again and main's commit would not, unless a pushed commit's "Moved-rows: <node> ...:
<reason>" trailer names each; rows main already buys again print as a warning, and when main's commit cannot be
worked out every moved row counts as the push's. The hook runs only once the owner sets
`git config score.movedCheck true`.
"""
import argparse
import datetime
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.graph import rebuy, stopped  # noqa: E402
from score.stages import moved  # noqa: E402
from score.store import Store  # noqa: E402

DETACH = "--detach"
RUN_ID = "SCORE_RUN_ID"
RUN_PID = "SCORE_RUN_PID"
# How long a stopped run's process group has to end after SIGTERM before what is left gets SIGKILL.
STOP_GRACE_SECONDS = 30


ENVIRONMENT_HELP = ("the environment's id, one of %(choices)s (stored ids keep the old word: world1 is environment 1)")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("world", metavar="environment", choices=sorted(stages.WORLDS), help=ENVIRONMENT_HELP)
    run.add_argument(DETACH, action="store_true", help="progress to a log, one result line at the end")
    run.add_argument("--jobs", type=int, default=graph.JOBS, help="nodes at once (default %(default)s)")
    run.add_argument("--rebuy-reason", help="why outputs already standing are bought again (needed over EUR 5)")
    status = commands.add_parser("status")
    status.add_argument("world", metavar="environment", nargs="?", default="world1", choices=sorted(stages.WORLDS),
                        help=ENVIRONMENT_HELP)
    status.add_argument("--json", action="store_true", help="the lines as one JSON object")
    plan = commands.add_parser("plan")
    plan.add_argument("world", metavar="environment", choices=sorted(stages.WORLDS), help=ENVIRONMENT_HELP)
    plan.add_argument("--rebuy-reason", help="the reason a run would be given")
    plan.add_argument("--jobs", type=int, default=graph.JOBS, help="nodes at once, as for run (default %(default)s)")
    plan.add_argument("--json", action="store_true", help="the plan as one JSON object (the only form)")
    spend = commands.add_parser("spend")
    spend.add_argument("--json", action="store_true", help="the month's spend as one JSON object (the only form)")
    spend.add_argument("--world", default="world1", metavar="ENVIRONMENT",
                       help="the environment whose stop line and spend since it are read (its id, world1)")
    price = commands.add_parser("price")
    price.add_argument("world", metavar="environment", choices=sorted(stages.WORLDS), help=ENVIRONMENT_HELP)
    price.add_argument("--node", action="append", required=True, help="a paid node (repeat it)")
    price.add_argument("--json", action="store_true", help="the prices as one JSON object (the only form)")
    images = commands.add_parser("images").add_subparsers(dest="images_command", required=True)
    images.add_parser("publish").add_argument("kind", choices=stages.images.proved_kinds())
    commands.add_parser("moved").add_argument("--pre-push", action="store_true",
                                              help="git's push lines on stdin: refuse the paid rows a push moves")
    for command in (run, status, plan):
        command.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
        command.add_argument("--stage", action="append", help="only this stage and what it reads (repeat it)")
    return parser.parse_args(argv)


def detach(argv):
    """Start this command (argv, less --detach) again in a session of its own under detached.py, its output and then
    its result line into a fresh log (graph/stopped.py: on a stopping signal too); print the log's path and return
    at once."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    log = detached.log_path_for("score-run")
    command = [sys.executable, stopped.__file__, "--log", str(log), "--outputs",
               str(Store.default().cache.parent / "faults"), "--", sys.executable,
               *[word for word in argv if word != DETACH]]
    with open(log, "a") as result:  # detached.py prints its result line here, after the run's own output
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=result, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    print(f"detached: started pid={process.pid} log={log}", flush=True)


def publish(kind):
    """Write the kind's accepted image proof into images.json; refused unless it passed and stands accepted."""
    try:
        record = stages.images.publish(stages.runner(world=stages.images.image_world()), kind)
    except graph.Blocked as block:
        sys.exit(f"not published: {block}")
    print(f"{kind}: {record['image']} into {stages.images.IMAGES_JSON}")


def buy_check(runner, places, whole, only, reason):
    """What a run of these lines would do before it starts, running nothing: {"missing": inputs it could never make
    itself, "buys": [Buy] in table order (none when inputs are missing: free checks before paid), "refusal": why the
    run is refused or None, "to_run": {node: why} of every node it would make, "blocked": {node: why} of every node
    it could not start}."""
    nodes = runner.line_nodes(places, whole, only)
    missing = runner.missing_inputs(nodes)
    if missing:
        return {"missing": missing, "buys": [], "to_run": {}, "blocked": {},
                "refusal": "refused: these inputs are missing, so the rows that read them would stop the run after it "
                           "paid for others:\n  " + "\n  ".join(missing)}
    with runner.still():
        bought = rebuy.buys(runner, nodes)
        states = {node: state for _, line_nodes in runner.lines(places, whole, only).values()
                  for node, state in line_nodes.items()}
    return {"missing": [], "buys": bought, "refusal": rebuy.refusal(bought, reason),
            "to_run": {node: state for node, state in states.items() if state.startswith("to run")},
            "blocked": {node: state for node, state in states.items() if state.startswith("blocked")}}


def become_run():
    """Make this process a run: the leader of a process group of its own (a shell with job control already made it
    one), its id in SCORE_RUN_ID and its pid in SCORE_RUN_PID for every process it starts; the run id."""
    if os.getpgrp() != os.getpid():
        os.setpgid(0, 0)
    os.environ[RUN_PID] = str(os.getpid())
    os.environ[RUN_ID] = f"{socket.gethostname()}-{os.getpid()}-{int(time.time())}"
    return os.environ[RUN_ID]


def group_members(group):
    """The live processes of a process group other than this one (zombies left out), read from /proc."""
    members = []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            fields = (entry / "stat").read_text().rpartition(")")[2].split()
        except OSError:  # gone while being read
            continue
        if fields[0] != "Z" and int(fields[2]) == group:
            members.append(int(entry.name))
    return members


def end_group(grace=STOP_GRACE_SECONDS):
    """SIGTERM to every other process of this run's group, then SIGKILL to those still there after `grace` seconds;
    the pids that needed SIGKILL. Only a group this process leads is signalled."""
    group = os.getpgrp()
    if group != os.getpid():
        return []
    for member in group_members(group):
        signal_quietly(member, signal.SIGTERM)
    deadline = time.time() + grace
    while group_members(group) and time.time() < deadline:
        time.sleep(0.2)
    left = group_members(group)
    for member in left:
        signal_quietly(member, signal.SIGKILL)
    return left


def signal_quietly(pid, number):
    """Send a signal to a process that may have ended meanwhile."""
    try:
        os.kill(pid, number)
    except ProcessLookupError:
        pass


def release_run(runner, run_id):
    """End the spend reservations this run's nodes held (a node ended by a signal never released its own) and its
    machine counts for the run-wide cap."""
    from score.adapters import compute
    compute.release_run(runner.store.cache.parent / "reservations.json", run_id)
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import capacity
    capacity.forget_run(run_id)


def stop_run(runner, run_id, number):
    """A stopping signal's end of a run: say so, end its process group, release what it held."""
    print(f"score run: stopped by signal {number}", flush=True)
    killed = end_group()
    if killed:
        print(f"score run: SIGKILL to {len(killed)} processes still there after {STOP_GRACE_SECONDS} s", flush=True)
    release_run(runner, run_id)


def checked_buys(runner, places, whole, options):
    """Print the paid rows the run would buy; exit when its re-buys pass the limit with no reason. The run itself (not
    the call that detaches it) writes a given reason to the cloud ledger. A run missing an input it could never make
    itself (Runner.missing_inputs) is refused first, each file named: free checks before paid."""
    missing = runner.missing_inputs(runner.line_nodes(places, whole, options.stage))
    if missing:
        sys.exit("refused: these inputs are missing, so the rows that read them would stop the run after it paid for "
                 "others:\n  " + "\n  ".join(missing))
    bought = rebuy.buys(runner, runner.line_nodes(places, whole, options.stage))
    print(rebuy.listing(bought), flush=True)
    refused = rebuy.refusal(bought, options.rebuy_reason)
    if refused:
        sys.exit(refused)
    if options.rebuy_reason and any(buy.again for buy in bought):
        print(f"re-buy reason: {options.rebuy_reason}", flush=True)
        if not options.detach:
            from score.adapters import compute
            compute.ledger().record(rebuy.ledger_entry(bought, options.rebuy_reason))


def plan_json(runner, places, whole, options):
    """The plan of a run (buy_check) as one JSON object: each buy as {node, euros (its estimate), why, again, price
    (buy_price)}, and the run's price over them (plan_price), the only euros and minutes the cockpit shows."""
    found = buy_check(runner, places, whole, options.stage, options.rebuy_reason)
    found["buys"] = [{"node": buy.node, "euros": buy.euros, "why": buy.why, "again": buy.again,
                      "price": buy_price(buy, counting_store(runner.store))} for buy in found["buys"]]
    return {"world": runner.world.name, "places": places, "stages": options.stage or [], **found,
            "price": plan_price([buy["price"] for buy in found["buys"]], options.jobs)}


def counting_store(store):
    """`store` read with its keys walked in a node's own folder (the library check's NodeFolders), so counting a
    node's units reads its accepts, not every blob of the store (a whole walk took 8 s a node)."""
    from score.stages.complete.library import stored
    from score.store import Store, runtime_store
    if isinstance(store.objects, runtime_store.FolderStore):
        return Store(stored.NodeFolders(store.objects.root), store.cache)
    return store


def buy_price(buy, store):
    """One buy's price on the runner's own numbers (compute.run_price: its stage's measured runs, the numbers its
    clearance reserves, else its measured units on `store`, else not measured yet with its estimate as a guess), or
    nothing for a Google ask its cache answers (rebuy prices it EUR 0)."""
    from score.adapters import compute
    if buy.euros == 0:
        return {"likely_euros": 0.0, "high_euros": 0.0, "likely_minutes": 0.0, "high_minutes": 0.0, "cards": None,
                "runs": 0, "basis": "cached"}
    return compute.run_price(buy.node, buy.euros, store)


def plan_price(prices, jobs):
    """The run's price over its buys' prices: {likely_euros, high_euros} the sums of the measured ones; {guessed_euros,
    guessed} the not-measured rows' estimates and their count, kept apart (a guess is never a price);
    {likely_minutes, high_minutes} the paid rows' time with `jobs` of them at once (the longest row, or their minutes
    over `jobs` when that is longer), None while any row's time is unmeasured; `measured` the rows priced from measured runs of `rows`. High
    is the sum of the rows' highs, so it reads high; the time leaves out the free rows and the waits between rows."""
    def wall(key):
        minutes = [price[key] for price in prices]
        if any(each is None for each in minutes):
            return None
        return round(max([*minutes, sum(minutes) / max(1, jobs)], default=0.0), 1)

    def priced(key):
        return round(sum(price[key] for price in prices if price[key] is not None), 2)
    guessed = [price for price in prices if price["likely_euros"] is None]
    return {"likely_euros": priced("likely_euros"), "high_euros": priced("high_euros"),
            "guessed_euros": round(sum(price["guess_euros"] for price in guessed), 2), "guessed": len(guessed),
            "likely_minutes": wall("likely_minutes"), "high_minutes": wall("high_minutes"),
            "measured": sum(1 for price in prices if price["runs"]), "rows": len(prices), "jobs": jobs}


def spend_json(world):
    """The money as the cockpit shows it: the world's spend since its first stop line against that line, and this
    month's cost by source, each saying where its number comes from and when it was read."""
    from score.adapters import compute
    reservations = Store.default().cache.parent / "reservations.json"
    held = compute.open_reservations(reservations)
    books = compute.books_now()
    read_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {**world_spend(world, held, books), "month": books["month"], "as_of": read_at,
            "lines": cost_lines(books, read_at),
            "credit_note": f"the Scaleway account's EUR {compute.ledger().MONTH_EUROS:.0f} monthly credit is shared with "
                           "Movalytics; it is not SCORE's budget"}


def world_spend(world, held, books):
    """{spent, reserved, ceiling, world, stop_at, note}: the world's spend since its first stop line, what its cleared
    runs still have in flight, and its newest line; all None with a note when it has no line."""
    from score.adapters import compute
    from score.adapters.compute import guard
    store = Store.default()
    line = guard.current(store, world)
    if line is None:
        return {"spent": None, "reserved": None, "ceiling": None, "world": world, "stop_at": None,
                "note": f"{world}: no stop set, paid launches refused (python -m score.review stop {world} <euros> "
                        f"--reason ...)"}
    spent = guard.spent_since(line["baseline"], compute.months_since(line["baseline"], books))
    flight = guard.in_flight({**compute.open_overrides(store), **held}, compute.ledger().entries())
    return {"spent": round(spent, 2), "reserved": round(sum(flight.values()), 2), "ceiling": line["euros"],
            "world": world, "stop_at": line["at"], "note": ""}


def cost_lines(books, read_at):
    """This month's measured cost lines: the cloud bill of SCORE's own project, and the Google call ledger, which
    misses calls and so is partial (the owner enters the Google bill's figure on the cockpit)."""
    return [{"source": "cloud", "label": "Cloud compute", "euros": round(books["bill"], 2), "partial": False,
             "origin": "Scaleway's bill of the SCORE project (farm-factory) only, never Movalytics; lags by hours",
             "read_at": read_at},
            {"source": "models", "label": "Google AI", "euros": round(books["google"], 2), "partial": True,
             "origin": "SCORE's own Google call ledger, which misses calls: the Google bill is higher",
             "read_at": read_at}]


def price_json(world, nodes):
    """{world, nodes: {node: price}}: each paid node at compute.run_price (its units counted on the framework store's
    accepted outputs, its stage's estimate as the guess); a node that is not a paid row of the stage table says so
    instead."""
    from score.adapters import compute
    from score.store import Store
    rows, store = {row.name: row for row in stages.STAGES}, counting_store(Store.default())
    found = {}
    for node in nodes:
        row = rows.get(node.partition("@")[0])
        found[node] = (compute.run_price(node, float(row.euros or 0), store) if row is not None and row.paid
                       else {"error": f"{node} is not a paid row of the stage table"})
    return {"world": world, "nodes": found}


def status_json(world, lines):
    """The lines of `status` as one JSON object: {world, made_at, lines: {line: {state, nodes: {node: state}}}}."""
    return {"world": world, "made_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "lines": {line: {"state": state, "nodes": nodes} for line, (state, nodes) in lines.items()}}


def every_world_moved():
    """{world: [rebuy.Buy]} of every world's re-buys against the framework store."""
    found = {}
    for name, make in sorted(stages.WORLDS.items()):
        runner = stages.runner(world=make())
        found[name] = moved.rebuys(runner, runner.line_nodes(stages.places(runner.world), True))
    return found


def moved_check(rows_by_world):
    """Print the moved rows; exit moved.MOVED_EXIT above EUR 0."""
    print(moved.listing(rows_by_world), flush=True)
    if moved.total(rows_by_world) > 0:
        sys.exit(moved.MOVED_EXIT)


def pre_push_check(push_lines):
    """The pre-push hook's check of the commit pushed to main (none passes at once): every world's re-buys in this
    checkout, which must be that commit, against those of main's commit (pushed_check)."""
    pushes = moved.main_pushes(push_lines)
    if not pushes:
        print("moved check: nothing pushed to main, not checked", flush=True)
        return
    tip, remote = pushes[-1]
    if not moved.tree_is_at(tip):
        sys.exit(f"refused: the moved check must run in a clean checkout of {tip} (.githooks/pre-push-moved makes one)")
    print(f"moved check: working out which paid rows {tip[:12]} and main's {remote[:12]} would buy again, every world "
          f"(a few minutes each)...", flush=True)
    pushed_check(every_world_moved(), moved.base_rebuys(remote), moved.pushed_reasons(pushes))


def pushed_check(rows_by_world, base, reasons):
    """Warn of the rows main's commit buys again too (`base`, {world: [node]}, None when not worked out); refuse
    (exit moved.MOVED_EXIT) when the push moves a paid row that no Moved-rows trailer names."""
    pushed, drift = moved.split(rows_by_world, base)
    if base is None:
        print("moved check: main's commit could not be worked out, so every moved row counts as this push's",
              flush=True)
    if any(drift.values()):
        print("warning, not refused: " + moved.listing(drift, "paid rows main already buys again"), flush=True)
    print(moved.listing(pushed, "paid rows this push would make the next run buy again"), flush=True)
    refused = moved.unexplained(pushed, reasons)
    if not any(refused.values()):
        if reasons:
            print(f"{moved.TRAILER}: " + "; ".join(reasons), flush=True)
        return
    names = " ".join(row.node for rows in refused.values() for row in rows)
    print(f"refused: this push moves paid rows no '{moved.TRAILER}:' trailer names. If they should be bought again, "
          f"add to a pushed commit: '{moved.TRAILER}: {names}: <why>'. A row priced EUR 0 (a Google ask its cache "
          f"answers) is listed, never refused.", file=sys.stderr, flush=True)
    sys.exit(moved.MOVED_EXIT)


def stop_on_term(signal_number, frame):
    """End with SystemExit on SIGTERM (the hook's timeout), so the `finally` blocks run: subprocess.run ends the child
    it waits on and moved.snapshot removes its checkout and folder."""
    sys.exit(f"stopped by signal {signal_number}")


def main(argv=None):
    options = parse(argv)
    if options.command == "images":
        publish(options.kind)
        return
    if options.command == "spend":
        print(json.dumps(spend_json(options.world)))
        return
    if options.command == "price":
        print(json.dumps(price_json(options.world, options.node)))
        return
    if options.command == "moved":
        signal.signal(signal.SIGTERM, stop_on_term)
        if options.pre_push:
            pre_push_check(sys.stdin.read().splitlines())
        else:
            moved_check(every_world_moved())
        return
    runner = stages.runner(world=stages.WORLDS[options.world]())
    places, whole = options.place or stages.places(runner.world), not options.place
    if options.command == "plan":
        print(json.dumps(plan_json(runner, places, whole, options)))
        return
    if options.command == "run":
        checked_buys(runner, places, whole, options)
    if getattr(options, "detach", False):
        detach(sys.argv)
        return
    if options.command == "run":
        run_id = become_run()
        stopped.stop_on_signals(lambda number: stop_run(runner, run_id, number))
        runner.drive(places, say=lambda line: print(line, flush=True), jobs=options.jobs, whole=whole,
                     only=options.stage)
        release_run(runner, run_id)
    lines = runner.lines(places, whole, options.stage)
    if getattr(options, "json", False):
        print(json.dumps(status_json(options.world, lines)))
        return
    for line, (state, nodes) in lines.items():
        print(f"{line}: {state}")
        if options.command == "status":
            print("\n".join(f"  {node}: {node_state}" for node, node_state in nodes.items()))
    if options.command == "status" and whole and stages.library.WORLD_ROW in runner.stages:
        print(stages.library.completion_line(runner.world.name,
                                             stages.library.world_completion(runner, places)))
    if options.command == "run" and any(state != "done" for state, _ in lines.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
