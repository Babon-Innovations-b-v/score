"""tools/cloud/this_pc.py: a run on this PC's card pulls only what a run reads from the conductor's home (never its
keys, ledgers or run registry), runs free only on this PC's card in a home of its own, and pushes back only by adding
files, never replacing one the conductor has. The agents' door itself (agent_door.py, as sshd's forced command runs
it) stands in for ssh, a folder for the conductor's home; nothing reaches the conductor.

Breaks (each applied once, seen red, reverted):
- agent_door.py `PULLED`: add "cloud" -> the runner's ssh key comes down with the store.
- agent_door.py `store_pull`: drop the `continue` after `kept += 1` -> a second pull sends every file again.
- agent_door.py `store_missing`: name every path, not only those missing -> the push carries files the conductor
  holds (its own add-only refusal is the door's test).
- this_pc.py `ENVIRONMENT`: drop "SCORE_FREE_ONLY": "1" -> a run here may buy (its runs are not free only).
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import this_pc  # noqa: E402


def door(conductor, verb):
    """The door's command for `verb` against the folder `conductor`, as sshd would run it."""
    return ["env", f"SSH_ORIGINAL_COMMAND={verb}", f"PROPS_HOME={conductor}", "SCORE_DOOR_ENV=/nonexistent",
            sys.executable, str(HERE / "conductor" / "agent_door.py")]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_pull_brings_what_a_run_reads_and_no_key_or_ledger_and_again_only_what_changed(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    for name in ("store/objects/blobs/aa", "design/props/hub.json", "work/pixal/take.glb", "cloud/google-cache/q.json",
                 "cache/library/swatch.png", "cloud/ssh_key", "cloud/self_delete_key.json", "cloud/ledger.jsonl",
                 "runs/active.json", "store/cache/checkouts/x", "frozen/copy/file", "dashboard/db.sqlite3"):
        write(conductor / name, name)
    home.mkdir()
    assert this_pc.pull(home, door(conductor, "store-pull")) == (5, sum(
        len(name) for name in ("store/objects/blobs/aa", "design/props/hub.json", "work/pixal/take.glb",
                               "cloud/google-cache/q.json", "cache/library/swatch.png")))
    pulled = sorted(str(path.relative_to(home)) for path in home.rglob("*") if path.is_file())
    assert pulled == ["cache/library/swatch.png", "cloud/google-cache/q.json", "design/props/hub.json",
                      "store/objects/blobs/aa", "work/pixal/take.glb"]
    write(conductor / "design/props/hub.json", "the hub, changed")
    assert this_pc.pull(home, door(conductor, "store-pull")) == (1, len("the hub, changed"))
    assert (home / "design/props/hub.json").read_text() == "the hub, changed"


def test_a_push_adds_new_outputs_and_never_replaces_the_conductors(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    write(conductor / "store/objects/records/hub/k1.json", "the conductor's record")
    write(home / "store/objects/records/hub/k1.json", "this PC's record")
    write(home / "store/objects/records/hub/k2.json", "made on this PC")
    write(home / "work/pixal/new.glb", "a take")
    write(home / "cloud/ssh_key", "this PC's runner key")
    pushed = this_pc.push(home, door(conductor, "store-push --missing"), door(conductor, "store-push"))
    assert pushed == (2, len("made on this PC") + len("a take"))  # only what the conductor lacks went
    assert (conductor / "store/objects/records/hub/k1.json").read_text() == "the conductor's record"
    assert (conductor / "store/objects/records/hub/k2.json").read_text() == "made on this PC"
    assert (conductor / "work/pixal/new.glb").read_text() == "a take"
    assert not (conductor / "cloud").exists() and not list((conductor / "tmp/this-pc-push").iterdir())


def test_a_run_here_is_free_only_on_this_pcs_card_in_its_own_home(tmp_path, monkeypatch):
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    home = this_pc.prepared(tmp_path / "home")
    environment = this_pc.run_environment(home)
    assert {key: environment[key] for key in this_pc.ENVIRONMENT} == {
        "SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1", "SCORE_MAX_MACHINES": "all=1"}
    assert environment["PROPS_HOME"] == str(home) and (home / "cloud/ssh_key.pub").exists()
    assert (home / "env").is_symlink()
