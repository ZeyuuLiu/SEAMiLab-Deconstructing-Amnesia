# Adapter Fixed Interface Spec (Bilingual) v0.6.0

## 1) Design Principle / 设计原则

**CN**  
评估层接口保持固定，记忆系统差异下沉到适配器层。  
新增记忆系统时，只需实现这些接口，不改评估核心。

**EN**  
Keep evaluator interfaces stable and push system differences into adapters.  
For a new memory system, implement adapter interfaces only; evaluator core stays unchanged.

---

## 2) Mandatory Interfaces / 必选接口

## 2.1 Runtime entry / 运行入口

### `ingest_conversation(sample_id, conversation) -> run_ctx`

**CN**  
作用：把样本会话加载进目标记忆系统并返回运行上下文。  
要求：`run_ctx` 可复用（同 `sample_id` 多 query 复用）。

**EN**  
Purpose: ingest one sample conversation into the target memory system and return a reusable runtime context.

---

## 2.2 Encoding interfaces / 编码层接口

### `export_full_memory(run_ctx) -> List[MemoryRecord]`

**CN**  
导出全量记忆视图 `M`。每条建议结构：
```json
{"id":"...", "text":"...", "meta":{"timestamp":"...", "speaker":"...", "source":"..."}}
```

**EN**  
Exports full memory view `M`. Suggested record shape: `id/text/meta`.

### `find_memory_records(run_ctx, query, f_key, memory_corpus) -> List[MemoryRecord]`

**CN**  
给编码层提供候选集（传统接口，兼容旧实现）。

**EN**  
Provides encoding candidates (legacy-compatible interface).

---

## 2.3 Retrieval interface / 检索层接口

### `retrieve_original(run_ctx, query, top_k) -> List[RetrievedRecord]`

**CN**  
返回原记忆系统原生检索结果 `C_original`（保序）。  
每条建议带 `score` 与 `meta.score_source`。

**EN**  
Returns ordered native retrieval results `C_original`, ideally with score provenance.

---

## 2.4 Generation interface / 生成层接口

### `generate_oracle_answer(run_ctx, query, oracle_context) -> str`

**CN**  
在完美证据上下文 `C_oracle` 下生成 `A_oracle`。

**EN**  
Generate `A_oracle` under perfect evidence context `C_oracle`.

---

## 3) Optional Interfaces / 可选增强接口

## 3.1 Encoding hybrid retrieval / 编码层混合检索增强

### `hybrid_retrieve_candidates(run_ctx, query, f_key, evidence_texts, top_n=100)`

**CN**  
用于“语义检索 + 关键词匹配 + 融合排序”的高召回候选生成。  
若不实现，评估层会回退到 `find_memory_records` + 规则兜底。

**EN**  
High-recall candidate retrieval (semantic + keyword + fusion).  
If absent, evaluator falls back to legacy candidate path.

## 3.2 Online answer export / 在线答案增强

### `generate_online_answer(run_ctx, query, top_k=5) -> str`

**CN**  
返回系统正常路径下的在线答案 `A_online`，用于生成层三答案对照。  
不实现也可运行（该字段将为空）。

**EN**  
Provides `A_online` from the system’s normal path for tri-answer comparison.  
Optional; evaluator can run without it.

---

## 4) Recommended Data Contract / 推荐数据契约

## 4.1 MemoryRecord

**CN**
```json
{
  "id": "string",
  "text": "<date_time> | <speaker>: <text>",
  "meta": {
    "timestamp": "string",
    "speaker": "string",
    "source": "json|redis|hbase|graph|sql|...",
    "storage_path": "optional",
    "raw_meta": {}
  }
}
```

**EN**  
Use normalized time-aware text plus source metadata for audit traceability.

## 4.2 RetrievedRecord

**CN**
```json
{
  "id": "string",
  "text": "string",
  "score": 0.0,
  "meta": {
    "score_source": "semantic|keyword|fusion|native",
    "raw_meta": {}
  }
}
```

**EN**  
Include explicit score source to avoid cross-system ambiguity.

---

## 5) Behavioral Requirements / 行为要求

**CN**
1. 接口异常要显式返回错误信息，不应静默吞掉。  
2. 真实模式失败是否允许 fallback 必须在 `raw_trace` 中可见。  
3. 同一 `sample_id` 可复用 `run_ctx`，避免重复写入导致状态污染。  

**EN**
1. Surface errors explicitly; avoid silent failures.  
2. If fallback occurs, expose it in `raw_trace`.  
3. Reuse `run_ctx` per `sample_id` to prevent duplicate-ingest contamination.

---

## 6) Why fixed interfaces matter / 为什么固定接口很关键

**CN**  
固定接口让评估核心保持稳定，便于：
1. 横向比较不同记忆系统；  
2. 逐步提升判定逻辑而不破坏系统接入层；  
3. 做长期可追溯实验。

**EN**  
Stable interfaces enable:
1. fair cross-system comparison,  
2. evaluator evolution without integration breakage,  
3. long-term reproducible experiments.
