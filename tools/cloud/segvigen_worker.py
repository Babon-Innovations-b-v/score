"""Runs on a rented machine: SegviGen (Nelipot-Lee/SegviGen at a pinned commit, MIT, on Microsoft's TRELLIS.2, MIT)
over our own Pixal3D models, once with no guidance and once guided by a part-colour map (job parts-test, 2026-10-09).

    cd /root/sv/SegviGen && /root/sv/venv/bin/python segvigen_worker.py <in folder> <out folder> <DINOv3 folder>

Each <in>/<take>/ holds raw.glb (the raw Pixal3D model, textured) and map.png (the close-up's finish regions in part
colours, clear around the object). <out>/<take>/ gets segvigen_auto.npz and segvigen_guided.npz: `coords` (the
predicted voxels on SegviGen's 512 grid), `colours` (their predicted part colours, 0..255), `centre` and `scale` (the
model's box centre and the scale its voxeliser took its longest side to 1 with), and segvigen_timing.json.

Two of SegviGen's parts are never used: its background remover (briaai/RMBG-2.0, non-commercial) is not loaded, since
both conditioning pictures carry their own alpha and are cropped here the way its own preprocess crops them; and its
glb exporter (o_voxel.postprocess.to_glb, which needs the non-commercial nvdiffrast) is not called, the voxels
coming back instead for the label transfer at home (../library/split_compare.py).
"""
import json
import pathlib
import sys
import time
import traceback

import numpy as np
import torch
import trimesh
from PIL import Image

sys.path.insert(0, str(pathlib.Path.cwd()))
from inference_full import (Gen3DSeg, Sampler, get_cond, process_glb_to_vxz,  # noqa: E402
                            tex_slat_sample_single, vxz_to_latent_slat)
from data_toolkit.bpy_render import render_from_transforms  # noqa: E402
from trellis2 import models  # noqa: E402
from trellis2.modules.image_feature_extractor import DinoV3FeatureExtractor  # noqa: E402

TRELLIS = "microsoft/TRELLIS.2-4B"
CHECKPOINTS = {"auto": "weights/full_seg.ckpt", "guided": "weights/full_seg_w_2d_map.ckpt"}
SEED = 0


def cropped(image):
    """SegviGen's preprocess_image without its background remover: the object's square box (alpha over 0.8),
    premultiplied onto black."""
    image = image.convert("RGBA")
    if max(image.size) > 1024:
        scale = 1024 / max(image.size)
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    alpha = np.asarray(image)[:, :, 3]
    box = np.argwhere(alpha > 0.8 * 255)
    low, high = box.min(0), box.max(0)
    centre = (low[1] + high[1]) / 2, (low[0] + high[0]) / 2
    size = int(max(high[1] - low[1], high[0] - low[0]))
    image = image.crop((centre[0] - size // 2, centre[1] - size // 2, centre[0] + size // 2, centre[1] + size // 2))
    pixels = np.asarray(image).astype(np.float32) / 255
    return Image.fromarray((pixels[:, :, :3] * pixels[:, :, 3:4] * 255).astype(np.uint8))


def box_of(glb):
    """The centre and scale SegviGen's voxeliser normalises the model with (process_glb_to_vxz)."""
    bounds = trimesh.load(glb, force="scene").bounding_box.bounds
    return (bounds[0] + bounds[1]) / 2, 0.99999 / float((bounds[1] - bounds[0]).max())


class Models:
    """SegviGen's models, loaded once for a share of takes."""

    def __init__(self, dinov3):
        self.pipeline = json.loads(pathlib.Path(f"{TRELLIS}/pipeline.json").read_text())["args"]
        self.segmenter = Gen3DSeg(models.from_pretrained(f"{TRELLIS}/ckpts/slat_flow_imgshape2tex_dit_1_3B_512_bf16"))
        self.segmenter.eval().cuda()
        self.weights = {mode: weights_of(path) for mode, path in CHECKPOINTS.items()}
        self.sampler = Sampler()
        self.shape_encoder = models.from_pretrained(f"{TRELLIS}/ckpts/shape_enc_next_dc_f16c32_fp16").cuda().eval()
        self.tex_encoder = models.from_pretrained(f"{TRELLIS}/ckpts/tex_enc_next_dc_f16c32_fp16").cuda().eval()
        self.shape_decoder = models.from_pretrained(f"{TRELLIS}/ckpts/shape_dec_next_dc_f16c32_fp16").cuda().eval()
        self.tex_decoder = models.from_pretrained(f"{TRELLIS}/ckpts/tex_dec_next_dc_f16c32_fp16").cuda().eval()
        self.image_model = DinoV3FeatureExtractor(model_name=dinov3)
        self.image_model.cuda()


def weights_of(path):
    """A SegviGen checkpoint's state dict, its keys as Gen3DSeg names them."""
    state = torch.load(path, map_location="cpu")["state_dict"]
    return {key.replace("gen3dseg.", ""): value for key, value in state.items()}


def predicted(loaded, mode, latents, picture):
    """The part colours SegviGen predicts for the model's voxels, conditioned on `picture`: (coords, colours)."""
    shape_slat, subs, tex_slat = latents
    loaded.segmenter.load_state_dict(loaded.weights[mode])
    condition = get_cond(loaded.image_model, [cropped(picture)])
    torch.manual_seed(SEED)
    output = tex_slat_sample_single(loaded.segmenter, loaded.sampler, loaded.pipeline, shape_slat, tex_slat, condition)
    with torch.no_grad():
        voxels = loaded.tex_decoder(output, guide_subs=subs) * 0.5 + 0.5
    coords = voxels.coords[:, 1:].cpu().numpy().astype(np.int16)
    colours = (voxels.feats[:, :3].clamp(0, 1) * 255).round().cpu().numpy().astype(np.uint8)
    return coords, colours


def one_take(loaded, take_in, take_out):
    """Both runs on one take; the seconds each step took."""
    take_out.mkdir(parents=True, exist_ok=True)
    glb, seconds = str(take_in / "raw.glb"), {}
    began = time.time()
    process_glb_to_vxz(glb, str(take_out / "input.vxz"))
    shape_slat, _, subs, tex_slat = vxz_to_latent_slat(loaded.shape_encoder, loaded.shape_decoder,
                                                       loaded.tex_encoder, str(take_out / "input.vxz"))
    seconds["encode"] = round(time.time() - began, 1)
    centre, scale = box_of(glb)
    began = time.time()
    render_from_transforms(glb, "data_toolkit/transforms.json", str(take_out / "render.png"))
    seconds["render"] = round(time.time() - began, 1)
    for mode, picture in (("auto", take_out / "render.png"), ("guided", take_in / "map.png")):
        began = time.time()
        coords, colours = predicted(loaded, mode, (shape_slat, subs, tex_slat), Image.open(picture))
        np.savez_compressed(take_out / f"segvigen_{mode}.npz", coords=coords, colours=colours, centre=centre,
                            scale=scale)
        seconds[mode] = round(time.time() - began, 1)
    (take_out / "input.vxz").unlink()
    return seconds


def main():
    source, out, dinov3 = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    began = time.time()
    loaded = Models(dinov3)
    load_seconds = round(time.time() - began, 1)
    takes = sorted(path for path in source.iterdir() if (path / "raw.glb").exists())
    failed = []
    for take_in in takes:
        try:
            seconds = one_take(loaded, take_in, out / take_in.name)
        except Exception:  # noqa: BLE001 - written down and reported below; the share's other takes still run
            (out / take_in.name / "segvigen_error.txt").write_text(traceback.format_exc())
            failed.append(take_in.name)
            continue
        finally:
            torch.cuda.empty_cache()
        seconds["load_share"] = round(load_seconds / len(takes), 1)
        (out / take_in.name / "segvigen_timing.json").write_text(json.dumps(seconds))
        print(take_in.name, json.dumps(seconds), flush=True)
    if failed:
        raise SystemExit(f"SegviGen failed on {', '.join(failed)}")


if __name__ == "__main__":
    main()
