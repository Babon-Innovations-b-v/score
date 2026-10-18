"""The proposals' files the state export carries next to the current version, in the order they go up: every
proposal's record and the index first, then its stills, before stills, media and light 3D copy, then the whole 3D
copies while they fit. The export (sync/building.py) copies each pair to the same path under its own folder
(<out>/proposals/...), so the hosted side reads them with records.py as the local side does."""
import pathlib

from score.dashboard.proposals import records

FIRST = ("proposal.json",)
THEN = ("stills/*", "before/*", "media/*", "web3d/*.json", "web3d/*-light.glb")
LAST = ("web3d/*.glb",)


def matching(root, patterns, taken):
    """[(file, path in the export)] of every proposal's files matching `patterns` not in `taken` yet."""
    found = []
    for folder in sorted(pathlib.Path(root).glob("*/*/")):
        if any(part.startswith(".") for part in folder.relative_to(root).parts):
            continue  # a proposal still being made
        for pattern in patterns:
            for path in sorted(folder.glob(pattern)):
                if path.is_file() and path not in taken:
                    taken.add(path)
                    found.append((path, f"proposals/{path.relative_to(root).as_posix()}"))
    return found


def files(root):
    """[(file, path in the export)] of every proposal under `root` (the dashboard home's proposals/), in upload
    order; [] when there are none."""
    root = pathlib.Path(root)
    if not (root / records.INDEX).is_file():
        return []
    taken = set()
    return [(root / records.INDEX, f"proposals/{records.INDEX}"), *matching(root, FIRST, taken),
            *matching(root, THEN, taken), *matching(root, LAST, taken)]


def is_whole_copy(path):
    """True for a proposal's whole 3D copy (web3d/<place>.glb), the biggest file and the last to go up."""
    path = pathlib.Path(path)
    return path.parent.name == "web3d" and path.suffix == ".glb" and not path.name.endswith("-light.glb")


def in_export(root, filler, wholes):
    """Copy every proposal's files into the export through `filler` (sync/building.py), the whole 3D copies only
    when `wholes`, else all the rest, in upload order."""
    for path, target in files(root):
        if is_whole_copy(path) == wholes:
            filler.place_copy(path, target, f"proposal {target}")
