# Design Notes (Iteration 0.1.0)

## D-001: Layered architecture

1. Evaluation Core:
   - Framework-owned logic only
   - No dependency on concrete memory systems
2. Adapter Layer:
   - Converts each system's outputs into framework input contracts
3. Dataset Builder:
   - Converts LOCOMO raw records into evaluation samples

## D-002: LOCOMO sample schema (demo)

Each sample record in demo output includes:

1. `sample_id`
2. `question_id`
3. `question`
4. `answer_gold`
5. `task_type`
6. `f_key` (fact list)
7. `oracle_context`
8. `evidence_ids`
9. `evidence_texts`
10. `construction_evidence` (reason trace for reproducibility)
11. `evidence_with_time` (time + speaker + utterance)

This schema is intentionally evidence-rich to support future attribution explanation output.

Time-aware evidence format:

`<date_time> | <speaker>: <text>`

## D-003: Negative sample construction rule

1. `f_key = []`
2. `oracle_context = "NO_RELEVANT_MEMORY"`
3. `construction_evidence` records this forced rule

## D-004: Key config policy

The demo reads `configs/keys.local.json`.

1. `--fkey-source rule`: no external API call
2. `--fkey-source llm`: calls OpenAI-compatible `/chat/completions`

## D-005: Runtime query resolution interface

Added dataset-side interface for future evaluator runtime calls:

1. `build_locomo_sample_registry(...)`
2. `LocomoSampleRegistry.find_by_query(query, sample_id=None)`
3. `LocomoSampleRegistry.get_by_question_id(question_id)`

This allows evaluator to resolve one incoming query into:

1. `answer_gold`
2. `task_type`
3. `f_key`
4. `oracle_context`
5. evidence fields
