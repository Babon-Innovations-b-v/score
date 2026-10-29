"""The bones-inside-skin test: a point is inside SOMA's posed skin when its generalised winding number is at least
0.5, by warp's BVH winding query on the CPU (Newton's Python carries warp)."""
import numpy as np
import warp as wp

wp.config.quiet = True
wp.init()


@wp.kernel
def _signs(mesh: wp.uint64, points: wp.array(dtype=wp.vec3), out: wp.array(dtype=float)):
    index = wp.tid()
    query = wp.mesh_query_point_sign_winding_number(mesh, points[index], 1.0e6, 2.0, 0.5)
    out[index] = query.sign


def inside(points, verts, faces):
    """Each point's winding-number inside test against the closed mesh (verts, faces): True inside."""
    mesh = wp.Mesh(points=wp.array(np.asarray(verts, dtype=np.float32), dtype=wp.vec3, device="cpu"),
                   indices=wp.array(np.asarray(faces, dtype=np.int32).ravel(), dtype=int, device="cpu"))
    out = wp.zeros(len(points), dtype=float, device="cpu")
    wp.launch(_signs, dim=len(points), inputs=[mesh.id, wp.array(np.asarray(points, dtype=np.float32),
                                                                     dtype=wp.vec3, device="cpu"), out], device="cpu")
    return out.numpy() < 0
