"""Every file a record names is a repository file, a library reference fetched by the library's own command and checked
against its entry's sha256, or a gap (None); and nothing names the game 2099's checkout (the owner, 2026-10-09: the
game and SCORE are fully separate things).

What each test pins:

- a reference reads as its parts, and its stage name holds no '@' (an OpenUSD asset path cannot);
- a repository file resolves without the library; a folder of one's own stands in for the library;
- a reference is fetched once into the cache by the library's command and served from there after, fetched again
  when the cached bytes changed, refused when the fetched bytes are other than the entry's sha256; a name the library
  does not hold is a gap; with no blob store set the command is handed the cloud backend's object store (a fake
  here) under the prefix score_lib, through its environment only;
- every name the data gives is a reference, a repository file that is there, or an old release name (a gap);
- a wording check guarding the owner's rule of 2026-10-09: no code, data or overlay names a Godot path (`res://`),
  the game's checkout (`projects/2099`, `2099/game`), the old `--world <the game's checkout>` option, or (outside
  comments and docstrings, and note keys in the data) a path into the game's tree (`game/...`, `sim/...`).

The break that turns each test red (applied once each, seen red, reverted):

- test_a_reference_reads_as_its_parts: REFERENCE's id part loses its `(?:\\.[a-z0-9_]+)?`.
- test_a_repository_file_or_a_folder_of_ones_own_resolves_without_the_library: resolve's `data/` branch removed.
- test_the_library_is_fetched_once_checked_and_a_name_it_lacks_is_a_gap: from_library's cache check
  `sha256(target) == expected` made `True` (a changed cache is served).
- test_the_cloud_store_is_handed_on_only_when_no_store_is_set: blob_store returns `values` at once.
- test_every_record_name_is_a_reference_a_repository_file_or_a_gap (a data guard: the data names no model or sound
  file today): a record value `"model": "assets/rover.glb"` added to data/library/lamps.json.
- test_nothing_names_the_games_checkout: a line `GODOT = "res://scenes/x.tscn"` added to library_files.py.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/library/test_every_record_name_resolves_or_is_a_gap.py
"""
import ast
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import library_files  # noqa: E402

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
# A stand-in library command: `fetch <address> --file <file> --into <cache>` copies the file from a blob folder named
# by the entry's sha256, as score-lib fetch does from its blob store, and notes each fetch and the store it was given.
FAKE_COMMAND = '''
import json, os, pathlib, shutil, sys
words = sys.argv[1:]
root = pathlib.Path(words[words.index("--root") + 1])
address, file = words[words.index("fetch") + 1], words[words.index("--file") + 1]
into = pathlib.Path(words[words.index("--into") + 1])
kind, rest = address.split("/", 1)
entry_id, version = rest.split("@")
record = json.loads((root / "entries" / kind / entry_id / version / "entry.json").read_text())
target = into / "score_lib" / kind / entry_id / version / file
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(root / "blobs" / record["files"][file]["sha256"], target)
(root / "fetches.txt").open("a").write(address + "\\n")
(root / "store.txt").write_text(os.environ.get("SCORE_LIB_S3_BUCKET", "") + "/" + os.environ.get("SCORE_LIB_S3_PREFIX", "")
                                + " " + os.environ.get("AWS_SECRET_ACCESS_KEY", ""))
'''
HUM = "sound/hum.recordings@1/audio/recordings/hum.ogg"


def test_a_reference_reads_as_its_parts():
    assert library_files.parsed("sound/habitat.recordings@1/audio/recordings/places/habitat.ogg") == {
        "address": "sound/habitat.recordings@1", "kind": "sound", "id": "habitat.recordings", "version": "1",
        "file": "audio/recordings/places/habitat.ogg"}
    for name in ("models/rover/rover.glb", "sound/hum@0/a.ogg", "Sound/hum@1/a.ogg", "sound/hum@1"):
        assert library_files.parsed(name) is None, name
    assert library_files.stage_name("model/rover.gltf@2/gltf/rover.glb") == "model/rover.gltf/2/gltf/rover.glb"
    assert library_files.stage_name("data/library/lamps.json") == "data/library/lamps.json"


def test_a_repository_file_or_a_folder_of_ones_own_resolves_without_the_library(tmp_path, monkeypatch):
    monkeypatch.delenv("SCORE_LIB_ROOT", raising=False)
    monkeypatch.delenv("SCORE_LIB_FILES", raising=False)
    assert library_files.resolve("data/library/lamps.json") == REPO / "data/library/lamps.json"
    with pytest.raises(FileNotFoundError):
        library_files.resolve("data/library/no-such-file.json")
    (tmp_path / "models/box").mkdir(parents=True)
    (tmp_path / "models/box/box.glb").write_bytes(b"box")
    assert library_files.resolve("models/box/box.glb", tmp_path) == tmp_path / "models/box/box.glb"
    assert library_files.resolve("models/box/none.glb", tmp_path) is None


@pytest.fixture
def toy_library(tmp_path, monkeypatch):
    """A library with one entry (the hum), its blob by sha256, the stand-in command, a fake cloud backend's object
    store, and PROPS_HOME in tmp_path; the library's root."""
    root = tmp_path / "library"
    (root / "blobs").mkdir(parents=True)
    sha = hashlib.sha256(b"a hum").hexdigest()
    (root / "blobs" / sha).write_bytes(b"a hum")
    entry = root / "entries/sound/hum.recordings/1"
    entry.mkdir(parents=True)
    (entry / "entry.json").write_text(json.dumps({"files": {"audio/recordings/hum.ogg": {"sha256": sha}}}))
    (tmp_path / "fetch.py").write_text(FAKE_COMMAND)
    monkeypatch.setenv("PROPS_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} {tmp_path / 'fetch.py'}")
    for variable in ("SCORE_LIB_FILES", *library_files.BLOB_STORE):
        monkeypatch.delenv(variable, raising=False)
    provider = type(sys)("provider")
    provider.cloud = type("Cloud", (), {"object_store": staticmethod(lambda: {
        "endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
        "secret_key": "SK"})})
    monkeypatch.setitem(sys.modules, "provider", provider)
    library_files.cloud_store.cache_clear()
    yield root
    library_files.cloud_store.cache_clear()


def test_the_library_is_fetched_once_checked_and_a_name_it_lacks_is_a_gap(toy_library, tmp_path):
    found = library_files.resolve(HUM)
    assert found == tmp_path / "home/cache/library/score_lib/sound/hum.recordings/1/audio/recordings/hum.ogg"
    assert found.read_bytes() == b"a hum"
    assert library_files.resolve(HUM) == found
    assert (toy_library / "fetches.txt").read_text().split() == ["sound/hum.recordings@1"]  # once
    found.write_bytes(b"changed")  # the cache's bytes moved: fetched again, then checked
    assert library_files.resolve(HUM).read_bytes() == b"a hum"
    assert len((toy_library / "fetches.txt").read_text().split()) == 2
    (toy_library / "blobs" / hashlib.sha256(b"a hum").hexdigest()).write_bytes(b"other bytes")
    found.unlink()
    with pytest.raises(library_files.LibraryUnreachable, match="does not hash"):
        library_files.resolve(HUM)
    for gap in ("models/hub_kit/console_1.gltf", "sound/nothing.recordings@1/audio/nothing.ogg",
                "sound/hum.recordings@1/audio/other.ogg"):
        assert library_files.resolve(gap) is None, gap


def test_the_cloud_store_is_handed_on_only_when_no_store_is_set(toy_library, monkeypatch):
    library_files.resolve(HUM)
    assert (toy_library / "store.txt").read_text() == "a-bucket/score_lib SK"
    assert not any("SK" == value for value in library_files.settings().values())  # never in this process's settings
    shutil.rmtree(toy_library.parent / "home/cache")  # fetched again, now with a store set
    monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", str(toy_library / "blobs"))
    library_files.resolve(HUM)
    assert (toy_library / "store.txt").read_text() == "/ "  # a store of its own: the cloud's is not read


def test_every_record_name_is_a_reference_a_repository_file_or_a_gap():
    """Every file name the data gives (a .glb, .gltf, .ogg or .wav) is a library reference, a repository file that is
    there, or an old release name (`models/...`, `sound/...`): a gap the remake fills."""
    named = set()

    def walk(value, key):
        if isinstance(value, dict):
            for inner, item in value.items():
                walk(item, inner)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)
        elif isinstance(value, str) and key not in NOTE_KEYS and re.fullmatch(r"[\w.@/-]+\.(glb|gltf|ogg|wav)", value):
            named.add(value)

    for path in sorted((REPO / "data").rglob("*.json")):
        walk(json.loads(path.read_text()), None)
    odd = sorted(name for name in named if not (library_files.parsed(name) or name.startswith(("models/", "sound/"))
                                                or (name.startswith("data/") and (REPO / name).exists())))
    assert not odd, "names that are neither a reference, a repository file nor a gap:\n  " + "\n  ".join(odd)


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
        def walk(value, key):
            if isinstance(value, dict):
                for inner, item in value.items():
                    yield from walk(item, inner)
            elif isinstance(value, list):
                for item in value:
                    yield from walk(item, key)
            elif isinstance(value, str) and key not in NOTE_KEYS and GAME_PATH.match(value):
                yield f"{where}: {key}: {value[:120]}"
        found += list(walk(json.loads(text), None))
    return found


def test_nothing_names_the_games_checkout():
    for line in ("export.py <record> --world ~/projects/game", "`--world <the game's checkout>`",
                 'parser.add_argument("--world", type=pathlib.Path, help="the game\'s checkout")', "--world=/srv/game"):
        assert FORBIDDEN.search(line), line  # the pattern itself catches the old option
    for line in ("store_page.py <place> [--world world1]", 'parser.add_argument("--world", default="world1")'):
        assert not FORBIDDEN.search(line), line  # and lets an environment's name through
    faults = [fault for path in tracked() for fault in game_names(path)]
    assert not faults, "the game's checkout is still named:\n  " + "\n  ".join(faults)
