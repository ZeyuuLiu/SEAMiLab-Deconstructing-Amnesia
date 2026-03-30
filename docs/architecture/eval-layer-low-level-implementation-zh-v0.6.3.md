# 评估层底层实现详解（v0.6.3）

## 1. 文档目标

这份文档从代码实现角度解释评估框架如何运行，重点回答四个问题：

1. 三层探针（编码/检索/生成）底层分别做了什么。
2. 评估层如何通过适配器层和外部记忆系统通信。
3. 每个阶段的输入从哪里来、如何被处理。
4. 每个阶段的输出如何组织并汇总到最终报告。

## 2. 总体分层与职责

项目把评估系统拆成四层：

1. 数据构建层（dataset）
   - 负责把 LOCOMO 原始样本转换为评估样本 `EvalSample`。
2. 评估核心层（eval_core）
   - 负责三探针判定逻辑、缺陷归因、证据结构化。
3. 适配器层（adapters）
   - 负责“把外部记忆系统能力翻译成评估层可调用协议”。
4. 流水线层（pipeline + scripts）
   - 负责端到端批处理运行、错误收集、结果落盘。

关键代码入口：

- `src/memory_eval/pipeline/runner.py`
- `src/memory_eval/eval_core/engine.py`
- `src/memory_eval/eval_core/{encoding,retrieval,generation}.py`
- `src/memory_eval/eval_core/adapter_protocol.py`
- `src/memory_eval/adapters/{registry,o_mem_adapter,membox_adapter}.py`

## 3. 统一数据契约（输入/输出类型）

### 3.1 统一输入样本：`EvalSample`

`EvalSample` 是评估核心唯一依赖的样本结构，核心字段：

- `question`：用户问题
- `answer_gold`：标准答案
- `task_type`：`POS` 或 `NEG`
- `f_key`：关键事实列表
- `oracle_context`：完美上下文
- `evidence_texts/evidence_with_time`：证据文本

定义位置：`src/memory_eval/eval_core/models.py`

### 3.2 单探针输出：`ProbeResult`

每个探针都必须返回同构结构：

- `probe`：`enc | ret | gen`
- `state`：探针状态
- `defects`：缺陷码列表
- `evidence`：证据字典
- `attrs`：附加属性（如 `rank/snr/grounding_overlap`）

### 3.3 单样本最终输出：`AttributionResult`

三探针结果会被组装成单样本归因结构：

- `states`：`enc/ret/gen` 三状态
- `defects`：缺陷并集（有序）
- `probe_results`：每层完整输出
- `attribution_evidence`：证据分层块 + 决策轨迹

## 4. 端到端执行路径（从命令到报告）

### 4.1 CLI 组装运行参数

脚本 `scripts/run_eval_pipeline.py` 负责：

1. 读取 `--memory-system` 或 `--adapter-module/--adapter-class`
2. 创建 `EvaluatorConfig`
3. 构建 `ThreeProbeEvaluationPipeline`
4. 调用 `pipeline.run(adapter)`

严格策略开关由 CLI 直接映射到 `EvaluatorConfig`：

- `require_llm_judgement`
- `strict_adapter_call`
- `disable_rule_fallback`
- `require_online_answer`

### 4.2 Pipeline 运行主循环

`ThreeProbeEvaluationPipeline.run(...)` 执行顺序：

1. `build_locomo_eval_samples(...)` 构建样本。
2. 从 dataset 读取会话并标准化为 turn 列表。
3. 对每个 `sample_id` 调用一次 `adapter.ingest_conversation(...)`，缓存 `run_ctx`。
4. 对每条 query 调用 `evaluator.evaluate_with_adapters(...)`。
5. 成功结果写入 `results[]`，异常写入 `errors[]`。
6. 汇总 `summary` 并落盘 JSON。

输出 JSON 顶层结构：

- `config`
- `adapter_manifest`
- `summary`
- `results`
- `errors`

## 5. 三探针并行调度与归因收敛

### 5.1 并行执行

`ParallelThreeProbeEvaluator.evaluate_with_adapters(...)` 使用 `ThreadPoolExecutor` 并行提交：

1. 编码探针
2. 检索探针
3. 生成探针

并行完成后统一做后处理。

### 5.2 归因收敛规则

当前实现中的关键规则：

- 当编码层 `enc.state == MISS` 且检索层包含 `RF` 时，移除 `RF`。
- 然后按 `DEFECT_ORDER` 做缺陷并集。
- 在 `attribution_evidence.decision_trace` 记录抑制行为。

该规则用于防止把“编码没写入”误归因成“检索失败”。

## 6. 编码探针底层实现（Encoding）

文件：`src/memory_eval/eval_core/encoding.py`

### 6.1 输入获取链路

`evaluate_encoding_probe_with_adapter(...)` 按顺序取输入：

1. `adapter.export_full_memory(run_ctx)` 获取全量 `M`。
2. 若实现了 `hybrid_retrieve_candidates(...)`，先取高召回候选。
3. 若还没有候选，调用 `adapter.find_memory_records(...)`。
4. 若开启 `encoding_merge_native_retrieval`，额外合并 `retrieve_original(...)` 的候选。
5. 若仍为空且允许规则兜底，执行 `_fallback_find_records(...)` 全库扫描。

### 6.2 判定逻辑

`evaluate_encoding_probe(...)` 分两种路径：

1. LLM 判定优先
   - 调 `llm_judge_encoding_storage(...)` 返回结构化 `encoding_state/defects`。
2. 规则判定兜底
   - NEG：有候选即 `DIRTY(DMP)`，无候选即 `MISS`。
   - POS：按 `f_key` 匹配结果判 `EXIST/MISS/CORRUPT_AMBIG/CORRUPT_WRONG`。

### 6.3 输出内容

编码层输出包括：

- `state`：`EXIST | MISS | CORRUPT_AMBIG | CORRUPT_WRONG | DIRTY`
- `defects`：`EM | EA | EW | DMP`
- `evidence`：匹配候选 id、命中事实、推理原因、LLM 判定原文等

## 7. 检索探针底层实现（Retrieval）

文件：`src/memory_eval/eval_core/retrieval.py`

### 7.1 输入获取链路

`evaluate_retrieval_probe_with_adapter(...)`：

1. 直接调用 `adapter.retrieve_original(run_ctx, query, top_k)` 获取 `C_original`。
2. 标准化成统一 item 结构后进入纯判定函数。

### 7.2 判定逻辑

`evaluate_retrieval_probe(...)` 先算基础属性：

- `rank, hit_indices`：关键事实命中位置
- `snr`：token 重叠信噪比

再按任务类型判定：

1. NEG
   - 优先 LLM 判噪声；失败时可走分数阈值规则。
   - 结果为 `NOISE(NIR)` 或 `MISS`。
2. POS
   - 优先 LLM 给出 `HIT/MISS/NOISE + defects`。
   - 规则侧补充 `RF/LATE/NOI`。
   - `RF` 受 `s_enc != MISS` 约束。

### 7.3 输出内容

检索层输出包括：

- `state`：`HIT | MISS | NOISE`
- `defects`：`RF | LATE | NOI | NIR`
- `attrs`：`rank_index/snr/hit_count/top_score`
- `evidence`：top items、hit indices、snr 元信息、LLM 判定结构

## 8. 生成探针底层实现（Generation）

文件：`src/memory_eval/eval_core/generation.py`

### 8.1 输入获取链路

`evaluate_generation_probe_with_adapter(...)`：

1. `adapter.generate_oracle_answer(run_ctx, query, oracle_context)` 得到 `A_oracle`。
2. 若适配器实现 `generate_online_answer(...)`，获取 `A_online`。
3. 严格模式下要求 `A_online` 非空，否则报错。

### 8.2 判定逻辑

`evaluate_generation_probe(...)` 的主逻辑：

1. 先判断 `A_oracle` 是否正确（LLM 优先，规则兜底）。
2. 正确则 `PASS`。
3. 错误则 `FAIL`，并细分缺陷：
   - NEG 失败：`GH`
   - POS 失败：`GF` 或 `GRF`
4. 严格模式要求 LLM 明确给出子状态，否则报错。

### 8.3 输出内容

生成层输出包括：

- `state`：`PASS | FAIL`
- `defects`：`GH | GF | GRF`
- `attrs`：`grounding_overlap`
- `evidence`：`online/oracle/gold` 三答案对照、比较判定、LLM 原始结构

## 9. 适配器层如何与外部系统互联

文件：`src/memory_eval/eval_core/adapter_protocol.py`

评估层不依赖具体系统，只依赖协议接口：

1. 编码协议
   - `export_full_memory`
   - `find_memory_records`
   - `hybrid_retrieve_candidates`（可选）
2. 检索协议
   - `retrieve_original`
3. 生成协议
   - `generate_oracle_answer`
   - `generate_online_answer`（可选但严格模式必需）

这意味着外部系统只要实现这些方法，就能被评估层直接接入。

## 10. 适配器注册与实例化机制

文件：`src/memory_eval/adapters/registry.py`

机制要点：

1. `_ADAPTER_BUILDERS` 把 `memory_system key -> builder` 映射固定下来。
2. `create_adapter_by_system(...)` 统一创建适配器实例。
3. `export_adapter_runtime_manifest(...)` 把适配器配置写入报告，便于复现实验。

当前注册项：

- `o_mem`
- `o_mem_stable_eval`
- `membox`
- `membox_stable_eval`

## 11. 外部系统接入示例：O-Mem 适配器

文件：`src/memory_eval/adapters/o_mem_adapter.py`

### 11.1 运行态上下文

`ingest_conversation(...)` 把会话转成系统运行态 `run_ctx`：

- real 模式：调用真实 O-Mem 构建上下文
- lightweight 模式：本地近似内存视图

### 11.2 提供评估层所需能力

O-Mem 适配器实现了完整协议：

1. `export_full_memory`：导出编码层可读内存视图
2. `find_memory_records`：执行事实/关键词匹配
3. `hybrid_retrieve_candidates`：编码层高召回候选
4. `retrieve_original`：导出原生检索载荷
5. `generate_oracle_answer`：完美上下文回答
6. `generate_online_answer`：正常链路回答

### 11.3 real 与 fallback 策略

`OMemAdapterConfig` 支持 `use_real_omem` 与 `allow_fallback_lightweight`，可控制：

- 是否强制使用真实系统路径
- 真实路径失败时是否降级

这与评估层 `strict_adapter_call` 的 fail-fast 策略共同决定运行行为。

## 12. 严格模式与失败语义

`EvaluatorConfig` 默认是严格策略，核心语义是“完整链路、失败即报错”：

1. 关键适配器调用失败直接抛错。
2. 必要 LLM 判定缺失直接抛错。
3. 禁止规则兜底时，不允许 silent fallback。
4. `A_online` 缺失在严格模式下视为错误。

pipeline 会把异常记录到 `errors[]`，状态记为 `EVAL_ERROR`，而不是静默吞掉。

## 13. 最终你在报告中能拿到什么

你最终可以得到两类信息：

1. 样本级可解释归因（results）
   - 三层状态
   - 缺陷并集
   - 每层证据与属性
2. 运行级统计与可复现信息（summary + adapter_manifest + config）
   - 缺陷计数
   - 状态计数
   - 运行参数与适配器配置

这套结构能支撑后续两类工作：

1. 继续深挖单样本错误根因。
2. 在批量层做指标聚合与看板扩展。

## 14. 当前实现边界

当前评估层已经完成“可运行的三探针归因闭环”，但“最终指标层（M_*/R_*/G_*）与系统诊断看板”尚未在代码中聚合输出。

也就是说：

1. 你已经有可解释缺陷归因引擎。
2. 下一步可以在现有 `results/summary` 之上增加指标计算器与看板聚合器，而不需要重写三探针主干。
