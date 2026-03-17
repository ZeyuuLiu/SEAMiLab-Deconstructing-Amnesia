# LLM Assist Strategy (Bilingual) v0.4.1

## 中文说明

### 1. 总体策略

三层探针（编码/检索/生成）默认开启 LLM 辅助判定。  
设计原则是：

1. **LLM 增强语义判定能力**（尤其是模糊匹配、复杂语义噪声、答案正确性细分）
2. **规则路径始终可回退**（LLM 失败时不阻塞评估）
3. **证据可审计**（保留 `llm_judgement` 原始判定结果）

### 2. 编码层（Encoding）LLM 辅助

目标：

1. 在 `Q + M + F_key` 场景下，辅助判断事实匹配是否成立
2. 对模糊表达、语义改写、时间描述变化做补充判断

调用点：

1. `llm_judge_fact_match(...)`
2. 输出字段：`match`, `ambiguous`, `reason`

回退机制：

1. 若 LLM 调用失败，回退到规则匹配 `_fact_match`

### 3. 检索层（Retrieval）LLM 辅助

目标：

1. 在 NEG 场景下辅助判断 `C_original` 是否属于高误导噪声
2. 减少仅靠 score 阈值带来的误判

调用点：

1. `llm_judge_retrieval_noise(...)`
2. 输出字段：`is_noise`, `reason`

回退机制：

1. 若 LLM 调用失败，使用 `top_score >= neg_noise_score_threshold` 的规则路径

### 4. 生成层（Generation）LLM 辅助

目标：

1. 比较 `A_oracle` 与 `A_gold` 时提供更强判题能力
2. 对 FAIL 子类进行细分：`GH/GF/GRF`

调用点：

1. `llm_judge_generation_answer(...)`
2. 输出字段：`correct`, `substate`, `grounded`, `reason`

回退机制：

1. 若 LLM 调用失败，回退到规则判题：
   - NEG: 是否拒答
   - POS: 是否正确 + grounded overlap 启发式分流

### 5. 默认开启配置

`EvaluatorConfig` 默认：

1. `use_llm_assist=True`
2. `llm_model="gpt-4o-mini"`（可配置）
3. `llm_base_url`、`llm_api_key` 由运行配置注入

建议：

1. 开发/离线调试可设 `use_llm_assist=False`
2. 正式实验建议固定 judge 模型并记录版本

### 6. 风险与控制

主要风险：

1. 非确定性（不同次调用结果可能波动）
2. 成本与延迟增加
3. 评测结果对 judge 模型敏感

控制建议：

1. 保留规则回退路径
2. 输出 `llm_judgement` 到证据字段
3. 固定模型与温度
4. 在报告中标注是否启用 LLM assist

---

## English Notes

### 1. Overall Strategy

LLM assistance is enabled by default for all three probes (encoding, retrieval, generation).
The strategy is:

1. **Use LLM for stronger semantic judgement**
2. **Always keep deterministic rule fallback**
3. **Preserve auditability via evidence logs (`llm_judgement`)**

### 2. Encoding Probe LLM Assist

Purpose:

1. Assist fact matching under `Q + M + F_key`
2. Improve robustness on paraphrase/time-expression variance

Hook:

1. `llm_judge_fact_match(...)`
2. Output: `match`, `ambiguous`, `reason`

Fallback:

1. If LLM fails, use `_fact_match` rule path

### 3. Retrieval Probe LLM Assist

Purpose:

1. In NEG tasks, judge whether `C_original` is misleading noise
2. Reduce false decisions from score-threshold-only logic

Hook:

1. `llm_judge_retrieval_noise(...)`
2. Output: `is_noise`, `reason`

Fallback:

1. If LLM fails, use rule threshold path (`top_score`)

### 4. Generation Probe LLM Assist

Purpose:

1. Compare `A_oracle` vs `A_gold` with stronger judgement
2. Classify fail subtype (`GH/GF/GRF`)

Hook:

1. `llm_judge_generation_answer(...)`
2. Output: `correct`, `substate`, `grounded`, `reason`

Fallback:

1. If LLM fails, use deterministic rule mode:
   - NEG: abstain check
   - POS: correctness + grounding overlap heuristic

### 5. Default Configuration

`EvaluatorConfig` defaults:

1. `use_llm_assist=True`
2. configurable model/base_url/api_key fields

Recommendation:

1. set `use_llm_assist=False` for offline debugging
2. pin judge model for formal benchmark runs

### 6. Risks and Controls

Risks:

1. non-determinism
2. latency/cost overhead
3. sensitivity to judge model quality

Controls:

1. deterministic fallback always available
2. persist `llm_judgement` in probe evidence
3. pin model + temperature
4. report whether LLM assist is enabled
