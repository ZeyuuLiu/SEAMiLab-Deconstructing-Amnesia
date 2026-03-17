# Memory Eval Framework 项目详解

这是一个用于评估长期记忆系统的“Clean-slate”（全新设计）评估框架。其核心设计理念是严格分离**评估核心（Evaluation Core）**与**适配器层（Adapter Layer）**，以确保评估的客观性、可扩展性和跨系统可比性。

## 1. 项目概览

**Memory Eval Framework** 旨在解决现有记忆系统评估中的痛点，如评估逻辑与系统实现耦合、缺乏细粒度的归因分析等。

### 核心原则
1.  **分层架构**：评估逻辑（框架所有）与系统集成（适配器所有）完全解耦。
2.  **可追溯性（Traceability）**：所有迭代、需求和设计决策都有文档记录（见 `docs/` 目录）。
3.  **证据优先**：评估输出不仅包含分数，必须包含机器可审计的证据（Evidence）。
4.  **并行探针**：采用并行三探针（Encoding, Retrieval, Generation）架构，提高评估效率并提供全链路诊断。

## 2. 核心架构设计

项目主要由两部分组成：

### 2.1 评估核心 (Evaluation Core)
位于 `src/memory_eval/eval_core/`，包含通用的评估逻辑。它不依赖于任何特定的记忆系统实现。

*   **并行三探针评估器 (`ParallelThreeProbeEvaluator`)**：
    *   这是评估的核心引擎，负责并行运行三个探针。
    *   **编码探针 (Encoding Probe)**：检查关键事实（Key Fact）是否已正确存储在记忆系统中。
    *   **检索探针 (Retrieval Probe)**：检查系统检索是否将关键事实带到了有效位置（Top-K）。
    *   **生成探针 (Generation Probe)**：检查在给定 Oracle 上下文的情况下，模型是否仍会失败（幻觉或推理错误）。
*   **归因收敛 (Attribution Reconciliation)**：
    *   在三个探针运行完毕后，评估器会综合结果进行归因。例如，如果编码层通过（HIT），但检索层失败（MISS），则归因于检索故障（RF - Retrieval Failure）。如果编码层就已丢失（MISS），则会抑制检索层的故障归因。

### 2.2 适配器层 (Adapter Layer)
这是一个协议层，通过 `EvalAdapterProtocol` 定义。具体的记忆系统（如 MemGPT, LangChain Memory 等）需要实现这些接口，以便接入评估框架。

*   适配器负责将系统的内部状态转换为评估框架理解的通用格式 (`AdapterTrace`)。
*   主要接口包括：
    *   `export_full_memory()`: 导出全量记忆视图。
    *   `retrieve()`: 执行检索并返回标准化的 `RetrievedItem` 列表。
    *   `answer()`: 返回系统的回答。

## 3. 数据模型与契约

框架定义了一系列严格的数据类（Dataclasses）作为组件间的契约，位于 `src/memory_eval/eval_core/models.py`。

### 3.1 评估样本 (`EvalSample`)
来自数据集层（如 LOCOMO），包含评估所需的所有真值信息：
*   `question`: 问题。
*   `answer_gold`: 标准答案。
*   `f_key`: 关键事实列表（Key Facts），用于验证记忆是否包含必要信息。
*   `oracle_context`: 上下文真值。
*   `evidence_ids/texts`: 证据ID和文本。

### 3.2 适配器踪迹 (`AdapterTrace`)
适配器返回的系统运行快照：
*   `memory_view`: 系统的全量记忆视图（用于编码探针）。
*   `retrieved_items`: 系统检索到的条目列表（用于检索探针）。
*   `answer_oracle`: 系统在给定 Oracle 上下文下的回答（用于生成探针）。

### 3.3 探针结果 (`ProbeResult`)
每个探针的输出：
*   `state`: 状态（如 `EXIST`, `MISS`, `HIT`, `PASS`, `FAIL`）。
*   `defects`: 缺陷列表（如 `EM` (Encoding Miss), `RF` (Retrieval Failure)）。
*   `evidence`: 支持该结论的证据（如匹配到的记忆ID、排名位置等）。

## 4. 关键流程

1.  **样本构建**：使用 `dataset/locomo_builder.py` 从原始数据（如 `locomo10.json`）构建 `EvalSample`。
2.  **系统运行**：适配器驱动待测记忆系统处理问题，并生成 `AdapterTrace`。
3.  **并行评估**：`ParallelThreeProbeEvaluator` 接收 `EvalSample` 和 `AdapterTrace`。
    *   **P_enc** 检查 `f_key` 是否在 `memory_view` 中。
    *   **P_ret** 检查 `f_key` 是否在 `retrieved_items` 的 Top-K 中。
    *   **P_gen** 检查 `answer_oracle` 是否正确。
4.  **结果汇总**：生成 `AttributionResult`，包含所有探针的状态、缺陷集合和详细证据。

## 5. 项目结构说明

```text
memory-eval-framework/
├── configs/                # 配置文件（如 API key）
├── data/                   # 数据文件（如 locomo10.json）
├── docs/                   # 文档中心
│   ├── architecture/       # 架构设计文档
│   ├── iterations/         # 迭代计划与记录
│   └── traceability/       # 需求与设计笔记
├── scripts/                # 实用脚本（Demo, 测试脚本）
├── src/
│   └── memory_eval/
│       ├── dataset/        # 数据集构建 (LOCOMO)
│       └── eval_core/      # 评估核心逻辑
│           ├── encoding.py # 编码探针实现
│           ├── retrieval.py# 检索探针实现
│           ├── engine.py   # 主评估引擎
│           └── models.py   # 数据模型
└── ...
```

## 6. 快速上手

### 环境准备
```bash
python -m venv .venv
source .venv/bin/activate  # 或 Windows: .venv\Scripts\Activate.ps1
pip install -e .
```

### 运行 Demo
生成 LOCOMO 评估样本的 Demo：
```bash
python scripts/demo_build_locomo_samples.py --limit 5 --fkey-source rule
```
这将读取 `data/locomo10.json` 并生成包含 `f_key` 的评估样本，输出到 `outputs/` 目录。

### 运行探针测试
测试编码探针逻辑：
```bash
python scripts/test_encoding_probe.py
```

## 7. 当前状态 (v0.3.0)

目前项目处于 v0.3.0 迭代阶段，重点在于：
1.  确立了并行三探针的架构。
2.  实现了基础的编码和检索探针逻辑。
3.  定义了完整的适配器协议。
4.  提供了 LOCOMO 数据集的构建工具。

这是一个正在快速演进的框架，旨在为长期记忆系统提供标准化的“体检”工具。
