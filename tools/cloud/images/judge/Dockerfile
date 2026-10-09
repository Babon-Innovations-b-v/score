# syntax=docker/dockerfile:1.7
# platforms: linux/amd64
# score-judge: vLLM 0.31.0 for the open judge (tools/props/cloud/judge_worker.py, Qwen3.8-27B in FP8), the version
# the machine runner's unpinned install took on 2026-10-08 and 09 (its logs); requirements.txt, resolved and hashed.
# amd64 only: every card class we rent is on x86 machines. No weights: models.json, fetched by the runtime into
# /cache, and `judge-run` (run.sh) links them where the worker looks.
#
# The CUDA 13.0 compiler and headers (NVIDIA's apt packages, the CUDA of vLLM's torch 2.13.0, with cuBLAS's headers,
# which FlashInfer's FP8 block-scale GEMM builds against on an H100) are in the image at /usr/local/cuda, so vLLM's
# DeepGEMM FP8 kernels and FlashInfer's sampler can build themselves: on the machine image, which had none, both failed
# (2026-10-08), and judge_worker.py turns them off with setdefault. Measured on an H100 PCIe with the same 7 questions
# on a warm node (2026-10-09): on, the longest answer (16,384 tokens) took 320 s, about 51 tokens a second; off, the
# longest (7,115 tokens) took 150 s, about 47 a second, so no clear gain, while a new node's first start with them on
# spent 250 s building kernels against 32 to 44 s warm. So they stay off by default (the worker's setdefault); a job
# turns them on with VLLM_USE_DEEP_GEMM=1 VLLM_USE_FLASHINFER_SAMPLER=1.
ARG BASE
FROM ${BASE}

ARG CUDA_PACKAGES="cuda-nvcc-13-0=13.0.88-1 cuda-crt-13-0=13.0.88-1 cuda-cudart-dev-13-0=13.0.96-1 \
cuda-cudart-13-0=13.0.96-1 cuda-driver-dev-13-0=13.0.96-1 cuda-culibos-dev-13-0=13.0.85-1 cuda-cccl-13-0=13.0.85-1 \
cuda-nvrtc-13-0=13.0.88-1 cuda-nvrtc-dev-13-0=13.0.88-1 libcurand-13-0=10.4.0.35-1 libcurand-dev-13-0=10.4.0.35-1 \
libcublas-13-0=13.1.1.3-1 libcublas-dev-13-0=13.1.1.3-1"
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ninja-build ${CUDA_PACKAGES} \
 && rm -rf /var/lib/apt/lists/* \
 && ln -sfn /usr/local/cuda-13.0 /usr/local/cuda \
 && /usr/local/cuda/bin/nvcc --version | tail -1
ENV CUDA_HOME=/usr/local/cuda PATH=/usr/local/cuda/bin:${PATH} HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1
COPY requirements.txt /opt/judge/requirements.txt
RUN uv venv --python 3.12.13 /opt/venv \
 && uv pip sync --python /opt/venv --require-hashes /opt/judge/requirements.txt \
 && /opt/venv/bin/python -c "import vllm, torch; print(vllm.__version__, torch.__version__, torch.version.cuda)"
COPY --chmod=755 run.sh /usr/local/bin/judge-run
