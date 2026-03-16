# Encoding Alignment Check v0.3.0

## Compared Documents

1. `docs/最终指标.md`
2. current encoding implementation (`src/memory_eval/eval_core/encoding.py`)

## Alignment Result

### Aligned points

1. Input contract is explicit: `Q + M + F_key`
2. `M` is adapter-exported, not evaluator-internal
3. State space matches target:
   - `EXIST`, `MISS`, `CORRUPT_AMBIG`, `CORRUPT_WRONG`, `DIRTY`
4. Defect mapping matches:
   - `EM`, `EA`, `EW`, `DMP`

### Required clarification applied

1. NEG clean case:
   - we keep `state=MISS`, `defects=[]`
   - this is compatible with negative-scene table where no pollution/no hallucination can be clean
2. Added optional LLM-assisted fact matching to improve ambiguous boundary handling.

### Bug found and fixed during check

1. False-positive short-token match (`he` inside `she`) caused incorrect `EXIST`.
2. Fixed by directed fact matching with token-level logic for short facts.

## Conclusion

Encoding layer is now consistent with final metric specification for current rule scope.
Further improvements can focus on better hallucinated-memory detection for `DIRTY` using richer adapter signals.
