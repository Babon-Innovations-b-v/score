"""Each library algorithm's demo, made on the store's machine for the cockpit's item page (#42: an algorithm's page
showed a still from a film and "in: code only"; owner, 2026-10-20: show what it does on one real example).

    .venv/bin/python -m score.stages.library.demos [--only crops_spots ...]

One module an algorithm in `score/stages/library/demo/` (its overlay has the shape) makes the demo from real data:
the repository's `data/` and the library entries' files, each fetched once into the library cache by the library's
own command (one object read). Every demo is checked against the shape and written into
`$PROPS_HOME/cache/library/demos.json` ({algorithm id: demo, or {"missing": why}}), which the cockpit reads and the
state export carries (`score/dashboard/state/library.py` `demos`). Never a row: nothing keys on it.
"""
import argparse
import importlib
import json
import pathlib
import pkgutil

from score.stages.library import backend, pictures

MAX_BYTES = 400_000  # one demo's JSON
VIEWS = ("plan", "side", "relief")
SHAPES = ("area", "line", "dots", "path", "text", "raster")
TONES = ("ground", "base", "made", "accent", "warn", "ghost", *(f"c{rank}" for rank in range(1, 9)))
REPO = pathlib.Path(__file__).resolve().parents[3]


class NoExample(Exception):
    """An algorithm has no real example to show yet; its words say why."""


class Inputs:
    """What a demo module reads: the repository's files and the library entries' files."""

    repo = REPO

    @staticmethod
    def library(address, named):
        """One file of a library entry in the library cache, fetched once; NoExample when the library lost it."""
        held, why = pictures.held_or_why(address, named, backend.settings().get("SCORE_LIB_ROOT"))
        if not held:
            raise NoExample(why or f"{address}: {named} not fetched")
        kind, rest = address.split("/", 1)
        entry_id, version = rest.split("@")
        return backend.library_files.cache_folder() / "score_lib" / kind / entry_id / version / named

    @staticmethod
    def json(address, named):
        return json.loads(Inputs.library(address, named).read_text())


def shape_problem(shape):
    """Why one shape is off the shape, or None."""
    if shape.get("kind") not in SHAPES:
        return f"shape kind {shape.get('kind')!r}"
    if shape.get("tone", "base") not in TONES:
        return f"tone {shape.get('tone')!r}"
    if not isinstance(shape.get("points"), list) or not shape["points"]:
        return f"{shape['kind']} without points"
    return None


def problems(demo):
    """What is off the shape in one demo (the overlay's), as words; [] when none."""
    found = [] if demo.get("view") in VIEWS else [f"view {demo.get('view')!r}"]
    if demo.get("view") == "relief" and not (demo.get("relief") or {}).get("heights"):
        found.append("relief without heights")
    if demo.get("view") != "relief" and len(demo.get("bounds") or []) != 4:
        found.append("no bounds")
    if not demo.get("example"):
        found.append("no example named")
    shapes = [shape for step in demo.get("steps") or [] for shape in step.get("shapes", [])]
    shapes += [shape for each in (demo.get("slider") or {}).get("shapes", []) for shape in each]
    found += [problem for problem in map(shape_problem, shapes) if problem]
    size = len(json.dumps(demo, separators=(",", ":")))
    if size > MAX_BYTES:
        found.append(f"{size} bytes, more than {MAX_BYTES}")
    return found


def modules():
    """{algorithm id: demo module} of every module in demo/."""
    from score.stages.library import demo
    found = {}
    for info in pkgutil.iter_modules(demo.__path__):
        module = importlib.import_module(f"score.stages.library.demo.{info.name}")
        found[module.ALGORITHM] = module
    return found


def made(module):
    """One module's demo, or {"missing": why} when it has no example or its demo is off the shape."""
    try:
        demo = module.made(Inputs)
    except NoExample as why:
        return {"missing": str(why)}
    except Exception as error:  # one broken demo is named in the run's line and on its page, never stops the others
        return {"missing": f"its demo failed: {type(error).__name__}: {str(error)[:200]}"}
    off = problems(demo)
    return {"missing": "its demo is off the shape: " + "; ".join(off)} if off else demo


def path():
    return backend.library_files.cache_folder() / "demos.json"


def run(only=None):
    """Make every demo (or `only` those) into demos.json, keeping the others it holds; the summary line."""
    target = path()
    kept = json.loads(target.read_text()) if target.is_file() else {}
    chosen = {name: module for name, module in modules().items() if not only or name in only}
    for name, module in chosen.items():
        kept[name] = made(module)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(kept, separators=(",", ":"), sort_keys=True))
    missing = {name: kept[name]["missing"] for name in chosen if "missing" in kept[name]}
    return (f"library demos: {len(chosen) - len(missing)} of {len(chosen)} made into {target}"
            + (f" (not made: {'; '.join(f'{name}: {why[:120]}' for name, why in missing.items())})" if missing else ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", action="append", help="an algorithm id whose demo to make (default: every one)")
    print(run(set(parser.parse_args(argv).only or [])))


if __name__ == "__main__":
    from score.stages.library import demos  # by its own name: the modules raise its NoExample, not __main__'s
    demos.main()
