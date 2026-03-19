# Three-Probe Full Pipeline v0.5.0

## Goal

Provide one complete evaluation flow:

1. Build eval samples from LOCOMO
2. Use adapter to build runtime context and expose three probe inputs
3. Run encoding/retrieval/generation probes
4. Merge attribution and export final report

## Implementation

Core pipeline:

1. `src/memory_eval/pipeline/runner.py`
2. `ThreeProbeEvaluationPipeline.run(adapter)`

CLI:

1. `scripts/run_eval_pipeline.py`

## Required adapter methods

1. `ingest_conversation(sample_id, conversation)`
2. `export_full_memory(run_ctx)`
3. `find_memory_records(run_ctx, query, f_key, memory_corpus)`
4. `retrieve_original(run_ctx, query, top_k)`
5. `generate_oracle_answer(run_ctx, query, oracle_context)`

## Output contract

Pipeline writes one JSON report:

1. `config`: run configuration
2. `summary`:
   - total
   - task_counts
   - defect_counts
   - state_counts by probe
3. `results`: per-question attribution records

## Validation

1. `scripts/test_eval_pipeline_mock.py` provides end-to-end smoke test with a mock adapter.
