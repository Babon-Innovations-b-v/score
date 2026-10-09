"""Check that the framework stands alone: no code or data in this repository reads a file of the game 2099's checkout
(the owner, 2026-10-09: the game and SCORE are fully separate things). Every file a record names is in git
(`data/...`) or in the world's release (tools/assets/world.py), and the manifest names every file the records name.

What fails:

- anywhere in the code, the data and the overlays: a Godot path (`res://`), the game's checkout on this machine
  (`projects/2099`, `2099/game`), or the old `--world <the game's checkout>` option;
- in Python and shell code (comments and docstrings aside, which may cite where a number came from): a string that is a
  path into the game's tree (`game/...`, `sim/...`);
- in the data: a value that is such a path, unless it sits under a key that only notes where something came from
  (`from`, `read_by`, `about`, `is`, ...).

Run: .venv/bin/python tools/assets/game_free_test.py   (make tests runs it with the framework's environment)
"""
import ast
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import world  # noqa: E402

# Anywhere, in any text file of the code and the data.
FORBIDDEN = re.compile(r"res://|projects/2099|2099/game|--world\b")
# A path into the game's tree: its top folders, then at least one more part.
GAME_PATH = re.compile(r"^(game|sim)/[\w.-]+/")
# Keys whose values only say where something came from or what a record is.
NOTE_KEYS = {"from", "from_file", "read_by", "about", "is", "by", "recorded", "close_up", "note", "why", "source"}
# The folders checked, and the files in them left out: the vendored tools keep their own text, as released.
CHECKED = ("tools", "data", "design", "Makefile", "pyproject.toml", "README.md", "docs/bible.md")
SKIPPED = ("vendor/", "tools/assets/game_free_test.py")
TEXT_ENDINGS = (".py", ".sh", ".json", ".md", ".html", ".js", ".toml", ".txt", ".usda", "")


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


def named_files():
    """Every file name a record's data gives for a model, a picture or a sound (notes aside)."""
    named = set()

    def walk(value, key):
        if isinstance(value, dict):
            for inner, item in value.items():
                walk(item, inner)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)
        elif isinstance(value, str) and key not in NOTE_KEYS and re.fullmatch(r"(models|sound)/[\w./-]+\.\w+", value):
            named.add(value)

    for path in sorted((REPO / "data").rglob("*.json")):
        if path != world.MANIFEST:
            walk(json.loads(path.read_text()), None)
    return named


def check_every_named_file_is_in_the_release():
    files = world.manifest()["files"]
    missing = sorted(name for name in named_files() if name not in files)
    assert not missing, "named but not in the world's release (data/assets/world1.json):\n  " + "\n  ".join(missing)


def check_every_file_in_the_release_has_its_terms():
    for name, about in world.manifest()["files"].items():
        assert about.get("licence") and about.get("source"), name


def check_the_terms_take_the_longest_match():
    licences = [{"match": "models/", "licence": "a"}, {"match": "models/rover/", "licence": "b"},
                {"match": "models/rover/rover.glb", "licence": "c"}]
    assert world.terms_of("models/rover/rover.glb", licences)["licence"] == "c"
    assert world.terms_of("models/rover/wheel.glb", licences)["licence"] == "b"
    assert world.terms_of("models/car/car.glb", licences)["licence"] == "a"
    assert world.terms_of("sound/x.ogg", licences) is None


def check_a_repository_file_resolves_without_the_release():
    assert world.resolve("data/ground/moon.json") == REPO / "data/ground/moon.json"


def main():
    check_nothing_names_the_game()
    check_every_named_file_is_in_the_release()
    check_every_file_in_the_release_has_its_terms()
    check_the_terms_take_the_longest_match()
    check_a_repository_file_resolves_without_the_release()
    print("game_free_test: ok")


if __name__ == "__main__":
    main()
