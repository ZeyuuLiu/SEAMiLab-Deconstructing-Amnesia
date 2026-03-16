# Memory Eval Framework

A clean-slate evaluation framework for long-term memory systems, designed with strict separation between:

1. Evaluation Core (framework-owned logic)
2. Adapter Layer (system-specific integration)

## Current Scope (Iteration 0.3.0)

This iteration focuses on:

1. Project bootstrap with strict versioning artifacts
2. A small demo that builds evaluation samples from `locomo10.json`
3. Time-aware oracle context and query lookup interfaces for runtime integration
4. Parallel three-probe evaluation core with adapter protocol contracts
5. Dedicated encoding probe and retrieval probe implementations with adapter-side contracts
6. Independent probe test scripts for encoding/retrieval

This is still a step-by-step implementation stage, not a full production pipeline.

## Principles

1. Step-by-step iteration
2. Every iteration is traceable with documents
3. No hidden assumptions: requirements and design notes are recorded
4. Attribution outputs must include evidence (implemented in future iterations, designed now)

## Project Layout

```text
memory-eval-framework/
  README.md
  VERSION
  CHANGELOG.md
  pyproject.toml
  .gitignore
  docs/
    PROJECT_LOG.md
    traceability/
      REQUIREMENTS.md
      DESIGN_NOTES.md
    iterations/
      ITERATION-0001.md
  src/
    memory_eval/
      __init__.py
      dataset/
        __init__.py
        locomo_builder.py
  scripts/
    demo_build_locomo_samples.py
  data/
    locomo10.json
```

## Quick Start

### 1) Python setup

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -e .
```

### 2) Run the LOCOMO demo

```powershell
python scripts/demo_build_locomo_samples.py --limit 5 --fkey-source rule
```

Expected:

1. prints dataset summary
2. writes demo output to `outputs/demo_locomo_samples.json`

You can also use LLM to extract `f_key`:

```powershell
python scripts/demo_build_locomo_samples.py --limit 5 --fkey-source llm
```

### 3) Resolve one query to evaluation sample

```powershell
python scripts/demo_build_locomo_samples.py --limit 5 --query "When did Caroline go to the LGBTQ support group?"
```

Or by question id:

```powershell
python scripts/demo_build_locomo_samples.py --question-id "conv-26:0"
```

## Runtime Interfaces (for future evaluator calls)

Provided in `src/memory_eval/dataset/locomo_builder.py`:

1. `build_locomo_eval_samples(...)`
2. `build_locomo_sample_registry(...)`
3. `LocomoSampleRegistry.get_by_question_id(question_id)`
4. `LocomoSampleRegistry.find_by_query(query, sample_id=None)`

These interfaces are intended for the future flow where a memory system submits one query to evaluator and evaluator resolves:

- `answer_gold`
- `task_type`
- `f_key`
- `oracle_context`
- evidence fields

## Evaluation Core (Parallel Three Probes)

Implemented under `src/memory_eval/eval_core/`:

1. `ParallelThreeProbeEvaluator` (parallel enc/ret/gen execution)
2. `EvalAdapterProtocol` (adapter integration contract)
3. Core data contracts:
   - `EvalSample`
   - `RetrievedItem`
   - `AdapterTrace`
   - `ProbeResult`
   - `AttributionResult`
   - `EvaluatorConfig`

Parallel design:

1. Encoding probe uses `memory_view + f_key`
2. Retrieval probe uses `retrieved_items + f_key + thresholds`
3. Generation probe uses `question + answer_gold + oracle_context + answer_oracle`

All three are independent and run concurrently. Attribution reconciliation (e.g., RF suppression when encoding is MISS) is performed after probe completion.

Minimal usage:

```python
from memory_eval.eval_core import ParallelThreeProbeEvaluator, EvaluatorConfig

evaluator = ParallelThreeProbeEvaluator(EvaluatorConfig(tau_rank=5, tau_snr=0.2))
result = evaluator.evaluate(sample, trace)
print(result.to_dict())
```

Output includes states, defect union, and evidence-by-probe blocks.

## Encoding Probe (v0.2.1 focus)

This iteration deepens encoding probe implementation with explicit adapter integration.

### Required input

1. `Q` (question)
2. `M` (full memory corpus from memory system)
3. `F_key` (key facts)

### How `M` is obtained

`M` is fetched via adapter protocol (not by evaluator internals):

1. `export_full_memory(run_ctx)`
2. `find_memory_records(run_ctx, query, f_key, memory_corpus)`

### APIs

1. `evaluate_encoding_probe_with_adapter(sample, adapter, run_ctx)`
2. `evaluate_encoding_probe(input, candidate_records=None)`

### Independent test

```powershell
python scripts/test_encoding_probe.py
```

Detailed doc:

1. `docs/architecture/encoding-probe-implementation-v0.2.1.md`

LLM-assisted encoding option:

1. Set `EvaluatorConfig(use_llm_assist=True, llm_api_key=..., llm_base_url=...)`
2. Encoding probe can use LLM to assist key-fact matching when rule matching is uncertain.

## Retrieval Probe (v0.3.0 focus)

### Required input

1. `Q` (question)
2. `C_original` (ordered retrieval result)
3. `F_key` (from LOCOMO sample builder)

### Adapter interface

1. `RetrievalAdapterProtocol.retrieve_original(run_ctx, query, top_k)`

### APIs

1. `evaluate_retrieval_probe(input, cfg, s_enc=None)`
2. `evaluate_retrieval_probe_with_adapter(sample, adapter, run_ctx, cfg, top_k, s_enc=None)`

### Independent test

```powershell
python scripts/test_retrieval_probe.py
```

LLM-assisted retrieval option:

1. Set `EvaluatorConfig(use_llm_assist=True, llm_api_key=..., llm_base_url=...)`
2. Retrieval probe can invoke LLM judgement for NEG noise detection.

Detailed docs:

1. `docs/architecture/retrieval-probe-implementation-v0.3.0.md`
2. `docs/architecture/encoding-alignment-check-v0.3.0.md`

## Time-aware Context Format

For evidence/oracle context, each line is:

`<date_time> | <speaker>: <text>`

Example:

`1:56 pm on 8 May, 2023 | Caroline: I went to a LGBTQ support group yesterday and it was so powerful.`

## API Key / Base URL

The demo reads `configs/keys.local.json`.
When `--fkey-source llm` is used, the demo invokes OpenAI-compatible `/chat/completions`.

## Versioning

1. Code version: `VERSION` file (SemVer)
2. Iteration notes: `docs/iterations/`
3. Requirement and design traceability: `docs/traceability/`
4. Change history: `CHANGELOG.md`

## Design Docs

1. `docs/architecture/three-layer-probe-implementation-plan.md`
2. `docs/traceability/DESIGN_NOTES.md`
