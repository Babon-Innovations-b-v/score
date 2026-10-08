"""Flatten a mesh's colour into a few tones, the drawn look a prop without its own texture takes.

`import_prop.py` calls this for a mesh imported without `--keep-texture`, a pack model most often:
its painted texture, or whatever colour it carries, is averaged into a handful of flat tones.
"""
import numpy as np
import trimesh


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
