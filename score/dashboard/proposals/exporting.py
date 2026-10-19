"""The basket's files the state export carries next to the current version, in the order they go up: the index, the
departments' items and the owner's answers first, then each place's details, its input pictures and its after's
light 3D copy, then the whole 3D copies while they fit. The export (sync/building.py) copies each pair to the same path under its own folder
(<out>/proposals/...), so the hosted side reads them with records.py as the local side does."""
import pathlib

from score.dashboard.proposals import records

FIRST = (records.DETAILS,)
THEN = ("inputs/*", "web3d/*.json", "web3d/*-light.glb")
LAST = ("web3d/*.glb",)


def matching(root, patterns, taken):
    """[(file, path in the export)] of every place's files matching `patterns` not in `taken` yet."""
    found = []
    for folder in sorted(pathlib.Path(root).glob("*/")):
        if folder.name.startswith("."):
            continue  # a place's details still being made
        for pattern in patterns:
            for path in sorted(folder.glob(pattern)):
                if path.is_file() and path not in taken:
                    taken.add(path)
                    found.append((path, f"proposals/{path.relative_to(root).as_posix()}"))
    return found


def files(root):
    """[(file, path in the export)] of the basket under `root` (the dashboard home's proposals/), in upload order;
    [] when none is made yet."""
    root = pathlib.Path(root)
    if not (root / records.INDEX).is_file():
        return []
    taken = set()
    kept = [(root / name, f"proposals/{name}") for name in (records.DECLARED, records.ANSWERS)
            if (root / name).is_file()]
    return [(root / records.INDEX, f"proposals/{records.INDEX}"), *kept, *matching(root, FIRST, taken),
            *matching(root, THEN, taken), *matching(root, LAST, taken)]


def is_whole_copy(path):
    """True for an after's whole 3D copy (web3d/<place>.glb or -around.glb), the biggest files and the last to go up."""
    path = pathlib.Path(path)
    return path.parent.name == "web3d" and path.suffix == ".glb" and not path.name.endswith("-light.glb")


def in_export(root, filler, wholes):
    """Copy the basket's files into the export through `filler` (sync/building.py), the whole 3D copies only when
    `wholes`, else all the rest, in upload order."""
    for path, target in files(root):
        if is_whole_copy(path) == wholes:
            filler.place_copy(path, target, f"basket {target}")
