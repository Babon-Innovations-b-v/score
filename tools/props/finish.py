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


def averaged_to_flats(colours, steps):
    """The generated colour, averaged into a handful of flat tones: the drawn effect.

    The model returns colour that varies across a surface the way a photograph does. Sorting
    those into a few groups and giving every vertex its group's colour keeps what the object
    actually is, a rust-brown tank or a blue-green dome, and drops the speckle that reads as a
    photograph rather than a drawing. Averaging per panel instead would be wrong: a dome is one
    panel, and its glass and its frame would merge into a single grey.
    """
    from scipy.cluster.vq import kmeans2

    usable = min(steps, len(np.unique(colours, axis=0)))
    if usable < 2:
        return np.repeat(colours.mean(axis=0)[None, :], len(colours), axis=0)
    centres, labels = kmeans2(colours.astype(np.float64), usable, minit="++", seed=1)
    # An empty group comes back as a nan centre; fall back to the colour already there.
    centres = np.where(np.isfinite(centres), centres, colours.mean(axis=0))
    return centres[labels]


def with_crease_normals(mesh, angle_degrees, colours=None, steps=6):
    """Split the vertices sitting on a crease, so each side gets its own normal.

    With `colours` (one row per input vertex) the output also carries those colours averaged
    into `steps` flat tones, which is how the generated colour becomes a drawn one.
    """
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

    vertex_colours = None
    if colours is not None:
        flat = averaged_to_flats(colours[unique[:, 0]], steps)
        vertex_colours = np.clip(flat * 255.0, 0, 255).astype(np.uint8)

    return trimesh.Trimesh(
        vertices=mesh.vertices[unique[:, 0]],
        faces=inverse.reshape(-1, 3),
        vertex_normals=normals,
        vertex_colors=vertex_colours,
        process=False,
    )


def colour_per_vertex(mesh):
    """One colour per vertex, whatever the mesh arrived carrying.

    A generated prop already has colour per vertex. A pack model has a texture and the coordinates
    that map the mesh onto it, so the colour is read out of the picture at each vertex. A model with
    neither, just one flat material colour, gives that colour everywhere. Returns None when there is
    no colour to be had, and the caller leaves the mesh alone.
    """
    visual = getattr(mesh, "visual", None)
    if visual is None:
        return None

    kind = getattr(visual, "kind", None)
    if kind == "vertex" and getattr(visual, "vertex_colors", None) is not None:
        return np.asarray(visual.vertex_colors)[:, :3].astype(np.float64) / 255.0

    if kind == "face" and getattr(visual, "face_colors", None) is not None:
        # Spread each face's colour onto its own vertices.
        colours = np.zeros((len(mesh.vertices), 3))
        counts = np.zeros(len(mesh.vertices))
        face_colours = np.asarray(visual.face_colors)[:, :3].astype(np.float64) / 255.0
        np.add.at(colours, mesh.faces.ravel(), np.repeat(face_colours, 3, axis=0))
        np.add.at(counts, mesh.faces.ravel(), 1.0)
        counts[counts == 0] = 1.0
        return colours / counts[:, None]

    # A texture: trimesh reads the picture at each vertex's coordinates for us.
    try:
        converted = visual.to_color()
    except Exception:
        return None
    if getattr(converted, "vertex_colors", None) is None:
        return None
    sampled = np.asarray(converted.vertex_colors)
    if len(sampled) != len(mesh.vertices):
        return None
    return sampled[:, :3].astype(np.float64) / 255.0


def flatten_to_the_look(mesh, steps=6):
    """Give any mesh the drawn look: a few flat tones instead of a photograph or a texture.

    This is what lets a bought prop and a generated one stand in the same room. A pack model's
    painted texture and a generated prop's surface colour are both reduced the same way, so the
    two arrive looking like one game rather than two. The outline is not done here; that is a
    material in the engine.
    """
    colours = colour_per_vertex(mesh)
    if colours is None:
        return mesh
    flat = np.clip(averaged_to_flats(colours, steps) * 255.0, 0, 255).astype(np.uint8)
    mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=flat)
    return mesh


def carry_colour_across(dense_vertices, dense_colours, new_vertices):
    """Move colour from the dense mesh onto the decimated one, by nearest point.

    Decimation drops everything but positions, so the colour is looked up again afterwards.
    """
    from scipy.spatial import cKDTree

    _, nearest = cKDTree(dense_vertices).query(new_vertices, k=1)
    return dense_colours[nearest]
