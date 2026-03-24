# Eval Layer Bottom-Up Implementation Audit

## Scope

This document explains how the evaluation layer is actually implemented from bottom to top in the current project.
It is based on reviewing the code under:

- `src/memory_eval/dataset/`
- `src/memory_eval/eval_core/`
- `src/memory_eval/pipeline/`
- `scripts/run_eval_pipeline.py`
- `scripts/run_omem_two_stage_eval.py`

This document focuses on implementation reality, not only intended design.

## 1. Overall Layering

The current evaluation stack is implemented as:

1. Dataset layer
   - Builds standardized `EvalSample` instances from `locomo10.json`
2. Eval core
   - Defines state spaces, defect labels, evidence contracts, LLM judges, and the three probes
3. Adapter layer
   - Converts an external memory system into the contracts required by the eval core
4. Pipeline layer
   - Connects dataset -> adapter runtime -> three probes -> json report
5. Experiment scripts
   - CLI runners, tests, audits, and the O-Mem two-stage evaluation script

This separation is real in code, not only in docs.

## 2. Dataset Layer

Implemented in `src/memory_eval/dataset/locomo_builder.py`.

### What it does

1. Reads `locomo10.json`
2. Flattens multi-session conversations into turn-level records
3. Resolves evidence ids into:
   - `evidence_texts`
   - `evidence_with_time`
   - `oracle_context`
4. Infers `task_type`
   - `POS` if answer is normal factual answer
   - `NEG` if answer matches abstain / unknown pattern
5. Produces unified `EvalSample`

### Important implementation details

1. `oracle_context` is time-aware:
   - `<date_time> | <speaker>: <text>`
2. For NEG samples:
   - `f_key = []`
   - `oracle_context = "NO_RELEVANT_MEMORY"`
3. Current default `f_key` construction is still evidence-based:
   - rule mode uses `evidence_with_time` directly

This means the dataset layer already enforces the evaluation layer's expected inputs and POS/NEG split.

## 3. Core Data Contracts

Implemented in `src/memory_eval/eval_core/models.py`.

### Key structures

1. `EvalSample`
   - question, gold answer, task type, key facts, oracle context, evidence
2. `RetrievedItem`
   - normalized retrieval item from adapter
3. `AdapterTrace`
   - full observation bundle for trace-based evaluation
4. `ProbeResult`
   - one probe's state, defects, evidence, attrs
5. `AttributionResult`
   - final per-sample attribution output
6. `EvaluatorConfig`
   - thresholds + LLM settings + strict execution policy

### Strict execution policy

This project has now encoded strict-mode defaults directly in `EvaluatorConfig`:

1. `require_llm_judgement = True`
2. `strict_adapter_call = True`
3. `disable_rule_fallback = True`
4. `require_online_answer = True`

So the evaluation layer is not "best effort" anymore by default. It is designed to fail explicitly.

## 4. Adapter Protocol Layer

Implemented in `src/memory_eval/eval_core/adapter_protocol.py`.

The evaluation layer depends on four protocol groups:

1. `EvalAdapterProtocol`
   - coarse runtime contract
2. `EncodingAdapterProtocol`
   - full memory export + candidate search
3. `RetrievalAdapterProtocol`
   - native retrieval export
4. `GenerationAdapterProtocol`
   - oracle answer generation + optional online answer generation

This is the key decoupling point:

- the eval layer does not know whether memory is stored in JSON, Redis, SQL, graph, or custom classes
- it only depends on adapter-provided normalized views

## 5. Probe Orchestration

Implemented in:

- `src/memory_eval/eval_core/probes.py`
- `src/memory_eval/eval_core/engine.py`

### Real implementation behavior

1. The three probes are executed in parallel using `ThreadPoolExecutor`
2. Probe inputs are independent
3. Responsibility coupling happens only after probe completion

### Attribution merge rule

Currently one explicit post-merge reconciliation rule is implemented:

1. if encoding state is `MISS`
2. and retrieval defects contain `RF`
3. then `RF` is suppressed

This matches the intended attribution logic that retrieval failure should not be blamed when the source was never stored.

## 6. Encoding Probe

Implemented in `src/memory_eval/eval_core/encoding.py`.

### Actual input

1. `question`
2. `memory_corpus`
3. `f_key`
4. `task_type`
5. `evidence_texts`

### Actual execution steps

1. Export full memory through adapter
2. Optionally call `hybrid_retrieve_candidates(...)`
3. Otherwise call adapter `find_memory_records(...)`
4. In non-strict mode only, evaluator may fallback to a global rule scan
5. Call `llm_judge_encoding_storage(...)`
6. If strict mode is on:
   - LLM failure => raise
   - invalid state => raise
   - no rule fallback allowed

### Rule path

There is still a rule-mode implementation for:

1. fact matching
2. ambiguity detection
3. corruption categorization

But in the current strict default config this path is intentionally blocked if LLM judgement fails.

### Encoding states

1. `EXIST`
2. `MISS`
3. `CORRUPT_AMBIG`
4. `CORRUPT_WRONG`
5. `DIRTY`

### Encoding defects

1. `EM`
2. `EA`
3. `EW`
4. `DMP`

## 7. Retrieval Probe

Implemented in `src/memory_eval/eval_core/retrieval.py`.

### Actual input

1. `question`
2. `C_original`
3. `f_key`
4. `task_type`
5. `evidence_texts`

### Actual metrics

Implemented in `src/memory_eval/eval_core/utils.py`:

1. `rank_and_hit_indices(...)`
2. `token_overlap_snr(...)`

### POS path

1. Compute `rank`
2. Compute `snr`
3. Call `llm_judge_retrieval_quality_pos(...)`
4. Use LLM state as primary state source in strict mode
5. Merge `LATE` / `NOI` based on thresholds if needed

### NEG path

1. Call `llm_judge_retrieval_quality_neg(...)`
2. If strict mode is on, LLM failure raises
3. In relaxed mode only, score threshold fallback may be used

### Retrieval states

1. `HIT`
2. `MISS`
3. `NOISE`

### Retrieval defects

1. `RF`
2. `LATE`
3. `NOI`
4. `NIR`

## 8. Generation Probe

Implemented in `src/memory_eval/eval_core/generation.py`.

### Actual input

1. `question`
2. `oracle_context`
3. `answer_online`
4. `answer_oracle`
5. `answer_gold`
6. `task_type`

### Actual execution steps

1. Adapter generates `A_oracle`
2. Adapter generates `A_online`
3. Eval layer runs two LLM judges:
   - `llm_judge_generation_answer(...)`
   - `llm_judge_generation_comparison(...)`
4. Strict mode requires both judgments to succeed
5. Output includes comparative evidence:
   - `online_correct`
   - `oracle_correct`
   - `comparative_judgement`

### Generation states

1. `PASS`
2. `FAIL`

### Generation defects

1. `GH`
2. `GF`
3. `GRF`

## 9. LLM Assist Layer

Implemented in `src/memory_eval/eval_core/llm_assist.py`.

### What exists now

The project already has dedicated structured LLM judges for:

1. encoding storage judgement
2. retrieval quality for POS
3. retrieval quality for NEG
4. local fact match support
5. oracle answer correctness
6. tri-answer generation comparison

### Important implementation fact

The helper expects strict JSON and strips markdown fences if the model wraps JSON in code blocks.
This is a practical stabilization step that was already added.

## 10. Pipeline Layer

Implemented in `src/memory_eval/pipeline/runner.py`.

### Current behavior

1. Build eval samples
2. Cache adapter runtime by `sample_id`
3. For each sample:
   - ingest conversation if needed
   - run strict parallel evaluator with adapters
4. Collect:
   - `results`
   - `errors`
   - `summary`
   - `adapter_manifest`

### Important current property

This pipeline is full-evaluation oriented, not "baseline-first incorrect-only" oriented.
That is why a second script was later added for O-Mem experiments.

## 11. Experiment Runner for O-Mem

Implemented in `scripts/run_omem_two_stage_eval.py`.

### What it actually does

1. Build first N questions from LOCOMO
2. For each question:
   - call O-Mem online answer
   - call a separate correctness judge LLM
   - bucket into `correct` / `incorrect`
3. Run attribution on:
   - all incorrect samples
   - sampled correct samples
4. Save all hyperparameters and model names into output report

This script is the first real implementation of the user's desired two-stage workflow.

## 12. Bottom-Line Assessment of the Eval Layer

### What is already solid

1. The evaluation layer is genuinely modular
2. The three probes are truly parallel
3. POS/NEG are explicitly separated
4. Evidence-first output is implemented
5. Strict execution semantics are implemented in config and probe code
6. Adapter decoupling is real, not superficial

### What is still not fully solved

1. Some rule fallback paths still exist in source, even though strict mode blocks them by default
2. The two-stage workflow is implemented only as an experiment script, not as the default main pipeline
3. Runtime stability still depends heavily on external memory-system behavior and LLM output quality

## Final Conclusion

The evaluation layer itself is already substantially implemented and aligned with the intended architecture:

- dataset normalization
- strict contracts
- parallel three-probe evaluation
- defect attribution merging
- adapter decoupling
- strict LLM-required execution
- report generation

The main remaining uncertainty is no longer the eval-core design.
The main uncertainty is whether a concrete external memory system, especially O-Mem, can run stably enough under this framework.
