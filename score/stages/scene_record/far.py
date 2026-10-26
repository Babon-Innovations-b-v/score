"""Where a far thing of a place stands (the owner, 2026-10-26: the skyline is the environment's own scenes where its
plan puts them, and ordinary objects for anything that is no scene; the sea is water in the place): along the bearing
its concept box is seen at, at the distance its read height rises to its box's height in the framework's view.

The bearing comes from the plan fixes' projection (score/review/plan_checks.projection: concept shares to plan metres,
fitted on the rows boxed and laid alike): away from the viewer is up the picture, across is its right. A box's middle
across is turned off that heading by its angle in the framework's view (VIEW_FOV across the
picture), and its distance is its read tall over its box's height at that view's focal length, as the terrain's far
landforms are sized (terrain.design.far_size). Both stand from the plan's middle.

    far.heading(plan, inventory)            # (away, right): unit plan vectors, or None without a projection
    far.spot(plan, inventory, row)          # {at, way, distance, bearing}: plan metres, or None
    far.far_object(row, beyond)             # a model row the place shows far off (beyond it, or its backdrop)
"""
import math

import numpy as np

VIEW_FOV = 80  # degrees across the picture: the framework's view, the scene record's views' fov
FAR_ANCHORS = ("floor", "ground")  # a far object stands on the far ground: a sky or wall row is none


def far_object(row, beyond):
    """Whether an inventory row is an ordinary object the place shows far off: no ground or water (terrain), standing
    on the ground, its part the backdrop or its id beyond the place (the plan's `beyond`)."""
    from score.review.plan_checks import anchor_of
    return not row.get("terrain") and anchor_of(row) in FAR_ANCHORS and (
        row.get("part") == "backdrop" or row["id"] in beyond)


def box_of(row, picture):
    """A row's surest box in concept pixels: SAM 3's, else Gemini's region round it; None with neither."""
    from score.review.plan_checks import gemini_box
    box = (row.get("boxes") or [row.get("box")])[0]
    if box:
        return box
    return gemini_box(row["region"], picture) if row.get("region") and picture else None


def focal(picture):
    """The framework's view's focal length in pixels of a picture `picture` [wide, tall] wide."""
    return picture[0] / 2 / math.tan(math.radians(VIEW_FOV) / 2)


def heading(plan, inventory):
    """(away, right) unit plan vectors: away from the concept's viewer (up the picture), and across to its right
    (square to away); None when the plan fixes fit no projection."""
    from score.review import plan_checks
    matrix = plan_checks.projection(plan, inventory)
    if matrix is None:
        return None
    away = -np.asarray(matrix[1], dtype=float)
    across = np.asarray(matrix[0], dtype=float)
    if np.linalg.norm(away) < 1e-9:
        return None
    away /= np.linalg.norm(away)
    right = across - (across @ away) * away
    if np.linalg.norm(right) < 1e-9:
        right = np.array([-away[1], away[0]])
    return away, right / np.linalg.norm(right)


def angle_at(across, picture):
    """The angle (radians, right positive) a picture column `across` pixels in is seen off the view's middle."""
    return math.atan((across - picture[0] / 2) / focal(picture))


def bearing(angle, ways):
    """The unit plan vector `angle` radians right of `away` (ways: heading's)."""
    away, right = ways
    return math.cos(angle) * away + math.sin(angle) * right


def middle_of(plan):
    return np.array([float(plan["w"]) / 2, float(plan["d"]) / 2])


def spot(plan, inventory, row):
    """Where a far row stands on its plan: {at: its middle [x, y] plan metres, way: the plan way its long side lies
    along (square to its bearing), distance (metres from the plan's middle), bearing}; None without a heading, a box
    or a read tall."""
    picture, ways = inventory.get("picture"), heading(plan, inventory)
    box = box_of(row, picture)
    size = row.get("size")
    if ways is None or not box or box[3] <= box[1] or not (isinstance(size, list) and len(size) == 3 and size[2]):
        return None
    toward = bearing(angle_at((box[0] + box[2]) / 2, picture), ways)
    reach = float(np.hypot(float(plan["w"]), float(plan["d"]))) / 2
    distance = max(float(size[2]) * focal(picture) / (box[3] - box[1]), reach + max(float(side) for side in size[:2]))
    at = middle_of(plan) + toward * distance
    return {"at": [round(float(value), 3) for value in at], "way": [float(toward[1]), -float(toward[0])],
            "distance": round(distance, 1), "bearing": [round(float(value), 4) for value in toward]}
