"""The shipped compute backend: the `score` command line on this machine (plan, spend, run --detach), and the
measured runs of the ledgers SCORE_LEDGER_FILES names. It imports nothing from tools/ or score.adapters: every
answer comes from a subprocess or a file."""
import json
import os
import pathlib
import re
import subprocess
import sys

from django.conf import settings

from score.dashboard.launch.backend import GroupPlan, LaunchHandle, LaunchState, MeasuredRun, RunGroup
from score.dashboard.state.models import Spend

STARTED = re.compile(r"detached: started pid=(\d+) log=(\S+)")
RESULT = re.compile(r"^detached: (ok|failed|stopped)\b")
RESULT_STATES = {"ok": "done", "failed": "failed", "stopped": "stopped"}
SECRETS = ("SCORE_DASHBOARD_SECRET_KEY", "SCORE_SYNC_TOKEN")
TAIL_LINES = 40


def selection(group):
    """The --place and --stage words of a group."""
    words = []
    for place in group.places:
        words += ["--place", place]
    for stage in group.stages:
        words += ["--stage", stage]
    return words


def run_command(group, jobs, rebuy_reason):
    """The runner command that launches a group, detached."""
    return [sys.executable, "-m", "score", "run", group.world, *selection(group), "--jobs", str(jobs), "--detach",
            *(["--rebuy-reason", rebuy_reason] if rebuy_reason else [])]


def plan_command(group):
    return [sys.executable, "-m", "score", "plan", group.world, *selection(group), "--json"]


def run_env():
    """The runner's environment: the dashboard's secrets left out, the month's stop passed on."""
    env = {name: value for name, value in os.environ.items() if name not in SECRETS}
    if settings.SCORE_MONTH_EUROS:
        env["SCORE_MONTH_EUROS"] = settings.SCORE_MONTH_EUROS
    return env


def last_json(text):
    """The last line of a command's output that is a JSON object."""
    for line in reversed(text.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise ValueError(f"no JSON in the command's output: {text[-400:]}")


def ticket_stage(ticket):
    """The stage a ledger ticket ("<stage>@<place> <key>" or "<stage> <key>") names, or None."""
    if not ticket:
        return None
    return ticket.split()[0].split("@")[0]


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
        found = last_json(done.stdout)
        return Spend(spent=found["spent"], reserved=found["reserved"], ceiling=found["ceiling"], as_of=found["as_of"])

    def measured(self):
        for row in ledger_rows(settings.SCORE_LEDGER_FILES):
            stage = ticket_stage(row.get("ticket"))
            if stage is None or row.get("euros") is None:
                continue
            yield MeasuredRun(stage=stage, euros=float(row["euros"]),
                              minutes=row.get("wall_minutes", row.get("minutes")))

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
