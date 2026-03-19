# One Memory System Full Evaluation Flow (Bilingual) v0.6.2

## 1. Goal / 目标

**CN**  
本文完整说明“单个记忆系统（先以 O-Mem 为例）”如何在当前评估框架中执行严格评测。  
强调：只描述流程，不执行代码。

**EN**  
This document explains the complete strict evaluation flow for one memory system (O-Mem first) under the current framework.  
It is a process walkthrough only, not an execution log.

---

## 2. Strict Evaluation Contract / 严格评测契约

默认策略必须满足：

1. `require_llm_judgement = true`
2. `strict_adapter_call = true`
3. `disable_rule_fallback = true`
4. `require_online_answer = true`

结论：任一阶段失败 -> 当前 query 标记 `EVAL_ERROR`，不降级，不补判。

---

## 3. End-to-End Data Path / 端到端数据链路

整体链路：

`locomo dataset -> sample builder -> adapter ingest -> native retrieval + native generation -> three probes -> attribution union -> json report`

---

## 4. Step-by-Step Workflow / 分步骤完整流程

## Step 0: Environment and dependency readiness / 环境与依赖准备

**CN**
1. 进入项目根目录。  
2. 保证 O-Mem 依赖齐全（至少包括 `torch`, `sentence-transformers`, `openai`, `nltk`, `transformers` 兼容版本）。  
3. 保证 API key/base_url 可用。  

**EN**
1. Enter project root.  
2. Ensure O-Mem dependencies are installed (including compatible `torch/sentence-transformers/openai/nltk/transformers`).  
3. Ensure API key/base_url are valid.

---

## Step 1: Build evaluation samples / 构建评估样本

由 `locomo_builder` 生成 `EvalSample`，包含：

1. `sample_id`, `question_id`, `question`
2. `task_type` (`POS`/`NEG`)
3. `answer_gold`
4. `f_key`
5. `oracle_context`
6. `evidence_texts` / `evidence_with_time`

这是后续三探针共同依赖的标准输入。

---

## Step 2: Adapter runtime ingest / 适配器运行态构建

对每个 `sample_id`：

1. 将对话 turns 送入 `adapter.ingest_conversation(...)`
2. O-Mem 真实模式下：
   - 初始化 `MemoryChain`
   - 初始化 `MemoryManager`
   - 回放 conversation 逐轮写入记忆
   - 同步 O-Mem 内部 topic/detail map
3. 产生 `run_ctx`

---

## Step 3: Per-query strict evaluation / 每个 query 的严格评测

对每个 query，在同一个 `run_ctx` 上并行运行三探针：

### 3.1 Encoding probe

输入：
`Q + M + F_key + evidence_texts`

过程：
1. `export_full_memory` 导出全量记忆视图
2. `hybrid_retrieve_candidates/find_memory_records` 提供候选
3. 调用编码 LLM 裁判输出 `EXIST/MISS/CORRUPT_*/DIRTY`

严格规则：
- LLM 失败或返回无效状态 => `EVAL_ERROR`

### 3.2 Retrieval probe

输入：
`Q + C_original + F_key`

过程（O-Mem 真实路径）：
1. `retrieve_original(...)` 调用 O-Mem 原生  
   `retrieve_from_memory_soft_segmentation(...)`
2. 将 O-Mem 原生检索结果标准化为评估条目（context/facts/attributes）
3. 调用 POS/NEG LLM 检索裁判
4. 记录 `rank/snr` 指标作为辅助证据

严格规则：
- LLM 判定失败 => `EVAL_ERROR`

### 3.3 Generation probe

输入：
`Q + A_gold + A_online + A_oracle + C_oracle`

过程：
1. `A_online`：O-Mem 原生检索结果 + O-Mem `generate_system_response(...)`
2. `A_oracle`：使用 `C_oracle` 调用 O-Mem `generate_system_response(...)`
3. 调用两个 LLM：
   - answer correctness judge
   - tri-answer comparison judge

严格规则：
- `A_online` 为空/调用失败 => `EVAL_ERROR`
- 任一 LLM 失败 => `EVAL_ERROR`

---

## Step 4: Attribution merge / 归因合并

对单 query：

1. 收集三层状态 `enc/ret/gen`
2. 缺陷并集：`D_total = D_enc ∪ D_ret ∪ D_gen`
3. 特例收敛：若 `enc = MISS`，抑制 `RF`
4. 输出 probe-level evidence + decision trace

---

## Step 5: Report output / 报告输出

输出 JSON 包含：

1. `config`（阈值、模型、严格策略）
2. `adapter_manifest`（适配器类与配置）
3. `summary`（total/ok/errors/defect/state 统计）
4. `results[]`（成功归因）
5. `errors[]`（失败 query 的错误详情）

---

## 5. Why this flow is faithful / 为什么这套流程满足“忠于原系统”

**CN**
1. 检索层不再自定义替代检索，而是直接调用 O-Mem 原生检索函数。  
2. 在线答案不再“取 top 文本当答案”，而是走 O-Mem 原生生成函数。  
3. 同一 query 上，检索与在线生成共享原生检索结果缓存，避免链路偏移。  

**EN**
1. Retrieval no longer uses adapter-side approximation and now calls native O-Mem retrieval.  
2. Online answer is no longer a top-text shortcut and now uses native O-Mem generation.  
3. Retrieval and online generation share the same native retrieval payload via per-query cache.

---

## 6. Single-system execution checklist / 单系统执行前检查清单

- [ ] O-Mem import passes in current Python env
- [ ] `use_real_omem = true`
- [ ] API key / base_url valid
- [ ] strict flags are all enabled (default)
- [ ] output report has both `results` and `errors`
- [ ] no fallback-only markers in strict run

---

## 7. Final note / 最终说明

先把 O-Mem 跑通是正确策略。  
当 O-Mem 在严格模式稳定后，再扩展到其他记忆系统，只需要实现各自独立 adapter 并注册到统一 registry。
