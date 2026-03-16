# Iteration 0002 - Parallel Three-Probe Core

## Goal

Implement first runnable version of evaluation core with fully parallel probe execution and adapter integration contracts.

## Completed

1. Added `eval_core` package with data contracts, probe logic, and parallel engine.
2. Added runtime adapter protocol interface for future memory-system integration.
3. Added evidence-first attribution result schema.
4. Updated LOCOMO builder for runtime query resolve interfaces.
5. Updated docs and README for v0.2.0.

## Validation

- [x] `python -m compileall src scripts`
- [x] demo script runs in `rule` mode
- [x] demo script runs in `llm` mode
- [x] query / question_id resolution works

## Notes

1. Probes are executed concurrently (`ThreadPoolExecutor`).
2. RF suppression is done in post-merge reconciliation if encoding is MISS.
3. LLM f_key quality optimization is deferred by design, as requested.
