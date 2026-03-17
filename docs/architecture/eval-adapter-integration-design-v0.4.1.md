# Eval Layer <-> Adapter Layer Integration Design v0.4.1

## 1. Design Goal

Define a clear and auditable integration between:

1. Evaluation Layer (framework-owned diagnosis logic)
2. Adapter Layer (memory-system-specific I/O and backend traversal)

This document focuses on:

1. relation between layers
2. runtime flow
3. parallel probe execution strategy
4. where and how LLM assistance is invoked

---

## 2. Layer Responsibilities

## 2.1 Evaluation Layer (must stay system-agnostic)

Owns:

1. state machine (`S_enc`, `S_ret`, `S_gen`)
2. defect mapping (`EM/EA/EW/DMP/RF/LATE/NOI/NIR/GH/GF/GRF`)
3. defect union and evidence output
4. metric computation and report generation

Must not own:

1. direct DB/VectorDB traversal code per memory system
2. system-specific retrieval/generation API details

## 2.2 Adapter Layer (must stay system-specific)

Owns:

1. exporting full memory corpus `M`
2. exporting original retrieval result `C_original`
3. generating oracle answer `A_oracle` with provided `C_oracle`
4. converting native system outputs to evaluator contracts

Must not own:

1. final defect decision logic
2. metric logic

---

## 3. Contract Interfaces

Current protocol set (recommended split):

1. `EncodingAdapterProtocol`
   - `export_full_memory(run_ctx) -> M`
   - `find_memory_records(run_ctx, query, f_key, memory_corpus) -> candidate_records`
2. `RetrievalAdapterProtocol`
   - `retrieve_original(run_ctx, query, top_k) -> C_original`
3. `GenerationAdapterProtocol`
   - `generate_oracle_answer(run_ctx, query, oracle_context) -> A_oracle`

Optional umbrella adapter:

1. A concrete adapter may implement all three protocols in one class.

---

## 4. End-to-End Runtime Flow

## 4.1 Sample resolution (dataset side)

For one incoming query from a memory system:

1. resolve `EvalSample` by `question_id` or `query`
2. get:
   - `Q`
   - `A_gold`
   - `task_type`
   - `F_key`
   - `C_oracle`
   - evidence fields

## 4.2 Adapter preparation

1. `run_ctx = adapter.ingest_conversation(sample_id, conversation)` (or prebuilt context)

## 4.3 Parallel probe execution

Three probes run concurrently:

1. Encoding:
   - input: `Q + M + F_key`
   - where `M` and candidates come from adapter protocol
2. Retrieval:
   - input: `Q + C_original + F_key (+ s_enc gate)`
   - where `C_original` comes from adapter protocol
3. Generation:
   - input: `Q + C_oracle (+ adapter generated A_oracle) + A_gold`
   - where `A_oracle` comes from adapter protocol

After probe completion:

1. apply reconciliation rules (e.g., suppress `RF` when `S_enc=MISS`)
2. build `D_total`
3. emit evidence-first attribution record

---

## 5. LLM Assistance Strategy

LLM assistance is optional and configurable. Rule path always remains fallback.

## 5.1 Encoding probe assist

Use case:

1. fuzzy fact match where rule matching is uncertain

API:

1. `llm_judge_fact_match(...)`

Output:

1. `match`
2. `ambiguous`
3. `reason`

## 5.2 Retrieval probe assist

Use case:

1. NEG noise judgement beyond score threshold heuristic

API:

1. `llm_judge_retrieval_noise(...)`

Output:

1. `is_noise`
2. `reason`

## 5.3 Generation probe assist

Use case:

1. smarter correctness/subtype judgement for `A_oracle` vs `A_gold`

API:

1. `llm_judge_generation_answer(...)`

Output:

1. `correct`
2. `substate` (`GH|GF|GRF|NONE`)
3. `grounded`
4. `reason`

---

## 6. Positive vs Negative Handling

The current logic is explicitly bifurcated:

1. POS:
   - evaluate factual existence, retrieval quality, correctness and grounding
2. NEG:
   - evaluate contamination/noise and abstention behavior

This split must remain explicit in each probe to avoid mixed semantics.

---

## 7. Recommended Adapter Implementation Pattern

For each memory system adapter:

1. implement 3 protocol methods first
2. add deterministic normalization:
   - ids
   - text
   - scores
3. keep raw payload under `meta/raw_trace` for audit
4. ensure no silent failure:
   - if retrieval fails, return empty list + error note in trace

Minimal adapter skeleton:

1. `export_full_memory`: convert native memory store to list of `{id,text,meta}`
2. `find_memory_records`: backend-aware scan/filter
3. `retrieve_original`: preserve order and score
4. `generate_oracle_answer`: call system model with provided `C_oracle`

---

## 8. Evidence Contract (must-have)

Every probe output should include:

1. human-readable reason
2. machine-auditable fields used in decision
3. source markers (`adapter.export_full_memory`, `adapter.retrieve_original`, etc.)

Final attribution record should include:

1. `states`
2. `defects`
3. `enc_evidence`, `ret_evidence`, `gen_evidence`
4. `decision_trace`

---

## 9. Failure and Fallback Policy

1. Adapter method error:
   - capture error in evidence
   - use empty/default safe input for that probe if allowed
2. LLM assist error:
   - ignore LLM output
   - use deterministic rule logic
3. Hard contract violation:
   - fail fast in test mode
   - soft continue in production mode with explicit error trace

---

## 10. Implementation Roadmap (Next)

## Step A (integration wiring)

1. add adapter-aware evaluator entry:
   - one call executes all three protocol paths
2. pass `s_enc` to retrieval probe in the same run

## Step B (adapter conformance suite)

1. build protocol conformance tests for each adapter
2. enforce required fields and fallback behavior

## Step C (full pipeline hardening)

1. persist unified traces
2. add metric-level audits and anomaly checks
3. add regression snapshots for stable releases

---

## 11. Review Summary

This architecture is correct for your objective:

1. evaluation logic remains unified and comparable
2. adapter logic remains pluggable per memory system
3. probes can run truly in parallel
4. evidence-first outputs remain auditable

The key execution requirement is strict contract discipline at adapter boundaries.
