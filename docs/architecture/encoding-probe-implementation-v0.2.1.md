# Encoding Probe Implementation v0.2.1

## 1. Scope

This document only covers Encoding Probe (`P_enc`) implementation.
It intentionally does not change retrieval/generation logic in this iteration.

## 2. Explicit Input Definition

Encoding probe input is:

1. `Q` (current question)
2. `M` (full memory corpus from target memory system)
3. `F_key` (key facts for current question)

In code:

1. `EncodingProbeInput.question`
2. `EncodingProbeInput.memory_corpus`
3. `EncodingProbeInput.f_key`

## 3. Adapter-Layer Integration (Important)

`M` is not directly owned by evaluator. It is provided via adapter APIs:

1. `export_full_memory(run_ctx)`:
   - Export full memory corpus from memory-system storage.
2. `find_memory_records(run_ctx, query, f_key, memory_corpus)`:
   - Adapter performs script-level traversal/matching in system-specific backend.

This enforces your required architecture:

1. evaluator owns diagnosis logic
2. adapter owns storage traversal details

## 4. Probe State / Defect Mapping

### POS

1. `EXIST` -> `[]`
2. `MISS` -> `[EM]`
3. `CORRUPT_AMBIG` -> `[EA]`
4. `CORRUPT_WRONG` -> `[EW]`

### NEG

1. `DIRTY` -> `[DMP]`
2. clean NEG -> `MISS` with no defect

## 5. Evidence Output

Encoding result includes evidence fields:

1. `memory_source` (`adapter.export_full_memory`)
2. `candidate_count`
3. `matched_facts`
4. `unmatched_facts`
5. `ambiguity_hits` (when applicable)
6. textual `reason`

This supports traceable attribution decisions.

## 6. Implementation Files

1. `src/memory_eval/eval_core/adapter_protocol.py`
   - `EncodingAdapterProtocol`
2. `src/memory_eval/eval_core/encoding.py`
   - `evaluate_encoding_probe_with_adapter(...)`
   - `evaluate_encoding_probe(...)`
3. `scripts/test_encoding_probe.py`
   - independent test runner

## 7. Independent Test Script

Run:

```powershell
python scripts/test_encoding_probe.py
```

Covered cases:

1. EXIST
2. MISS
3. CORRUPT_AMBIG
4. CORRUPT_WRONG
5. DIRTY (NEG)
6. clean NEG

If any mismatch exists, script exits non-zero and prints failure evidence.

## 8. Review Checklist Used

1. Input contract explicitly includes `Q + M + F_key`
2. `M` acquisition explicitly goes through adapter interface
3. Probe output includes evidence payload
4. NEG handling follows abstain-definition alignment
5. Independent script validates core state/defect paths
