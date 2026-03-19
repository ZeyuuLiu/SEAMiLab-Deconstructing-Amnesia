# Three-Probe Implementation Logic (Bilingual) v0.6.0

## 1) Overview / 总览

**CN**  
本版本三探针实现改为“规则兜底 + LLM结构化判定”的混合模式，并保留并行执行。  
目标：提高异构记忆系统场景下的鲁棒性与可解释性。

**EN**  
The probe stack now uses a hybrid strategy: deterministic fallback + structured LLM judgment, while keeping parallel execution.  
Goal: better robustness and interpretability across heterogeneous memory systems.

---

## 2) Encoding Probe / 编码层

### 2.1 Current implementation logic / 当前实现逻辑

**CN**
1. 从适配器导出全量记忆 `M`：`export_full_memory`。  
2. 优先调用适配器可选高召回接口：`hybrid_retrieve_candidates(query, f_key, evidence_texts, top_n)`。  
3. 若未提供或失败，则回落到 `find_memory_records`；再失败则评估层兜底扫描。  
4. 若开启 LLM 辅助：调用 `llm_judge_encoding_storage`，直接返回结构化状态（`EXIST/MISS/CORRUPT_AMBIG/CORRUPT_WRONG/DIRTY`）与缺陷。  
5. 若 LLM 不可用，走规则判定（事实匹配、部分命中、歧义检测、NEG污染判定）。

**EN**
1. Export full memory `M` via `export_full_memory`.  
2. Prefer optional high-recall adapter method `hybrid_retrieve_candidates(...)`.  
3. Fallback to `find_memory_records`, then evaluator-side fallback scan.  
4. If LLM assist is enabled: use `llm_judge_encoding_storage` for structured state/defects.  
5. If unavailable: use rule fallback (fact matching, partial-match ambiguity checks, NEG dirty checks).

### 2.2 Output semantics / 输出语义

**CN**  
输出 `ProbeResult(probe="enc")`，证据中包含：候选数、命中ID、证据片段、LLM判定对象。

**EN**  
Returns `ProbeResult(probe="enc")` with candidate counts, matched IDs, evidence snippets, and LLM judgment payload.

---

## 3) Retrieval Probe / 检索层

### 3.1 Current implementation logic / 当前实现逻辑

**CN**
1. 从适配器获取 `C_original`。  
2. 计算两类指标：  
   - `Rank(F_key, C_original)`（首命中位次，无命中 `-1`）  
   - `SNR(C_original)`（token overlap 比率）  
3. NEG 样本：  
   - 阈值噪声检测（`top_score`）  
   - LLM NEG 提示词判定（`llm_judge_retrieval_quality_neg`）  
4. POS 样本：  
   - 规则命中 + `rank/snr` 打 `LATE/NOI`  
   - LLM POS 提示词判定（`llm_judge_retrieval_quality_pos`）可补充缺陷或判 `MISS`。  

**EN**
1. Get `C_original` from adapter.  
2. Compute metrics:
   - `Rank(F_key, C_original)` (first hit rank, `-1` if absent)
   - token-overlap `SNR(C_original)`  
3. NEG path:
   - score-threshold noise detection
   - LLM NEG prompt (`llm_judge_retrieval_quality_neg`)  
4. POS path:
   - deterministic hit/rank/snr defects
   - LLM POS prompt (`llm_judge_retrieval_quality_pos`) can enrich defects or switch to `MISS`.

### 3.2 Output semantics / 输出语义

**CN**  
输出包含 `retrieval_state`、缺陷、指标元信息 (`snr_meta`)、LLM判定对象。

**EN**  
Output includes retrieval state, defects, metric metadata (`snr_meta`), and structured LLM judgment.

---

## 4) Generation Probe / 生成层

### 4.1 Current implementation logic / 当前实现逻辑

**CN**
1. 生成层输入扩展为三答案：`A_online`, `A_oracle`, `A_gold`。  
2. 适配器入口：
   - 必选：`generate_oracle_answer`  
   - 可选：`generate_online_answer`（若实现则用于在线答案对照）  
3. 规则判定仍以 `A_oracle vs A_gold` 为核心（用于判断“给足证据后模型能力”）。  
4. 开启 LLM 时：
   - `llm_judge_generation_answer`（子类 GH/GF/GRF）  
   - `llm_judge_generation_comparison`（三答案对照结论）  
5. 输出中新增 `comparative_judgement` 与 `online_correct/oracle_correct`。

**EN**
1. Generation input now includes three answers: `A_online`, `A_oracle`, `A_gold`.  
2. Adapter entry:
   - required: `generate_oracle_answer`
   - optional: `generate_online_answer`  
3. Rule core remains `A_oracle vs A_gold` (model capability under perfect context).  
4. With LLM assist:
   - `llm_judge_generation_answer` for subtype
   - `llm_judge_generation_comparison` for tri-answer comparative reasoning  
5. Output adds `comparative_judgement` and `online_correct/oracle_correct`.

---

## 5) Parallel Merge / 并行合并

**CN**  
`ParallelThreeProbeEvaluator` 仍保持并行执行。  
合并时保留规则：`enc == MISS` 时抑制检索层 `RF`。

**EN**  
`ParallelThreeProbeEvaluator` remains parallel.  
Merge rule is preserved: suppress retrieval `RF` when `enc == MISS`.

---

## 6) Important Notes / 重要说明

**CN**
1. 本版强调“先高召回，再由 LLM 做结构化裁判”，降低单纯字符串匹配误判。  
2. LLM 不可用时全链路可回退规则模式，保证可运行性。  
3. 三层输出都保留证据字段，便于审计。

**EN**
1. This version prioritizes high recall then LLM structured adjudication, reducing pure string-match errors.  
2. Full deterministic fallback is retained if LLM is unavailable.  
3. Evidence-rich outputs remain in all probes for auditability.
