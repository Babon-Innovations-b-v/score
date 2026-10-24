"""Runs inside Blender on a rented card (tools/cloud/blender_cloud.py; ../baked_body.py, the dress's bake): a
dressed body's library surfaces baked into one picture set, the way the library bakes a code-built piece's own
surfaces (tools/props/library/inside/bake.py `Atlas.bake_self`: each slot's recipe, wear and dirt given off as light
into base colour, roughness and metal, the normal map from the shaded recipe).

    blender -b --python bake_body.py -- <job.json>

The job: {"repo": the checkout whose tools/props/library and vendor folders were sent, "mesh": an .npz of the body
at its bind (points and normals in glTF's frame, triangles, slots: each triangle's surface number), "slots": the
surface names by number, "specs", "wear", "dirt", "seed", "density", "out"}. Writes into `out`: uvs.npy (each
triangle's corners' bake coordinates, glTF's convention, v down the picture), base_color.png,
metal_roughness.png (roughness in green, metal in blue) and normal.png.
"""
import json
import pathlib
import sys

import bpy
import numpy as np

JOB = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
sys.path.insert(0, str(pathlib.Path(JOB["repo"]) / "tools/props/library/inside"))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402
import scene_setup  # noqa: E402

BAKE_SAMPLES = 16  # make_chunky's: a bake reads the emitted colour, not a lit picture


def blender_frame(values):
    """glTF's frame (y up, -z forward) onto Blender's (z up), as make_chunky.GLTF_TO_BLENDER lays a take."""
    return np.column_stack([values[:, 0], -values[:, 2], values[:, 1]])


def body_object(stored, count):
    """The body as one mesh, its triangles in the job's order, slot `s<n>` the surface numbered n, shaded smooth
    with the body's own normals (the normal map is baked in their tangent space)."""
    mesh = bpy.data.meshes.new("body")
    mesh.from_pydata(blender_frame(stored["points"]).tolist(), [], stored["triangles"].tolist())
    for number in range(count):
        mesh.materials.append(bpy.data.materials.new(f"s{number}"))
    mesh.polygons.foreach_set("material_index", stored["slots"].astype(np.int32))
    mesh.shade_smooth()
    mesh.normals_split_custom_set_from_vertices(blender_frame(stored["normals"]).tolist())
    mesh.update()
    item = bpy.data.objects.new("body", mesh)
    bpy.context.scene.collection.objects.link(item)
    return item


def corner_uvs(item, triangles):
    """Each triangle's corners' `bake` coordinates (glTF's v, down the picture); refused when Blender's faces are not
    the job's triangles in order."""
    mesh = item.data
    starts = np.zeros(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get("loop_start", starts)
    vertices = np.zeros(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", vertices)
    flat = np.zeros(len(mesh.loops) * 2)
    mesh.uv_layers["bake"].data.foreach_get("uv", flat)
    corners = starts[:, None] + np.arange(3)
    if len(starts) != len(triangles) or not np.array_equal(vertices[corners], triangles):
        raise SystemExit(f"Blender's {len(starts)} faces are not the job's {len(triangles)} triangles in order")
    uvs = flat.reshape(-1, 2)[corners]
    uvs[..., 1] = 1.0 - uvs[..., 1]
    return uvs


def saved(picture, path):
    picture.filepath_raw = str(path)
    picture.file_format = "PNG"
    picture.save()


def main():
    out = pathlib.Path(JOB["out"])
    out.mkdir(parents=True, exist_ok=True)
    scene_setup.empty_scene(256, BAKE_SAMPLES)
    with np.load(JOB["mesh"]) as stored:
        stored = dict(stored)
    specs = {f"s{number}": JOB["specs"][name] for number, name in enumerate(JOB["slots"])}
    item = body_object(stored, len(JOB["slots"]))
    atlas = bake.Atlas("body", [item], JOB["density"], specs, one_piece=True, backs_hidden=False)
    atlas.bake_self(item, specs, JOB["wear"], JOB["dirt"], JOB["seed"])
    atlas.finish()
    np.save(out / "uvs.npy", corner_uvs(item, stored["triangles"]))
    saved(atlas.pictures["base_color"], out / "base_color.png")
    saved(atlas.metal_roughness[0], out / "metal_roughness.png")
    saved(atlas.pictures["normal"], out / "normal.png")
    print("BAKED", json.dumps({"side": atlas.side, "capped_density": atlas.capped,
                               "triangles": len(stored["triangles"])}), flush=True)


main()
