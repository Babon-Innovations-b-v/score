"""The push gate (moved.py, `score moved`, .githooks/pre-push-moved) names exactly the paid rows a change would buy
again, each with its price and why, and refuses a push to main only for the rows that push moves and no Moved-rows
trailer names with a reason; drift already on main is a warning, a move no file explains (a params, contract or
model change) is refused like any other, and the hook leaves no process or checkout behind.

A toy git repository stands in for this one (moved.REPO, _code.REPO): a paid render whose make sits in it and imports
a framework file, a paid bake, each reading a data file of its own, and a paid film reading an unpaid drawing of a
third data file. The hook itself is run against a toy repository whose score package only records what it was given.

Faults it guards (2026-10-17): about EUR 65 of re-buys (view maps, turntables, the cockpit library push) came from
code and data changes nobody saw would move a paid row's key before they were pushed (8b402226: blender_cloud.py,
outside every code version but declared by the turntables; 1f90a0fe: new gap files a paid row declares). The first
hook refused every push over drift already on main, refused branch deletions and took any trailer as leave for every
row; its second form let a framework-only push through unchecked and only warned of a move no file explains. The two
tests that worked out the real commits 8b402226 and 1f90a0fe took two minutes (and the first no longer held on
today's table): the toy's declared data files hold the same rule, a file a row declares moves it.

Breaks that turn it red (each applied once and seen red, then reverted):
- `total`: `sum(row.euros ...)` read as `sum(0 * row.euros ...)`  -> the price-and-why test ("about EUR 3.00").
- `main_pushes`: `ref == MAIN and` dropped  -> test_only_pushes_to_main_are_checked.
- `trailer_nodes`: `and why.strip()` dropped  -> test_a_trailer_names_a_row_only_among_its_nodes_and_with_a_reason.
- `split`: the pushed rows' `if base is None or row.node not in known...` dropped  -> the drift tests (drift refused).
- `unexplained`: `not named_in(...)` read as `named_in(...)`  -> test_a_trailer_lets_only_the_rows_it_names_go.
- `edited_into_framework`: `after - before` read as `before - after`  -> the framework-move test.
- .githooks/pre-push-moved: its `trap '... worktree remove ...' EXIT` line made a no-op  -> the changed-tree hook test
  (the checkout is left behind).
"""
import contextlib
import importlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.graph import _code  # noqa: E402
from score.stages import moved  # noqa: E402
from score.store import Store  # noqa: E402


def test_a_file_moved_into_framework_and_edited_in_the_same_change_is_named():
    """A module moved into FRAMEWORK and edited in the same change makes the rows that read it again (no narrowing
    carry): it is named, a plain move is not."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="moved_repo_")).resolve()
    (repo / "score" / "graph").mkdir(parents=True)
    declared = repo / "score" / "graph" / "_code.py"

    def commit(framework, helpers):
        declared.write_text(f"FRAMEWORK = {{REPO / name for name in {framework!r}}}\n")
        for name, text in helpers.items():
            (repo / name).write_text(text)
        for command in (["add", "."], ["-c", "user.name=test", "-c", "user.email=test@test", "commit", "-qm", "step"],
                        ["rev-parse", "HEAD"]):
            done = subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True, text=True)
        return done.stdout.strip()

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    saved = _code.REPO
    _code.REPO = repo
    try:
        first = commit((), {"plain.py": "A = 1\n", "edited.py": "B = 1\n"})
        second = commit(("plain.py", "edited.py"), {"edited.py": "B = 2\n"})
        assert moved.edited_into_framework(first, second) == ["edited.py"]
    finally:
        _code.REPO = saved


TEXT = contracts.Contract("toy-text", 1, lambda folder: [])
RENDER_MAKE = """import toy_frame


def make(inputs, out, seed, params):
    (out / "text.txt").write_text(toy_frame.WORD + inputs["brief"].read_text())
"""


def make_copy(inputs, out, seed, params):
    (out / "text.txt").write_text(inputs["brief"].read_text())


def make_film(inputs, out, seed, params):
    (out / "text.txt").write_text((inputs["draw"] / "text.txt").read_text())


def judge_said(output, inputs, evidence):
    return checks.Verdict("said", checks.PASS, "a text was written")


SAID = (checks.Check("said", judge_said),)


def git(repo, *words):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=toy", "-c", "user.email=toy@example.com",
                           *words], capture_output=True, text=True, check=True).stdout.strip()


def committed(repo, message="toy"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def command():
    from score import __main__
    return __main__


@contextlib.contextmanager
def toy():
    """A git repository standing in for this one (the render's make, a framework file it imports, three data files)
    for the time of a `with`; the framework's globals and the command's hooks are put back afterwards."""
    main = command()
    kept = (_code.REPO, _code.FRAMEWORK, moved.REPO, list(sys.path), compute.books_refusal,
            main.every_world_moved, moved.base_rebuys)
    repo = pathlib.Path(tempfile.mkdtemp()).resolve()
    git(repo, "init", "-q")
    (repo / "toy_render.py").write_text(RENDER_MAKE)
    (repo / "toy_frame.py").write_text('WORD = "made: "\n')
    (repo / ".gitignore").write_text("__pycache__/\n")  # an import's bytecode is no change to the tree
    (repo / "render.txt").write_text("a hall")
    (repo / "bake.txt").write_text("a hall's light")
    (repo / "draw.txt").write_text("a hall's plan")
    committed(repo)
    _code.REPO = moved.REPO = repo
    _code.FRAMEWORK = _code.FRAMEWORK | {repo / "toy_frame.py"}
    compute.books_refusal = lambda: None  # the month's books are compute_test's; not this one's
    sys.path.insert(0, str(repo))
    _code.search_folders.cache_clear()
    sys.modules.pop("toy_render", None)
    sys.modules.pop("toy_frame", None)
    try:
        yield repo
    finally:
        (_code.REPO, _code.FRAMEWORK, moved.REPO, sys.path[:], compute.books_refusal,
         main.every_world_moved, moved.base_rebuys) = kept
        _code.search_folders.cache_clear()


def a_runner(repo, store, bake_params=None):
    render = graph.Stage("render", "place", importlib.import_module("toy_render").make, TEXT, SAID,
                         files={"brief": "{data}/render.txt"}, paid=True, euros=4.0)
    bake = graph.Stage("bake", "place", make_copy, TEXT, SAID, files={"brief": "{data}/bake.txt"}, paid=True,
                       euros=3.0, params=bake_params or {})
    draw = graph.Stage("draw", "place", make_copy, TEXT, SAID, files={"brief": "{data}/draw.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, SAID, after={"draw": ("toy-text", 1)}, paid=True, euros=2.0)
    return graph.Runner([render, bake, draw, film], graph.Environment("toy", 1, {"data": repo}), store,
                        model_record=lambda kind: {"kind": kind})


def made(repo):
    """Every row made and accepted at the toy repository's commit; their store."""
    store = Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(repo, store)
    for stage in runner.stages.values():
        assert "accepted automatically" in runner.run_node(stage, "hangar"), stage.name
    return store


def rows(repo, store, **table):
    runner = a_runner(repo, store, **table)
    return {"toy": moved.rebuys(runner, list(runner.nodes(["hangar"])))}


def nodes(rows_by_world):
    """{world: [node]}: what base_rebuys gives for a commit."""
    return {world: [row.node for row in found] for world, found in rows_by_world.items()}


def exit_code(call, *args):
    """What `call` printed and its exit code (0 when it returned)."""
    with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()) as said:
        try:
            call(*args)
        except SystemExit as stop:  # sys.exit("message") prints its message and exits 1
            message = stop.code if isinstance(stop.code, str) else ""
            return printed.getvalue() + said.getvalue() + message, 1 if message else stop.code
    return printed.getvalue() + said.getvalue(), 0


def pushed(repo, message, files):
    """Commit `files` ({name: text}) over the toy repository's tip; (the git push line to main, tip)."""
    base = git(repo, "rev-parse", "HEAD")
    for name, text in files.items():
        (repo / name).write_text(text)
    tip = committed(repo, message)
    return f"refs/heads/main {tip} refs/heads/main {base}", tip


def test_nothing_changed_lists_nothing_and_passes():
    with toy() as repo:
        found = rows(repo, made(repo))
        assert found == {"toy": []} and exit_code(command().moved_check, found)[1] == 0


def test_a_file_read_by_one_paid_row_lists_that_row_with_its_price_and_why():
    with toy() as repo:
        store = made(repo)
        (repo / "bake.txt").write_text("a hall's brighter light")
        found = rows(repo, store)
        assert [(row.node, row.euros, row.why) for row in found["toy"]] == [("bake@hangar", 3.0, "brief changed")]
        printed, code = exit_code(command().moved_check, found)
        assert code == moved.MOVED_EXIT and "toy bake@hangar: EUR 3.00, brief changed" in printed
        assert "about EUR 3.00" in printed


def test_a_framework_only_edit_lists_nothing():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_frame.py").write_text('WORD = "made by the framework: "\n')
        assert rows(repo, store) == {"toy": []}


def test_a_row_moved_through_what_it_reads_is_listed():
    with toy() as repo:
        store = made(repo)
        (repo / "draw.txt").write_text("a hall's new plan")
        found = rows(repo, store)
        assert [(row.node, row.euros, row.why) for row in found["toy"]] == [("film@hangar", 2.0, "reads draw@hangar")]


def test_only_pushes_to_main_are_checked():
    tip, base = "a" * 40, "b" * 40
    lines = [f"refs/heads/main {moved.ZERO} refs/heads/main {base}",  # a deletion
             f"refs/tags/v1 {tip} refs/tags/v1 {moved.ZERO}",
             f"refs/heads/side {tip} refs/heads/side {base}"]
    assert moved.main_pushes(lines) == []
    printed, code = exit_code(command().pre_push_check, lines)
    assert code == 0 and "nothing pushed to main" in printed
    assert moved.main_pushes(lines + [f"HEAD {tip} refs/heads/main {base}"]) == [(tip, base)]


def test_a_push_is_refused_only_for_the_rows_it_moves_and_drift_is_a_warning():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_render.py").write_text(RENDER_MAKE + "\n# moved before this push\n")
        committed(repo, "render: already on main")
        base = nodes(rows(repo, store))
        pushed(repo, "data: a brighter hall", {"bake.txt": "a hall's brighter light"})
        found = rows(repo, store)
        assert base == {"toy": ["render@hangar"]} and [row.node for row in found["toy"]] == ["render@hangar",
                                                                                              "bake@hangar"]
        printed, code = exit_code(command().pushed_check, found, base, [])
        assert code == moved.MOVED_EXIT
        assert "warning, not refused" in printed and "toy render@hangar: EUR 4.00, code changed" in printed
        assert "Moved-rows: bake@hangar: <why>" in printed and "render@hangar: <why>" not in printed
        assert "EUR 0" in printed  # the refusal says a cached Google ask is never refused


def test_drift_alone_lets_the_push_go():
    with toy() as repo:
        store = made(repo)
        (repo / "toy_render.py").write_text(RENDER_MAKE + "\n# moved before this push\n")
        committed(repo, "render: already on main")
        base = nodes(rows(repo, store))
        pushed(repo, "notes", {"notes.txt": "nothing a row reads"})
        printed, code = exit_code(command().pushed_check, rows(repo, store), base, [])
        assert code == 0 and "warning, not refused" in printed


def test_a_move_no_file_explains_is_refused():
    """A stage table edit (a row's params here; a contract, a model or an after alike) moves the row with no file of
    its own changed: refused like any other, never a warning."""
    with toy() as repo:
        store = made(repo)
        base = nodes(rows(repo, store))
        found = rows(repo, store, bake_params={"light": 2})
        assert [(row.node, row.why) for row in found["toy"]] == [("bake@hangar", "params changed")]
        printed, code = exit_code(command().pushed_check, found, base, [])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert "warning, not refused" not in printed


def test_when_mains_commit_cannot_be_worked_out_every_moved_row_counts_as_the_pushes():
    with toy() as repo:
        store = made(repo)
        (repo / "bake.txt").write_text("a hall's brighter light")
        printed, code = exit_code(command().pushed_check, rows(repo, store), None, [])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert "could not be worked out" in printed


def test_base_rebuys_is_none_for_a_new_ref_an_unknown_commit_or_a_failing_tree_and_leaves_nothing_behind():
    with toy() as repo:
        left = set(repo.parent.glob("moved-*"))
        assert moved.base_rebuys(moved.ZERO) is None
        assert moved.base_rebuys("f" * 40) is None  # no such commit here
        assert moved.base_rebuys(git(repo, "rev-parse", "HEAD")) is None  # the toy has no score package to run
        assert set(repo.parent.glob("moved-*")) == left
        assert len(git(repo, "worktree", "list").splitlines()) == 1


def test_a_trailer_lets_only_the_rows_it_names_go():
    with toy() as repo:
        store = made(repo)
        base = nodes(rows(repo, store))
        line, tip = pushed(repo, "data: a brighter hall and a new plan\n\nMoved-rows: bake@hangar: the owner asked",
                           {"bake.txt": "a hall's brighter light", "draw.txt": "a hall's new plan"})
        found = rows(repo, store)
        pushes = moved.main_pushes([line])
        reasons = moved.pushed_reasons(pushes)
        assert reasons == ["bake@hangar: the owner asked"]
        printed, code = exit_code(command().pushed_check, found, base, reasons)
        assert code == moved.MOVED_EXIT and "Moved-rows: film@hangar: <why>" in printed
        assert moved.pushed_reasons([(tip, moved.ZERO)]) == reasons  # a new remote ref: commits on no remote yet
        assert not moved.named_in("bake@hangar", ["x"]) and not moved.named_in("bake@hang", reasons)
        printed, code = exit_code(command().pushed_check, found, base, reasons + ["film@hangar: a new plan"])
        assert code == 0 and "Moved-rows: bake@hangar: the owner asked" in printed


def test_a_trailer_names_a_row_only_among_its_nodes_and_with_a_reason():
    """"Moved-rows: <node> ...: <reason>": a node with no reason, or one only in another row's reason, is not named."""
    assert moved.named_in("bake@hangar", ["bake@hangar film@hangar: the owner asked"])
    assert moved.named_in("film@hangar", ["bake@hangar, film@hangar: the owner asked"])
    assert not moved.named_in("bake@hangar", ["bake@hangar"])
    assert not moved.named_in("bake@hangar", ["bake@hangar:  "])
    assert not moved.named_in("bake@hangar", ["film@hangar: it reads bake@hangar"])


def test_pre_push_checks_the_pushed_commit_against_mains_not_a_changed_tree():
    with toy() as repo:
        store = made(repo)
        line, tip = pushed(repo, "data: a brighter hall", {"bake.txt": "a hall's brighter light"})
        main = command()
        worked_out, bases = [], []
        main.every_world_moved = lambda: worked_out.append(1) or rows(repo, store)
        moved.base_rebuys = lambda remote: bases.append(remote) or {"toy": []}
        (repo / "draw.txt").write_text("not committed")
        printed, code = exit_code(main.pre_push_check, [line])
        assert code != 0 and "clean checkout" in printed and worked_out == []
        git(repo, "checkout", "--", "draw.txt")
        printed, code = exit_code(main.pre_push_check, [line])
        assert code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed
        assert worked_out == [1] and bases == [line.split()[3]]


def test_a_framework_only_push_is_still_checked():
    """The stage table is a framework file left out of every code version, yet it sets every row's params, contract,
    models and after: a push of it alone is worked out like any other."""
    with toy() as repo:
        store = made(repo)
        line, _ = pushed(repo, "framework", {"toy_frame.py": 'WORD = "made by the framework: "\n'})
        main = command()
        worked_out = []
        main.every_world_moved = lambda: worked_out.append(1) or rows(repo, store, bake_params={"light": 2})
        moved.base_rebuys = lambda remote: {"toy": []}
        printed, code = exit_code(main.pre_push_check, [line])
        assert worked_out == [1] and code == moved.MOVED_EXIT and "Moved-rows: bake@hangar: <why>" in printed


HOOK = REPO / ".githooks/pre-push-moved"
RECORDER = """import json, os, pathlib, sys
pathlib.Path(os.environ["HOOK_RECORD"]).write_text(json.dumps({"cwd": os.getcwd(), "argv": sys.argv[1:],
    "stdin": sys.stdin.read(), "python": sys.executable}))
sys.exit(int(os.environ.get("HOOK_EXIT", "0")))  # stands in for: score moved --pre-push
"""


STALLED = """import os, pathlib, sys
del sys.modules["score"]  # this toy package: the real score command is loaded in its place
sys.path.insert(0, os.environ["SCORE_REPO"])
from score import __main__ as real
from score.stages import moved
moved.REPO = pathlib.Path.cwd()
sleeper = "import os, pathlib, time; pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(600)"
real.every_world_moved = lambda: moved.snapshot("HEAD", sleeper % os.environ["HOOK_RECORD"])
real.main(["moved", "--pre-push"])  # never --pre-push --again
"""


def hook_repo(command_text=RECORDER):
    """A toy repository whose score package records how the hook ran it (or runs `command_text`), with its own .venv
    python; it sits alone in a folder of its own, where moved.snapshot puts its checkouts."""
    repo = pathlib.Path(tempfile.mkdtemp()).resolve() / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "score").mkdir()
    (repo / "score/__init__.py").write_text("")
    (repo / "score/__main__.py").write_text(command_text)
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(sys.executable)
    committed(repo)
    return repo


def hook(where, push_lines, exit_with=0, temp=None, env=None):
    """Run .githooks/pre-push-moved in `where` (with `env` added to its environment); (its exit code, its output, the
    recorder's record or None)."""
    record = pathlib.Path(tempfile.mkdtemp()) / "record.json"
    ran = subprocess.run(["bash", str(HOOK), "origin", "toy"], cwd=where, input="\n".join(push_lines) + "\n",
                         capture_output=True, text=True,
                         env={**os.environ, "HOOK_RECORD": str(record), "HOOK_EXIT": str(exit_with),
                              **({"TMPDIR": str(temp)} if temp else {}), **(env or {})})
    return ran.returncode, ran.stdout + ran.stderr, json.loads(record.read_text()) if record.exists() else None


def test_the_hook_is_off_until_the_owner_turns_it_on():
    repo = hook_repo()
    tip = git(repo, "rev-parse", "HEAD")
    line = f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"
    assert hook(repo, [line]) == (0, "", None)
    git(repo, "config", "score.movedCheck", "true")
    code, _, record = hook(repo, [line])
    assert code == 0 and record["cwd"] == str(repo) and record["argv"] == ["moved", "--pre-push"]
    assert record["stdin"] == line + "\n"
    assert hook(repo, [line], exit_with=3)[0] == 3


def test_the_hook_passes_deletions_tags_and_other_branches_at_once():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tip = git(repo, "rev-parse", "HEAD")
    for line in (f"(delete) {moved.ZERO} refs/heads/main {tip}", f"refs/tags/v1 {tip} refs/tags/v1 {moved.ZERO}",
                 f"refs/heads/side {tip} refs/heads/side {moved.ZERO}"):
        assert hook(repo, [line], exit_with=3) == (0, "", None), line


def test_the_hook_checks_a_changed_tree_in_a_worktree_of_the_pushed_commit():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tip = git(repo, "rev-parse", "HEAD")
    (repo / "loose.txt").write_text("not committed")
    code, _, record = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and record["cwd"] != str(repo)
    assert not pathlib.Path(record["cwd"]).exists()  # removed afterwards
    assert len(git(repo, "worktree", "list").splitlines()) == 1


def test_the_hook_refuses_and_leaves_nothing_when_no_worktree_can_be_made():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    temp = pathlib.Path(tempfile.mkdtemp())
    code, printed, record = hook(repo, [f"refs/heads/main {'f' * 40} refs/heads/main {moved.ZERO}"], temp=temp)
    assert code != 0 and record is None and "refused" in printed
    assert list(temp.iterdir()) == [] and len(git(repo, "worktree", "list").splitlines()) == 1


def test_the_hook_skips_a_commit_made_before_score_moved():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    (repo / "score/__main__.py").write_text(RECORDER.replace("score moved --pre-push", "an older command"))
    tip = committed(repo, "before score moved")
    code, printed, record = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and "predates score moved" in printed and record is None


def gone(pid):
    """True once process `pid` has ended (waited for up to 10 s)."""
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


def test_a_hook_that_runs_out_of_time_leaves_no_process_or_checkout_behind():
    """score.movedTimeout ends the check with SIGTERM while it works out a commit in a checkout of its own: the child
    it started ends and the checkout is removed, its folder and git's record of it alike (review, 2026-10-17: SIGTERM
    killed the Python before its `finally` ran, leaving 10 to 12 moved-* worktrees)."""
    repo = hook_repo(STALLED)
    python = repo / ".venv/bin/python"  # this environment's own python (a bare link to it would leave the venv)
    python.unlink()
    python.write_text(f'#!/usr/bin/env bash\nexec {sys.executable} "$@"\n')
    python.chmod(0o755)
    git(repo, "config", "score.movedCheck", "true")
    git(repo, "config", "score.movedTimeout", "15")
    tip = git(repo, "rev-parse", "HEAD")
    code, printed, sleeper = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"],
                                  env={"SCORE_REPO": str(REPO)})  # the sleeper's record is its pid
    assert code != 0 and "ran past 15 s" in printed and isinstance(sleeper, int), printed
    assert gone(sleeper)
    assert sorted(path.name for path in repo.parent.iterdir()) == ["repo"]
    assert len(git(repo, "worktree", "list", "--porcelain").split("worktree ")) == 2


def test_the_hook_gives_the_check_an_hour_unless_told_otherwise():
    """Two commits worked out, every world each, took past 15 minutes under load (review, 2026-10-17): the default
    must not refuse every push to main."""
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    shim = pathlib.Path(tempfile.mkdtemp())
    (shim / "timeout").write_text(f'#!/usr/bin/env bash\necho "$1" > "$TIMEOUT_RECORD"\n'
                                  f'exec {shutil.which("timeout")} "$@"\n')
    (shim / "timeout").chmod(0o755)
    limit = shim / "limit.txt"
    tip = git(repo, "rev-parse", "HEAD")
    code, _, _ = hook(repo, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"],
                      env={"PATH": f"{shim}:{os.environ['PATH']}", "TIMEOUT_RECORD": str(limit)})
    assert code == 0 and limit.read_text().strip() == "3600"


def test_a_worktree_hook_uses_the_main_checkouts_python():
    repo = hook_repo()
    git(repo, "config", "score.movedCheck", "true")
    tree = pathlib.Path(tempfile.mkdtemp()).resolve() / "tree"
    git(repo, "worktree", "add", "-q", "--detach", str(tree))
    tip = git(tree, "rev-parse", "HEAD")
    code, _, record = hook(tree, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
    assert code == 0 and record["cwd"] == str(tree) and record["python"] == str(repo / ".venv/bin/python")
    shutil.rmtree(tree)

