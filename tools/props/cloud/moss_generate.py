"""On the rented card: every job in /root/sfx/jobs.json (or the share named, `moss_generate.py <jobs.json> <tag>`, when
a page is spread over machines) through MOSS-SoundEffect v2.0, one WAV each, timed; then every take scored for how
well it matches its prompt with LAION's CLAP (laion/larger_clap_general, Apache-2.0), the cosine of the take's and
the prompt's embeddings, into out/scores.json (out/scores-<tag>.json for a share; moss_sound.py joins them). The picker reads the score as one part of
choosing a sound's take; the rest (clipping, silence, length, a loop's join) it measures itself.

A job is {"file", "prompt", "seconds", "seed"}; the settings are the ones the owner heard on the trial (2026-10-06):
100 steps, guidance 4.0, sigma shift 5.0.
"""
import json
import os
import sys
import time

import soundfile
import torch

sys.path.insert(0, "/root/sfx/MOSS-TTS")
from moss_soundeffect_v2 import MossSoundEffectPipeline  # noqa: E402

JOBS = "/root/sfx/jobs.json"
OUT = "/root/sfx/out"
CLAP = "laion/larger_clap_general"
CLAP_REVISION = "ada0c23a36c4e8582805bb38fec3905903f18b41"
## CLAP hears ten seconds; a take is heard from just after its start.
CLAP_SECONDS = 10.0
CLAP_SKIP_SECONDS = 0.3
STEPS = 100
GUIDANCE = 4.0
SIGMA_SHIFT = 5.0


def generate(jobs):
    """Every job's take, written to OUT; the timings. A take already there (a run picked up again) is kept."""
    began = time.time()
    pipe = MossSoundEffectPipeline.from_pretrained("/root/sfx/model", torch_dtype=torch.bfloat16, device="cuda")
    timings = {"load_seconds": round(time.time() - began, 1), "sample_rate": pipe.sample_rate, "runs": {}}
    print("loaded", timings["load_seconds"], "s", flush=True)
    for job in jobs:
        target = f"{OUT}/{job['file']}"
        if os.path.exists(target):
            continue
        began = time.time()
        audio = pipe(prompt=job["prompt"], seconds=job["seconds"], num_inference_steps=STEPS, cfg_scale=GUIDANCE,
                     sigma_shift=SIGMA_SHIFT, seed=job["seed"])
        torch.cuda.synchronize()
        soundfile.write(target + ".part.wav", audio[0].detach().float().cpu().numpy().T, pipe.sample_rate,
                        subtype="PCM_24")
        os.replace(target + ".part.wav", target)
        timings["runs"][job["file"]] = round(time.time() - began, 1)
        print(job["file"], timings["runs"][job["file"]], "s", flush=True)
    timings["peak_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 1)
    del pipe
    torch.cuda.empty_cache()
    return timings


def score(jobs):
    """Each take's CLAP match to its prompt, by file."""
    import numpy
    from transformers import ClapModel, ClapProcessor
    model = ClapModel.from_pretrained(CLAP, revision=CLAP_REVISION).to("cuda").eval()
    processor = ClapProcessor.from_pretrained(CLAP, revision=CLAP_REVISION)
    scores = {}
    for job in jobs:
        samples, rate = soundfile.read(f"{OUT}/{job['file']}", always_2d=True)
        mono = samples.mean(axis=1).astype(numpy.float32)
        mono = mono[int(CLAP_SKIP_SECONDS * rate):][:int(CLAP_SECONDS * rate)]
        inputs = processor(text=[job["prompt"]], audios=[mono], sampling_rate=rate, return_tensors="pt",
                           padding=True)
        with torch.no_grad():
            heard = model(**{key: value.to("cuda") for key, value in inputs.items()})
        audio = torch.nn.functional.normalize(heard.audio_embeds, dim=-1)
        text = torch.nn.functional.normalize(heard.text_embeds, dim=-1)
        scores[job["file"]] = round(float((audio * text).sum()), 4)
        print(job["file"], "clap", scores[job["file"]], flush=True)
    return scores


def main():
    jobs = json.load(open(sys.argv[1] if len(sys.argv) > 1 else JOBS))
    tag = f"-{sys.argv[2]}" if len(sys.argv) > 2 else ""
    timings = generate(jobs)
    json.dump(timings, open(f"{OUT}/timings{tag}.json", "w"), indent=1)
    began = time.time()
    scores = score(jobs)
    json.dump(scores, open(f"{OUT}/scores{tag}.json", "w"), indent=1)
    timings["score_seconds"] = round(time.time() - began, 1)
    json.dump(timings, open(f"{OUT}/timings{tag}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
