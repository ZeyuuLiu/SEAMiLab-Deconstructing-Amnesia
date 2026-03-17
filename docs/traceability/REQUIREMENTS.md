# Requirements Traceability (Iteration 0.1.0)

## R-001: Record requirements and understanding

- Status: Done
- Evidence:
  - `docs/PROJECT_LOG.md`
  - `docs/traceability/DESIGN_NOTES.md`

## R-002: Attribution must include evidence

- Status: Designed (not implemented in engine yet)
- Design hook:
  - sample schema includes `evidence_ids`, `evidence_texts`, `oracle_context`, `construction_evidence`

## R-003: Step-by-step iterative delivery

- Status: Done for this iteration
- Evidence:
  - `docs/iterations/ITERATION-0001.md`
  - small isolated demo only

## R-004: Build LOCOMO evaluation sample demo

- Status: Done
- Evidence:
  - `src/memory_eval/dataset/locomo_builder.py`
  - `scripts/demo_build_locomo_samples.py`

## R-005: Strict project version control discipline

- Status: Done (bootstrap level)
- Evidence:
  - `VERSION`
  - `CHANGELOG.md`
  - `docs/traceability/VERSION_POLICY.md`

## R-006: Three probes must run in parallel

- Status: Done
- Evidence:
  - `src/memory_eval/eval_core/engine.py`
  - `src/memory_eval/eval_core/probes.py`

## R-007: Runtime query-resolve interface for evaluator calls

- Status: Done
- Evidence:
  - `src/memory_eval/dataset/locomo_builder.py`
  - `LocomoSampleRegistry.find_by_query(...)`
  - `LocomoSampleRegistry.get_by_question_id(...)`

## R-008: Keep README continuously updated

- Status: Done for iteration 0.2.0
- Evidence:
  - `README.md`

## R-009: Encoding probe must explicitly use Q + M + F_key

- Status: Done
- Evidence:
  - `src/memory_eval/eval_core/encoding.py`
  - `src/memory_eval/eval_core/adapter_protocol.py`

## R-010: Independent test script for encoding layer

- Status: Done
- Evidence:
  - `scripts/test_encoding_probe.py`

## R-011: Retrieval probe implementation aligned with 最终指标

- Status: Done
- Evidence:
  - `src/memory_eval/eval_core/retrieval.py`
  - `docs/architecture/retrieval-probe-implementation-v0.3.0.md`

## R-012: Provide retrieval probe independent test script

- Status: Done
- Evidence:
  - `scripts/test_retrieval_probe.py`

## R-013: Check encoding alignment with final metric spec

- Status: Done
- Evidence:
  - `docs/architecture/encoding-alignment-check-v0.3.0.md`

## R-014: Generation probe implemented with oracle-context path

- Status: Done
- Evidence:
  - `src/memory_eval/eval_core/generation.py`
  - `src/memory_eval/eval_core/adapter_protocol.py`

## R-015: Generation probe independent test script

- Status: Done
- Evidence:
  - `scripts/test_generation_probe.py`

## R-016: Full three-probe vulnerability review document

- Status: Done
- Evidence:
  - `docs/architecture/three-probe-vulnerability-review-v0.4.0.md`
