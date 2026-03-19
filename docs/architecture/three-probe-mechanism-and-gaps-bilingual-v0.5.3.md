# Three-Probe Mechanism and Gaps (Bilingual) v0.5.3

## 1) Document Goal / 文档目标

**CN**  
本文件只做机制说明与漏洞审视，不修改代码。目标是回答三件事：  
1. 当前编码/检索/生成三探针到底如何工作；  
2. 你提出的“先复现实验系统原始效果，再调用评估体系”的完整流程应如何落地；  
3. 当前实现的主要漏洞、风险与影响面。

**EN**  
This document is analysis-only (no code changes). It answers three questions:  
1. How the current encoding/retrieval/generation probes actually work;  
2. How to operationalize your full workflow: reproduce original system results first, then run attribution;  
3. What major vulnerabilities and risks exist in the current implementation.

---

## 2) Current Three-Probe Detection Logic / 当前三探针探测逻辑

### 2.1 Encoding Probe (`encoding.py`)

**CN - 输入与流程**
1. 输入：`Q + M + F_key + task_type`。  
2. 先由适配器导出全量记忆库 `M`：`export_full_memory(run_ctx)`。  
3. 再由适配器做候选筛选：`find_memory_records(run_ctx, query, f_key, memory_corpus)`。  
4. 若适配器返回空候选，评估层兜底扫描（`text_match` 做 query/fact 匹配）。  
5. POS 样本：逐个 `fact` 在候选中 `_fact_match`（主要是规范化后 `fact in text`）。  
6. NEG 样本：只要存在“query/f_key 相关候选”就判 `DIRTY(DMP)`，否则 `MISS`。  

**EN - Input and flow**
1. Input: `Q + M + F_key + task_type`.  
2. Export full memory `M` via adapter: `export_full_memory(run_ctx)`.  
3. Adapter pre-filters candidates: `find_memory_records(...)`.  
4. If adapter returns none, evaluator performs fallback scanning with `text_match`.  
5. POS: each fact is matched against candidates via `_fact_match` (`fact in text` style).  
6. NEG: if any query/fact-related candidate exists -> `DIRTY(DMP)`, else `MISS`.

**CN - 状态与缺陷映射**
- `EXIST`: 全部 key facts 命中。  
- `MISS + EM`: 一个都没命中。  
- `CORRUPT_AMBIG + EA`: 部分命中且文本含歧义代词模式。  
- `CORRUPT_WRONG + EW`: 部分命中且非歧义。  
- `DIRTY + DMP`: NEG 样本不应有相关记忆却出现候选。  

**EN - State/defect mapping**
- `EXIST`: all key facts matched.  
- `MISS + EM`: no key facts matched.  
- `CORRUPT_AMBIG + EA`: partial match with ambiguity signals.  
- `CORRUPT_WRONG + EW`: partial match without ambiguity.  
- `DIRTY + DMP`: NEG sample contains related memory candidates.

---

### 2.2 Retrieval Probe (`retrieval.py`)

**CN - 输入与流程**
1. 输入：`Q + C_original + F_key + task_type`。  
2. `C_original` 由适配器 `retrieve_original(run_ctx, query, top_k)` 给出。  
3. POS：  
   - `rank_and_hit_indices` 用 `text_match` 判断命中；  
   - 命中数为 0 -> `MISS`（默认带 `RF`，但后续可能被收敛规则抑制）；  
   - 命中后再按阈值打 `LATE`（`rank > tau_rank`）和 `NOI`（`snr < tau_snr`）。  
4. NEG：  
   - 看 `top_score >= neg_noise_score_threshold` 判噪声；  
   - 可叠加 LLM 判断 `is_noise`；  
   - 噪声成立 -> `NOISE + NIR`，否则 `MISS`。  

**EN - Input and flow**
1. Input: `Q + C_original + F_key + task_type`.  
2. `C_original` comes from adapter `retrieve_original(...)`.  
3. POS:  
   - use `rank_and_hit_indices` with `text_match`;  
   - if no hit -> `MISS` (typically `RF`, later may be suppressed);  
   - if hit -> add `LATE` (`rank > tau_rank`) and/or `NOI` (`snr < tau_snr`).  
4. NEG:  
   - threshold-based top-score noise check;  
   - optional LLM `is_noise`;  
   - noisy -> `NOISE + NIR`, else `MISS`.

---

### 2.3 Generation Probe (`generation.py`)

**CN - 输入与流程**
1. 输入：`Q + C_oracle + A_oracle + A_gold + task_type`。  
2. `A_oracle` 由适配器 `generate_oracle_answer(...)` 生成。  
3. 规则判定：  
   - POS：`normalize(A_oracle) == normalize(A_gold)` 或 `A_gold in A_oracle`；  
   - NEG：命中拒答模式（`is_abstain`）才算正确。  
4. 可选 LLM 判题覆盖 `correct/substate`。  
5. 若失败：  
   - NEG -> `GH`;  
   - POS -> `GF/GRF`（LLM 子类优先，否则用 token overlap 阈值）。  

**EN - Input and flow**
1. Input: `Q + C_oracle + A_oracle + A_gold + task_type`.  
2. `A_oracle` is produced by adapter `generate_oracle_answer(...)`.  
3. Rule correctness:  
   - POS: exact or containment match with normalized strings;  
   - NEG: must satisfy abstention patterns.  
4. Optional LLM can override correctness/substate.  
5. On failure:  
   - NEG -> `GH`;  
   - POS -> `GF/GRF` (LLM subtype first, else token-overlap fallback).

---

### 2.4 Attribution Merge (`engine.py`)

**CN**
三探针并行跑完后，统一做缺陷并集；有一个关键收敛规则：  
- 若 `enc == MISS` 且 `ret` 含 `RF`，则抑制 `RF`（认为根因在编码层）。  

**EN**
After parallel probe execution, defects are merged. Key reconciliation rule:  
- If `enc == MISS` and `ret` contains `RF`, suppress `RF` (root cause assigned to encoding).

---

## 3) Full Workflow You Proposed / 你提出的完整评测流程

## 3.1 Recommended End-to-End Process / 推荐端到端流程

**CN**
### Phase A: 复现实验系统原始结果（先不接我们评估）
1. 按源项目官方方式复现实验环境与依赖。  
2. 跑原系统在 LOCOMO 的官方实验脚本，得到原始输出（answer、原始检索、官方指标）。  
3. 保存“可复现实验包”：命令、commit、配置、输出目录。  

### Phase B: 构建样本分层（错误样例优先）
4. 基于原系统输出和 `A_gold` 对齐，标注每题 `correct / incorrect`。  
5. 先对 `incorrect` 子集运行我们的三探针评估（核心归因分析）。  
6. 再抽样 `correct` 子集运行评估（健康性侧证）。  

### Phase C: 归因与解释闭环
7. 汇总错误子集的缺陷分布（EM/EW/RF/NOI/GF...）。  
8. 对比正确子集的缺陷分布（理想上显著更低）。  
9. 对差异做根因解释：编码缺失、检索噪声、生成推理失败各占比。  

**EN**
### Phase A: Reproduce baseline system results (without our attribution first)
1. Rebuild the original system environment/dependencies as officially specified.  
2. Run official LOCOMO experiment scripts to get native outputs (answers, retrievals, baseline metrics).  
3. Persist reproducibility bundle: commands, commit hash, configs, output artifacts.  

### Phase B: Build stratified sample sets (error-first)
4. Align system answers with `A_gold` and label each item as `correct/incorrect`.  
5. Run our three-probe attribution on `incorrect` subset first (primary diagnostics).  
6. Then run on sampled `correct` subset (sanity/health validation).  

### Phase C: Attribution closed loop
7. Aggregate defect distribution on incorrect subset.  
8. Compare against correct subset defect profile.  
9. Produce root-cause interpretation split by encoding/retrieval/generation.

## 3.2 Current Code Coverage vs This Workflow / 当前代码与该流程的覆盖度

**CN**
- 已有：三探针评估、适配器协议、端到端 pipeline。  
- 缺口：  
  1. 没有“官方基线结果自动解析 + 正误样本自动分桶”模块；  
  2. 没有“先跑原系统官方评估，再触发归因评估”的一键编排器；  
  3. 正确/错误样本分组统计目前需手工或外部脚本补充。  

**EN**
- Existing: three-probe attribution engine, adapter contracts, end-to-end pipeline.  
- Missing:  
  1. no built-in parser for official baseline outputs and auto bucketing by correctness;  
  2. no single orchestrator to run baseline-first then attribution;  
  3. grouped analytics for correct vs incorrect still requires external scripting.

---

## 4) Current Vulnerabilities and Risks / 当前漏洞与风险清单

## 4.1 Encoding-layer risks / 编码层风险

**CN**
1. **候选依赖过强**：探针只在候选集上做事实匹配，若候选筛错会误报 `EM`。  
2. **字符串匹配脆弱**：`fact in text` 对说话人别名、同义改写、时态改写很敏感。  
3. **NEG误伤风险**：NEG 只要有 query 相关候选就判 `DIRTY`，可能把泛化记忆误判为污染。  
4. **歧义判别偏粗**：`looks_ambiguous` 规则化较硬，可能漏检或误检。  

**EN**
1. **Over-dependence on candidate filtering**: wrong candidate set can trigger false `EM`.  
2. **Fragile string matching**: highly sensitive to alias/paraphrase/tense variants.  
3. **NEG over-penalization**: any related candidate may be labeled `DIRTY`.  
4. **Coarse ambiguity detection**: token-list heuristic can over/under trigger ambiguity.

## 4.2 Retrieval-layer risks / 检索层风险

**CN**
1. **命中定义过硬**：`text_match` 对完整 `f_key` 做命中，容易因格式差异漏命中。  
2. **阈值静态**：`tau_rank/tau_snr/neg_noise_threshold` 未按数据分布自适应。  
3. **评分来源不可比**：适配器可用不同评分策略，跨系统对比会失真。  
4. **并行上下文缺失**：`evaluate_with_adapters` 中 retrieval 的 `s_enc` 传入为 `None`，虽后处理抑制 `RF`，但探针内部证据链不完全一致。  

**EN**
1. **Hard hit criterion**: full-string `f_key` match is format-sensitive.  
2. **Static thresholds**: no data-adaptive calibration.  
3. **Score non-comparability**: adapter-defined score scales differ by system.  
4. **Parallel context gap**: retrieval receives `s_enc=None`; post-hoc suppression handles `RF` but internal evidence is less coherent.

## 4.3 Generation-layer risks / 生成层风险

**CN**
1. **规则判题偏简单**：POS 主要靠 exact/containment，语义等价易误判。  
2. **拒答词表有限**：NEG 拒答模式不全会导致 `GH` 偏差。  
3. **GF/GRF 依赖 token overlap**：简单重叠率不能可靠反映“有据但推理错”。  
4. **LLM裁决无一致性保障**：未做多次采样一致性或仲裁策略。  

**EN**
1. **Simplistic rule scoring**: semantic-equivalent answers can be misclassified.  
2. **Limited abstain patterns** for NEG.  
3. **GF/GRF via token overlap** is a weak grounding proxy.  
4. **No agreement protocol** for LLM judgments (single-shot uncertainty).

## 4.4 Adapter and orchestration risks / 适配器与编排层风险

**CN**
1. **真实模式静默降级**：`ingest_conversation` 失败会回退 lightweight，可能掩盖“未真正跑原系统”。  
2. **角色映射问题**：`Caroline` vs `User` 这类别名差异会放大编码/检索漏判。  
3. **原系统内部 JSON 解析脆弱**：运行中多次 `JSONDecodeError`，虽可最终成功，但稳定性/可复现性受影响。  
4. **缺少 baseline-first 自动流程**：与目标流程不完全一致，需要补编排。  

**EN**
1. **Silent fallback in real mode**: failures can downgrade to lightweight mode and hide true runtime status.  
2. **Role alias mismatch** (`Caroline` vs `User`) can inflate misses.  
3. **Original-system JSON parsing fragility** (`JSONDecodeError`) affects stability/reproducibility.  
4. **No built-in baseline-first orchestrator**, so your intended flow is only partially automated.

---

## 5) Practical Interpretation for Your Concern / 对你当前担忧的直接结论

**CN**
你指出“编码层判断是否真正包含证据有明显漏洞”是成立的，而且不仅编码层，检索层与生成层也有结构性风险。  
当前版本更适合做“可审计的第一版归因框架”，不应直接当作“最终高置信裁判器”。

**EN**
Your concern is valid: encoding has real evidence-detection weaknesses, and retrieval/generation also carry structural risks.  
Current implementation is best viewed as an auditable first-pass attribution framework, not a final high-confidence judge.

---

## 6) Recommended Next Non-coding Action / 下一步（先不改代码）的建议动作

**CN**
1. 先用你要求的流程跑一轮：`baseline 全量 -> incorrect 子集归因 -> correct 子集抽检归因`。  
2. 输出一份“错误样例归因矩阵”和“正确样例健康矩阵”做对照。  
3. 再决定代码修改优先级（建议先改 Encoding/alias-normalization 与 baseline-first 编排器）。  

**EN**
1. Execute one full cycle with your desired flow: baseline full run -> incorrect-subset attribution -> correct-subset attribution.  
2. Produce paired matrices: failure attribution matrix and healthy-sample matrix.  
3. Then prioritize code changes (encoding/alias normalization and baseline-first orchestrator first).
