#!/usr/bin/env bash
# The judge image's command (installed as judge-run): links the judge's weights from the node cache
# (SCORE_MODEL_QWEN3_8_27B_FP8, models.json) to /root/model, where judge_worker.py loads them, then runs the job's
# arguments with the model Python (for example: judge-run tools/props/cloud/judge_worker.py /root/judge/jobs.json).
# A job that names a kernel_cache (job.json; kernels.py points CUDA_CACHE_PATH into the node cache, per card and
# driver, and keeps it in the store) gets vLLM's torch.compile cache, DeepGEMM's and FlashInfer's compiled kernels and
# Triton's beside it, so a node's first judge job takes them from the store instead of compiling.
set -euo pipefail

ln -sfn "${SCORE_MODEL_QWEN3_8_27B_FP8:?the job names the model qwen3.8-27b-fp8}" /root/model
if [ -n "${CUDA_CACHE_PATH:-}" ]; then
  compiled="$(dirname "$CUDA_CACHE_PATH")"
  export VLLM_CACHE_ROOT="$compiled/vllm" DG_JIT_CACHE_DIR="$compiled/deep_gemm" \
    FLASHINFER_WORKSPACE_BASE="$compiled/flashinfer" TRITON_CACHE_DIR="$compiled/triton"
fi
exec /opt/venv/bin/python "$@"
