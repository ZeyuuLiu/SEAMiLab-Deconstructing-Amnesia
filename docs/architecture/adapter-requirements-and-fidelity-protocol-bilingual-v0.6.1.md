# Adapter Requirements and Fidelity Protocol (Bilingual) v0.6.1

## 1. Purpose / 文档目的

**CN**  
本文是对你提出的 5 条适配要求的正式化说明，目标是：  
1) 在多记忆系统评测时保持“忠于原系统”；  
2) 在归因时保持“证据可审计”；  
3) 在跨系统比较时保持“控制变量一致”。  
本文只给规范与流程，不涉及代码修改。

**EN**  
This document formalizes your five adapter requirements, with three goals:  
1) preserve fidelity to each original memory system,  
2) ensure auditable evidence for attribution,  
3) guarantee controlled variables for cross-system comparison.  
This is specification/process only, with no code changes.

---

## 2. Core Interpretation of Your 5 Requirements / 你 5 条要求的核心理解

## 2.1 Encoding: storage-aware, system-specific / 编码层：存储适配优先，按系统定制

**CN**  
编码层不是“字符串比对任务”，而是“存储存在性判定任务”。  
因此编码层适配器必须围绕“系统真实存储结构”实现：JSON 文件、KV、关系库、向量库、图谱都应以系统原生方式查询，再统一输出候选证据给评估层与 LLM 裁判。

**EN**  
Encoding is not a string-matching task; it is a storage-existence task.  
So the encoding adapter must query each system’s real storage form (JSON/KV/RDB/vector/graph) natively, then normalize candidate evidence for evaluator + LLM adjudication.

## 2.2 Retrieval: use original system output directly / 检索层：必须忠于原系统原生输出

**CN**  
检索层输入必须是“该记忆系统在真实推理链路中，给输出模型的检索上下文”。  
禁止替换为适配器自定义重排或近似检索结果，否则评估失真。

**EN**  
Retrieval input must be exactly what the memory system passes to its answer model in the real pipeline.  
Replacing it with adapter-side approximation/re-ranking is not acceptable and breaks fidelity.

## 2.3 Generation: tri-answer comparison under model consistency / 生成层：三答案对照且模型一致

**CN**  
生成层归因使用三答案：  
1) `A_gold`（标准答案）  
2) `A_online`（系统检索证据下最终答案）  
3) `A_oracle`（标准证据下答案）  
必须保持“最终生成模型一致”（同 model / same decoding config），才能做有效归因。

**EN**  
Generation attribution compares three answers:
1) `A_gold` (reference),  
2) `A_online` (system retrieval-based),  
3) `A_oracle` (gold evidence-based).  
The final generation model must be held constant (same model/decoding config) for valid attribution.

## 2.4 Fail-fast only / 失败即失败，不允许降级

**CN**  
评测必须 full-path + LLM required。  
任一环节失败（调用失败、解析失败、超时）应直接标记该 query `EVAL_ERROR`，不得自动 fallback/降级。

**EN**  
Evaluation must run the full path with mandatory LLM calls.  
Any failure (API, parsing, timeout, etc.) should mark the query as `EVAL_ERROR`; no silent fallback/degradation.

## 2.5 Multi-system attribution requires strict controls / 多系统归因必须严格控参

**CN**  
你要比较多个记忆系统，控制变量是前提：同数据切片、同问题集合、同输出模型、同评测 LLM、同提示词版本、同阈值策略、同随机种子/温度。

**EN**  
For cross-system attribution, controlled variables are mandatory: same dataset slice, same question set, same answer model, same evaluator LLM, same prompt version, same thresholds, same randomness settings.

---

## 3. Required Adapter Behavior by Layer / 分层适配器行为规范

## 3.1 Encoding Adapter (system-specific strategy required) / 编码层适配器（必须系统特化）

### 3.1.1 Responsibilities / 职责

**CN**
1. 直接访问原系统底层存储（而不是仅访问导出文本）。  
2. 提供“高召回候选证据集合”，输入需包含 `query + F_key + gold evidence`。  
3. 输出候选时附带存储来源元数据（库名/表名/key/path/node-id/timestamp/speaker）。  

**EN**
1. Access original storage backend directly (not text-only exports).  
2. Return high-recall candidate evidence using `query + F_key + gold evidence`.  
3. Include storage provenance metadata (table/key/path/node/timestamp/speaker).

### 3.1.2 Strategy examples / 策略示例

**CN**
- JSON/文件系统：路径遍历 + 字段过滤 + 语义召回  
- Redis/KV：key pattern + value parser + embedding rerank  
- SQL：结构化 where + 全文索引 + 向量列检索  
- Graph：子图扩展（entity/relation neighborhood）+ 语义重排  

**EN**
- JSON/files: path traversal + field filtering + semantic recall  
- Redis/KV: key patterns + value parsing + embedding rerank  
- SQL: structured filters + fulltext + vector retrieval  
- Graph: neighborhood expansion + semantic reranking

### 3.1.3 Output contract / 输出契约

```json
{
  "id": "string",
  "content": "string",
  "storage_type": "json|redis|sql|graph|vector|...",
  "source_ref": "path/key/table/node-id",
  "timestamp": "optional",
  "speaker": "optional",
  "scores": {
    "keyword": 0.0,
    "semantic": 0.0,
    "fusion": 0.0
  },
  "raw_meta": {}
}
```

---

## 3.2 Retrieval Adapter (must be native pipeline output) / 检索层适配器（必须原生链路）

### 3.2.1 Hard requirement / 硬性要求

**CN**  
`C_original` 必须来自原系统真实检索函数的输出（最终送入 answer model 的上下文），不能被适配器替换为“近似重建结果”。

**EN**  
`C_original` must come from the original system’s actual retrieval function (the exact context fed into the answer model), not adapter-side approximations.

### 3.2.2 Required trace fields / 必需追踪字段

**CN**
1. `retrieval_fn_name`（实际调用函数名）  
2. `retrieval_params`（top_k, threshold, filters）  
3. `retrieved_raw_payload`（系统原始返回）  
4. `provided_to_model_payload`（真正喂给模型的上下文）  

**EN**
1. `retrieval_fn_name`  
2. `retrieval_params`  
3. `retrieved_raw_payload`  
4. `provided_to_model_payload`

---

## 3.3 Generation Adapter (online/oracle consistency) / 生成层适配器（一致性约束）

### 3.3.1 Required behavior / 行为要求

**CN**
1. `A_online`：使用原系统真实检索上下文生成；  
2. `A_oracle`：替换为标准证据上下文生成；  
3. 两者必须使用相同模型、相同采样参数（温度、max_tokens、top_p、stop）。

**EN**
1. `A_online`: generated from original retrieval context;  
2. `A_oracle`: generated from gold/oracle evidence context;  
3. both must use the same model and decoding params.

### 3.3.2 Consistency manifest / 一致性清单

**CN / EN**
- `answer_model_name`  
- `answer_model_endpoint`  
- `temperature`  
- `top_p`  
- `max_tokens`  
- `seed` (if supported)  
- `prompt_template_version`

---

## 4. Fail-Fast Evaluation Protocol / 失败即失败协议

## 4.1 Query-level status / query级状态

**CN**
每个 query 仅允许三种最终状态：  
1. `EVAL_OK`  
2. `EVAL_ERROR_RUNTIME`（运行错误）  
3. `EVAL_ERROR_LLM`（LLM调用/解析错误）  

出现错误时，不进行降级，不补跑规则模式，不“猜测结果”。

**EN**
Each query ends in exactly one status:  
1. `EVAL_OK`  
2. `EVAL_ERROR_RUNTIME`  
3. `EVAL_ERROR_LLM`  
On error: no fallback, no degraded path, no inferred judgment.

## 4.2 Error payload contract / 错误载荷规范

```json
{
  "query_id": "conv-xx:n",
  "status": "EVAL_ERROR_LLM",
  "stage": "encoding|retrieval|generation",
  "error_type": "timeout|json_parse|api_error|...",
  "error_message": "...",
  "trace_id": "...",
  "timestamp": "..."
}
```

---

## 5. Controlled-Variable Protocol Across Systems / 多系统控参协议

## 5.1 Must-control variable matrix / 必控变量矩阵

**CN**
1. 数据：同一数据版本、同一 question 集  
2. 运行：同 batch 策略、同重试策略、同超时阈值  
3. 模型：同 answer model、同 evaluator LLM  
4. 提示词：同 prompt 版本  
5. 指标：同阈值（rank/snr/noise）  
6. 随机性：同 temperature/top_p/seed  

**EN**
1. data: same version and question set  
2. runtime: same batching/retry/timeout policy  
3. models: same answer model and evaluator LLM  
4. prompts: same template versions  
5. metrics: same thresholds  
6. randomness: same temperature/top_p/seed

## 5.2 Run manifest (required) / 运行清单（必需）

每次评测输出必须包含：
```json
{
  "memory_system": "o-mem|x-mem|...",
  "system_commit": "hash",
  "dataset_version": "locomo10@hash",
  "answer_model": "...",
  "evaluator_model": "...",
  "prompt_versions": {
    "encoding": "...",
    "retrieval_pos": "...",
    "retrieval_neg": "...",
    "generation_pos": "...",
    "generation_neg": "..."
  },
  "thresholds": {
    "tau_rank": 5,
    "tau_snr": 0.2,
    "neg_noise_threshold": 0.15
  },
  "runtime_policy": {
    "retry": 2,
    "timeout_sec": 30,
    "fail_fast": true
  }
}
```

---

## 6. Recommended Evaluation Workflow / 推荐评测流程

**CN**
1. 先跑原系统官方流程，产出 baseline。  
2. 按 `A_online vs A_gold` 切分 correct/incorrect。  
3. 先对 incorrect 跑归因（主分析）。  
4. 再对 correct 跑归因（健全性验证）。  
5. 输出跨系统对照报告（缺陷分布 + 证据样例）。  

**EN**
1. Run official baseline pipeline first.  
2. Split samples by `A_online vs A_gold`.  
3. Run attribution on incorrect subset first.  
4. Run attribution on correct subset for sanity.  
5. Produce cross-system comparative attribution report.

---

## 7. O-Mem Specific Practical Guidance / O-Mem 的具体指导

**CN**
对 O-Mem，适配层要重点保证：
1. Retrieval 必须调用 O-Mem 原生检索函数输出，而非适配器重算。  
2. `A_online` 必须来自 O-Mem 原生“检索->生成”链路。  
3. 编码候选来源应覆盖 working/episodic/persona 等真实层级，并保留来源标注。  
4. 真实模式失败必须直接报错，禁止 fallback lightweight。  

**EN**
For O-Mem adapter fidelity:
1. Retrieval must use O-Mem native retrieval outputs (no adapter re-computation).  
2. `A_online` must come from native retrieve->generate path.  
3. Encoding candidates should cover real layers (working/episodic/persona) with provenance tags.  
4. Real-mode failures must be surfaced directly; no lightweight fallback.

---

## 8. Acceptance Checklist / 验收清单

**CN / EN**
- [ ] Encoding candidates are storage-native and provenance-complete  
- [ ] Retrieval payload equals native context delivered to answer model  
- [ ] `A_online` and `A_oracle` use identical answer-model configuration  
- [ ] No fallback path in evaluation (fail-fast enforced)  
- [ ] Cross-system run manifests are complete and comparable  
- [ ] Query-level errors are explicit and auditable

---

## 9. Final Note / 最终说明

**CN**  
你这 5 条要求的核心是“保真 + 可审计 + 可对比”。  
只要适配层严格执行上述协议，评估结果才能真正支持跨记忆系统归因分析。

**EN**  
Your five requirements converge on fidelity, auditability, and comparability.  
If adapters follow this protocol strictly, attribution results become valid for cross-memory-system analysis.
