# O-Mem StableEval Internal Fix Notes

## Goal

The original `system/O-Mem` must be preserved.
To stabilize runtime behavior for strict evaluation, a new parallel directory was created:

- `system/O-Mem-StableEval`

The intention is:

1. keep the original O-Mem untouched
2. create a patched evaluation-oriented runtime
3. use explicit bounded retries instead of unbounded loops
4. make JSON parsing robust enough for real LLM outputs

## New Runtime Entry

A new adapter registry key is added:

- `o_mem_stable_eval`

This key points to `system/O-Mem-StableEval` by default through adapter config.

So the project now supports two O-Mem tracks:

1. `o_mem`
   - original runtime path
2. `o_mem_stable_eval`
   - patched runtime path for strict evaluation experiments

## What Was Patched

### 1. `memory_chain/utils.py`

Added shared stabilization helpers:

1. `parse_json_response(...)`
   - strips markdown fences
   - extracts balanced JSON object/list
2. `require_keys(...)`
   - validates required JSON keys
3. `call_llm_json_with_retries(...)`
   - async bounded retry helper
4. `call_llm_text_with_retries(...)`
   - async bounded text-call retry helper
5. `call_llm_json_sync_with_retries(...)`
   - sync bounded retry helper

### 2. `memory_chain/memory_manager.py`

Patched functions:

1. `receive_message(...)`
2. `understand_dialogue(...)`
3. `wm_to_em_router(...)`
4. `wm_to_em_router_fact(...)`
5. `wm_to_em_router_attr(...)`
6. `generate_system_response(...)`

Main changes:

1. removed `while len(...) == 0` infinite loops
2. replaced raw `json.loads(...)` with shared robust parser
3. added bounded retry count
4. added explicit payload key validation

### 3. `memory_chain/episodic_memory.py`

Patched `evolve_topic_episodic_memory(...)`:

1. removed retry-until-success loop
2. replaced with bounded JSON retry helper
3. validated expected `Grouped Topics` structure

### 4. `memory_chain/persona_memory.py`

Patched:

1. `update_preference_persona(...)`
2. `update_attribute_persona(...)`

Main changes:

1. no more `while response == ""`
2. bounded retries
3. robust JSON parsing

### 5. `memory_chain/memory.py`

Patched `reorganize_profile_base_on_message(...)`:

1. removed open-ended loop
2. switched to sync bounded retry helper

## What This Fix Solves

The patched runtime directly addresses the main failure mode previously observed during real O-Mem evaluation:

1. model returns markdown-wrapped JSON
2. model returns extra prose before/after JSON
3. model returns parseable JSON substring but not pure JSON
4. old code fails `json.loads(...)`
5. old code enters long or infinite retry loops

The patched version now:

1. tries to recover JSON payload
2. retries only a limited number of times
3. raises explicit failure after retry exhaustion

This is much better aligned with the evaluation framework's strict fail-fast policy.

## What This Fix Does Not Solve

This patch improves runtime stability, but it does not guarantee that every O-Mem call will succeed.

It does not solve:

1. upstream model quality issues
2. network/API instability
3. semantic mistakes in returned JSON content
4. all possible O-Mem architectural inefficiencies

So this is a stability patch, not a claim that O-Mem is now perfect.

## Recommended Usage

For strict evaluation experiments, prefer:

- `--memory-system o_mem_stable_eval`

For reference comparison with the untouched upstream runtime, use:

- `--memory-system o_mem`

## Final Note

The most important result of this patch is not "fewer exceptions".
The most important result is:

**the runtime now has a bounded failure model**

That means evaluation can terminate with an explicit error instead of hanging indefinitely, which is necessary for a real benchmarking framework.
