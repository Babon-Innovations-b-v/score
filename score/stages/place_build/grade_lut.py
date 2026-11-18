"""Runs inside Blender: the final render's grade (its view transform and look, through Blender's own OpenColorIO) as a
picture an engine samples, so a game's frame is graded as SCORE's render of it is. A lattice of `size` cubed scene
linear colours, each channel at `middle` * 2 ** (`low` + c * (`high` - `low`)) for c from 0 to 1 (scene_package.GRADE;
c = 0 stands for black), laid as `size` tiles of size x size side by side (red along each tile, blue tile by tile,
green up from the bottom row), saved as a 16-bit PNG through save_render: each pixel the display's sRGB value Blender
shows for that colour.

    blender -b --python grade_lut.py -- <out.png> <view transform> <look> <size> <low> <high> <middle>
                                                                              (scene_package.blender_graded)
"""
import sys

import bpy
import numpy as np


def lattice(size, low, high, middle):
    """The lattice's scene linear colours, (size, size * size, 3), rows bottom first as Blender's pixels are."""
    steps = middle * 2.0 ** (low + np.linspace(0.0, 1.0, size) * (high - low))
    steps[0] = 0.0
    columns = np.arange(size * size)
    red, blue = steps[columns % size], steps[columns // size]
    found = np.empty((size, size * size, 3), dtype=np.float32)
    found[..., 0], found[..., 2] = red[None, :], blue[None, :]
    found[..., 1] = steps[:, None]
    return found


def main():
    out, view, look, size, low, high, middle = sys.argv[sys.argv.index("--") + 1:][:7]
    size = int(size)
    scene = bpy.context.scene
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = view
    scene.view_settings.look = look
    scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "16"
    colours = lattice(size, float(low), float(high), float(middle))
    image = bpy.data.images.new("grade", size * size, size, alpha=True, float_buffer=True)
    pixels = np.ones((size, size * size, 4), dtype=np.float32)
    pixels[..., :3] = colours
    image.pixels.foreach_set(pixels.ravel())
    image.save_render(out, scene=scene)
    print("GRADE", out, view, look, size)


main()
