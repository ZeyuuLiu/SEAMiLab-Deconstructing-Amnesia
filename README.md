# Memory Eval Framework

A clean-slate evaluation framework for long-term memory systems, designed with strict separation between:

1. Evaluation Core (framework-owned logic)
2. Adapter Layer (system-specific integration)

## Current Scope (Iteration 0.1.0+)

This iteration intentionally focuses on only two goals:

1. Project bootstrap with strict versioning artifacts
2. A small demo that builds evaluation samples from `locomo10.json`
3. Time-aware oracle context and query lookup interfaces for runtime integration

No full end-to-end attribution engine is implemented in this iteration.

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
