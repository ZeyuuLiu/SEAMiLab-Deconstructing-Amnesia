# Iteration 0005 - Generation Probe Focus

## Goal

Implement generation probe according to final metric requirements and perform a full three-probe review.

## Completed

1. Added generation probe module and adapter protocol.
2. Implemented adapter-based oracle answer generation path.
3. Added optional LLM-assisted generation judgement.
4. Added independent generation test script.
5. Performed and documented cross-layer vulnerability review.

## Validation

- [x] compile checks pass
- [x] `scripts/test_encoding_probe.py` pass
- [x] `scripts/test_retrieval_probe.py` pass
- [x] `scripts/test_generation_probe.py` pass

## Notes

1. Generation input now explicitly includes `C_oracle`.
2. `A_oracle` is produced via adapter protocol for original system model path.
3. LLM judgement remains optional; rule fallback is always available.
