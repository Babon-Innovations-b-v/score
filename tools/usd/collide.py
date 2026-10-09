"""Collision queries on a place's objects, each model's bounding volume tree built once and every copy of it mapped to
that one tree: which objects touch, whether two still touch after a nudge, and what a ray meets.

The shape of the interface follows ProcFunc's collision tools (Raistrick et al., arXiv 2604.26943: a collision set,
an intersection test and a raycast over FCL and trimesh, each mesh's tree built once and instances mapped to their
source), which its released code (v0.37.0, checked 2026-10-09) does not yet include; this is the small version on the
same libraries: python-fcl (BSD-3-Clause) for the trees and the broad and narrow phase, trimesh (MIT) for rays.

    scene = collide.Scene()
    scene.add(name, source, vertices, triangles, matrix)   # matrix: 4x4, column vectors, the object's own to the stage's
    scene.collision_set()                       # {(first, second)} of objects whose surfaces meet
    scene.intersection_test(first, second, offset=(0, 0, 0))   # whether they meet with the first moved by offset
    scene.distance(first, second)               # how far apart their surfaces are
    scene.touches(name, within)                 # whether any other object comes within that distance
    scene.raycast(origins, directions)          # per ray: (distance, object name) of the first hit, or (inf, None)

A copy's scale is kept in its tree (one tree per model and scale), since FCL's transforms carry only a turn and a move.
"""
import numpy as np
import fcl
import trimesh


def split_matrix(matrix):
    """A 4x4 matrix (column vectors, no shear) as its scale per axis, its turn and its move."""
    matrix = np.asarray(matrix, dtype=np.float64)
    scale = np.linalg.norm(matrix[:3, :3], axis=0)
    turn = matrix[:3, :3] / scale
    if np.linalg.det(turn) < 0:  # a mirrored copy: the mirror goes into the scale
        scale[0], turn[:, 0] = -scale[0], -turn[:, 0]
    return scale, turn, matrix[:3, 3]


def pose_key(placed):
    """An FCL object's pose, rounded, as a key."""
    return tuple(np.round(placed.getTranslation(), 7)) + tuple(np.round(placed.getQuatRotation(), 7))


class Scene:
    """A place's objects for collision queries."""

    def __init__(self):
        self.trees = {}  # (source, scale) -> (fcl.BVHModel, scaled vertices, triangles)
        self.objects = {}  # name -> fcl.CollisionObject
        self.placed = {}  # name -> (tree key, turn, move)
        self.bounds = {}  # name -> (low, high) in the stage's frame
        self.manager = None
        self.ray_mesh = None

    def tree(self, source, vertices, triangles, scale):
        """The tree of one model at one scale, built the first time it is asked for."""
        key = (source, tuple(np.round(scale, 6)))
        if key not in self.trees:
            scaled = np.asarray(vertices, dtype=np.float64) * scale
            model = fcl.BVHModel()
            model.beginModel(len(scaled), len(triangles))
            model.addSubModel(scaled, np.asarray(triangles, dtype=np.int64))
            model.endModel()
            self.trees[key] = (model, scaled, np.asarray(triangles))
        return key

    def add(self, name, source, vertices, triangles, matrix):
        """One object: a copy of the source model's mesh (its own frame) placed by the matrix."""
        scale, turn, move = split_matrix(matrix)
        key = self.tree(source, vertices, triangles, scale)
        placed = fcl.CollisionObject(self.trees[key][0], fcl.Transform(turn, move))
        self.objects[name] = placed
        self.placed[name] = (key, turn, move)
        corners = self.trees[key][1] @ turn.T + move
        self.bounds[name] = (corners.min(axis=0), corners.max(axis=0))
        self.manager = self.ray_mesh = None

    def collision_set(self):
        """Every pair of objects whose surfaces meet, each pair (first, second) in name order: the broad phase from
        FCL's tree of boxes, each candidate pair then tested on the models' own trees."""
        if self.manager is None:
            self.manager = fcl.DynamicAABBTreeCollisionManager()
            self.manager.registerObjects(list(self.objects.values()))
            self.manager.setup()
        # FCL hands the callback its own wrappers of the objects: they are known again by their pose.
        by_pose = {}
        for name, placed in self.objects.items():
            by_pose.setdefault(pose_key(placed), []).append(name)
        found = set()

        def candidate(first, second, _):
            for one in by_pose.get(pose_key(first), []):
                for other in by_pose.get(pose_key(second), []):
                    if one != other and fcl.collide(self.objects[one], self.objects[other], fcl.CollisionRequest(),
                                                    fcl.CollisionResult()):
                        found.add(tuple(sorted((one, other))))
            return False

        self.manager.collide(fcl.CollisionData(), candidate)
        return found

    def intersection_test(self, first, second, offset=(0.0, 0.0, 0.0)):
        """Whether two objects' surfaces meet, the first moved by offset (metres, the stage's frame)."""
        key, turn, move = self.placed[first]
        moved = fcl.CollisionObject(self.trees[key][0], fcl.Transform(turn, move + np.asarray(offset, dtype=float)))
        return fcl.collide(moved, self.objects[second], fcl.CollisionRequest(), fcl.CollisionResult()) > 0

    def distance(self, first, second):
        """The shortest distance between two objects' surfaces (0 when they meet)."""
        return max(0.0, fcl.distance(self.objects[first], self.objects[second], fcl.DistanceRequest(),
                                     fcl.DistanceResult()))

    def touches(self, name, within):
        """Whether an object's surface comes within this distance of any other object's (not one inside it in the
        prim tree: a name under it)."""
        low, high = self.bounds[name]
        for other, (other_low, other_high) in self.bounds.items():
            if other == name or other.startswith(name + "/") or name.startswith(other + "/"):
                continue
            if np.any(other_low > high + within) or np.any(other_high < low - within):
                continue
            if self.distance(name, other) <= within:
                return True
        return False

    def world_mesh(self, name):
        """One object's mesh in the stage's frame."""
        key, turn, move = self.placed[name]
        _, scaled, triangles = self.trees[key]
        return trimesh.Trimesh(scaled @ turn.T + move, triangles, process=False)

    def raycast(self, origins, directions):
        """Each ray's first hit: (distances, object names), inf and None where a ray meets nothing."""
        names = sorted(self.objects)
        if self.ray_mesh is None:
            meshes = [self.world_mesh(name) for name in names]
            owner = np.concatenate([np.full(len(mesh.faces), index) for index, mesh in enumerate(meshes)])
            self.ray_mesh = (trimesh.util.concatenate(meshes), owner)
        mesh, owner = self.ray_mesh
        origins, directions = np.asarray(origins, dtype=float), np.asarray(directions, dtype=float)
        distances = np.full(len(origins), np.inf)
        hit_names = np.full(len(origins), None, dtype=object)
        locations, rays, faces = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(
            origins, directions, multiple_hits=False)
        for location, ray, face in zip(locations, rays, faces):
            distance = float(np.linalg.norm(location - origins[ray]))
            if distance < distances[ray]:
                distances[ray], hit_names[ray] = distance, names[owner[face]]
        return distances, list(hit_names)
