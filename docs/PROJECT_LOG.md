# Project Log

This document is a permanent high-level project log for backtracking decisions.

## 2026-03-16

### User Instructions Captured

1. Build a reusable evaluation layer that can adapt to many memory systems.
2. Keep evaluation logic decoupled from system-specific integration.
3. Use `locomo10.json` as the first dataset.
4. Build `F_key` and `C_oracle` from LOCOMO evidence links.
5. For negative samples: use empty `F_key` and irrelevant/no-memory oracle context.
6. Provide evidence along with attribution conclusions.
7. Iterate slowly and verify each step against requirements.
8. In this iteration, only bootstrap new project and build a small LOCOMO sample-construction demo.

### Assistant Understanding Captured

1. This iteration is intentionally narrow:
   - project structure
   - version-control artifacts
   - locomo sample-construction proof-of-feasibility
2. Full attribution engine and full adapter implementations are out of scope for this iteration.
3. Evidence-carrying output should be designed now in sample schema for future attribution support.

## 2026-03-17

### User Instructions Captured

1. Oracle context should include time + speaker + text, but not session prefix tags.
2. Provide callable interfaces so evaluator can resolve one runtime query into eval sample fields.
3. Keep README continuously updated.
4. Write a concrete local implementation plan for three-layer probes before coding deeper.

### Assistant Actions Captured

1. Updated LOCOMO time-aware evidence format.
2. Added `LocomoSampleRegistry` lookup interfaces (`query` / `question_id`).
3. Added three-layer implementation plan doc under `docs/architecture/`.
4. Updated README and traceability notes.
