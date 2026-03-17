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

### Additional User Constraints Captured

1. Three probes must be fully parallel for efficiency.
2. f_key LLM instability is acknowledged and deferred from optimization scope.
3. NEG is defined by "should abstain", and should be handled accordingly in probe logic.

### Additional Assistant Actions Captured

1. Implemented `eval_core` package with parallel probe engine.
2. Added adapter protocol contracts and evidence-first output schema.
3. Added runtime query resolution registry interfaces for evaluator integration.
4. Added v0.2.0 coding specification and iteration record.

## 2026-03-17 (Encoding-focused iteration)

### User Instructions Captured

1. Focus only on encoding probe implementation.
2. Encoding probe input must explicitly be `Q + M + F_key`.
3. `M` must come from adapter-layer interfaces over real memory-system storage.
4. Provide independent test script to verify encoding probe correctness.

### Assistant Actions Captured

1. Added `EncodingAdapterProtocol` with full-memory export and adapter-side matching APIs.
2. Implemented encoding probe module with evidence-first outputs.
3. Added independent test script `scripts/test_encoding_probe.py`.
4. Fixed short-token false-positive matching bug via directed fact matching.
5. Re-validated compile and test pass.

## 2026-03-17 (Retrieval-focused iteration)

### User Instructions Captured

1. Focus on retrieval probe implementation with inputs `Q + C_original + F_key`.
2. Align implementation with `docs/最终指标.md`.
3. Re-check encoding layer consistency against final metric spec.
4. Retrieval probe may use advanced LLM-assisted judgement.
5. Add retrieval test script.
6. Improve encoding with optional LLM-assisted judgement and update tests/README.

### Assistant Actions Captured

1. Added dedicated retrieval probe module and adapter protocol.
2. Added optional LLM-assisted retrieval noise judgement.
3. Added optional LLM-assisted encoding fact-match judgement.
4. Added retrieval independent test script and ran validations.
5. Added alignment-check documentation and updated versioning docs.

## 2026-03-17 (Generation-focused iteration)

### User Instructions Captured

1. Focus this step on generation probe implementation.
2. Follow `docs/最终指标.md` logic:
   - Use oracle context to generate `A_oracle`
   - Compare `A_oracle` and `A_gold` (LLM-assisted allowed)
3. Re-review all three probes for potential vulnerabilities.

### Assistant Actions Captured

1. Added generation adapter protocol and generation module.
2. Added optional LLM-assisted generation judgement.
3. Added independent generation test script.
4. Added full three-probe vulnerability review document.
5. Updated README/changelog/version/iteration docs.
