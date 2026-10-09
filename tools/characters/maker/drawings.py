"""The person route's three drawings, by FLUX.2 klein 4B (Apache-2.0) on the rented card:

    /root/envs/picture/bin/python drawings.py apose <out.png> "<who>" [<reference> ...] [--seeds 1 2]
    /root/envs/picture/bin/python drawings.py hair <out folder> "<the hair>" <bald view> <head picture> [--seeds ...]
    /root/envs/picture/bin/python drawings.py face <out folder> "<the face>" <depth.png> <head picture> [--seeds ...]

- `apose`: the person as a softly lit 3D render in the skeleton's A-pose, the picture SAM3DBody-cpp reads the build
  off; from the references when there are any, from the words alone when there are none.
- `hair`: the person's bald head (blender_views.py) redrawn as a clay model wearing the reference's hair, the picture
  Hi3DGen makes the hair mesh from (round three's hair option 4, #100).
- `face`: the front master of the face, drawn by klein base 4B with the refcontrol reference-depth LoRA
  (thedeoxen/refcontrol-FLUX.2-klein-4B-reference-depth-lora, Apache-2.0) on the person's exact head depth, the
  reference head as the reference (#112).

Each writes one picture a seed (`<name>_s<seed>.png`) and prints its seconds. The wordings are the nev_mars job's
(#112), kept word for word where a person's own words are not swapped in.
"""
import argparse
import pathlib
import time

import torch
from diffusers import AutoencoderKLFlux2, FlowMatchEulerDiscreteScheduler, Flux2KleinPipeline, Flux2Transformer2DModel
from PIL import Image
from transformers import AutoTokenizer, Qwen3ForCausalLM

MODELS = pathlib.Path("/root/models")
KLEIN = MODELS / "klein-4b"
KLEIN_BASE = MODELS / "klein-base-4b"
LORA = MODELS / "refcontrol" / "flux2_klein_4b_refcontrol_depth.safetensors"

FORM = ("softly lit detailed 3D render of a realistic character as a game asset, believable materials with visible "
        "shading and fabric folds, soft studio light, no cast shadows, plain light grey background, not a toy, no text")
POSE = ("full body seen straight from the front, standing still and symmetrical in an A-pose: both arms held straight "
        "and away from the body, pointing down at 45 degrees, hands open and clear of the hips, feet a shoulder width "
        "apart, looking straight ahead, the whole figure in the picture with space around it")


def apose_wording(who, referenced):
    """The A-pose picture's words: the person, the pose and the form."""
    lead = f"the same person as in the reference: {who}" if referenced else who
    return f"{lead}, {POSE}, {FORM}"


def hair_wording(hair):
    """The clay hair picture's words (round three's klein_hair.py)."""
    return (f"matte clay model of the bald head from image 1, same head, same face, same angle, now wearing the hair "
            f"of the person in image 2: {hair}; clean solid silhouette made of a few large clean clumps, no loose "
            f"strands; the hair in dark grey clay, the skin in light grey clay, no colour, three-quarter view from the "
            f"front left, level telephoto camera, soft even studio light, plain white background")


def face_wording(face):
    """The face drawing's words (the nev_mars job's draw_face.py)."""
    return (f"refcontrol. The person from the reference, {face}, seen straight from the front, calm closed mouth, "
            f"graphic novel ink drawing, bold black outlines, clean line work, flat colours, flat even front light, no "
            f"shading, no shadows, plain white background.")


def klein():
    """FLUX.2 klein 4B (distilled), whole on the card."""
    return Flux2KleinPipeline.from_pretrained(KLEIN, torch_dtype=torch.bfloat16).to("cuda")


def klein_base_with_depth():
    """klein base 4B's transformer with the distilled model's text encoder, tokenizer and VAE (the same files), and
    the reference-depth LoRA loaded."""
    pipeline = Flux2KleinPipeline(
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(KLEIN_BASE / "scheduler"),
        vae=AutoencoderKLFlux2.from_pretrained(KLEIN / "vae", torch_dtype=torch.bfloat16),
        text_encoder=Qwen3ForCausalLM.from_pretrained(KLEIN / "text_encoder", torch_dtype=torch.bfloat16),
        tokenizer=AutoTokenizer.from_pretrained(KLEIN / "tokenizer"),
        transformer=Flux2Transformer2DModel.from_pretrained(KLEIN_BASE / "transformer", torch_dtype=torch.bfloat16),
        is_distilled=False)
    pipeline.load_lora_weights(str(LORA.parent), weight_name=LORA.name, adapter_name="refcontrol")
    pipeline.set_adapters(["refcontrol"], adapter_weights=[1.0])
    return pipeline.to("cuda")


def draw(pipeline, out, seeds, settings):
    """One picture a seed into `out` (a path with `{seed}` in its name); their paths."""
    made = []
    for seed in seeds:
        began = time.time()
        picture = pipeline(generator=torch.Generator("cpu").manual_seed(seed), **settings).images[0]
        path = pathlib.Path(str(out).format(seed=seed))
        path.parent.mkdir(parents=True, exist_ok=True)
        picture.save(path)
        made.append(path)
        print(f"{path.name} {time.time() - began:.1f}", flush=True)
    return made


def pictures(paths):
    return [Image.open(path).convert("RGB") for path in paths]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=("apose", "hair", "face"))
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("words")
    parser.add_argument("inputs", nargs="*", type=pathlib.Path)
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2])
    options = parser.parse_args()
    if options.what == "apose":
        settings = {"image": pictures(options.inputs) or None, "num_inference_steps": 4, "guidance_scale": 1.0,
                    "prompt": apose_wording(options.words, bool(options.inputs)), "height": 1152, "width": 896}
        draw(klein(), options.out.with_name(options.out.stem + "_s{seed}.png"), options.seeds, settings)
    elif options.what == "hair":
        settings = {"image": pictures(options.inputs), "prompt": hair_wording(options.words), "height": 1024,
                    "width": 1024, "num_inference_steps": 4, "guidance_scale": 1.0}
        draw(klein(), options.out / "klein_s{seed}.png", options.seeds, settings)
    else:
        settings = {"image": pictures(options.inputs), "prompt": face_wording(options.words), "height": 1024,
                    "width": 1024, "num_inference_steps": 50, "guidance_scale": 4.0}
        draw(klein_base_with_depth(), options.out / "drawn_s{seed}.png", options.seeds, settings)


if __name__ == "__main__":
    main()
