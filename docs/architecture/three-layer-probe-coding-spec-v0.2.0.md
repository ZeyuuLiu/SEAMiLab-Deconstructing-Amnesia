# Three-Layer Probe Coding Spec v0.2.0

## 1. Framework Thought Process (Why this is correct)

This architecture is correct for your objective because:

1. It isolates evaluation logic from memory-system implementation details.
2. It enables cross-system comparability under one defect taxonomy.
3. It forces evidence-backed attribution instead of label-only outputs.
4. It supports probe-level parallelism for efficiency.

In short:

1. Adapter provides observations.
2. Evaluator diagnoses.
3. Report summarizes.

No single layer leaks internal assumptions into another.

## 2. Parallel Probe Execution Plan

The three probes are independent by input, so they run concurrently:

1. Encoding probe:
   - input: `M_view`, `f_key`, `task_type`
2. Retrieval probe:
   - input: `retrieved_items`, `f_key`, `task_type`, thresholds
3. Generation probe:
   - input: `answer_oracle`, `answer_gold`, `oracle_context`, `task_type`

Post-merge reconciliation:

1. If `S_enc == MISS`, suppress `RF`.
2. Merge defects using stable order for deterministic outputs.

## 3. NEG Strategy Clarification

Per your instruction:

1. NEG means "should abstain".
2. Labeling is based on abstention expectation, not positive evidence completeness.
3. Generation NEG failure is `GH` when not abstaining.

This is implemented as first-class rule path in generation probe.

## 4. f_key Strategy Clarification

Current implementation:

1. Supports `rule` and `llm` source.
2. LLM instability is acknowledged and deferred from optimization scope.
3. Rule mode remains deterministic baseline.

Later optimization path:

1. Adapter-specific prompts
2. memory-system-specific extraction strategy
3. offline calibration sets for f_key quality

## 5. Evidence-First Attribution Output

Every probe outputs:

1. state
2. defects
3. probe evidence
4. optional attributes (rank/snr/overlap etc.)

Final result includes:

1. `states`
2. `defects` union
3. `attribution_evidence`:
   - `enc_evidence`
   - `ret_evidence`
   - `gen_evidence`
   - `decision_trace`

## 6. Bottom-Up Implementation Guidance

### Step 1 (done in v0.2.0)

1. Core contracts
2. Parallel evaluator skeleton
3. Rule-based probes
4. Dataset runtime lookup interfaces

### Step 2 (next)

1. Add adapter implementation examples (mock + one real)
2. Add pipeline runner around evaluator
3. Add jsonl trace writer

### Step 3

1. Metrics module
2. report renderer
3. regression tests

## 7. Implementation Mapping

1. `src/memory_eval/eval_core/models.py`
2. `src/memory_eval/eval_core/adapter_protocol.py`
3. `src/memory_eval/eval_core/probes.py`
4. `src/memory_eval/eval_core/engine.py`
5. `src/memory_eval/eval_core/utils.py`

Runtime sample resolution:

1. `src/memory_eval/dataset/locomo_builder.py`
2. `build_locomo_sample_registry(...)`

## 8. Known Limits in v0.2.0

1. Rule-mode generation judge is heuristic.
2. Encoding DIRTY logic for NEG is conservative heuristic and should be improved with better adapter signals.
3. Full runner/report is not finalized in this version.
