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


def module_file(name):
    """The source file an import name finds on today's path, or None when it finds none or none of ours."""
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):  # a parent package that does not import here: not one of ours to hash
        return None
    origin = spec.origin if spec else None
    return pathlib.Path(origin).resolve() if origin and origin.endswith(".py") and in_repo(origin) else None


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
    pending = [pathlib.Path(inspect.getsourcefile(function)).resolve() for function in functions]
    found = set()
    while pending:
        path = pending.pop()
        if path in found or not in_repo(path):
            continue
        found.add(path)
        for name in imported_names(path, package_of(path)):
            module = module_file(name)
            if module and module not in found:
                pending.append(module)
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
