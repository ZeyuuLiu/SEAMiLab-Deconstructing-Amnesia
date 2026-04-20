#!/usr/bin/env bash
# Embedding 服务（单 GPU）。用法：
#   conda activate <你的环境>   # 已安装 vllm
#   bash deploy-qwen3-embed.sh
# 或：chmod +x deploy-qwen3-embed.sh && ./deploy-qwen3-embed.sh
#
# 模型目录可通过环境变量覆盖（默认指向当前工作区已存在的 HF 缓存路径）
: "${EMBEDDING_MODEL_PATH:=/DATA/disk4/workspace/zhongjian/memory/cache/models/Qwen/Qwen3-Embedding-0___6B}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

# 与 Qwen3-8B 等同卡并行时，默认 0.9 会因空闲显存不足报错；请调低或改用另一张卡（如 CUDA_VISIBLE_DEVICES=1）
: "${VLLM_GPU_MEMORY_UTILIZATION:=0.07}"

# vLLM 0.19+：--runner pooling + --convert embed（已无 --task embed）
exec vllm serve "${EMBEDDING_MODEL_PATH}" \
  --runner pooling \
  --convert embed \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION}" \
  --host 0.0.0.0 \
  --port 8001 \
  --served-model-name Qwen3-Embedding-0.6B \
  --trust-remote-code
