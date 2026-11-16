"""A plain-torch UV-space rasterizer in place of nvdiffrast's rasterize/interpolate (non-commercial licence).

o_voxel.postprocess.to_glb only rasterizes the mesh's UV layout (z=0, w=1) to find, for every texel, its triangle and
barycentric weights; that is a 2D point-in-triangle test, done here per triangle over its pixel bounding box.
Output layout as nvdiffrast's: (u, v, z, triangle id + 1, 0 where empty), p = u*v0 + v*v1 + (1-u-v)*v2.
"""
import torch


class RasterizeCudaContext:
    def __init__(self, *args, **kwargs):
        pass


def _pixels(tris, width, height, block):
    """Every (triangle, pixel) candidate of a block of triangles in their pixel bounding boxes."""
    lo = torch.floor(tris.amin(1) - 0.5).clamp(min=0)
    hi = torch.ceil(tris.amax(1) - 0.5).clamp(max=torch.tensor([width - 1, height - 1], device=tris.device))
    span = (hi - lo + 1).clamp(min=0).long()
    count = span[:, 0] * span[:, 1]
    owner = torch.repeat_interleave(torch.arange(tris.shape[0], device=tris.device), count)
    start = torch.cumsum(count, 0) - count
    local = torch.arange(owner.shape[0], device=tris.device) - start[owner]
    col = lo[owner, 0].long() + local % span[owner, 0]
    row = lo[owner, 1].long() + local // span[owner, 0]
    return owner, col, row


def rasterize(ctx, pos, tri, resolution, **kwargs):
    height, width = resolution
    clip = pos[0]
    xy = (clip[:, :2] / clip[:, 3:4] + 1) * 0.5 * torch.tensor([width, height], device=clip.device, dtype=clip.dtype)
    tri = tri.long()
    out = torch.zeros((1, height, width, 4), device=clip.device, dtype=torch.float32)
    block = 20000
    for first in range(0, tri.shape[0], block):
        faces = tri[first:first + block]
        corners = xy[faces]  # (F, 3, 2) in pixels
        owner, col, row = _pixels(corners, width, height, block)
        point = torch.stack([col.float() + 0.5, row.float() + 0.5], -1)
        a, b, c = corners[owner, 0], corners[owner, 1], corners[owner, 2]
        v0, v1, v2 = b - a, c - a, point - a
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        ok = den.abs() > 1e-12
        den = torch.where(ok, den, torch.ones_like(den))
        w1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        w2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        w0 = 1 - w1 - w2
        inside = ok & (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        owner, row, col, w0, w1 = owner[inside], row[inside], col[inside], w0[inside], w1[inside]
        values = torch.stack([w0, w1, torch.zeros_like(w0), (owner + first + 1).float()], -1)
        out[0, row, col] = values
    return out, None


def interpolate(attr, rast, tri, **kwargs):
    attr = attr[0] if attr.dim() == 3 else attr
    ids = rast[0, ..., 3].long() - 1
    hit = ids >= 0
    corners = attr[tri.long()[ids.clamp(min=0)]]  # (H, W, 3, C)
    u, v = rast[0, ..., 0:1], rast[0, ..., 1:2]
    value = u * corners[..., 0, :] + v * corners[..., 1, :] + (1 - u - v) * corners[..., 2, :]
    value = torch.where(hit[..., None], value, torch.zeros_like(value))
    return value[None], None
