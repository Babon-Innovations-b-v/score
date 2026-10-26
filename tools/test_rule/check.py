"""The guard on the test rule (docs/bible.md workflow/module-standard; owner, 2026-10-26: "only 1 but one actual good
meaning full test file per module ... i feel like that rule kinda drifted by now"): it lists every way the repository's
test files break the rule, so the rule cannot drift again. `make tests` runs it and fails on any fault.

    python3 tools/test_rule/check.py                 # every module in the repository
    python3 tools/test_rule/check.py <test file> ... # only the modules those files belong to (make tests TESTS="...")

A test file is a file named `test_*.py` or `*_test.py`, tracked or new (not ignored), outside `vendor/`. Its faults:

- **named for its module, not its invariant**: every test file is `test_<invariant>.py`.
- **no break**: its module docstring has no line naming the break that turns it red ("break" and "red" in one statement,
  at most 200 characters apart, as "Breaks (each applied once, seen red, reverted), in ...:").
- **more than one test file in a module**: a module is the directory its test file sits in, a `tests/` folder counting
  as its parent's (`.claude/hooks/tests` is `.claude/hooks`). In a flat folder of independent tools (`FLAT_TOOL_FOLDERS`)
  a top-level test file belongs to the tool script its docstring names first (as `tools/<folder>/<tool>.py`, else as
  `<tool>.py`, else as the bare name), and one that names none is a fault of its own.

`ALLOWLIST` holds the modules other agents' sweeps are still reworking, dated; each sweep empties its own entries, and
nothing else goes in it. The output is one summary line, then one line a fault.
"""
import ast
import fnmatch
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]

# Folders of independent command-line tools: each top-level tool script is a module of its own.
FLAT_TOOL_FOLDERS = ("tools/cloud", "tools/props", "tools/review")

# Modules still being swept by other agents on 2026-10-26: skipped until their sweep empties the entry.
ALLOWLIST_DATE = "2026-10-26"
ALLOWLIST = (
    "tools/usd/*",
    "score/stages/complete/*",
    "score/stages/closeup/*",
    "score/stages/props/*",
    "score/stages/settling/*",
    "score/stages/physics/*",
    "score/review/plan_fixes*",
    "score/review/plan_checks*",
    "*prepare*",
)

# "break" and "red" in one statement, which may wrap over the docstring's lines.
BREAK_LINE = re.compile(r"\bbreaks?\b.{0,200}?\bred\b|\bred\b.{0,200}?\bbreaks?\b", re.IGNORECASE)


def is_test_file(path):
    """Whether a repository path names a test file under the rule (vendor/ is third-party, kept as released)."""
    name = path.name
    return (not path.parts or path.parts[0] != "vendor") and name.endswith(".py") and (
        name.startswith("test_") or name.endswith("_test.py"))


def test_files(root):
    """The repository's test files, tracked or new and not ignored, that exist on disk, as paths from the root."""
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            check=True, capture_output=True, text=True).stdout
    paths = {pathlib.PurePosixPath(entry) for entry in listed.split("\0") if entry}
    return sorted(path for path in paths if is_test_file(path) and (root / path).is_file())


def allowlisted(path):
    """Whether a test file sits in a module the allowlist still exempts."""
    return any(fnmatch.fnmatch(str(path), pattern) for pattern in ALLOWLIST)


def docstring(root, path):
    """A test file's module docstring ("" when it has none), or None when the file does not parse."""
    try:
        return ast.get_docstring(ast.parse((root / path).read_text(encoding="utf-8"))) or ""
    except SyntaxError:
        return None


def named_tool(root, path, text):
    """The tool script of a flat folder that a top-level test file's docstring names first, or None."""
    folder = path.parent
    tools = {sibling.stem for sibling in (root / folder).glob("*.py")
             if not is_test_file(pathlib.PurePosixPath(sibling.name)) and sibling.name != "__init__.py"}
    for pattern in (re.escape(str(folder)) + r"/(\w+)\.py\b", r"\b(\w+)\.py\b", r"\b(\w+)\b"):
        for found in re.finditer(pattern, text):
            if found.group(1) in tools:
                return found.group(1)
    return None


def module_of(root, path, text):
    """The module a test file belongs to, as a path from the root, or None for a flat-folder test naming no tool."""
    folder = path.parent
    if folder.name == "tests":
        folder = folder.parent
    if str(path.parent) in FLAT_TOOL_FOLDERS:
        tool = named_tool(root, path, text or "")
        return folder / tool if tool else None
    return folder


def file_faults(path, text):
    """One test file's own faults: its name and its docstring's break line."""
    faults = []
    if not path.name.startswith("test_"):
        faults.append(f"{path}: named for its module, not its invariant (rename to test_<invariant>.py)")
    if text is None:
        faults.append(f"{path}: does not parse")
    elif not BREAK_LINE.search(" ".join(text.split())):
        faults.append(f"{path}: its docstring has no line naming the break that turns it red")
    return faults


def faults(root, named=()):
    """Every fault of the rule in the repository at `root`, or only in the modules of the `named` test files."""
    root = pathlib.Path(root)
    modules = {}
    found = []
    for path in test_files(root):
        if allowlisted(path):
            continue
        text = docstring(root, path)
        module = module_of(root, path, text)
        if module is None:
            found.append(f"{path}: its docstring names none of {path.parent}'s tool scripts")
            module = path
        modules.setdefault(module, []).append((path, text))
    wanted = {pathlib.PurePosixPath(name) for name in named}
    for module, files in sorted(modules.items()):
        if wanted and not wanted & {path for path, _ in files}:
            continue
        if len(files) > 1:
            found.append(f"{module}: {len(files)} test files, one a module: {', '.join(str(path) for path, _ in files)}")
        for path, text in files:
            found.extend(file_faults(path, text))
    return sorted(set(found))


def main(argv):
    """Print the summary line and each fault; exit 1 when there is any."""
    found = faults(REPO, argv)
    print(f"test rule: {len(found)} fault(s) (allowlist of {ALLOWLIST_DATE}: {len(ALLOWLIST)} entries)")
    for fault in found:
        print(f"  {fault}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
