"""The repository's conftest.py refuses a pytest run that could touch the real runtime: PROPS_HOME unset, the real
home, the temp folder itself or anywhere outside it, or a PROPS_WORK outside the temp folder (a test unlinked the real
cloud ledger, 2026-10-17). Driven from outside, as `make tests` runs pytest."""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
TARGET = ".claude/scripts/tests/test_gate_scope.py"  # any test file of this repository: only collected here


def guard():
    """The repository's conftest.py as a module."""
    spec = importlib.util.spec_from_file_location("repo_conftest", REPO / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def collect(home, work=None):
    """pytest collecting one test file of the repository with PROPS_HOME `home` (None: unset); (exit code, output)."""
    environ = {name: value for name, value in os.environ.items() if name not in ("PROPS_HOME", "PROPS_WORK")}
    environ.update({"PROPS_HOME": home} if home else {})
    environ.update({"PROPS_WORK": work} if work else {})
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only", TARGET],
                          cwd=REPO, env=environ, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def test_the_guard_names_every_home_outside_a_sandbox():
    module, temp = guard(), tempfile.gettempdir()
    sandbox = tempfile.mkdtemp()
    assert module.sandbox_refusal({}) == "PROPS_HOME is not set"
    for home in (str(pathlib.Path.home() / ".farm-factory-props"), temp, "/"):
        assert "is not a folder of its own" in module.sandbox_refusal({"PROPS_HOME": home})
    assert module.sandbox_refusal({"PROPS_HOME": sandbox}) is None
    assert "PROPS_WORK" in module.sandbox_refusal({"PROPS_HOME": sandbox, "PROPS_WORK": str(pathlib.Path.home())})
    assert module.sandbox_refusal({"PROPS_HOME": sandbox, "PROPS_WORK": f"{sandbox}/work"}) is None


def test_a_run_without_a_sandbox_home_stops_before_collecting():
    for home in (None, str(pathlib.Path.home() / ".farm-factory-props")):
        code, said = collect(home)
        assert code == 4 and "refused" in said and "test_gate_scope" not in said, said


def test_a_run_in_a_sandbox_home_goes_on():
    code, said = collect(tempfile.mkdtemp())
    assert code == 0, said


def sandbox_script():
    """.claude/scripts/sandbox-home.py as a module."""
    spec = importlib.util.spec_from_file_location("sandbox_home", REPO / ".claude/scripts/sandbox-home.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_home():
    """A stand-in real home: world data (work/) and state (cloud/ledger.jsonl), the ledger read-only."""
    real = pathlib.Path(tempfile.mkdtemp()) / "home"
    (real / "work").mkdir(parents=True)
    (real / "work" / "seed.txt").write_text("seed")
    (real / "cloud").mkdir()
    (real / "cloud" / "ledger.jsonl").write_text("{}\n")
    return real


def test_a_test_reads_world_data_and_writes_only_its_own_home():
    module, real = sandbox_script(), fake_home()
    if module.read_only_command(real, ["true"]) is None:
        return  # no bubblewrap here: nothing is linked, covered below
    script = ("import os, pathlib; home = pathlib.Path(os.environ['PROPS_HOME']);"
              "assert (home / 'work' / 'seed.txt').read_text() == 'seed';"
              "assert not (home / 'cloud').exists();"
              "(home / 'cloud').mkdir(); (home / 'cloud' / 'ledger.jsonl').write_text('mine');"
              "(home / 'store-tests').mkdir(); (home / 'store-tests' / 'kept').write_text('x');"
              "os.chmod(home / 'store-tests' / 'kept', 0o444); os.chmod(home / 'store-tests', 0o555);"
              "import sys; pathlib.Path(sys.argv[1]).write_text(str(home))")
    said = pathlib.Path(tempfile.mkdtemp()) / "home.txt"
    assert module.run([sys.executable, "-c", script, str(said)], real) == 0
    assert (real / "cloud" / "ledger.jsonl").read_text() == "{}\n"
    assert (real / "work" / "seed.txt").read_text() == "seed"
    assert not pathlib.Path(said.read_text()).exists()


def test_a_write_through_a_link_fails_and_the_real_home_stands():
    module, real = sandbox_script(), fake_home()
    if module.read_only_command(real, ["true"]) is None:
        return
    script = "import os, pathlib; (pathlib.Path(os.environ['PROPS_HOME']) / 'work' / 'seed.txt').write_text('gone')"
    assert module.run([sys.executable, "-c", script], real) != 0
    assert (real / "work" / "seed.txt").read_text() == "seed"
    remove = "import os, pathlib; (pathlib.Path(os.environ['PROPS_HOME']) / 'work' / 'seed.txt').unlink()"
    module.run([sys.executable, "-c", remove], real)  # removes at most the sandbox's own link
    assert (real / "work" / "seed.txt").read_text() == "seed"


def test_a_test_adds_its_own_work_folder_beside_the_real_ones():
    """Fault (2026-10-18 review): work/ was one link, so a test making a folder in it (carry.py's commits, a ship
    build's plan) failed on the read-only real home."""
    module, real = sandbox_script(), fake_home()
    if module.read_only_command(real, ["true"]) is None:
        return
    (real / "work" / "carry-commits" / "old").mkdir(parents=True)
    script = ("import os, pathlib; work = pathlib.Path(os.environ['PROPS_HOME']) / 'work';"
              "assert (work / 'seed.txt').read_text() == 'seed' and (work / 'carry-commits' / 'old').is_dir();"
              "(work / 'mine').mkdir(); (work / 'carry-commits' / 'new').mkdir();"
              "assert (pathlib.Path(os.environ['PROPS_HOME']) / 'store' / 'cache').is_dir()")
    assert module.run([sys.executable, "-c", script], real) == 0
    assert sorted(entry.name for entry in (real / "work").iterdir()) == ["carry-commits", "seed.txt"]
    assert [entry.name for entry in (real / "work" / "carry-commits").iterdir()] == ["old"]


def test_without_bubblewrap_nothing_is_linked():
    module, real = sandbox_script(), fake_home()
    sandbox = module.make_sandbox(real, link=False)
    try:
        assert [entry.name for entry in sandbox.iterdir()] == ["store"]
    finally:
        module.remove(sandbox)
    linked = module.make_sandbox(real, link=True)
    try:
        assert sorted(entry.name for entry in linked.iterdir()) == ["store", "work"]
    finally:
        module.remove(linked)
    assert (real / "work" / "seed.txt").read_text() == "seed" and not linked.exists()


def test_a_spend_store_outside_the_temp_folder_is_refused():
    """kept.py's and preflight.py's folders prefer SCORE_SPEND_STORE over PROPS_HOME (2026-10-18 review)."""
    module, sandbox = guard(), tempfile.mkdtemp()
    real_store = str(pathlib.Path.home() / ".farm-factory-props" / "store")
    assert "SCORE_SPEND_STORE" in module.sandbox_refusal({"PROPS_HOME": sandbox, "SCORE_SPEND_STORE": real_store})
    assert module.sandbox_refusal({"PROPS_HOME": sandbox, "SCORE_SPEND_STORE": f"{sandbox}/store"}) is None


# Folders whose every file is in a paid row's code key (score.stages.moved): a test edited there moves paid rows, so
# their plain-script tests are run only through `make tests` until those rows are next made.
KEYED = ("tools/characters/maker/", "tools/characters/people/", "tools/props/closeup/")


def plain_script_tests():
    """Every test file of the repository run as a plain script (it has a `__main__` block), outside KEYED."""
    listed = subprocess.run(["git", "ls-files", "tools/*_test.py", "score/*_test.py"], cwd=REPO, capture_output=True,
                            text=True, check=True).stdout.split()
    return [REPO / name for name in listed
            if not name.startswith(KEYED) and 'if __name__ == "__main__":' in (REPO / name).read_text()]


def test_every_plain_script_test_refuses_first_without_a_sandbox_home():
    """Fault (2026-10-18 review): conftest.py covered pytest runs only; 146 of 149 plain-script tests ran by hand
    against the real home."""
    assert len(plain_script_tests()) > 100
    for path in plain_script_tests():
        block = path.read_text().split('if __name__ == "__main__":\n', 1)[1].splitlines()
        assert block[2].strip().startswith("runpy.run_path(") and "refuse_outside_sandbox" in block[2], path
        assert f"parents[{len(path.relative_to(REPO).parts) - 1}] / " in block[2], path  # the repository's root
    environ = {name: value for name, value in os.environ.items() if name not in ("PROPS_HOME", "PROPS_WORK")}
    done = subprocess.run([sys.executable, str(REPO / "tools/usd/triage_test.py")], cwd=REPO, env=environ,
                          capture_output=True, text=True)
    assert done.returncode != 0 and "refused: PROPS_HOME is not set" in done.stderr, done.stderr
