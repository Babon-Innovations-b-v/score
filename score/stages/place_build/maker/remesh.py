"""CuMesh's narrow-band dual contouring remesher (cumesh/remeshing.py at setup.sh's CUMESH, JeffreyXiang/CuMesh, MIT)
with its card memory cut, its answer bit for bit the same (#169): to_glb remeshes a box-like model at 1024 through 40
million band voxels, and the remesher held every step's scratch to its end and built the four edge neighbours of every
voxel's three edges (5.4 GB) to keep the few that cross the surface; with the Windows desktop on the card it passed the
16 GB card. Here each step's scratch goes once read, and only the crossing edges' neighbours are built.
generate.lean_decoders lays it over cumesh.remeshing.remesh_narrow_band_dc, which to_glb calls by that name.
"""
import torch


def tables(device):
    """The remesher's topology tables, cumesh's: each edge's four neighbour voxels (x, y and z edges), and each quad's
    two ways of splitting into triangles, by its crossing sign."""
    return {"edge_neighbours": torch.tensor([
                [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]],
                [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]],
                [[0, 0, 0], [0, 1, 0], [1, 1, 0], [1, 0, 0]]], dtype=torch.int32, device=device),
            "split_1_n": torch.tensor([0, 1, 2, 0, 2, 3], dtype=torch.long, device=device),
            "split_1_p": torch.tensor([0, 2, 1, 0, 3, 2], dtype=torch.long, device=device),
            "split_2_n": torch.tensor([0, 1, 3, 3, 1, 2], dtype=torch.long, device=device),
            "split_2_p": torch.tensor([0, 3, 1, 3, 2, 1], dtype=torch.long, device=device)}


def band_voxels(bvh, center, scale, resolution, eps, device):
    """The voxels at `resolution` whose cell the surface (shifted out by eps) passes near, refined from a coarse grid
    of at most 32 a side: each level's points and distances dropped before the next level's are made."""
    base_resolution = resolution
    while base_resolution > 32:
        assert base_resolution % 2 == 0, "Failed to find a base resolution that is a multiple of 2"
        base_resolution //= 2
    offsets = torch.tensor([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]],
                           dtype=torch.int32, device=device)
    coords = torch.stack(torch.meshgrid(torch.arange(base_resolution, device=device),
                                        torch.arange(base_resolution, device=device),
                                        torch.arange(base_resolution, device=device), indexing="ij"),
                         dim=-1).int().reshape(-1, 3)
    while True:
        cell_size = scale / base_resolution
        points = ((coords.float() + 0.5) / base_resolution - 0.5) * scale + center
        distances = bvh.unsigned_distance(points)[0]
        del points
        distances -= eps
        distances = torch.abs(distances)
        coords = coords[distances < 0.87 * cell_size]
        del distances
        if base_resolution >= resolution:
            return coords
        base_resolution *= 2
        coords *= 2
        coords = (coords.unsqueeze(1) + offsets.unsqueeze(0)).reshape(-1, 3)


def dual_contour(bvh, coords, center, scale, resolution, eps, device):
    """(The voxels' hashmap, each voxel's dual vertex, each voxel's three edges' crossing signs): the band's corner
    vertices' distances read and dropped once the dual contour has them."""
    from cumesh import _C
    from cumesh.remeshing import _init_hashmap
    hashmap_vox = _init_hashmap(resolution, 2 * coords.shape[0], device)
    _C.hashmap_insert_3d_idx_as_val_cuda(*hashmap_vox, torch.cat([torch.zeros_like(coords[:, :1]), coords], dim=1),
                                         resolution, resolution, resolution)
    grid_verts = _C.get_sparse_voxel_grid_active_vertices(*hashmap_vox, coords, resolution, resolution, resolution)
    points = (grid_verts.float() / resolution - 0.5) * scale + center
    distances_vert = bvh.unsigned_distance(points)[0]
    del points
    distances_vert -= eps
    hashmap_vert = _init_hashmap(resolution + 1, 2 * grid_verts.shape[0], device)
    _C.hashmap_insert_3d_idx_as_val_cuda(*hashmap_vert,
                                         torch.cat([torch.zeros_like(grid_verts[:, :1]), grid_verts], dim=1),
                                         resolution + 1, resolution + 1, resolution + 1)
    del grid_verts
    dual_verts, intersected = _C.simple_dual_contour(*hashmap_vert, coords, distances_vert,
                                                     resolution + 1, resolution + 1, resolution + 1)
    return hashmap_vox, dual_verts, intersected


def crossing(table, coords, intersected):
    """(The four voxels round each edge the surface crosses, its crossing sign), built for the crossing edges alone,
    in the order cumesh's mask over every voxel's three edges gives them (voxel by voxel, x, y, z)."""
    voxel, axis = torch.nonzero(intersected, as_tuple=True)
    return coords[voxel].reshape(-1, 1, 3) + table["edge_neighbours"][axis], intersected[voxel, axis]


def quads(table, hashmap_vox, coords, intersected, resolution):
    """(Each quad's four voxels, its crossing sign) for every crossing edge whose four voxels are all in the band."""
    from cumesh import _C
    connected_voxel, signs = crossing(table, coords, intersected)
    count = connected_voxel.shape[0]
    keys = torch.cat([torch.zeros((count * 4, 1), dtype=torch.int, device=coords.device),
                      connected_voxel.reshape(-1, 3)], dim=1)
    del connected_voxel
    indices = _C.hashmap_lookup_3d_cuda(*hashmap_vox, keys, resolution, resolution, resolution).reshape(count, 4).int()
    del keys
    valid = (indices != 0xffffffff).all(dim=1)
    return indices[valid].int(), signs[valid].int()


def split_quads(table, mesh_vertices, quad_indices, intersected_dir):
    """Each quad as the two triangles of its better split (the diagonal whose triangles' normals agree more), as
    cumesh splits it."""
    def alignment(triangles):
        normals0 = torch.cross(mesh_vertices[triangles[:, 1]] - mesh_vertices[triangles[:, 0]],
                               mesh_vertices[triangles[:, 2]] - mesh_vertices[triangles[:, 0]])
        normals1 = torch.cross(mesh_vertices[triangles[:, 2]] - mesh_vertices[triangles[:, 1]],
                               mesh_vertices[triangles[:, 3]] - mesh_vertices[triangles[:, 1]])
        return (normals0 * normals1).sum(dim=1).abs()
    flipped = (intersected_dir == 1).unsqueeze(1)
    first = torch.where(flipped, quad_indices[:, table["split_1_p"]], quad_indices[:, table["split_1_n"]])
    second = torch.where(flipped, quad_indices[:, table["split_2_p"]], quad_indices[:, table["split_2_n"]])
    return torch.where((alignment(first) > alignment(second)).unsqueeze(1), first, second).reshape(-1, 3)


def remesh_narrow_band_dc(vertices, faces, center, scale, resolution, band=1, project_back=0, verbose=False,
                          bvh=None):
    """cumesh.remeshing.remesh_narrow_band_dc's (vertices, faces), from the same steps on less card memory."""
    from cumesh.bvh import cuBVH
    assert vertices.ndim == 2 and vertices.shape[1] == 3 and vertices.dtype == torch.float32
    assert faces.ndim == 2 and faces.shape[1] == 3 and faces.dtype == torch.int32
    assert center.ndim == 1 and center.shape[0] == 3
    device = vertices.device
    table = tables(device)
    if bvh is None:
        bvh = cuBVH(vertices, faces)
    eps = band * scale / resolution
    coords = band_voxels(bvh, center, scale, resolution, eps, device)
    hashmap_vox, dual_verts, intersected = dual_contour(bvh, coords, center, scale, resolution, eps, device)
    quad_indices, intersected_dir = quads(table, hashmap_vox, coords, intersected, resolution)
    del hashmap_vox, intersected
    unique_verts = torch.unique(quad_indices.reshape(-1))
    dual_verts = dual_verts[unique_verts]
    vert_map = torch.zeros((coords.shape[0],), dtype=torch.int32, device=device)
    del coords
    vert_map[unique_verts] = torch.arange(unique_verts.shape[0], dtype=torch.int32, device=device)
    quad_indices = vert_map[quad_indices]
    del vert_map, unique_verts
    mesh_vertices = (dual_verts / resolution - 0.5) * scale + center
    del dual_verts
    mesh_triangles = split_quads(table, mesh_vertices, quad_indices, intersected_dir)
    del quad_indices, intersected_dir
    if project_back > 0:
        _, face_id, uvw = bvh.unsigned_distance(mesh_vertices, return_uvw=True)
        projected_verts = (vertices[faces[face_id.long()]] * uvw.unsqueeze(-1)).sum(dim=1)
        mesh_vertices -= project_back * (mesh_vertices - projected_verts)
    return mesh_vertices, mesh_triangles.int()
