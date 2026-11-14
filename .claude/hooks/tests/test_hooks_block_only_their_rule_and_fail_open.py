r"""The hooks block exactly what their rule names, let everything else through, and fail open on what they cannot read.

Every hook is driven as the harness drives it: its own script, the payload as JSON on stdin; a PreToolUse or Stop
guard blocks with exit 2 and a reason on stderr, allows with exit 0. Each case's answer is the rule's, worked out by
hand from the hook's docstring and the owner rule it guards, never from the hook's code. The shared hooks (the ones
every repository built from this template carries) run as a copy in a scratch repo with its own project.json, so no
test reads or edits the real config, the real checkout or its state folder; this repository's own hooks
(.claude/hooks/local) run in place.

The break that turns each test red (applied once each, seen red, reverted):

- test_hooks_block_only_their_rule_and_fail_open, one row per call a hook answers from the call and its world alone:
  - its accept_guard rows: `_owner_area_write` returns None at once. Drop `if _FRAMEWORK.search(path): return None`;
    or drop the `not _TEXT_FILE.search(path)` in `_file_offence`. Add `grant_benchmark` to `_OWNER_CALL`'s names. In
    `_owner_command`, `not _YES_ID.match(...)` -> `False`; or drop the `_LOCK_CALL` check; or drop `spend_override|`
    from `_LOCK_CALL` (his spend override called straight from Python passes); or drop
    `(owners_|write_)?google_month|set_books_figure|` from `_LOCK_CALL` (his Google month written straight from
    Python passes). `_YES_ID` made `^$` (every id refused), or drop `and not _DASHBOARD.search(path)` in
    `_file_offence`. The env-assignment group of `_REVIEW_RUN`, `_DECIDE_RUN` and `_WRITER` back to `(\S+=\S*\s+)*`
    (CodeQL py/redos: exponential on many `!== `; the hook hangs past the row's 20 s, the harness fails it open); or
    to `([^\s=]+=\s+)*` (an env-prefixed accept passes).
  - its completion_guard rows: `claimed` returns `set()` at once. Drop `or _NEGATION.search(sentence)` in `claimed`;
    or in `_says_all_done`, return `bool(re.search(every, sentence, re.IGNORECASE))` (any "all places" counts). Its
    as-listed rows (an incident, 2026-10-18: it imports score.stages, which needs pxr, so under the system python3 it
    crashed on every stop and blocked nothing): the local hooks list runs it with `python3`.
  - its torn_commit_guard rows: `sourced_shell_dirs` returns [] at once; or `blocks` returns False at once.
  - its leftover_guard rows: `session_worktree` returns None at once.
  - its soul_guard rows: `broken_rules` returns [] at once.
  - its call_efficiency rows: `is_single_fast` returns False at once.
  - its checkout_current rows: `catch_up` returns "" at once.
  - its output_cap rows: `text_excerpt`'s `if matches:` made `if False:`; or `leave_alone` returns False at once; or
    `capped_output`'s saving check made `if False:`.
  - its issue_guard rows: `_is_destructive_git` returns False at once. `_is_gh_issue_create` returns `"create" in`
    the joined tokens (a substring match, not adjacent tokens). `_areas` returns [] at once. `_open_roots` returns []
    at once; or `_check_duplicate` returns at once. `_check_dead_paths` returns at once; or `_check_size` returns at
    once; or `_check_edit_size` returns at once (an edit then grows an over-cap body unchecked).
  - its md_guard rows: the `tee` pattern taken out of `_SHELL_TARGETS`; or `_recent_typed_messages` returns `texts`
    (a yes 21 typed messages back is heard). `_approved` returns an empty set at once; or `_user_asked_for_markdown`
    returns False at once (the user's yes is never heard). Its timed rows: in `main`, ask `_user_asked_for_markdown`
    before `not offenders` (a non-md call reads the transcript: it hangs on the pipe); or `_recent_typed_messages`
    starts with `chunk = size` (the whole transcript read, over 100 ms).
  - its commit_guard rows: `bypass_in` returns None at once. `live_session_worktrees` returns [] at once.
    `is_git_commit` returns `"commit" in tokens` (any word).
  - its wait_guard rows: `poll_loop` returns None at once; or `_foreground_runs` returns [] at once; or `tail_follow`
    returns None at once; or `long_timeout` returns None at once. Drop the `_MESSAGE.sub` in `blocked`; or drop
    `seconds > LONGEST_SLEEP and` in `long_timeout`; or `_TAIL_FOLLOW`'s flag group made `\\S+` (a tail -n blocked).
  - its push-gate rows (.claude/hooks/local/pre-push, in a scratch clone): `gate`'s `if rule.returncode != 0` block
    dropped (a grown debt file pushes); `run_tests` returns True at once, or `touched_tests` returns ([], []) (a
    failing touched test pushes); `touched_tests`'s `gpu` made [] (a GPU module is run, not left to a run by hand);
    `main` returns 0 instead of handing the push lines to pre-push-moved; `main`'s `GIT_HOOK_ENV` pop dropped (the
    clean push's test file, a git-driving one here, then runs against the pushing repository's GIT_DIR); `checked`'s
    `.venv` link dropped (the push from a clone moved off it, checked in a copy, has no environment for its test).
  - its push-cap rows (.claude/hooks/pre-push and push_cap.py, in scratch repos): `claim`'s `len(today) >= cap` made
    `>` (a 7th push of a 6-a-day cap goes); `limit_for` takes the first entry instead of the latest started one (the
    later, lower limit never applies); the pre-push's `release` call dropped (a refused push keeps its slot);
    `never_reached_main` returns False at once (a push the remote refused keeps its slot); `main`'s `uncounted` check
    dropped (a release-only repository's push takes a slot), or `uncounted` returns True at once (every push passes
    uncounted).
  - its redo-guard rows (score.stages.moved and local/remake_freeze.py, in scratch repos): `remade_accepted` takes
    `row["places"]` for a file-moved row too (a place the file does not move in counts); `remakes_line` sums every
    row's euros, not the paid ones'; `main` returns 0 when `freeze` stands (an unnamed remade row pushes); `named`
    drops its `why.strip()` (a bare list names rows); `standing_freeze` returns None on an unreadable file (a broken
    freeze pushes).
  - its fail-open rows: accept_guard's `except Exception: return 0` made `return 2`.

Run: PROPS_HOME=$(mktemp -d) python3 -m pytest .claude/hooks/tests/
"""

import concurrent.futures
import functools
import json
import math
import os
import pathlib
import runpy
import shutil
import subprocess
import sys
import time

import pytest

HOOKS = pathlib.Path(__file__).resolve().parent.parent
REPO = HOOKS.parents[1]
BLOCK, ALLOW = 2, 0


def hook(name):
    """A hook's script: a shared hook sits in .claude/hooks, a repository's own in .claude/hooks/local."""
    shared = HOOKS / name
    return shared if shared.exists() else HOOKS / "local" / name


def run(script, payload, env=None, cwd=None, timeout=None):
    """(exit code, stderr, stdout) of a hook script (or a command line, as a list) given this payload (a dict as JSON,
    or raw text) on stdin."""
    argv = script if isinstance(script, list) else [sys.executable, str(script)]
    done = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd,
                          timeout=timeout,
                          input=payload if isinstance(payload, str) else json.dumps(payload))
    return done.returncode, done.stderr, done.stdout


def hook_copy(folder, name, config=None):
    """The shared hook `name` copied into a scratch repo at `folder`, with this project.json; its path. A guard that
    reads the files beside it (project.json, the repo it polices, a state folder) then reads the scratch ones."""
    hooks = folder / ".claude" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    shutil.copy(HOOKS / name, hooks)
    (folder / ".claude" / "project.json").write_text(json.dumps(config or {"repo": "acme/widget", "areas": []}))
    return hooks / name


def bash(command, background=False):
    return {"tool_name": "Bash", "tool_input": {"command": command, "run_in_background": background}}


# accept_guard: only the owner accepts, rejects, waives, spends or stops; the runner accepts by the gates.

OWNER_ACTIONS = [
    bash(".venv/bin/python -m score.review accept assembly@hangar abc123"),
    bash("cd wt && python3 -m score.review spend render@hub k1 4.5"),
    bash("python score/review/__main__.py accept a@b c"),
    bash(".venv/bin/python -m score.review reject assembly@hangar abc123 --reason x"),
    bash(".venv/bin/python -m score.review stop world1 680 --reason films"),
    bash("python -c 'from score.adapters.compute import guard; guard.set_line(s, \"w\", 9e9, \"\", 1, 2, 3)'"),
    bash("python -c 'from score import review; review.accept(store, \"a@b\", \"o\", \"me\")'"),
    bash(".venv/bin/python - <<EOF\nstore.write_accept('a@b', {})\nEOF"),
    # the store's owner folders by any shell route
    bash("echo '{}' > ~/.farm-factory-props/store/objects/stops/world1/1.json"),
    bash("rm -r store/objects/stops/world1"),
    bash("echo '{}' > ~/.farm-factory-props/store/objects/accepts/a@b/1.json"),
    bash("cp x.json $HOME/.farm-factory-props/store/objects/spend-yes/a@b/k.json"),
    bash("rm -r store/objects/accepts/assembly@hangar"),
    bash("mkdir -p objects/waivers/x && touch objects/waivers/x/y.json"),
    bash("cp c.json store/objects/clearances/render@hub/k1/1.json"),
    bash("echo '{}' > store/objects/rejects/a@b/1.json"),
    # the review of step 0 (2026-10-11): each of these got through
    bash(".venv/bin/python -c 'from score.review import accept; accept(store, \"a@b\", \"o\", \"me\")'"),
    bash(".venv/bin/python -c 'import score.review as r; r.accept(store, \"a@b\", \"o\", \"me\")'"),
    bash(".venv/bin/python -c 'from score.store import Store; Store.default().write_once(\"acc\"+\"epts/a@b/1.json\", {})'"),
    bash("python -m score.review \"accept\" a@b o"),
    bash("cd score/review && python __main__.py accept a@b o"),
    bash("uv run python -m score.review waive render@hub gate --reason x"),
    bash("git status; bash -c '.venv/bin/python -m score.review accept a@b o'"),
    bash("script -qc '.venv/bin/python -m score.review page a@b' /dev/null"),
    bash("cat > /tmp/do_it.py <<EOF\nfrom score import review\nreview.accept(store, 'a@b', 'o', 'me')\nEOF"),
    # taking Claude Code's mark off a process
    bash("env -u CLAUDECODE .venv/bin/python /tmp/x.py"),
    bash("unset CLAUDECODE; python3 /tmp/x.py"),
    bash("CLAUDECODE= .venv/bin/python /tmp/x.py"),
    bash("env -i PATH=$PATH .venv/bin/python /tmp/x.py"),
    # a grant by hand, and the owner's commands beside a grant
    bash("echo '{}' > ~/.farm-factory-props/store/objects/grants/benchmark/1.json"),
    bash("rm -r store/objects/grants/used"),
    bash("python -c 'from score.adapters import compute; compute.grant_benchmark(\"y\", \"q\", 5); "
         "review.accept(s, \"a@b\", \"o\", \"me\")'"),
    bash("SCORE_BENCHMARK_GRANT=x .venv/bin/python -m score.review spend render@hub k1 4.5"),
    bash("python -c 'store.write_once(\"grants/benchmark/1.json\", {})'"),
    # file tools and the artifact database
    {"tool_name": "Write", "tool_input": {"file_path": "/home/x/.farm-factory-props/store/objects/accepts/a@b/1.json"}},
    {"tool_name": "Edit", "tool_input": {"file_path": "/home/x/.farm-factory-props/store/objects/accepts/a@b/1.json"}},
    {"tool_name": "Write", "tool_input": {"file_path": "/h/store/objects/grants/benchmark/1.json", "content": "{}"}},
    {"tool_name": "Write", "tool_input": {"file_path": "/tmp/do_it.py",
                                          "content": "from score import review\nreview.accept(s, 'a', 'o')\n"}},
    {"tool_name": "Edit", "tool_input": {"file_path": "/tmp/x.py", "new_string": "os.environ.pop('CLAUDECODE')"}},
    {"tool_name": "Artifact", "tool_input": {"action": "write_db", "collection": "accepts", "doc_id": "assembly@hangar",
                                             "data": {"output": "o"}}},
    {"tool_name": "Artifact", "tool_input": {"action": "write_db", "db_op": "batch", "writes": [
        {"op": "set", "collection": "notes", "doc_id": "n1", "data": {}},
        {"op": "set", "collection": "store/x/accepts", "doc_id": "a@b", "data": {}}]}},
]

READ_AND_RUN = [
    bash(".venv/bin/python -m score.review page assembly@hangar"),
    bash("ls ~/.farm-factory-props/store/objects/accepts/"),
    bash("ls ~/.farm-factory-props/store/objects/stops/world1"),
    bash("cat ~/.farm-factory-props/store/objects/accepts/a@b/1.json"),
    bash("grep -n 'review.accept(' score/review/review_test.py"),
    bash(".venv/bin/python score/review/review_test.py"),
    bash("make check"),
    bash(".venv/bin/python -m score.stages run hangar garage"),
    # the review of step 0: any `>`, or the owner's words in an unrelated write, were blocked
    bash('grep -rn "accepts/" score 2>/dev/null'),
    bash("ls ~/.farm-factory-props/store/objects/accepts/ 2>&1 | head"),
    bash("git log > /tmp/x; echo spend-yes/"),
    bash("grep -c accept score/review/__init__.py > /tmp/count.txt"),
    {"tool_name": "Edit", "tool_input": {"file_path": "score/review/__init__.py"}},
    {"tool_name": "Edit", "tool_input": {"file_path": "/repo/score/review/review_test.py",
                                         "new_string": "review.accept(store, node, output, 'me')"}},
    # code edits and text that only mention the owner's words (owner, 2026-10-27: narrow it to his actual actions)
    bash("cd /tmp/wt-accept && .venv/bin/python -m pytest score/review/tests"),
    bash(".venv/bin/python -m pytest score/graph score/review -k 'accept or stop'"),
    bash("git commit -m 'review: a bought batch accepts; python -m score.review accept stays his'"),
    bash("cat > score/graph/tests/test_x.py <<EOF\nreview.accept(store, node, output, 'me')\nEOF"),
    {"tool_name": "Edit", "tool_input": {"file_path": "/repo/docs/bible.md",
                                         "new_string": "the runner calls `review.accept(store, node, output)`"}},
    {"tool_name": "Artifact", "tool_input": {"action": "read_db", "collection": "accepts"}},
    {"tool_name": "Artifact", "tool_input": {"action": "write_db", "collection": "notes", "doc_id": "n1",
                                             "data": {"text": "acceptance criteria, spend and waivers"}}},
]

GRANT_QUESTION = ("Confirm this standing rule: in a Claude Code session, I may ask you to approve a benchmark batch of "
                  "at most €20. It covers benchmarks only; anything else and anything over €20 still needs your "
                  "cockpit click.")
GRANTED = [  # the owner's standing rule of 2026-10-20: the session that asked him writes his yes and runs the batch
    bash(".venv/bin/python - <<'EOF'\nfrom score.adapters import compute\n"
         f"print(compute.grant_benchmark('Yes, approve it', {GRANT_QUESTION!r}, 12.0))\nEOF"),
    bash("SCORE_BENCHMARK_GRANT=20261020T120000.000000+0000 .venv/bin/python -m score run world1 --detach "
         "--place campgrounds --stage pixal"),
]
# Many `!== ` words are answered within the row's 20 s, never a hang the harness fails open; an env-prefixed accept
# stays blocked.
LONG_WORDS = bash("!== " * 40 + "x")
ENV_PREFIXED_ACCEPT = bash("A=1 B=x=y python -m score.review accept closeup@hub")


YES = "20261027T170000123456Z"
OWN_LOCKS_AND_STEPS = [
    bash(".venv/bin/python -m score.dashboard decide"),
    bash(".venv/bin/python -m score.dashboard decide 'accept closeup@hub'"),
    bash("python3 tools/cloud/this_pc.py decide accept"),
    bash("ssh -i ~/.ssh/score_conductor_agents score@1.2.3.4 'decide lock-film'"),
    bash("python -c 'from score.dashboard.pages import actions; actions.concept_pick(\"joey\", {\"place\": \"hub\"})'"),
    bash("python -c 'from score.dashboard.pages import films; films.film_locked(\"joey\", {\"film\": \"f\"})'"),
    bash("python -c 'from score.review import concepts; concepts.pick(s, \"hub\", \"sha\", \"joey\")'"),
    bash("python -c 'from score.review import web; web.spend_override(s, \"relight\", 4.0, \"joey\", \"why\")'"),
    bash("python -c 'from score.dashboard.pages import actions; actions.spend_override(\"joey\", {\"euros\": 4})'"),
    bash("ssh score@1.2.3.4 'decide spend relight'"),
    bash("python -c 'from score.review import web; web.google_month(0, by=\"joey\")'"),
    bash("python -c 'from score.adapters import compute; compute.write_google_month(0.0, \"joey\")'"),
    bash("python -c 'from score.dashboard.pages import actions; actions.set_books_figure(\"joey\", 0)'"),
    bash("ssh score@1.2.3.4 'decide google-month 2026-11'"),
    bash(f"python -c 'from score.dashboard.sync import chat_decisions as c; c.chat_decisions.apply(\"{YES}\")'"),
    bash("python -c 'from score.dashboard.sync import applying; applying.apply({\"kind\": \"decision\"}, s)'"),
    bash(f"python -c 'from score.review import web; web.decision_yes_spent(s, \"{YES}\", {{}})'"),
    bash("echo '{}' > ~/.farm-factory-props/dashboard/films/locked/env.json"),
    bash("cp x.json store/objects/concepts/hub/picks/1.json"),
    {"tool_name": "Write", "tool_input": {"file_path": "/tmp/lock.py",
                                          "content": "from score.dashboard.pages import films\nfilms.film_locked(u, p)\n"}},
]
CHAT_ROUTE = [
    bash(f".venv/bin/python -m score.dashboard decide {YES}"),
    bash(f"python3 tools/cloud/this_pc.py decide {YES}"),
    bash(f"ssh -i ~/.ssh/score_conductor_agents -o IdentitiesOnly=yes score@1.2.3.4 'decide {YES}'"),
    bash(".venv/bin/python -m score.dashboard decide-yes lock-film env 'Yes, lock it' 'Lock film env as shown?'"),
    bash("ssh score@1.2.3.4 \"decide-yes accept closeup@hub --output abc 'yes' 'Accept closeup@hub abc?'\""),
    bash("ssh score@1.2.3.4 \"decide-yes spend relight-hangar --euros 4 --purpose 'one relight' 'yes' 'EUR 4?'\""),
    bash("SCORE_THIS_PC_HOME=/home/x/run python3 tools/cloud/this_pc.py decide-yes google-month 2026-11 --euros 0 "
         "'EUR 0' 'Enter EUR 0 as the Google month for 2026-11?'"),
    bash("python3 -c 'from score.adapters import compute; compute.grant_benchmark(a, q, 5, google_month=0)'"),
    bash("SCORE_OWNERS_GO=20261027T170000Z python3 tools/cloud/this_pc.py env1"),
    bash("SCORE_SPEND_TICKET='override relight-hangar' .venv/bin/python -m score.stages run hangar"),
    bash("git commit -m 'sync: python -m score.dashboard decide <yes id> applies it'"),
    {"tool_name": "Write", "tool_input": {"file_path": "/repo/score/dashboard/sync/chat_decisions.py",
                                          "content": "applying.apply(request, source)\n"}},
]


# completion_guard: a stop may not claim a place it worked on is done while the place's gate does not pass.

PLACE = "zz_test_place"


def transcript(folder, last_text, entries=None):
    """A session that edited the place's inventory (or made these tool calls) and ended with this text."""
    calls = entries if entries is not None else [{"type": "tool_use", "name": "Edit",
                                                  "input": {"file_path": f"/x/data/inventory/{PLACE}.json"}}]
    lines = [{"type": "user", "message": {"role": "user", "content": "finish the place"}},
             {"type": "assistant", "message": {"role": "assistant", "content": calls}},
             {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": last_text}]}}]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return str(path)


def known_place_env(folder):
    """The environment in which the guard knows the place (a places file naming it) and finds no stage for it, so its
    gate's every requirement is unknown, which blocks like fail."""
    folder.mkdir(parents=True, exist_ok=True)
    within = folder / "within.json"
    within.write_text(json.dumps({"shells": {PLACE: {}}}))
    return dict(os.environ, SCORE_GUARD_WITHIN=str(within), PROPS_WORK=str(folder / "work"))


def stop(name, last_text, entries=None, **more):
    """A Stop payload made in a world: the session `name` (see transcript), and per key in `more` another transcript
    ending with that text."""
    return lambda world: {"transcript_path": transcript(world / name, last_text, entries),
                          **{key: transcript(world / f"{name}-{key}", said) for key, said in more.items()}}


FALSE_CLAIMS = [
    stop("claim-a", f"The {PLACE} is complete now."),
    lambda world: {"transcript_path": transcript(world / "claim-b", "Reading the inventory now."),  # the transcript lags
                   "last_assistant_message": f"The {PLACE} is done."},
    stop("claim-c", "Nothing claimed here.", agent_transcript_path=f"The {PLACE} is done."),  # a sub-agent's own transcript
    stop("claim-e", "Every place is finished."),
]
HONEST_STOPS = [
    stop("honest-a", f"Left: export it, then run `complete.py done {PLACE}`."),  # a quoted command
    stop("honest-b", f"The {PLACE} is not complete: rows remain."),
    stop("honest-c", f"No place is complete, {PLACE} included."),
    stop("honest-d", "I moved two crates."),
    stop("honest-e", f"The whole film is done too: it ends at the {PLACE}."),  # owner, 2026-10-21
    stop("honest-f", f"The {PLACE} is done.", entries=[  # a place the session never worked on
        {"type": "tool_use", "name": "Edit", "input": {"file_path": "/x/data/inventory/nowhere_else.json"}}]),
    stop("honest-g", f"The {PLACE} is done.",  # only named in a hand-off
         entries=[{"type": "tool_use", "name": "Agent", "input": {"prompt": f"read data/inventory/{PLACE}.json"}}]),
    # a done-word beside "all places", no claim (2026-10-27)
    stop("honest-i", "Each place's shots wait for its complete check, and the film comes after all places."),
]


# As the local hooks list runs it: its own shell command for that event, in the checkout, the project's folder the
# main checkout (whose .venv it falls back to). It imports score.stages, which needs pxr, so only the project's python
# refuses a false claim; the system python3 crashes on the import and blocks nothing.
LISTED_COMPLETION = {entry["event"]: entry["command"] for entry in json.loads((HOOKS / "local/hooks.json").read_text())
                     if "completion_guard.py" in entry["command"]}


def listed_completion(event):
    """A world: completion_guard run by the local hooks list's command for this event, its place known."""
    def make(world):
        main = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              capture_output=True, text=True).stdout.strip()
        env = dict(known_place_env(world), CLAUDE_PROJECT_DIR=str(pathlib.Path(main).parent))
        return ["bash", "-c", LISTED_COMPLETION[event]], env, REPO
    return make



# issue_guard: every new issue has an assignee, a category and (once the project has areas) an area; no rot in its
# body; a PRD is a root that names the roots it checked; no history-destroying git.

def issue_guard_copy(folder, areas, **config):
    """issue_guard.py in a scratch repo whose project.json lists these areas (and any other keys); its path."""
    return hook_copy(folder, "issue_guard.py", {"repo": "acme/widget", "areas": areas, **config})


FULL_ISSUE = "gh issue create --title x --label bug --assignee someone"
ROOT_CHECKED = ' --body "## Root check\nNo open root covers this."'

BARE_OR_DESTRUCTIVE = [
    (bash('gh issue create --title "x" --body "y"'), "bare issue creation"),
    (bash("gh issue create --title x --label PRD"), "assignee"),
    (bash("gh issue create --title x --assignee someone"), "PRD or bug/enhancement"),
    (bash('gh issue close 1 --comment "done" && gh issue create --title "x"'), "bare issue creation"),
    ({"tool_name": "mcp__github__create_issue", "tool_input": {"title": "x"}}, "bare issue creation"),
    (bash(FULL_ISSUE + ' --body "Per plan.md line 117 this holds."'), "numbers in prose rot"),
    (bash(FULL_ISSUE + ' --body "See notes.md:42 for the claim."'), "numbers in prose rot"),
    ({"tool_name": "mcp__github__create_issue", "tool_input": {
        "title": "x", "labels": ["bug"], "assignees": ["someone"], "body": "See notes.md:42"}}, "numbers in prose rot"),
    (bash('gh issue create --title x --label PRD --assignee someone --body "## Parent\n#5"'), "names #5 as its parent"),
    (bash("gh issue create --title x --label PRD --assignee someone"), "## Root check"),
    ({"tool_name": "mcp__github__create_issue", "tool_input": {
        "title": "x", "labels": ["PRD"], "assignees": ["someone"], "body": "no sections"}}, "## Root check"),
    (bash("git push --force origin main"), "destructive git"),
    (bash("git push --force-with-lease origin main"), "destructive git"),
    (bash("git push -f origin main"), "destructive git"),
    (bash("git push origin +main:main"), "destructive git"),
    (bash("git reset --hard origin/main"), "destructive git"),
]

COMPLETE_OR_ORDINARY = [
    bash('gh issue create --title "x" --label PRD --assignee someone' + ROOT_CHECKED),
    bash('gh issue create --title "x" -l "bug,enhancement" -a someone'),
    bash("gh issue create --title=x --label=PRD --assignee=someone" + ROOT_CHECKED),
    {"tool_name": "mcp__github__create_issue", "tool_input": {"title": "x", "labels": ["PRD"], "assignees": ["someone"],
                                                              "body": "## Root check\nnone"}},
    bash(FULL_ISSUE + ' --body "Bug lives in src/dispatcher.py:419"'),  # a code ref is the house citation
    bash(FULL_ISSUE + ' --body "## Parent\n#5"'),  # a nested issue names its parent
    bash("gh issue list --label needs-triage"),
    bash('gh issue close 919 --comment "the guard now enforces the create rules"'),
    bash("ls -la && echo hi"),
    bash("git push origin HEAD:main"),
    bash('git commit -m "note: never run git push -f here"'),
]



def created(title, body="x", labels=("bug",)):
    """An issue made through the GitHub tool, assigned, with these labels and body."""
    return {"tool_name": "mcp__github__create_issue", "tool_input": {
        "title": title, "labels": list(labels), "assignees": ["someone"], "body": body}}


AREA_ASKS = [  # once the project has areas, an issue names one, under the project's own prefix when it names one
    ("issue-areas", bash(FULL_ISSUE), "block", ("area:<x>",)),
    ("issue-areas", bash(FULL_ISSUE + " --label area:dev"), "allow", ()),
    ("issue-team", bash(FULL_ISSUE + " --label area:dev"), "block", ("team:<x>",)),
    ("issue-team", bash(FULL_ISSUE + " --label team:dev"), "allow", ()),
]

# An open root's subject is its own title's words and its children's; a standing backlog PRD is never one; a new
# sub-issue sharing three subject words with an open one is refused unless its Duplicate check names it.
ROOTS = [{"number": 7, "title": "Render farm queue", "parent": None, "labels": ["PRD"]},
         {"number": 8, "title": "Lighting rig rebuild", "parent": 7, "labels": ["bug"]},
         {"number": 36, "title": "Shader cleanup", "parent": None, "labels": ["PRD"]}]
OPEN_WORK = [{"number": 41, "title": "Rename the wire field treatment_path to label", "labels": ["bug"], "parent": None},
             {"number": 40, "title": "Rename everything", "labels": ["PRD"], "parent": None}]
NEW_PRD = 'gh issue create --title "{title}" --label PRD --assignee someone --body "## Root check\n{check}"'
OPEN_WORK_ASKS = [
    ("issue-roots", bash(NEW_PRD.format(title="Lighting rig for night scenes", check="none")), "block",
     ("#7 Render farm queue", "lighting")),
    ("issue-roots", bash(NEW_PRD.format(title="Lighting rig for night scenes", check="#7 is the farm, not lights")),
     "allow", ()),
    ("issue-roots", bash(NEW_PRD.format(title="Shader library", check="none")), "allow", ()),
    ("issue-open", created("Rename wire field treatment_path everywhere"), "block", ("#41",)),
    ("issue-open", created("Rename wire field treatment_path everywhere", "## Duplicate check\n#41 is the API half."),
     "allow", ()),
    ("issue-open", created("Fix the hero image on mobile"), "allow", ()),
]

# Cited paths under a listed prefix must exist; an area with a required first line must carry it; a sub-issue, a PRD
# and a vision PRD each have a maximum body, a comment has its own; an edit may shrink an over-cap body but never grow
# it, and a first `<!-- Budget: -->` line lifts the cap.
IN_AREA = FULL_ISSUE + " --label area:{area} --body '{body}'"
CAPS = {"sub_issue": 300, "prd": 600, "vision_prd": 1000, "comment": 250}
ROOT_BODY = "## Root check\nNo open root covers this.\n"
COMMENT = {"tool_name": "mcp__github__add_issue_comment", "tool_input": {"issue_number": 7}}
OVER_CAP = {"body": "z" * 400, "labels": [{"name": "bug"}]}  # the issue an edit changes, as gh shows it
EDIT = {"tool_name": "mcp__github__update_issue", "tool_input": {"issue_number": 7}}
BODY_ASKS = [
    ("issue-business", bash(IN_AREA.format(area="dev", body="See business/gone/plan.md")), "block",
     ("business/gone/plan.md",)),
    ("issue-business", bash(IN_AREA.format(area="dev", body="See business/real.md")), "allow", ()),
    ("issue-business", bash(IN_AREA.format(area="sales", body="Sell it.")), "block", ("**Business case:**",)),
    ("issue-business", bash(IN_AREA.format(area="sales", body="**Business case:** x\nSell it.")), "allow", ()),
    ("issue-caps", created("a size probe", "x" * 301), "block", ("300",)),
    ("issue-caps", created("a size probe", "x" * 300), "allow", ()),
    ("issue-caps", created("a size probe", "<!-- Budget: a long spec -->\n" + "x" * 900), "allow", ()),
    ("issue-caps", created("a size probe", ROOT_BODY + "x" * 600, ["PRD"]), "block", ()),
    ("issue-caps", created("a size probe", ROOT_BODY + "x" * 600, ["PRD", "vision"]), "allow", ()),
    ("issue-caps", {**COMMENT, "tool_input": {**COMMENT["tool_input"], "body": "y" * 251}}, "block", ()),
    ("issue-caps", {**COMMENT, "tool_input": {**COMMENT["tool_input"], "body": "y" * 250}}, "allow", ()),
    ("issue-caps", bash("gh issue comment 7 --body " + "y" * 251), "block", ()),
    ("issue-edit", {**EDIT, "tool_input": {**EDIT["tool_input"], "body": OVER_CAP["body"] + "more"}}, "block", ()),
    ("issue-edit", {**EDIT, "tool_input": {**EDIT["tool_input"], "body": OVER_CAP["body"][:-50]}}, "allow", ()),
]


def listed(issues):
    """A world's environment in which the guard sees these open issues as GitHub's."""
    def environment(world):
        known = world / "open.json"
        known.write_text(json.dumps(issues))
        return dict(os.environ, ISSUE_GUARD_ROOTS=str(known))
    return environment


def issue_world(areas=(), environment=None, **config):
    """A world: issue_guard.py in it with these areas and project.json keys, run in this environment."""
    def make(world):
        return issue_guard_copy(world, list(areas), **config), environment and environment(world), None
    return make


def business_world(world):
    """issue_guard.py whose project wants business/ citations to exist (business/real.md does) and a sales issue's
    body to open with its business case."""
    guard = issue_guard_copy(world, ["sales", "dev"], cited_paths_must_exist=["business/"],
                             area_first_line={"sales": {"label": "Business case", "example": "**Business case:** x"}})
    (world / "business").mkdir()
    (world / "business" / "real.md").write_text("# real\n")
    return guard, None, None


def edit_world(world):
    """issue_guard.py under body caps, with a stand-in gh on PATH that shows the issue an edit changes."""
    guard = issue_guard_copy(world, [], issue_body_caps=CAPS)
    stand_in = world / "bin"
    stand_in.mkdir()
    (world / "issue.json").write_text(json.dumps(OVER_CAP))
    (stand_in / "gh").write_text(f"#!/bin/sh\ncat {world / 'issue.json'}\n")
    (stand_in / "gh").chmod(0o755)
    return guard, {**os.environ, "PATH": f"{stand_in}:{os.environ.get('PATH', '')}"}, None

# md_guard: a new .md inside the repo needs the user's yes.

def md_world(folder):
    """A scratch repo at folder/repo holding md_guard.py, a local md_allowed.json with one yes, and one existing .md;
    (guard, repo)."""
    repo = folder / "repo"
    guard = hook_copy(repo, "md_guard.py")
    (guard.parent / "local").mkdir()
    (guard.parent / "local" / "md_allowed.json").write_text(json.dumps([
        {"path": "docs/asked-for.md", "words": "yes, write it", "at": "2026-01-01T00:00Z"},
        {"path": "docs/no-words.md", "at": "2026-01-01T00:00Z"}]))
    (repo / "docs").mkdir()
    (repo / "docs" / "existing.md").write_text("# kept\n")
    return guard, repo


def md_write(repo, path, transcript=None):
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(repo / path)}, "cwd": str(repo)}
    return dict(payload, transcript_path=str(transcript)) if transcript else payload


def md_bash(repo, command):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(repo)}


def typed_transcript(folder, entries):
    """A session transcript of these user entries: a string is a typed message, a dict a tool result."""
    lines = [{"type": "user", "message": {"role": "user", "content": entry if isinstance(entry, str) else [
        {"type": "tool_result", "tool_use_id": "x", "content": entry["result"]}]}} for entry in entries]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return path


def in_md_repo(make):
    """A payload made in an md world: make(repo, world)."""
    return lambda world: make(world / "repo", world)


NEW_MD_WITHOUT_A_YES = [in_md_repo(make) for make in (
    lambda repo, world: md_write(repo, "docs/never-asked-for.md"),
    lambda repo, world: md_write(repo, "docs/no-words.md"),
    lambda repo, world: md_write(repo, "docs/never-asked-for.md", typed_transcript(  # a tool result is not the person
        world / "never", ["hello", "run the validation", {"result": "wrote notes.md"}])),
    lambda repo, world: md_bash(repo, "echo hi > notes.md"),
    lambda repo, world: md_bash(repo, "echo hi | tee -a docs/summary.md"),
    lambda repo, world: md_bash(repo, "touch docs/new.md"),
    lambda repo, world: md_bash(repo, "cp docs/existing.md docs/copy.md"),
    lambda repo, world: md_bash(repo, "cd docs && echo x > new.md"),
    lambda repo, world: md_bash(repo, f"OUT={repo}/docs; echo x > $OUT/n.md"),
    lambda repo, world: md_write(repo, "docs/report.md", typed_transcript(  # the yes is 21 typed messages back
        world / "stale", ["make a md file for it"] + [f"step {at}" for at in range(20)])),
)]
STANDING_EXCEPTIONS = [in_md_repo(make) for make in (
    lambda repo, world: md_write(repo, "docs/asked-for.md"),  # listed with the user's words
    lambda repo, world: md_write(repo, "docs/report.md", typed_transcript(  # asked for in the user's last messages
        world / "asked", ["hello", "can you make a report, u can make a md file for it"])),
    lambda repo, world: md_write(repo, ".claude/memory/some-note.md"),  # private memory
    lambda repo, world: md_write(repo, "tools/new/CLAUDE.md"),  # a directory's overlay
    lambda repo, world: md_write(repo, "docs/existing.md"),  # an edit
    lambda repo, world: md_write(repo, "notes.txt"),
    lambda repo, world: md_bash(repo, "mv docs/existing.md docs/renamed.md"),  # a rename keeps the count
    lambda repo, world: md_bash(repo, f"echo x > {world}/outside.md"),  # outside the repo
    lambda repo, world: md_bash(repo, f"cd {world} && echo x > page.md"),
    lambda repo, world: md_bash(repo, "echo x > $UNKNOWN_SOMEWHERE/page.md"),  # unknowable: fail open
)]


def unread_pipe(world):
    """A transcript path that is a pipe nobody writes: a guard that reads it never answers."""
    pipe = world / "unread.jsonl"
    os.mkfifo(pipe)
    return str(pipe)


# A call that creates no .md answers without reading the transcript, and a new .md reads only the transcript's end for
# the yes: a long session's runs to hundreds of MB, read whole it took seconds a call, so the harness timed the guard
# out (failing open) 341 times. Each is timed against the same guard on a call it answers from the call alone (a
# listed path, no transcript), on the box as loaded now: the guard's own start-up is the box's, and on the gate's pods
# (2 slower cores, files side by side) a bare interpreter start took 0.07 s and the guard's 0.2 s, so only what the
# call's transcript adds is judged against the 100 ms.
LISTED_ALONE = {"timed": in_md_repo(lambda repo, world: md_write(repo, "docs/asked-for.md"))}
MD_TIMED = [
    ("md", in_md_repo(lambda repo, world: dict(md_bash(repo, "ls docs; git status"),
                                               transcript_path=unread_pipe(world))), "allow", (), LISTED_ALONE),
    ("md", in_md_repo(lambda repo, world: md_write(repo, "docs/report.md", typed_transcript(
        world / "long", ["a line of chat " * 50] * 60000 + ["write a md file for it"]))), "allow", (), LISTED_ALONE),
]
TIMED_ROUNDS, TRANSCRIPT_SECONDS = 3, 0.1


# commit_guard: a session may not waive the commit guards, nor commit in the shared checkout while another session
# is live in a worktree.

GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
               GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


def git(repo, *args):
    """Run git in `repo` with a clean config; its stdout."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True,
                          env=GIT_ENV).stdout.strip()


def git_repo(folder, files=None):
    """A git repo at `folder` on `main`, with these files (path: text) in its first commit."""
    folder.mkdir(parents=True, exist_ok=True)
    git(folder, "init", "-q", "-b", "main")
    for path, text in (files or {"README": "x\n"}).items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "first")
    return folder


WAIVERS = ["git commit --no-verify -m x", "git commit -n -m x", "TORN_GUARD=0 git commit -m x",
           "LEFTOVER_GUARD=0 true"]


ALLOWED_BESIDE_WAIVERS = ['git commit -m "never use --no-verify or TORN_GUARD=0"', "git status", "ls -n"]


def in_commit_world(command, where="repo"):
    """A Bash call of this command made in a commit world, run in its repo (or its worktree, or the world itself)."""
    places = {"repo": lambda world: world / "repo", "worktree": lambda world: world / "repo/.claude/worktrees/w1",
              "world": lambda world: world}
    return lambda world: dict(bash(command.format(world=world)), cwd=str(places[where](world)))


def live_world(locked):
    """A world: a repo with a session's worktree w1 (locked by this live process, or not), commit_guard.py beside it
    in hooks_home, run with a clean git config."""
    def make(world):
        repo = git_repo(world / "repo")
        guard = hook_copy(world / "hooks_home", "commit_guard.py")
        worktree = repo / ".claude" / "worktrees" / "w1"
        git(repo, "worktree", "add", "-q", "-b", "w1", str(worktree))
        if locked:
            git(repo, "worktree", "lock", "--reason", f"claude session pid {os.getpid()}", str(worktree))
        return guard, GIT_ENV, None
    return make


WORKTREE_W1 = "{world}/repo/.claude/worktrees/w1"
COMMIT_ASKS = [
    *(("commit", in_commit_world(waiver, "world"), "block", ("routes around",)) for waiver in WAIVERS),
    *(("commit", in_commit_world(allowed, "world"), "allow", ()) for allowed in ALLOWED_BESIDE_WAIVERS),
    ("commit-unlocked", in_commit_world("git commit -m x"), "allow", ()),  # nobody else is live
    ("commit-live", in_commit_world("git commit -m x"), "block", ("w1",)),
    ("commit-live", in_commit_world("git commit -m x", "worktree"), "allow", ()),  # inside a worktree
    ("commit-live", in_commit_world("git -C {world} commit -m x"), "allow", ()),
    ("commit-live", in_commit_world(f"cd {WORKTREE_W1}; git commit -m x"), "allow", ()),
    ("commit-live", in_commit_world(f"cd {WORKTREE_W1} && git commit -m x"), "allow", ()),
    # `~` reaches the guard unexpanded; it names the home directory as the shell would.
    *(("commit-live", in_commit_world(elsewhere), "allow", (), {"env": lambda world: {"HOME": str(world)}})
      for elsewhere in ("git -C ~/repo/.claude/worktrees/w1 commit -m x",
                        "cd ~/repo/.claude/worktrees/w1 && git commit -m x")),
    # only git's own subcommand is a commit
    *(("commit-live", in_commit_world(commit), "block", ())
      for commit in ("git -c user.name=x commit -m x", "/usr/bin/git commit -m x", "git status; git commit -m x")),
    *(("commit-live", in_commit_world(other), "allow", ())
      for other in ("git log --grep commit", 'gh issue comment 1 --body "git log shows the commit"',
                    "git status && echo commit")),
    ("commit-live", in_commit_world("git commit -m x"), "allow", (), {"env": lambda world: {"WORKTREE_GUARD": "0"}}),
]

# torn_commit_guard: a commit may not need what it leaves behind.

def torn_repo(folder, sourced=None, files=None):
    """A repo holding torn_commit_guard.py (and a project.json listing these sourced dirs) and these files (path:
    text), all committed."""
    hook_copy(folder, "torn_commit_guard.py", {"sourced_shell_dirs": sourced or []})
    return git_repo(folder, {"lib/module_kept.py": "VALUE = 1\n", **(files or {})})


def torn_world(staged, sourced=None, committed=None, loose=None):
    """A world: torn_commit_guard.py run as git runs a pre-commit hook (in the repo's top folder), its repo listing
    these sourced dirs, holding the committed files, these staged ones and these written but never staged (path:
    text)."""
    def make(world):
        repo = torn_repo(world / "repo", sourced, committed)
        for path, text in staged.items():
            stage(repo, path, text)
        for path, text in (loose or {}).items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text)
        return repo / ".claude/hooks/torn_commit_guard.py", GIT_ENV, repo
    return make


FIRST_STEP = {"steps/10-first.sh": "made_here=1\n"}
TORN_ASKS = [  # a git hook refuses with exit 1; a sourced step may read only what an earlier step made, or a default
    ("torn-markers", "", "refuse", ("conflict markers",)),
    ("torn-unmade", "", "refuse", ("made_nowhere",), {"lacks": ("made_here",)}),
    ("torn-defaulted", "", "allow", ()),
    # a staged test reading a fixture never committed; a tracked file merely dirty is a note, not a block
    ("torn-uncommitted", "", "refuse", ("fixtures/case_fixture.json",)),
    ("torn-uncommitted", "", "allow", (), {"env": lambda world: {"TORN_GUARD": "0"}}),
    ("torn-staged", "", "allow", ()),
    ("torn-dirty", "", "allow", ("note",)),
]
READS_FIXTURE = {"tests/test_reads.py": "DATA = 'fixtures/case_fixture.json'\n"}
FIXTURE = {"fixtures/case_fixture.json": "{}\n"}


def stage(repo, path, text):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text(text)
    git(repo, "add", path)


# The push gate (.claude/hooks/local/pre-push): no push leaves main red, run in a clone of this checkout.

GATE_FILES = (".claude/hooks/local/pre-push", "tools/test_rule/check.py", "Makefile", ".claude/scripts/sandbox-home.py")
HOLDS_TEST = '''"""A held value stays held, in its own repository with the framework's environment. Break: holds.py's VALUE
made 2 turns it red."""
import pathlib
import subprocess


def test_value_holds():
    here = pathlib.Path(__file__).resolve().parent
    assert (here / "holds.py").read_text() == "VALUE = 1\\n"
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True).stdout
    assert pathlib.Path(top.strip()) == here.parents[1], top
    assert (here.parents[1] / ".venv/bin/python").exists()
'''


def main_push_line(repo, pushed="HEAD", base="HEAD~1"):
    """The push line git hands a pre-push hook for a push of `pushed` onto main at `base`."""
    return f"refs/heads/main {git(repo, 'rev-parse', pushed)} refs/heads/main {git(repo, 'rev-parse', base)}\n"


def gate_world(files, away=False):
    """A world: a clone of this checkout with this tree's gate files, a module `tools/zz_gate` whose test passes and
    its pre-push-moved a stand-in writing its stdin to world/moved.txt, all committed as the base; then one commit on
    it writing files(clone) (path: text), its push line in world/push-line; `away` puts the clone back on the base, so
    the commit pushed is not the one checked out. The gate runs as git runs it, its GIT_DIR the clone's."""
    def make(world):
        clone = world / "clone"
        git(world, "clone", "-q", "--shared", str(REPO), str(clone))
        for name in GATE_FILES:
            shutil.copy(REPO / name, clone / name)
        moved = clone / ".claude/hooks/local/pre-push-moved"
        moved.write_text(f"#!/usr/bin/env bash\ncat > {world / 'moved.txt'}\n")
        moved.chmod(0o755)
        (clone / "tools/zz_gate").mkdir()
        (clone / "tools/zz_gate/holds.py").write_text("VALUE = 1\n")
        (clone / "tools/zz_gate/test_a_held_value_stays_held.py").write_text(HOLDS_TEST)
        own = REPO / ".venv"
        common = pathlib.Path(git(REPO, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent / ".venv"
        (clone / ".venv").symlink_to(own if own.exists() else common)
        git(clone, "add", "-A")
        git(clone, "commit", "-q", "-m", "base")
        for path, text in files(clone).items():
            (clone / path).parent.mkdir(parents=True, exist_ok=True)
            (clone / path).write_text(text)
        git(clone, "add", "-A")
        git(clone, "commit", "-q", "-m", "pushed")
        (world / "push-line").write_text(main_push_line(clone))
        if away:
            git(clone, "reset", "-q", "--hard", "HEAD~1")
        # a test's own scratch git must not inherit GIT_DIR
        return clone / ".claude/hooks/local/pre-push", dict(GIT_ENV, GIT_DIR=str(clone / ".git")), clone
    return make


def grown_debt(clone):
    """A file still on FUNCTION_DEBT, read from the guard itself (a hard-coded one went stale when its fold paid it
    off), grown by one test function."""
    debt = next(iter(runpy.run_path(str(REPO / "tools" / "test_rule" / "check.py"))["FUNCTION_DEBT"]))
    return {debt: (clone / debt).read_text() + "\n\ndef test_grown():\n    pass\n"}


def pushed_line(world):
    return (world / "push-line").read_text()


GATE_SECONDS = {"seconds": 110}  # the gate runs the touched module's test file
GATE_ASKS = [  # a grown debt file and a failing touched test are refused; a clean push goes on to the moved check
    ("gate-grown", pushed_line, "refuse", ("test rule",),
     {"prints": ("may not grow",), "holds": {"moved.txt": None}, **GATE_SECONDS}),
    ("gate-failing", pushed_line, "refuse", ("touched module's test failed",),
     {"holds": {"moved.txt": None}, **GATE_SECONDS}),
    ("gate-clean", pushed_line, "allow", (),
     {"prints": ("passed in", "1 test file",
                 "test_rra_moves_mass_and_torso_by_the_mean_residual.py needs a GPU, left to a run by hand"),
      "begins": {"moved.txt": "refs/heads/main "}, **GATE_SECONDS}),
    # the clone moved off the pushed commit: the gate checks it in a copy of its own
    ("gate-away", pushed_line, "allow", (), {"prints": ("1 test file",), "begins": {"moved.txt": "refs/heads/main "},
                                             **GATE_SECONDS}),
]


# The redo guard (pre-push-moved, score.stages.moved, remake_freeze.py): the push counts every accepted node it makes
# again, free ones too, in one line; while a freeze stands a push remaking accepted rows is refused unless a pushed
# commit's Remakes trailer names them with a reason; no freeze, a freeze past its day or nothing remade passes, and a
# freeze file that cannot be read refuses.

REMADE_COUNT = """import json, sys
from score.stages import moved
found = {"light": {"paid": True, "euros": 2.5, "code": True, "files": {}, "places": ["hub", "camp"]},
         "images:pins": {"paid": False, "euros": 1.5, "code": True, "files": {}, "places": ["None"]},
         "settle": {"paid": False, "euros": 0, "code": False, "files": {"a.py": ["hub"]}, "places": ["hub", "camp"]}}
accepted = {"light@hub", "light@camp", "pins", "settle@camp"}
remade = moved.remade_accepted(found, lambda node: "out" if node in accepted else None)
print(json.dumps(sorted(row["node"] for row in remade)))
print(moved.remakes_line(remade))"""


def remade_world(world):
    """score.stages.moved asked in this checkout by its own interpreter."""
    own = REPO / ".venv/bin/python"
    common = pathlib.Path(git(REPO, "rev-parse", "--path-format=absolute", "--git-common-dir")).parent / ".venv/bin/python"
    return [str(own if own.exists() else common), "-c", REMADE_COUNT], dict(GIT_ENV, PYTHONDONTWRITEBYTECODE="1"), REPO


STANDING_FREEZE = '{"until": "2999-01-01", "reason": "the film"}'


def freeze_world(message, remade=("light@hub", "pins"), freeze_text=STANDING_FREEZE):
    """A world: remake_freeze.py on a push of one commit with this message, these accepted nodes remade (free ones)
    and this freeze file (None: none)."""
    def make(world):
        repo = world / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "commit", "-q", "--allow-empty", "-m", "base")
        git(repo, "commit", "-q", "--allow-empty", "-m", message)
        remakes, freeze = world / "remakes.json", world / "freeze.json"
        remakes.write_text(json.dumps({"remade": [{"node": node, "paid": False, "euros": 0} for node in remade]}))
        if freeze_text is not None:
            freeze.write_text(freeze_text)
        return ([sys.executable, str(HOOKS / "local/remake_freeze.py"), str(remakes)],
                dict(GIT_ENV, SCORE_PUSH_FREEZE=str(freeze)), repo)
    return make


def pushed_head(world):
    return main_push_line(world / "repo")


FREEZE_ASKS = [
    # settle moved only by a file at hub, accepted only at camp: not remade
    ("remade", "", "allow", (),
     {"tail": ['["light@camp", "light@hub", "pins"]', "this push re-makes 3 accepted rows (2 paid, EUR 5.00)"]}),
    ("freeze-unnamed", pushed_head, "refuse", ("light@hub pins", "Remakes: light pins: <why>")),
    ("freeze-one-named", pushed_head, "refuse", ("pins",), {"lacks": ("light@hub",)}),  # a row left unnamed refuses
    ("freeze-named", pushed_head, "allow", ()),
    ("freeze-no-reason", pushed_head, "refuse", ()),  # a trailer with no reason names nothing
    ("freeze-nothing", pushed_head, "allow", ()),
    ("freeze-none", pushed_head, "allow", ()),
    ("freeze-past", pushed_head, "allow", ()),
    ("freeze-broken", pushed_head, "refuse", ("cannot be read",)),
]


# The push cap (.claude/hooks/pre-push and push_cap.py): a day's pushes to main over every repository sharing one
# config stop at its limit, the latest limit started wins, a push the repository's own hook refused gives its slot
# back, other branches are not counted, a release-only repository's pushes and a release tag pass uncounted, no
# config is no cap and an unreadable one refuses.

def capped_repo(folder, origin):
    """A scratch repo at `folder` (remote origin `origin`) holding the shared pre-push and push_cap.py, its own
    pre-push a stand-in that refuses when LOCAL_REFUSES is 1."""
    hooks = folder / ".claude/hooks"
    (hooks / "local").mkdir(parents=True)
    git(folder, "init", "-q")
    git(folder, "remote", "add", "origin", origin)
    for name in ("pre-push", "push_cap.py"):
        shutil.copy(HOOKS / name, hooks / name)
    own = hooks / "local/pre-push"
    own.write_text('#!/usr/bin/env bash\ncat >/dev/null\n[ "${LOCAL_REFUSES:-0}" != 1 ]\n')
    own.chmod(0o755)


def cap_world(world):
    """A world: repositories one (remote git@example.com:a/one.git) and two (x/two) sharing cap configs in
    world/caps. In one, a commit origin's main took and a later one it refused; refused.json a ledger of today holding
    one's taken push and its refused one from long ago and from just now, and two's from long ago; kept.json the
    entries it then keeps."""
    one, two = world / "one", world / "two"
    capped_repo(one, "git@example.com:a/one.git")
    capped_repo(two, "x/two")
    caps = world / "caps"
    caps.mkdir()
    today = time.strftime("%Y-%m-%d", time.gmtime())

    def config(name, limits, ledger, **more):
        (caps / name).write_text(json.dumps({"limits": [{"from": day, "per_day": count} for day, count in limits],
                                             "ledger": str(world / ledger), **more}))
    # 6 a day from long ago, 4 from a day that has not come: 6 holds, over both repositories
    config("six.json", [("2000-01-01", 6), ("2999-01-01", 4)], "six-ledger.json")
    config("today.json", [("2000-01-01", 6), (today, 4)], "later.json")  # the latest started limit wins
    config("one-uncounted.json", [("2000-01-01", 4)], "later.json", uncounted=["one"])  # by its name
    config("two-uncounted.json", [("2000-01-01", 4)], "later.json", uncounted=["x/two"])  # by its whole url
    config("refused.json", [("2000-01-01", 4)], "refused.json")
    (caps / "broken.json").write_text("{not json")
    git(one, "commit", "-q", "--allow-empty", "-m", "taken")
    taken = git(one, "rev-parse", "HEAD")
    git(one, "update-ref", "refs/remotes/origin/main", taken)
    git(one, "commit", "-q", "--allow-empty", "-m", "refused")
    refused = git(one, "rev-parse", "HEAD")
    old, recent = "2000-01-01T00:00:00+00:00", time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    entries = [["git@example.com:a/one.git", taken, old], ["git@example.com:a/one.git", refused, old],
               ["git@example.com:a/one.git", refused, recent], ["x/two", refused, old]]
    (world / "refused.json").write_text(json.dumps(
        {today: [{"repo": repo, "sha": sha, "at": at} for repo, sha, at in entries]}))
    (world / "kept.json").write_text(json.dumps([entries[0], entries[2], entries[3]]))
    return None, GIT_ENV, None


def cap_ask(verdict, words=(), repo="one", config="six.json", branch="main", ref="refs/heads/", refuses=False, **more):
    """A push to `branch` from repository `repo` under the cap config `config`, its own pre-push refusing or not."""
    return ("push-cap", f"{ref}{branch} {'1' * 40} {ref}{branch} {'2' * 40}\n", verdict, words,
            {"hook": lambda world: (["bash", str(world / repo / ".claude/hooks/pre-push"), "origin", "x"], world / repo),
             "env": lambda world: {"HARNESS_PUSH_CAP": str(world / "caps" / config),
                                   "LOCAL_REFUSES": "1" if refuses else "0"}, **more})


CAP_PUSH_ASKS = [  # asked in this order
    *(cap_ask("allow", repo=repo) for repo in ("one", "two", "one", "two", "one")),
    cap_ask("refuse", refuses=True),  # the repository's own hook still refuses
    cap_ask("allow", repo="two", branch="feature"),  # another branch is no push to main
    cap_ask("allow", repo="two"),  # the refused push gave its slot back: this is the 6th
    cap_ask("refuse", ("reached today's limit of 6", "a/one.git", "x/two")),
    *(cap_ask("allow", config="today.json") for _ in range(4)),
    cap_ask("refuse", config="today.json"),
    cap_ask("allow", repo="two", config="today.json", ref="refs/tags/", branch="v1"),  # a release tag
    *(cap_ask("allow", config="one-uncounted.json") for _ in range(3)),  # one is release-only: its pushes pass
    cap_ask("refuse", ("reached today's limit of 4",), repo="two", config="one-uncounted.json",
            times={"a/one.git": 4}),
    cap_ask("allow", repo="two", config="two-uncounted.json"),  # two by its whole url passes
    cap_ask("refuse", config="two-uncounted.json"),  # one is counted again
    cap_ask("allow", config="none.json"),  # no config, no cap
    # a push the remote refused (its commit not on origin's main) gives its slot back at the next claim from its
    # repository: this is the 4th; one the remote took, one still on its way and another repository's keep theirs
    cap_ask("allow", config="refused.json"),
    cap_ask("refuse", config="refused.json", ledger=("refused.json", "kept.json")),
    cap_ask("refuse", ("cannot be read",), config="broken.json"),
]


# leftover_guard: a session may not end leaving its own worktree dirty; said once.

def leftover_world(world):
    """A world: leftover_guard.py beside a repo whose session worktree w1 holds an uncommitted file, the shared
    checkout an untracked file of someone else's."""
    repo = git_repo(world / "repo")
    guard = hook_copy(world / "hooks_home", "leftover_guard.py")
    worktree = repo / ".claude" / "worktrees" / "w1"
    git(repo, "worktree", "add", "-q", "-b", "w1", str(worktree))
    (worktree / "half_done.py").write_text("x = 1\n")
    (repo / "someone_elses.py").write_text("y = 1\n")
    return guard, GIT_ENV, None


def ending(where, session):
    """A Stop payload of this session, ended in the world's `where`."""
    return lambda world: {"cwd": str(world / where), "session_id": session}


SENT_BACK = {"fields": {("decision",): "block"}}
LEFTOVER_ASKS = [  # asked in this order
    ("leftover", ending("repo/.claude/worktrees/w1", "s1"), "said", ("half_done.py",), SENT_BACK),
    ("leftover", ending("repo/.claude/worktrees/w1", "s1"), "quiet", ()),  # said once per session
    ("leftover", ending("repo", "s2"), "quiet", ()),  # the shared checkout's dirt is everybody's
    ("leftover", ending("repo/.claude/worktrees/w1", "s3"), "quiet", (),
     {"env": lambda world: {"LEFTOVER_GUARD": "0"}}),
]


# soul_guard: no em dash, and no long reply to a short question that did not ask for detail; sent back at most twice.

def soul_turn(folder, question, reply):
    lines = [{"type": "user", "message": {"role": "user", "content": question}},
             {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}}]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    return {"transcript_path": str(path)}


def soul(name, question, reply, rewrite=None):
    """A Stop payload of one turn; with `rewrite` (False on the first stop, True on a stop after a send-back) in a
    session of the world's own."""
    def payload(world):
        turn = soul_turn(world / name, question, reply)
        if rewrite is None:
            return turn
        session = dict(turn, session_id=f"soul-twice-{world.name}")
        return dict(session, stop_hook_active=True) if rewrite else session
    return payload


LONG_REPLY = " ".join(["word"] * 150)
SOUL_ASKS = [  # asked in this order
    ("soul", soul("a", "is it done?", "Yes — it is."), "said", ("Rule 3",), SENT_BACK),
    ("soul", soul("b", "is it done?", LONG_REPLY), "said", ("Rules 2 and 5",), SENT_BACK),
    ("soul", soul("c", "is it done?", "Yes, it is."), "quiet", ()),
    ("soul", soul("d", "explain in detail how the cache works", LONG_REPLY), "quiet", ()),
    ("soul", soul("f", "can u list me all modules and their groups", LONG_REPLY), "quiet", ()),
    # the rewrite is checked again: a still-long rewrite goes back once more, then the turn may end
    ("soul", soul("e", "is it done?", LONG_REPLY, rewrite=False), "said", (), SENT_BACK),
    ("soul", soul("e", "is it done?", LONG_REPLY, rewrite=True), "said", (), SENT_BACK),
    ("soul", soul("e", "is it done?", LONG_REPLY, rewrite=True), "quiet", ()),
]


# call_efficiency: count single fast commands; nudge on the third in a row; land one row a session at Stop.

EFFICIENCY_ASKS = [  # asked in this order
    *(("efficiency", dict(bash(command), session_id="s1"), "quiet", ()) for command in ("ls", "cat a.txt")),
    ("efficiency", dict(bash("git status"), session_id="s1"), "said", ("3 single fast commands",),
     {"fields": {("hookSpecificOutput", "hookEventName"): "PostToolUse"}}),
    # a bundle or a real job resets the streak
    *(("efficiency", dict(bash(command), session_id="s2"), "quiet", ())
      for command in ("ls && cat a.txt", "make tests", "ls", "cat b")),
    ("efficiency", {"session_id": "s1"}, "allow", ("3 Bash calls",),
     {"env": lambda world: {"CLAUDE_HOOK": "Stop"}, "rows": (".claude/state/call-efficiency.jsonl", "single_fast", [3])}),
]


# checkout_current: the shared checkout on main catches up with origin/main, and says so when it cannot.

def checkout_world(diverged):
    """A world: checkout_current.py at session start on a shared clone that origin/main passed by three commits, the
    clone (when `diverged`) holding a local commit that conflicts with them; the clone's HEAD tagged `before`."""
    def make(world):
        origin = world / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=GIT_ENV)
        seed = git_repo(world / "seed", {"shared.txt": "one\n"})
        git(seed, "push", "-q", str(origin), "main")
        shared = world / "shared"
        subprocess.run(["git", "clone", "-q", str(origin), str(shared)], check=True, env=GIT_ENV)
        if diverged:
            (shared / "shared.txt").write_text("local\n")
            git(shared, "commit", "-q", "-am", "local")
        for round_number in range(3):
            (seed / "shared.txt").write_text(f"remote {round_number}\n")
            git(seed, "commit", "-q", "-am", f"remote {round_number}")
        git(seed, "push", "-q", str(origin), "main")
        git(shared, "tag", "before")
        return HOOKS / "checkout_current.py", dict(GIT_ENV, CLAUDE_PROJECT_DIR=str(shared),
                                                   CLAUDE_HOOK="SessionStart"), None
    return make


CHECKOUT_ASKS = [  # where the clone then stands, its tracked files as committed
    ("checkout-behind", {"session_id": "s1"}, "allow", (), {"stands_at": ("shared", "origin/main")}),
    ("checkout-diverged", {"session_id": "s2"}, "allow", ("cannot catch itself up",),
     {"stands_at": ("shared", "before")}),
]


# output_cap: a long output goes whole to a file and the agent sees a short summary with its path.

def long_log():
    lines = [f"step {index}: fine, the part settled at rest on the floor" for index in range(400)]
    lines[200] = "ERROR: the bake of part 7 failed"
    lines[250] = "Traceback (most recent call last):"
    return "\n".join(lines)


def cap_bash(command, stdout, stderr="", call="toolu_1", **response):
    return {"tool_name": "Bash", "session_id": "s1", "tool_use_id": call, "tool_input": {"command": command},
            "tool_response": {"stdout": stdout, "stderr": stderr, "interrupted": False, "isImage": False, **response}}


LOG = long_log()
WIDE = "\n".join(f"{index} " + "y" * 900 for index in range(200))  # 181,000 chars of long lines, clipped too
DOCUMENT = {"rows": [{"row": f"r{index}", "copies": 2} for index in range(300)], "place": "wreck"}
SHOWN = ("hookSpecificOutput", "updatedToolOutput")
CAP_ASKS = [  # each spills to {world}/s1/<its call>.txt
    ("cap", cap_bash("python3 tools/usd/settle.py hub", LOG, "a warning on stderr", "toolu_1",
                     returnCodeInterpretation="exit 1"), "said",
     ("{world}/s1/toolu_1.txt", "401 lines",  # 400 log lines and the stderr line
      "step 0: fine,", "a warning on stderr",  # the first and the last lines
      "201: ERROR: the bake of part 7 failed", "251: Traceback"),  # the errors between
     {"lacks": ("step 100: fine,",), "under": len(LOG) / 3,
      "fields": {(*SHOWN, "stderr"): "", (*SHOWN, "interrupted"): False, (*SHOWN, "returnCodeInterpretation"): "exit 1"},
      "holds": {"s1/toolu_1.txt": "$ python3 tools/usd/settle.py hub\n" + LOG + "\n--- stderr ---\na warning on stderr"}}),
    ("cap", cap_bash("python3 diff.py", WIDE, call="toolu_2"), "said", ("more chars]",), {"under": 6000}),
    ("cap", cap_bash("python3 -c 'print(json)'", json.dumps(DOCUMENT, indent=1), call="toolu_3"), "said",
     ("JSON object, 2 keys", "rows: array, 300 items", 'place: "wreck"'),
     {"holds": {"s1/toolu_3.txt": "$ python3 -c 'print(json)'\n" + json.dumps(DOCUMENT, indent=1)}}),
    ("cap", cap_bash("cd /x && cat tools/props/library/route.py", LOG, call="toolu_4"), "said",
     ("whole-file cat of tools/props/library/route.py", "offset, limit")),
    ("cap", cap_bash("sed -n 1,20p a.py; cat big.log", LOG, call="toolu_5"), "said",  # one stage not narrowed
     ("{world}/s1/toolu_5.txt",)),
    # what the agent asked for is left alone, and nothing of it spills
    *(("cap-alone", cap_bash(command, LOG), "quiet", ())
      for command in ("sed -n '1,400p' route.py", "git log -p | head -500", "grep -c x big.log",
                      "awk 'NR>=10 && NR<=400' f", "cd /x; sed -n 1,300p a.py; echo ===; tail -n 200 b.py",
                      "FULL_OUTPUT=1 make tests", "cat tools/props/library/CLAUDE.md",
                      "ls x; cat .claude/skills/grill/SKILL.md", "ls y && cat a/CLAUDE.md 2>/dev/null | head -150")),
    *(("cap-alone", payload, "quiet", ())
      for payload in (cap_bash("ls", "a\nb\n"), cap_bash("cat a.png", LOG, isImage=True),
                      cap_bash("make tests", LOG, backgroundTaskId="b1"),
                      {"tool_name": "Read", "tool_input": {}, "tool_response": {"stdout": LOG}})),
    # A JSON object of 40 keys of 150 characters each (about 6,600 chars): its outline names every key, so the
    # summary is about as long as the output and saves nothing.
    ("cap-alone", cap_bash("python3 report.py", json.dumps({f"k{index:02d}" + "x" * 147: "v" for index in range(40)})),
     "quiet", (), {"holds": {"s1": None}}),
]


# wait_guard: no waiting in the foreground; the project names its own long runs in project.json.

PYTHON_RUN = r"(?:^|\s)\S*python[\w.]*\s+(?:-\S+\s+)*\S*"
WAIT_CONFIG = {"wait_guard": {"foreground_runs": [
    {"run": PYTHON_RUN + r"blender_cloud\.py\b", "unless": r"--dry-run\b", "what": "a cloud Blender run"},
    {"run": PYTHON_RUN + r"settle\.py\b.*--cloud\b", "unless": None, "what": "a cloud Blender run"},
    {"run": PYTHON_RUN + r"review/page\.py\b.*--cloud\b", "unless": r"--no-render\b", "what": "a cloud Blender run"},
], "way_out": "Add --detach."}}


FOREGROUND_WAITS = [
    ("cd /tmp && sleep 300 && cat out.json", "sleep of 300 s"),
    ("make env; sleep 2m", "sleep of 120 s"),
    ("sleep 300; tail -n 20 run.log", "sleep of 300 s"),
    ("while ! test -f done.json; do sleep 30; done; cat done.json", "while loop"),
    ("until scw instance server list | grep -q stopped; do sleep 5; done", "until loop"),
    ("for i in $(seq 60); do kubectl get jobs; sleep 6; done", "for loop"),
    ("python tools/cloud/blender_cloud.py job.json --who me", "cloud Blender run"),
    ("cd wt && ~/.farm-factory-props/env/bin/python tools/cloud/blender_cloud.py j.json --who me > log",
     "cloud Blender run"),
    (".venv/bin/python tools/usd/settle.py stage.usda --cloud", "cloud Blender run"),
    (".venv/bin/python tools/review/page.py hub --run r --out o --cloud", "cloud Blender run"),
    ("timeout 118 tail --pid=394341 -f /dev/null; tail -5 run.log", "tail that follows"),
    ("tail -f run.log", "tail that follows"), ("tail -n 0 -F run.log", "tail that follows"),
    ("timeout 590 tail -F x | grep -m1 y", "tail that follows"),
    ("timeout 58 tail -n +1 --follow=name run.log | grep -m1 EXIT; true", "tail that follows"),
    ("timeout 300 inotifywait -e close_write out.json", "timeout of 300 s around a wait"),
    ("cd wt && timeout 10m gh run watch 12", "timeout of 600 s around a wait"),
    ("timeout 120 bash -c 'wait_for_it; sleep 50'", "timeout of 120 s around a wait"),
]

SHORT_OR_BACKGROUND = [
    bash("sleep 2; ls"), bash("cd x && sleep 60 && ls"),
    bash("for i in 1 2 3; do curl -s x && break; sleep 5; done"),
    bash("python -c 'import time\nwhile True: time.sleep(5)'"), bash("git commit -m 'sleep 600'"),
    bash("python tools/cloud/blender_cloud.py job.json --who me --dry-run"),
    bash("python tools/review/page.py hub --run r --out o --cloud --no-render"), bash("make tests"),
    bash("sed -n 1,60p tools/cloud/blender_cloud.py; grep -n add_argument tools/cloud/blender_cloud.py"),
    bash("grep -n detach tools/cloud/blender_cloud*.py | head -40"), bash("cat tools/usd/settle.py | grep cloud"),
    bash("git diff tools/review/page.py --stat"),
    bash("tail -n 40 run.log"), bash("tail -5 run.log | grep -c x"), bash("timeout 58 sleep 50; ls"),
    bash("timeout 600 .venv/bin/python -m pytest -q tools/x"), bash("grep -c tail-f notes.txt; tail -c 200 x.log"),
    bash("timeout 25 ssh host ls"), bash("timeout 300 bash -c 'make tests'"),
    bash("while true; do sleep 30; done", background=True),
    {"tool_name": "Bash", "tool_input": {"command": "while true; do sleep 60; done", "timeout_ms": 1800000,
                                         "description": "the Monitor tool's watch script"}},
    bash("python tools/cloud/blender_cloud.py job.json --who me", background=True),
    {"tool_name": "Read", "tool_input": {"file_path": "x"}},
]


# every hook: a payload it cannot read never wedges a tool call (never exit 2; md_guard exits 1 on a tool_input that
# is not an object, which the harness also lets through). Shared hooks run as a copy in a scratch folder that is no
# repository, so none of them reads or moves the real checkout.

SHARED_HOOKS = ["issue_guard.py", "md_guard.py", "output_cap.py", "wait_guard.py", "commit_guard.py",
                "torn_commit_guard.py", "leftover_guard.py", "checkout_current.py", "soul_guard.py",
                "call_efficiency.py"]


GARBAGE = ["not json at all {{{", {"tool_name": "Bash"}, {"tool_name": "Bash", "tool_input": "text"},
           bash('gh issue create --title "unterminated'), {"transcript_path": "/nowhere/at/all.jsonl"},
           {"tool_name": "Bash", "tool_input": {"command": "x"}, "tool_response": "text"}]


def open_world(name):
    """A world for a hook fed garbage: a shared hook as a copy in world/scratch (no repository, so it reads and moves
    no real checkout) run there, a local one in place; output_cap spills into the world."""
    def make(world):
        scratch = world / "scratch"
        shared = name in SHARED_HOOKS
        env = dict(GIT_ENV, OUTPUT_CAP_DIR=str(world), CLAUDE_PROJECT_DIR=str(scratch))
        return (hook_copy(scratch, name) if shared else hook(name)), env, scratch if shared else None
    return make


def spill_blocked_world(world):
    """output_cap whose spill folder is a file: the output stays whole."""
    blocker = world / "file"
    blocker.write_text("")
    return HOOKS / "output_cap.py", dict(os.environ, OUTPUT_CAP_DIR=str(blocker)), None


def completion_world(scenes):
    """completion_guard.py in place, its place known with no stage (or, with no scene list at all, matching none)."""
    def make(world):
        env = known_place_env(world)
        if not scenes:
            env = dict(env, SCORE_GUARD_WITHIN=str(world / "none.json"))
        return hook("completion_guard.py"), env, None
    return make


WORLDS = {
    "accept": lambda world: (hook("accept_guard.py"), None, None),
    "completion": completion_world(scenes=True),
    "completion-no-scene": completion_world(scenes=False),  # an empty scene list matched all
    "issue": issue_world(),
    "issue-areas": issue_world(["dev", "art"]),
    "issue-team": issue_world(["dev"], area_label_prefix="team:"),  # the project names its prefix
    "issue-roots": issue_world(environment=listed(ROOTS), backlog_prd=36),
    "issue-open": issue_world(environment=listed(OPEN_WORK)),
    "issue-business": business_world,
    "issue-caps": issue_world(issue_body_caps=CAPS),
    "issue-edit": edit_world,
    "md": lambda world: (md_world(world)[0], None, None),
    "commit": lambda world: (hook_copy(world, "commit_guard.py"), None, None),
    "commit-unlocked": live_world(locked=False),
    "commit-live": live_world(locked=True),
    "wait": lambda world: (hook_copy(world, "wait_guard.py", WAIT_CONFIG), None, None),
    **{f"open-{name}": open_world(name) for name in SHARED_HOOKS + ["accept_guard.py", "completion_guard.py"]},
    "spill-blocked": spill_blocked_world,
    **{f"completion-listed-{event}": listed_completion(event) for event in ("Stop", "SubagentStop")},
    "torn-markers": torn_world({"notes.txt": "a\n<<<<<<< Updated upstream\nb\n=======\nc\n>>>>>>> Stashed changes\n"}),
    "torn-unmade": torn_world({"steps/20-second.sh": 'echo "$made_here $made_nowhere"\n'}, ["steps"], FIRST_STEP),
    "torn-defaulted": torn_world({"steps/20-second.sh": 'echo "$made_here ${made_nowhere:-}"\n'}, ["steps"],
                                 FIRST_STEP),
    "torn-uncommitted": torn_world(READS_FIXTURE, loose=FIXTURE),
    "torn-staged": torn_world({**READS_FIXTURE, **FIXTURE}),
    "torn-dirty": torn_world({"tests/test_kept.py": "from lib import module_kept\n"},
                             loose={"lib/module_kept.py": "VALUE = 2\n"}),
    "gate-grown": gate_world(grown_debt),
    "gate-failing": gate_world(lambda clone: {"tools/zz_gate/holds.py": "VALUE = 2\n"}),
    "gate-clean": gate_world(lambda clone: {"tools/zz_gate/notes.txt": "x\n",
                                            "score/stages/sim_body/inside/rra/note.txt": "x\n"}),
    "gate-away": gate_world(lambda clone: {"tools/zz_gate/notes.txt": "y\n"}, away=True),
    "remade": remade_world,
    "freeze-unnamed": freeze_world("fix"),
    "freeze-one-named": freeze_world("fix\n\nRemakes: light: the hub's lamp was wrong"),
    "freeze-named": freeze_world("fix\n\nRemakes: light@hub, pins: both wrong"),
    "freeze-no-reason": freeze_world("fix\n\nRemakes: light pins:"),
    "freeze-nothing": freeze_world("fix", remade=()),
    "freeze-none": freeze_world("fix", freeze_text=None),
    "freeze-past": freeze_world("fix", freeze_text='{"until": "2000-01-01", "reason": "old"}'),
    "freeze-broken": freeze_world("fix", freeze_text="{not json"),
    "push-cap": cap_world,
    "leftover": leftover_world,
    "soul": lambda world: (HOOKS / "soul_guard.py", None, None),
    "efficiency": lambda world: (hook_copy(world, "call_efficiency.py"), dict(os.environ, CLAUDE_HOOK="PostToolUse"),
                                 None),
    "checkout-behind": checkout_world(diverged=False),
    "checkout-diverged": checkout_world(diverged=True),
    **{name: lambda world: (HOOKS / "output_cap.py", dict(os.environ, OUTPUT_CAP_DIR=str(world)), None)
       for name in ("cap", "cap-alone")},
}
SEQUENTIAL = {"leftover", "soul", "efficiency", "push-cap"}  # worlds whose hook keeps state between calls: asked in row order

# One row a call: (world, payload or payload(world), verdict, words its reason holds (`{world}` the world's folder),
# optional more: env(world) on top, the hook and its folder(world) in place of the world's, seconds it may take, words
# the hook must not say, words its stdout prints, words its reason holds this many times, its stdout's last lines, a
# length its told text stays under, values the JSON it prints holds by key path, files the world then holds (None:
# absent) or begins with, a JSONL file's field values, a ledger's entries other than this test's pushes against the
# world's expected ones, where a repo of the world then stands with its tracked files as committed, and a call made in
# the same world it must answer within TRANSCRIPT_SECONDS of, asked alone TIMED_ROUNDS times each).
ROWS = [
    *(("completion-listed-" + event, stop("listed", f"The {PLACE} is complete now."), "block", (PLACE,),
       {"lacks": ("ModuleNotFoundError",)}) for event in ("Stop", "SubagentStop")),
    *TORN_ASKS, *GATE_ASKS, *FREEZE_ASKS, *CAP_PUSH_ASKS, *LEFTOVER_ASKS, *SOUL_ASKS, *EFFICIENCY_ASKS, *CHECKOUT_ASKS, *CAP_ASKS,
    *(("accept", payload, "block", ("only the owner accepts or rejects",))
      for payload in OWNER_ACTIONS + OWN_LOCKS_AND_STEPS),
    ("accept", ENV_PREFIXED_ACCEPT, "block", ()),
    *(("accept", payload, "allow", ()) for payload in READ_AND_RUN + GRANTED + [LONG_WORDS] + CHAT_ROUTE),
    *(("completion", payload, "block", (PLACE, "unknown")) for payload in FALSE_CLAIMS),
    *(("completion", payload, "allow", ()) for payload in HONEST_STOPS),
    ("completion-no-scene", stop("h", f"The {PLACE} is complete now."), "allow", ()),
    *(("issue", payload, "block", (reason,)) for payload, reason in BARE_OR_DESTRUCTIVE),
    *(("issue", payload, "allow", ()) for payload in COMPLETE_OR_ORDINARY),
    *AREA_ASKS, *OPEN_WORK_ASKS, *BODY_ASKS,
    *(("md", payload, "block", ("go-ahead",)) for payload in NEW_MD_WITHOUT_A_YES),
    *(("md", payload, "allow", ()) for payload in STANDING_EXCEPTIONS),
    *MD_TIMED,
    *COMMIT_ASKS,
    *(("wait", bash(command), "block",
       (reason, "run_in_background") + (("Add --detach.",) if "cloud" in reason else ()))
      for command, reason in FOREGROUND_WAITS),
    *(("wait", payload, "allow", ()) for payload in SHORT_OR_BACKGROUND),
    # never exit 2 and say nothing on what a hook cannot read; md_guard exits 1 on a tool_input that is no object
    *((f"open-{name}", payload, "open", ())
      for name in SHARED_HOOKS + ["accept_guard.py", "completion_guard.py"] for payload in GARBAGE),
    ("spill-blocked", cap_bash("make tests", LOG), "quiet", ()),
]
NAMES = [f"{index:03d}-{row[0]}-{row[2]}" for index, row in enumerate(ROWS)]


def spoken(out):
    """Every string the JSON a hook printed holds, one a line; None when it printed no JSON."""
    def strings(value):
        if isinstance(value, dict):
            return [text for item in value.values() for text in strings(item)]
        if isinstance(value, list):
            return [text for item in value for text in strings(item)]
        return [value] if isinstance(value, str) else []
    try:
        return "\n".join(strings(json.loads(out)))
    except ValueError:
        return None


VERDICTS = {  # (exit code, stderr, stdout, words) -> the row holds
    "block": lambda code, said, out, words: code == BLOCK and all(word in said for word in words),
    "refuse": lambda code, said, out, words: code == 1 and all(word in said for word in words),
    "allow": lambda code, said, out, words: code == ALLOW and all(word in said for word in words),
    "said": lambda code, said, out, words: code == ALLOW and spoken(out) is not None and all(
        word in spoken(out) for word in words),
    "open": lambda code, said, out, words: code != BLOCK and out.strip() == "",
    "quiet": lambda code, said, out, words: (code, out) == (ALLOW, ""),
}
ANSWER_SECONDS = 20  # a hook that has not answered by then hangs: the harness would fail it open


def made(value, world):
    return value(world) if callable(value) else value


def ask(script, payload, env, cwd, seconds):
    """run(...) of one call, or (None, why, "") when the hook gives no answer within `seconds`."""
    try:
        return run(script, payload, env=env, cwd=cwd, timeout=seconds)
    except subprocess.TimeoutExpired:
        return None, f"no answer in {seconds} s", ""


def timed(call, baseline):
    """The last answer to `call` asked alone TIMED_ROUNDS times, each beside `baseline`; with how much longer than the
    baseline its quickest took, and every exit code of both."""
    timings, starts, codes = [], [], []
    for _ in range(TIMED_ROUNDS):
        started = time.monotonic()
        answer = ask(*call)
        timings.append(time.monotonic() - started)
        codes.append(answer[0])
        started = time.monotonic()
        codes.append(ask(*baseline)[0])
        starts.append(time.monotonic() - started)
    return (*answer, (min(timings) - min(starts), codes))


@pytest.fixture(scope="module")
def answers(tmp_path_factory):
    """Every row's (exit code, stderr, stdout, its world's folder, its timing or None): each world made once in a
    scratch folder of its own, every call asked side by side, a sequential world's calls in row order, a timed call
    alone after them."""
    folders = {name: tmp_path_factory.mktemp(name) for name in WORLDS}
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        worlds = dict(zip(WORLDS, pool.map(lambda name: (folders[name], *WORLDS[name](folders[name])), WORLDS)))
    calls, turns, alone = [], {}, {}
    for index, (world, payload, _, _, *more) in enumerate(ROWS):
        folder, script, env, cwd = worlds[world]
        more = more[0] if more else {}
        if "env" in more:
            env = {**(env or os.environ), **more["env"](folder)}
        if "hook" in more:
            script, cwd = more["hook"](folder)
        seconds = more.get("seconds", ANSWER_SECONDS)
        calls.append((script, made(payload, folder), env, cwd, seconds))
        if "timed" in more:
            alone[index] = (script, made(more["timed"], folder), env, cwd, seconds)
        else:
            turns.setdefault(world if world in SEQUENTIAL else index, []).append(index)

    def asked(indices):
        return [(*ask(*calls[index]), None) for index in indices]
    found = [None] * len(ROWS)
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for indices, said in zip(turns.values(), pool.map(asked, turns.values())):
            for index, answer in zip(indices, said):
                found[index] = answer
    for index, baseline in alone.items():
        found[index] = timed(calls[index], baseline)
    return [(*answer[:3], worlds[ROWS[index][0]][0], answer[3]) for index, answer in enumerate(found)]


@pytest.mark.parametrize("row", range(len(ROWS)), ids=NAMES)
def test_hooks_block_only_their_rule_and_fail_open(answers, row):
    """Each hook, asked as the harness asks it, blocks the calls its rule names with that rule's reason, lets every
    other call through, says what it says once and only where its rule asks, leaves its world as the rule says, and
    fails open on what it cannot read."""
    _, _, verdict, words, *extra = ROWS[row]
    more = extra[0] if extra else {}
    code, said, out, folder, timing = answers[row]
    words = [word.replace("{world}", str(folder)) for word in words]
    why = (NAMES[row], words, code, said[-600:], out[-300:])
    assert VERDICTS[verdict](code, said, out, words), why
    told = said + (spoken(out) or "")
    assert not [word for word in more.get("lacks", ()) if word in told], why
    assert all(word in out for word in more.get("prints", ())), why
    assert all(said.count(word) == count for word, count in more.get("times", {}).items()), why
    if "tail" in more:
        assert out.strip().splitlines()[-len(more["tail"]):] == more["tail"], why
    assert len(spoken(out) or "") < more.get("under", math.inf), why
    for path, value in more.get("fields", {}).items():
        assert functools.reduce(lambda node, key: node[key], path, json.loads(out)) == value, (path, why)
    for path, text in more.get("holds", {}).items():
        there = folder / path
        assert (there.read_text() if there.is_file() else there.exists() or None) == text, (path, why)
    for path, start in more.get("begins", {}).items():
        assert (folder / path).is_file() and (folder / path).read_text().startswith(start), (path, why)
    if "ledger" in more:
        ledger, expected = (json.loads((folder / path).read_text()) for path in more["ledger"])
        entries = [entry for day in ledger.values() for entry in day if entry["sha"] != "1" * 40]
        assert [[entry["repo"], entry["sha"], entry["at"]] for entry in entries] == expected, (entries, why)
    if "timed" in more:
        gap, codes = timing
        assert gap < TRANSCRIPT_SECONDS and codes == [ALLOW] * 2 * TIMED_ROUNDS, (timing, why)
    if "rows" in more:
        path, field, values = more["rows"]
        assert [json.loads(line)[field] for line in (folder / path).read_text().splitlines()] == values, why
    if "stands_at" in more:
        repo, ref = more["stands_at"]
        assert git(folder / repo, "rev-parse", "HEAD") == git(folder / repo, "rev-parse", ref), why
        assert not git(folder / repo, "status", "--porcelain", "-uno"), why
