"""Runs inside Blender with no scene: a film's frames composed from their layers (../layered.py writes the listing).

    blender -b --python compose.py -- <compose.json>

compose.json: {"look": {view settings, glare}, "pictures": [{"out": <png>, "background": <exr>, "layers": [<exr>, ...],
"names": [<layer>, ...]}, ...]}; beside it, shares.json: {<png>: {<layer>: the share of the picture it covers}}. Each picture in linear light (composite): the background multiplied by every layer's
Shadow Catcher pass, then the layers laid over it far to near at each pixel by their depth, each premultiplied over
what is under it (Blender's Alpha Over); a layer's pixels outside the box it was drawn in (its Combined and Shadow
Catcher both exactly nought) leave what is under them. Then the place's look applied once, as its own render applies
it: the compositor's glare (the listing's look, Blender's compositor on the processor) and the view settings, as PNG.
Nothing is rendered: the compositor reads only images, so Blender draws no scene.
"""
import json
import pathlib
import sys

import numpy as np


def channels(path):
    """{pass.channel: array (top row first)} of a multilayer EXR, its view layer's name dropped."""
    import OpenImageIO
    found = {}
    parts = OpenImageIO.ImageBuf(str(path)).nsubimages
    for part in range(parts):
        held = OpenImageIO.ImageBuf(str(path), part, 0)
        pixels = np.asarray(held.get_pixels(OpenImageIO.FLOAT))
        for index, name in enumerate(held.spec().channelnames):
            found[name.split(".", 1)[1] if name.count(".") > 1 else name] = pixels[:, :, index]
    return found


def rgb(found, name):
    return np.dstack([found[f"{name}.{axis}"] for axis in "RGB"])


def layer_of(found):
    """A layer render's arrays: its premultiplied colour, alpha, shadow catcher (1 outside its box) and depth
    (infinite where it shows nothing)."""
    colour, alpha = rgb(found, "Combined"), found["Combined.A"]
    shadow = rgb(found, "Shadow Catcher")
    outside = (alpha == 0) & (shadow.sum(axis=2) == 0)
    shadow[outside] = 1.0
    depth = np.where(alpha > 0, found["Depth.Z"], np.inf)
    return {"colour": colour, "alpha": alpha, "shadow": shadow, "depth": depth}


def composite(background, layers):
    """The picture (h x w x 3, linear) of a background and its layers (layer_of's): the background under every
    layer's shadow, then the layers far to near at each pixel, each over what is under it."""
    picture = background * np.prod([layer["shadow"] for layer in layers], axis=0) if layers else background.copy()
    if not layers:
        return picture
    colours = np.stack([layer["colour"] for layer in layers])
    alphas = np.stack([layer["alpha"] for layer in layers])
    order = np.argsort(-np.stack([layer["depth"] for layer in layers]), axis=0, kind="stable")
    for rank in range(len(layers)):
        index = order[rank][None]
        colour = np.take_along_axis(colours, index[..., None], axis=0)[0]
        alpha = np.take_along_axis(alphas, index, axis=0)[0]
        picture = colour + picture * (1.0 - alpha[..., None])
    return picture


def looked(scene, look, image):
    """The scene's compositor reading `image` through the look's glare (none without one), its view settings the
    look's."""
    import bpy
    view = scene.view_settings
    scene.display_settings.display_device = look["display"]
    view.view_transform, view.look, view.exposure, view.gamma = (look["view_transform"], look["look"],
                                                                 look["exposure"], look["gamma"])
    tree = bpy.data.node_groups.new("composed", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    source = tree.nodes.new("CompositorNodeImage")
    source.image = image
    output = tree.nodes.new("NodeGroupOutput")
    made = source.outputs[0]
    if look["glare"]:
        glare = tree.nodes.new("CompositorNodeGlare")
        for name, value in look["glare"].items():
            glare.inputs[name].default_value = value
        tree.links.new(made, glare.inputs["Image"])
        made = glare.outputs["Image"]
    tree.links.new(made, output.inputs[0])
    scene.compositing_node_group = tree
    scene.render.use_compositing = True
    scene.render.compositor_device = "CPU"


def main():
    import bpy
    listing = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    tall, wide = channels(listing["pictures"][0]["background"])["Combined.R"].shape
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = wide, tall, 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    image = bpy.data.images.new("composed", wide, tall, float_buffer=True, alpha=True)
    looked(scene, listing["look"], image)
    shares = {}
    for picture in listing["pictures"]:
        layers = [layer_of(channels(path)) for path in picture["layers"]]
        made = composite(rgb(channels(picture["background"]), "Combined"), layers)
        if made.shape[:2] != (tall, wide):
            raise ValueError(f"{picture['background']}: {made.shape[1]}x{made.shape[0]}, the film's {wide}x{tall}")
        shares[picture["out"]] = {name: float((layer["alpha"] > 0.5).mean())
                                  for name, layer in zip(picture["names"], layers)}
        image.pixels.foreach_set(np.dstack([made, np.ones((tall, wide))])[::-1].astype(np.float32).ravel())
        image.update()
        pathlib.Path(picture["out"]).parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = picture["out"]
        bpy.ops.render.render(write_still=True)
    (pathlib.Path(sys.argv[sys.argv.index("--") + 1]).parent / "shares.json").write_text(json.dumps(shares, indent=1))


if __name__ == "__main__":
    main()
