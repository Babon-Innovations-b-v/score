"""SCORE's one command: the runner drives an environment's lines to their end, with no agent in the loop.

    .venv/bin/python -m score run <environment> [--place P ...] [--stage S ...] [--jobs N] [--detach] [--rebuy-reason R]
        [--uncommitted] [--oversubscribe]
    .venv/bin/python -m score status [<environment>] [--place P ...] [--stage S ...]                   # every line's state
    .venv/bin/python -m score images publish <kind>   # an accepted image proof's record into images.json
    .venv/bin/python -m score plan <environment> [--place P ...] [--stage S ...] [--rebuy-reason R] [--jobs N] --json
    .venv/bin/python -m score spend --json            # this month's spend, open reservations and the ceiling
    .venv/bin/python -m score spend --read-back       # the month's Scaleway and Google bills read back into the books (#13)
    .venv/bin/python -m score spend --google-month EUR   # the owner's own: Google's month before its ledger began again
    .venv/bin/python -m score price <environment> --node N [--node N ...] --json   # each paid node's likely and high price
    .venv/bin/python -m score moved [--pre-push]      # the paid rows this tree would buy again, every environment
    .venv/bin/python -m score resume [--dry]          # start again the runs a reboot cut off (score/graph/runs.py)

`status --json` prints the same lines as one JSON object. `plan` works out what `run` would do with the same arguments,
running nothing: the missing inputs, the nodes it would make and why, the paid rows it would buy with their estimates
and the re-buy refusal (the dashboard's launch basket reads it, score/dashboard); each buy's `price` and the run's
(`price`: likely and high euros and minutes) are `price`'s numbers, so the basket and the clearance read the same.
`spend` reads the month's spend as the runner's clearance counts it, and its `paid_refused` says why paid work is
refused while the month's books are unknown (tools/props/cloud/ledger.py books_refusal; both ledgers were lost on
2026-10-19): `--read-back` writes the Scaleway bill and Google's (its billing export, SCORE_GOOGLE_BILLING_TABLE)
into the books, `known` once Google's was read, and the owner's `--google-month` (refused in an agent's process)
overrides the Google figure and makes them `known`. `price` gives each paid node its likely and high euros and minutes and the cards
its run is sized on, from the stage's measured runs in the cloud ledger (the numbers its clearance reserves), else
its estimate (the cockpit prices a fix branch's moved paid rows with it).

`run` drives the lines side by side (with --place, those places' lines and only the whole-environment nodes they read), each node in
a process of its own and at most --jobs at once (default score.graph.JOBS; --jobs 1 runs one node at a time), each
node's thread pools and its children's capped at this PC's cores shared out among the jobs (OMP_NUM_THREADS and the
others in score.graph.THREAD_VARIABLES, and the OpenBLAS pools already loaded), so a lone node at the default --jobs
still gets only its share (--jobs 1 gives it every core); more jobs than cores is refused unless given --oversubscribe;
with --stage, only those stages and the ones they read (a line's other rows, a paid surface row say, are left alone). It
starts
each node the moment the nodes it reads stand accepted, gathers a gate's missing evidence itself (a paid step cleared by
the runner, waited on by the runner), and stops a line whose node fails, errors or is blocked, with a plain fault report
(faults/<node>.txt beside the store) to point an agent or the owner at; the other lines go on. It exits 1 when any line
stopped. Every score.graph.HEARTBEAT seconds it prints a heartbeat line (rows done, running and queued, then this run's
rows' paid runs open and the euros the ledger holds for them since it started), and it always ends with one `exit:
<status>` line, after the lines' closing states and on an error or a stopping signal too: `exit: ok, ...` only when
every line is done, else `exit: stopped, N of M lines done, ...` (exit code 1), `exit: error: ...` or `exit: stopped by
signal N, exit 128+N`. --detach returns at once with the log's path: the run goes on in a session of its own
(tools/props/cloud/detached.py), its progress in that log and, when every line is done or stopped, one result line
(`detached: ok|failed exit=N minutes=M log=... outputs=<faults folder>`) as the log's last line; a run stopped by
SIGTERM, SIGINT or SIGHUP says `score run: stopped by signal N`, then `detached: stopped by signal N exit=128+N ...`.
Wait for that line with the Monitor tool, never a poll loop. Its log is under $PROPS_HOME/logs, not /tmp, so it
outlives a reboot. Every run that drives is registered in $PROPS_HOME/runs (score/graph/runs.py), and `resume` starts
again, from its own worktree, each one an earlier boot cut off; a run the owner stopped (Ctrl-C, a kill while the
machine is up, a closed session) is marked stopped and never started again.

A run and everything it starts end together (2026-10-17: orphaned cloud machines and boxes billed by the started hour
after runs were stopped): `run` names itself SCORE_RUN_ID (every node, batch and cloud tool it starts inherits it; their
machines count against one cap for the whole run, tools/props/cloud/capacity.py) and leads a process group of its own
(a later stage of a shell pipeline takes the terminal along, so Ctrl-C still reaches it, and gives it back when the run
ends). Stopped by SIGTERM, SIGINT or SIGHUP, it passes the stop on to that whole group unless the signal already reached
it (Ctrl-C, a closed terminal, `kill -- -<pgid>`: a batch stops deleting at its second signal): stopped.PASS_ON to its
nodes, each sending SIGTERM to its own children unless the group's stop reached it first, SIGTERM to the rest, so each
batch deletes its machines through its own delete path once. After STOP_GRACE_SECONDS it sends SIGKILL to what is left
except the cloud tools and the nodes they write to, whose deletes and parks may take minutes. However the run ends it
releases its spend reservations, once those cloud tools have ended. A node process whose runner is gone sends the
group SIGTERM itself, once for the whole group (score.graph).

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

One commit per store (score/graph/runs.py): `run` refuses while a live run from another commit holds the store (naming
it, its commit and its worktree), or one at the same commit would make some of the same nodes (one not standing
accepted: environment nodes already made do not count, so one run per place goes side by side), and refuses a
worktree with tracked changes not committed that would buy a paid row unless given --uncommitted. A detached run
registers itself: a run registering between its check and that is refused, `detached: refused: ...` its result line.
"""
import argparse
import atexit
import datetime
import json
import os
import pathlib
import signal
import socket
import subprocess
import sys
import time
import traceback

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.graph import _code, rebuy, runs, stopped  # noqa: E402
from score.stages import moved  # noqa: E402
from score.store import Store  # noqa: E402

DETACH = "--detach"
RUN_ID = "SCORE_RUN_ID"
RUN_PID = "SCORE_RUN_PID"
# How long a stopped run's process group has to end after SIGTERM before what is left gets SIGKILL, cloud tools and
# the nodes they write to spared (cloud_side).
STOP_GRACE_SECONDS = 30
# How long a stopped run looks for a node showing the same stop (the signal went to the whole group: Ctrl-C, a closed
# terminal, `kill -- -<pgid>`) before it sends the group SIGTERM itself.
GROUP_STOP_SECONDS = 1
# A process running anything from here is a cloud tool: it deletes its machines on its own stop path, which may take
# minutes (park.park's remote clean-up, one machine after another), and is never sent SIGKILL by a stopped run.
CLOUD_TOOLS = REPO / "tools/props/cloud"
# The cloud tools and the nodes they write to that a stopped run left to end on their own (stop_run): the run's
# release waits for them (release_once_ended), checking every RELEASE_POLL_SECONDS.
STILL_ENDING = []
RELEASE_POLL_SECONDS = 1


ENVIRONMENT_HELP = ("the environment's id, one of %(choices)s (stored ids keep the old word: world1 is environment 1)")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("world", metavar="environment", choices=sorted(stages.WORLDS), help=ENVIRONMENT_HELP)
    run.add_argument(DETACH, action="store_true", help="progress to a log, one result line at the end")
    run.add_argument("--jobs", type=jobs_count, default=graph.JOBS, help="nodes at once (default %(default)s)")
    run.add_argument("--oversubscribe", action="store_true", help="allow more jobs than this PC has cores")
    run.add_argument("--rebuy-reason", help="why outputs already standing are bought again (needed over EUR 5)")
    run.add_argument("--uncommitted", action="store_true", help="run this worktree's changes not committed")
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
    spend.add_argument("--read-back", action="store_true",
                       help="read the month's Scaleway and Google bills back into the books (read-only)")
    spend.add_argument("--google-month", type=float, metavar="EUR",
                       help="the owner's figure: what Google billed this month before its ledger began again")
    price = commands.add_parser("price")
    price.add_argument("world", metavar="environment", choices=sorted(stages.WORLDS), help=ENVIRONMENT_HELP)
    price.add_argument("--node", action="append", help="a paid node (repeat it)")
    price.add_argument("--holes", action="store_true",
                       help="every hole's chain priced, written to WORK/checks/holes-price/<environment>.json")
    price.add_argument("--json", action="store_true", help="the prices as one JSON object (the only form)")
    images = commands.add_parser("images").add_subparsers(dest="images_command", required=True)
    images.add_parser("publish").add_argument("kind", choices=stages.images.proved_kinds())
    commands.add_parser("moved").add_argument("--pre-push", action="store_true",
                                              help="git's push lines on stdin: refuse the paid rows a push moves")
    commands.add_parser("resume").add_argument("--dry", action="store_true", help="only list the runs it would start")
    for command in (run, status, plan):
        command.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
        command.add_argument("--stage", action="append", help="only this stage and what it reads (repeat it)")
        command.add_argument("--object", action="append",
                             help="only this object of a place, in the stages that select (repeat it)")
    return parser.parse_args(argv)


def jobs_count(text):
    """--jobs as a whole number of at least 1; argparse refuses anything else plainly."""
    jobs = int(text)
    if jobs < 1:
        raise argparse.ArgumentTypeError(f"{text}: at least 1")
    return jobs


def detach(argv):
    """Start this command (argv, less --detach) again in a session of its own under detached.py, its output and then
    its result line into a fresh log (graph/stopped.py: on a stopping signal too); print the log's path and return
    at once."""
    log = runs.log_path("score-run")
    command = [sys.executable, stopped.__file__, "--log", str(log), "--outputs",
               str(Store.default().cache.parent / "faults"), "--", sys.executable,
               *[word for word in argv if word != DETACH]]
    with open(log, "a") as result:  # detached.py prints its result line here, after the run's own output
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=result, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    print(f"detached: started pid={process.pid} (it registers on the store itself and may still be refused: its "
          f"result line says) log={log}", flush=True)


def publish(kind):
    """Write the kind's accepted image proof into images.json; refused unless it passed and stands accepted."""
    try:
        record = stages.images.publish(stages.runner(world=stages.images.image_world()), kind)
    except graph.Blocked as block:
        sys.exit(f"not published: {block}")
    print(f"{kind}: {record['image']} into {stages.images.IMAGES_JSON}")


def buy_check(runner, places, whole, only, reason):
    """What a run of these lines would do before it starts, running nothing: {"missing": inputs it could never make
    itself, "buys": [Buy] in table order (listed when inputs are missing too, so the cockpit's basket shows what a run
    would buy; that run is refused: free checks before paid), "refusal": why the run is refused or None, "to_run":
    {node: why} of every node it would make, "blocked": {node: why} of every node it could not start}."""
    nodes = runner.line_nodes(places, whole, only)
    missing = runner.missing_inputs(nodes)
    with runner.still():
        bought = rebuy.buys(runner, nodes)
        states = {} if missing else {node: state for _, line_nodes in runner.lines(places, whole, only).values()
                                     for node, state in line_nodes.items()}
    if missing:
        return {"missing": missing, "buys": bought, "to_run": {}, "blocked": {},
                "refusal": "refused: these inputs are missing, so the rows that read them would stop the run after it "
                           "paid for others:\n  " + "\n  ".join(missing)}
    return {"missing": [], "buys": bought, "refusal": rebuy.refusal(bought, reason),
            "to_run": {node: state for node, state in states.items() if state.startswith("to run")},
            "blocked": {node: state for node, state in states.items() if state.startswith("blocked")}}


def become_run():
    """Make this process a run: the leader of a process group of its own (a shell with job control already made it
    one), its id in SCORE_RUN_ID and its pid in SCORE_RUN_PID for every process it starts. The group that held the
    terminal before it took it over (lead_group), None when it took none."""
    held_before = lead_group() if os.getpgrp() != os.getpid() else None
    os.environ[RUN_PID] = str(os.getpid())
    os.environ[RUN_ID] = f"{socket.gethostname()}-{os.getpid()}-{int(time.time())}"
    return held_before


def lead_group():
    """Lead a process group of its own. A later stage of a shell pipeline (`... | score run`) was in the pipeline's
    group, the one holding the terminal: its new group takes the terminal over, so Ctrl-C still reaches the run. The
    group that held the terminal before, None when it took none."""
    terminal = controlling_terminal()
    held_before = os.getpgrp() if terminal is not None and os.tcgetpgrp(terminal) == os.getpgrp() else None
    os.setpgid(0, 0)
    if held_before is not None:
        hand_terminal(terminal, os.getpgrp())
    if terminal is not None:
        os.close(terminal)
    return held_before


def give_terminal_back(held_before):
    """Hand the terminal back to the group that held it before the run took it (lead_group), so a script that started
    the run without job control reads from it again and gets Ctrl-C; nothing when the run took none, or the terminal
    is no longer the run's."""
    terminal = controlling_terminal() if held_before is not None else None
    if terminal is None:
        return
    try:
        if os.tcgetpgrp(terminal) == os.getpgrp():
            hand_terminal(terminal, held_before)
    except PermissionError:  # that group has ended meanwhile: no one is left to give it back to
        pass
    finally:
        os.close(terminal)


def controlling_terminal():
    """A descriptor of this process's controlling terminal; None when it has none (a detached run, a test)."""
    try:
        return os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        return None


def hand_terminal(terminal, group):
    """Make `group` the terminal's foreground group (SIGTTOU, sent to a background group asking this, ignored
    meanwhile)."""
    before = signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    try:
        os.tcsetpgrp(terminal, group)
    finally:
        signal.signal(signal.SIGTTOU, before)


def group_parents(group):
    """Each live process of a process group other than this one (zombies left out) with its parent's pid, read from
    /proc."""
    members = {}
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            fields = (entry / "stat").read_text().rpartition(")")[2].split()
        except OSError:  # gone while being read
            continue
        if fields[0] != "Z" and int(fields[2]) == group:
            members[int(entry.name)] = int(fields[1])
    return members


def group_members(group):
    """The live processes of a process group other than this one."""
    return list(group_parents(group))


def stop_shown(group, wait=None):
    """Whether one of this run's node processes (its children in `group`) shows a stop within `wait` seconds
    (GROUP_STOP_SECONDS): the stopping signal went to the whole group."""
    deadline = time.time() + (GROUP_STOP_SECONDS if wait is None else wait)
    while True:
        nodes = [member for member, parent in group_parents(group).items() if parent == os.getpid()]
        if any(map(stopped.shows_stop, nodes)):
            return True
        if time.time() >= deadline:
            return False
        time.sleep(0.05)


def cloud_side(group):
    """The processes of `group` running a cloud tool (CLOUD_TOOLS), with every process of the group above one (a node
    holding its output's pipe)."""
    parents = group_parents(group)
    spared = set()
    for member in parents:
        if runs_cloud_tool(member):
            while member in parents and member not in spared:
                spared.add(member)
                member = parents[member]
    return spared


def runs_cloud_tool(pid):
    """Whether a process's command line names a file or folder under CLOUD_TOOLS; False when it is gone."""
    try:
        words = pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return False
    return any(word.startswith(str(CLOUD_TOOLS)) for word in words)


def end_group():
    """End the other processes of the run's group: pass the stop on (pass_stop_on), unless the stopping signal already
    reached them (stop_shown) or a node's watch sent it (one stop at most: a batch stops deleting at its second
    signal), then, after STOP_GRACE_SECONDS, SIGKILL to those left but the cloud side (cloud_side). The pids sent
    SIGKILL and those spared. Only a group this process leads is signalled."""
    group = os.getpgrp()
    if group != os.getpid():
        return [], []
    if not stop_shown(group) and stopped.claim_stop(stopped.stop_mark(os.getpid())):
        pass_stop_on(group)
    deadline = time.time() + STOP_GRACE_SECONDS
    while group_members(group) and time.time() < deadline:
        time.sleep(0.2)
    spared = cloud_side(group)
    left = [member for member in group_members(group) if member not in spared]
    for member in left:
        signal_quietly(member, signal.SIGKILL)
    return left, sorted(spared)


def pass_stop_on(group):
    """The run's own stop to the rest of its group, one signal for each process: stopped.PASS_ON to each of its nodes
    (forked processes holding its handler), which sends SIGTERM to its own children unless the whole group already had
    a stop its main thread had not handled yet; SIGTERM to every other process not started under a node (one the run
    started itself, one whose node is gone)."""
    parents = group_parents(group)
    nodes = {member for member, parent in parents.items() if parent == os.getpid() and stopped.catches_pass_on(member)}
    for member in parents:
        if member in nodes:
            signal_quietly(member, stopped.PASS_ON)
        elif not under_node(member, nodes, parents):
            signal_quietly(member, signal.SIGTERM)


def under_node(member, nodes, parents):
    """Whether a process of the group descends from one of `nodes`, following `parents` within the group."""
    while member in parents:
        member = parents[member]
        if member in nodes:
            return True
    return False


def signal_quietly(pid, number):
    """Send a signal to a process that may have ended meanwhile."""
    try:
        os.kill(pid, number)
    except ProcessLookupError:
        pass


def release_run(runner, run_id, mark):
    """End the spend reservations this run's nodes held (a node ended by a signal never released its own), its
    machine counts for the run-wide cap and its stop mark (`mark`)."""
    from score.adapters import compute
    compute.release_run(compute.covering_store(runner.store).cache.parent / "reservations.json", run_id)
    sys.path.insert(0, str(CLOUD_TOOLS))
    import capacity
    capacity.forget_run(run_id)
    mark.unlink(missing_ok=True)


def release_once_ended(runner, run_id, mark):
    """release_run now, or, when a stop left cloud tools still deleting and parking (STILL_ENDING), from a process of
    its own once they have all ended: their machines bill until then, and a release before them freed the run's
    reservations and machine counts early (review of C7, 2026-10-17)."""
    ending = [pid for pid in STILL_ENDING if alive(pid)]
    if not ending:
        release_run(runner, run_id, mark)
        return
    if os.fork() == 0:
        os.setsid()  # outside the run's group and session: what ends those does not end this
        code = 1
        try:
            while any(map(alive, ending)):
                time.sleep(RELEASE_POLL_SECONDS)
            release_run(runner, run_id, mark)
            code = 0
        except Exception:  # noqa: BLE001 - said on the run's error output; this process has no caller to raise to
            traceback.print_exc()
        finally:
            os._exit(code)


def alive(pid):
    """Whether a process is there and not a zombie."""
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"
    except OSError:
        return False


def stop_run(number):
    """A stopping signal's end of a run: say so and end its process group (end_group)."""
    print(f"score run: stopped by signal {number}", flush=True)
    killed, spared = end_group()
    if killed:
        print(f"score run: SIGKILL to {len(killed)} processes still there after {STOP_GRACE_SECONDS} s", flush=True)
    if spared:
        print(f"score run: {len(spared)} processes of cloud tools and the nodes they write to still ending their "
              f"machines after {STOP_GRACE_SECONDS} s, left to end on their own; the run's reservations are released "
              "once they have", flush=True)
    STILL_ENDING[:] = spared


def as_run(runner, drive):
    """Call `drive()` as a run (become_run; a stopping signal ends its group, stop_run); however the drive ends
    (returned, raised or stopped) the terminal goes back to the group that held it and what the run held is released
    (release_once_ended)."""
    held_before = become_run()
    run_id, mark = os.environ[RUN_ID], stopped.stop_mark(os.getpid())
    stopped.stop_on_signals(stop_run)
    try:
        drive()
    finally:
        give_terminal_back(held_before)
        release_once_ended(runner, run_id, mark)


def checked_thread_variables():
    """Exit when a thread variable the owner set is not a thread count: every node would stop on it."""
    try:
        graph.owner_thread_counts()
    except ValueError as error:
        sys.exit(f"refused: {error}")


def checked_threads(options):
    """Exit when the run's jobs times their threads would pass this PC's core count and --oversubscribe was not
    given."""
    refused = graph.oversubscribed(options.jobs)
    if refused and not options.oversubscribe:
        sys.exit(f"refused: {refused}")


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


def spend_command(options):
    """`spend`: the books read back, or the owner's Google month written, when asked; else the month's spend as JSON."""
    from score.adapters import compute
    if options.read_back:
        print(json.dumps(compute.read_back_books()))
    elif options.google_month is not None:
        try:
            print(json.dumps(compute.owners_google_month(options.google_month)))
        except compute.Refused as refused:
            sys.exit(f"refused: {refused}")
    else:
        print(json.dumps(spend_json(options.world)))


def spend_json(world):
    """The money as the cockpit shows it: the world's spend since its first stop line against that line, and this
    month's cost by source, each saying where its number comes from and when it was read."""
    from score.adapters import compute
    reservations = Store.default().cache.parent / "reservations.json"
    held = compute.open_reservations(reservations)
    books = compute.books_now()
    read_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {**world_spend(world, held, books), "month": books["month"], "as_of": read_at,
            "lines": cost_lines(books, read_at), "paid_refused": compute.ledger().books_refusal(),
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
        found[node] = (compute.run_price(node, float(row.euros or 0), store, guess_from=row.euros_from)
                       if row is not None and row.paid
                       else {"error": f"{node} is not a paid row of the stage table"})
    return {"world": world, "nodes": found}


HOLES_PRICE = "work/checks/holes-price"  # under PROPS_HOME: the holes' prices the cockpit reads, one file a world


def holes_record(world):
    """Every place's holes priced through their chains (score/stages/complete/holes/price.py) on the framework store."""
    from score.stages.complete.holes import OUT, price
    from score.store import Store
    runner = stages.runner(world=stages.WORLDS[world]())
    return price.holes_price(runner, world, OUT, stages.places(runner.world), counting_store(Store.default()))


def holes_price(world):
    """The holes' prices (holes_record) written whole to WORK/checks/holes-price/<world>.json for the cockpit, said
    in one line: {written, totals, after_work, code_work, eta (its minutes and how many rows are untimed), nodes,
    holes, unfillable, outside, not_current, not_checked}."""
    from score.dashboard.proposals.records import swapped_json
    from score.stages.complete.holes import price
    from score.store import PROPS_HOME
    record = holes_record(world)
    out = PROPS_HOME / HOLES_PRICE / f"{world}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    swapped_json(out, record)
    after = {node: found for entry in record["after_work"].values() for node, found in entry["nodes"].items()}
    coded = {label: found for entry in record["code_work"].values() for label, found in entry["nodes"].items()}
    return {"written": str(out), "totals": record["totals"], "after_work": price.totals(after),
            "code_work": price.totals(coded), "eta": {name: value for name, value in record["eta"].items()
                                                      if name not in ("path", "high_path", "unknown")}
            | {"unknown": len(record["eta"]["unknown"])},
            "nodes": len(record["nodes"]), "holes": sum(len(found) for found in record["holes"].values()),
            "unfillable": sum(entry["holes"] for entry in record["unfillable"]),
            "outside": sum(entry["holes"] for entry in record["outside"]), "not_current": record["not_current"],
            "not_checked": record["not_checked"]}


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


def run_gauges(runner, places, whole, only, started):
    """The run's gauges for its heartbeat lines, read from files alone (no cloud call) and scoped to this run's rows:
    their paid runs cleared and still open (each holds a rented machine or is about to), and the euros the cloud ledger
    holds for batches this checkout ran for them since `started` (a row's batch carries its spend ticket, `<node>
    <key>`)."""
    from score.adapters import compute
    nodes = {graph.node_name(*node) for node in runner.line_nodes(places, whole, only)}

    def gauges():
        books = compute.ledger()
        here = books.origin()["worktree"]
        euros = sum(batch["euros"] for batch in books.entries() if batch.get("worktree") == here
                    and (batch.get("ticket") or "").partition(" ")[0] in nodes and batch["started"] >= started)
        held = compute.open_reservations(compute.covering_store(runner.store).cache.parent / "reservations.json")
        mine = [at for at, cleared in held.items() if cleared.get("node") in nodes]
        return f"this run's rows: paid runs open {len(mine)}, EUR {euros:.2f} in the ledger since the run started"
    return gauges


def closing_lines(runner, places, whole, options):
    """Each line's state printed (with each node's under `status`); {line: (its state, {node: state})}."""
    lines = runner.lines(places, whole, options.stage)
    for line, (state, nodes) in lines.items():
        print(f"{line}: {state}")
        if options.command == "status":
            print("\n".join(f"  {node}: {node_state}" for node, node_state in nodes.items()))
    return lines


def exit_status(found, lines):
    """A finished run's exit status: ok only when every line is done (main exits 0 then), else stopped; with how many
    rows ran and how many were not run because their line stopped."""
    done = sum(state == "done" for state, _ in lines.values())
    not_run = sum(did.startswith("not run:") for did in found.values())
    rows = f"{len(found) - not_run} rows ran" + (f", {not_run} not run" if not_run else "")
    if done == len(lines):
        return f"ok, {done} of {len(lines)} lines done, {rows}"
    return f"stopped, {done} of {len(lines)} lines done, {len(lines) - done} stopped, {rows}"


def raised_status(error):
    """A run's exit status from what it raised: a signal's stop (exit code 128 + its number) named as such."""
    if isinstance(error, SystemExit):
        code = error.code if isinstance(error.code, int) else 1
        return f"stopped by signal {code - 128}, exit {code}" if code > 128 else f"exited, exit {code}"
    return f"error: {type(error).__name__}: {error}"


def run_with_exit_line(runner, places, whole, options, argv):
    """Drive the lines as a run (as_run) registered in the run registry (driven), then print their closing states,
    then one `exit: <status>` line, the run's last, said in every case: when it ends, raises, or is stopped by a
    signal (stopped.stop_on_signals raises SystemExit); the lines."""
    status = "ended without a status"
    try:
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # the ledger's own time format
        found = {}
        as_run(runner, lambda: found.update(driven(runner, places, whole, options, argv,
                                                   gauges=run_gauges(runner, places, whole, options.stage, started))))
        lines = closing_lines(runner, places, whole, options)
        status = exit_status(found, lines)
        return lines
    except BaseException as error:  # noqa: BLE001 - said, then raised again as it was
        status = raised_status(error)
        raise
    finally:
        print(f"exit: {status}", flush=True)


def driven(runner, places, whole, options, argv, gauges=None):
    """Drive the lines, registered in the run registry while they run (graph/runs.py): `ended` once the drive returns,
    `crashed` when the runner raises, `stopped` by a stopping signal unless it is a shutdown's SIGTERM (runs.stopped_by:
    then it stays `running`, for `score resume` after the reboot); what the drive did. The stopping signals are handled
    before it is called (as_run), so a stop as the entry is written leaves it stopped, never running."""
    entry = runs.new_entry(argv)
    path = runs.entry_path(entry)
    try:
        with runs.beating(runs.written(path, entry)):
            found = runner.drive(places, say=lambda line: print(line, flush=True), jobs=options.jobs, whole=whole,
                                 only=options.stage, gauges=gauges)
    except Exception:
        if path.exists():
            runs.mark(path, runs.CRASHED)
        raise
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 0
        if code > 128 and path.exists():  # stopped.stop_on_signals exits 128 + the signal's number
            runs.stopped_by(path, code - 128)
        raise
    runs.mark(path, runs.ENDED)
    return found


def run_commit(runner, nodes, options):
    """The commit this run registers as; exit when the worktree has tracked changes not committed, the run would buy
    a paid row and no --uncommitted is given."""
    dirty = runs.tracked_changes()
    refused = runs.dirty_refusal(dirty, options.uncommitted, dirty and bool(rebuy.buys(runner, nodes)))
    if refused:
        sys.exit(refused)
    return runs.identity(_code.git_commit()["commit"], dirty, REPO)


def claim(runner, places, whole, options):
    """Register this run on the store (graph/runs.py), released at exit; exit REFUSED (graph/stopped.py, so a
    detached run's result line is the refusal) when a live run of another commit, or one at this commit that would
    make some of the same nodes, holds it. Before detaching it only checks: the detached run registers itself, and a
    run that registers in between refuses it then."""
    nodes = runner.line_nodes(places, whole, options.stage)
    commit = run_commit(runner, nodes, options)
    making = runs.would_make(runner, nodes)
    if options.detach:
        refused = runs.claim_refusal(commit, making)
    else:
        refused = runs.claim(commit, making, os.getpid())
        atexit.register(runs.unclaim, os.getpid())
    if refused:
        print(refused, file=sys.stderr, flush=True)
        sys.exit(stopped.REFUSED)


def main(argv=None):
    options = parse(argv)
    if options.command == "images":
        publish(options.kind)
        return
    if options.command == "spend":
        spend_command(options)
        return
    if options.command == "price":
        if bool(options.holes) == bool(options.node):
            sys.exit("score price: give --node (repeat it) or --holes")
        print(json.dumps(holes_price(options.world) if options.holes else price_json(options.world, options.node)))
        return
    if options.command == "moved":
        signal.signal(signal.SIGTERM, stop_on_term)
        if options.pre_push:
            pre_push_check(sys.stdin.read().splitlines())
        else:
            moved_check(every_world_moved())
        return
    if options.command == "resume":
        runs.resume(options.dry, say=lambda line: print(line, flush=True))
        return
    runner = stages.runner(world=stages.WORLDS[options.world]())
    runner.objects = frozenset(options.object) if options.object else None
    places, whole = options.place or stages.places(runner.world), not options.place
    if options.command == "plan":
        print(json.dumps(plan_json(runner, places, whole, options)))
        return
    if options.command == "run":
        checked_thread_variables()
        checked_threads(options)
        claim(runner, places, whole, options)
        checked_buys(runner, places, whole, options)
    if getattr(options, "detach", False):
        detach(sys.argv)
        return
    if options.command == "status":
        if getattr(options, "json", False):
            print(json.dumps(status_json(options.world, runner.lines(places, whole, options.stage))))
            return
        closing_lines(runner, places, whole, options)
        if whole and stages.library.WORLD_ROW in runner.stages:
            print(stages.library.completion_line(runner.world.name,
                                                 stages.library.world_completion(runner, places)))
        for line in runs.unresumable():
            print(f"unresumable run {line}")
        return
    lines = run_with_exit_line(runner, places, whole, options, sys.argv[1:] if argv is None else argv)
    if any(state != "done" for state, _ in lines.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
