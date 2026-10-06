"""A kit room as real meshes in the room's frame, for the gates: the shell's outer skin from the room's numbers and
every laid piece's own model placed as the game places it (HubKit), never its box.

    import room
    skin = room.outer_skin()                                     # the hub shell's outer solid (convex)
    placed = room.placed(layout, room.game_models)               # [(index, kind, mesh in the room's frame)]

The placing is HubKit's (game/base/hub_kit/hub_kit.gd), in numpy: a kind's model turned by its `base`, fitted per
axis to the size its piece is laid at, standing on its foot's middle, then put at the piece's origin and axes. A kind
drawn from its picture (HubKit.pictured_mesh, pictured_triangle) is the same unit box, less its hole, or the triangle
slab. Models load without their pictures (`skip_materials`), so a room of them stays small in memory.
"""
import math
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools/props/scene"))
import hub_kit  # noqa: E402

GAME_MODELS = REPO / "game/base/models"
SHELL_WALL = 0.3  # ModuleShell.WALL
ROOF_THICK = 0.25  # ModuleShell.ROOF_THICK
FLOOR_UNDER = -1.2  # below the pit's floor


def outer_skin():
    """The hub shell's outer solid: the twelve walls' outside faces and the roof's top, closed under the pit."""
    outer = hub_kit.APOTHEM + SHELL_WALL
    slope = math.atan2(hub_kit.RISE, hub_kit.APOTHEM)
    lift = ROOF_THICK / math.cos(slope)  # the roof's top plane, as high again over every point of its underside
    eave = hub_kit.WALL_HIGH + lift - SHELL_WALL * math.tan(slope)
    apex = hub_kit.WALL_HIGH + hub_kit.RISE + lift
    corner = outer / math.cos(math.pi / hub_kit.FACETS)
    points = []
    for index in range(hub_kit.FACETS):
        angle = math.radians(index * 30 + 15)
        x, z = math.sin(angle) * corner, -math.cos(angle) * corner
        points += [(x, FLOOR_UNDER, z), (x, eave, z)]
    points.append((0.0, apex, 0.0))
    return trimesh.convex.convex_hull(np.array(points))


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


def pictured_box(hole):
    """HubKit.pictured_mesh: the unit box (x -0.5..0.5, y 0..1, z -0.5..0.5) less its hole, seen from in front."""
    bars = [(0.0, 0.0, 1.0, 1.0)]
    if len(hole) == 4:
        left, bottom, right, top = (float(value) for value in hole)
        bars = [(0.0, 0.0, left, 1.0), (right, 0.0, 1.0, 1.0), (left, top, right, 1.0)]
        if bottom > 0:
            bars.append((left, 0.0, right, bottom))
    boxes = []
    for left, bottom, right, top in bars:
        low = np.array([0.5 - right, bottom, -0.5])
        high = np.array([0.5 - left, top, 0.5])
        boxes.append(trimesh.creation.box(bounds=[low, high]))
    return trimesh.util.concatenate(boxes)


def pictured_triangle():
    """HubKit.pictured_triangle: a triangular slab, foot along y 0, tip at the top middle."""
    corners = [(-0.5, 0.0), (0.5, 0.0), (0.0, 1.0)]
    points = np.array([(x, y, z) for z in (-0.5, 0.5) for x, y in corners])
    return trimesh.convex.convex_hull(points)


def game_models(kind, about):
    """A kind's unit model as the game draws it from data/kit layouts; None when it has none."""
    if "picture" in about:
        return pictured_triangle() if about.get("shape") == "triangle" else pictured_box(about.get("hole", []))
    path = GAME_MODELS / kind / f"{kind}.glb"
    if not path.exists():
        return None
    mesh = trimesh.load(path, force="mesh", skip_materials=True)
    return unit_fit(mesh, basis(about["base"]) if "base" in about else np.eye(3))


def models_in(folder):
    """A resolver for kinds whose models are .glb files in `folder`, in the kit frame already (code-built)."""
    def resolve(kind, about):
        path = pathlib.Path(folder) / f"{kind}.glb"
        if not path.exists():
            return game_models(kind, about)
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


def placed(layout, resolve, chosen=None):
    """Every laid piece (or the `chosen` indices) as its model in the room's frame: (index, kind, mesh)."""
    units = {}
    found = []
    for index, laid in enumerate(layout["pieces"]):
        if chosen is not None and index not in chosen:
            continue
        kind = laid["kind"]
        if kind not in units:
            units[kind] = resolve(kind, layout["kinds"].get(kind, {}))
        if units[kind] is None:
            continue
        mesh = units[kind].copy()
        mesh.apply_transform(piece_matrix(laid))
        found.append((index, kind, mesh))
    return found


def bearing_of(points):
    """Bearings (degrees clockwise from north, -z) of points in the room's frame."""
    return np.degrees(np.arctan2(points[:, 0], -points[:, 2])) % 360
