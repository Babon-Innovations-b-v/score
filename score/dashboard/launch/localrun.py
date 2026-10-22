"""The shipped compute backend: the `score` command line on this machine (plan, spend, price, run --detach), and
the billed lines of the ledgers SCORE_LEDGER_FILES names. It imports nothing from tools/ or score.adapters: every
answer comes from a subprocess or a file."""
import json
import os
import pathlib
import re
import subprocess
import sys

from django.conf import settings

from score.dashboard.launch.backend import Billed, GroupPlan, LaunchHandle, LaunchState, RunGroup
from score.dashboard.state import money
from score.dashboard.state.models import Spend

STARTED = re.compile(r"^detached: started pid=(\d+) log=(.+)$", re.MULTILINE)  # `score run --detach`'s own line
RESULT = re.compile(r"^detached: (ok|failed|stopped|refused)\b")
RESULT_STATES = {"ok": "done", "failed": "failed", "stopped": "stopped", "refused": "refused"}
SECRETS = ("SCORE_DASHBOARD_SECRET_KEY", "SCORE_SYNC_TOKEN")
# One run's own tags, never inherited by a launch: a benchmark grant would clear the owner's batch against the grant
# instead of his stop line, a machine cap would shrink it, a run id would fold it into another run's machine count.
RUN_TAGS = ("SCORE_BENCHMARK_GRANT", "SCORE_MAX_MACHINES", "SCORE_RUN_ID", "SCORE_RUN_PID")
TAIL_LINES = 40
BENCHMARKS = "score.stages.complete.prepare.benchmarks"  # the Benchmarks item's batch, a subprocess like `score`


def selection(group):
    """The --place and --stage words of a group."""
    words = []
    for place in group.places:
        words += ["--place", place]
    for stage in group.stages:
        words += ["--stage", stage]
    return words


def run_command(group, jobs, rebuy_reason):
    """The runner command that launches a group, detached: the benchmarks' own batch for the Benchmarks item."""
    if group.benchmarks:
        return [sys.executable, "-m", BENCHMARKS, "run", "--detach"]
    return [sys.executable, "-m", "score", "run", group.world, *selection(group), "--jobs", str(jobs), "--detach",
            *(["--rebuy-reason", rebuy_reason] if rebuy_reason else [])]


def plan_command(group):
    return [sys.executable, "-m", "score", "plan", group.world, *selection(group), "--json"]


def run_env():
    """The runner's environment: the dashboard's secrets and any run's own tags left out."""
    return {name: value for name, value in os.environ.items() if name not in SECRETS + RUN_TAGS}


def last_json(text):
    """The last line of a command's output that is a JSON object."""
    for line in reversed(text.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"no JSON in the command's output: {text[-400:]}")


def ticket_node(ticket):
    """The node a ledger ticket ("<node> <key>") names, or None."""
    return ticket.split()[0] if ticket else None


def ledger_rows(paths):
    """Every JSON row of the JSONL ledgers at `paths` that exist."""
    for path in paths:
        path = pathlib.Path(path)
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                yield json.loads(line)


def pid_alive(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def log_tail(path, lines=TAIL_LINES):
    path = pathlib.Path(path) if path else None
    if not path or not path.is_file():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])


class LocalBackend:
    name = "local score command"

    def __init__(self, run=subprocess.run):
        self.run = run

    def call(self, command):
        return self.run(command, cwd=settings.SCORE_REPO, env=run_env(), capture_output=True, text=True)

    def plan(self, group: RunGroup) -> GroupPlan:
        done = self.call(plan_command(group))
        if done.returncode != 0:
            raise RuntimeError(f"score plan failed: {(done.stderr or done.stdout)[-600:]}")
        found = last_json(done.stdout)
        return GroupPlan(missing=found["missing"], buys=found["buys"], refusal=found["refusal"],
                         to_run=found["to_run"], blocked=found.get("blocked", {}))

    def spend(self) -> Spend:
        done = self.call([sys.executable, "-m", "score", "spend", "--json"])
        if done.returncode != 0:
            return Spend(note=f"spend not read: {(done.stderr or done.stdout)[-300:]}")
        return money.with_bill_days(Spend.model_validate(last_json(done.stdout)), settings.SCORE_HOME)

    def launch(self, group: RunGroup, jobs: int, rebuy_reason: str | None) -> LaunchHandle:
        command = run_command(group, jobs, rebuy_reason)
        done = self.call(command)
        started = STARTED.search(done.stdout or "")
        if done.returncode != 0 or not started:
            return LaunchHandle(command=command, refused=((done.stdout or "") + (done.stderr or ""))[-2000:])
        return LaunchHandle(command=command, pid=int(started.group(1)), log=started.group(2))

    def poll(self, handle: LaunchHandle) -> LaunchState:
        if handle.refused is not None:
            return LaunchState("refused", handle.refused)
        text = log_tail(handle.log)
        last = text.splitlines()[-1] if text else ""
        ended = RESULT.match(last)
        if ended:
            return LaunchState(RESULT_STATES[ended.group(1)], last, text)
        if handle.pid and pid_alive(handle.pid):
            return LaunchState("running", "", text)
        return LaunchState("failed", "the run ended without its result line", text)

    def price(self, world, nodes):
        """{node: price} from `score price` (the runner's measured numbers, C19)."""
        asked = [word for node in nodes for word in ("--node", node)]
        command = [sys.executable, "-m", "score", "price", world, *asked, "--json"]
        done = self.call(command)
        if done.returncode != 0:
            raise RuntimeError(f"score price failed: {(done.stderr or done.stdout)[-600:]}")
        return last_json(done.stdout)["nodes"]

    def ledgered(self, nodes, since):
        """[Billed] of the ledger lines whose ticket names one of `nodes`, started at or after `since`."""
        wanted = set(nodes)
        return [Billed(node=ticket_node(row["ticket"]), euros=float(row.get("euros") or 0.0),
                       minutes=row.get("wall_minutes", row.get("minutes")), started=row.get("started", ""))
                for row in ledger_rows(settings.SCORE_LEDGER_FILES)
                if ticket_node(row.get("ticket")) in wanted and row.get("started", "") >= since]
