# EncodingAgent 详细技术设计（v0.1）

## 1. 文档目标

这份文档是对上一份方案文档的继续细化。

上一份文档已经说明了：

1. 三层探针应被重新理解为三个评估 Agent
2. 编码层本质上是“证据存在性裁判问题”
3. 最终还需要一个 AttributionAgent 做跨层归因

这份文档只聚焦一件事：

> **把 EncodingAgent 落到可以指导代码重构的技术设计层面。**

目标是回答下面几个问题：

1. EncodingAgent 的职责边界到底是什么
2. 它的输入输出 schema 应该如何定义
3. 它内部应拆成哪些阶段
4. 它如何和适配器层协同
5. 它如何判断“证据存在”
6. 它如何输出高质量证据链
7. 它如何兼容当前仓库已有代码结构

## 2. 设计前提

本文以当前项目现状为前提：

- 项目目录：`/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia`
- 主设计文档：`docs/最终指标.md`
- 当前编码层实现：`src/memory_eval/eval_core/encoding.py`
- 当前适配器协议：`src/memory_eval/eval_core/adapter_protocol.py`

同时，本文继承上一份方案文档中的三个核心约束：

1. 编码层不等于检索层
2. 编码层不是回答“系统有没有取出来”，而是回答“系统内部有没有存”
3. 编码层必须保留完整证据链，不能只返回一个标签

## 3. EncodingAgent 的正式职责定义

我建议把 EncodingAgent 定义为：

> **在给定 query、gold evidence、系统可观测记忆视图和候选集合的条件下，判断当前被测记忆系统是否以可接受形式真实存储了回答该 query 所需证据，并输出结构化证据链。**

这个定义里面有四个关键词。

### 3.1 “给定 query”

EncodingAgent 不是盲评，它知道当前用户问了什么。

query 的作用不是直接做匹配，而是：

1. 帮助锁定证据范围
2. 帮助理解问题意图
3. 在 gold evidence 过长时决定哪些事实更关键

### 3.2 “gold evidence”

EncodingAgent 不应该只吃 `f_key`。

它应该尽量吸收数据集中可获得的全部上帝视角信息：

1. `f_key`
2. `evidence_texts`
3. `evidence_with_time`
4. `oracle_context`
5. `task_type`

也就是说，EncodingAgent 是在评测条件下工作的，它比真实系统拥有更多信息，这正是编码层存在的意义。

### 3.3 “系统可观测记忆视图”

EncodingAgent 不是直接访问系统内部内存对象，而是访问适配器导出的观测。

因此它只能在“可观测性边界”内做判断。

所以编码层输出时必须带一个重要结论：

> 本次判断是在什么观测覆盖范围内作出的。

### 3.4 “以可接受形式真实存储”

这里的“真实存储”不是字面硬匹配，而是允许下面四种存在形式：

1. **Literal existence**
   - 字面存在
2. **Structured existence**
   - 结构字段可重建
3. **Semantic existence**
   - 语义等价存在
4. **Compositional existence**
   - 多条记录联合存在

## 4. EncodingAgent 的非职责边界

为了避免编码层无限膨胀，必须明确它不负责什么。

EncodingAgent 不负责：

1. 判断检索结果是否召回
2. 判断生成答案是否正确
3. 判断最终系统失败责任优先级
4. 直接修改或修复记忆系统
5. 推断系统内部不可观测区域的真实状态

特别是第五点非常重要。

EncodingAgent 可以输出：

- “在当前可观测范围内未发现证据”

但不应该假装自己知道：

- “系统绝对没有存”

因此我们需要把“结论”和“覆盖率”一起输出。

## 5. EncodingAgent 的总体架构

我建议把 EncodingAgent 内部分成六个模块：

1. `EvidenceNormalizer`
2. `ObservationCollector`
3. `CandidateFusionEngine`
4. `ExistenceJudge`
5. `EvidenceCompressor`
6. `EncodingResultMapper`

这六个模块不是必须做成六个类，但在设计语义上应明确分离。

### 5.1 EvidenceNormalizer

职责：

1. 从 `EvalSample` 中抽取证据
2. 构建统一 `EvidenceSpec`
3. 把自然语言证据转成结构化判定合同

### 5.2 ObservationCollector

职责：

1. 向适配器请求可观测视图
2. 统一成框架内部可处理的观测格式
3. 形成 `MemoryObservationBundle`

### 5.3 CandidateFusionEngine

职责：

1. 合并不同来源候选
2. 去重
3. 来源打标
4. 生成组合候选

### 5.4 ExistenceJudge

职责：

1. 综合 evidence 和候选
2. 判断 `EXIST/MISS/CORRUPT_AMBIG/CORRUPT_WRONG/DIRTY`
3. 生成支持证据和反驳证据

### 5.5 EvidenceCompressor

职责：

1. 把过长候选压缩成可归因摘要
2. 形成供 AttributionAgent 使用的证据链摘要

### 5.6 EncodingResultMapper

职责：

1. 把内部评估结果映射回统一外部输出
2. 保持和当前 `ProbeResult` 兼容

## 6. 核心中间对象设计

这是最关键的一节。  
因为后续代码是否容易重构，核心取决于中间对象是否定义清楚。

## 6.1 EvidenceSpec

`EvidenceSpec` 是 EncodingAgent 的 gold evidence 合同对象。

建议字段如下：

1. `query`
2. `task_type`
3. `question_id`
4. `sample_id`
5. `f_key`
6. `evidence_texts`
7. `evidence_with_time`
8. `oracle_context`
9. `fact_units`
10. `must_have_constraints`
11. `soft_constraints`
12. `negative_constraints`
13. `evidence_priority`
14. `normalization_notes`

### 6.1.1 fact_units

这是最重要字段。

建议把证据拆成一组细粒度事实单元，每个单元可类似：

1. `subject`
2. `predicate`
3. `object`
4. `time`
5. `location`
6. `qualifier`

目的不是强行做知识图谱，而是：

> 把“文本证据”转换为“可判定结构”。

### 6.1.2 must_have_constraints

表示判定 EXIST 所必须满足的条件。

例如：

1. 人物必须命中
2. 核心事件必须命中
3. 时间若是判题关键则必须命中

### 6.1.3 soft_constraints

表示增强置信度但不是强制的条件。

例如：

1. 说话人信息
2. 会话编号
3. 细粒度时间格式

### 6.1.4 negative_constraints

用于 NEG 样本。

例如：

1. 不应出现与 query 强相关的虚假支撑记忆
2. 不应出现可直接支撑回答的伪证据

## 6.2 MemoryObservation

这是对一条可观测记忆记录的统一封装。

建议字段如下：

1. `memory_id`
2. `text`
3. `normalized_text`
4. `source_type`
5. `source_name`
6. `storage_kind`
7. `speaker`
8. `timestamp`
9. `session_id`
10. `score`
11. `meta`
12. `raw_payload_ref`

### 6.2.1 source_type

建议固定枚举：

1. `full_memory_export`
2. `native_candidate`
3. `framework_candidate`
4. `native_retrieval_shadow`
5. `synthetic_combination`

这样后面做证据链解释时会非常清楚。

## 6.3 MemoryObservationBundle

这是编码层最重要的新对象。

它表示：

> 为了判断编码状态，本次评测到底看到了哪些观测来源。

建议字段：

1. `full_memory_view`
2. `native_candidate_view`
3. `framework_candidate_view`
4. `native_retrieval_shadow`
5. `combined_candidates`
6. `adapter_manifest`
7. `observability_notes`
8. `coverage_report`

### 6.3.1 coverage_report

这是当前代码最缺的能力。

建议包含：

1. 是否导出了全量记忆
2. 是否只导出了分页/截断视图
3. 是否使用系统原生候选
4. 是否使用框架弱混合候选
5. 是否合并了检索层影子结果
6. 本次观测盲区说明

## 6.4 CandidateGroup

当前代码基本把候选扁平化成一个 list，这不够。

我建议再引入 `CandidateGroup`：

1. `group_id`
2. `member_ids`
3. `group_type`
4. `aggregated_text`
5. `supporting_slots`
6. `source_breakdown`
7. `confidence_hint`

### 6.4.1 group_type

建议至少支持：

1. `single_record`
2. `same_session`
3. `same_subject`
4. `same_timestamp`
5. `cross_record_composition`

这是为了支撑“组合存在性判断”。

## 6.5 EncodingAssessment

这是 EncodingAgent 内部最终结果对象。

建议字段：

1. `state`
2. `defects`
3. `confidence`
4. `matched_ids`
5. `supporting_snippets`
6. `contradicting_snippets`
7. `missing_fact_units`
8. `ambiguous_fact_units`
9. `coverage_report`
10. `reasoning_chain`
11. `evidence_found_by`
12. `risk_flags`
13. `debug_payload`

### 6.5.1 evidence_found_by

建议取值：

1. `single_record`
2. `structured_fields`
3. `semantic_equivalence`
4. `record_combination`
5. `not_found`
6. `dirty_memory_detected`

这个字段能极大提升解释性。

## 7. EncodingAgent 的输入输出 schema

## 7.1 输入 schema

EncodingAgent 的输入不应该再是当前这种松散参数，而应该是：

1. `evidence_spec`
2. `observation_bundle`
3. `agent_config`

### 7.1.1 agent_config

建议字段：

1. `strict_mode`
2. `allow_framework_fallback`
3. `enable_combination_search`
4. `max_candidate_count`
5. `max_group_count`
6. `require_llm_judgement`
7. `llm_model`
8. `llm_temperature`
9. `confidence_thresholds`
10. `coverage_policy`

## 7.2 输出 schema

对外先不破坏现有结构，仍映射成：

1. `ProbeResult`

但对内必须先输出：

1. `EncodingAssessment`

推荐输出分两层：

1. **内部标准输出**
   - `EncodingAssessment`
2. **外部兼容输出**
   - `ProbeResult(probe="enc", ...)`

## 8. EncodingAgent 的阶段化执行流程

下面给出完整执行流程。

## 8.1 Stage A：构建 EvidenceSpec

输入：

1. `EvalSample`

过程：

1. 提取 `query`
2. 提取 `task_type`
3. 提取 `f_key`
4. 提取 `evidence_texts/evidence_with_time`
5. 提取 `oracle_context`
6. 构建 `fact_units`
7. 推导 must-have / soft / negative constraints

输出：

1. `EvidenceSpec`

### 为什么要做这一步

因为当前代码是把 `f_key` 和 `evidence_texts` 直接散着传，这样后面做高级裁判会越来越乱。

## 8.2 Stage B：采集多源观测

输入：

1. `run_ctx`
2. `adapter`
3. `EvidenceSpec`

过程：

1. 取 `export_full_memory`
2. 取 `hybrid_retrieve_candidates`
3. 取 `find_memory_records`
4. 取 `retrieve_original` 影子观测
5. 统一标准化为 `MemoryObservation`

输出：

1. `MemoryObservationBundle`

### 关键要求

不能只返回“候选列表”，而必须保留来源信息。

## 8.3 Stage C：候选融合

输入：

1. `MemoryObservationBundle`
2. `EvidenceSpec`

过程：

1. 统一文本规范化
2. 去重
3. 同源聚类
4. 交叉来源聚类
5. 组合候选生成

输出：

1. `combined_candidates`
2. `candidate_groups`

### 为什么必须做这一层

因为编码层很容易出现：

- 单条不命中
- 联合后命中

如果没有组合层，编码层就只能一直误判 MISS。

## 8.4 Stage D：存在性裁判

输入：

1. `EvidenceSpec`
2. `MemoryObservationBundle`
3. `CandidateGroups`

过程：

1. 先做轻量规则筛查
2. 再做 LLM 综合裁判
3. 必要时对冲突候选再做二次局部裁判

输出：

1. `EncodingAssessment`

### 为什么不是纯 LLM 一步到位

因为一步到位会有三个问题：

1. 输入过长
2. 解释链不稳定
3. 难以复盘局部争议

所以更好的方式是：

1. 规则和结构化预处理负责缩小范围
2. LLM 负责最终存在性裁判

## 8.5 Stage E：证据压缩与摘要

输入：

1. `EncodingAssessment`

过程：

1. 压缩 supporting snippets
2. 压缩 contradicting snippets
3. 生成 coverage 摘要
4. 生成供 AttributionAgent 使用的摘要版证据链

输出：

1. `compressed_assessment`

## 8.6 Stage F：映射到兼容输出

输入：

1. `EncodingAssessment`

输出：

1. `ProbeResult`

这样当前 `engine.py`、`pipeline/runner.py` 都可以先不动。

## 9. 如何判断“证据存在”

这是整个设计最关键的问题。

我建议把“存在性判断”做成分层裁决，而不是单一判决。

## 9.1 判定层一：literal hit

是否存在字面近似命中：

1. 关键实体命中
2. 关键事件短语命中
3. 关键时间表达命中

若命中充分，可以直接形成高置信候选。

## 9.2 判定层二：structured reconstruction

是否能从结构字段重建证据：

1. entity 命中
2. event 命中
3. time 命中

即使文本不完全一致，也可以视为存在。

## 9.3 判定层三：semantic equivalence

是否存在语义等价表达。

这一层必须主要依赖 LLM。

但建议 LLM 判定时不要问模糊问题，而要问：

1. 这条候选是否表达了相同事件
2. 时间是否等价
3. 参与者是否一致
4. 是否存在值错误

## 9.4 判定层四：compositional existence

若单条记录不足以支撑，则看组合后是否成立。

例如：

1. 记录 A 提供实体
2. 记录 B 提供事件
3. 记录 C 提供时间

三条联合是否能支持同一 gold evidence。

## 9.5 最终状态映射

建议映射规则如下。

### EXIST

满足：

1. must-have constraints 被满足
2. 没有核心值冲突
3. 观测来源足以支撑结论

### MISS

满足：

1. 在当前观测范围内未发现足够证据
2. 不是因为值错误或模糊表达导致

### CORRUPT_AMBIG

满足：

1. 找到了相关候选
2. 但核心指代模糊
3. 无法唯一支撑 gold evidence

### CORRUPT_WRONG

满足：

1. 找到了相关候选
2. 但核心值与 gold evidence 冲突
3. 不是简单缺失，而是存错了

### DIRTY

满足：

1. 对于 NEG 样本，发现了不应存在的虚假支撑记忆
2. 这些记忆足以诱导系统回答

## 10. LLM Judge 设计建议

这里我建议不要把 EncodingAgent 做成“单 prompt 大包判断”，而要分三层 prompt。

## 10.1 Prompt A：EvidenceSpec 规范化

作用：

1. 从 `query + evidence` 提取 fact units
2. 生成 must-have constraints

输出是结构化 schema，而不是最终结论。

## 10.2 Prompt B：候选局部匹配判断

作用：

1. 判断某条候选或某组候选是否支持某个 fact unit

适用于：

1. 单候选
2. 组合候选
3. 冲突候选

## 10.3 Prompt C：最终存在性裁判

作用：

1. 综合 EvidenceSpec 和候选支持情况
2. 输出最终 `encoding_state`
3. 输出 `defects`
4. 输出 `reasoning_chain`

### 为什么建议三层 prompt

因为这会让系统更稳定：

1. 可诊断
2. 可分步缓存
3. 可局部重试
4. 便于后续评估 prompt 自身质量

## 11. 失败语义设计

EncodingAgent 需要非常明确的失败语义。

我建议区分两类失败。

## 11.1 Agent 评估失败

例如：

1. LLM 返回非法 JSON
2. 必需字段缺失
3. 候选构造失败
4. 观测对象无法标准化

这类失败应直接形成：

1. `EVAL_ERROR`

而不应偷偷回退成规则匹配。

## 11.2 证据不存在

这不是系统错误，而是正常评估结果。

因此：

- `MISS` 是结论
- `EVAL_ERROR` 是过程失败

两者不能混。

## 12. 与当前代码的兼容落点

为了降低重构成本，我建议分层兼容。

## 12.1 当前可直接复用的部分

1. `EvalSample`
2. `EvaluatorConfig`
3. `export_full_memory`
4. `find_memory_records`
5. `hybrid_retrieve_candidates`
6. `retrieve_original`
7. `ProbeResult`

## 12.2 当前最需要被抽离的部分

1. `encoding.py` 中观测获取逻辑
2. `encoding.py` 中候选合并逻辑
3. `encoding.py` 中 rule fallback 逻辑
4. `llm_assist.py` 中单阶段粗粒度 prompt 逻辑

## 12.3 当前最适合新增的层

1. `encoding_types.py`
2. `encoding_observation.py`
3. `encoding_agent.py`
4. `encoding_mapper.py`

## 13. 推荐类与函数边界

后续实现时，我建议至少形成下面这些边界。

### 13.1 EvidenceNormalizer

建议方法：

1. `build_evidence_spec(sample) -> EvidenceSpec`

### 13.2 ObservationCollector

建议方法：

1. `collect(adapter, run_ctx, evidence_spec, cfg) -> MemoryObservationBundle`

### 13.3 CandidateFusionEngine

建议方法：

1. `fuse(bundle, evidence_spec, cfg) -> list[CandidateGroup]`

### 13.4 EncodingAgent

建议方法：

1. `assess(evidence_spec, bundle, cfg) -> EncodingAssessment`

### 13.5 EncodingResultMapper

建议方法：

1. `to_probe_result(assessment) -> ProbeResult`

## 14. 推荐最小可落地版本

如果不想一开始做太大，我建议先做一个 MVP。

MVP 只要完成：

1. 引入 `EvidenceSpec`
2. 引入 `MemoryObservationBundle`
3. 引入 `EncodingAssessment`
4. 支持多来源候选保留来源标签
5. 支持组合候选
6. 输出 `coverage_report`

这六点落地之后，编码层就会从“当前版本”跃迁到“可持续演进版本”。

## 15. 推荐增强版

增强版再继续做：

1. 分阶段 LLM prompts
2. conflict-specific 二次裁判
3. 可缓存局部判断
4. 候选组合搜索优化
5. 对不同存储类型的 specialized observation policy

## 16. 结论

我对 EncodingAgent 的最终判断是：

> 它不是一个“编码匹配函数”，而是一个“证据存在性评估器”。

它的核心不是匹配，而是：

1. 统一证据合同
2. 聚合多源观测
3. 判断存在性
4. 解释判断依据
5. 把结论压缩成后续 AttributionAgent 可消费的标准证据链

因此后续重构的重点不应只是“把 `encoding.py` 改得更复杂”，而应是：

> **围绕 EncodingAgent 建立一套中间对象与阶段化执行结构。**
