# Changelog

All notable changes to this project are documented in this file.

## [0.4.1] - 2026-03-17

### Added

1. `system/` directory for baseline memory-system source code storage.
2. Bilingual LLM-assist strategy design doc:
   - `docs/architecture/llm-assist-strategy-bilingual-v0.4.1.md`

### Changed

1. `EvaluatorConfig.use_llm_assist` is now enabled by default.
2. README updated for:
   - `system/` directory convention
   - default-on LLM assist behavior

## [0.4.0] - 2026-03-17

### Added

1. Generation probe dedicated module:
   - `src/memory_eval/eval_core/generation.py`
2. Generation adapter protocol:
   - `GenerationAdapterProtocol.generate_oracle_answer(...)`
3. LLM-assisted generation judge:
   - `llm_judge_generation_answer(...)`
4. Independent generation test script:
   - `scripts/test_generation_probe.py`
5. Generation implementation and full three-probe vulnerability review docs:
   - `docs/architecture/generation-probe-implementation-v0.4.0.md`
   - `docs/architecture/three-probe-vulnerability-review-v0.4.0.md`

### Changed

1. Probe wrapper now routes generation logic through dedicated generation module.
2. Eval core exports include generation adapter protocol and generation APIs.
3. README updated with generation probe usage and test command.

## [0.3.0] - 2026-03-17

### Added

1. Retrieval probe dedicated module:
   - `src/memory_eval/eval_core/retrieval.py`
2. Retrieval adapter protocol:
   - `RetrievalAdapterProtocol.retrieve_original(...)`
3. Optional LLM-assist helper module:
   - `src/memory_eval/eval_core/llm_assist.py`
4. Independent retrieval test script:
   - `scripts/test_retrieval_probe.py`
5. Retrieval design document and encoding alignment check docs:
   - `docs/architecture/retrieval-probe-implementation-v0.3.0.md`
   - `docs/architecture/encoding-alignment-check-v0.3.0.md`

### Changed

1. Probe wrappers now call dedicated encoding/retrieval modules.
2. Encoding probe supports optional LLM-assisted fact matching.
3. README updated with retrieval and LLM-assist usage.

## [0.2.1] - 2026-03-17

### Added

1. Dedicated encoding probe implementation with explicit input contract `Q + M + F_key`
2. Adapter-bound encoding interfaces:
   - `EncodingAdapterProtocol.export_full_memory(...)`
   - `EncodingAdapterProtocol.find_memory_records(...)`
3. Encoding-only evaluation APIs:
   - `evaluate_encoding_probe(...)`
   - `evaluate_encoding_probe_with_adapter(...)`
4. Independent validation script:
   - `scripts/test_encoding_probe.py`
5. Detailed implementation doc:
   - `docs/architecture/encoding-probe-implementation-v0.2.1.md`

### Fixed

1. Safer short-token fact matching in encoding probe to avoid false positives (`he` vs `she`).

## [0.2.0] - 2026-03-17

### Added

1. Parallel three-probe evaluation core (`src/memory_eval/eval_core/`)
2. Adapter runtime protocol for evaluator integration
3. Evidence-first attribution output contract with probe-level evidence blocks
4. Runtime query resolution interfaces:
   - `build_locomo_sample_registry(...)`
   - `get_by_question_id(...)`
   - `find_by_query(...)`
5. Time-aware oracle context format update:
   - `<date_time> | <speaker>: <text>`
6. Three-layer probe implementation plan document:
   - `docs/architecture/three-layer-probe-implementation-plan.md`

### Changed

1. LOCOMO sample includes `evidence_with_time` and time-aware `oracle_context`
2. Demo script supports query-level sample resolve and LLM/rule f_key source selection

## [0.1.0] - 2026-03-16

### Added

1. New project bootstrap in `memory-eval-framework/`
2. Traceability docs for requirements and design notes
3. LOCOMO sample builder demo (`scripts/demo_build_locomo_samples.py`)
4. Dataset builder module (`src/memory_eval/dataset/locomo_builder.py`)
5. Versioning files: `VERSION`, `CHANGELOG.md`
