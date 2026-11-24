"""Runs in the model maker's own Python (setup.sh): one TRELLIS.2 model from one cut-out picture, its paint baked.

    <env>/venv/bin/python -I generate.py <env folder> <picture.png (RGBA, its alpha the cut-out)> <out.glb> [faces]

TRELLIS.2's 1024 cascade at seed 42, its texture 2048 and at most 500k faces (the maker's defaults; quality is never
cut): `faces` is the count its size in the place needs (maker.faces_for), the same faces a square metre for every
model, so a 0.3 m sprout is not made at a building's 500k (2026-11-21: 168 crops at 462,710 faces each).
No RMBG-2.0 (the picture's own alpha is the cut-out: an all-opaque picture is refused), no flash-attn and no NVIDIA
nvdiffrast (shim/). One model a process: each flow model is dropped from the card and RAM after its stage (moved to
torch's meta device), which keeps the process under 20 GB. Its card memory is cut to fit beside the Windows desktop
(lean, remesh.py; the same model bit for bit) and held to the card's free memory (capped). Writes <out.glb> and
<out>.json (seconds, card peak).
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
# to_glb's remesh contours the surface lying BAND voxels off TRELLIS.2's own, then moves each vertex PROJECT of the way
# back to it: one voxel off, as at band 1 with no projection (the shape kept: the bench's shape moved 0.3 thousandths
# of the box on the fridge, 0.07 on the locker), while a hole through a thin sheet up to BAND voxels across is closed
# (#191: at band 1 the fridge's 2 mm glass door kept 155 pinholes seen straight on, 4 at band 3).
BAND = 3
PROJECT = 1 - 1 / BAND
# 1024_cascade never uses the 512 texture flow model, so it is not loaded (2.6 GB of RAM).
MODELS = ["sparse_structure_decoder", "sparse_structure_flow_model", "shape_slat_decoder", "shape_slat_flow_model_512",
          "shape_slat_flow_model_1024", "tex_slat_decoder", "tex_slat_flow_model_1024"]
DROPPED = ("sparse_structure_flow_model", "shape_slat_flow_model_512", "shape_slat_flow_model_1024",
           "tex_slat_flow_model_1024")
# FlexGEMM's implicit GEMM for the sparse convs: TRELLIS.2's masked one first sorts each level's neighbour map (4 GB of
# scratch at the 1024 decoders' top level); this one adds the absent neighbours' zeros, the same sums bit for bit.
CONVOLUTION = "implicit_gemm"
MARGIN_GIB = 0.25  # card memory left beside the allocator's cap: the kernels' and libraries' own
ROWS_AT_ONCE = 2**26  # values a chunked norm takes at once (256 MB of float32)


def chunked_layer_norm(self, x):
    """LayerNorm32's forward (float32 inside, the input's type out) a block of rows at a time: each row is normalised
    alone, so the answer is TRELLIS.2's bit for bit, without a float32 copy of the whole input and a float32 answer
    beside it. Under autocast LayerNorm32 casts nothing, and neither does this."""
    import torch
    if torch.is_autocast_enabled():
        return torch.nn.LayerNorm.forward(self, x)
    out = torch.empty_like(x)
    step = max(1, ROWS_AT_ONCE // max(1, x.shape[-1]))
    for start in range(0, x.shape[0], step):
        part = x[start:start + step].type(torch.float32)
        out[start:start + step] = torch.nn.LayerNorm.forward(self, part).type(x.dtype)
    return out


def layer_norm_in_place(input, normalized_shape, weight=None, bias=None, eps=1e-5):
    """F.layer_norm as the decoders' last norm calls it (no weight or bias, on their own float32 copy of the
    features): the rows normalised in place a block at a time, F.layer_norm's answer bit for bit with no second
    float32 tensor of them all; any other call is F.layer_norm's own."""
    import torch
    if weight is not None or bias is not None or input.dim() != 2:
        return torch.nn.functional.layer_norm(input, normalized_shape, weight, bias, eps)
    step = max(1, ROWS_AT_ONCE // max(1, input.shape[-1]))
    for start in range(0, input.shape[0], step):
        input[start:start + step] = torch.nn.functional.layer_norm(input[start:start + step], normalized_shape, eps=eps)
    return input


def lean():
    """TRELLIS.2's card memory cut to what fits this PC's card beside the Windows desktop, its model bit for bit the
    same (#169: a printer box's and a fridge's 1024 decoders and remesh passed the 16 GB card and stopped with 'CUDA
    driver error: device not ready'): the sparse convs on FlexGEMM's implicit GEMM, the norms a block of rows at a
    time, the remesh on remesh.py."""
    import types
    import torch
    import cumesh.remeshing
    from trellis2.modules import norm
    from trellis2.modules.sparse.conv import config
    from trellis2.models.sc_vaes import sparse_unet_vae
    import remesh
    config.FLEX_GEMM_ALGO = CONVOLUTION
    norm.LayerNorm32.forward = chunked_layer_norm
    sparse_unet_vae.F = types.SimpleNamespace(**{**vars(torch.nn.functional), "layer_norm": layer_norm_in_place})
    cumesh.remeshing.remesh_narrow_band_dc = remesh.remesh_narrow_band_dc


def capped(torch):
    """torch's card allocator held to the card's free memory at the start, less MARGIN_GIB: past the card, WSL's
    driver answers 'device not ready' where it should say out of memory, an error the allocator cannot recover from
    (#169); under its cap it gives its cached blocks back and tries again first, and only then says out of memory."""
    free, total = torch.cuda.mem_get_info()
    torch.cuda.set_per_process_memory_fraction(max(0.0, free - MARGIN_GIB * 2**30) / total)


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


def made(pipeline, picture, out, faces=FACES):
    """The model of `picture` written as `out` (GLB); its counts."""
    import torch
    import o_voxel.postprocess  # imported by name: the meshparts image's o_voxel leaves it out of its __init__
    from PIL import Image
    image = Image.open(picture)
    if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] == 255:
        raise SystemExit(f"{picture}: not a cut-out (no transparent background); the maker reads its alpha")
    mesh = pipeline.run(image, seed=SEED, pipeline_type="1024_cascade")[0]
    mesh.simplify(16777216)
    torch.cuda.empty_cache()  # the decoders' cached blocks back to the card: the remesh starts from what is in use
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs, coords=mesh.coords,
        attr_layout=mesh.layout, voxel_size=mesh.voxel_size, aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=faces, texture_size=TEXTURE, remesh=True, remesh_band=BAND, remesh_project=PROJECT, verbose=False)
    glb.export(str(out), extension_webp=False)
    return {"faces": int(len(glb.faces)), "vertices": int(len(glb.vertices))}


def main():
    env, picture, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
    faces = int(sys.argv[4]) if len(sys.argv) > 4 else FACES
    sys.path[:0] = [str(HERE / "shim"), str(env / "src/TRELLIS.2")]
    sys.path.append(str(HERE))  # remesh.py, last so its neighbours shadow nothing (-I leaves the script's folder out)
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    os.environ.setdefault("ATTN_BACKEND", "sdpa")  # the dense attention on torch's own; the sparse one on shim/
    os.environ.setdefault("SPARSE_ATTN_BACKEND", "flash_attn")
    import torch
    began = time.time()
    capped(torch)
    lean()
    pipeline = loaded(env)
    loaded_at = time.time()
    counts = made(pipeline, picture, out, faces)
    stats = {"picture": str(picture), "seed": SEED, "texture": TEXTURE, "faces_target": faces, **counts,
             "load_s": round(loaded_at - began, 1), "make_s": round(time.time() - loaded_at, 1),
             "card_peak_mib": round(torch.cuda.max_memory_reserved() / 2**20),
             "made_with": json.loads((env / "ready.json").read_text())}
    out.with_suffix(".json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
