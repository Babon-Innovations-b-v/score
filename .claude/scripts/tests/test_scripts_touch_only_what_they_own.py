"""The harness scripts change only what they own: board-status only this repo's card, setup-github only this repo's
labels, board and config (nothing on a dry run), worktree-reap only a dead session's clean merged worktree, the
installers only their own settings (the committed ones and the user's own put back), and sandbox-home and conftest.py
keep every test off the real home while removing everything a test leaves.

Every script is driven from outside as a copy in a scratch git repo (each finds its repo from its own path); `gh`,
`claude`, `uv` and the pinned binaries are stand-ins that log their calls, and HOME is a scratch folder, so nothing
runs against this machine. The expected answers are the scripts' rules, written out by hand here.

The break that turns each test red (applied once each, seen red, reverted):

- test_board_status_refuses_another_repos_board_or_an_unknown_column: config()'s `here and repo and here != repo`
  made `False`.
- test_board_status_moves_a_card_on_the_board_into_its_column: main's mutation sent with `o=options[0]["id"]`.
- test_board_status_adds_a_card_from_another_board_first: board_item's `node["project"]["number"] == number` made
  `True`.
- test_gate_scope_runs_nothing_only_for_documents: is_document's `BUILT_PREFIXES + CODE_PREFIXES` made
  `BUILT_PREFIXES`.
- test_gate_scope_runs_everything_when_asked_or_on_ci: forced_reason's CI branch removed.
- test_setup_github_needs_a_login_and_a_dry_run_changes_nothing: sync_labels creates a label even on a dry run.
- test_setup_github_resets_a_template_config_and_syncs_labels: main keeps the template's backlog_prd.
- test_setup_github_gives_the_board_its_columns_and_fields: "Review" taken out of STATUS_OPTIONS.
- test_worktree_reap_reaps_only_a_dead_sessions_clean_merged_worktree: is_clean returns True at once; or reap's
  `idle_hours(...) >= IDLE_HOURS` made `True` (a recent unlocked worktree is reaped).
- test_worktree_reap_speaks_json_as_a_hook_and_only_when_it_did_something: main prints the report also when empty.
- test_the_guard_names_every_home_outside_a_sandbox: outside_temp's `folder == temp` test dropped.
- test_a_pytest_run_without_a_sandbox_home_stops_before_collecting: pytest_configure's refusal skipped.
- test_a_sandboxed_test_reads_world_data_and_writes_only_its_own_home: sandbox-home's read_only_command drops
  `--ro-bind`.
- test_a_sandbox_removes_what_its_test_leaves_even_when_stopped: run's `finally` drops `shutil.rmtree(temp, ...)`.
- test_a_test_run_by_hand_removes_its_temp_stores_and_its_empty_home: own_temp's `removed` holds only `[folder]`.
- test_a_test_adds_its_own_work_folder_beside_the_real_ones: `MIRRORED = ()`.
- test_every_plain_script_test_refuses_first_without_a_sandbox_home (a wording check guarding the owner's rule that
  no test touches the real home, 2026-10-18): refuse_outside_sandbox's `if refusal:` made `if False:`.
- test_install_writes_claude_mem_settings_and_keeps_the_rest: the installer's settings merge starts from `{}`.
- test_install_adds_the_plugin_and_puts_the_committed_settings_back: the installer's restore of settings.json removed.
- test_bootstrap_links_memory_without_losing_any: bootstrap moves the old memory folder aside without copying it.
- test_bootstrap_sets_the_hooks_and_builds_the_runtime_python_once: bootstrap's runtime build ignores PROPS_HOME.

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
LOGGING_TOOL = '#!/bin/sh\necho "$(basename "$0") $*" >> "$TOOL_LOG"\n'


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
    """A git repo holding a copy of the scripts, the codebase-memory pin and a project.json for acme/widget."""
    repo = tmp_path / "repo"
    shutil.copytree(SCRIPTS, repo / ".claude" / "scripts", ignore=shutil.ignore_patterns("tests"))
    pin = repo / "vendor" / "codebase-memory-mcp"
    pin.mkdir(parents=True)
    shutil.copy(REPO / "vendor" / "codebase-memory-mcp" / "release.env", pin)
    (repo / "vendor" / "claude-mem").mkdir()
    (repo / ".claude" / "settings.json").write_text('{"committed": true}\n')
    (repo / ".claude" / "project.json").write_text(json.dumps({"repo": "acme/widget"}) + "\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "remote", "add", "origin", "git@github.com:acme/widget.git")
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


# board-status: only this repo's card, only into a column the board has.

FIELDS = {"fields": [{"id": "F1", "name": "Status", "options": [
    {"id": "O1", "name": "Not started"}, {"id": "O2", "name": "Done"}]}]}


def on_board(project_number):
    return {"repository": {"issue": {"id": "I1", "projectItems": {"nodes": [
        {"id": "ITEM", "project": {"id": "P1", "number": project_number}}]}}}}


def configure(repo, config):
    (repo / ".claude" / "project.json").write_text(json.dumps(config))


def test_board_status_refuses_another_repos_board_or_an_unknown_column(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    assert "board-status.py <issue-number> <status>" in script(scratch_repo, env, "board-status.py", "7").stderr
    configure(scratch_repo, {"repo": "template/origin", "project": {"number": 3}})
    run = script(scratch_repo, env, "board-status.py", "7", "Done")
    assert run.returncode != 0 and "names template/origin but this checkout is acme/widget" in run.stderr
    assert calls() == []  # refused before gh was asked anything
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 0}})
    run = script(scratch_repo, env, "board-status.py", "7", "Done")
    assert run.returncode != 0 and "setup-github.py --board" in run.stderr
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    answer({"project field-list": {"stdout": json.dumps(FIELDS)}})
    run = script(scratch_repo, env, "board-status.py", "7", "Doing")
    assert run.returncode != 0 and "unknown status 'Doing'; board columns: Not started, Done" in run.stderr


def test_board_status_moves_a_card_on_the_board_into_its_column(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    answer({"project field-list": {"stdout": json.dumps(FIELDS)},
            "graphql query": {"stdout": json.dumps({"data": on_board(3)})},
            "graphql mutation": {"stdout": json.dumps({"data": {}})}})
    run = script(scratch_repo, env, "board-status.py", "7", "Done")
    assert (run.returncode, run.stdout) == (0, "#7 -> Done\n"), run.stderr
    assert {"p=P1", "i=ITEM", "f=F1", "o=O2"} <= set(calls()[-1]["args"])  # Done's option on board 3's item
    assert not any(call["args"][:2] == ["project", "item-add"] for call in calls())


def test_board_status_adds_a_card_from_another_board_first(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    configure(scratch_repo, {"repo": "acme/widget", "project": {"number": 3, "owner": "acme"}})
    # the stand-in answers every query alike, so after item-add the issue is still only on board 9
    answer({"project field-list": {"stdout": json.dumps(FIELDS)},
            "graphql query": {"stdout": json.dumps({"data": on_board(9)})}})
    run = script(scratch_repo, env, "board-status.py", "7", "Done")
    assert run.returncode != 0 and "#7 could not be added to board #3" in run.stderr
    assert [call["args"] for call in calls() if call["args"][:2] == ["project", "item-add"]] == [
        ["project", "item-add", "3", "--owner", "acme", "--url", "https://github.com/acme/widget/issues/7"]]
    assert not any("mutation" in " ".join(call["args"]) for call in calls())  # no other board's card was moved


# gate-scope: documents alone run nothing; anything else, and every doubt, runs everything.

gate_scope = module(SCRIPTS / "gate-scope.py", "gate_scope")


@pytest.mark.parametrize("changed,mode", [
    ({"CONTEXT.md", "docs/bible.md", "src/CLAUDE.md", ".claude/skills/grill/SKILL.md"}, "none"),
    ({"docs/bible.md", "src/app.py"}, "full"),
    ({"paper/source/score.md"}, "full"),  # the paper's draft is a build input
    ({".claude/hooks/md_guard.py"}, "full"), ({".claude/scripts/gate-scope.py"}, "full"),
    ({".claude/settings.json"}, "full"),
    (None, "full"),  # nothing to compare with
])
def test_gate_scope_runs_nothing_only_for_documents(changed, mode):
    assert gate_scope.plan(changed, "")[0] == mode


def test_gate_scope_runs_everything_when_asked_or_on_ci(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GATE_FULL", raising=False)
    assert gate_scope.forced_reason([]) == ""
    assert gate_scope.plan({"README.md"}, gate_scope.forced_reason(["--full"]))[0] == "full"
    monkeypatch.setenv("CI", "true")
    assert gate_scope.plan({"README.md"}, gate_scope.forced_reason([]))[0] == "full"


# setup-github: labels synced, a template's config reset, the board given its columns, a dry run changes nothing.

REPO_VIEW = {"stdout": json.dumps({"nameWithOwner": "acme/widget", "owner": {"login": "acme"}})}


def test_setup_github_needs_a_login_and_a_dry_run_changes_nothing(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    answer({"auth status": {"exit": 1}})
    run = script(scratch_repo, env, "setup-github.py")
    assert run.returncode != 0 and "gh auth login" in run.stderr
    config = scratch_repo / ".claude" / "project.json"
    before = config.read_text()
    answer({"repo view": REPO_VIEW, "label list": {"stdout": json.dumps([{"name": "bug"}])}})
    run = script(scratch_repo, env, "setup-github.py", "--dry-run", "--board")
    assert run.returncode == 0, run.stderr
    assert "would update label bug" in run.stdout and "would create label PRD" in run.stdout
    assert "would create a project on acme and link it to acme/widget" in run.stdout
    assert config.read_text() == before
    assert not any(call["args"][:2] in (["label", "create"], ["label", "edit"], ["project", "create"])
                   for call in calls())


def test_setup_github_resets_a_template_config_and_syncs_labels(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    config = scratch_repo / ".claude" / "project.json"
    config.write_text(json.dumps({"repo": "template/origin", "project": {"number": 4, "owner": "template"},
                                  "backlog_prd": 12, "people": {"someone": "someone"}, "areas": ["paper"]}))
    answer({"repo view": REPO_VIEW, "label list": {"stdout": "[]"}})
    run = script(scratch_repo, env, "setup-github.py")
    assert run.returncode == 0, run.stderr
    assert "config came from template/origin; resetting board, backlog and people" in run.stdout
    assert json.loads(config.read_text()) == {
        "repo": "acme/widget", "owner": "acme", "project": {"number": 0, "owner": ""},
        "backlog_prd": None, "people": {"acme": "acme"}, "areas": ["paper"]}
    assert [call["args"][2] for call in calls() if call["args"][:2] == ["label", "create"]] == [
        "PRD", "vision", "bug", "enhancement", "needs-triage", "needs-info", "ready-for-agent", "ready-for-human",
        "wontfix"]


def test_setup_github_gives_the_board_its_columns_and_fields(scratch_repo, fake_gh):
    env, answer, calls = fake_gh
    config = scratch_repo / ".claude" / "project.json"
    config.write_text(json.dumps({"repo": "acme/widget", "areas": ["paper"]}))
    fields = {"fields": [{"id": "F1", "name": "Status", "options": [{"name": "Todo"}]},
                         {"id": "F2", "name": "Roadmap start"}]}
    answer({"repo view": REPO_VIEW, "label list": {"stdout": "[]"},
            "project list": {"stdout": json.dumps({"projects": [
                {"title": "widget", "closed": False, "number": 5, "url": "https://example.test/5"}]})},
            "project view": {"stdout": json.dumps({"id": "PROJ"})},
            "project field-list": {"stdout": json.dumps(fields)},
            "graphql mutation": {"stdout": json.dumps({"data": {}})}})
    run = script(scratch_repo, env, "setup-github.py", "--board")
    assert run.returncode == 0, run.stderr
    assert json.loads(config.read_text())["project"] == {"number": 5, "owner": "acme"}
    mutations = [json.loads(call["stdin"])["variables"] for call in calls() if call["stdin"]]
    assert [option["name"] for option in mutations[0]["o"]] == [
        "LowPriority", "Not started", "In Progress", "Review", "Done"]
    assert mutations[1] == {"p": "PROJ", "n": "Roadmap end"}  # Roadmap start was there already
    assert mutations[2]["o"] == [{"name": "paper", "color": "BLUE", "description": "paper"}] and len(mutations) == 3
    assert ["project", "link", "5", "--owner", "acme", "--repo", "acme/widget"] in [call["args"] for call in calls()]


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


def add_worktree(main, name, pid=None):
    path = main / ".claude" / "worktrees" / name
    git(main, "worktree", "add", "-q", "-b", f"worktree-{name}", str(path))
    if pid is not None:
        git(main, "worktree", "lock", "--reason", f"claude agent {name} (pid {pid} start 1)", str(path))
    return path


def reap(main, hook=False):
    env = {key: value for key, value in os.environ.items() if key != "CLAUDE_HOOK"}
    if hook:
        env["CLAUDE_HOOK"] = "SessionStart"
    return subprocess.run(["python3", main / ".claude" / "scripts" / "worktree-reap.py"], env=env,
                          capture_output=True, text=True)


def test_worktree_reap_reaps_only_a_dead_sessions_clean_merged_worktree(tmp_path):
    main = main_checkout(tmp_path)
    gone = add_worktree(main, "gone", dead_pid())
    dirty = add_worktree(main, "dirty", dead_pid())
    (dirty / "work.txt").write_text("unsaved")
    unmerged = add_worktree(main, "unmerged", dead_pid())
    git(unmerged, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local")
    live = add_worktree(main, "live", os.getpid())
    kept = add_worktree(main, "kept")  # unlocked but touched just now: a finished agent's, kept for IDLE_HOURS
    idle = add_worktree(main, "idle")  # unlocked, clean, merged and untouched for a day: reaped
    idle_dirty = add_worktree(main, "idle_dirty")  # unlocked and old but holding work: never touched
    (idle_dirty / "work.txt").write_text("unsaved")
    admin = pathlib.Path(git(main, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "worktrees"
    for name in ("idle", "idle_dirty"):
        for path in (admin / name).rglob("*"):
            if path.is_file():
                os.utime(path, (time.time() - 86400, time.time() - 86400))
    run = reap(main)
    assert run.returncode == 0
    assert run.stdout == ("Reaped 2 orphaned worktree(s): gone, idle. Left 2 stale-locked worktree(s) with "
                          "uncommitted work: dirty, unmerged. Recover or discard by hand.\n")
    assert not gone.exists() and not idle.exists()
    assert all(path.exists() for path in (dirty, unmerged, live, kept, idle_dirty))
    branches = git(main, "branch", "--format=%(refname:short)").split()
    assert "worktree-gone" not in branches
    assert {"worktree-dirty", "worktree-unmerged", "worktree-live", "worktree-kept"} <= set(branches)
    alone = tmp_path / "alone"  # outside a git repo it does nothing
    alone.mkdir()
    shutil.copy(SCRIPTS / "worktree-reap.py", alone)
    run = subprocess.run(["python3", alone / "worktree-reap.py"], capture_output=True, text=True,
                         env=dict(os.environ, GIT_CEILING_DIRECTORIES=str(tmp_path)))
    assert (run.returncode, run.stdout) == (0, "")


def test_worktree_reap_speaks_json_as_a_hook_and_only_when_it_did_something(tmp_path):
    main = main_checkout(tmp_path)
    add_worktree(main, "live", os.getpid())
    quiet = reap(main, hook=True)
    assert (quiet.returncode, quiet.stdout) == (0, "")
    add_worktree(main, "gone", dead_pid())
    run = reap(main, hook=True)
    assert run.returncode == 0
    assert json.loads(run.stdout) == {"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": "Reaped 1 orphaned worktree(s): gone."}}


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


def test_the_guard_names_every_home_outside_a_sandbox(tmp_path):
    sandbox = tempfile.mkdtemp()
    assert repo_conftest.sandbox_refusal({}) == "PROPS_HOME is not set"
    for home in (str(pathlib.Path.home() / ".farm-factory-props"), repo_conftest.system_temp(), "/"):
        assert "is not a folder of its own" in repo_conftest.sandbox_refusal({"PROPS_HOME": str(home)}), home
    assert repo_conftest.sandbox_refusal({"PROPS_HOME": sandbox}) is None
    assert "PROPS_WORK" in repo_conftest.sandbox_refusal({"PROPS_HOME": sandbox, "PROPS_WORK": str(pathlib.Path.home())})
    assert repo_conftest.sandbox_refusal({"PROPS_HOME": sandbox, "PROPS_WORK": f"{sandbox}/work"}) is None
    real_store = str(pathlib.Path.home() / ".farm-factory-props" / "store")  # kept.py and preflight.py prefer it
    assert "SCORE_SPEND_STORE" in repo_conftest.sandbox_refusal({"PROPS_HOME": sandbox, "SCORE_SPEND_STORE": real_store})
    assert repo_conftest.sandbox_refusal({"PROPS_HOME": sandbox, "SCORE_SPEND_STORE": f"{sandbox}/store"}) is None


def test_a_pytest_run_without_a_sandbox_home_stops_before_collecting():
    target = pathlib.Path(__file__).relative_to(REPO)
    environ = {name: value for name, value in os.environ.items() if name not in ("PROPS_HOME", "PROPS_WORK")}
    for home, collected in ((None, False), (str(pathlib.Path.home() / ".farm-factory-props"), False),
                            (tempfile.mkdtemp(), True)):
        done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only",
                               str(target)], cwd=REPO, env={**environ, **({"PROPS_HOME": home} if home else {})},
                              capture_output=True, text=True)
        said = done.stdout + done.stderr
        if collected:
            assert done.returncode == 0 and target.stem in said, said
        else:
            assert done.returncode == 4 and "refused" in said and target.stem not in said, said


@pytest.mark.skipif(not BUBBLEWRAP, reason="no bubblewrap: nothing is linked, so nothing to write through")
def test_a_sandboxed_test_reads_world_data_and_writes_only_its_own_home(tmp_path):
    real = fake_home(tmp_path)
    said = tmp_path / "home.txt"
    writes = ("import os, pathlib, sys; home = pathlib.Path(os.environ['PROPS_HOME']);"
              "assert (home / 'work' / 'seed.txt').read_text() == 'seed';"
              "assert not (home / 'cloud').exists();"
              "(home / 'cloud').mkdir(); (home / 'cloud' / 'ledger.jsonl').write_text('mine');"
              "(home / 'store-tests').mkdir(); (home / 'store-tests' / 'kept').write_text('x');"
              "os.chmod(home / 'store-tests' / 'kept', 0o444); os.chmod(home / 'store-tests', 0o555);"
              "pathlib.Path(sys.argv[1]).write_text(str(home))")
    assert sandbox_home.run([sys.executable, "-c", writes, str(said)], real) == 0
    assert not pathlib.Path(said.read_text()).exists()  # the sandbox and its read-only files are gone
    through = "import os, pathlib; (pathlib.Path(os.environ['PROPS_HOME']) / 'work' / 'seed.txt').write_text('gone')"
    assert sandbox_home.run([sys.executable, "-c", through], real) != 0  # a write through a link fails loudly
    remove = "import os, pathlib; (pathlib.Path(os.environ['PROPS_HOME']) / 'work' / 'seed.txt').unlink()"
    sandbox_home.run([sys.executable, "-c", remove], real)  # removes at most the sandbox's own link
    assert (real / "cloud" / "ledger.jsonl").read_text() == "{}\n"
    assert (real / "work" / "seed.txt").read_text() == "seed"


def test_a_sandbox_removes_what_its_test_leaves_even_when_stopped(tmp_path):
    real = fake_home(tmp_path)
    said = tmp_path / "left.txt"
    leaves = ("import os, pathlib, sys, tempfile; left = pathlib.Path(tempfile.mkdtemp()); (left / 'kept').write_text('x');"
              "home = pathlib.Path(os.environ['PROPS_HOME']);"
              "assert home.parent == pathlib.Path(tempfile.gettempdir()), home;"
              "pathlib.Path(sys.argv[1]).write_text(str(left))")
    assert sandbox_home.run([sys.executable, "-c", leaves, str(said)], real) == 0
    assert not pathlib.Path(said.read_text()).exists()
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


def test_a_test_run_by_hand_removes_its_temp_stores_and_its_empty_home(tmp_path):
    """2026-10-26: 529 stores left in /tmp by test files run by hand with PROPS_HOME=$(mktemp -d)."""
    home = pathlib.Path(tempfile.mkdtemp())
    said = tmp_path / "left.txt"
    leaves = ("import pathlib, runpy, sys, tempfile;"
              f"runpy.run_path({str(REPO / 'conftest.py')!r})['refuse_outside_sandbox']();"
              "left = pathlib.Path(tempfile.mkdtemp()) / 'store'; left.mkdir(); (left / 'object').write_text('x');"
              "(left / 'object').chmod(0o444); left.chmod(0o555); pathlib.Path(sys.argv[1]).write_text(str(left))")
    try:
        subprocess.run([sys.executable, "-c", leaves, str(said)], check=True, env={**os.environ, "PROPS_HOME": str(home)})
        assert not pathlib.Path(said.read_text()).exists() and not home.exists()
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_a_test_adds_its_own_work_folder_beside_the_real_ones(tmp_path):
    """Fault (2026-10-18 review): work/ was one link, so a test making a folder in it (carry.py's commits, a ship
    build's plan) failed on the read-only real home."""
    real = fake_home(tmp_path)
    (real / "work" / "carry-commits" / "old").mkdir(parents=True)
    linked = sandbox_home.make_sandbox(real, link=True)
    bare = sandbox_home.make_sandbox(real, link=False)  # without bubblewrap nothing is linked
    try:
        assert sorted(entry.name for entry in linked.iterdir()) == ["store", "work"]  # cloud/ is state: not linked
        assert (linked / "work").is_dir() and not (linked / "work").is_symlink()
        assert (linked / "work" / "carry-commits").is_dir() and not (linked / "work" / "carry-commits").is_symlink()
        assert (linked / "work" / "carry-commits" / "old").is_symlink()
        assert [entry.name for entry in bare.iterdir()] == ["store"]
    finally:
        sandbox_home.remove(linked)
        sandbox_home.remove(bare)
    assert not linked.exists() and (real / "work" / "seed.txt").read_text() == "seed"
    if BUBBLEWRAP:
        adds = ("import os, pathlib; work = pathlib.Path(os.environ['PROPS_HOME']) / 'work';"
                "(work / 'mine').mkdir(); (work / 'carry-commits' / 'new').mkdir()")
        assert sandbox_home.run([sys.executable, "-c", adds], real) == 0
    assert sorted(entry.name for entry in (real / "work").iterdir()) == ["carry-commits", "seed.txt"]
    assert [entry.name for entry in (real / "work" / "carry-commits").iterdir()] == ["old"]


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


def test_every_plain_script_test_refuses_first_without_a_sandbox_home(tmp_path):
    """Fault (2026-10-18 review): conftest.py covered pytest runs only; 146 of 149 plain-script tests ran by hand
    against the real home. A wording check on each file's `__main__` block, then one run without a home."""
    plain = plain_script_tests()
    for path in plain:
        # the lines after the guard; its own line may end in a comment
        block = path.read_text().split(MAIN_BLOCK, 1)[1].splitlines()[1:]
        guard = next(line for line in block if not line.strip().startswith("import "))  # first after its imports
        if guard.strip().startswith("sys.exit(pytest.main("):
            continue  # a pytest run: conftest.py refuses it
        # its first step, inline or through a conftest loaded before (a wrong path to it fails loudly, not silently)
        assert "refuse_outside_sandbox" in guard and '"conftest.py"' in path.read_text(), path
    environ = {name: value for name, value in os.environ.items() if name not in ("PROPS_HOME", "PROPS_WORK")}
    environ["HOME"] = str(tmp_path)  # were the refusal gone, the run would reach a scratch home, not the real one
    for path in plain[:1]:
        done = subprocess.run([sys.executable, str(path)], cwd=REPO, env=environ, capture_output=True, text=True)
        assert done.returncode != 0 and "refused: PROPS_HOME is not set" in done.stderr, done.stderr


# install-agent-tools.sh and bootstrap.sh, against a scratch HOME with the pinned tools already in place.

@pytest.fixture
def machine(tmp_path, scratch_repo):
    """A scratch HOME with the pinned tools in place, and the env to run the scripts in."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    write_tool(home / ".local" / "bin", "codebase-memory-mcp",
               '#!/bin/sh\n[ "$1" = --version ] && { echo "codebase-memory-mcp 0.11.0"; exit; }\n'
               + LOGGING_TOOL.split("\n", 1)[1])
    write_tool(home / ".bun" / "bin", "bun", "#!/bin/sh\necho 1.4.2\n")
    # the real `claude` writes the marketplace path into the committed settings; so does this one
    write_tool(tmp_path / "bin", "claude", LOGGING_TOOL + 'echo scribbled > "$PWD/.claude/settings.json"\n')
    write_tool(tmp_path / "bin", "gh", '#!/bin/sh\nexit 1\n')
    # uv logs where it was asked to sync into, and leaves an interpreter there as the real one does
    write_tool(tmp_path / "bin", "uv", '#!/bin/sh\necho "uv $* env=$UV_PROJECT_ENVIRONMENT" >> "$TOOL_LOG"\n'
               '[ -n "$UV_PROJECT_ENVIRONMENT" ] && mkdir -p "$UV_PROJECT_ENVIRONMENT/bin" '
               '&& printf "#!/bin/sh\\n" > "$UV_PROJECT_ENVIRONMENT/bin/python" '
               '&& chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"\nexit 0\n')
    env = {key: value for key, value in os.environ.items()
           if key not in ("CLAUDE_MEM_DATA_DIR", "CLAUDE_CONFIG_DIR", "CBM_BIN_DIR", "PROPS_HOME")}
    env.update(HOME=str(home), PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}", TOOL_LOG=str(tmp_path / "tools.log"))
    return home, env


def shell(repo, env, name):
    return subprocess.run(["bash", repo / ".claude" / "scripts" / name], env=env, capture_output=True, text=True)


def test_install_writes_claude_mem_settings_and_keeps_the_rest(scratch_repo, machine):
    home, env = machine
    mem = home / ".claude-mem"
    mem.mkdir()
    (mem / "settings.json").write_text(json.dumps({
        "MINE": "kept",
        "CLAUDE_MEM_PROJECT_ENVIRONMENTS": json.dumps([{"name": "other", "patterns": ["/x/**"]},
                                                       {"name": "score", "patterns": ["/old/**"]}])}))
    (mem / "telemetry.json").write_text(json.dumps({"installId": "abc", "enabled": True}))
    for _ in range(2):  # safe to re-run
        run = shell(scratch_repo, env, "install-agent-tools.sh")
        assert run.returncode == 0, run.stderr
    assert json.loads((mem / "settings.json").read_text()) == {
        "MINE": "kept",
        "CLAUDE_MEM_PROJECT_ENVIRONMENTS": [{"name": "other", "patterns": ["/x/**"]},
                                            {"name": "score", "patterns": [f"{scratch_repo}/**"]}],
        "CLAUDE_MEM_TELEMETRY": "0", "CLAUDE_MEM_TELEMETRY_ERRORS": "0", "CLAUDE_MEM_CHROMA_ENABLED": "false",
        "CLAUDE_MEM_FILE_READ_GATE_ENABLED": "false", "CLAUDE_MEM_CONTEXT_OBSERVATION_TYPES": "decision,bugfix",
        "CLAUDE_MEM_SKIP_SUBAGENT_OBSERVATIONS": "false"}
    telemetry = json.loads((mem / "telemetry.json").read_text())
    assert (telemetry["installId"], telemetry["enabled"]) == ("abc", False) and "decidedAt" in telemetry
    assert (home / ".claude" / ".ponytail-statusline-nudged").exists()
    assert "codebase-memory-mcp: 0.11.0 already installed" in run.stdout  # the pinned binaries: nothing downloaded
    assert "bun: 1.4.2 already installed" in run.stdout


def test_install_adds_the_plugin_and_puts_the_committed_settings_back(scratch_repo, machine, tmp_path):
    _, env = machine
    run = shell(scratch_repo, env, "install-agent-tools.sh")
    assert run.returncode == 0, run.stderr
    assert (scratch_repo / ".claude" / "settings.json").read_text() == '{"committed": true}\n'
    assert (tmp_path / "tools.log").read_text().splitlines() == [
        f"claude plugin marketplace add {scratch_repo}/vendor/claude-mem --scope project",
        "claude plugin install claude-mem@thedotmack --scope project",
        f"codebase-memory-mcp cli --quiet index_repository --repo-path {scratch_repo}"]


def test_bootstrap_links_memory_without_losing_any(scratch_repo, machine):
    home, env = machine
    target = home / ".claude" / "projects" / str(scratch_repo).replace("/", "-") / "memory"
    target.mkdir(parents=True)
    (target / "note.txt").write_text("an old memory")
    run = shell(scratch_repo, env, "bootstrap.sh")
    assert run.returncode == 0, run.stderr
    assert target.is_symlink() and target.resolve() == scratch_repo / ".claude" / "memory"
    assert (scratch_repo / ".claude" / "memory" / "note.txt").read_text() == "an old memory"
    assert len(list(target.parent.glob("memory.bak.*"))) == 1
    assert "memory: already linked" in shell(scratch_repo, env, "bootstrap.sh").stdout


def test_bootstrap_sets_the_hooks_and_builds_the_runtime_python_once(scratch_repo, machine, tmp_path):
    _, env = machine
    env["PROPS_HOME"] = str(tmp_path / "elsewhere")  # the cloud runner calls PROPS_HOME's env: a moved home moves it
    runtime = tmp_path / "elsewhere" / "env"
    run = shell(scratch_repo, env, "bootstrap.sh")
    assert run.returncode == 0, run.stderr
    assert git(scratch_repo, "config", "core.hooksPath") == ".githooks"
    assert "gh: installed but not logged in. Run: gh auth login" in run.stdout
    assert (runtime / "bin" / "python").exists()
    assert f"runtime python: already at {runtime}" in shell(scratch_repo, env, "bootstrap.sh").stdout
    syncs = [line for line in (tmp_path / "tools.log").read_text().splitlines() if line.startswith("uv ")]
    assert syncs == ["uv sync -q --frozen env=", f"uv sync -q --frozen --no-dev --project {scratch_repo} env={runtime}",
                     "uv sync -q --frozen env="]
