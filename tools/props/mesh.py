"""Turn a reference picture into a game-ready mesh, geometry only.

Nothing here touches nvdiffrast, diffoctreerast or mipgaussian. Those three kernels are
non-commercial, and TRELLIS uses them only for preview renders, gaussian splats and baking a
texture. This look needs none of them: colour comes from the palette, one flat colour per part.
The mesh itself comes off FlexiCubes, which NVIDIA relicensed to Apache 2.0 on 2025-04-03 and
TRELLIS moved onto on 2025-04-29. The check below fails the run if one is ever imported, so the
licence position cannot rot quietly.
"""
import argparse
import json
import os
import pathlib
import sys
import time

# TRELLIS reads its backends from the environment at import, so these come before it loads.
os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("SPARSE_BACKEND", "spconv")
os.environ.setdefault("SPCONV_ALGO", "native")
# DINOv2 reads the picture in float32, and no xformers backend does float32 attention on a
# Blackwell card. This switch is DINOv2's own and sends it to PyTorch's attention instead;
# TRELLIS picks its own backend from ATTN_BACKEND above and is unaffected.
os.environ.setdefault("XFORMERS_DISABLED", "1")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import MESHES, TRELLIS, make_directories, ready  # noqa: E402

sys.path.insert(0, str(TRELLIS))

import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from PIL import Image  # noqa: E402
from trimesh.exchange.gltf import export_glb  # noqa: E402

from finish import carry_colour_across, take_out_ripples, with_crease_normals  # noqa: E402

BANNED = ("nvdiffrast", "diffoctreerast", "diff_gaussian_rasterization")
MODEL = "microsoft/TRELLIS-image-large"
# Z-up to Y-up, the same basis change TRELLIS applies in its own exporter.
TO_Y_UP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float32)


def check_licence():
    """Fail loudly if a non-commercial kernel was pulled in behind our back."""
    loaded = [name for name in BANNED if name in sys.modules]
    if loaded:
        raise SystemExit(
            f"non-commercial kernel loaded: {loaded}. These may not ship in this game; "
            "remove whatever imported it rather than silencing this check."
        )


def load_picture(path):
    """Read the picture, cutting the background away when it is still opaque."""
    image = Image.open(path)
    if image.mode == "RGBA" and np.array(image)[..., 3].min() < 255:
        return image
    import rembg

    return rembg.remove(image.convert("RGB"))


def decimate(vertices, faces, budget):
    """Cut the mesh down to the triangle budget, keeping its shape."""
    if len(faces) <= budget:
        return vertices, faces
    import fast_simplification

    return fast_simplification.simplify(vertices, faces, 1.0 - budget / len(faces))


_PIPELINE = None


def loaded_pipeline():
    """The model, loaded once. A batch of props otherwise spends as long loading as generating."""
    global _PIPELINE
    if _PIPELINE is None:
        from trellis.pipelines import TrellisImageTo3DPipeline

        _PIPELINE = TrellisImageTo3DPipeline.from_pretrained(MODEL)
        _PIPELINE.cuda()
    return _PIPELINE


def build(picture, name, faces_budget, seed, steps, smooth, crease, colour=True):
    make_directories()
    started = time.time()
    pipeline = loaded_pipeline()
    loaded = time.time()

    result = pipeline.run(
        load_picture(picture),
        seed=seed,
        formats=["mesh"],
        sparse_structure_sampler_params={"steps": steps, "cfg_strength": 7.5},
        slat_sampler_params={"steps": steps, "cfg_strength": 3.0},
    )
    generated = time.time()
    check_licence()

    raw = result["mesh"][0]
    vertices = raw.vertices.detach().cpu().numpy().astype(np.float32)
    faces = raw.faces.detach().cpu().numpy().astype(np.int32)
    raw_faces = len(faces)
    # The mesh decoder hands back colour per vertex alongside the normal. This is the whole
    # reason we can keep the generated colour without baking a texture, which is the step that
    # would have needed the non-commercial rasteriser.
    colours = None
    if colour and raw.vertex_attrs is not None:
        colours = raw.vertex_attrs[:, :3].detach().cpu().numpy().astype(np.float32)

    # Smooth while the mesh is still dense: the ripples are small, and there are enough
    # triangles here to lose them without dragging the shape along.
    started_finish = time.time()
    # process=False on purpose: welding would renumber the vertices and break the colour's
    # correspondence with them. What comes out of the decoder is already a shared-vertex mesh.
    dense = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    take_out_ripples(dense, smooth, crease)
    dense_vertices = np.ascontiguousarray(dense.vertices, dtype=np.float32)
    vertices, faces = decimate(
        dense_vertices, np.ascontiguousarray(dense.faces, dtype=np.int32), faces_budget,
    )
    carried = carry_colour_across(dense_vertices, colours, vertices) if colours is not None else None
    low = trimesh.Trimesh(vertices=vertices @ TO_Y_UP, faces=faces, process=False)
    out = with_crease_normals(low, crease, carried)
    finish_seconds = time.time() - started_finish

    path = MESHES / f"{name}.glb"
    path.write_bytes(export_glb(trimesh.Scene(out), include_normals=True))

    import torch

    report = {
        "name": name,
        "picture": str(picture),
        "faces_raw": raw_faces,
        "faces_final": int(len(out.faces)),
        "vertices_final": int(len(out.vertices)),
        "size_kb": round(path.stat().st_size / 1000, 1),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2),
        "load_seconds": round(loaded - started, 1),
        "generate_seconds": round(generated - loaded, 1),
        "finish_seconds": round(finish_seconds, 1),
        "smooth_passes": smooth,
        "crease_degrees": crease,
        "colour": "flat per panel, averaged from the generated colour" if colours is not None else "none",
        # TRELLIS normalises every prop into a unit box, so this is proportion, not size.
        # The real size is written down per prop kind when the engine imports it.
        "extent_unit_box": [round(float(value), 3) for value in out.extents],
    }
    (MESHES / f"{name}-report.json").write_text(json.dumps(report, indent=1))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("picture")
    parser.add_argument("--faces", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--steps", type=int, default=12,
                        help="Sampling steps. Raising this does not fix a bowed prop; the "
                             "reference picture does.")
    parser.add_argument("--smooth", type=int, default=10,
                        help="Smoothing passes over the dense mesh; 0 leaves the ripples in.")
    parser.add_argument("--crease", type=float, default=40.0,
                        help="Folds sharper than this many degrees stay sharp.")
    parser.add_argument("--no-colour", action="store_true",
                        help="Leave the generated colour out; the prop is painted from tokens instead.")
    args = parser.parse_args()

    missing = ready()
    if missing:
        raise SystemExit("the prop tool chain is not built on this box:\n  " + "\n  ".join(missing))
    print(json.dumps(build(args.picture, args.name, args.faces, args.seed, args.steps,
                           args.smooth, args.crease, not args.no_colour), indent=1))


if __name__ == "__main__":
    main()
