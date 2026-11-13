"""Every file a record names is a repository file, a library reference fetched by the library's own command and checked
against its entry's sha256, or a gap (None); and nothing names the game 2099's checkout (the owner, 2026-10-09: the
game and SCORE are fully separate things).

What the test pins, on one toy library (a git checkout with a bare remote, its blobs by sha256 beside it, and a
stand-in `score-lib` that fetches a blob out by the entry's sha256 and takes takes in: writes the entry with each
file's sha256 and blob, commits and pushes), and on the repository's own code and data:

- a name reads as its parts or as no reference, and its stage name holds no '@' (an OpenUSD asset path cannot); a
  repository file resolves without the library (a missing one raises); a folder of one's own stands in for the
  library; a name the library does not hold is a gap and is never fetched (rows of one name table);
- a reference is fetched once into the cache by the library's command and served from there after, fetched again
  when the cached bytes changed, refused when the fetched bytes are other than the entry's sha256; with no blob store
  set the command is handed the cloud backend's object store (a fake here) under the prefix score_lib, through its
  environment only, and with one set the cloud's is not read;
- a Pixal3D take freed from work/pixal (pixal_takes.py) comes back whole from the library, the same bytes under the
  same names, camera folder included, and is read back whole only when the library hands every file back at its size
  and hash;
- every name the data gives is a reference, a repository file that is there, or an old release name (a gap);
- a wording check guarding the owner's rule of 2026-10-09: no code, data or overlay names a Godot path (`res://`),
  the game's checkout (`projects/2099`, `2099/game`), the old `--world <the game's checkout>` option, or (outside
  comments and docstrings, and note keys in the data) a path into the game's tree (`game/...`, `sim/...`).

The break that turns the test red (applied once each, seen red, reverted):

- REFERENCE's id part loses its `(?:\\.[a-z0-9_]+)?` (the habitat.recordings row reads as no reference).
- resolve's `data/` branch removed (the repository rows resolve to None).
- from_library's cache check `sha256(target) == expected` made `True` (a changed cache is served).
- blob_store returns `values` at once (the command is handed no cloud store).
- a record value `"model": "assets/rover.glb"` added to data/library/lamps.json (a data guard: the data names no model
  or sound file today).
- a line `GODOT = "res://scenes/x.tscn"` added to library_files.py.
- pixal_takes.take_back's `missing = [name for name in sorted(record["files"]) if not (folder / name).exists()]` ->
  `missing = [name for name in sorted(record["files"]) if name.endswith(".glb") and not (folder / name).exists()]`
  (the close-up and camera stay lost).
- pixal_takes.read_back's `if library_files.sha256(there) != library_files.sha256(here):` -> `if False:` (a blob with
  other bytes passes).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/library/test_every_record_name_resolves_or_is_a_gap.py
"""
import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import library_files  # noqa: E402
import pixal_takes  # noqa: E402

# Anywhere, in any text file of the code and the data.
FORBIDDEN = re.compile(r"res://|projects/2099|2099/game|--world(?:[\s=]+[\"']?[~/.<$]|[\"'],\s*type=pathlib\.Path)")
# A path into the game's tree: its top folders, then at least one more part.
GAME_PATH = re.compile(r"^(game|sim)/[\w.-]+/")
# Keys whose values only say where something came from or what a record is.
NOTE_KEYS = {"from", "from_file", "read_by", "about", "is", "by", "recorded", "close_up", "note", "why", "source"}
# The folders checked, and the files in them left out: the vendored tools keep their own text, as released.
CHECKED = ("tools", "data", "design", "Makefile", "pyproject.toml", "README.md", "docs/bible.md")
SKIPPED = ("vendor/", "tools/library/test_every_record_name_resolves_or_is_a_gap.py")
TEXT_ENDINGS = (".py", ".sh", ".json", ".md", ".html", ".js", ".toml", ".txt", ".usda", "")
# A stand-in library command. `take-in <list> --save --report <file>` writes each take's entry with every file's sha256
# and its blob, commits and pushes; `fetch <address> (--file <file>)... --into <cache>` copies each file from the blob
# folder by the entry's sha256, as score-lib does from its blob store, and notes each fetch and the store it was given.
COMMAND = r'''
import hashlib, json, os, pathlib, shutil, subprocess, sys
words = sys.argv[1:]
root = pathlib.Path(words[words.index("--root") + 1])
blobs = root.parent / "blobs"
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
    (root.parent / "fetches.txt").open("a").write(address + "\n")
    (root.parent / "store.txt").write_text(os.environ.get("SCORE_LIB_S3_BUCKET", "") + "/"
                                           + os.environ.get("SCORE_LIB_S3_PREFIX", "") + " "
                                           + os.environ.get("AWS_SECRET_ACCESS_KEY", ""))
'''
HUM = "sound/hum.recordings@1/audio/recordings/hum.ogg"
TAKE = {"cup-s1.glb": b"glTF raw", "cup-s1-12000.glb": b"glTF thin", "cup-s1-final.glb": b"glTF up",
        "cup-s1.json": b"{}", "cup-s1.svviews/input.png": b"PNG close-up", "cup-s1.svviews/transforms.json": b"{}"}
GAP, MISSING = "gap", "missing"


@pytest.fixture
def library(tmp_path, monkeypatch):
    """The toy library's checkout (pushed to its bare remote) holding the hum entry, its blobs beside it, the stand-in
    command, a fake cloud backend's object store, PROPS_HOME in tmp_path with a work/pixal holding one take, and a
    folder of one's own; the checkout."""
    root, remote = tmp_path / "lib" / "score_lib", tmp_path / "lib" / "remote.git"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    for words in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                  ["remote", "add", "origin", str(remote)], ["commit", "-q", "--allow-empty", "-m", "start"],
                  ["push", "-q", "-u", "origin", "HEAD"]):
        subprocess.run(["git", "-C", str(root), *words], check=True, capture_output=True)
    (tmp_path / "lib" / "blobs").mkdir()
    sha = hashlib.sha256(b"a hum").hexdigest()
    (tmp_path / "lib" / "blobs" / sha).write_bytes(b"a hum")
    entry = root / "entries/sound/hum.recordings/1"
    entry.mkdir(parents=True)
    (entry / "entry.json").write_text(json.dumps({"files": {"audio/recordings/hum.ogg": {"sha256": sha}}}))
    (tmp_path / "score-lib.py").write_text(COMMAND)
    monkeypatch.setenv("PROPS_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} {tmp_path / 'score-lib.py'}")
    for variable in ("SCORE_LIB_FILES", *library_files.BLOB_STORE):
        monkeypatch.delenv(variable, raising=False)
    provider = type(sys)("provider")
    provider.cloud = type("Cloud", (), {"object_store": staticmethod(lambda: {
        "endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
        "secret_key": "SK"})})
    monkeypatch.setitem(sys.modules, "provider", provider)
    pixal = tmp_path / "home" / "work" / "pixal"
    for name, data in TAKE.items():
        (pixal / name).parent.mkdir(parents=True, exist_ok=True)
        (pixal / name).write_bytes(data)
    (pixal / "cup-s10.glb").write_bytes(b"another take")  # its name starts like cup-s1's: not one of its files
    (tmp_path / "own/models/box").mkdir(parents=True)
    (tmp_path / "own/models/box/box.glb").write_bytes(b"box")
    library_files.cloud_store.cache_clear()
    yield root
    library_files.cloud_store.cache_clear()


def tracked():
    """The tracked text files the wording check reads."""
    listed = subprocess.run(["git", "ls-files", "--", *CHECKED], cwd=REPO, check=True, capture_output=True,
                            text=True).stdout.split()
    return [REPO / name for name in listed
            if not name.startswith(SKIPPED) and pathlib.PurePosixPath(name).suffix in TEXT_ENDINGS
            and (REPO / name).is_file()]


def docstrings(tree):
    """The ids of every docstring node in a module."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def game_names(path):
    """Every place in one file naming the game's checkout, a Godot path, or (in code and data) a path into the game's
    tree."""
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        return []
    where = path.relative_to(REPO)
    found = [f"{where}:{number}: {line.strip()[:120]}" for number, line in enumerate(text.splitlines(), 1)
             if FORBIDDEN.search(line)]
    if path.suffix == ".py":
        tree = ast.parse(text)
        skipped = docstrings(tree)
        found += [f"{where}:{node.lineno}: {node.value[:120]}" for node in ast.walk(tree)
                  if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped
                  and GAME_PATH.match(node.value)]
    elif path.suffix == ".sh":
        found += [f"{where}:{number}: {line.strip()[:120]}" for number, line in enumerate(text.splitlines(), 1)
                  if re.search(r"(^|[\s\"'=/])(game|sim)/[\w.-]+/", line.split("#", 1)[0])]
    elif path.suffix == ".json":
        found += [f"{where}: {key}: {value[:120]}" for key, value in strings(json.loads(text))
                  if GAME_PATH.match(value)]
    return found


def strings(value, key=None):
    """Every (key, string) a JSON value holds outside its note keys, a list's items under the list's key."""
    if isinstance(value, dict):
        for inner, item in value.items():
            yield from strings(item, inner)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item, key)
    elif isinstance(value, str) and key not in NOTE_KEYS:
        yield key, value


def test_every_record_name_resolves_or_is_a_gap(library, tmp_path, monkeypatch):
    own, cache = tmp_path / "own", tmp_path / "home/cache/library/score_lib"
    fetches, store = tmp_path / "lib/fetches.txt", tmp_path / "lib/store.txt"
    # name, the folder of one's own given to resolve, its stage name, and what resolve gives: a path, a gap or missing.
    names = [
        ("sound/habitat.recordings@1/audio/recordings/places/habitat.ogg", None,
         "sound/habitat.recordings/1/audio/recordings/places/habitat.ogg", GAP),  # the library holds no such entry
        ("model/rover.gltf@2/gltf/rover.glb", None, "model/rover.gltf/2/gltf/rover.glb", GAP),
        ("sound/nothing.recordings@1/audio/nothing.ogg", None, "sound/nothing.recordings/1/audio/nothing.ogg", GAP),
        ("sound/hum.recordings@1/audio/other.ogg", None, "sound/hum.recordings/1/audio/other.ogg", GAP),  # no such file
        (HUM, None, "sound/hum.recordings/1/audio/recordings/hum.ogg",
         cache / "sound/hum.recordings/1/audio/recordings/hum.ogg"),
        ("models/rover/rover.glb", None, "models/rover/rover.glb", GAP),  # an old release name: no reference
        ("models/hub_kit/console_1.gltf", None, "models/hub_kit/console_1.gltf", GAP),
        ("sound/hum@0/a.ogg", None, "sound/hum@0/a.ogg", GAP),  # version 0
        ("Sound/hum@1/a.ogg", None, "Sound/hum@1/a.ogg", GAP),  # a capital in the kind
        ("sound/hum@1", None, "sound/hum@1", GAP),  # no file in the entry
        ("data/library/lamps.json", None, "data/library/lamps.json", REPO / "data/library/lamps.json"),
        ("data/library/no-such-file.json", None, "data/library/no-such-file.json", MISSING),
        ("models/box/box.glb", own, "models/box/box.glb", own / "models/box/box.glb"),
        ("models/box/none.glb", own, "models/box/none.glb", GAP),
    ]
    for name, folder, stage, outcome in names:
        assert library_files.stage_name(name) == stage, name
        assert (library_files.parsed(name) is None) == (stage == name), name
        if outcome == MISSING:
            with pytest.raises(FileNotFoundError):
                library_files.resolve(name, folder)
        else:
            assert library_files.resolve(name, folder) == (None if outcome == GAP else outcome), name
    assert library_files.parsed(names[0][0]) == {
        "address": "sound/habitat.recordings@1", "kind": "sound", "id": "habitat.recordings", "version": "1",
        "file": "audio/recordings/places/habitat.ogg"}

    # Only the hum was fetched, once, with the cloud's store in the command's environment and never in this process.
    found = cache / "sound/hum.recordings/1/audio/recordings/hum.ogg"
    assert found.read_bytes() == b"a hum"
    assert library_files.resolve(HUM) == found
    assert fetches.read_text().split() == ["sound/hum.recordings@1"]
    assert store.read_text() == "a-bucket/score_lib SK"
    assert not any("SK" == value for value in library_files.settings().values())
    found.write_bytes(b"changed")  # the cache's bytes moved: fetched again, then checked, now with a store set
    monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", str(tmp_path / "lib/blobs"))
    assert library_files.resolve(HUM).read_bytes() == b"a hum"
    assert len(fetches.read_text().split()) == 2
    assert store.read_text() == "/ "  # a store of its own: the cloud's is not read
    (tmp_path / "lib/blobs" / hashlib.sha256(b"a hum").hexdigest()).write_bytes(b"other bytes")
    found.unlink()
    with pytest.raises(library_files.LibraryUnreachable, match="does not hash"):
        library_files.resolve(HUM)

    # A Pixal3D take taken in, freed from work/pixal and put back whole; read back whole until a blob changes.
    pixal = tmp_path / "home/work/pixal"
    assert pixal_takes.take_names("cup-s1", pixal) == sorted(TAKE)
    report = pixal_takes.taken_in(["cup-s1"], pixal, "0" * 40, tmp_path / "scratch")
    assert report["new"] == ["take/cup_s1@1"] and report["saved"]["pushed"], report
    assert pixal_takes.upstream_holds("cup-s1")
    assert json.loads((library / "entries/take/cup_s1/1/entry.json").read_text())["title"] == "cup-s1"
    assert pixal_takes.read_back("cup-s1", pixal, tmp_path) is None
    for name in TAKE:
        (pixal / name).unlink()
    assert pixal_takes.take_back("cup-s1", pixal) == sorted(TAKE)
    assert {name: (pixal / name).read_bytes() for name in TAKE} == TAKE
    assert pixal_takes.take_back("cup-s1", pixal) == []
    assert pixal_takes.take_back("bowl-s1", pixal) == []
    assert (pixal / "cup-s10.glb").read_bytes() == b"another take"
    sha = hashlib.sha256(TAKE["cup-s1.svviews/input.png"]).hexdigest()
    (tmp_path / "lib/blobs" / sha).write_bytes(b"PNG close-UP")  # the same size, other bytes
    assert pixal_takes.read_back("cup-s1", pixal, tmp_path) == "cup-s1.svviews/input.png came back with other bytes"

    # The repository's data: every file name (a .glb, .gltf, .ogg or .wav) is a reference, a repository file that is
    # there, or an old release name (`models/...`, `sound/...`): a gap the remake fills.
    named = {value for path in sorted((REPO / "data").rglob("*.json"))
             for _, value in strings(json.loads(path.read_text()))
             if re.fullmatch(r"[\w.@/-]+\.(glb|gltf|ogg|wav)", value)}
    odd = sorted(name for name in named if not (library_files.parsed(name) or name.startswith(("models/", "sound/"))
                                                or (name.startswith("data/") and (REPO / name).exists())))
    assert not odd, "names that are neither a reference, a repository file nor a gap:\n  " + "\n  ".join(odd)

    # The repository's code and data name no game checkout; the pattern catches the old option and lets an
    # environment's name through.
    for line, forbidden in (("export.py <record> --world ~/projects/game", True),
                            ("`--world <the game's checkout>`", True),
                            ('parser.add_argument("--world", type=pathlib.Path, help="the game\'s checkout")', True),
                            ("--world=/srv/game", True),
                            ("store_page.py <place> [--world world1]", False),
                            ('parser.add_argument("--world", default="world1")', False)):
        assert bool(FORBIDDEN.search(line)) == forbidden, line
    faults = [fault for path in tracked() for fault in game_names(path)]
    assert not faults, "the game's checkout is still named:\n  " + "\n  ".join(faults)
