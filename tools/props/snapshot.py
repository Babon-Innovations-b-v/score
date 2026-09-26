"""Draw a mesh to a picture from a few angles, so a made prop can be checked without the engine.

The prop environment has no renderer of its own, and a page in a browser is not something a run
can look at. This projects the triangles, keeps the nearest one per pixel, and shades each by how
squarely it faces the viewer, tinted by its own colour. Crude, but enough to judge a silhouette:
it is the difference between publishing a page and checking the work.

    python tools/props/snapshot.py some.glb other.glb --out sheet.png
"""
import argparse
import pathlib

import numpy as np
import trimesh
from PIL import Image, ImageDraw

# Degrees about the vertical, then how far the view looks down. Front is -z, as in the game.
VIEWS = ((-35.0, 25.0), (55.0, 25.0), (145.0, 25.0), (0.0, 89.0))
BACKGROUND = (232, 220, 192)
SIDE = 320


def one_mesh(path):
    """The file as a single mesh, whatever it holds."""
    return trimesh.load(path, force="mesh", process=False)


def face_colours(mesh):
    """One colour per face, from the vertices when the mesh carries colour, else plain hull."""
    visual = getattr(mesh, "visual", None)
    if visual is not None and getattr(visual, "kind", None) == "vertex":
        colours = np.asarray(visual.vertex_colors)[:, :3].astype(np.float64)
        return colours[mesh.faces].mean(axis=1)
    return np.full((len(mesh.faces), 3), 241.0)


def view_matrix(turn, down):
    """Rotates the world so the viewer looks along -z after turning and tilting."""
    yaw, pitch = np.radians(turn), np.radians(down)
    about_y = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    about_x = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
    return about_x @ about_y


def draw_view(mesh, colours, turn, down, side):
    """One picture of the mesh from one angle, nearest face per pixel."""
    rotated = mesh.vertices @ view_matrix(turn, down).T
    low, high = rotated.min(axis=0), rotated.max(axis=0)
    middle = (low + high) / 2.0
    reach = max(high[0] - low[0], high[1] - low[1]) * 0.55 or 1.0
    scale = side / (2.0 * reach)
    screen = np.empty_like(rotated)
    screen[:, 0] = (rotated[:, 0] - middle[0]) * scale + side / 2.0
    screen[:, 1] = side / 2.0 - (rotated[:, 1] - middle[1]) * scale
    screen[:, 2] = rotated[:, 2]

    normals = mesh.face_normals @ view_matrix(turn, down).T
    light = np.clip(0.35 + 0.65 * np.abs(normals[:, 2]), 0.0, 1.0)
    shaded = np.clip(colours * light[:, None], 0, 255).astype(np.uint8)

    image = Image.new("RGB", (side, side), BACKGROUND)
    pen = ImageDraw.Draw(image)
    # Painter's order: the farthest first, so the nearest face is drawn last and stays on top.
    depth = screen[mesh.faces][:, :, 2].mean(axis=1)
    for face in np.argsort(depth):
        corners = [tuple(point) for point in screen[mesh.faces[face], :2]]
        pen.polygon(corners, fill=tuple(int(value) for value in shaded[face]))
    return image


def sheet(paths, side=SIDE):
    """Every mesh in a row of its own, one column per view, its name and size written over it."""
    rows = []
    for path in paths:
        mesh = one_mesh(path)
        colours = face_colours(mesh)
        row = Image.new("RGB", (side * len(VIEWS), side), BACKGROUND)
        for column, (turn, down) in enumerate(VIEWS):
            row.paste(draw_view(mesh, colours, turn, down, side), (column * side, 0))
        size = " x ".join(f"{value:.2f}" for value in mesh.extents)
        ImageDraw.Draw(row).text((8, 8), f"{pathlib.Path(path).stem}   {size}   {len(mesh.faces)} tris",
                                 fill=(27, 23, 20))
        rows.append(row)
    out = Image.new("RGB", (side * len(VIEWS), side * len(rows)), BACKGROUND)
    for index, row in enumerate(rows):
        out.paste(row, (0, index * side))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meshes", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--side", type=int, default=SIDE)
    arguments = parser.parse_args()
    sheet(arguments.meshes, arguments.side).save(arguments.out)
    print(arguments.out)


if __name__ == "__main__":
    main()
