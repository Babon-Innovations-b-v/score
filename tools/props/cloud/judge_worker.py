"""Runs on a rented machine: answers every question in its share with one vision-language model, all at once.

    /root/venv/bin/python judge_worker.py /root/judge/jobs.json

Each job is {"name", "text", "images"}: the question and its pictures (names under /root/judge/in/), the pictures
put before the text in the order given. The model's weights are under /root/model (judge_setup.sh), run through
vLLM with its thinking on; each answer is written whole to /root/judge/out/<name>.txt, and a line "<name> <tokens>"
is printed for each, so the runner can follow along.
"""
import base64
import json
import os
import pathlib
import sys
import time

# vLLM's DeepGEMM FP8 kernels and FlashInfer's sampler compile themselves with the CUDA toolkit, which the GPU image
# does not carry (two runs failed on it, 2026-10-08); vLLM's own kernels for both need none.
os.environ.setdefault("VLLM_USE_DEEP_GEMM", "0")
os.environ.setdefault("VLLM_USE_FLASHINFER_SAMPLER", "0")

from vllm import LLM, SamplingParams  # noqa: E402

MODEL = "/root/model"
IN = pathlib.Path("/root/judge/in")
OUT = pathlib.Path("/root/judge/out")
# The model card's sampling for thinking, with a fixed seed so a run can be repeated.
# Questions answered side by side; vLLM's default of 1024 asks more of the model's recurrent-state cache than a card
# holds (785 on an H100 at 0.9 of its memory, 2026-10-08).
MAX_AT_ONCE = 64
SAMPLING = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, max_tokens=16384, seed=7)


def picture_part(name):
    """One picture as a data URL, the way vLLM's chat takes it without opening local files."""
    data = base64.b64encode((IN / name).read_bytes()).decode()
    kind = "png" if name.endswith(".png") else "jpeg"
    return {"type": "image_url", "image_url": {"url": f"data:image/{kind};base64,{data}"}}


def conversation(job):
    """The one user turn of a job: its pictures, then its text."""
    return [{"role": "user", "content": [*(picture_part(name) for name in job["images"]),
                                         {"type": "text", "text": job["text"]}]}]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text())
    model = LLM(model=MODEL, max_model_len=32768, max_num_seqs=MAX_AT_ONCE, limit_mm_per_prompt={"image": 4},
                gpu_memory_utilization=0.9)
    began = time.time()
    answers = model.chat([conversation(job) for job in jobs], SAMPLING,
                         chat_template_kwargs={"enable_thinking": True})
    for job, answer in zip(jobs, answers):
        (OUT / f"{job['name']}.txt").write_text(answer.outputs[0].text)
        print(job["name"], len(answer.outputs[0].token_ids), flush=True)
    print("seconds", round(time.time() - began, 1), flush=True)


if __name__ == "__main__":
    main()
