"""Runs inside Blender (on a rented machine, cloud/library_bake.py): a library surface baked as a repeating tile, for a
place's room shell (the scene record's code-built walls, decks and roofs, drawn by tools/usd/scene.py), so the shell
is drawn with its library surface (colour, relief, roughness and metal from its recipe) instead of a flat colour.

The job: {"script": "make_tiles.py", "out": folder, "density": px a metre (the normal map's), "metres": the tile's
side, "wear", "dirt", "seed", "specs": {library variant: resolved entry}, "tiles": [library variant, ...]}.

Each surface's recipe is baked flat onto a square `metres` a side (its channels given off as light, its relief as the
normal map, as bake.Atlas bakes a piece), then made to repeat without a seam (`seamless`: the tile blended with itself
shifted by half its side, the shifted copy at the edges, the tile itself in the middle). A flat face has no edge, so
the tile carries no edge wear; it carries the recipe's relief, grain and dirt. Writes <out>/<variant>_base_color.png,
_metal_roughness.png and _normal.png (colour and metal-roughness at half the normal map's side, as bake.Atlas) and
<out>/tiles.json ({variant: {"metres", "side"}}).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
import recipes  # noqa: E402
import scene_setup  # noqa: E402

BAKE_SAMPLES = 16
# Where the skirt round a tile lies on the picture: one point off it, so it bakes nothing.
SKIRT_UV = (5.0, 5.0)


def flat_square(metres, variant):
    """A flat square (facing up) `metres` a side whose `bake` UV map exactly fills 0 to 1, in `variant`, in the middle of
    a skirt of eight more squares whose UVs all lie on one point off the picture: the recipe's bevel test sees the
    surface run on past the tile's sides, so no edge wear is drawn round it, and the skirt bakes nothing."""
    import bmesh
    mesh = bmesh.new()
    steps = [metres * (step - 1.5) for step in range(4)]
    corners = [[mesh.verts.new((across, along, 0.0)) for across in steps] for along in steps]
    layer = mesh.loops.layers.uv.new("bake")
    for row in range(3):
        for column in range(3):
            face = mesh.faces.new((corners[row][column], corners[row][column + 1], corners[row + 1][column + 1],
                                   corners[row + 1][column]))
            for loop in face.loops:
                place = loop.vert.co
                inside = (row, column) == (1, 1)
                loop[layer].uv = ((place.x / metres + 0.5, place.y / metres + 0.5) if inside else SKIRT_UV)
    data = bpy.data.meshes.new(f"tile_{variant}")
    mesh.to_mesh(data)
    mesh.free()
    square = bpy.data.objects.new(f"tile_{variant}", data)
    bpy.context.scene.collection.objects.link(square)
    data.uv_layers.active = data.uv_layers["bake"]
    data.materials.append(bpy.data.materials.new(variant))
    return square


def seamless(pixels):
    """A picture (rows x columns x channels, floats) that repeats without a seam: blended with itself shifted by half
    its side, the shifted copy (whose edges meet) at the edges and the picture itself in the middle."""
    side = pixels.shape[0]
    shifted = np.roll(pixels, (side // 2, side // 2), axis=(0, 1))
    ramp = 1.0 - np.abs(np.linspace(-1.0, 1.0, side))
    weight = np.clip(np.minimum.outer(ramp, ramp) * 2.0, 0.0, 1.0)[..., None]
    return pixels * weight + shifted * (1.0 - weight)


def renormalised(pixels):
    """A tangent normal map's texels (0 to 1) made unit length again after blending."""
    vectors = pixels[..., :3] * 2.0 - 1.0
    vectors /= np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-6)
    found = pixels.copy()
    found[..., :3] = vectors * 0.5 + 0.5
    return found


def picture_pixels(picture):
    side = picture.size[0]
    return np.array(picture.pixels[:], dtype=np.float32).reshape(side, side, 4)


def saved(pixels, name, out, colour_data):
    """`pixels` written as <out>/<name>.png."""
    picture = bake.new_picture(name, pixels.shape[0], colour_data)
    picture.pixels.foreach_set(pixels.astype(np.float32).ravel())
    picture.filepath_raw = str(out / f"{name}.png")
    picture.file_format = "PNG"
    picture.save()


def baked_channels(square, found, side):
    """The square's recipe baked: {channel: pixels} for base colour, roughness and metal (at half `side`) and the
    normal map (at `side`)."""
    half = max(bake.SMALLEST // 2, side // 2)
    pictures = {channel: bake.new_picture(f"{square.name}_{channel}", half, colour)
                for channel, colour in bake.CHANNELS}
    pictures["normal"] = bake.new_picture(f"{square.name}_normal", side, False)
    bake.select_for_bake([square], square)
    for channel, _ in bake.CHANNELS:
        square.data.materials[0] = bake.with_target(bake.channel_materials([found], channel)[0], pictures[channel])
        bpy.ops.object.bake(type="EMIT", margin=0, use_clear=True)
    square.data.materials[0] = bake.with_target(bake.shaded_materials([found])[0], pictures["normal"])
    bpy.ops.object.bake(type="NORMAL", margin=0, use_clear=True, normal_space="TANGENT")
    return {channel: picture_pixels(picture) for channel, picture in pictures.items()}


def metal_roughness(channels):
    """glTF's metal-roughness texels: roughness in green, metal in blue."""
    both = np.ones_like(channels["roughness"])
    both[..., 1] = channels["roughness"][..., 0]
    both[..., 2] = channels["metallic"][..., 0]
    return both


def make_tile(variant, job, out):
    """One surface's tile, its three pictures written; its side."""
    side = int(2 ** np.ceil(np.log2(max(bake.SMALLEST, job["metres"] * job["density"]))))
    square = flat_square(job["metres"], variant)
    found = recipes.channels(job["specs"][variant], job["wear"], job["dirt"], job["seed"])
    channels = baked_channels(square, found, side)
    saved(seamless(channels["base_color"]), f"{variant}_base_color", out, True)
    saved(seamless(metal_roughness(channels)), f"{variant}_metal_roughness", out, False)
    saved(renormalised(seamless(channels["normal"])), f"{variant}_normal", out, False)
    bpy.data.objects.remove(square)
    return side


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    scene_setup.empty_scene(256, BAKE_SAMPLES)
    report = {variant: {"metres": job["metres"], "side": make_tile(variant, job, out)} for variant in job["tiles"]}
    (out / "tiles.json").write_text(json.dumps(report, indent=1))


main()
