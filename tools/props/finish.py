"""Take the ripples out of a generated mesh, and tell the renderer where the creases are.

Two separate jobs, easily confused. Smoothing moves vertices: it removes the waviness the
generator leaves on a surface that should be flat or evenly curved. Crease normals move nothing:
they decide, per edge, whether the faces either side are shaded as one surface or as two panels
meeting at a corner. Without them every edge is averaged, which is what turns a crisp door line
soft; with plain smoothing and no pinning the corners get eaten instead.
"""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

# The Taubin pair: a shrinking pass, then a slightly larger expanding one, so the prop keeps
# its size instead of slowly deflating the way plain Laplacian smoothing makes it.
SHRINK = 0.5
EXPAND = -0.53


def neighbour_average(mesh):
    """A matrix that replaces each vertex with the average of the vertices joined to it."""
    edges = mesh.edges_unique
    both = np.vstack([edges, edges[:, ::-1]])
    size = len(mesh.vertices)
    counts = np.bincount(both[:, 0], minlength=size).astype(float)
    counts[counts == 0] = 1.0
    weights = 1.0 / counts[both[:, 0]]
    return coo_matrix((weights, (both[:, 0], both[:, 1])), shape=(size, size)).tocsr()


def edge_vertices(mesh, angle_degrees):
    """The vertices sitting on a fold sharper than the given angle."""
    sharp = mesh.face_adjacency_angles >= np.radians(angle_degrees)
    pinned = np.zeros(len(mesh.vertices), dtype=bool)
    if sharp.any():
        pinned[np.unique(mesh.face_adjacency_edges[sharp])] = True
    return pinned


def take_out_ripples(mesh, passes, angle_degrees):
    """Smooth the surface between the creases, holding the creases still.

    Smoothing everything pulls a corner towards its neighbours and rounds the prop off, so the
    vertices on a sharp fold are pinned and only the surface between them moves.
    """
    if passes <= 0:
        return mesh
    free = ~edge_vertices(mesh, angle_degrees)
    average = neighbour_average(mesh)
    vertices = mesh.vertices.copy()
    for _ in range(passes):
        for factor in (SHRINK, EXPAND):
            step = average @ vertices - vertices
            vertices[free] += factor * step[free]
    mesh.vertices = vertices
    return mesh


def smooth_surfaces(mesh, angle_degrees):
    """Label each face, so faces forming one smooth surface share a label."""
    adjacency = mesh.face_adjacency
    smooth = adjacency[mesh.face_adjacency_angles < np.radians(angle_degrees)]
    if len(smooth) == 0:
        return np.arange(len(mesh.faces))
    size = len(mesh.faces)
    graph = coo_matrix((np.ones(len(smooth)), (smooth[:, 0], smooth[:, 1])), shape=(size, size))
    _, labels = connected_components(graph, directed=False)
    return labels


def with_crease_normals(mesh, angle_degrees):
    """Split the vertices sitting on a crease, so each side gets its own normal."""
    labels = smooth_surfaces(mesh, angle_degrees)
    faces = mesh.faces
    # One output vertex per (original vertex, smooth surface it belongs to).
    keys = np.stack([faces.ravel(), np.repeat(labels, 3)], axis=1)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)

    weighted = mesh.face_normals * mesh.area_faces[:, None]
    normals = np.zeros((len(unique), 3))
    np.add.at(normals, inverse, np.repeat(weighted, 3, axis=0))
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1.0
    normals /= lengths[:, None]

    return trimesh.Trimesh(
        vertices=mesh.vertices[unique[:, 0]],
        faces=inverse.reshape(-1, 3),
        vertex_normals=normals,
        process=False,
    )
