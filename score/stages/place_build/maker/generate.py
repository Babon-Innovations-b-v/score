"""Runs in the model maker's own Python (setup.sh): one TRELLIS.2 model from one cut-out picture, its paint baked.

    <env>/venv/bin/python -I generate.py <env folder> <picture.png (RGBA, its alpha the cut-out)> <out.glb>

TRELLIS.2's 1024 cascade at seed 42, its texture 2048 and 500k faces (the maker's defaults; quality is never cut).
No RMBG-2.0 (the picture's own alpha is the cut-out: an all-opaque picture is refused), no flash-attn and no NVIDIA
nvdiffrast (shim/). One model a process: each flow model is dropped from the card and RAM after its stage (moved to
torch's meta device), which keeps the process under 20 GB. Writes <out.glb> and <out>.json (seconds, card peak).
"""
import json
import os
import pathlib
import sys
import time
import types

HERE = pathlib.Path(__file__).resolve().parent
SEED = 42
TEXTURE = 2048
FACES = 500000
# 1024_cascade never uses the 512 texture flow model, so it is not loaded (2.6 GB of RAM).
MODELS = ["sparse_structure_decoder", "sparse_structure_flow_model", "shape_slat_decoder", "shape_slat_flow_model_512",
          "shape_slat_flow_model_1024", "tex_slat_decoder", "tex_slat_flow_model_1024"]
DROPPED = ("sparse_structure_flow_model", "shape_slat_flow_model_512", "shape_slat_flow_model_1024",
           "tex_slat_flow_model_1024")


def local_pipeline(weights):
    """TRELLIS.2-4B's pipeline.json with its models read from this PC's weights folder (the structure decoder from
    TRELLIS-image-large, DINOv3 from its own folder), written beside the weights as pipeline_here.json."""
    config = json.loads((weights / "TRELLIS.2-4B/pipeline.json").read_text())
    models = config["args"]["models"]
    models["sparse_structure_decoder"] = str(weights / "TRELLIS-image-large/ckpts/ss_dec_conv3d_16l8_fp16")
    config["args"]["image_cond_model"]["args"]["model_name"] = str(weights / "dinov3")
    path = weights / "TRELLIS.2-4B/pipeline_here.json"
    path.write_text(json.dumps(config, indent=1))
    return path.name


def loaded(env):
    """The pipeline on the card, its flow models set to drop themselves after their stage."""
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    import trellis2.pipelines.rembg as rembg_module
    rembg_module.BiRefNet = lambda **kwargs: None  # never loaded: the picture's alpha is the cut-out
    weights = env / "weights"
    Trellis2ImageTo3DPipeline.model_names_to_load = MODELS
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained(str(weights / "TRELLIS.2-4B"), local_pipeline(weights))
    pipeline.cuda()
    for key in DROPPED:
        model = pipeline.models[key]
        model.cpu = types.MethodType(lambda self: self.to("meta"), model)
    return pipeline


def made(pipeline, picture, out):
    """The model of `picture` written as `out` (GLB); its counts."""
    import o_voxel.postprocess  # imported by name: the meshparts image's o_voxel leaves it out of its __init__
    from PIL import Image
    image = Image.open(picture)
    if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] == 255:
        raise SystemExit(f"{picture}: not a cut-out (no transparent background); the maker reads its alpha")
    mesh = pipeline.run(image, seed=SEED, pipeline_type="1024_cascade")[0]
    mesh.simplify(16777216)
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs, coords=mesh.coords,
        attr_layout=mesh.layout, voxel_size=mesh.voxel_size, aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=FACES, texture_size=TEXTURE, remesh=True, remesh_band=1, remesh_project=0, verbose=False)
    glb.export(str(out), extension_webp=False)
    return {"faces": int(len(glb.faces)), "vertices": int(len(glb.vertices))}


def main():
    env, picture, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
    sys.path[:0] = [str(HERE / "shim"), str(env / "src/TRELLIS.2")]
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault("ATTN_BACKEND", "sdpa")  # the dense attention on torch's own; the sparse one on shim/
    os.environ.setdefault("SPARSE_ATTN_BACKEND", "flash_attn")
    import torch
    began = time.time()
    pipeline = loaded(env)
    loaded_at = time.time()
    counts = made(pipeline, picture, out)
    stats = {"picture": str(picture), "seed": SEED, "texture": TEXTURE, "faces_target": FACES, **counts,
             "load_s": round(loaded_at - began, 1), "make_s": round(time.time() - loaded_at, 1),
             "card_peak_mib": round(torch.cuda.max_memory_reserved() / 2**20),
             "made_with": json.loads((env / "ready.json").read_text())}
    out.with_suffix(".json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
