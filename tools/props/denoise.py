"""Iron the noise out of a made mesh while keeping its real edges.

A generated mesh has a fine wobble on every surface: walls ripple, tubes wander, flat panels are
not flat. Plain smoothing rounds the edges off along with the wobble. This filters the direction
each face points instead: a face is averaged only with neighbours that are close and already point
nearly the same way, so noise on a panel is averaged out but the fold between two panels is not.
Then the corners are moved until the faces take up their filtered directions.
"""
import numpy as np
from scipy.sparse import coo_matrix


def face_neighbours(mesh):
    """Every pair of faces sharing a corner, both ways round."""
    corners = mesh.faces.reshape(-1)
    owner = np.repeat(np.arange(len(mesh.faces)), 3)
    touching = coo_matrix((np.ones(len(corners)), (owner, corners)),
                          shape=(len(mesh.faces), len(mesh.vertices))).tocsr()
    shared = (touching @ touching.T).tocoo()
    keep = shared.row != shared.col
    return shared.row[keep], shared.col[keep]


def filtered_normals(mesh, rounds, spread, sameness):
    """Each face's direction, averaged with near neighbours that point almost the same way."""
    first, second = face_neighbours(mesh)
    normals = mesh.face_normals.copy()
    centres = mesh.triangles_center
    area = mesh.area_faces
    distance = np.linalg.norm(centres[first] - centres[second], axis=1)
    near = area[second] * np.exp(-(distance ** 2) / (2 * spread ** 2))
    for _ in range(rounds):
        turn = np.linalg.norm(normals[first] - normals[second], axis=1)
        weight = near * np.exp(-(turn ** 2) / (2 * sameness ** 2))
        summed = normals * area[:, None]
        np.add.at(summed, first, normals[second] * weight[:, None])
        normals = summed / np.linalg.norm(summed, axis=1, keepdims=True)
    return normals


def follow(mesh, normals, rounds):
    """Move each corner so the faces round it lie on the planes their filtered directions give."""
    vertices = mesh.vertices.copy()
    faces = mesh.faces
    counts = np.bincount(faces.reshape(-1), minlength=len(vertices)).astype(float)[:, None]
    for _ in range(rounds):
        centres = vertices[faces].mean(axis=1)
        step = np.zeros_like(vertices)
        for corner in range(3):
            offset = centres - vertices[faces[:, corner]]
            np.add.at(step, faces[:, corner], normals * (normals * offset).sum(1, keepdims=True))
        vertices += step / np.maximum(counts, 1)
    mesh.vertices = vertices
    return mesh


def denoise(mesh, strength=1.2, sameness=0.35):
    """Filter the directions, then let the surface follow them. Strength scales the reach; past
    about 2 a round leg starts to go flat."""
    edge = mesh.edges_unique_length.mean()
    normals = filtered_normals(mesh, rounds=int(12 * strength) + 4, spread=2.5 * edge * strength,
                               sameness=sameness)
    return follow(mesh, normals, rounds=int(20 * strength) + 5)
