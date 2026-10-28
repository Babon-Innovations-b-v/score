"""tools/library/pixal_takes.py's invariant: a Pixal3D take freed from work/pixal comes back whole from the library,
the same bytes under the same names, camera folder included, and a take is read back whole only when the library
hands every file back at its size and hash.

The library here is a toy: a git checkout with a bare remote and a stand-in `score-lib` (take-in --save writes the
take's entry with each file's sha256 and its blob, commits and pushes; fetch copies a blob out by the entry's sha256),
as score_lib's own commands do.

Break that turns it red:
- test_a_freed_take_comes_back_whole: pixal_takes.take_back's `missing = [name for name in sorted(record["files"]) if
  not (folder / name).exists()]` -> `missing = [name for name in sorted(record["files"]) if name.endswith(".glb") and
  not (folder / name).exists()]` (the close-up and camera stay lost).
- test_read_back_names_a_file_that_came_back_changed: pixal_takes.read_back's `if library_files.sha256(there) !=
  library_files.sha256(here):` -> `if False:` (a blob with other bytes passes).
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import pixal_takes  # noqa: E402

FAKE = r'''
import hashlib, json, pathlib, shutil, subprocess, sys
words = sys.argv[1:]
root = pathlib.Path(words[words.index("--root") + 1])
blobs = root.parent / "blobs"
blobs.mkdir(exist_ok=True)
if "take-in" in words:
    listing = json.loads(pathlib.Path(words[words.index("take-in") + 1]).read_text())
    report = {"new": [], "unchanged": [], "changed draft": [], "new version": [], "refused": []}
    for entry in listing["entries"]:
        files = {}
        for name, about in entry["files"].items():
            data = pathlib.Path(about["path"]).read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            (blobs / sha).write_bytes(data)
            files[name] = {"sha256": sha, "bytes": len(data), "role": "gltf"}
        address = f"take/{entry['id']}@1"
        path = root / "entries/take" / entry["id"] / "1" / "entry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"address": address, "kind": "take", "id": entry["id"], "version": 1,
                                    "title": entry["title"], "files": files}))
        report["new"].append(address)
    git = ["git", "-C", str(root)]
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "take-in"], check=True)
    subprocess.run(git + ["push", "-q", "origin", "HEAD"], check=True, capture_output=True)
    report["saved"] = {"committed": "x", "pushed": True, "why": ""}
    pathlib.Path(words[words.index("--report") + 1]).write_text(json.dumps(report))
else:
    address = words[words.index("fetch") + 1]
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    record = json.loads((root / "entries" / kind / entry_id / version / "entry.json").read_text())
    into = pathlib.Path(words[words.index("--into") + 1]) / "score_lib" / kind / entry_id / version
    for at, word in enumerate(words):
        if word == "--file":
            name = words[at + 1]
            (into / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(blobs / record["files"][name]["sha256"], into / name)
'''
TAKE = {"cup-s1.glb": b"glTF raw", "cup-s1-12000.glb": b"glTF thin", "cup-s1-final.glb": b"glTF up",
        "cup-s1.json": b"{}", "cup-s1.svviews/input.png": b"PNG close-up", "cup-s1.svviews/transforms.json": b"{}"}


@pytest.fixture
def library(tmp_path, monkeypatch):
    """A toy library checkout with its remote, its stand-in command, and a work/pixal holding one take."""
    root, remote = tmp_path / "lib" / "score_lib", tmp_path / "lib" / "remote.git"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    for words in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                  ["remote", "add", "origin", str(remote)], ["commit", "-q", "--allow-empty", "-m", "start"],
                  ["push", "-q", "-u", "origin", "HEAD"]):
        subprocess.run(["git", "-C", str(root), *words], check=True, capture_output=True)
    (tmp_path / "score-lib.py").write_text(FAKE)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} {tmp_path / 'score-lib.py'}")
    monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", str(tmp_path / "lib" / "blobs"))
    monkeypatch.setenv("PROPS_HOME", str(tmp_path / "home"))
    pixal = tmp_path / "home" / "work" / "pixal"
    for name, data in TAKE.items():
        (pixal / name).parent.mkdir(parents=True, exist_ok=True)
        (pixal / name).write_bytes(data)
    (pixal / "cup-s10.glb").write_bytes(b"another take")  # its name starts like cup-s1's: not one of its files
    return pixal


def test_a_freed_take_comes_back_whole(library, tmp_path):
    assert pixal_takes.take_names("cup-s1", library) == sorted(TAKE)
    report = pixal_takes.taken_in(["cup-s1"], library, "0" * 40, tmp_path / "scratch")
    assert report["new"] == ["take/cup_s1@1"] and report["saved"]["pushed"], report
    assert pixal_takes.upstream_holds("cup-s1")
    assert pixal_takes.read_back("cup-s1", library, tmp_path) is None
    for name in TAKE:
        (library / name).unlink()
    assert pixal_takes.take_back("cup-s1", library) == sorted(TAKE)
    assert {name: (library / name).read_bytes() for name in TAKE} == TAKE
    assert pixal_takes.take_back("cup-s1", library) == [] and pixal_takes.take_back("bowl-s1", library) == []
    assert (library / "cup-s10.glb").read_bytes() == b"another take"


def test_read_back_names_a_file_that_came_back_changed(library, tmp_path):
    pixal_takes.taken_in(["cup-s1"], library, "0" * 40, tmp_path / "scratch")
    sha = hashlib.sha256(TAKE["cup-s1.svviews/input.png"]).hexdigest()
    (tmp_path / "lib" / "blobs" / sha).write_bytes(b"PNG close-UP")  # the same size, other bytes
    assert pixal_takes.read_back("cup-s1", library, tmp_path) == "cup-s1.svviews/input.png came back with other bytes"
    entry = json.loads((tmp_path / "lib/score_lib/entries/take/cup_s1/1/entry.json").read_text())
    assert entry["title"] == "cup-s1"
