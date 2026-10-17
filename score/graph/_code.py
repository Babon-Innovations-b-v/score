"""A stage's code version, computed: the hash of every repository file its functions' modules are, and every
repository module those import, followed import by import. No hand-bumped string to forget."""
import ast
import functools
import hashlib
import importlib.util
import inspect
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUTSIDE = (REPO / ".venv", REPO / ".git")
# What runs a stage, not what a stage runs: the runner, the review pages, the clearance and the stage table. A stage
# reaches them through imports (batch -> compute -> graph), and every builder edits them, so hashing them moved every
# stage's key on each other's edits (terrain re-made under the effects line, 2026-10-12). Their imports are not
# followed either. The store stays in: stages call it (PROPS_HOME, Store). The renting code is left out too (the
# coordinator, 2026-10-12): which card, zone and machine a job gets, parking and the ledger change what a run costs,
# never what it makes, and the cost fixes of that day would otherwise have re-made terrain and every assembly.
FRAMEWORK = {REPO / name for name in ("score/__main__.py", "score/graph/__init__.py", "score/graph/_code.py",
                                      "score/review/__init__.py", "score/review/__main__.py",
                                      "score/adapters/compute/__init__.py", "score/stages/__init__.py",
                                      "score/stages/__main__.py", "tools/props/cloud/batch.py",
                                      "tools/props/cloud/capacity.py", "tools/props/cloud/park.py",
                                      "tools/props/cloud/blender_cloud.py", "tools/props/cloud/ledger.py")}


def in_repo(path):
    """True for a source file of this repository (not its virtual environment)."""
    path = pathlib.Path(path).resolve()
    return path.is_relative_to(REPO) and not any(path.is_relative_to(folder) for folder in OUTSIDE)


@functools.cache
def search_folders():
    """The import path's folders as this process first works out a code version, kept from then on. A make or a
    later import that puts a folder on the path (the light layer's tools/props/scene, terrain's tools/props/cloud)
    would otherwise give another same-named module to a stage worked out after it: effects-layer took in triage.py
    and feet.py through stages_test's earlier tests, 2026-10-13."""
    return tuple(sorted({pathlib.Path(entry).resolve() for entry in sys.path if entry}))


def module_files(name):
    """Every source file of ours an import name could find in each folder of the path (`search_folders`), read
    from the files alone, never from what is imported. Hashing all of them keeps the code version the same whatever
    order a process put the path's folders in (judge.py puts tools/props first when imported; a row's key moved
    with no file changed)."""
    found = set()
    parts = name.split(".")
    for folder in search_folders():
        for path in (folder.joinpath(*parts).with_suffix(".py"), folder.joinpath(*parts, "__init__.py")):
            if path.is_file() and in_repo(path):
                found.add(path.resolve())
    return found


def imported_names(path, package):
    """Every module name a source file imports, anywhere in it (inside functions too), made absolute."""
    names = []
    for node in ast.walk(ast.parse(pathlib.Path(path).read_text(), str(path))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = importlib.util.resolve_name("." * node.level + (node.module or ""), package) if node.level \
                else node.module
            names += [base] + [f"{base}.{alias.name}" for alias in node.names]
    return names


def package_of(path):
    """The dotted package a repository file sits in, for its relative imports ('' outside a package)."""
    parts = []
    folder = pathlib.Path(path).parent
    while (folder / "__init__.py").exists():
        parts.insert(0, folder.name)
        folder = folder.parent
    return ".".join(parts)


def source_files(functions):
    """Every repository file the functions' modules are or import, followed through each import, the framework's
    own files (FRAMEWORK) left out."""
    pending = [pathlib.Path(inspect.getsourcefile(each)).resolve() for function in functions
               for each in (function, inspect.unwrap(function))]  # a wrapped judge: the wrapper's and its own
    found = set()
    while pending:
        path = pending.pop()
        if path in found or path in FRAMEWORK or not in_repo(path):
            continue
        found.add(path)
        for name in imported_names(path, package_of(path)):
            pending += [module for module in module_files(name) if module not in found]
    return sorted(found)


def code_version(functions, hash_file):
    """The hash of the source files behind the functions, with the Python version."""
    parts = [f"python {sys.version_info.major}.{sys.version_info.minor}"]
    parts += [f"{path.relative_to(REPO).as_posix()} {hash_file(path)}" for path in source_files(functions)]
    return parts


def holds(commit):
    """True when this checkout's HEAD is `commit` or comes after it, or when no branch holds `commit` any more (a local
    commit rebased onto main before its push: its change is on main under another commit, and nothing could ever
    hold it; terrain's hangar seat, 2026-10-13); False for a commit it lacks or one only a newer main holds."""
    if subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", commit, "HEAD"],
                      capture_output=True).returncode == 0:
        return True
    known = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True)
    branches = subprocess.run(["git", "-C", str(REPO), "for-each-ref", "--contains", commit, "refs/heads",
                               "refs/remotes"], capture_output=True, text=True)
    return known.returncode == 0 and branches.returncode == 0 and not branches.stdout.strip()


def changed_since(commit, relatives):
    """Of the repository paths `relatives`, those whose content differs between `commit` and this tree (changes not
    committed included); None when git does not know the commit (nothing can be proved against it)."""
    found = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", commit, "--", *relatives],
                           capture_output=True, text=True)
    return sorted(found.stdout.split()) if found.returncode == 0 else None


def unchanged_since(commit, relatives):
    """True when every repository file in `relatives` is in `commit`'s tree and reads now as it did there (changes
    not committed included); False for one git does not hold at that commit (a new file, never committed, that a
    plain diff passes over) or for a commit git does not know."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", commit, "--", *relatives],
                            capture_output=True, text=True)
    if listed.returncode or set(relatives) - set(filter(None, listed.stdout.split("\0"))):
        return False
    return changed_since(commit, relatives) == []


def source_hash_at(commit, relative):
    """The key hash (graph.source_hash) a repository file or folder had at `commit`, from git's own objects (None
    for a commit git does not know): the
    sources only, as git holds no bytecode."""
    from score.store import listing_hash
    listed = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", commit, "--", relative],
                            capture_output=True, text=True)
    if listed.returncode:  # a commit git does not know: nothing to compare with
        return None
    entries = listed.stdout.split("\0")
    blobs = {}
    for entry in filter(None, entries):
        meta, name = entry.split("\t", 1)
        if meta.split()[1] == "blob":
            blobs[pathlib.PurePosixPath(name).name if name == relative
                  else pathlib.PurePosixPath(name).relative_to(relative).as_posix()] = meta.split()[2]
    if not blobs:  # nothing there at that commit
        return listing_hash({})
    asked = ("\n".join(blobs.values()) + "\n").encode()
    batch = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"], input=asked, capture_output=True,
                           check=True).stdout
    listing, at = {}, 0
    for name, blob in blobs.items():
        header_end = batch.index(b"\n", at)
        size = int(batch[at:header_end].split()[2])
        listing[name] = hashlib.sha256(batch[header_end + 1:header_end + 1 + size]).hexdigest()
        at = header_end + 1 + size + 1
    return listing_hash(listing)


def git_commit():
    """The repository's commit, and whether its tree has changes not committed."""
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    changes = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True,
                             check=True)
    return {"commit": head.stdout.strip(), "uncommitted": bool(changes.stdout.strip())}
