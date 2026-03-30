# 记忆系统评估框架 — 项目进展汇报（2026-03-25）

## 1. 项目背景与目标

本项目在 **SEAMiLab-Deconstructing-Amnesia** 仓库中实现了一套面向 LoCoMo 数据的 **记忆系统评估框架**。核心目标不是仅统计问答正确率，而是将失败原因拆解到三层：

| 层级 | 关注点 |
|------|--------|
| **编码层（Encoding）** | 关键事实是否被正确写入/保留在记忆系统中 |
| **检索层（Retrieval）** | 系统原生检索路径是否能把关键证据以合理排序取出 |
| **生成层（Generation）** | 在给定 oracle 上下文与在线检索路径下，生成是否符合 gold / 拒答规范 |

框架通过 **适配器（Adapter）** 将具体记忆系统（当前以 **O-Mem** 为参考实现）接入统一协议，与评估核心解耦。

---

## 2. 技术架构现状（已实现）

### 2.1 数据与样本契约

- 数据源：`data/locomo10.json`（LoCoMo）。
- 样本构建：`src/memory_eval/dataset/locomo_builder.py` 将原始 episode 转为统一 `EvalSample`。
- **POS / NEG** 由 gold answer 模式推断；**NEG** 样本强制 `f_key = []`、`oracle_context = "NO_RELEVANT_MEMORY"`，与评估语义一致。

### 2.2 评估核心（eval_core）

- 三探针并行：`src/memory_eval/eval_core/engine.py`（`ParallelThreeProbeEvaluator`）。
- 归因合并：当编码层为 **MISS** 时，抑制检索层 **RF**，避免「未存储却归咎检索失败」。
- **严格模式默认开启**（`EvaluatorConfig`）：要求 LLM 判定、适配器调用失败即暴露、默认禁用规则兜底等，整体取向为 **fail-fast、可审计**，而非静默降级。

### 2.3 流水线与脚本

- 全量三探针流水线：`src/memory_eval/pipeline/runner.py` + `scripts/run_eval_pipeline.py`。
- O-Mem 两阶段实验脚本（先基线正误、再归因）：`scripts/run_omem_two_stage_eval.py`。
- StableEval 单次冒烟：`scripts/run_omem_stable_smoke_once.py`（用于快速验证真实 O-Mem + StableEval 路径）。

### 2.4 O-Mem 接入与双轨运行时

- 适配器：`src/memory_eval/adapters/o_mem_adapter.py`。
- 注册：`src/memory_eval/adapters/registry.py` 支持：
  - `o_mem`：原始 `system/O-Mem`
  - `o_mem_stable_eval`：默认指向 `system/O-Mem-StableEval`（评估向补丁版，**不修改上游 O-Mem 目录**）

StableEval 侧主要增强：**鲁棒 JSON 解析、有界重试、显式错误**，以配合评估框架的严格语义。

---

## 3. 环境与部署进展

### 3.1 已完成

- 使用 Conda 环境 **`omem-paper100`**（Python 3.10）符合 runbook 建议。
- 在项目根目录（含 `pyproject.toml` 的路径）执行可编辑安装与依赖安装；曾出现因在错误父目录执行 `pip install -e .` 导致「非 Python 项目」报错，**已明确根目录要求**。
- 已安装 `system/O-Mem-StableEval/requirements.txt` 中依赖（含 `transformers`、`sentence-transformers`、`torch` 等）。
- **`scripts/audit_o_mem_adapter.py`** 与 **`run_eval_pipeline.py --list-memory-systems`** 在目标环境中通过，确认：
  - 适配器协议层面完整；
  - `o_mem` / `o_mem_stable_eval` 均已注册。

### 3.2 配置要求

- 真实跑通需要 **`configs/keys.local.json`**（API Key、Base URL、模型名等）；冒烟脚本硬编码读取该路径。
- 本地嵌入模型路径：冒烟脚本默认使用项目内 **`Qwen/Qwen3-Embedding-0.6B`**（需存在于磁盘）。

---

## 4. 运行验证与问题闭环

### 4.1 问题一：冒烟脚本找不到密钥文件

- **现象**：`FileNotFoundError: .../configs/keys.local.json`。
- **状态**：已通过创建/补全 `configs/keys.local.json` 解决（与 `keys.local.example.json` 对齐）。

### 4.2 问题二：StableEval 检索阶段 `torch.topk` 非法 k 崩溃

- **现象**：`RuntimeError: selected index k out of range`，栈指向  
  `system/O-Mem-StableEval/memory_chain/memory_manager.py` 中  
  `retrive_from_data_attr_fact_topic(...)`。
- **根因**：
  - 该函数对三路候选的 `topk` 使用了实验性硬编码偏移（如 `top_k - 9`）。
  - 冒烟脚本固定 **`top_k = 5`**，故 `5 - 9 = -4`，再经 `min(...)` 仍可能得到 **非法 k**。
  - 当日志中 **persona attributes 数量为 0** 时，第一路相似度向量为空，与负 `k` 叠加，直接导致 `torch.topk` 报错。
- **修复**（最小改动，仅 **O-Mem-StableEval**，保留原始 `O-Mem` 不动）：
  - 在 `retrive_from_data_attr_fact_topic` 内增加 **`_safe_topk`**：对 **空候选** 或 **`desired_k <= 0`** 返回空结果；否则将 `k` 限制在 `1..len(similarities)`。
  - 目的：先保证 **检索阶段不因参数越界崩溃**，使冒烟与严格评估能够继续向后执行。

### 4.3 冒烟运行耗时与当前状态说明

- O-Mem **ingest** 对 **每一轮对话** 会触发大量 LLM 调用与内部记忆更新，**单样本（如 conv-30）端到端可能需数十分钟甚至更久**，属系统特性而非评估框架「卡住」。
- 修复 `topk` 后，预期行为是：ingest 完成后应能进入 **`stage=retrieval`**，并继续 **online / oracle 生成** 与 **三探针评估**，最终写出 JSON 结果文件。
- **汇报口径建议**：  
  - **框架与适配器层面**：审计与注册已通过；阻塞性崩溃点（非法 `k`）已在 StableEval 侧修复。  
  - **系统级**：完整冒烟/全量跑仍受 **API 延迟、对话长度、GPU/驱动与 torch 版本匹配** 影响，需以「单次完整跑通的 wall-clock 时间」作为运维指标单独跟踪。

---

## 5. 风险与待办事项

### 5.1 技术风险

| 风险 | 说明 | 缓解方向 |
|------|------|----------|
| O-Mem 内部仍高度依赖 LLM 与 JSON | 即使用 StableEval，仍可能因模型输出、网络等失败 | 维持有界重试与明确错误；必要时调低实验规模或缓存中间结果 |
| `retrive_from_data_attr_fact_topic` 三路 `top_k` 分配仍为启发式 | 当前修复为「不崩」，检索预算分配未必最优 | 后续可按 `n1/n2/n3` 动态分配总 `topn`，替代固定偏移 |
| CUDA 驱动与 PyTorch 版本 | 日志中曾出现 driver 过旧类警告 | 服务器侧升级驱动或安装与驱动匹配的 PyTorch 构建 |
| 评估严格模式 | 任意一层失败都会显性报错 | 与「论文可复现、可审计」一致；调试阶段可临时放宽 CLI 开关（需谨慎对照实验） |

### 5.2 建议的下一步（按优先级）

1. **完成一次 StableEval 冒烟落盘**：确认 `outputs/...json` 生成且含 `attribution_result`。  
2. **`run_eval_pipeline.py --limit 1 --memory-system o_mem_stable_eval`**：验证严格流水线最小闭环。  
3. **小规模两阶段实验**：`run_omem_two_stage_eval.py` 小 `limit-questions` 试跑。  
4. （可选）**重构三路 top-k 分配逻辑**，在「不崩」之上提升检索行为合理性。

---

## 6. 汇报用一句话摘要

**评估框架（数据集 → 适配器 → 三探针并行 → JSON 归因）与 O-Mem 双轨接入已落地并通过静态/导入审计；环境与 StableEval 依赖已可按文档安装；真实运行中已定位并修复 StableEval 检索内 `torch.topk` 非法 k 导致的崩溃；当前主要成本在长对话 ingest 的 LLM 调用与基础设施（驱动/torch），后续以「端到端冒烟 + limit=1 流水线 + 小规模两阶段」逐步验证稳定性。**

---

## 7. 文档与代码索引（便于复核）

| 内容 | 路径 |
|------|------|
| 评估层实现审计（自下而上） | `docs/code-audit/2026-03-19/eval-layer-bottom-up-implementation-audit.md` |
| O-Mem 适配器完成度审计 | `docs/code-audit/2026-03-19/o-mem-adapter-completion-audit.md` |
| StableEval 内部修复说明 | `docs/code-audit/2026-03-19/o-mem-stable-eval-internal-fix-notes.md` |
| 服务器 runbook | `docs/code-audit/2026-03-24/o-mem-stable-eval-server-runbook.md` |
| StableEval `topk` 安全修复 | `system/O-Mem-StableEval/memory_chain/memory_manager.py`（`retrive_from_data_attr_fact_topic` 内 `_safe_topk`） |
| 单次冒烟脚本 | `scripts/run_omem_stable_smoke_once.py` |

---

*本文档根据截至 2026-03-25 的代码审查、环境配置与运行日志整理，用于对内/对外进度同步。*
