# 评估层 Agent 化重构实现说明（v0.1）

## 1. 文档目标

这份文档说明这次已经完成的评估层代码重构内容。

目标不是继续提方案，而是明确：

1. 这次代码到底改了什么
2. 现在评估层如何运行
3. 三个并行评估探针 Agent 和最终归因 Agent 如何协作
4. 编码层 Agent 的显式接口是什么
5. 当前版本还保留了哪些兼容性设计

## 2. 本次重构后的总体结构

现在评估层已经从原来的“probe function + engine”结构，推进到“**三个并行评估 Agent + 一个最终归因 Agent**”结构。

当前四个核心 Agent 为：

1. `EncodingAgent`
2. `RetrievalAgent`
3. `GenerationAgent`
4. `AttributionAgent`

其中：

- 前三个 Agent 在 `ParallelThreeProbeEvaluator` 中并行执行
- `AttributionAgent` 在三个 Agent 完成后统一汇总归因

## 3. 新增与重构的核心代码位置

本次核心改动集中在：

1. `src/memory_eval/eval_core/encoding_agent.py`
2. `src/memory_eval/eval_core/retrieval_agent.py`
3. `src/memory_eval/eval_core/generation_agent.py`
4. `src/memory_eval/eval_core/attribution_agent.py`
5. `src/memory_eval/eval_core/engine.py`
6. `src/memory_eval/eval_core/models.py`
7. `src/memory_eval/eval_core/encoding.py`
8. `src/memory_eval/eval_core/probes.py`
9. `src/memory_eval/eval_core/__init__.py`

## 4. 当前执行链路

现在单样本评估的执行顺序是：

1. pipeline 准备样本与 `run_ctx`
2. `ParallelThreeProbeEvaluator` 创建三个并行任务
3. 分别调用：
   - `EncodingAgent`
   - `RetrievalAgent`
   - `GenerationAgent`
4. 三个 Agent 返回各自 `ProbeResult`
5. `AttributionAgent` 接收三层结果
6. 输出最终 `AttributionResult`

也就是说，现在的评估层主干已经具备明确的 Agent 边界，而不是只靠几个函数直接拼接。

## 5. EncodingAgent 已实现的接口

编码层现在是这次重构的重点。

当前已经提供了显式接口：

### 5.1 样本级主入口

1. `build_evidence_spec(sample)`
2. `collect_observations(sample, adapter, run_ctx, cfg, retrieval_adapter=None, top_k=None)`
3. `assess_bundle(evidence_spec, bundle, cfg)`
4. `to_probe_result(assessment, evidence_spec, bundle)`
5. `evaluate_with_adapter(...)`
6. `evaluate(...)`

这意味着编码层不再只是一个“黑盒判定函数”，而是已经具备：

1. 证据合同构建
2. 多源观测采集
3. 存在性裁判
4. 标准结果映射

## 6. EncodingAgent 的内部阶段

当前实现已经按下面的语义分层：

### 6.1 证据规范化

通过 `build_evidence_spec(sample)` 把样本中的：

1. `query`
2. `f_key`
3. `evidence_texts`
4. `evidence_with_time`
5. `oracle_context`
6. `task_type`

整理成统一的 `EvidenceSpec`。

这一步的意义是：

1. 编码层不再只吃 `f_key`
2. 后面所有裁判都围绕统一证据合同进行

### 6.2 多源观测采集

通过 `collect_observations(...)` 编码层会采集以下来源：

1. `full_memory_view`
2. `native_candidate_view`
3. `framework_candidate_view`
4. `native_retrieval_shadow`

这一步已经把“编码层看到的世界”从单一候选列表升级成了一个 **观测束**。

### 6.3 候选组合

当前实现已经引入：

1. `combined_candidates`
2. `candidate_groups`

这意味着编码层不只看单条记录，还能构造：

1. 单条候选
2. 跨记录组合候选

虽然当前组合逻辑还是第一版，但结构已经搭起来了。

### 6.4 存在性裁判

`assess_bundle(...)` 负责：

1. 严格模式下优先走 LLM holistic judgement
2. 非严格模式下保留规则路径
3. 输出 `EncodingAssessment`

### 6.5 结果映射

`to_probe_result(...)` 负责把 richer 内部结果压缩为兼容现有框架的 `ProbeResult`。

因此这次重构的一个关键目标已经实现：

> **对内 richer，对外兼容。**

## 7. 新增的核心中间对象

本次已经在 `models.py` 中新增了以下结构：

1. `EvidenceSpec`
2. `MemoryObservation`
3. `CandidateGroup`
4. `MemoryObservationBundle`
5. `EncodingAssessment`

这五个对象的意义分别是：

### 7.1 EvidenceSpec

负责承载 gold evidence 合同。

### 7.2 MemoryObservation

负责承载单条可观测记忆对象及其来源信息。

### 7.3 CandidateGroup

负责表达组合候选。

### 7.4 MemoryObservationBundle

负责表达“本次编码判定到底看了哪些观测来源”。

### 7.5 EncodingAssessment

负责承载编码层内部最终 richer 结果。

## 8. RetrievalAgent 与 GenerationAgent 的完善

检索层和生成层原本已经比较接近“简单 Agent”，这次重构主要做了两件事：

1. 给它们加上正式的 Agent 类封装
2. 在输出 evidence 中显式写入 `agent_name`

也就是说：

- `RetrievalAgent` 现在已经成为正式的评估组件
- `GenerationAgent` 现在已经成为正式的评估组件

当前它们仍然复用原来的主判定逻辑，这样做的好处是：

1. 保持稳定
2. 不破坏已有测试
3. 先完成架构重构，再逐步强化内部能力

## 9. AttributionAgent 已完成的工作

现在最终归因逻辑已经不再直接散落在 `engine.py` 里，而是抽成了独立的 `AttributionAgent`。

当前它负责：

1. 接收 `enc/ret/gen` 三层结果
2. 保留原有的核心门控规则
   - 例如 `enc=MISS` 时抑制 `RF`
3. 输出：
   - `primary_cause`
   - `secondary_causes`
   - `cross_probe_summary`

这意味着归因层已经从“结果合并逻辑”变成了“显式归因 Agent 雏形”。

## 10. engine 的变化

这次重构中，`engine.py` 的职责被收敛得更明确。

现在它主要负责：

1. 初始化四个 Agent
2. 并行运行前三个评估 Agent
3. 把结果交给 `AttributionAgent`

换句话说：

- `engine` 不再亲自做 probe 级判定
- `engine` 现在更像 Agent 调度器

这和你要求的“整体评估层为三个并行评估探针 agent，以及一个最终归因 agent”是对齐的。

## 11. 当前版本的兼容性策略

这次重构没有直接推翻现有外部接口，而是保留了兼容层。

### 11.1 保持不变的外部入口

当前仍然保留：

1. `evaluate_encoding_probe(...)`
2. `evaluate_encoding_probe_with_adapter(...)`
3. `evaluate_retrieval_probe(...)`
4. `evaluate_retrieval_probe_with_adapter(...)`
5. `evaluate_generation_probe(...)`
6. `evaluate_generation_probe_with_adapter(...)`

### 11.2 兼容方式

其中编码层入口现在会转调 `EncodingAgent`。

这样现有调用方不用立刻全改，但底层已经切换为 Agent 化结构。

## 12. 当前版本已经解决的问题

这次重构已经解决了几个关键问题。

### 12.1 编码层显式接口缺失

现在编码层已经不只是一个 probe function，而是有了明确的 Agent 方法边界。

### 12.2 最终归因逻辑散落

现在归因已经抽到 `AttributionAgent`。

### 12.3 评估层没有明确 Agent 边界

现在已经明确成四个 Agent：

1. 编码
2. 检索
3. 生成
4. 归因

### 12.4 编码层缺少观测束

现在已经引入 `MemoryObservationBundle`。

## 13. 当前版本仍然保留的限制

虽然这次已经完成 Agent 化重构主干，但仍有一些限制是刻意保留的。

### 13.1 RetrievalAgent 和 GenerationAgent 仍偏“薄封装”

它们已经是正式 Agent，但内部裁判逻辑还基本沿用原有实现。

后续可以继续增强：

1. 更细的中间对象
2. 更完整的证据链结构
3. 更强的局部 LLM judge 机制

### 13.2 编码层组合判断还是第一版

当前已经支持组合候选结构，但组合策略还不够复杂。

后续仍可继续增强：

1. session 级组合
2. subject 级组合
3. 时间对齐组合
4. conflict-specific 局部裁判

### 13.3 AttributionAgent 目前还是“规则约束 + 摘要归因”

它已经独立成 Agent，但还没有引入单独的大模型归因裁判。

这一步适合放到后续版本继续做。

## 14. 当前版本为什么是合理的

我认为这次重构策略是合理的，因为它实现了三件非常重要的事：

1. 架构先立住了
2. 行为基本兼容
3. 现有测试仍能跑通

这意味着你现在得到的不是一个“推倒重来、风险很高的半成品”，而是一个：

> **已经切到 Agent 化架构，但仍保持现有框架可运行的过渡版本。**

## 15. 后续建议

基于当前版本，后续最值得继续做的方向有三个：

1. 深化 EncodingAgent
   - 更强的候选组合
   - 更强的局部 judge
   - 更强的 coverage 解释

2. 深化 RetrievalAgent / GenerationAgent
   - 引入更完整的 assessment 对象
   - 让它们和 EncodingAgent 一样拥有 richer 内部结构

3. 强化 AttributionAgent
   - 增加大模型归因解释层
   - 标准化跨层证据链

## 16. 结论

这次代码重构已经把评估层主干改造成：

1. 三个并行评估探针 Agent
2. 一个最终归因 Agent

并且编码层 Agent 已经具备了你要求的显式接口与中间结构。

当前版本最重要的价值不是“所有高级能力都已经做完”，而是：

> **Agent 化的架构骨架已经真正落到代码里了，后续增强有了稳定的挂载点。**
