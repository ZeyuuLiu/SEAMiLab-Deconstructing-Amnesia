#!/usr/bin/env bash
# Qwen3-8B 主模型（OpenAI 兼容 Chat/Completion）。用法：
#   conda activate <已安装 vllm 的环境>
#   bash deploy-qwen3-8B.sh
#
# 模型目录可通过环境变量覆盖
: "${LLM_MODEL_PATH:=/DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/Qwen/Qwen3-32B}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

# 与其它进程共用 GPU 时按需调低（约 ≤ 空闲显存/总显存）；独占整卡可设 0.9
: "${VLLM_GPU_MEMORY_UTILIZATION:=0.9}"

# 与 .env 中 VLLM_MODEL_NAME、VLLM_BASE_URL 默认一致（8000/v1）
: "${VLLM_PORT:=8000}"
: "${VLLM_SERVED_MODEL_NAME:=Qwen3-32B}"

# LangGraph / LangChain 会发 tool_choice=auto，vLLM 必须开启下列选项，否则 chat 报 400
# 可选：qwen3_xml（Qwen3 推荐）、hermes（部分 Qwen 也可用）；见 vllm serve --help
: "${VLLM_TOOL_CALL_PARSER:=qwen3_xml}"

exec vllm serve "${LLM_MODEL_PATH}" \
  --served-model-name "${VLLM_SERVED_MODEL_NAME}" \
  --dtype auto \
  --max-model-len 8192 \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION}" \
  --enable-auto-tool-choice \
  --tool-call-parser "${VLLM_TOOL_CALL_PARSER}" \
  --host 0.0.0.0 \
  --port "${VLLM_PORT}" \
  --trust-remote-code
