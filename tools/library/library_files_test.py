"""The library resolver (library_files.py) and the rule it keeps: the framework stands alone. No code or data in this
repository reads a file of the game 2099's checkout (the owner, 2026-10-09: the game and SCORE are fully separate
things); every file a record names is in git (`data/...`), a library reference, or a gap.

What fails:

- anywhere in the code, the data and the overlays: a Godot path (`res://`), the game's checkout on this machine
  (`projects/2099`, `2099/game`), or the old `--world <the game's checkout>` option (a `--world` that takes a path;
  `--world world1`, a SCORE environment's name, is fine);
- in Python and shell code (comments and docstrings aside, which may cite where a number came from): a string that is a
  path into the game's tree (`game/...`, `sim/...`);
- in the data: a value that is such a path, unless it sits under a key that only notes where something came from
  (`from`, `read_by`, `about`, `is`, ...);
- the resolver: a reference fetched by the library's own command and checked against its entry's sha256, served from
  the cache after, fetched again when the cached bytes changed; a name the library does not hold a gap (None);
- the blob store: with none set, the command is handed the cloud backend's object store (a fake here) under the prefix
  score_lib, through its environment only.

Run: .venv/bin/python tools/library/library_files_test.py   (make tests runs it with the framework's environment)
"""
import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

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
SKIPPED = ("vendor/", "tools/library/library_files_test.py")
TEXT_ENDINGS = (".py", ".sh", ".json", ".md", ".html", ".js", ".toml", ".txt", ".usda", "")
# A fake library command: `fetch <address> --file <file> --into <cache>` copies the file from a blob folder named by
# the entry's sha256, as score-lib fetch does from its blob store.
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
(root / "store.txt").write_text(os.environ.get("SCORE_LIB_S3_BUCKET", "") + "/" + os.environ.get("SCORE_LIB_S3_PREFIX", ""))
'''


def tracked():
    """The tracked files this check reads."""
    listed = subprocess.run(["git", "ls-files", "--", *CHECKED], cwd=REPO, check=True, capture_output=True,
                            text=True).stdout.split()
    return [REPO / name for name in listed
            if not name.startswith(SKIPPED) and pathlib.PurePosixPath(name).suffix in TEXT_ENDINGS
            and (REPO / name).is_file()]


def forbidden_lines(path):
    """Every line of a file naming the game's checkout or a Godot path."""
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        return []
    return [f"{path.relative_to(REPO)}:{number}: {line.strip()[:120]}"
            for number, line in enumerate(text.splitlines(), 1) if FORBIDDEN.search(line)]


def docstrings(tree):
    """The ids of every docstring node in a module."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                found.add(id(first.value))
    return found


def python_game_paths(path):
    """Every string in a Python file's code (docstrings aside) that is a path into the game's tree."""
    tree = ast.parse(path.read_text())
    skipped = docstrings(tree)
    return [f"{path.relative_to(REPO)}:{node.lineno}: {node.value[:120]}" for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped
            and GAME_PATH.match(node.value)]


def shell_game_paths(path):
    """Every line of a shell script, comments aside, naming a path into the game's tree."""
    found = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        code = line.split("#", 1)[0]
        if re.search(r"(^|[\s\"'=/])(game|sim)/[\w.-]+/", code):
            found.append(f"{path.relative_to(REPO)}:{number}: {line.strip()[:120]}")
    return found


def data_game_paths(path):
    """Every value in a JSON file that is a path into the game's tree, notes aside."""
    found = []

    def walk(value, key):
        if isinstance(value, dict):
            for inner, item in value.items():
                walk(item, inner)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)
        elif isinstance(value, str) and key not in NOTE_KEYS and GAME_PATH.match(value):
            found.append(f"{path.relative_to(REPO)}: {key}: {value[:120]}")

    walk(json.loads(path.read_text()), None)
    return found


def check_nothing_names_the_game():
    faults = []
    for path in tracked():
        faults += forbidden_lines(path)
        if path.suffix == ".py":
            faults += python_game_paths(path)
        elif path.suffix == ".sh":
            faults += shell_game_paths(path)
        elif path.suffix == ".json":
            faults += data_game_paths(path)
    assert not faults, "the game's checkout is still named:\n  " + "\n  ".join(faults)


def check_only_the_old_world_option_is_forbidden():
    for line in ("export.py <record> --world ~/projects/game", "`--world <the game's checkout>`",
                 'parser.add_argument("--world", type=pathlib.Path, help="the game\'s checkout")', "--world=/srv/game"):
        assert FORBIDDEN.search(line), line
    for line in ("store_page.py <place> [--world world1]", 'parser.add_argument("--world", default="world1")'):
        assert not FORBIDDEN.search(line), line


def check_a_reference_reads_as_its_parts():
    parts = library_files.parsed("sound/habitat.recordings@1/audio/recordings/places/habitat.ogg")
    assert parts == {"address": "sound/habitat.recordings@1", "kind": "sound", "id": "habitat.recordings",
                     "version": "1", "file": "audio/recordings/places/habitat.ogg"}, parts
    assert library_files.parsed("models/rover/rover.glb") is None
    assert library_files.stage_name("model/rover.gltf@2/gltf/rover.glb") == "model/rover.gltf/2/gltf/rover.glb"
    assert library_files.stage_name("data/ground/moon.json") == "data/ground/moon.json"


def check_a_repository_file_resolves_without_the_library():
    assert library_files.resolve("data/ground/moon.json") == REPO / "data/ground/moon.json"


def toy_library(folder, files):
    """A library folder with one entry per {reference: bytes}, its blobs by sha256 and a fake fetch command."""
    root = folder / "library"
    (root / "blobs").mkdir(parents=True)
    for name, data in files.items():
        parts = library_files.parsed(name)
        sha = hashlib.sha256(data).hexdigest()
        (root / "blobs" / sha).write_bytes(data)
        entry = root / "entries" / parts["kind"] / parts["id"] / parts["version"]
        entry.mkdir(parents=True)
        (entry / "entry.json").write_text(json.dumps({"files": {parts["file"]: {"sha256": sha}}}))
    (folder / "fetch.py").write_text(FAKE_COMMAND)
    return root


def check_the_library_is_fetched_once_checked_and_gaps_are_none():
    reference = "sound/hum.recordings@1/audio/recordings/hum.ogg"
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        root = toy_library(folder, {reference: b"a hum"})
        os.environ.update({"PROPS_HOME": str(folder / "home"), "SCORE_LIB_ROOT": str(root),
                           "SCORE_LIB_COMMAND": f"{sys.executable} {folder / 'fetch.py'}"})
        for variable in ("SCORE_LIB_FILES", *library_files.BLOB_STORE):
            os.environ.pop(variable, None)
        provider = type(sys)("provider")  # a fake cloud backend: its object store a fixed dict
        provider.cloud = type("Cloud", (), {"object_store": staticmethod(lambda: {
            "endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
            "secret_key": "SK"})})
        sys.modules["provider"] = provider
        library_files.cloud_store.cache_clear()
        found = library_files.resolve(reference)
        assert (root / "store.txt").read_text() == "a-bucket/score_lib", "the cloud's store was not handed on"
        assert found.read_bytes() == b"a hum"
        assert found == folder / "home/cache/library/score_lib/sound/hum.recordings/1/audio/recordings/hum.ogg"
        assert library_files.resolve(reference) == found
        assert (root / "fetches.txt").read_text().split() == ["sound/hum.recordings@1"], "fetched twice"
        found.write_bytes(b"changed")  # the cache's bytes moved: fetched again, then checked
        assert library_files.resolve(reference).read_bytes() == b"a hum"
        assert len((root / "fetches.txt").read_text().split()) == 2
        (root / "blobs" / hashlib.sha256(b"a hum").hexdigest()).write_bytes(b"other bytes")
        found.unlink()
        try:
            library_files.resolve(reference)
        except library_files.LibraryUnreachable as refused:
            assert "does not hash" in str(refused), refused
        else:
            raise AssertionError("a fetched file of other bytes was taken")
        assert library_files.resolve("models/hub_kit/console_1.gltf") is None
        assert library_files.resolve("sound/nothing.recordings@1/audio/nothing.ogg") is None
        assert library_files.resolve("sound/hum.recordings@1/audio/other.ogg") is None


def check_a_folder_of_one_s_own_stands_in():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "models/box").mkdir(parents=True)
        (folder / "models/box/box.glb").write_bytes(b"box")
        assert library_files.resolve("models/box/box.glb", folder) == folder / "models/box/box.glb"
        assert library_files.resolve("models/box/none.glb", folder) is None


def check_every_record_name_is_a_reference_a_repository_file_or_a_gap():
    """Every file name the data gives is a library reference, a repository file that is there, or an old release name
    (`models/...`, `sound/...`): a gap the remake fills."""
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
    # the data named old models and sounds until they were retired (2026-10-21): now it may name none
    assert not odd, "names that are neither a reference, a repository file nor a gap:\n  " + "\n  ".join(odd)


def main():
    check_only_the_old_world_option_is_forbidden()
    check_nothing_names_the_game()
    check_a_reference_reads_as_its_parts()
    check_a_repository_file_resolves_without_the_library()
    check_the_library_is_fetched_once_checked_and_gaps_are_none()
    check_a_folder_of_one_s_own_stands_in()
    check_every_record_name_is_a_reference_a_repository_file_or_a_gap()
    print("library_files_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    main()
