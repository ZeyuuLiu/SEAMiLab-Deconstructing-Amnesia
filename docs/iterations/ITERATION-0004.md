# Iteration 0004 - Retrieval Probe Focus + Encoding LLM Assist

## Goal

Focus on retrieval probe implementation aligned with `docs/最终指标.md`, and enhance encoding probe with optional LLM assistance.

## Completed

1. Added dedicated retrieval probe module and adapter protocol.
2. Added optional LLM-assisted retrieval noise judgement.
3. Added optional LLM-assisted encoding fact match judgement.
4. Added retrieval independent test script.
5. Added alignment documentation between encoding implementation and final metric specification.

## Validation

- [x] compile checks pass
- [x] `scripts/test_encoding_probe.py` passes
- [x] `scripts/test_retrieval_probe.py` passes

## Notes

1. Retrieval probe defect mapping follows final metric rules:
   - `RF` only when `s_enc != MISS`
2. LLM-assist is optional; rule mode remains deterministic fallback.
