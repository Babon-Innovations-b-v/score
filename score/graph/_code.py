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
# followed either. The store stays in: stages call it (PROPS_HOME, Store). The run machinery is left out too (the
# coordinator, 2026-10-12; the owner, 2026-10-23, after a body was made again for EUR 0.30 by warm-pool edits: "oh
# yeah u can fix that"): code that only decides where and how a job runs (renting, pools, zones, classes, parking,
# the ledger and books, money guards, forecasts, kept jobs, secrets, detaching, the cockpit) changes what a run costs,
# never what it makes. What shapes an output stays in: a maker and the scripts it sends up (each runner's own module,
# its set-up and worker, tools/cloud/runtime and the job images), its pinned models, parameters, recipes and the
# libraries it reads. An entry is a file, or a folder whose every file is left out. The shared loop's package
# (score/stages/shapes_first/__init__.py) is the table's wiring too: it defines no make or check, only the rows, and
# scene_palette's `from score.stages.shapes_first import align` put it and the whole prop route behind it into
# surface-library's, the palette's and body-face's keys (2026-10-28: a likeness_row edit moved body-face-earth).
FRAMEWORK = {REPO / name for name in ("score/__main__.py", "score/graph/__init__.py", "score/graph/_code.py",
                                      "score/review/__init__.py", "score/review/__main__.py",
                                      "score/adapters/compute", "score/dashboard", "score/stages/__init__.py",
                                      "score/stages/__main__.py", "score/stages/shapes_first/__init__.py",
                                      "tools/cloud/batch.py",
                                      "tools/cloud/capacity.py", "tools/cloud/park.py",
                                      "tools/cloud/pool.py", "tools/cloud/spread.py",
                                      "tools/cloud/provider.py", "tools/cloud/backends",
                                      "tools/cloud/preflight.py", "tools/cloud/kept.py",
                                      "tools/cloud/self_delete.py", "tools/cloud/secret_store.py",
                                      "tools/cloud/detached.py", "tools/cloud/google_spend.py",
                                      "tools/cloud/google_bill.py", "tools/cloud/blender_cloud.py",
                                      "tools/cloud/ledger.py", "tools/cloud/inputs.py",
                                      "tools/library/pixal_takes.py")}
# Where FRAMEWORK is declared, read at an older commit to rebuild the code version a record was made under.
DECLARED_IN = "score/graph/_code.py"


def in_repo(path):
    """True for a source file of this repository (not its virtual environment)."""
    return under_repo(pathlib.Path(path), REPO, OUTSIDE)


@functools.cache
def under_repo(path, repo, outside):
    """in_repo's answer, once a path a process (a code version asks it of every file behind every stage)."""
    path = path.resolve()
    return path.is_relative_to(repo) and not any(path.is_relative_to(folder) for folder in outside)


@functools.cache
def search_folders():
    """The import path's folders as this process first works out a code version, kept from then on. A make or a
    later import that puts a folder on the path (the light layer's tools/props/scene, terrain's tools/cloud)
    would otherwise give another same-named module to a stage worked out after it: effects-layer took in triage.py
    and feet.py through stages_test's earlier tests, 2026-10-13."""
    return tuple(sorted({pathlib.Path(entry).resolve() for entry in sys.path if entry}))


def module_files(name, is_file=pathlib.Path.is_file):
    """Every source file of ours an import name could find in each folder of the path (`search_folders`), read
    from the files alone, never from what is imported; `is_file` says which files the tree holds (this checkout's by
    default). Hashing all of them keeps the code version the same whatever order a process put the path's folders in
    (judge.py puts tools/props first when imported; a row's key moved with no file changed)."""
    found = set()
    parts = name.split(".")
    for folder in search_folders():
        for path in (folder.joinpath(*parts).with_suffix(".py"), folder.joinpath(*parts, "__init__.py")):
            if is_file(path) and in_repo(path):  # the cheap test first: most candidates are not there
                found.add(path.resolve())
    return found


def imported_names(source, path, package):
    """Every module name a source file's text imports, anywhere in it (inside functions too), made absolute."""
    names = []
    for node in ast.walk(ast.parse(source, str(path))):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = importlib.util.resolve_name("." * node.level + (node.module or ""), package) if node.level \
                else node.module
            names += [base] + [f"{base}.{alias.name}" for alias in node.names]
    return names


def package_of(path, is_file=pathlib.Path.is_file):
    """The dotted package a repository file sits in, for its relative imports ('' outside a package); `is_file` says
    which files the tree holds (this checkout's by default)."""
    parts = []
    folder = pathlib.Path(path).parent
    while is_file(folder / "__init__.py"):
        parts.insert(0, folder.name)
        folder = folder.parent
    return ".".join(parts)


def start_files(functions):
    """The source files the functions are defined in (a wrapped judge: the wrapper's and its own)."""
    return [pathlib.Path(inspect.getsourcefile(each)).resolve() for function in functions
            for each in (function, inspect.unwrap(function))]


def imports_of(path, is_file, read_text):
    """The repository files a file's imports could be found as, in the tree `is_file` and `read_text` read."""
    return {module for name in imported_names(read_text(path), path, package_of(path, is_file))
            for module in module_files(name, is_file)}


def in_framework(path, framework):
    """True for a file `framework` names, or one inside a folder it names (a set lookup of the path and each folder
    above it: the walk asks it of every file behind every stage)."""
    return path in framework or not framework.isdisjoint(path.parents)


def followed(starts, framework, imports):
    """Every repository file of a tree the start files are or import, followed through each import, the files in
    `framework` (in_framework) left out; `imports` gives a file's imported files in that tree (imports_of)."""
    pending, found = list(starts), set()
    while pending:
        path = pending.pop()
        if path in found or in_framework(path, framework) or not in_repo(path):
            continue
        found.add(path)
        pending += [module for module in imports(path) if module not in found]
    return sorted(found)


LIVE_IMPORTS = {}  # (path, search_folders()): ((mtime_ns, size), imports_of's answer) for this checkout's files


def live_imports(path):
    """imports_of for a file of this checkout, worked out again only when its size or modification time moved or a
    file it found is gone: every row's walk parses each module behind it, about 1 s a row cold, and the runner's plan
    and the sync's price ask for every row (#49). A new file an unchanged file's import would now also find is not
    seen until that file changes or the process restarts."""
    stat = path.stat()
    stamp, key = (stat.st_mtime_ns, stat.st_size), (path, search_folders())
    known = LIVE_IMPORTS.get(key)
    if known is None or known[0] != stamp or not all(module.is_file() for module in known[1]):
        known = LIVE_IMPORTS[key] = (stamp, imports_of(path, pathlib.Path.is_file, pathlib.Path.read_text))
    return known[1]


def source_files(functions):
    """Every repository file the functions' modules are or import, followed through each import, the framework's
    own files (FRAMEWORK) left out."""
    return followed(start_files(functions), FRAMEWORK, live_imports)


def python_part():
    """The code version's first part: this Python's version."""
    return f"python {sys.version_info.major}.{sys.version_info.minor}"


def code_version(functions, hash_file):
    """The hash of the source files behind the functions, with the Python version."""
    parts = [python_part()]
    parts += [f"{path.relative_to(REPO).as_posix()} {hash_file(path)}" for path in source_files(functions)]
    return parts


TREES = {}  # (repository, commit): blobs_at's answer, once known


def blobs_at(commit):
    """{repository path: its blob id} of every file in `commit`'s tree (read once a process); None for a commit git
    does not know (asked again next time: a fetch may bring it)."""
    if (REPO, commit) not in TREES:
        listed = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", commit], capture_output=True,
                                text=True)
        if listed.returncode:
            return None
        entries = (entry.split("\t", 1) for entry in listed.stdout.split("\0") if entry)
        TREES[REPO, commit] = {name: meta.split()[2] for meta, name in entries if meta.split()[1] == "blob"}
    return TREES[REPO, commit]


@functools.cache
def blob_bytes(blob):
    """A git blob's content."""
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", blob], capture_output=True,
                          check=True).stdout


def framework_at(commit):
    """FRAMEWORK as `commit`'s tree declared it (the names in DECLARED_IN's FRAMEWORK assignment); None when that
    tree has no such file or assignment, or git does not know the commit."""
    blobs = blobs_at(commit)
    if blobs is None or DECLARED_IN not in blobs:
        return None
    for node in ast.walk(ast.parse(blob_bytes(blobs[DECLARED_IN]))):
        if isinstance(node, ast.Assign) and any(getattr(target, "id", None) == "FRAMEWORK" for target in node.targets):
            return {REPO / found.value for found in ast.walk(node.value)
                    if isinstance(found, ast.Constant) and isinstance(found.value, str)}
    return None


VERSIONS = {}  # (repository, commit, start files, Python): code_version_at's answer


def code_version_at(commit, functions):
    """The code version the functions' start files had at `commit`, rebuilt from git once a process (each place of a
    stage asks): see rebuilt_at. Cold, it costs about 2 s a stage (264 s for all 135 stages, 2026-10-17), paid once a
    process for each stage whose key moved, before the runner falls back to a make; a caller timing a run or a rebuy
    count must allow for it."""
    asked = (REPO, commit, tuple(start_files(functions)), python_part())
    if asked not in VERSIONS:
        VERSIONS[asked] = rebuilt_at(commit, asked[2])
    return VERSIONS[asked]


def rebuilt_at(commit, starts):
    """The code version start files had at `commit`, rebuilt from git: the files they were or imported in that tree,
    followed with that tree's FRAMEWORK, hashed as code_version hashes them, after this Python's version. None when
    git does not know the commit, its FRAMEWORK cannot be read or a start file was not in it."""
    blobs, framework = blobs_at(commit), framework_at(commit)
    if blobs is None or framework is None or any(relative(path) not in blobs for path in starts
                                                 if in_repo(path) and not in_framework(path, framework)):
        return None

    def is_file(path):
        return in_repo(path) and relative(path) in blobs

    def read_text(path):
        return blob_bytes(blobs[relative(path)]).decode()

    parts = [python_part()]
    parts += [f"{relative(path)} {hashlib.sha256(blob_bytes(blobs[relative(path)])).hexdigest()}"
              for path in followed(starts, framework, lambda path: imports_of(path, is_file, read_text))]
    return parts


DOCUMENTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)


def doc_reads(tree):
    """How a parsed file reads docstrings: "others" when it reads any object's (`x.__doc__`, `getdoc`), "own" when
    only its module's (`__doc__`: a usage text), None when it reads none."""
    found = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("__doc__", "getdoc") or \
                isinstance(node, ast.Name) and node.id == "getdoc":
            return "others"
        if isinstance(node, ast.Name) and node.id == "__doc__":
            found = "own"
    return found


def without_docstrings(tree):
    """The parsed file with every module, class and function docstring taken out (an emptied body gets `pass`)."""
    for node in ast.walk(tree):
        if isinstance(node, DOCUMENTED) and node.body and isinstance(node.body[0], ast.Expr) and \
                isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    return tree


def words_only(commit, relatives, read):
    """True when each repository Python file of `relatives` differs between `commit` and this tree only in words
    that cannot change what it does: comments, blank lines, layout and docstrings (these count when a file reads its
    own `__doc__`, and in every file when any file of `read`, the files the code reads today, reads another
    object's). Type hints and names count: a dataclass or a caller can read them. False for any other file, a file
    not at `commit`, one deleted, or one that does not parse."""
    blobs = blobs_at(commit)
    if blobs is None:
        return False
    pairs = []
    for name in relatives:
        path = REPO / name
        if not name.endswith(".py") or name not in blobs or not path.is_file():
            return False
        try:
            pairs.append((ast.parse(blob_bytes(blobs[name])), ast.parse(path.read_text())))
        except (SyntaxError, ValueError, UnicodeDecodeError):
            return False
    keep_all = any(doc_reads(tree) == "others" for pair in pairs for tree in pair) or \
        any(doc_reads(ast.parse((REPO / name).read_text())) == "others" for name in read if name.endswith(".py"))
    for then, now in pairs:
        docstrings = keep_all or "own" in (doc_reads(then), doc_reads(now))
        if meaning_of(then, docstrings) != meaning_of(now, docstrings):
            return False
    return True


def meaning_of(tree, docstrings):
    """What a parsed Python file does, as text: its syntax tree's dump, so comments, blank lines and layout are not
    in it, its docstrings left out unless `docstrings`. Two files of the same meaning run the same."""
    return ast.dump(tree if docstrings else without_docstrings(tree))


def unchanged(entries, hash_file):
    """True when every code version entry ("<repository path> <hash>") names a file this checkout still holds and
    `hash_file` hashes as the entry says. A deleted file is not unchanged: an unchanged file that imported it may now
    fail, or find a same-named module outside the repository."""
    for entry in entries:
        name, recorded = entry.rsplit(" ", 1)
        path = REPO / name
        if not path.is_file() or hash_file(path) != recorded:
            return False
    return True


def relative(path):
    """A repository file's path as git names it."""
    return pathlib.Path(path).resolve().relative_to(REPO).as_posix()


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
