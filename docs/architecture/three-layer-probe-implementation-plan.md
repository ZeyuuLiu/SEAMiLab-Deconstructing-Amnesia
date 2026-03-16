# Three-Layer Probe Implementation Plan

## 1. Goal

Implement a memory-system-agnostic evaluator with three probes:

1. Encoding probe (`P_enc`)
2. Retrieval probe (`P_ret`)
3. Generation probe (`P_gen`)

The evaluator must output:

1. defect set (`D_total`)
2. machine-auditable evidence for each defect decision

## 2. Is this direction correct?

Yes. The framework split is correct:

1. Dataset layer builds standardized eval samples
2. Adapter layer provides system observations (`M_view`, `C_original`, answers)
3. Evaluation core performs attribution independent of system internals

This separation is the right base for cross-system comparability and debugging.

## 3. Required Input Contracts

### 3.1 Dataset-side sample (`EvalSample`)

Must include:

1. `question`, `answer_gold`, `task_type`
2. `f_key`
3. `oracle_context`
4. evidence fields:
   - `evidence_ids`
   - `evidence_texts`
   - `evidence_with_time`

### 3.2 Adapter-side trace (`AdapterTrace`)

Must include:

1. `memory_view` (for encoding check)
2. `retrieved_items` (for retrieval check)
3. `answer_online`
4. `answer_oracle`
5. optional `raw_trace`

## 4. Probe-by-Probe Implementation

### 4.1 Encoding Probe (`P_enc`)

Question:

Is key fact in memory view, and is it correct/clean?

State space:

1. `EXIST`
2. `MISS`
3. `CORRUPT_AMBIG`
4. `CORRUPT_WRONG`
5. `DIRTY` (NEG only)

Defects:

1. `MISS -> EM`
2. `CORRUPT_AMBIG -> EA`
3. `CORRUPT_WRONG -> EW`
4. `DIRTY -> DMP`

Evidence to record:

1. matched memory ids/text
2. unmatched `f_key` items
3. ambiguity markers (pronouns/deictic forms)
4. contradiction samples (if any)

### 4.2 Retrieval Probe (`P_ret`)

Question:

Did the system retrieval bring key facts to effective positions?

State space:

1. `HIT`
2. `MISS`
3. `NOISE` (NEG only)

Defects:

1. `MISS` with `S_enc != MISS` -> `RF`
2. `HIT` with `rank > tau_rank` -> `LATE`
3. `HIT` with `snr < tau_snr` -> `NOI`
4. `NOISE` -> `NIR`

Attributes:

1. `rank_index`
2. `snr`

Evidence to record:

1. first hit position
2. hit items and matched `f_key` items
3. top-k noise candidates
4. exact numerator/denominator used by `snr`

### 4.3 Generation Probe (`P_gen`)

Question:

Given oracle context, can model still fail?

State space:

1. `PASS`
2. `FAIL`

FAIL subclasses:

1. `GH` (NEG but not abstaining)
2. `GF` (POS, answer not grounded in oracle context)
3. `GRF` (POS, grounded but reasoning wrong)

Evidence to record:

1. judge decision and reason
2. abstain detection details
3. grounding overlap or rationale
4. answer-vs-gold mismatch summary

## 5. Defect Union and Evidence-First Output

For each sample:

1. `D_total = D_enc ∪ D_ret ∪ D_gen`
2. output `attribution_evidence` object with:
   - `enc_evidence`
   - `ret_evidence`
   - `gen_evidence`
   - `decision_trace` (rule trigger logs)

This directly satisfies the requirement that attribution must provide reasons/evidence.

## 6. How to implement bottom-up

### Step A (minimal runnable)

1. Define immutable data contracts (`EvalSample`, `AdapterTrace`, `ProbeResult`, `AttributionResult`)
2. Implement deterministic rule mode for all three probes
3. Persist `traces.jsonl` with evidence blocks

### Step B (quality hardening)

1. Add consistent normalization and matching utilities
2. Add edge-case handling (missing evidence ids, empty retrieval, malformed answers)
3. Add deterministic unit tests for each defect rule

### Step C (metrics and report)

1. compute atomic/system metrics
2. include denominator auditing
3. provide defect distribution + evidence examples in report

## 7. Runtime integration interface (important)

When a memory system says "this query should be evaluated", evaluator should call:

1. `LocomoSampleRegistry.find_by_query(query, sample_id=None)` or
2. `LocomoSampleRegistry.get_by_question_id(question_id)`

Then evaluator obtains:

1. `answer_gold`
2. `task_type`
3. `f_key`
4. `oracle_context`
5. evidence fields

This satisfies your requested future call path.

## 8. Current design risks and mitigations

Risk 1:

Question text collisions across episodes.

Mitigation:

Use `(sample_id, question)` or `question_id` whenever available.

Risk 2:

`f_key` quality instability in LLM mode.

Mitigation:

Keep `rule` as deterministic baseline and record `f_key_mode` in evidence.

Risk 3:

NEG label inference errors.

Mitigation:

Keep traceable label derivation in `construction_evidence`; later add explicit label override config.
