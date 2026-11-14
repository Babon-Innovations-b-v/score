"""The harness scripts change only what they own: gate-scope nothing (documents alone run no tests), board-status
only this repo's card, setup-github only this repo's labels, board and config (nothing on a dry run), worktree-reap only a dead session's clean merged worktree,
bootstrap only its own links and flags, ssh-agent.sh only its agent socket, its ~/.bashrc block and its
~/.ssh/config lines (GitHub's port 443 only when port 22 is refused), and sandbox-home and conftest.py keep every test off the real home while
removing everything a test leaves.

Every script is driven from outside as a copy in a scratch git repo (each finds its repo from its own path) on a
scratch machine: `gh`, `uv` and the ssh tools are stand-ins that log their calls, and HOME is a scratch folder, so
nothing runs against this machine. Each row of test_scripts_change_only_what_they_own is data: the machine it starts
from, the runs in order (a script, or a pytest or plain-script run of this repository's tests under the guard; the
worktrees laid out and folders made fresh before each), and what every run says and leaves; one body judges every
row alike. The expected answers are the scripts' rules, written out by hand here.

The break that turns each test red (applied once each, seen red, reverted):

- test_scripts_change_only_what_they_own, one row red per break: gate-scope's is_document's `BUILT_PREFIXES +
  CODE_PREFIXES` made `BUILT_PREFIXES` (a hook change runs nothing); or gate-scope's forced_reason's CI branch
  removed; or board-status's config()'s `here and repo and here != repo` made `False` (another repo's board); main's mutation sent with `o=options[0]["id"]` (moves the
  card); board_item's `node["project"]["number"] == number` made `True` (adds from another board); sync_labels
  creates a label even on a dry run; main keeps the template's backlog_prd (resets a template's config); "Review"
  taken out of STATUS_OPTIONS, or main's `config.get("owner") or owner` made `owner` (a re-run overwrites the
  hand-edited owner) (gives the board its columns).
- its worktree-reap row: is_clean returns True at once; or reap's
  `idle_hours(...) >= IDLE_HOURS` made `True` (a recent unlocked worktree is reaped); or main prints the report also
  when empty (the idle hook speaks); or (an env1 run's code worktree was reaped mid-run and while paused, 2026-10-31)
  reap's `or entry.name in in_use` dropped, held_by_processes returns `set()` (only the cwd and locked_cwd worktrees
  go), or named_by_runs returns `set()` (only registered and paused go).
- its sandbox-home row (owner's rule: tests use small fixtures, never the real store or home, 2026-10-28):
  sandbox-home's read_only_command drops `--ro-bind`; or run's `finally` drops `shutil.rmtree(temp, ...)`; or
  make_sandbox links the real home's work/ into the sandbox.
- its guard rows (the owner's rule that no test touches the real home, 2026-10-18), one guard row red per break:
  outside_temp's `folder == temp` test dropped; or pytest_configure's refusal skipped; or own_temp's `removed` holds
  only `[folder]`; or refuse_outside_sandbox's `if refusal:` made `if False:`.
- its bootstrap and ssh-agent rows: bootstrap moves the old memory folder aside
  without copying it; or its runtime build ignores PROPS_HOME; or
  ssh-agent.sh's `elif github_answers git@github.com` branch dropped (a box whose port 22 works gets the 443
  fallback); or its `grep -qF 'ssh/agent/agent.sock'` made `false` (a re-run writes the ~/.bashrc block twice); or
  use_repo_hooks' `config score.movedCheck true` dropped (the push gate's re-buy check stays off).

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest .claude/scripts/tests/
"""
import glob
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
# uv logs where it was asked to sync into, and leaves an interpreter there as the real one does
FAKE_UV = ('#!/bin/sh\necho "uv $* env=$UV_PROJECT_ENVIRONMENT" >> "$TOOL_LOG"\n'
           '[ -n "$UV_PROJECT_ENVIRONMENT" ] && mkdir -p "$UV_PROJECT_ENVIRONMENT/bin" '
           '&& printf "#!/bin/sh\\n" > "$UV_PROJECT_ENVIRONMENT/bin/python" '
           '&& chmod +x "$UV_PROJECT_ENVIRONMENT/bin/python"\nexit 0\n')
# ssh-agent, ssh-add, ssh-keygen and ssh: the agent is a file at its socket, its keys a file beside it; ssh logs its
# call and answers as GitHub does, port 22 as FAKE_SSH_22 says, port 443 always.
FAKE_SSH = {
    "ssh-agent": '#!/bin/sh\n[ "$1" = -a ] && : > "$2"\n',
    "ssh-add": ('#!/bin/sh\n[ -e "$SSH_AUTH_SOCK" ] || exit 2\n'
                'if [ "$1" = -l ]; then [ -s "$SSH_AUTH_SOCK.keys" ] && cat "$SSH_AUTH_SOCK.keys" && exit 0; '
                'echo "The agent has no identities."; exit 1; fi\n'
                'echo "256 SHA256:fake $1 (ED25519)" >> "$SSH_AUTH_SOCK.keys"\n'),
    "ssh-keygen": '#!/bin/sh\necho "256 SHA256:fake tester (ED25519)"\n',
    "ssh": ('#!/bin/sh\necho "ssh $*" >> "$TOOL_LOG"\n'
            'case "$*" in *"-p 443"*) ok=ok ;; *) ok="$FAKE_SSH_22" ;; esac\n'
            '[ "$ok" = ok ] || { echo "git@github.com: Permission denied (publickey)." >&2; exit 255; }\n'
            'echo "Hi tester! You\'ve successfully authenticated, but GitHub does not provide shell access." >&2\n'
            'exit 1\n'),
}


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
def machine(tmp_path):
    """A scratch machine: a git repo holding the scripts committed (then one empty commit) with a project.json for
    acme/widget, a HOME, and the gh, uv and ssh stand-ins first on PATH."""
    repo = tmp_path / "repo"
    shutil.copytree(SCRIPTS, repo / ".claude" / "scripts", ignore=shutil.ignore_patterns("tests"))
    (repo / ".claude" / "settings.json").write_text('{"committed": true}\n')
    (repo / ".claude" / "project.json").write_text(json.dumps({"repo": "acme/widget"}) + "\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "remote", "add", "origin", "git@github.com:acme/widget.git")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "scripts")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "second")
    (tmp_path / "home" / ".claude").mkdir(parents=True)
    write_tool(tmp_path / "bin", "gh", FAKE_GH.format(python=sys.executable))
    write_tool(tmp_path / "bin", "uv", FAKE_UV)
    for name, body in FAKE_SSH.items():
        write_tool(tmp_path / "bin", name, body)
    env = {key: value for key, value in os.environ.items()
           if key not in ("CI", "GATE_FULL", "CLAUDE_HOOK", "CLAUDE_CONFIG_DIR")}
    env.update(HOME=str(tmp_path / "home"), PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
               FAKE_GH_ANSWERS=str(tmp_path / "gh-answers.json"), FAKE_GH_LOG=str(tmp_path / "gh-log.jsonl"),
               TOOL_LOG=str(tmp_path / "tools.log"))
    return repo, env


def fill(value, where):
    """Every {name} of where in a row's strings, at any depth, made the scratch machine's path."""
    if isinstance(value, str):
        for name, text in where.items():
            value = value.replace("{" + name + "}", text)
        return value
    if isinstance(value, (list, tuple)):
        return type(value)(fill(item, where) for item in value)
    if isinstance(value, dict):
        return {fill(key, where): fill(item, where) for key, item in value.items()}
    return value


# A gh call is a write unless it is one of these reads, so a write the rows do not expect, of any kind, turns its row
# red. gate-scope reads the change against origin/main and asks nothing of GitHub: documents alone run nothing;
# anything else, and every doubt, runs everything.

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


def run(command, environ=None, add=(), succeeds=True, said="", unsaid=(), fresh=(), stop_when=None):
    """One run: a script of the scripts folder, or ("python", ...) this Python in the repository; the worktrees laid
    out and the folders made fresh and empty just before it, its extra environment (None unsets a variable), its exit
    (True: 0, False: not 0, a number: that one), what it says (a str: the whole stdout; a dict: stdout as JSON; a
    list: fragments of stdout, or of stderr when it fails) and never says, and the file whose writing stops it
    (SIGTERM)."""
    return {"command": command, "environ": environ or {}, "add": add, "succeeds": succeeds, "said": said,
            "unsaid": unsaid, "fresh": fresh, "stop_when": stop_when}


def case(name, *runs, config=None, changed=None, gh=None, home=None, scripts_in="{repo}", asks_gh=False, writes=(),
         after=None, tools=None, files=(), git_config=None, branches=None):
    """A row: project.json before (None: acme/widget's), the paths changed since origin/main (None: no origin/main),
    gh's answers, files seeded in HOME, where the scripts sit (a folder outside any git repo, or the repo), the runs
    in order; then whether gh was asked at all, its writes in order, project.json after (None: unchanged), the
    stand-in tools' logged lines by prefix, the files left (True: there; False: gone; ("text", t), ("count", part,
    n), ("link", target), ("matches", n) for a glob), git config values and which branches remain."""
    return {"id": name, "runs": runs, "config": config, "changed": changed, "gh": gh or {}, "home": home or {},
            "scripts_in": scripts_in, "asks_gh": asks_gh, "writes": list(writes), "after": after,
            "tools": tools or {}, "files": files, "git_config": git_config or {}, "branches": branches or {}}


def gate(name, changed, command, environ, said):
    """A gate-scope row: the paths changed since origin/main (None: no origin/main), its environment, its answer."""
    return case(name, run(["gate-scope.py", *command], environ, said=said), changed=changed)


def tree(name, lock=None, at="HEAD~1", dirty=False, local_commit=False, idle=False, held=False, named_by=None):
    """A worktree: locked by a session alive or dead, its commit, unsaved work, a commit of its own, untouched for a
    day, a process working in it, and the this-PC run whose record names it (running, finished, paused)."""
    return {"name": name, "lock": lock, "at": at, "dirty": dirty, "local_commit": local_commit, "idle": idle,
            "held": held, "named_by": named_by}


THIS_PC = {"SCORE_THIS_PC_HOME": "{tmp}/this-pc"}
HOOK = {**THIS_PC, "CLAUDE_HOOK": "SessionStart"}
REAPED = ("gone", "idle", "finished", "gone_later")
LEFT = ("dirty", "unmerged", "live", "kept", "idle_dirty", "cwd", "locked_cwd", "registered", "paused")
DIRTY_LEFT = "Left 2 stale-locked worktree(s) with uncommitted work: dirty, unmerged. Recover or discard by hand."
PROBE = "ssh -T -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8"
MEMORY = "{home}/.claude/projects/{project}/memory"
FALLBACK = "Host github.com\n  HostName ssh.github.com\n  Port 443\n  User git\n"
KEY = {".ssh/id_ed25519": "key", ".ssh/id_ed25519.pub": "ssh-ed25519 AAAA tester"}


def ssh_agent(port_22, probes, fallbacks):
    """ssh-agent.sh run twice on a home holding a key, GitHub's port 22 answering as port_22 says."""
    return case(
        f"ssh-agent with port 22 {port_22}",
        run(["ssh-agent.sh"], {"FAKE_SSH_22": port_22}, said=["ssh-agent: key loaded"]),
        run(["ssh-agent.sh"], {"FAKE_SSH_22": port_22}, said=["ssh-agent: key already loaded"]),
        home=KEY, tools={"ssh -T": probes},
        files=[("{home}/.ssh/agent/agent.sock", True),
               ("{home}/.bashrc", ("count", 'SSH_AUTH_SOCK="$HOME/.ssh/agent/agent.sock"', 1)),
               ("{home}/.ssh/config", ("count", "AddKeysToAgent yes", 1)),
               ("{home}/.ssh/config", ("count", FALLBACK, fallbacks))])


CASES = [
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
    case("board-status usage",
         run(["board-status.py", "7"], succeeds=False, said=["board-status.py <issue-number> <status>"])),
    case("board-status refuses another repo's board",
         run(["board-status.py", "7", "Done"], succeeds=False,
             said=["names template/origin but this checkout is acme/widget"]),
         config={"repo": "template/origin", "project": {"number": 3}}),
    case("board-status needs a board",
         run(["board-status.py", "7", "Done"], succeeds=False, said=["setup-github.py --board"]),
         config={"repo": "acme/widget", "project": {"number": 0}}),
    case("board-status refuses an unknown column",
         run(["board-status.py", "7", "Doing"], succeeds=False,
             said=["unknown status 'Doing'; board columns: Not started, Done"]),
         config=BOARD, gh={"project field-list": {"stdout": json.dumps(FIELDS)}}, asks_gh=True),
    case("board-status moves the card on its board", run(["board-status.py", "7", "Done"], said="#7 -> Done\n"),
         config=BOARD, gh={"project field-list": {"stdout": json.dumps(FIELDS)}, "graphql query": on_board(3),
                           "graphql mutation": {"stdout": json.dumps({"data": {}})}},
         asks_gh=True, writes=[["mutation", {"p": "P1", "i": "ITEM", "f": "F1", "o": "O2"}]]),  # Done on board 3
    # the stand-in answers every query alike, so after item-add the issue is still only on board 9
    case("board-status adds a card from another board first",
         run(["board-status.py", "7", "Done"], succeeds=False, said=["#7 could not be added to board #3"]),
         config=BOARD, gh={"project field-list": {"stdout": json.dumps(FIELDS)}, "graphql query": on_board(9)},
         asks_gh=True,
         writes=[["project", "item-add", "3", "--owner", "acme", "--url", "https://github.com/acme/widget/issues/7"]]),
    case("setup-github needs a login", run(["setup-github.py"], succeeds=False, said=["gh auth login"]),
         gh={"auth status": {"exit": 1}}, asks_gh=True),
    case("setup-github dry run changes nothing",
         run(["setup-github.py", "--dry-run", "--board"],
             said=["would update label bug", "would create label PRD",
                   "would create a project on acme and link it to acme/widget"]),
         gh={"repo view": REPO_VIEW, "label list": {"stdout": json.dumps([{"name": "bug"}])}}, asks_gh=True),
    case("setup-github resets a template's config",
         run(["setup-github.py"], said=["config came from template/origin; resetting board, backlog and people"]),
         config={"repo": "template/origin", "project": {"number": 4, "owner": "template"}, "backlog_prd": 12,
                 "people": {"someone": "someone"}, "areas": ["paper"]},
         gh={"repo view": REPO_VIEW, "label list": {"stdout": "[]"}}, asks_gh=True, writes=LABELS_MADE,
         after={"repo": "acme/widget", "owner": "acme", "project": {"number": 0, "owner": ""}, "backlog_prd": None,
                "people": {"acme": "acme"}, "areas": ["paper"]}),
    # a re-run in the same repo keeps the hand-edited owner; Roadmap start was there already
    case("setup-github gives the board its columns and fields", run(["setup-github.py", "--board"], said=[]),
         config={"repo": "acme/widget", "owner": "someone", "areas": ["paper"]},
         gh={"repo view": REPO_VIEW, "label list": {"stdout": "[]"},
             "project list": {"stdout": json.dumps({"projects": [
                 {"title": "widget", "closed": False, "number": 5, "url": "https://example.test/5"}]})},
             "project view": {"stdout": json.dumps({"id": "PROJ"})},
             "project field-list": {"stdout": json.dumps({"fields": [
                 {"id": "F1", "name": "Status", "options": [{"name": "Todo"}]}, {"id": "F2", "name": "Roadmap start"}]})},
             "graphql mutation": {"stdout": json.dumps({"data": {}})}},
         asks_gh=True,
         writes=LABELS_MADE + [["mutation", {"f": "F1", "o": COLUMNS}], ["mutation", {"p": "PROJ", "n": "Roadmap end"}],
                               ["mutation", {"p": "PROJ", "o": [{"name": "paper", "color": "BLUE",
                                                                 "description": "paper"}]}],
                               ["project", "link", "5", "--owner", "acme", "--repo", "acme/widget"]],
         after={"repo": "acme/widget", "owner": "someone", "areas": ["paper"], "people": {"acme": "acme"},
                "project": {"number": 5, "owner": "acme"}}),
    # worktree-reap: only a dead session's clean, merged worktree goes. One checkout holding a worktree of every
    # kind, reaped three times: as a hook with nothing to say, by hand, and as a hook again after one more session
    # died. origin/main is the second commit; every worktree but paused sits on the first.
    case("worktree-reap reaps only a dead session's clean merged worktree",
         run(["worktree-reap.py"], HOOK, add=[tree("live", lock="live")], said=""),  # a quiet hook says nothing
         run(["worktree-reap.py"], THIS_PC, add=[
             tree("gone", lock="dead"),
             tree("dirty", lock="dead", dirty=True),
             tree("unmerged", lock="dead", local_commit=True),
             tree("kept"),  # unlocked but touched just now: a finished agent's, kept for IDLE_HOURS
             tree("idle", idle=True),  # unlocked, clean, merged and untouched for a day: reaped
             tree("idle_dirty", dirty=True, idle=True),  # unlocked and old but holding work: never touched
             tree("cwd", idle=True, held=True),  # a process works in it (the run's leader, its venv's Python)
             tree("locked_cwd", lock="dead", held=True),  # its session is dead, a process it started is not
             tree("registered", idle=True, named_by="running"),  # a running this-PC run's registry entry names it
             tree("finished", idle=True, named_by="finished"),  # only a finished run's entry names it: reaped
             tree("paused", at="HEAD", idle=True, named_by="paused")],  # checked out at the paused run's commit
             said=f"Reaped 3 orphaned worktree(s): finished, gone, idle. {DIRTY_LEFT}\n"),
         run(["worktree-reap.py"], HOOK, add=[tree("gone_later", lock="dead")],  # off the paused run's commit
             said={"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
                                          f"Reaped 1 orphaned worktree(s): gone_later. {DIRTY_LEFT}"}}),
         changed=set(),
         files=[(f"{{repo}}/.claude/worktrees/{name}", name in LEFT) for name in REAPED + LEFT],
         branches={"worktree-gone": False, "worktree-gone_later": False, "worktree-dirty": True,
                   "worktree-unmerged": True, "worktree-live": True, "worktree-kept": True}),
    case("worktree-reap outside a git repo does nothing",
         run(["worktree-reap.py"], {"GIT_CEILING_DIRECTORIES": "{tmp}"}, said=""), scripts_in="{tmp}/alone"),
    # bootstrap.sh run twice on a scratch HOME that already holds a memory folder; the cloud runner calls
    # PROPS_HOME's env, so a moved home moves it
    case("bootstrap links, flags and builds only its own",
         run(["bootstrap.sh"], {"PROPS_HOME": "{tmp}/elsewhere"},
             said=["gh: installed but not logged in. Run: gh auth login",
                   "ssh-agent: no ~/.ssh/id_ed25519"]),  # no key: nothing of ~/.ssh is touched
         run(["bootstrap.sh"], {"PROPS_HOME": "{tmp}/elsewhere"},
             said=["memory: already linked", "runtime python: already at {tmp}/elsewhere/env"]),
         gh={"auth status": {"exit": 1}}, home={".claude/projects/{project}/memory/note.txt": "an old memory"},
         asks_gh=True,
         tools={"uv ": ["uv sync -q --frozen env=",
                        "uv sync -q --frozen --no-dev --project {repo} env={tmp}/elsewhere/env",
                        "uv sync -q --frozen env="], "ssh -T": []},
         files=[(MEMORY, ("link", "{repo}/.claude/memory")),
                ("{repo}/.claude/memory/note.txt", ("text", "an old memory")),
                (MEMORY + ".bak.*", ("matches", 1)),
                ("{tmp}/elsewhere/env/bin/python", True),
                ("{home}/.ssh", False), ("{home}/.bashrc", False)],
         git_config={"core.hooksPath": ".claude/hooks", "score.movedCheck": "true"}),
    ssh_agent("refused", [f"{PROBE} git@github.com", f"{PROBE} -p 443 git@ssh.github.com"], 1),  # 443 tried, kept
    ssh_agent("ok", [f"{PROBE} git@github.com", f"{PROBE} git@github.com"], 0),  # 22 works: 443 never tried
]


def dead_pid():
    child = subprocess.Popen(["true"])
    child.wait()
    return child.pid


def lay_out(repo, spec, this_pc, held):
    """Add one worktree as its spec says; a process working in it joins held."""
    path = repo / ".claude" / "worktrees" / spec["name"]
    git(repo, "worktree", "add", "-q", "-b", f"worktree-{spec['name']}", str(path), spec["at"])
    if spec["lock"]:
        pid = os.getpid() if spec["lock"] == "live" else dead_pid()
        git(repo, "worktree", "lock", "--reason", f"claude agent {spec['name']} (pid {pid} start 1)", str(path))
    if spec["dirty"]:
        (path / "work.txt").write_text("unsaved")
    if spec["local_commit"]:
        git(path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local")
    if spec["idle"]:  # its git admin files a day old, past IDLE_HOURS
        admin = pathlib.Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "worktrees"
        for part in (admin / spec["name"]).rglob("*"):
            if part.is_file():
                os.utime(part, (time.time() - 86400, time.time() - 86400))
    if spec["held"]:
        held.append(subprocess.Popen(["sleep", "60"], cwd=path))
    if spec["named_by"] == "paused":
        this_pc.mkdir(parents=True, exist_ok=True)
        (this_pc / "paused.json").write_text(json.dumps({"commit": git(path, "rev-parse", "HEAD"), "argv": ["run"]}))
    elif spec["named_by"]:
        (this_pc / "runs").mkdir(parents=True, exist_ok=True)
        (this_pc / "runs" / f"{spec['name']}.json").write_text(
            json.dumps({"state": spec["named_by"], "worktree": str(path.resolve())}))


# sandbox-home and conftest.py: no test reaches the real home, and what a test leaves goes with its sandbox
# (a test unlinked the real cloud ledger, 2026-10-17; the tests' temp stores took every inode of /tmp, 2026-10-25).
# Their rows run in the same scratch machine: HOME stands in for the real home, and {tmp}/temps is the temp folder
# the runs are given, so a store or home left behind is a file left there.

BUBBLEWRAP = shutil.which("bwrap") is not None
REAL_HOME = {"work/seed.txt": "seed", "cloud/ledger.jsonl": "{}\n"}  # world data and state
SANDBOXED = {"SCORE_REAL_HOME": "{home}", "TMPDIR": "{tmp}/temps"}
# a test that looks at its home (empty but for its store, nothing of the real home linked), writes there, and leaves
# a temp folder and read-only files
LOOKS = ("import os, pathlib, tempfile; home = pathlib.Path(os.environ['PROPS_HOME']);"
         "listing = ' '.join(sorted(str(path.relative_to(home)) + ('@' if path.is_symlink() else '')"
         " for path in home.rglob('*')));"
         "assert not (home / 'cloud').exists();"
         "(home / 'cloud').mkdir(); (home / 'cloud' / 'ledger.jsonl').write_text('mine');"
         "(home / 'store-tests').mkdir(); (home / 'store-tests' / 'kept').write_text('x');"
         "os.chmod(home / 'store-tests' / 'kept', 0o444); os.chmod(home / 'store-tests', 0o555);"
         "left = pathlib.Path(tempfile.mkdtemp()); (left / 'kept').write_text('x');"
         "assert home.parent == pathlib.Path(tempfile.gettempdir()), home; print(listing)")
WRITES_THROUGH = "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('gone')"
WAITS = "import os, pathlib, sys, time; pathlib.Path(sys.argv[1]).write_text(os.environ['TMPDIR']); time.sleep(60)"

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
UNGUARDED = {name: None for name in GUARDED}
REAL_PROPS = str(pathlib.Path.home() / ".farm-factory-props")
SYSTEM = str(module(REPO / "conftest.py", "repo_conftest").system_temp())
TARGET = str(pathlib.Path(__file__).relative_to(REPO))
COLLECT = ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only", TARGET]
# a plain script's first step, then the stores it leaves behind in its temp folder
LEAVES = ("import pathlib, runpy, sys, tempfile;"
          f"runpy.run_path({str(REPO / 'conftest.py')!r})['refuse_outside_sandbox']();"
          "left = pathlib.Path(tempfile.mkdtemp()) / 'store'; left.mkdir(); (left / 'object').write_text('x');"
          "(left / 'object').chmod(0o444); left.chmod(0o555); pathlib.Path(sys.argv[1]).write_text(str(left))")


def outside(name, value):
    return f"{name}={value} is not a folder of its own inside {SYSTEM}"


def guard(name, guarded, refusal):
    """A guard row: a pytest run of this file, then a plain script's first step, each with these guarded variables
    ({tmp}/sandbox: a fresh, empty folder in the temp folder) and nothing else of them; refused (the refusal) or run
    (None), and a run removes its stores and its empty home."""
    environ = {**UNGUARDED, **guarded, "TMPDIR": "{tmp}/temps"}
    sandbox = ["{tmp}/sandbox"]
    if refusal is None:
        return case(f"guard: {name}", run(COLLECT, environ, fresh=sandbox, said=[pathlib.Path(TARGET).stem]),
                    run(["python", "-c", LEAVES, "{tmp}/left.txt"], environ, fresh=sandbox, said=[]),
                    files=[("{tmp}/left.txt", True), ("{tmp}/temps/*", ("matches", 0)), ("{tmp}/sandbox", False)])
    told = [f"refused: {refusal}. Tests run in a sandbox home"]
    return case(f"guard: {name}",
                run(COLLECT, environ, fresh=sandbox, succeeds=4, said=told, unsaid=[pathlib.Path(TARGET).stem]),
                run(["python", "-c", LEAVES, "{tmp}/left.txt"], environ, fresh=sandbox, succeeds=False, said=told),
                files=[("{tmp}/left.txt", False)])


PLAIN = plain_script_tests()
CASES += [
    # Fault (2026-10-28): the sandbox linked the real home's design/plans and work/, so tests leaned on real data
    # unnoticed. One sandboxed test looks and writes; one tries to write the real home (only bubblewrap can mount it
    # read-only); one is stopped mid-run, as a stopped make or a closed terminal does.
    case("sandbox-home runs a test in an empty home of its own and removes all it leaves",
         run(["sandbox-home.py", "--", sys.executable, "-c", LOOKS], SANDBOXED, said="store store/cache\n"),
         *([run(["sandbox-home.py", "--", sys.executable, "-c", WRITES_THROUGH, "{home}/work/seed.txt"], SANDBOXED,
                succeeds=False, said=["Read-only file system"])] if BUBBLEWRAP else []),
         run(["sandbox-home.py", "--", sys.executable, "-c", WAITS, "{tmp}/temp.txt"], SANDBOXED, succeeds=False,
             stop_when="{tmp}/temp.txt"),
         home=REAL_HOME,
         files=[("{home}/work/seed.txt", ("text", "seed")), ("{home}/cloud/ledger.jsonl", ("text", "{}\n")),
                ("{tmp}/temp.txt", True), ("{tmp}/temps/*", ("matches", 0))]),
    # Faults: a test unlinked the real cloud ledger (2026-10-17); conftest.py covered pytest runs only, so 146 of 149
    # plain-script tests ran by hand against the real home (2026-10-18 review); 529 stores were left in /tmp by test
    # files run by hand with PROPS_HOME=$(mktemp -d) (2026-10-26).
    guard("no home", {}, "PROPS_HOME is not set"),
    guard("the real home", {"PROPS_HOME": REAL_PROPS}, outside("PROPS_HOME", REAL_PROPS)),
    guard("the system temp", {"PROPS_HOME": SYSTEM}, outside("PROPS_HOME", SYSTEM)),
    guard("the root", {"PROPS_HOME": "/"}, outside("PROPS_HOME", "/")),
    guard("a sandbox", {"PROPS_HOME": "{tmp}/sandbox"}, None),
    guard("work in the real home", {"PROPS_HOME": "{tmp}/sandbox", "PROPS_WORK": str(pathlib.Path.home())},
          outside("PROPS_WORK", pathlib.Path.home())),
    guard("work in the sandbox", {"PROPS_HOME": "{tmp}/sandbox", "PROPS_WORK": "{tmp}/sandbox/work"}, None),
    # kept.py and preflight.py prefer the real store
    guard("the real spend store", {"PROPS_HOME": "{tmp}/sandbox", "SCORE_SPEND_STORE": f"{REAL_PROPS}/store"},
          outside("SCORE_SPEND_STORE", f"{REAL_PROPS}/store")),
    guard("a sandbox spend store", {"PROPS_HOME": "{tmp}/sandbox", "SCORE_SPEND_STORE": "{tmp}/sandbox/store"}, None),
    # every plain-script test refuses first; one run by hand with no home is refused before it reaches a scratch home
    case("guard: every plain-script test run by hand",
         run(["python", str(PLAIN[0])], {**UNGUARDED, "HOME": "{tmp}"}, succeeds=False,
             said=["refused: PROPS_HOME is not set"]),
         files=[(str(path), ("guarded",)) for path in PLAIN]),
]


def holds(path, expected):
    """Whether the file at path is as a row expects it."""
    if isinstance(expected, bool):
        return pathlib.Path(path).exists() == expected
    kind, *values = expected
    if kind == "matches":
        return len(glob.glob(path)) == values[0]
    if kind == "link":
        return pathlib.Path(path).is_symlink() and pathlib.Path(path).resolve() == pathlib.Path(values[0])
    text = pathlib.Path(path).read_text()
    if kind == "guarded":  # a plain-script test: its first step after its imports refuses outside a sandbox
        block = text.split(MAIN_BLOCK, 1)[1].splitlines()[1:]
        first = next(line for line in block if not line.strip().startswith("import "))
        if first.strip().startswith("sys.exit(pytest.main("):
            return True  # a pytest run: conftest.py refuses it
        # inline or through a conftest loaded before (a wrong path to it fails loudly, not silently)
        return "refuse_outside_sandbox" in first and '"conftest.py"' in text
    return text == values[0] if kind == "text" else text.count(values[0]) == values[1]


def stopped(argv, environ, when):
    """argv run until it has written the file `when`, then stopped as a closed terminal stops it (SIGTERM)."""
    # its output to files, not pipes: a command it started under bubblewrap may outlive it holding them
    told = [when.with_name(when.name + part) for part in (".out", ".err")]
    with told[0].open("w") as stdout, told[1].open("w") as stderr:
        running = subprocess.Popen(argv, env=environ, stdout=stdout, stderr=stderr)
        try:
            deadline = time.time() + 20
            while not (when.exists() and when.read_text()) and time.time() < deadline:
                time.sleep(0.05)
            running.terminate()
            running.wait(20)
        finally:
            running.kill()
    return subprocess.CompletedProcess(argv, running.returncode, *(path.read_text() for path in told))


@pytest.mark.parametrize("row", CASES, ids=[row["id"] for row in CASES])
def test_scripts_change_only_what_they_own(machine, tmp_path, row):
    repo, env = machine
    home = pathlib.Path(env["HOME"])
    row = fill(row, {"repo": str(repo), "home": str(home), "tmp": str(tmp_path),
                     "project": str(repo).replace("/", "-")})
    (tmp_path / "temps").mkdir()
    if row["changed"] is not None:  # origin/main is the scratch repo's HEAD, and each path is changed on top of it
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        for name in row["changed"]:
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            with (repo / name).open("a") as changing:
                changing.write("\n")
    config = repo / ".claude" / "project.json"
    if row["config"] is not None:
        config.write_text(json.dumps(row["config"]))
    kept = config.read_text()
    for name, text in row["home"].items():
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_text(text)
    pathlib.Path(env["FAKE_GH_ANSWERS"]).write_text(json.dumps(row["gh"]))
    scripts = pathlib.Path(row["scripts_in"]) / ".claude" / "scripts"
    if not scripts.exists():
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("tests"))
    held = []
    try:
        for step in row["runs"]:
            for spec in step["add"]:
                lay_out(repo, spec, tmp_path / "this-pc", held)
            for folder in step["fresh"]:
                shutil.rmtree(folder, ignore_errors=True)
                os.makedirs(folder)
            name, *args = step["command"]
            argv = ([sys.executable, *args] if name == "python"
                    else ["bash" if name.endswith(".sh") else "python3", scripts / name, *args])
            environ = {key: value for key, value in {**env, **step["environ"]}.items() if value is not None}
            if step["stop_when"]:
                ran = stopped(argv, environ, pathlib.Path(step["stop_when"]))
            else:
                ran = subprocess.run(argv, cwd=REPO if name == "python" else None, env=environ, capture_output=True,
                                     text=True)
            said, succeeds = step["said"], step["succeeds"]
            exited = (ran.returncode == 0) == succeeds if isinstance(succeeds, bool) else ran.returncode == succeeds
            assert exited, (step["command"], ran.returncode, ran.stdout + ran.stderr)
            if isinstance(said, str):
                assert ran.stdout == said, (step["command"], ran.stdout, ran.stderr)
            elif isinstance(said, dict):
                assert json.loads(ran.stdout) == said, ran.stderr
            for fragment in said if isinstance(said, list) else []:
                assert fragment in (ran.stdout if succeeds is True else ran.stderr), ran.stdout + ran.stderr
            for fragment in step["unsaid"]:
                assert fragment not in ran.stdout + ran.stderr, (step["command"], fragment)
    finally:
        for worker in held:
            worker.kill()
            worker.wait()
    log = pathlib.Path(env["FAKE_GH_LOG"])
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    assert bool(calls) == row["asks_gh"], calls
    assert [written(call) for call in calls if is_write(call)] == row["writes"]
    assert (json.loads(config.read_text()) == row["after"]) if row["after"] is not None else config.read_text() == kept
    tools = pathlib.Path(env["TOOL_LOG"])
    logged = tools.read_text().splitlines() if tools.exists() else []
    for prefix, lines in row["tools"].items():
        assert [line for line in logged if line.startswith(prefix)] == lines, prefix
    for path, expected in row["files"]:
        assert holds(path, expected), (path, expected)
    for key, value in row["git_config"].items():
        assert git(repo, "config", key) == value, key
    branches = set(git(repo, "branch", "--format=%(refname:short)").split())
    for branch, there in row["branches"].items():
        assert (branch in branches) == there, branch
