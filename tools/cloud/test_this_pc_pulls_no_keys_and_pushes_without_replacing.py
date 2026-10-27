"""tools/cloud/this_pc.py: a run on this PC's card pulls only what a run reads from the conductor's home (never its
keys, ledgers or run registry), runs free only on this PC's card in a home of its own, and pushes back only by adding
files, never replacing one the conductor has. Real rsync between two folders stands in for the conductor (its
`score@host:` ends rewritten to local paths); nothing reaches the conductor.

Breaks (each applied once, seen red, reverted), in this_pc.py:
- `PULLED`: add "/cloud/***" -> the runner's ssh key comes down with the store.
- `push_commands`: drop "--ignore-existing" -> the conductor's own record is replaced by this PC's.
- `ENVIRONMENT`: drop "SCORE_FREE_ONLY": "1" -> a run here may buy (its runs are not free only).
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import this_pc  # noqa: E402


def local(command, source, destination):
    """`command` with its ssh and conductor ends swapped for local folders, so rsync copies between them."""
    kept, skip = [], False
    for argument in command[:-2]:
        if skip:
            skip = False
            continue
        if argument == "-e":
            skip = True
            continue
        if not argument.startswith(("--temp-dir", "--rsync-path")):
            kept.append(argument)
    return [*kept, f"{source}/", f"{destination}/"]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_a_pull_brings_what_a_run_reads_and_no_key_or_ledger(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    for name in ("store/objects/blobs/aa", "design/props/hub.json", "work/pixal/take.glb", "cloud/google-cache/q.json",
                 "cloud/ssh_key", "cloud/self_delete_key.json", "cloud/ledger.jsonl", "runs/active.json",
                 "store/cache/checkouts/x", "frozen/copy/file", "dashboard/db.sqlite3"):
        write(conductor / name, name)
    subprocess.run(local(this_pc.pull_command("192.0.2.1", "~/.ssh/id_ed25519", home), conductor, home), check=True)
    pulled = sorted(str(path.relative_to(home)) for path in home.rglob("*") if path.is_file())
    assert pulled == ["cloud/google-cache/q.json", "design/props/hub.json", "store/objects/blobs/aa",
                      "work/pixal/take.glb"]


def test_a_push_adds_new_outputs_and_never_replaces_the_conductors(tmp_path):
    conductor, home = tmp_path / "conductor", tmp_path / "home"
    write(conductor / "store/objects/records/hub/k1.json", "the conductor's record")
    write(home / "store/objects/records/hub/k1.json", "this PC's record")
    write(home / "store/objects/records/hub/k2.json", "made on this PC")
    write(home / "work/pixal/new.glb", "a take")
    for command, folder in zip(this_pc.push_commands("192.0.2.1", "~/.ssh/id_ed25519", home), this_pc.PUSHED):
        (conductor / folder).mkdir(parents=True, exist_ok=True)
        subprocess.run(local(command, home / folder, conductor / folder), check=True)
    assert (conductor / "store/objects/records/hub/k1.json").read_text() == "the conductor's record"
    assert (conductor / "store/objects/records/hub/k2.json").read_text() == "made on this PC"
    assert (conductor / "work/pixal/new.glb").read_text() == "a take"


def test_a_run_here_is_free_only_on_this_pcs_card_in_its_own_home(tmp_path, monkeypatch):
    monkeypatch.setattr(this_pc, "PC_ENV", tmp_path / "env")
    home = this_pc.prepared(tmp_path / "home")
    environment = this_pc.run_environment(home)
    assert {key: environment[key] for key in this_pc.ENVIRONMENT} == {
        "SCORE_CLOUD": "local", "SCORE_FREE_ONLY": "1", "SCORE_INPUTS_DIRECT": "1", "SCORE_MAX_MACHINES": "all=1"}
    assert environment["PROPS_HOME"] == str(home) and (home / "cloud/ssh_key.pub").exists()
    assert (home / "env").is_symlink()
