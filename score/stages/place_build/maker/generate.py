"""Runs in the model maker's own Python (setup.sh): one TRELLIS.2 model from one cut-out picture, its paint baked.

    <env>/venv/bin/python -I generate.py <env folder> <picture.png (RGBA, its alpha the cut-out)> <out.glb> [faces]

TRELLIS.2's 1024 cascade at seed 42, its texture 2048 and at most 500k faces (the maker's defaults; quality is never
cut): `faces` is the count its size in the place needs (maker.faces_for), the same faces a square metre for every
model, so a 0.3 m sprout is not made at a building's 500k (2026-11-21: 168 crops at 462,710 faces each).
No RMBG-2.0 (the picture's own alpha is the cut-out: an all-opaque picture is refused), no flash-attn and no NVIDIA
nvdiffrast (shim/). One model a process: each flow model is dropped from the card and RAM after its stage (moved to
torch's meta device), which keeps the process under 20 GB. Its card memory is cut to fit beside the Windows desktop
(lean, remesh.py; the same model bit for bit) and held to the card's free memory (capped). Writes <out.glb> and
<out>.json (seconds, card peak), and beside them the decoded mesh before the remesh (`decoded_path`, #159): it keeps
the drawer seams, door lines and vents the remesh closes, which the look and the bake shade from (bake.seamed).
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
# to_glb's remesh contours the surface lying `band` voxels off TRELLIS.2's own (band_for), then moves each vertex
# `project` of the way back to it, so it lies one voxel off at either band (the shape kept). Contoured BAND voxels off,
# every gap or hole up to twice BAND voxels across is closed: a thin sheet's pinholes (#191: the fridge's 2 mm glass
# door kept 155 pinholes seen straight on at band 1, 4 at band 3), but also every groove, slot and hole the model
# holds (#159 r15: hand drill b01's gear teeth, the tool cart's pegboard holes and the locker's vents; the surface
# TRELLIS.2 decoded lay 5.5 voxels from the band 3 remesh at its 99th percentile on the drill, 4.9 on the cart, against
# 1.2 and 3.0 at band 1). So BAND is laid only on a model TRELLIS.2 decoded as see-through (glass: its pinholes are
# where its alpha drops), every other at band 1 with no projection.
BAND = 3
PROJECT = 1 - 1 / BAND
CLEAR = 0.5  # a voxel whose decoded alpha is under this is see-through
SEE_THROUGH = 0.01  # the share of its voxels see-through that makes a model glass-holding (laid at BAND)
# The decoded mesh before the remesh (#159, r11): TRELLIS.2's own surface holds every drawer seam and panel line a voxel
# or less wide, which the remesh closes with #191's pinholes, so it is kept beside the model as the shape its seams are
# shaded from (bake.seamed), never shown. Cut to FACES whatever the model's own faces (a 20k-face toaster still shades
# from the seams 500k faces hold). Only its shape is kept, so it is cleaned and cut as to_glb's no-remesh branch does
# and written with no UV unwrap and no texture bake (decoded_shape): to_glb's xatlas unwrap of 500k raw faces ran on
# the processor while the make held the card, 1 min 54 s of a 3 min 21 s generate (2026-11-26, tower top mast).
# 1024_cascade never uses the 512 texture flow model, so it is not loaded (2.6 GB of RAM). The DROPPED flow models are
# each read from its checkpoint when its stage first asks for it (OnUse) and dropped after it, so a make holds about one
# in RAM, not all four (#159, 2026-11-25: 15.7 GB at the most with all read at once, 11.0 GB read on use, the toaster's
# make 95.5 s against 92.7). Two makes side by side were slower, not faster (the four: 2 to 3 times each one's time
# alone, each held at its memory cap), so a make has the card to itself.
MODELS = ["sparse_structure_decoder", "sparse_structure_flow_model", "shape_slat_decoder", "shape_slat_flow_model_512",
          "shape_slat_flow_model_1024", "tex_slat_decoder", "tex_slat_flow_model_1024"]
DROPPED = ("sparse_structure_flow_model", "shape_slat_flow_model_512", "shape_slat_flow_model_1024",
           "tex_slat_flow_model_1024")
# FlexGEMM's implicit GEMM for the sparse convs: TRELLIS.2's masked one first sorts each level's neighbour map (4 GB of
# scratch at the 1024 decoders' top level); this one adds the absent neighbours' zeros, the same sums bit for bit.
CONVOLUTION = "implicit_gemm"
MARGIN_GIB = 0.25  # card memory left beside the allocator's cap: the kernels' and libraries' own
ROWS_AT_ONCE = 2**26  # values a chunked norm takes at once (256 MB of float32)
# torch's fills of a model's weights as it is built (torch.nn.init), each one overwritten by TRELLIS.2's checkpoint:
# 36 of the load's 49 s (#159, 2026-11-25: kaiming_uniform_ 22.5 s, normal_ 13.4 s; the files read in 5.2 s), skipped
# while its models are built (unfilled). COMPUTED: what a model makes itself and no checkpoint holds (the structure
# flow model's rope phases, from its positions), the one thing a load may leave unread.
FILLS = ("kaiming_uniform_", "kaiming_normal_", "normal_", "uniform_", "xavier_uniform_", "xavier_normal_",
         "trunc_normal_", "constant_", "zeros_", "ones_")
COMPUTED = frozenset({"rope_phases"})


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


def unfilled(load):
    """`load` (trellis2.models.from_pretrained: a model built, then its checkpoint read with strict=False) with torch's
    weight fills (FILLS) skipped while it builds, so the model is the checkpoint's alone; refused when the checkpoint
    leaves anything but COMPUTED unread, which would then hold no fill at all."""
    import torch

    def built(path, **kwargs):
        fills = {name: getattr(torch.nn.init, name) for name in FILLS}
        reading = torch.nn.Module.load_state_dict
        unread = []

        def read(module, state, *arguments, **keywords):
            result = reading(module, state, *arguments, **keywords)
            unread.extend(key for key in result.missing_keys if key.rsplit(".", 1)[-1] not in COMPUTED)
            return result
        for name in FILLS:
            setattr(torch.nn.init, name, lambda tensor, *arguments, **keywords: tensor)
        torch.nn.Module.load_state_dict = read
        try:
            model = load(path, **kwargs)
        finally:
            for name, fill in fills.items():
                setattr(torch.nn.init, name, fill)
            torch.nn.Module.load_state_dict = reading
        if unread:
            raise SystemExit(f"{path}: its checkpoint holds no {', '.join(unread[:5])}; built unfilled, they would "
                             f"hold nothing")
        return model
    return built


class OnUse(dict):
    """TRELLIS.2's models: those held, and each of `paths` (DROPPED) read by `load` when a stage first asks for it,
    torch's random state kept round the read (the seeded sampling draws as if every model were read before), set to
    drop itself after its stage (its `cpu` to the meta device)."""

    def __init__(self, held, paths, load):
        super().__init__(held)
        self.paths, self.load = paths, load

    def __contains__(self, key):
        return key in self.paths or super().__contains__(key)

    def __missing__(self, key):
        import torch
        if key not in self.paths:
            raise KeyError(key)
        with torch.random.fork_rng(devices=[torch.cuda.current_device()] if torch.cuda.is_available() else []):
            model = self.load(self.paths[key])
        model.eval()
        model.cpu = types.MethodType(lambda self: self.to("meta"), model)
        self[key] = model
        return model


def loaded(env):
    """The pipeline on the card, its held models (MODELS less DROPPED) read now, each DROPPED one when its stage asks
    (OnUse), dropped after it."""
    import trellis2.models
    from trellis2.pipelines import Trellis2ImageTo3DPipeline
    import trellis2.pipelines.rembg as rembg_module
    trellis2.models.from_pretrained = unfilled(trellis2.models.from_pretrained)
    rembg_module.BiRefNet = lambda **kwargs: None  # never loaded: the picture's alpha is the cut-out
    weights = env / "weights"
    Trellis2ImageTo3DPipeline.model_names_to_load = [name for name in MODELS if name not in DROPPED]
    root = weights / "TRELLIS.2-4B"
    pipeline = Trellis2ImageTo3DPipeline.from_pretrained(str(root), local_pipeline(weights))
    pipeline.cuda()
    listed = pipeline._pretrained_args["models"]
    pipeline.models = OnUse(pipeline.models, {name: str(root / listed[name]) for name in DROPPED},
                            trellis2.models.from_pretrained)
    return pipeline


def decoded_path(out):
    """Where the model `out`'s decoded mesh is kept: <out stem>-decoded.glb beside it."""
    return out.with_name(f"{out.stem}-decoded.glb")


def decoded_shape(vertices, faces, target):
    """TRELLIS.2's decoded `vertices` and `faces` (card tensors) cleaned and cut to `target` faces by
    o_voxel.postprocess.to_glb's own no-remesh steps, in its order, and turned to its GLB frame (Y up); its vertices
    and faces as arrays. The steps to_glb takes after these (UV unwrap, texture bake) never move a vertex."""
    import cumesh
    mesh = cumesh.CuMesh()
    mesh.init(vertices.cuda(), faces.cuda())
    mesh.fill_holes(max_hole_perimeter=3e-2)
    mesh.simplify(target * 3, verbose=False)
    for cut in (target, None):
        mesh.remove_duplicate_faces()
        mesh.repair_non_manifold_edges()
        mesh.remove_small_connected_components(1e-5)
        mesh.fill_holes(max_hole_perimeter=3e-2)
        if cut:
            mesh.simplify(cut, verbose=False)
    mesh.unify_face_orientations()
    shaped, cells = (part.cpu().numpy() for part in mesh.read())
    shaped[:, 1], shaped[:, 2] = shaped[:, 2], -shaped[:, 1]
    return shaped, cells


def decoded_written(mesh, out):
    """TRELLIS.2's decoded `mesh` cut to FACES with no remesh, its shape alone (decoded_shape), written at
    decoded_path(out) in the model's own frame (to_glb's, as `out`'s); its faces."""
    import trimesh
    shaped, cells = decoded_shape(mesh.vertices, mesh.faces, FACES)
    trimesh.Trimesh(vertices=shaped, faces=cells, process=False).export(str(decoded_path(out)))
    return int(len(cells))


def see_through(mesh):
    """The share of TRELLIS.2's decoded voxels (`mesh.attrs`, its PBR volume) whose alpha is under CLEAR."""
    alpha = mesh.attrs[:, mesh.layout["alpha"]].float()
    return float((alpha < CLEAR).float().mean())


def band_for(clear):
    """(band, project) to_glb's remesh is laid at for a model `clear` (see_through) of its voxels see-through: BAND
    projected back to one voxel off for a model holding glass (SEE_THROUGH or more), else band 1 unprojected."""
    return (BAND, PROJECT) if clear >= SEE_THROUGH else (1, 0.0)


def made(pipeline, picture, out, faces=FACES):
    """The model of `picture` written as `out` (GLB), its decoded mesh beside it (decoded_written); its counts."""
    import torch
    import o_voxel.postprocess  # imported by name: the meshparts image's o_voxel leaves it out of its __init__
    from PIL import Image
    image = Image.open(picture)
    if image.mode != "RGBA" or image.getchannel("A").getextrema()[0] == 255:
        raise SystemExit(f"{picture}: not a cut-out (no transparent background); the maker reads its alpha")
    mesh = pipeline.run(image, seed=SEED, pipeline_type="1024_cascade")[0]
    mesh.simplify(16777216)
    torch.cuda.empty_cache()  # the decoders' cached blocks back to the card: the remesh starts from what is in use
    clear = see_through(mesh)
    band, project = band_for(clear)
    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices, faces=mesh.faces, attr_volume=mesh.attrs, coords=mesh.coords,
        attr_layout=mesh.layout, voxel_size=mesh.voxel_size, aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=faces, texture_size=TEXTURE, remesh=True, remesh_band=band, remesh_project=project,
        verbose=False)
    glb.export(str(out), extension_webp=False)
    torch.cuda.empty_cache()
    return {"faces": int(len(glb.faces)), "vertices": int(len(glb.vertices)), "see_through": round(clear, 5),
            "band": band, "decoded_faces": decoded_written(mesh, out)}


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
