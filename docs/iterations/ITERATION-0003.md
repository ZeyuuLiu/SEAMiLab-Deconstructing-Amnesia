# Iteration 0003 - Encoding Probe Focus

## Goal

Implement and validate encoding probe with explicit adapter-backed memory access.

## Done

1. Added `EncodingAdapterProtocol` for full-memory export and record matching.
2. Added encoding-only evaluator APIs:
   - `evaluate_encoding_probe(...)`
   - `evaluate_encoding_probe_with_adapter(...)`
3. Added independent script `scripts/test_encoding_probe.py`.
4. Added detailed implementation doc:
   - `docs/architecture/encoding-probe-implementation-v0.2.1.md`
5. Fixed short-token matching false-positive issue.

## Validation

- [x] compile checks pass
- [x] independent encoding script passes all designed cases

## Notes

This iteration intentionally focuses only on encoding probe, per requirement.
