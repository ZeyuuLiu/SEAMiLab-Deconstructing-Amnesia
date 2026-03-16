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
