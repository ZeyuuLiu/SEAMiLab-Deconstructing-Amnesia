# O-Mem StableEval Server Runbook

## Goal

This document explains how to move the current project to a server and run the patched stable-eval O-Mem path.

This runbook is intentionally practical:

1. environment creation
2. dependency installation
3. smoke run
4. full pipeline run
5. two-stage run
6. known limitations

## 1. Recommended Environment

Use:

1. Python `3.10`
2. `conda` environment
3. GPU is optional but strongly recommended

Recommended environment name:

- `omem-paper100`

## 2. Files That Must Exist On Server

Before running, make sure these paths exist:

1. project root
2. `data/locomo10.json`
3. `configs/keys.local.json`
4. local embedding model:
   - `Qwen/Qwen3-Embedding-0.6B`
5. patched O-Mem runtime:
   - `system/O-Mem-StableEval`

## 3. Create Environment

```bash
conda create -n omem-paper100 python=3.10 -y
```

## 4. Install Dependencies

From project root:

```bash
conda run -n omem-paper100 python -m pip install -e .
conda run -n omem-paper100 python -m pip install -r system/O-Mem-StableEval/requirements.txt
```

This stable-eval requirements file already pins:

1. `transformers==4.57.6`
2. `tokenizers==0.22.2`
3. `nltk>=3.9.0`

These are required for:

1. local `Qwen3-Embedding-0.6B`
2. current O-Mem code path

## 5. Verify Runtime Importability

```bash
conda run -n omem-paper100 python scripts/audit_o_mem_adapter.py
```

Expected minimum:

1. `has_full_eval_adapter = true`
2. `importable_in_current_env = true`

## 6. Verify Available Adapter Keys

```bash
conda run -n omem-paper100 python scripts/run_eval_pipeline.py --list-memory-systems
```

Expected:

1. `o_mem`
2. `o_mem_stable_eval`

## 7. Fastest Real Smoke Run

This is the recommended first real run:

```bash
conda run -n omem-paper100 python -u scripts/run_omem_stable_smoke_once.py \
  --sample-id conv-30 \
  --question-index 0 \
  --output outputs/omem_stable_smoke_conv30_q0.json \
  --memory-dir outputs/omem_stable_smoke_conv30_q0_memory
```

Why this run first:

1. `conv-30` is shorter than `conv-26`
2. this gives the highest chance of producing a first real output file

## 8. Strict Full Pipeline Run

If smoke succeeds, run strict pipeline:

```bash
conda run -n omem-paper100 python scripts/run_eval_pipeline.py \
  --memory-system o_mem_stable_eval \
  --adapter-config-json "{\"use_real_omem\":true,\"api_key\":\"YOUR_KEY\",\"base_url\":\"YOUR_URL\",\"llm_model\":\"gpt-4o-mini\",\"embedding_model_name\":\"Qwen/Qwen3-Embedding-0.6B\",\"memory_dir\":\"outputs/omem_stable_eval_pipeline\",\"async_call_timeout_sec\":180}" \
  --dataset data/locomo10.json \
  --output outputs/eval_pipeline_omem_stableeval_limit1.json \
  --limit 1 \
  --top-k 5 \
  --fkey-source rule \
  --llm-model gpt-4o-mini \
  --llm-api-key YOUR_KEY \
  --llm-base-url YOUR_URL \
  --llm-temperature 0.0
```

## 9. Two-Stage O-Mem Experiment

After smoke and strict pipeline succeed, run the experimental two-stage script:

```bash
conda run -n omem-paper100 python scripts/run_omem_two_stage_eval.py \
  --dataset data/locomo10.json \
  --output outputs/omem_two_stage_eval_100.json \
  --limit-questions 100 \
  --correct-sample-count 20 \
  --fkey-source rule \
  --top-k 5 \
  --tau-rank 5 \
  --tau-snr 0.2 \
  --neg-noise-threshold 0.15 \
  --max-workers 3 \
  --omem-llm-model gpt-4o-mini \
  --judge-model gpt-4o-mini \
  --eval-llm-model gpt-4o-mini \
  --llm-temperature 0.0 \
  --api-key YOUR_KEY \
  --base-url YOUR_URL \
  --embedding-model-path Qwen/Qwen3-Embedding-0.6B \
  --memory-dir outputs/omem_real_memory_100 \
  --omem-root system/O-Mem-StableEval
```

## 10. Hyperparameters Currently Assumed

### Stable O-Mem runtime

1. `working_memory_max_size = 20`
2. `episodic_memory_refresh_rate = 5`
3. `retrieval_pieces = 15`
4. `retrieval_drop_threshold = 0.1`
5. `async_call_timeout_sec = 180`

### Eval layer

1. `tau_rank = 5`
2. `tau_snr = 0.2`
3. `neg_noise_score_threshold = 0.15`
4. strict mode enabled by default

### Model usage

1. O-Mem internal generation / routing model:
   - currently tested with `gpt-4o-mini`
2. evaluation-layer LLM judge:
   - currently tested with `gpt-4o-mini`
3. baseline correctness judge in two-stage runner:
   - currently tested with `gpt-4o-mini`
4. embedding model:
   - local `Qwen/Qwen3-Embedding-0.6B`

## 11. Known Limitations

Even after the stable-eval patch:

1. long O-Mem ingest can still be slow
2. some samples may still take a long time because O-Mem itself is LLM-heavy
3. stable-eval prevents indefinite retry loops, but it does not make O-Mem cheap
4. one-question smoke should always be run first

## 12. Recommended Server Workflow

Use this order:

1. `audit_o_mem_adapter.py`
2. `run_omem_stable_smoke_once.py` on `conv-30`
3. `run_eval_pipeline.py --limit 1`
4. `run_omem_two_stage_eval.py` on a small slice
5. then scale to larger slices

## 13. Cross-Window Cursor Usage

If you open another Cursor window on the server, the safest way to continue with the same project context is:

1. open the same project root
2. ask the agent to first read:
   - `docs/code-audit/2026-03-19/eval-layer-bottom-up-implementation-audit.md`
   - `docs/code-audit/2026-03-19/o-mem-adapter-completion-audit.md`
   - `docs/code-audit/2026-03-19/o-mem-stable-eval-internal-fix-notes.md`
   - this runbook
3. optionally give it the prior conversation transcript link:
   - [评估框架上下文](a15e12f7-1df3-4d18-b772-8f688b4b5fca)

Important:

There is no guaranteed automatic cross-window memory transfer.
To preserve context, always provide either:

1. the key docs above
2. or a short handoff summary
3. or the transcript link
