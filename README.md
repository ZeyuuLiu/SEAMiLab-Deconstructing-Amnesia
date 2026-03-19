# Memory Eval Framework

A clean-slate evaluation framework for long-term memory systems, designed with strict separation between:

1. Evaluation Core (framework-owned logic)
2. Adapter Layer (system-specific integration)

## Current Scope (Iteration 0.6.2)

This iteration focuses on:

1. Project bootstrap with strict versioning artifacts
2. A small demo that builds evaluation samples from `locomo10.json`
3. Time-aware oracle context and query lookup interfaces for runtime integration
4. Parallel three-probe evaluation core with adapter protocol contracts
5. Dedicated encoding probe and retrieval probe implementations with adapter-side contracts
6. Independent probe test scripts for encoding/retrieval/generation
7. `system/` directory for baseline memory-system source code
8. LLM assist enabled by default for all three probes
9. Adapter-aware unified evaluator entrypoint for direct protocol integration
10. O-Mem adapter compliance audit script and audit documentation
11. End-to-end evaluation pipeline (`dataset -> adapter -> three probes -> report`)
12. Bilingual real-run report of O-Mem on LOCOMO sample0
13. Three-probe redesign implementation (hybrid + LLM-judge)
14. Bilingual fixed adapter interface specification
15. Strict full-path fail-fast evaluation policy (LLM-required)
16. Registry-based per-memory-system adapter creation (`one system -> one adapter module`)
17. O-Mem native retrieval->generation online path integration in real mode

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
  system/
    .keep
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

Adapter-aware usage:

```python
result = evaluator.evaluate_with_adapters(
    sample=sample,
    run_ctx=run_ctx,
    encoding_adapter=enc_adapter,
    retrieval_adapter=ret_adapter,
    generation_adapter=gen_adapter,
    top_k=5,
)
```

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

## Generation Probe (v0.4.0 focus)

### Required input

1. `Q`
2. `C_oracle`
3. `A_oracle` (from original memory-system model under oracle context)
4. `A_gold`
5. `task_type`

### Adapter interface

1. `GenerationAdapterProtocol.generate_oracle_answer(run_ctx, query, oracle_context)`

### APIs

1. `evaluate_generation_probe(input, cfg)`
2. `evaluate_generation_probe_with_adapter(sample, adapter, run_ctx, cfg)`

### Independent test

```powershell
python scripts/test_generation_probe.py
```

### Optional LLM-assisted judgement

Set:

1. `EvaluatorConfig(use_llm_assist=True, llm_api_key=..., llm_base_url=..., llm_model=...)`

The probe can call LLM to judge correctness and subtype (`GH/GF/GRF`) while preserving rule fallback.

### Default behavior update

`use_llm_assist` is now enabled by default in `EvaluatorConfig`.
If no valid key/base_url is provided or LLM call fails, probes automatically fallback to rule-based logic.

Detailed docs:

1. `docs/architecture/generation-probe-implementation-v0.4.0.md`
2. `docs/architecture/three-probe-vulnerability-review-v0.4.0.md`
3. `docs/architecture/llm-assist-strategy-bilingual-v0.4.1.md`

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

## O-Mem Adapter Audit

To check whether `system/O-Mem` is compliant with eval adapter protocols in this repo:

```powershell
python scripts/audit_o_mem_adapter.py
```

This script reports:

1. static protocol-method compliance hits
2. runtime importability in current environment
3. overall readiness conclusion

## Full Evaluation Pipeline

Run full three-probe pipeline on LOCOMO with your adapter implementation:

```powershell
python scripts/run_eval_pipeline.py `
  --memory-system o_mem `
  --adapter-config-json "{\"use_real_omem\":true,\"api_key\":\"...\",\"base_url\":\"...\"}" `
  --dataset data/locomo10.json `
  --output outputs/eval_pipeline_results.json `
  --limit 10
```

Or load a custom adapter class directly:

```powershell
python scripts/run_eval_pipeline.py `
  --adapter-module your_adapter_module `
  --adapter-class YourAdapterClass `
  --dataset data/locomo10.json `
  --output outputs/eval_pipeline_results.json `
  --limit 10
```

Adapter must implement:

1. `ingest_conversation(...)`
2. `export_full_memory(...)`
3. `find_memory_records(...)`
4. `retrieve_original(...)`
5. `generate_oracle_answer(...)`
6. Recommended: `generate_online_answer(...)` (required by strict generation mode)

Strict policy defaults:

1. LLM judgement required for three probes (`require_llm_judgement=True`)
2. Adapter-call errors are fail-fast (`strict_adapter_call=True`)
3. Rule fallback disabled (`disable_rule_fallback=True`)
4. Online answer required (`require_online_answer=True`)

For debug-only relaxed runs, enable fallback flags in CLI:

```powershell
python scripts/run_eval_pipeline.py `
  --memory-system o_mem `
  --allow-rule-fallback `
  --allow-adapter-fallback `
  --allow-empty-online-answer
```

Quick smoke test (mock adapter):

```powershell
python scripts/test_eval_pipeline_mock.py
```

## Design Docs

1. `docs/architecture/three-layer-probe-implementation-plan.md`
2. `docs/traceability/DESIGN_NOTES.md`
3. `docs/architecture/eval-layer-final-implementation-v0.4.2.md`
4. `docs/architecture/o-mem-adapter-compliance-audit-v0.4.2.md`
5. `docs/architecture/o-mem-real-run-sample0-report-v0.5.2.md`
6. `docs/architecture/three-probe-implementation-logic-bilingual-v0.6.0.md`
7. `docs/architecture/adapter-fixed-interface-spec-bilingual-v0.6.0.md`
8. `docs/architecture/adapter-requirements-and-fidelity-protocol-bilingual-v0.6.1.md`
9. `docs/architecture/three-probe-framework-implementation-bilingual-v0.6.1.md`
10. `docs/architecture/one-memory-system-full-evaluation-flow-bilingual-v0.6.2.md`
