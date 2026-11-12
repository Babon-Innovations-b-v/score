"""Runs inside Blender on the bake's card, in place of make_chunky.py (paint_fit.py's last step): make_chunky as it
is, with each model's texture layout measured once its UVs are packed and laid again only where it would fail
surfaces-check's "texture layout sound" (../uv_layout.py, #92):

    blender -b --python layout_fit.py -- <make_chunky job>

- texture shared by two faces: smart_project folds a lumpy take's island over itself (env1's 13 such models, every
  shared texel inside one chart, 2026-11-12): the faces on a shared texel are projected again on their own at a
  smaller angle limit, so each layer of a fold becomes islands of its own (`unfolding`, UNFOLD_ANGLES), a round kept
  only when it shares fewer texels (an angle-based unwrap of the folded charts shared fewer but stretched lumps, flat's slippers
  1.5% under a quarter of their density);
- charts too thin for a colour: a small model's picture (128 or 256 px) puts its remeshed triangles' islands under a
  texel (33 models): the picture's side doubled, the islands packed again, until its thin share is under TARGET or the
  side reaches bake.LARGEST (`next_step`).

A model whose layout the check would pass (under LIMIT on both) is baked exactly as make_chunky bakes it: nothing but
the measure runs; so is one no laying again brings under LIMIT (camp's refrigerator at the largest side: unfolding
took its shared texels from 1.2% to 0 and its thin charts from 0.1% to 1.2%), so a bake changes only where it is
fixed. A
split, per-face or capped piece, or a set of several pieces (make_bodied's), is left as made. The measure is the
check's in kind (texel centres on two triangles; chart width 2 * area / perimeter over charts joined by position and
texture coordinate), written here so an edit of the check moves no bake.
"""
import pathlib
import sys

import numpy as np

# The check's limit (uv_layout.LEAST): a layout is laid again only past it, so a layout the check passes is baked as
# made; once laid again it goes on to under TARGET, half of it, well inside the gate.
LIMIT = 0.01
TARGET = 0.005
THIN_TEXELS = 1.0
# A triangle under a ten-thousandth of a texel measures nothing (uv_layout.DEGENERATE_TEXELS).
DEGENERATE_TEXELS = 1e-4
UNFOLD = "unfold"
# Each unfolding round's smart_project angle limit, in degrees: the faces a fold lays on one texel lie 13 to 22% of
# their model's size apart, their normals a median 27 to 35 degrees apart (flat's slippers, stairwell's open door,
# the street's diner, habitat's curtain, 2026-11-12), so the bake's 60 groups them into one island and a smaller
# limit parts them; projected again at 60 they folded the same (slippers' 4.6% shared stayed).
UNFOLD_ANGLES = (30.0, 15.0, 8.0)
UNFOLD_ROUNDS = len(UNFOLD_ANGLES)


def signed_texels(pixels):
    """Each triangle's signed area in texels (corners in texels)."""
    first, second, third = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    return 0.5 * ((second[:, 0] - first[:, 0]) * (third[:, 1] - first[:, 1])
                  - (second[:, 1] - first[:, 1]) * (third[:, 0] - first[:, 0]))


def texels_inside(triangle, side):
    """The flat indices of a `side` square picture's texels whose centres lie strictly inside the triangle (its
    corners in texels, wrapped onto the picture as the bake samples)."""
    triangle = triangle - np.floor(triangle.min(axis=0) / side) * side
    low = np.maximum(np.floor(triangle.min(axis=0) - 0.5).astype(int), 0)
    high = np.minimum(np.ceil(triangle.max(axis=0) - 0.5).astype(int), side - 1)
    columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
    columns, rows = columns.ravel(), rows.ravel()
    frame = np.array([triangle[1] - triangle[0], triangle[2] - triangle[0]]).T
    if len(columns) == 0 or abs(np.linalg.det(frame)) < 1e-12:
        return columns[:0]
    local = np.linalg.solve(frame, (np.stack([columns + 0.5, rows + 0.5], axis=1) - triangle[0]).T).T
    inside = (local[:, 0] > 1e-9) & (local[:, 1] > 1e-9) & (local.sum(axis=1) < 1 - 1e-9)
    return rows[inside] * side + columns[inside]


def charts_of(positions, uvs, triangles):
    """Each triangle's chart: triangles joined by an edge whose two ends share position and texture coordinate."""
    _, corner_ids = np.unique(np.round(np.concatenate([positions, uvs], axis=1), 9), axis=0, return_inverse=True)
    corners = corner_ids.reshape(-1)[triangles]
    edges = np.sort(np.concatenate([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]]), axis=1)
    _, edge_ids, uses = np.unique(edges, axis=0, return_inverse=True, return_counts=True)
    edge_ids = edge_ids.reshape(-1)
    owners = np.tile(np.arange(len(triangles)), 3)
    parent = np.arange(len(triangles))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    first = {}
    for edge, owner in zip(edge_ids.tolist(), owners.tolist()):
        if edge in first:
            parent[root(owner)] = root(first[edge])
        else:
            first[edge] = owner
    charts = np.unique([root(index) for index in range(len(triangles))], return_inverse=True)[1].reshape(-1)
    return charts, edge_ids, owners, uses[edge_ids] == 1


def measured(positions, uvs, triangles, side):
    """A packed layout's measures on a `side` square base colour picture: `thin` and `overlap` as the check keeps them
    (shares of surface area in charts under THIN_TEXELS wide, of covered texels written by two triangles), each
    whether each triangle lies on a shared texel (`shared`)."""
    corners = positions[triangles]
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    pixels = uvs[triangles] * side
    texel_areas = np.abs(signed_texels(pixels))
    charts, edge_ids, owners, border = charts_of(positions, uvs, triangles)
    edge_pixels = np.concatenate([pixels[:, [0, 1]], pixels[:, [1, 2]], pixels[:, [2, 0]]])
    lengths = np.linalg.norm(edge_pixels[:, 1] - edge_pixels[:, 0], axis=1)
    area = np.bincount(charts, weights=texel_areas)
    perimeter = np.bincount(charts[owners[border]], weights=lengths[border], minlength=len(area))
    with np.errstate(divide="ignore", invalid="ignore"):
        width = np.where(perimeter > 0, 2 * area / perimeter, np.inf)[charts]
    counts = np.zeros(side * side, dtype=np.int32)
    covered = [texels_inside(triangle, side) for triangle in pixels]
    for texels in covered:
        np.add.at(counts, texels, 1)
    shared = np.array([bool((counts[texels] > 1).any()) for texels in covered], dtype=bool)
    valid = texel_areas > DEGENERATE_TEXELS
    total = float(areas.sum()) or 1.0
    return {"thin": float(areas[valid & (width < THIN_TEXELS)].sum() / total),
            "overlap": float((counts > 1).sum() / max(int((counts > 0).sum()), 1)),
            "shared": shared}


def failing(found):
    """Whether a layout fails the check's limit on thin charts or shared texels (only then is it laid again)."""
    return found["thin"] > LIMIT or found["overlap"] > LIMIT


def next_step(found, side, largest, rounds):
    """What a layout measured at `side` needs next: UNFOLD while its folds share texels over TARGET, past LIMIT before
    the first round, and fewer than UNFOLD_ROUNDS were laid (`rounds`, None once a round shared no fewer), else twice
    the side while its thin share is over TARGET and the side may grow, else None (kept)."""
    if found["overlap"] > (TARGET if rounds else LIMIT) and rounds is not None and rounds < UNFOLD_ROUNDS:
        return UNFOLD
    if found["thin"] > TARGET and side * 2 <= largest:
        return side * 2
    return None


def folded_faces(found, polygons):
    """The polygon indices of the triangles on a shared texel (`polygons`: each triangle's polygon)."""
    return np.unique(polygons[found["shared"]])


def mesh_layout(item):
    """The item's triangles as the bake lays them: each corner's world position and `bake` texture coordinate, the
    corners of each triangle, and each triangle's polygon."""
    mesh = item.data
    mesh.calc_loop_triangles()
    triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get("loops", triangles)
    polygons = np.empty(len(mesh.loop_triangles), dtype=np.int64)
    mesh.loop_triangles.foreach_get("polygon_index", polygons)
    vertex_of = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", vertex_of)
    points = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", points)
    points = points.reshape(-1, 3) @ np.asarray(item.matrix_world)[:3, :3].T
    uvs = np.empty(len(mesh.loops) * 2)
    mesh.uv_layers["bake"].data.foreach_get("uv", uvs)
    return points[vertex_of], uvs.reshape(-1, 2), triangles.reshape(-1, 3), polygons


def unfolding(smart, rounds):
    """An unwrap: bake.unwrap's (`smart`), then each round's faces (`rounds`, polygon indices) projected again on their
    own by smart_project at that round's UNFOLD_ANGLES limit, so they leave the islands they folded over."""
    import math
    import bpy

    def unwrap(item):
        smart(item)
        for faces, angle in zip(rounds, UNFOLD_ANGLES):
            chosen = np.zeros(len(item.data.polygons), dtype=bool)
            chosen[faces] = True
            item.data.polygons.foreach_set("select", chosen)
            item.data.update()
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.002, area_weight=1.0,
                                     scale_to_bounds=False)
            bpy.ops.object.mode_set(mode="OBJECT")
    return unwrap


def fitted_atlas(bake):
    """bake.Atlas whose single piece's layout is measured once packed and laid again by next_step."""
    import bpy

    class Fitted(bake.Atlas):
        def __init__(self, name, items, density, specs=None, one_piece=False, backs_hidden=True, per_face=False,
                     split=False):
            arguments = (specs, one_piece, backs_hidden, per_face, split)
            super().__init__(name, items, density, *arguments)
            if per_face or self.maps > 1 or self.capped or len(items) != 1:
                return
            smart, found, rounds, stopped = bake.unwrap, self.measure(items[0]), [], False
            if not failing(found):
                return
            made = density
            first = (self.side, found["thin"], found["overlap"])
            step = next_step(found, self.colour_side, bake.LARGEST // 2, len(rounds))
            while step is not None:
                kept = (density, list(rounds), found)
                if step == UNFOLD:
                    rounds.append(folded_faces(found, mesh_layout(items[0])[3]))
                else:
                    density = density * (2 * step * 0.999) / self.wanted(items, density, specs, backs_hidden)
                self.laid_again(name, items, density, arguments, unfolding(smart, rounds) if rounds else smart)
                found = self.measure(items[0])
                if step == UNFOLD and found["overlap"] >= kept[2]["overlap"]:
                    density, rounds, found, stopped = (*kept, True)
                    self.laid_again(name, items, density, arguments, unfolding(smart, rounds) if rounds else smart)
                step = next_step(found, self.colour_side, bake.LARGEST // 2, None if stopped else len(rounds))
            if failing(found):  # still past the limit: kept as made, so its bake moves only where it is fixed
                print(f"UNFITTED {name}: thin {first[1]:.4f}, shared {first[2]:.4f} as made; best laid again: side "
                      f"{self.side}, thin {found['thin']:.4f}, shared {found['overlap']:.4f}", flush=True)
                self.laid_again(name, items, made, arguments, smart)
            elif (self.side, found["thin"], found["overlap"]) != first:
                print(f"FITTED {name}: side {first[0]} -> {self.side}, thin {first[1]:.4f} -> {found['thin']:.4f}, "
                      f"shared {first[2]:.4f} -> {found['overlap']:.4f} after {len(rounds)} unfolding rounds",
                      flush=True)

        @property
        def colour_side(self):
            return self.sets[0]["base_color"].size[0]

        def measure(self, item):
            """The layout's measures; a piece of one surface (one material slot: the cut-down copy keeps its full
            model's slots, its remesh not their faces) has no thin-chart fault (uv_layout.ONE_SURFACE: its thin
            chart's neighbours bake its own finish), so its thin share counts as none."""
            positions, uvs, triangles, _ = mesh_layout(item)
            found = measured(positions, uvs, triangles, self.colour_side)
            return dict(found, thin=0.0) if len(item.data.materials) == 1 else found

        def wanted(self, items, density, specs, backs_hidden):
            """The normal map's side the Atlas works out at `density`, before rounding (bake.Atlas's own rule)."""
            area = bake.visible_area(items, bake.sharp_slots(specs, density), backs_hidden)
            return (area / bake.UV_FILL) ** 0.5 * density

        def laid_again(self, name, items, density, arguments, unwrap):
            """The pictures made so far removed and the layout made again at `density` with `unwrap`."""
            for pictures in self.sets:
                for picture in pictures.values():
                    bpy.data.images.remove(picture)
            made = bake.unwrap
            bake.unwrap = unwrap
            try:
                super().__init__(name, items, density, *arguments)
            finally:
                bake.unwrap = made
    return Fitted


def main():
    """make_chunky run with bake.Atlas fitted."""
    import runpy
    library = pathlib.Path(__file__).resolve().parents[4] / "tools/props/library/inside"
    sys.path.insert(0, str(library))
    import runtime
    runtime.ready()
    import bake
    bake.Atlas = fitted_atlas(bake)
    runpy.run_path(str(library / "make_chunky.py"), run_name="__main__")


if __name__ == "__main__":
    main()
