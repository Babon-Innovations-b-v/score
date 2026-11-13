"""The harness scripts change only what they own: gate-scope nothing (documents alone run no tests), board-status
only this repo's card, setup-github only this repo's labels, board and config (nothing on a dry run), worktree-reap only a dead session's clean merged worktree,
bootstrap only its own links and flags, ssh-agent.sh only its agent socket, its ~/.bashrc block and its
~/.ssh/config lines (GitHub's port 443 only when port 22 is refused), and sandbox-home and conftest.py keep every test off the real home while
removing everything a test leaves.

Every script is driven from outside as a copy in a scratch git repo (each finds its repo from its own path); `gh`
and `uv` are stand-ins that log their calls, and HOME is a scratch folder, so nothing runs against this machine. The expected answers are the scripts' rules, written out by hand here.

The break that turns each test red (applied once each, seen red, reverted):

- test_scripts_change_only_what_they_own, one row red per break: gate-scope's is_document's `BUILT_PREFIXES +
  CODE_PREFIXES` made `BUILT_PREFIXES` (a hook change runs nothing); or gate-scope's forced_reason's CI branch
  removed; or board-status's config()'s `here and repo and here != repo` made `False` (another repo's board); main's mutation sent with `o=options[0]["id"]` (moves the
  card); board_item's `node["project"]["number"] == number` made `True` (adds from another board); sync_labels
  creates a label even on a dry run; main keeps the template's backlog_prd (resets a template's config); "Review"
  taken out of STATUS_OPTIONS, or main's `config.get("owner") or owner` made `owner` (a re-run overwrites the
  hand-edited owner) (gives the board its columns).
- test_worktree_reap_reaps_only_a_dead_sessions_clean_merged_worktree: is_clean returns True at once; or reap's
  `idle_hours(...) >= IDLE_HOURS` made `True` (a recent unlocked worktree is reaped); or main prints the report also
  when empty (the idle hook speaks); or (an env1 run's code worktree was reaped mid-run and while paused, 2026-10-31)
  reap's `or entry.name in in_use` dropped, held_by_processes returns `set()` (only the cwd and locked_cwd worktrees
  go), or named_by_runs returns `set()` (only registered and paused go).
- test_a_sandbox_run_writes_only_its_own_empty_home_and_removes_all_it_leaves (owner's rule: tests use small
  fixtures, never the real store or home, 2026-10-28): sandbox-home's read_only_command drops `--ro-bind`; or run's
  `finally` drops `shutil.rmtree(temp, ...)`; or make_sandbox links the real home's work/ into the sandbox.
- test_no_test_starts_outside_a_sandbox_home (the owner's rule that no test touches the real home, 2026-10-18), one
  guard row red per break: outside_temp's `folder == temp` test dropped; or pytest_configure's refusal skipped; or
  own_temp's `removed` holds only `[folder]`; or refuse_outside_sandbox's `if refusal:` made `if False:`.
- test_bootstrap_touches_only_its_links_flags_runtime_and_ssh_lines: bootstrap moves the old memory folder aside
  without copying it; or its runtime build ignores PROPS_HOME; or
  ssh-agent.sh's `elif github_answers git@github.com` branch dropped (a box whose port 22 works gets the 443
  fallback); or its `grep -qF 'ssh/agent/agent.sock'` made `false` (a re-run writes the ~/.bashrc block twice); or
  use_repo_hooks' `config score.movedCheck true` dropped (the push gate's re-buy check stays off).

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest .claude/scripts/tests/
"""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent
REPO = SCRIPTS.parents[1]

# A stand-in for gh: answers from FAKE_GH_ANSWERS (keyed by its first two arguments, or "graphql query" / "graphql
# mutation") and appends every call to FAKE_GH_LOG as one JSON line.
FAKE_GH = """#!{python}
import json, os, sys
args = sys.argv[1:]
stdin = sys.stdin.read() if "--input" in args else ""
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps({{"args": args, "stdin": stdin}}) + "\\n")
answers = json.load(open(os.environ["FAKE_GH_ANSWERS"]))
key = " ".join(args[:2])
if key == "api graphql":
    key = "graphql mutation" if "mutation" in " ".join(args) + stdin else "graphql query"
answer = answers.get(key, {{}})
sys.stdout.write(answer.get("stdout", ""))
sys.exit(answer.get("exit", 0))
"""


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def write_tool(folder, name, body):
    """Write an executable stand-in tool and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(body)
    path.chmod(0o755)
    return path


def module(path, name):
    """A file of this repository loaded as a module."""
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def scratch_repo(tmp_path):
    """A git repo holding a committed copy of the scripts and a project.json for acme/widget."""
    repo = tmp_path / "repo"
    shutil.copytree(SCRIPTS, repo / ".claude" / "scripts", ignore=shutil.ignore_patterns("tests"))
    (repo / ".claude" / "settings.json").write_text('{"committed": true}\n')
    (repo / ".claude" / "project.json").write_text(json.dumps({"repo": "acme/widget"}) + "\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "remote", "add", "origin", "git@github.com:acme/widget.git")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "scripts")
    return repo


@pytest.fixture
def fake_gh(tmp_path):
    """Put the gh stand-in first on PATH; (env, set its answers, read its logged calls)."""
    answers = tmp_path / "gh-answers.json"
    log = tmp_path / "gh-log.jsonl"
    answers.write_text("{}")
    write_tool(tmp_path / "bin", "gh", FAKE_GH.format(python=sys.executable))
    env = dict(os.environ, PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
               FAKE_GH_ANSWERS=str(answers), FAKE_GH_LOG=str(log))

    def answer(by_key):
        answers.write_text(json.dumps(by_key))

    def calls():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    return env, answer, calls


def script(repo, env, name, *args):
    return subprocess.run(["python3", repo / ".claude" / "scripts" / name, *args], env=env, capture_output=True,
                          text=True)


# Every script run in the scratch repo against a stand-in gh. A gh call is a write unless it is one of these reads,
# so a write the rows do not expect, of any kind, turns its row red. gate-scope reads the change against origin/main
# and asks nothing of GitHub: documents alone run nothing; anything else, and every doubt, runs everything.

READS = (["auth", "status"], ["repo", "view"], ["label", "list"], ["project", "list"], ["project", "view"],
         ["project", "field-list"])
FIELDS = {"fields": [{"id": "F1", "name": "Status", "options": [
    {"id": "O1", "name": "Not started"}, {"id": "O2", "name": "Done"}]}]}
REPO_VIEW = {"stdout": json.dumps({"nameWithOwner": "acme/widget", "owner": {"login": "acme"}})}
BOARD = {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}}
# The board's columns and the labels the loop reads, written out by hand: the scripts' rules.
COLUMNS = [
    {"name": "LowPriority", "color": "GRAY",
     "description": "Real, not now. The standing backlog PRDs live here permanently."},
    {"name": "Not started", "color": "GRAY", "description": "Accepted, nobody has begun."},
    {"name": "In Progress", "color": "YELLOW", "description": "Someone is working on it right now."},
    {"name": "Review", "color": "ORANGE", "description": "Done by its author, waiting on a second pair of eyes."},
    {"name": "Done", "color": "GREEN", "description": "Acceptance list genuinely met."}]
LABELS_MADE = [["label", "create", name] for name in (
    "PRD", "vision", "bug", "enhancement", "needs-triage", "needs-info", "ready-for-agent", "ready-for-human",
    "wontfix")]


def on_board(project_number):
    return {"stdout": json.dumps({"data": {"repository": {"issue": {"id": "I1", "projectItems": {"nodes": [
        {"id": "ITEM", "project": {"id": "P1", "number": project_number}}]}}}}})}


def written(call):
    """A gh call as the change it makes: a mutation's variables, a label by its name, any other command whole."""
    args = call["args"]
    if args[:2] == ["api", "graphql"]:
        if call["stdin"]:
            return ["mutation", json.loads(call["stdin"])["variables"]]
        pairs = [args[at + 1] for at, arg in enumerate(args) if arg == "-F"]
        return ["mutation", dict(pair.split("=", 1) for pair in pairs)]
    return args[:3] if args[0] == "label" else args


def is_write(call):
    args = call["args"]
    if args[:2] == ["api", "graphql"]:
        return "mutation" in " ".join(args) + call["stdin"]
    return args[:2] not in READS


DOCUMENTS = {"CONTEXT.md", "docs/bible.md", "src/CLAUDE.md", ".claude/skills/grill/SKILL.md"}
NONE = "MODE none\nWHY only documents changed\n"


def one_code_file(path):
    return f"MODE full\nWHY 1 changed files are not documents, first {path}\n"


def gate(name, changed, command, environ, said):
    """A gate-scope row: the paths changed since origin/main (None: no origin/main), its environment, its answer."""
    return (name, None, changed, environ, {}, ["gate-scope.py", *command], True, said, False, [], None)


def github(name, before, *rest):
    """A board-status or setup-github row: run with nothing changed, no origin/main and no extra environment."""
    return (name, before, None, {}, *rest)


CASES = [  # (id, project.json before (None: acme/widget's), paths changed since origin/main (None: no origin/main),
    # extra environment, gh answers, script and arguments, succeeds, what it says (a str: the whole stdout; else
    # fragments of stdout, or of stderr when it fails), asks gh at all, the writes in order, project.json after (None:
    # unchanged))
    gate("gate-scope: documents", DOCUMENTS, [], {}, NONE),
    gate("gate-scope: documents and code", {"docs/bible.md", "src/app.py"}, [], {}, one_code_file("src/app.py")),
    # the paper's draft is a build input
    gate("gate-scope: paper draft", {"paper/score/source/score.md"}, [], {},
         one_code_file("paper/score/source/score.md")),
    gate("gate-scope: hook", {".claude/hooks/md_guard.py"}, [], {}, one_code_file(".claude/hooks/md_guard.py")),
    gate("gate-scope: itself", {".claude/scripts/gate-scope.py"}, [], {},
         one_code_file(".claude/scripts/gate-scope.py")),
    gate("gate-scope: settings", {".claude/settings.json"}, [], {}, one_code_file(".claude/settings.json")),
    gate("gate-scope: no origin", None, [], {}, "MODE full\nWHY no origin/main to compare with\n"),
    # nothing asked for and not on CI: nothing forces the full gate
    gate("gate-scope: readme", {"README.md"}, [], {}, NONE),
    gate("gate-scope: readme --full", {"README.md"}, ["--full"], {}, "MODE full\nWHY asked for the full gate\n"),
    gate("gate-scope: readme on CI", {"README.md"}, [], {"CI": "true"},
         "MODE full\nWHY running on CI, which always runs everything\n"),
    github("board-status usage", None, {}, ["board-status.py", "7"], False,
     ["board-status.py <issue-number> <status>"], False, [], None),
    github("board-status refuses another repo's board", {"repo": "template/origin", "project": {"number": 3}}, {},
     ["board-status.py", "7", "Done"], False, ["names template/origin but this checkout is acme/widget"], False, [],
     None),
    github("board-status needs a board", {"repo": "acme/widget", "project": {"number": 0}}, {},
     ["board-status.py", "7", "Done"], False, ["setup-github.py --board"], False, [], None),
    github("board-status refuses an unknown column", BOARD, {"project field-list": {"stdout": json.dumps(FIELDS)}},
     ["board-status.py", "7", "Doing"], False, ["unknown status 'Doing'; board columns: Not started, Done"], True,
     [], None),
    github("board-status moves the card on its board", BOARD,
     {"project field-list": {"stdout": json.dumps(FIELDS)}, "graphql query": on_board(3),
      "graphql mutation": {"stdout": json.dumps({"data": {}})}},
     ["board-status.py", "7", "Done"], True, "#7 -> Done\n", True,
     [["mutation", {"p": "P1", "i": "ITEM", "f": "F1", "o": "O2"}]], None),  # Done's option on board 3's item
    # the stand-in answers every query alike, so after item-add the issue is still only on board 9
    github("board-status adds a card from another board first", BOARD,
     {"project field-list": {"stdout": json.dumps(FIELDS)}, "graphql query": on_board(9)},
     ["board-status.py", "7", "Done"], False, ["#7 could not be added to board #3"], True,
     [["project", "item-add", "3", "--owner", "acme", "--url", "https://github.com/acme/widget/issues/7"]], None),
    github("setup-github needs a login", None, {"auth status": {"exit": 1}}, ["setup-github.py"], False,
     ["gh auth login"], True, [], None),
    github("setup-github dry run changes nothing", None,
     {"repo view": REPO_VIEW, "label list": {"stdout": json.dumps([{"name": "bug"}])}},
     ["setup-github.py", "--dry-run", "--board"], True,
     ["would update label bug", "would create label PRD", "would create a project on acme and link it to acme/widget"],
     True, [], None),
    github("setup-github resets a template's config", {
        "repo": "template/origin", "project": {"number": 4, "owner": "template"}, "backlog_prd": 12,
        "people": {"someone": "someone"}, "areas": ["paper"]},
     {"repo view": REPO_VIEW, "label list": {"stdout": "[]"}}, ["setup-github.py"], True,
     ["config came from template/origin; resetting board, backlog and people"], True, LABELS_MADE,
     {"repo": "acme/widget", "owner": "acme", "project": {"number": 0, "owner": ""}, "backlog_prd": None,
      "people": {"acme": "acme"}, "areas": ["paper"]}),
    # a re-run in the same repo keeps the hand-edited owner; Roadmap start was there already
    github("setup-github gives the board its columns and fields", {"repo": "acme/widget", "owner": "someone",
                                                             "areas": ["paper"]},
     {"repo view": REPO_VIEW, "label list": {"stdout": "[]"},
      "project list": {"stdout": json.dumps({"projects": [
          {"title": "widget", "closed": False, "number": 5, "url": "https://example.test/5"}]})},
      "project view": {"stdout": json.dumps({"id": "PROJ"})},
      "project field-list": {"stdout": json.dumps({"fields": [
          {"id": "F1", "name": "Status", "options": [{"name": "Todo"}]}, {"id": "F2", "name": "Roadmap start"}]})},
      "graphql mutation": {"stdout": json.dumps({"data": {}})}},
     ["setup-github.py", "--board"], True, [], True,
     LABELS_MADE + [["mutation", {"f": "F1", "o": COLUMNS}], ["mutation", {"p": "PROJ", "n": "Roadmap end"}],
                    ["mutation", {"p": "PROJ", "o": [{"name": "paper", "color": "BLUE", "description": "paper"}]}],
                    ["project", "link", "5", "--owner", "acme", "--repo", "acme/widget"]],
     {"repo": "acme/widget", "owner": "someone", "areas": ["paper"], "people": {"acme": "acme"},
      "project": {"number": 5, "owner": "acme"}}),
]


@pytest.mark.parametrize("before,changed,environ,answers,command,succeeds,said,asks_gh,writes,after",
                         [case[1:] for case in CASES], ids=[case[0] for case in CASES])
def test_scripts_change_only_what_they_own(scratch_repo, fake_gh, before, changed, environ, answers, command,
                                           succeeds, said, asks_gh, writes, after):
    env, answer, calls = fake_gh
    env = {**{key: value for key, value in env.items() if key not in ("CI", "GATE_FULL")}, **environ}
    if changed is not None:  # origin/main is the committed scratch repo, and each path is changed on top of it
        git(scratch_repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        for name in changed:
            (scratch_repo / name).parent.mkdir(parents=True, exist_ok=True)
            with (scratch_repo / name).open("a") as changing:
                changing.write("\n")
    config = scratch_repo / ".claude" / "project.json"
    if before is not None:
        config.write_text(json.dumps(before))
    kept = config.read_text()
    answer(answers)
    run = script(scratch_repo, env, *command)
    assert (run.returncode == 0) == succeeds, run.stdout + run.stderr
    if isinstance(said, str):
        assert run.stdout == said, run.stderr
    for fragment in said if isinstance(said, list) else []:
        assert fragment in (run.stdout if succeeds else run.stderr), run.stdout + run.stderr
    assert bool(calls()) == asks_gh, calls()
    assert [written(call) for call in calls() if is_write(call)] == writes
    assert (json.loads(config.read_text()) == after) if after is not None else config.read_text() == kept


# worktree-reap: only a dead session's clean, merged worktree goes.

def dead_pid():
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


def main_checkout(tmp_path):
    """A clone whose main is on origin, with the reaper copied in."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    main = tmp_path / "main"
    git(tmp_path, "clone", "-q", str(origin), str(main))
    git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "first")
    git(main, "push", "-q", "origin", "main")
    (main / ".claude" / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPTS / "worktree-reap.py", main / ".claude" / "scripts")
    return main


def add_worktree(main, name, pid=None, at="HEAD"):
    path = main / ".claude" / "worktrees" / name
    git(main, "worktree", "add", "-q", "-b", f"worktree-{name}", str(path), at)
    if pid is not None:
        git(main, "worktree", "lock", "--reason", f"claude agent {name} (pid {pid} start 1)", str(path))
    return path


def reap(main, hook=False, this_pc_home=None):
    env = {key: value for key, value in os.environ.items() if key != "CLAUDE_HOOK"}
    env["SCORE_THIS_PC_HOME"] = str(this_pc_home or main.parent / "no-this-pc")
    if hook:
        env["CLAUDE_HOOK"] = "SessionStart"
    return subprocess.run(["python3", main / ".claude" / "scripts" / "worktree-reap.py"], env=env,
                          capture_output=True, text=True)


def make_idle(main, *names):
    """Age these worktrees' git admin files a day, past IDLE_HOURS."""
    admin = pathlib.Path(git(main, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "worktrees"
    for name in names:
        for path in (admin / name).rglob("*"):
            if path.is_file():
                os.utime(path, (time.time() - 86400, time.time() - 86400))


def test_worktree_reap_reaps_only_a_dead_sessions_clean_merged_worktree(tmp_path):
    """One checkout holding a worktree of every kind, reaped three times: as a hook with nothing to say, by hand,
    and as a hook again after one more session died."""
    main = main_checkout(tmp_path)
    live = add_worktree(main, "live", os.getpid())
    quiet = reap(main, hook=True)
    assert (quiet.returncode, quiet.stdout) == (0, "")  # a hook with nothing reaped or left says nothing
    gone = add_worktree(main, "gone", dead_pid())
    dirty = add_worktree(main, "dirty", dead_pid())
    (dirty / "work.txt").write_text("unsaved")
    unmerged = add_worktree(main, "unmerged", dead_pid())
    git(unmerged, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local")
    kept = add_worktree(main, "kept")  # unlocked but touched just now: a finished agent's, kept for IDLE_HOURS
    idle = add_worktree(main, "idle")  # unlocked, clean, merged and untouched for a day: reaped
    idle_dirty = add_worktree(main, "idle_dirty")  # unlocked and old but holding work: never touched
    (idle_dirty / "work.txt").write_text("unsaved")
    cwd = add_worktree(main, "cwd")  # a process works in it (the run's leader, its venv's Python)
    locked_cwd = add_worktree(main, "locked_cwd", dead_pid())  # its session is dead, a process it started is not
    registered = add_worktree(main, "registered")  # a running this-PC run's registry entry names it
    finished = add_worktree(main, "finished")  # only a finished run's entry names it: reaped
    git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "second")
    git(main, "push", "-q", "origin", "main")
    paused = add_worktree(main, "paused")  # checked out at the paused run's commit
    make_idle(main, "idle", "idle_dirty", "cwd", "registered", "finished", "paused")
    home = tmp_path / "this-pc"
    (home / "runs").mkdir(parents=True)
    (home / "runs" / "1.json").write_text(json.dumps({"state": "running", "worktree": str(registered.resolve())}))
    (home / "runs" / "0.json").write_text(json.dumps({"state": "finished", "worktree": str(finished.resolve())}))
    (home / "paused.json").write_text(json.dumps({"commit": git(main, "rev-parse", "HEAD"), "argv": ["run"]}))
    workers = [subprocess.Popen(["sleep", "60"], cwd=folder) for folder in (cwd, locked_cwd)]
    try:
        run = reap(main, this_pc_home=home)
        gone_later = add_worktree(main, "gone_later", dead_pid(), at="HEAD~1")  # off the paused run's commit
        hooked = reap(main, hook=True, this_pc_home=home)
    finally:
        for worker in workers:
            worker.kill()
            worker.wait()
    assert (run.returncode, run.stdout) == (0, "Reaped 3 orphaned worktree(s): finished, gone, idle. Left 2 "
                                               "stale-locked worktree(s) with uncommitted work: dirty, unmerged. "
                                               "Recover or discard by hand.\n")
    assert hooked.returncode == 0
    assert json.loads(hooked.stdout) == {"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": "Reaped 1 orphaned worktree(s): gone_later. Left 2 "
                                                              "stale-locked worktree(s) with uncommitted work: dirty, "
                                                              "unmerged. Recover or discard by hand."}}
    assert not any(path.exists() for path in (gone, idle, finished, gone_later))
    assert all(path.exists() for path in (dirty, unmerged, live, kept, idle_dirty, cwd, locked_cwd, registered, paused))
    branches = git(main, "branch", "--format=%(refname:short)").split()
    assert "worktree-gone" not in branches and "worktree-gone_later" not in branches
    assert {"worktree-dirty", "worktree-unmerged", "worktree-live", "worktree-kept"} <= set(branches)
    alone = tmp_path / "alone"  # outside a git repo it does nothing
    alone.mkdir()
    shutil.copy(SCRIPTS / "worktree-reap.py", alone)
    run = subprocess.run(["python3", alone / "worktree-reap.py"], capture_output=True, text=True,
                         env=dict(os.environ, GIT_CEILING_DIRECTORIES=str(tmp_path)))
    assert (run.returncode, run.stdout) == (0, "")


# sandbox-home and conftest.py: no test reaches the real home, and what a test leaves goes with its sandbox
# (a test unlinked the real cloud ledger, 2026-10-17; the tests' temp stores took every inode of /tmp, 2026-10-25).

sandbox_home = module(SCRIPTS / "sandbox-home.py", "sandbox_home")
repo_conftest = module(REPO / "conftest.py", "repo_conftest")
BUBBLEWRAP = shutil.which("bwrap") is not None


def fake_home(tmp_path):
    """A stand-in real home: world data (work/) and state (cloud/ledger.jsonl)."""
    real = tmp_path / "real-home"
    (real / "work").mkdir(parents=True)
    (real / "work" / "seed.txt").write_text("seed")
    (real / "cloud").mkdir()
    (real / "cloud" / "ledger.jsonl").write_text("{}\n")
    return real


def test_a_sandbox_run_writes_only_its_own_empty_home_and_removes_all_it_leaves(tmp_path):
    """Fault (2026-10-28): the sandbox linked the real home's design/plans and work/, so tests leaned on real data
    unnoticed; a test lays out its own small fixture instead. One sandboxed command looks at its home, writes there,
    leaves a temp folder and read-only files; one tries to write the real home; one is stopped mid-run."""
    real = fake_home(tmp_path)
    said = tmp_path / "said.json"
    works = ("import json, os, pathlib, sys, tempfile; home = pathlib.Path(os.environ['PROPS_HOME']);"
             "listing = ' '.join(sorted(str(path.relative_to(home)) + ('@' if path.is_symlink() else '')"
             " for path in home.rglob('*')));"
             "assert not (home / 'cloud').exists();"
             "(home / 'cloud').mkdir(); (home / 'cloud' / 'ledger.jsonl').write_text('mine');"
             "(home / 'store-tests').mkdir(); (home / 'store-tests' / 'kept').write_text('x');"
             "os.chmod(home / 'store-tests' / 'kept', 0o444); os.chmod(home / 'store-tests', 0o555);"
             "left = pathlib.Path(tempfile.mkdtemp()); (left / 'kept').write_text('x');"
             "assert home.parent == pathlib.Path(tempfile.gettempdir()), home;"
             "pathlib.Path(sys.argv[1]).write_text(json.dumps({'home': str(home), 'listing': listing, 'left': str(left)}))")
    assert sandbox_home.run([sys.executable, "-c", works, str(said)], real) == 0
    seen = json.loads(said.read_text())
    assert seen["listing"] == "store store/cache"  # empty but for its store, nothing of the real home linked
    assert not pathlib.Path(seen["home"]).exists() and not pathlib.Path(seen["left"]).exists()
    if BUBBLEWRAP:  # without bubblewrap the real home cannot be mounted read-only
        through = f"import pathlib; pathlib.Path({str(real / 'work' / 'seed.txt')!r}).write_text('gone')"
        assert sandbox_home.run([sys.executable, "-c", through], real) != 0  # a write to the real home fails loudly
    assert (real / "cloud" / "ledger.jsonl").read_text() == "{}\n"
    assert (real / "work" / "seed.txt").read_text() == "seed"
    # a stopped make or a closed terminal (SIGTERM) left the run's temp folder with its stores
    said = tmp_path / "temp.txt"
    waits = "import os, pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(os.environ['TMPDIR']); time.sleep(60)"
    sandbox = subprocess.Popen([sys.executable, str(SCRIPTS / "sandbox-home.py"), "--", sys.executable, "-c", waits,
                                str(said)], env={**os.environ, "SCORE_REAL_HOME": str(real)})
    try:
        deadline = time.time() + 20
        while not (said.exists() and said.read_text()) and time.time() < deadline:
            time.sleep(0.05)
        sandbox.terminate()
        assert sandbox.wait(20) != 0 and not pathlib.Path(said.read_text()).exists()
    finally:
        sandbox.kill()


# Folders whose every file is in a paid row's code key (score.stages.moved): a test edited there moves paid rows, so
# their plain-script tests are run only through `make tests` until those rows are next made.
KEYED = ("tools/characters/maker/", "tools/characters/people/", "tools/props/closeup/")
MAIN_BLOCK = 'if __name__ == "__main__":'


def plain_script_tests():
    """Every test file of the repository run as a plain script (it has a `__main__` block), outside KEYED."""
    listed = subprocess.run(["git", "ls-files", "tools/*_test.py", "score/*_test.py", "tools/*/test_*.py",
                             "score/*/test_*.py"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return [REPO / name for name in sorted(set(listed))
            if not name.startswith(KEYED) and (REPO / name).is_file() and MAIN_BLOCK in (REPO / name).read_text()]


GUARDED = ("PROPS_HOME", "PROPS_WORK", "SCORE_SPEND_STORE")
REAL_PROPS = str(pathlib.Path.home() / ".farm-factory-props")
GUARD_CASES = [  # (id, the guarded variables ({sandbox}: a fresh mkdtemp), the refusal (None: runs), whole or a part)
    ("no home", {}, "PROPS_HOME is not set", True),
    ("the real home", {"PROPS_HOME": REAL_PROPS}, "is not a folder of its own", False),
    ("the system temp", {"PROPS_HOME": "{temp}"}, "is not a folder of its own", False),
    ("the root", {"PROPS_HOME": "/"}, "is not a folder of its own", False),
    ("a sandbox", {"PROPS_HOME": "{sandbox}"}, None, True),
    ("work in the real home", {"PROPS_HOME": "{sandbox}", "PROPS_WORK": str(pathlib.Path.home())}, "PROPS_WORK", False),
    ("work in the sandbox", {"PROPS_HOME": "{sandbox}", "PROPS_WORK": "{sandbox}/work"}, None, True),
    # kept.py and preflight.py prefer the real store
    ("the real spend store", {"PROPS_HOME": "{sandbox}", "SCORE_SPEND_STORE": f"{REAL_PROPS}/store"},
     "SCORE_SPEND_STORE", False),
    ("a sandbox spend store", {"PROPS_HOME": "{sandbox}", "SCORE_SPEND_STORE": "{sandbox}/store"}, None, True),
]


def test_no_test_starts_outside_a_sandbox_home(tmp_path):
    """Faults: a test unlinked the real cloud ledger (2026-10-17); conftest.py covered pytest runs only, so 146 of 149
    plain-script tests ran by hand against the real home (2026-10-18 review); 529 stores were left in /tmp by test
    files run by hand with PROPS_HOME=$(mktemp -d) (2026-10-26). Each guarded environment is judged by the guard, by a
    pytest run and by a plain-script run; then every plain-script test is read for the guard as its first step."""
    target = pathlib.Path(__file__).relative_to(REPO)
    clean = {name: value for name, value in os.environ.items() if name not in GUARDED}
    # a plain script's first step, then the stores it leaves behind in its temp folder
    leaves = ("import pathlib, runpy, sys, tempfile;"
              f"runpy.run_path({str(REPO / 'conftest.py')!r})['refuse_outside_sandbox']();"
              "left = pathlib.Path(tempfile.mkdtemp()) / 'store'; left.mkdir(); (left / 'object').write_text('x');"
              "(left / 'object').chmod(0o444); left.chmod(0o555); pathlib.Path(sys.argv[1]).write_text(str(left))")
    for number, (name, guarded, refusal, whole) in enumerate(GUARD_CASES):
        sandbox = tempfile.mkdtemp()
        environ = {key: value.format(sandbox=sandbox, temp=repo_conftest.system_temp())
                   for key, value in guarded.items()}
        judged = repo_conftest.sandbox_refusal(environ)
        assert (judged == refusal) if whole or refusal is None else (refusal in (judged or "")), (name, judged)
        collected = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only",
                                    str(target)], cwd=REPO, env={**clean, **environ}, capture_output=True, text=True)
        said = collected.stdout + collected.stderr
        if refusal is None:
            assert collected.returncode == 0 and target.stem in said, (name, said)
        else:
            assert collected.returncode == 4 and "refused" in said and target.stem not in said, (name, said)
        left = tmp_path / f"left-{number}.txt"
        try:
            ran = subprocess.run([sys.executable, "-c", leaves, str(left)], env={**clean, **environ},
                                 capture_output=True, text=True)
            if refusal is None:  # it ran, and its stores and its empty home went with it
                assert ran.returncode == 0, (name, ran.stderr)
                assert not pathlib.Path(left.read_text()).exists() and not pathlib.Path(sandbox).exists(), name
            else:
                assert ran.returncode != 0 and f"refused: {judged}" in ran.stderr and not left.exists(), (name, ran.stderr)
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
    plain = plain_script_tests()
    for path in plain:
        # the lines after the guard; its own line may end in a comment
        block = path.read_text().split(MAIN_BLOCK, 1)[1].splitlines()[1:]
        guard = next(line for line in block if not line.strip().startswith("import "))  # first after its imports
        if guard.strip().startswith("sys.exit(pytest.main("):
            continue  # a pytest run: conftest.py refuses it
        # its first step, inline or through a conftest loaded before (a wrong path to it fails loudly, not silently)
        assert "refuse_outside_sandbox" in guard and '"conftest.py"' in path.read_text(), path
    # a real plain-script test run with no home; were the refusal gone, it would reach a scratch home, not the real one
    done = subprocess.run([sys.executable, str(plain[0])], cwd=REPO, env={**clean, "HOME": str(tmp_path)},
                          capture_output=True, text=True)
    assert done.returncode != 0 and "refused: PROPS_HOME is not set" in done.stderr, done.stderr


# bootstrap.sh, against a scratch HOME.

def write_ssh_tools(folder):
    """Stand-ins for ssh-agent, ssh-add, ssh-keygen and ssh: the agent is a file at its socket, its keys a file beside
    it; ssh logs its call and answers as GitHub does, port 22 as FAKE_SSH_22 says, port 443 always."""
    write_tool(folder, "ssh-agent", '#!/bin/sh\n[ "$1" = -a ] && : > "$2"\n')
    write_tool(folder, "ssh-add", '#!/bin/sh\n[ -e "$SSH_AUTH_SOCK" ] || exit 2\n'
               'if [ "$1" = -l ]; then [ -s "$SSH_AUTH_SOCK.keys" ] && cat "$SSH_AUTH_SOCK.keys" && exit 0; '
               'echo "The agent has no identities."; exit 1; fi\n'
               'echo "256 SHA256:fake $1 (ED25519)" >> "$SSH_AUTH_SOCK.keys"\n')
    write_tool(folder, "ssh-keygen", '#!/bin/sh\necho "256 SHA256:fake tester (ED25519)"\n')
    write_tool(folder, "ssh", '#!/bin/sh\necho "ssh $*" >> "$TOOL_LOG"\n'
               'case "$*" in *"-p 443"*) ok=ok ;; *) ok="$FAKE_SSH_22" ;; esac\n'
               '[ "$ok" = ok ] || { echo "git@github.com: Permission denied (publickey)." >&2; exit 255; }\n'
               'echo "Hi tester! You\'ve successfully authenticated, but GitHub does not provide shell access." >&2\n'
               'exit 1\n')


@pytest.fixture
def machine(tmp_path, scratch_repo):
    """A scratch HOME and the env to run the scripts in."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    write_tool(tmp_path / "bin", "gh", '#!/bin/sh\nexit 1\n')
    # uv logs where it was asked to sync into, and leaves an interpreter there as the real one does
    write_tool(tmp_path / "bin", "uv", '#!/bin/sh\necho "uv $* env=$UV_PROJECT_ENVIRONMENT" >> "$TOOL_LOG"\n'
               '[ -n "$UV_PROJECT_ENVIRONMENT" ] && mkdir -p "$UV_PROJECT_ENVIRONMENT/bin" '
               '&& printf "#!/bin/sh\\n" > "$UV_PROJECT_ENVIRONMENT/bin/python" '
               '&& chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"\nexit 0\n')
    write_ssh_tools(tmp_path / "bin")
    env = {key: value for key, value in os.environ.items()
           if key not in ("CLAUDE_CONFIG_DIR", "PROPS_HOME")}
    env.update(HOME=str(home), PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}", TOOL_LOG=str(tmp_path / "tools.log"))
    return home, env


def shell(repo, env, name):
    return subprocess.run(["bash", repo / ".claude" / "scripts" / name], env=env, capture_output=True, text=True)


def test_bootstrap_touches_only_its_links_flags_runtime_and_ssh_lines(scratch_repo, machine, tmp_path):
    """bootstrap.sh run twice on a scratch HOME that already holds a memory folder, then ssh-agent.sh twice on two
    homes holding a key."""
    home, env = machine
    target = home / ".claude" / "projects" / str(scratch_repo).replace("/", "-") / "memory"
    target.mkdir(parents=True)
    (target / "note.txt").write_text("an old memory")
    env["PROPS_HOME"] = str(tmp_path / "elsewhere")  # the cloud runner calls PROPS_HOME's env: a moved home moves it
    runtime = tmp_path / "elsewhere" / "env"
    run = shell(scratch_repo, env, "bootstrap.sh")
    assert run.returncode == 0, run.stderr
    assert target.is_symlink() and target.resolve() == scratch_repo / ".claude" / "memory"
    assert (scratch_repo / ".claude" / "memory" / "note.txt").read_text() == "an old memory"
    assert len(list(target.parent.glob("memory.bak.*"))) == 1
    assert git(scratch_repo, "config", "core.hooksPath") == ".claude/hooks"
    assert git(scratch_repo, "config", "score.movedCheck") == "true"
    assert "gh: installed but not logged in. Run: gh auth login" in run.stdout
    assert (runtime / "bin" / "python").exists()
    again = shell(scratch_repo, env, "bootstrap.sh").stdout
    assert "memory: already linked" in again and f"runtime python: already at {runtime}" in again
    syncs = [line for line in (tmp_path / "tools.log").read_text().splitlines() if line.startswith("uv ")]
    assert syncs == ["uv sync -q --frozen env=", f"uv sync -q --frozen --no-dev --project {scratch_repo} env={runtime}",
                     "uv sync -q --frozen env="]
    assert "ssh-agent: no ~/.ssh/id_ed25519" in run.stdout  # no key: nothing of ~/.ssh is touched
    assert not (home / ".ssh").exists() and not (home / ".bashrc").exists()
    # ssh-agent.sh with a key, on two scratch homes: one whose port 22 GitHub refuses, one where it works
    for port_22, home in (("refused", tmp_path / "home22refused"), ("ok", tmp_path / "home22ok")):
        (home / ".ssh").mkdir(parents=True)
        (home / ".ssh" / "id_ed25519").write_text("key")
        (home / ".ssh" / "id_ed25519.pub").write_text("ssh-ed25519 AAAA tester")
        env.update(HOME=str(home), FAKE_SSH_22=port_22)
        first, again = shell(scratch_repo, env, "ssh-agent.sh"), shell(scratch_repo, env, "ssh-agent.sh")
        assert first.returncode == 0 and again.returncode == 0, first.stderr + again.stderr
        assert "ssh-agent: key loaded" in first.stdout and "ssh-agent: key already loaded" in again.stdout
        assert (home / ".ssh" / "agent" / "agent.sock").exists()
        assert (home / ".bashrc").read_text().count('SSH_AUTH_SOCK="$HOME/.ssh/agent/agent.sock"') == 1
        config = (home / ".ssh" / "config").read_text()
        assert config.count("AddKeysToAgent yes") == 1
        fallback = "Host github.com\n  HostName ssh.github.com\n  Port 443\n  User git\n"
        assert config.count(fallback) == (1 if port_22 == "refused" else 0), config
    probes = [line for line in (tmp_path / "tools.log").read_text().splitlines() if line.startswith("ssh -T")]
    probe = "ssh -T -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8"
    assert probes == [f"{probe} git@github.com", f"{probe} -p 443 git@ssh.github.com",  # 22 refused: 443 tried, kept
                      f"{probe} git@github.com", f"{probe} git@github.com"]  # 22 works: 443 never tried
