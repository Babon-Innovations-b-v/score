"""A kit room as real meshes in the room's frame, for the gates: every laid piece's own model placed as the game
places it (HubKit), never its box (the hub shell's outer skin went with the old kits, 2026-10-21).

    import room
    placed = room.placed(layout, room.models_in(folder))         # [(index, kind, mesh in the room's frame)]

The placing is HubKit's (game/base/hub_kit/hub_kit.gd), in numpy: a piece's model (its own made model, `model`, or
its kind's) turned by its `base` if it has one, fitted per axis to the size the piece is laid at, standing on its
foot's middle, then put at the piece's origin and axes. Models load without their pictures (`skip_materials`), so a
room of them stays small in memory.
"""
import pathlib

import numpy as np
import trimesh


def basis(rows):
    """HubKit's Basis from a kind's `base` (nine numbers, row by row)."""
    return np.array(rows, dtype=np.float64).reshape(3, 3)


def unit_fit(mesh, turn):
    """The model turned, scaled per axis into a unit box standing on its foot's middle (HubKit.made_mesh)."""
    moved = mesh.copy()
    matrix = np.eye(4)
    matrix[:3, :3] = turn
    moved.apply_transform(matrix)
    low, high = moved.bounds
    size = np.maximum(high - low, 1e-6)
    foot = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    moved.apply_translation(-foot)
    moved.vertices = moved.vertices / size
    return moved


def model_file(folder, kind):
    """A kind's model in a folder, as .glb or .gltf; None when it has neither."""
    for suffix in (".glb", ".gltf"):
        path = pathlib.Path(folder) / f"{kind}{suffix}"
        if path.exists():
            return path
    return None


def models_in(*folders):
    """A resolver for models that are files in the folders (a route's made pieces, a scene package's objects), turned
    by their `base` if they have one; None for a model in none of them."""
    def resolve(name, about):
        path = next((found for found in (model_file(folder, name) for folder in folders) if found), None)
        if path is None:
            return None
        return unit_fit(trimesh.load(path, force="mesh", skip_materials=True),
                        basis(about["base"]) if "base" in about else np.eye(3))
    return resolve


def piece_matrix(laid):
    """HubKit.piece_transform: the piece's axes, scaled by its laid size, at its origin."""
    matrix = np.eye(4)
    axes = np.column_stack([laid["x"], laid["y"], laid["z"]]) * np.array(laid["size"])
    matrix[:3, :3] = axes
    matrix[:3, 3] = laid["at"]
    return matrix


def about_of(layout, laid):
    """A laid piece's model record: its own made model's (`model`) or its kind's."""
    return layout.get("models", {}).get(laid["model"], {}) if "model" in laid else layout["kinds"].get(laid["kind"], {})


def placed(layout, resolve, chosen=None):
    """Every laid piece (or the `chosen` indices) as its model in the room's frame: (index, kind, mesh)."""
    units = {}
    found = []
    for index, laid in enumerate(layout["pieces"]):
        if chosen is not None and index not in chosen:
            continue
        kind = laid["kind"]
        name = laid.get("model", kind)
        if name not in units:
            units[name] = resolve(name, about_of(layout, laid))
        if units[name] is None:
            continue
        mesh = units[name].copy()
        mesh.apply_transform(piece_matrix(laid))
        found.append((index, kind, mesh))
    return found


def bearing_of(points):
    """Bearings (degrees clockwise from north, -z) of points in the room's frame."""
    return np.degrees(np.arctan2(points[:, 0], -points[:, 2])) % 360
