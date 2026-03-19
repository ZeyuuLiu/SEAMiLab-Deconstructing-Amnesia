# Three-Probe Framework Implementation (Bilingual) v0.6.1

## 1) Why this update / 本次更新目标

**CN**  
本次实现聚焦你强调的 5 个原则：  
1. 编码层按系统存储特化；  
2. 检索层忠于原系统真实输出；  
3. 生成层三答案对照且模型一致；  
4. 失败即失败，不降级；  
5. 多系统评测严格控参。  

**EN**  
This update enforces your five requirements:
1. storage-specific encoding adaptation,  
2. retrieval fidelity to native system output,  
3. tri-answer generation attribution with model consistency,  
4. fail-fast with no degradation,  
5. strict variable control across systems.

---

## 2) Code-level changes / 代码级改动总览

1. `src/memory_eval/eval_core/models.py`  
   - Added strict policy flags in `EvaluatorConfig`:
   - `require_llm_judgement`
   - `strict_adapter_call`
   - `disable_rule_fallback`
   - `require_online_answer`

2. `src/memory_eval/eval_core/encoding.py`  
   - In strict mode:
   - adapter hybrid retrieval exceptions are surfaced
   - LLM encoding judgement is mandatory
   - invalid/missing LLM judgement raises error
   - rule fallback scan is blocked

3. `src/memory_eval/eval_core/retrieval.py`  
   - In strict mode:
   - POS/NEG LLM judgement is mandatory
   - LLM state can be used as primary retrieval state
   - invalid/missing LLM judgement raises error
   - no fallback to rule-only path

4. `src/memory_eval/eval_core/generation.py`  
   - In strict mode:
   - `generate_online_answer` failures are surfaced
   - empty online answer is treated as error
   - both generation LLM judges are mandatory

5. `src/memory_eval/pipeline/runner.py`  
   - pipeline now captures per-query `EVAL_ERROR`
   - output includes:
   - `results` (successful attributions)
   - `errors` (fail-fast query errors)
   - `adapter_manifest` (for audit/reproducibility)

6. `src/memory_eval/adapters/registry.py`  
   - Added registry-based adapter factory:
   - `create_adapter_by_system(...)`
   - `list_supported_memory_systems(...)`
   - `export_adapter_runtime_manifest(...)`
   - Enforces "one memory system -> dedicated adapter implementation entry"

7. `src/memory_eval/adapters/o_mem_adapter.py`  
   - Real O-Mem ingest no longer silently falls back unless explicitly allowed:
   - `allow_fallback_lightweight=False` by default

8. `scripts/run_eval_pipeline.py`  
   - Added `--memory-system` flow via adapter registry
   - Added strict/fallback control flags

---

## 3) Three-probe execution logic (strict mode) / 三层探针严格模式逻辑

## 3.1 Encoding probe / 编码层

**Input**  
`Q + M + F_key + evidence_texts`

**Execution**
1. Adapter exports full memory corpus `M`.
2. Adapter provides candidate records (`hybrid_retrieve_candidates` / `find_memory_records`).
3. Evaluator calls LLM storage judge.
4. If LLM judgement missing/invalid -> immediate query error.

**Output**
- state: `EXIST | MISS | CORRUPT_AMBIG | CORRUPT_WRONG | DIRTY`
- defects: `EM | EA | EW | DMP`
- evidence: matched ids, snippets, LLM structured reasoning

---

## 3.2 Retrieval probe / 检索层

**Input**  
`Q + C_original + F_key (+ evidence_texts for POS)`

**Execution**
1. Adapter returns native `C_original` (ordered retrieval payload).
2. Evaluator computes metrics (`rank`, `snr`) as auxiliary evidence.
3. Evaluator calls POS/NEG-specific LLM retrieval judge.
4. If LLM judgement missing/invalid -> immediate query error.

**Output**
- state: `HIT | MISS | NOISE`
- defects: `RF | LATE | NOI | NIR`
- evidence: top items, hit indices, SNR meta, LLM rationale

---

## 3.3 Generation probe / 生成层

**Input**  
`Q + C_oracle + A_gold + A_online + A_oracle`

**Execution**
1. Adapter generates `A_oracle` under oracle context.
2. Adapter returns native `A_online` from normal path.
3. Evaluator calls two LLM judges:
   - oracle-vs-gold correctness
   - tri-answer comparison (`online`, `oracle`, `gold`)
4. Missing/invalid LLM judgement or missing online answer -> query error.

**Output**
- state: `PASS | FAIL`
- defects: `GH | GF | GRF`
- evidence: comparative judgement + both LLM outputs

---

## 4) Fail-fast semantics / 失败即失败语义

**CN**  
严格模式中，任一探针报错不会被“规则降级”吞掉。  
该 query 直接进入 `errors[]`，状态为 `EVAL_ERROR`，同时保留错误类型与错误消息。

**EN**  
In strict mode, probe errors are never absorbed by rule fallback.  
The query is recorded in `errors[]` as `EVAL_ERROR`, with error type and message.

---

## 5) Multi-system variable control / 多系统控参实现建议

在每次运行记录以下字段（已支持 `adapter_manifest` + pipeline config）：

1. adapter identity + adapter config
2. dataset path/version hash
3. evaluator config (LLM model/prompt thresholds/strict flags)
4. runtime policy (fallback flags / timeout / retries outside this layer)

这保证跨系统对比时可复现、可解释。

---

## 6) How to use / 使用方式

```powershell
python scripts/run_eval_pipeline.py `
  --memory-system o_mem `
  --adapter-config-json "{\"use_real_omem\":true,\"api_key\":\"...\",\"base_url\":\"...\"}" `
  --dataset data/locomo10.json `
  --output outputs/eval_pipeline_results.json `
  --limit 10
```

调试（允许非严格降级）：

```powershell
python scripts/run_eval_pipeline.py `
  --memory-system o_mem `
  --allow-rule-fallback `
  --allow-adapter-fallback `
  --allow-empty-online-answer
```

---

## 7) Final note / 结论

当前实现已经将框架默认模式切到你要求的方向：  
**“完整流程 + LLM 必经 + 失败显式暴露 + 多系统可比”**。  
接下来每接入一个新记忆系统，只需在独立适配器模块实现同一协议并注册到 registry。
