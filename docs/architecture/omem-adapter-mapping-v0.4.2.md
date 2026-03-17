# O-Mem Adapter Mapping v0.4.2

## 1. 冻结映射范围

本映射覆盖评估核心要求的三项观测：

1. `memory_view`
2. `retrieved_items`
3. `answer_oracle`

适配器实现位于 `src/memory_eval/adapters/o_mem_adapter.py`，并由 `scripts/run_omem_adapter_minimal.py` 进行最小联调。

## 2. `memory_view` 映射

标准输出项结构：

- `id: str`
- `text: str`
- `meta: dict`

`meta` 冻结字段：

- `layer`: `conversation_cache` 或 O-Mem 层级名（如 `user_working`、`user_episodic`）
- `turn_index`: 原轮次序号
- `role`: `user` 或 `agent`
- `speaker`: 原 speaker 文本
- `timestamp`: 会话时间戳

来源策略：

1. 轻量模式：直接从展开后的会话 turn 生成。
2. 真实 O-Mem 模式：从 working/episodic 缓存导出并标准化。

## 3. `retrieved_items` 映射

标准输出项结构：

- `id: str`
- `text: str`
- `score: float`
- `meta: dict`

顺序规则：

1. 按 `score` 降序。
2. 作为 `C_original` 原顺序透传给检索探针。

分数降级策略：

1. 当 O-Mem 原生检索分数不可直接稳定导出时，使用 lexical overlap 计算分值。
2. `meta.score_source` 固定记录为 `lexical_overlap_fallback`，确保可审计。

## 4. `answer_oracle` 映射

调用路径冻结为独立 `generate_oracle_answer(run_ctx, query, oracle_context)`：

1. 真实 O-Mem 模式：通过 O-Mem 侧生成接口，仅使用传入 `oracle_context`。
2. 轻量模式：使用 `oracle_context` 的确定性回退生成，不复用常规检索拼接结果。

该路径不依赖 `retrieve_original` 的输出，保证生成探针与检索因素隔离。
