# Three-Probe Redesign Plan (Bilingual) v0.5.4

## 0. Scope / 范围说明

**CN**  
本文件是“思路汇报 + 修改说明”，只定义改造方案，不修改代码。  
目标是解决当前三层探针评估过于生硬、对异构存储适配不足、证据判定不稳健的问题。

**EN**  
This document is a design report and modification plan only. No code changes are included.  
The goal is to address current probe rigidity, insufficient adaptation to heterogeneous storage backends, and weak evidence-grounded judgments.

---

## 1. Problem Statement / 问题定义

## 1.1 Encoding probe issue / 编码层问题

**CN**  
当前编码层主要依赖：
1. 适配器返回候选；
2. `text_match` 规则匹配 query/fact。  
这对异构记忆系统不够严谨，容易出现“存了但判没存 / 没存却误判存了”。

**EN**  
Current encoding judgment relies on:
1. adapter-side candidate selection;
2. rule-based `text_match` over query/facts.  
This is not rigorous enough for heterogeneous backends and can cause false misses/false hits.

## 1.2 Retrieval probe issue / 检索层问题

**CN**  
当前检索层规则命中逻辑偏硬，难以表达语义相关但非字面匹配的情况；对 POS/NEG 场景区分也不够“语义化”。

**EN**  
Current retrieval evaluation is too literal and struggles with semantically relevant but non-literal matches; POS/NEG semantics are under-modeled.

## 1.3 Generation probe issue / 生成层问题

**CN**  
生成层需要比较三类答案：  
1. 标准答案 `A_gold`  
2. 记忆系统最终回答 `A_online`  
3. 完整证据驱动回答 `A_oracle`  
当前机制对这三者的联合判定和证据解释还不够完整。

**EN**  
Generation evaluation should jointly compare:
1. gold answer `A_gold`
2. system online answer `A_online`
3. oracle-context answer `A_oracle`  
Current logic lacks a complete tri-answer reasoning protocol and evidence explanation.

---

## 2. Redesign Objectives / 改造目标

**CN**
1. 让编码层真正“面向存储事实存在性”，而不是表面字符串匹配。  
2. 让检索层评估变成“LLM语义裁判 + 指标辅助”，并区分 POS/NEG。  
3. 让生成层变成“多答案对照 + 归因证据”评测闭环。  
4. 保留可审计性：每个结论必须给证据与推理链。

**EN**
1. Make encoding evaluation truly about evidence existence in storage, not shallow text matching.  
2. Make retrieval evaluation LLM-semantic-first with metric support, separated for POS/NEG.  
3. Make generation evaluation a tri-answer comparative attribution loop.  
4. Preserve auditability: every conclusion must include evidence and rationale.

---

## 3. Proposed Redesign by Probe / 分层改造方案

## 3.1 Encoding Probe Redesign / 编码层改造

### A) Core idea / 核心思想

**CN**  
编码层应改为“混合检索 + LLM判定”：
1. 混合检索：语义检索 + 关键词检索（query + `F_key` + evidence 全输入）  
2. 候选扩展：尽量高召回（宁可多取）  
3. LLM判定：让 LLM 综合候选证据、标准证据、问题，判断“是否真实记录”

**EN**  
Encoding should move to a “hybrid retrieval + LLM adjudication” architecture:
1. Hybrid retrieval: semantic + keyword, using query + `F_key` + evidence signals  
2. High-recall candidate expansion  
3. LLM adjudication over retrieved candidates vs gold evidence

### B) Adapter responsibilities / 适配器职责重定义

**CN**
适配器不再只是“返回文本列表”，而是要负责：
1. 底层存储访问（JSON/Redis/HBase/Graph/SQL 等）  
2. 统一候选视图（`id`, `content`, `source`, `timestamp`, `speaker`, `storage_path`, `raw_meta`）  
3. 混合检索执行与打分来源说明（semantic score / keyword score / fusion score）

**EN**
Adapter should provide:
1. backend-specific access (JSON/Redis/HBase/Graph/SQL, etc.)  
2. normalized candidate schema  
3. hybrid retrieval execution and score provenance (semantic/keyword/fusion)

### C) Hybrid retrieval design / 混合检索设计

**CN**
建议流程：
1. 关键词检索：BM25/倒排/LIKE/图谱属性过滤  
2. 语义检索：向量索引（FAISS/Milvus/PGVector/系统自带 embedding）  
3. 融合排序：RRF 或 weighted sum  
4. 输出 topN（例如 50~200）供 LLM 判断

**EN**
Recommended flow:
1. keyword retrieval (BM25/inverted index/filters/graph attributes)  
2. semantic retrieval (vector search)  
3. fusion ranking (RRF or weighted sum)  
4. output topN (e.g., 50~200) for LLM judging

### D) LLM judgment contract / LLM判定契约

**CN**
LLM 输入：
1. `Q`, `F_key`, gold evidence
2. candidate list with metadata
3. task type (POS/NEG)  
LLM 输出 JSON：
```json
{
  "encoding_state": "EXIST|MISS|CORRUPT_AMBIG|CORRUPT_WRONG|DIRTY",
  "defects": ["EM|EA|EW|DMP"],
  "confidence": 0.0,
  "matched_candidate_ids": [],
  "reasoning": "...",
  "evidence_snippets": []
}
```

**EN**
LLM input:
1. `Q`, `F_key`, gold evidence
2. candidate list + metadata
3. task type (POS/NEG)  
LLM output JSON with state/defects/confidence/matched IDs/rationale/evidence snippets.

---

## 3.2 Retrieval Probe Redesign / 检索层改造

### A) Core idea / 核心思想

**CN**  
检索层改为“LLM主裁判 + 指标辅助核验”。  
POS/NEG 使用不同提示词和不同裁判标准。

**EN**  
Retrieval should become “LLM as primary judge + metrics as supporting checks.”  
Use separate prompts/criteria for POS and NEG.

### B) POS and NEG prompt split / POS 与 NEG 提示词分离

**CN**
1. POS 提示词关注：
   - 关键事实是否在检索结果中被覆盖
   - 排序是否靠前
   - 是否有噪声干扰  
2. NEG 提示词关注：
   - 是否出现“误导性高相关噪声”
   - 是否诱导模型不该回答却回答

**EN**
1. POS prompt focuses on:
   - key-fact coverage in retrieved context
   - ranking quality
   - noise interference  
2. NEG prompt focuses on:
   - misleading high-relevance noise
   - risk of causing non-abstain behavior

### C) Metrics kept as quantitative side-channel / 保留指标作为量化旁证

**CN**
保留并规范：
1. `Rank(F_key, C_original)`：命中首位索引，不存在为 `-1`  
2. `SNR(C_original)`：  
\[
\frac{\text{TokenCount}(F_{key} \cap C_{original})}{\text{TokenCount}(C_{original})}
\]
3. 可补充 `Coverage@k`, `MRR`, `NoiseRate`。  

**EN**
Keep and normalize:
1. `Rank(F_key, C_original)` first-hit index, `-1` if absent  
2. `SNR(C_original)` as token overlap ratio  
3. optionally add `Coverage@k`, `MRR`, `NoiseRate`.

### D) Retrieval output contract / 检索层输出契约

**CN**
```json
{
  "retrieval_state": "HIT|MISS|NOISE",
  "defects": ["RF|LATE|NOI|NIR"],
  "llm_judgement": {...},
  "metrics": {
    "rank_fkey": -1,
    "snr": 0.0,
    "coverage_at_k": 0.0
  },
  "evidence": {...}
}
```

**EN**
Return retrieval state/defects, LLM judgment, metrics, and evidence in one auditable structure.

---

## 3.3 Generation Probe Redesign / 生成层改造

### A) Core idea / 核心思想

**CN**  
生成层改为“三答案联合裁判”：
1. `A_online`：记忆系统真实最终回答  
2. `A_oracle`：完美证据上下文下生成回答  
3. `A_gold`：标准答案  
让 LLM 对三者关系做结构化判断。

**EN**  
Generation should be tri-answer comparative judging:
1. `A_online` (real system final answer)
2. `A_oracle` (answer under oracle evidence)
3. `A_gold` (reference)

### B) POS/NEG separate criteria / POS/NEG 分场景判定

**CN**
1. POS：  
   - `A_oracle` 是否可达正确（用于排除模型本身能力瓶颈）  
   - `A_online` 与 `A_gold` 差异是否由记忆链路导致  
2. NEG：  
   - 是否应拒答  
   - `A_online` 是否发生幻觉型输出  
   - `A_oracle` 是否仍拒答（验证流程一致性）  

**EN**
1. POS:
   - whether `A_oracle` can reach correctness (controls model capability)  
   - whether `A_online` error is memory-pipeline-induced  
2. NEG:
   - abstention expectation  
   - hallucination in `A_online`  
   - consistency of `A_oracle` behavior

### C) Generation output contract / 生成层输出契约

**CN**
```json
{
  "generation_state": "PASS|FAIL",
  "defects": ["GH|GF|GRF"],
  "comparative_judgement": {
    "online_vs_gold": "...",
    "oracle_vs_gold": "...",
    "online_vs_oracle": "..."
  },
  "evidence": {...}
}
```

**EN**
Output includes final state/defects plus comparative analysis among online/oracle/gold answers.

---

## 4. Full Evaluation Workflow (Your Desired Process) / 你期望流程的完整化

## 4.1 Phase-1 Baseline reproduction / 第一阶段：原系统复现实验

**CN**
1. 固定版本（代码 commit、模型、依赖、配置）  
2. 跑原系统官方 LOCOMO 流程  
3. 产出原始结果（答案、检索、官方指标）并固化

**EN**
1. lock code/model/dependency/config versions  
2. run official LOCOMO pipeline of original system  
3. freeze native outputs and baseline metrics

## 4.2 Phase-2 Attribution on failure-first / 第二阶段：错误优先归因

**CN**
4. 按 `A_online vs A_gold` 划分正确/错误样本  
5. 先跑错误样本归因（主任务）  
6. 再跑正确样本归因（健全性侧证）

**EN**
4. bucket samples by correctness (`A_online vs A_gold`)  
5. run attribution on incorrect subset first  
6. run attribution on correct subset as sanity evidence

## 4.3 Phase-3 Cross-analysis / 第三阶段：对照分析

**CN**
7. 输出错误子集缺陷分布  
8. 输出正确子集缺陷分布  
9. 比较两者差异，确认评估体系区分能力

**EN**
7. produce defect distribution for incorrect subset  
8. produce defect distribution for correct subset  
9. compare to verify discriminative power of the evaluation framework

---

## 5. Known Vulnerabilities in Current Code / 当前代码漏洞清单

**CN**
1. 编码层对“存储事实存在性”的判据仍过于文本表面化。  
2. 检索层 `text_match` 命中定义对格式/别名过敏。  
3. 生成层缺少三答案联合裁判协议（当前只看 `A_oracle vs A_gold` 为主）。  
4. 真实适配器存在异常时会 fallback lightweight，可能掩盖真实失败。  
5. 目前尚无 baseline-first 的自动编排器（需人工串联）。  

**EN**
1. Encoding existence judgment is still too text-surface-driven.  
2. Retrieval hit definition is sensitive to format/alias mismatch.  
3. Generation lacks full tri-answer adjudication protocol.  
4. Real adapter can fall back to lightweight mode and mask true runtime failures.  
5. No automatic baseline-first orchestrator yet.

---

## 6. Proposed Modification Plan (No code yet) / 修改计划（仅方案，不改代码）

### Step A: Contract redesign / 协议重构
**CN** 定义三层 LLM 裁判输入/输出 JSON schema，统一证据结构。  
**EN** Define strict LLM I/O schemas and unified evidence contract.

### Step B: Encoding hybrid retrieval / 编码层混合检索
**CN** 在适配器层落地 semantic+keyword+fusion，输出高召回候选。  
**EN** Implement semantic+keyword+fusion retrieval in adapters with high recall.

### Step C: POS/NEG dual prompts / POS/NEG 双提示词
**CN** 检索层、生成层分别设计 POS/NEG prompt 模板与判据。  
**EN** Build separate POS/NEG prompt templates and criteria for retrieval/generation.

### Step D: Baseline-first orchestrator / 基线优先编排器
**CN** 自动串联“原系统复现 -> 错误筛选 -> 归因评估 -> 对照报告”。  
**EN** Add one orchestrator for baseline run, bucketing, attribution, and comparative reporting.

### Step E: Reliability controls / 可靠性控制
**CN** 增加 LLM 重试、JSON schema 校验、低置信度回退与人工复核标记。  
**EN** Add retries, schema validation, low-confidence fallback, and human-review tags.

---

## 7. Acceptance Criteria / 验收标准

**CN**
1. 任一结论必须可追溯到候选证据与判定理由。  
2. 错误样本中缺陷识别率显著高于正确样本。  
3. 不同存储后端接入后，不需要改评估核心逻辑。  

**EN**
1. Every conclusion must map to concrete evidence and rationale.  
2. Defect discovery rate must be significantly higher on incorrect subset than correct subset.  
3. New storage backends should plug in via adapters without changing core evaluator logic.
