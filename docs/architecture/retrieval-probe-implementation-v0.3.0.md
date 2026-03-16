# Retrieval Probe Implementation v0.3.0

## 1. Scope

This document focuses on retrieval probe (`P_ret`) implementation aligned to `docs/最终指标.md`.

## 2. Explicit Input Definition

Retrieval probe input is:

1. `Q` (user query)
2. `C_original` (ordered retrieval list from real memory system)
3. `F_key` (from `demo_build_locomo_samples.py` output)

In code:

1. `RetrievalProbeInput.question`
2. `RetrievalProbeInput.retrieved_items`
3. `RetrievalProbeInput.f_key`

## 3. Adapter-Layer Integration

`Q` and `C_original` are adapter-provided:

1. `RetrievalAdapterProtocol.retrieve_original(run_ctx, query, top_k)`

Probe entry:

1. `evaluate_retrieval_probe_with_adapter(sample, adapter, run_ctx, cfg, top_k, s_enc)`

## 4. State and Defect Rules (Aligned to 最终指标.md)

### State

1. `NOISE` for NEG with high misleading similarity/score
2. `MISS` when `F_key` is not found in `C_original`
3. `HIT` when `F_key` appears in `C_original`

### Defect mapping

1. `MISS` + `s_enc != MISS` -> `RF`
2. `HIT` + `rank > tau_rank` -> `LATE`
3. `HIT` + `snr < tau_snr` -> `NOI`
4. `NOISE` -> `NIR`

### Attributes

1. `rank_index`
2. `snr`

## 5. LLM-Assisted Judgement

Optional LLM assistance added:

1. `cfg.use_llm_assist=True` can trigger `llm_judge_retrieval_noise(...)` for NEG noise check.
2. If LLM unavailable/fails, rule-based path remains deterministic fallback.

This keeps runtime robust while allowing stronger semantic checks.

## 6. Evidence Output

Retrieval result includes:

1. `top_items`
2. `hit_indices`
3. `snr_numerator`, `snr_denominator`
4. `rf_gate_s_enc`
5. optional `llm_noise_judgement`

## 7. Validation Script

Independent script:

1. `scripts/test_retrieval_probe.py`

Covered cases:

1. HIT clean
2. HIT + LATE + NOI
3. MISS + RF
4. MISS without RF when `s_enc=MISS`
5. NEG NOISE
6. NEG MISS
7. adapter-entry smoke
