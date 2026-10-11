"""A stage's code version, computed: the hash of every repository file its functions' modules are, and every
repository module those import, followed import by import. No hand-bumped string to forget."""
import ast
import importlib.util
import inspect
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUTSIDE = (REPO / ".venv", REPO / ".git")


def in_repo(path):
    """True for a source file of this repository (not its virtual environment)."""
    path = pathlib.Path(path).resolve()
    return path.is_relative_to(REPO) and not any(path.is_relative_to(folder) for folder in OUTSIDE)


def module_files(name):
    """Every source file of ours an import name could find: the one it finds on today's path, and the one in each
    other folder on the path. Hashing all of them keeps the code version the same whatever order a process put the
    path's folders in (judge.py puts tools/props first when imported; a row's key moved with no file changed)."""
    found = set()
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):  # a parent package that does not import here: not one of ours to hash
        spec = None
    origin = spec.origin if spec else None
    if origin and origin.endswith(".py") and in_repo(origin):
        found.add(pathlib.Path(origin).resolve())
    parts = name.split(".")
    for folder in {pathlib.Path(entry).resolve() for entry in sys.path if entry}:  # "" (the cwd): find_spec's
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
    """Every repository file the functions' modules are or import, followed through each import."""
    pending = [pathlib.Path(inspect.getsourcefile(each)).resolve() for function in functions
               for each in (function, inspect.unwrap(function))]  # a wrapped judge: the wrapper's and its own
    found = set()
    while pending:
        path = pending.pop()
        if path in found or not in_repo(path):
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


def git_commit():
    """The repository's commit, and whether its tree has changes not committed."""
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    changes = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True,
                             check=True)
    return {"commit": head.stdout.strip(), "uncommitted": bool(changes.stdout.strip())}
