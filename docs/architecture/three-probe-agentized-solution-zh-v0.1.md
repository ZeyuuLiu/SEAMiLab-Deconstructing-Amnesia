# 三层探针 Agent 化评估方案说明（聚焦编码层证据存在性判断）

## 1. 文档目的

这份文档不是代码实现说明，而是下一阶段的方案说明文档。

目标有三个：

1. 把你定义的三层探针明确重述为三个评估 Agent。
2. 在不推翻现有代码框架的前提下，给出一套更完整的 Agent 化评估方案。
3. 重点解决编码层最难的问题：如何判断“该系统是否真实存储了当前 query 所需证据”。

本文默认以当前仓库现状为基线：

- 项目根目录：`/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia`
- 设计主文档：`docs/最终指标.md`
- 当前实现主链路：`dataset -> adapter -> three probes -> attribution`

## 2. 先明确：我对你目标的理解

你现在要的不是“再加几个普通函数”，而是要把评估层重新解释成一套 **多 Agent 协作评估系统**：

1. **编码层 Agent**
   - 目标不是看模型答没答对，而是判断记忆系统内部是否真的存有与当前问题相关的证据。
   - 由于不同系统底层存储结构不同，所以必须有系统级适配能力。
   - 同时，希望尽量把通用逻辑收进评估框架内部，减少每个记忆系统重复写复杂适配代码。

2. **检索层 Agent**
   - 输入原记忆系统真实检索结果。
   - 再与标准证据对比，输出检索层状态与证据。

3. **生成层 Agent**
   - 输入完美证据上下文下的输出、原系统正常链路输出、标准答案。
   - 输出生成层状态与证据。

4. **最终归因 Agent**
   - 接收前三个 Agent 的输入与证据链。
   - 输出最终归因，而不是只做简单缺陷并集。
   - 需要保留完整证据链，明确解释该 query 为什么失败、主要责任在哪一层。

我认为这个方向是合理的，而且和你现在的代码现状并不冲突：  
当前代码已经有了三探针框架、适配器层、LLM judge，只是还没有把它们明确组织成“多 Agent 协作结构”。

## 3. 当前代码现状和这个方案的关系

当前代码已经具备以下基础：

1. 有统一样本结构 `EvalSample`
2. 有三探针执行入口 `ParallelThreeProbeEvaluator`
3. 有适配器协议：
   - `export_full_memory`
   - `find_memory_records`
   - `hybrid_retrieve_candidates`
   - `retrieve_original`
   - `generate_oracle_answer`
   - `generate_online_answer`
4. 有三层独立 LLM judge
5. 有最终归因结果 `AttributionResult`

所以，这个方案不要求你推翻现有框架，而是建议把当前框架重构为下面的认知结构：

- **现在**：三层 probe + adapter + engine
- **目标**：三层评估 Agent + 最终归因 Agent + 可复用观测合同 + 证据链标准

也就是说，当前代码可以视为未来 Agent 化方案的 **第一版执行骨架**。

## 4. 目标架构：四个 Agent 协作

我建议把评估层正式抽象成四个 Agent：

1. `EncodingAgent`
2. `RetrievalAgent`
3. `GenerationAgent`
4. `AttributionAgent`

它们不是聊天意义上的“对话代理”，而是 **四个有明确输入、输出、证据合同、失败语义的评估决策体**。

### 4.1 EncodingAgent

职责：

1. 获取和 query 相关的记忆观测
2. 判断目标证据是否真实存在于系统记忆中
3. 输出编码层状态、缺陷、证据链、置信度

### 4.2 RetrievalAgent

职责：

1. 读取系统真实检索输出
2. 判断标准证据是否被有效召回
3. 输出检索层状态、缺陷、证据链、排序/噪声属性

### 4.3 GenerationAgent

职责：

1. 比较 `A_online / A_oracle / A_gold`
2. 判断问题到底出在忠实度、推理能力还是幻觉
3. 输出生成层状态、缺陷、证据链

### 4.4 AttributionAgent

职责：

1. 接收前三个 Agent 的结果
2. 做跨层因果归因
3. 输出最终缺陷结论、责任优先级、解释性证据链

## 5. 为什么编码层最难

检索层和生成层之所以相对清楚，是因为它们面对的是比较稳定的对象：

1. 检索层面对的是 `C_original`
2. 生成层面对的是 `A_online / A_oracle / A_gold`

这两个层级的输入都已经是“显式可见对象”。

但编码层的问题是：

> “系统内部到底有没有存这条证据？”

这不是一个简单的字符串匹配问题，而是一个 **系统内部状态可观测性问题**。

难点主要有六个：

1. **底层存储异构**
   - 可能是 JSON
   - 可能是 SQLite
   - 可能是向量数据库
   - 可能是图结构
   - 可能是 working / episodic / semantic 多层混合

2. **证据表达形式变化**
   - 标准证据是一种表达
   - 系统写入时可能被压缩、改写、抽象、拆分、融合

3. **不能只靠精确字符串匹配**
   - 时间格式可能不同
   - 人称可能不同
   - 事实可能被拆到多条记录里

4. **不能只看原生检索结果**
   - 检索没召回，不等于没存
   - 编码判断应该比检索更接近“上帝视角”

5. **不能无限制全库暴力扫描**
   - 某些系统没有完整导出能力
   - 某些系统导出成本过高

6. **需要可解释证据链**
   - 不能只输出“EXIST/MISS”
   - 必须回答“你为什么这么判”

因此，编码层本质上不是简单的 rule-based matching，而是：

> **一个基于多源观测的证据存在性裁判问题**

## 6. 编码层的核心设计原则

我建议编码层方案遵循六条原则。

### 6.1 原则一：适配器负责“可观测性”，框架负责“裁决”

必须明确区分：

1. **适配器职责**
   - 告诉评估器“这个系统里有什么可以被观测”
   - 把内部存储翻译成统一格式
   - 提供系统原生候选召回能力

2. **框架职责**
   - 用统一合同组织观测输入
   - 调用 EncodingAgent 做综合判断
   - 统一输出状态与证据链

如果不这样分，问题会变成：

- 每个系统各写一套编码判定器
- 最后不同系统的判定标准不一致

这会直接毁掉横向可比性。

### 6.2 原则二：编码层判断必须基于“证据对象”，不是只基于 query

仅有 query 不够。

因为 query 通常是自然语言提问，而你评估时其实额外拥有：

1. `f_key`
2. `evidence_texts`
3. `evidence_with_time`
4. `oracle_context`

这些都应该成为 EncodingAgent 的输入。

也就是说，编码层不是在做：

> “query 有没有被记住？”

而是在做：

> “回答这个 query 所需的 gold evidence，是否以某种可接受形式存在于系统记忆中？”

### 6.3 原则三：编码层必须允许“语义存在”，不能只允许“字面存在”

记忆系统不一定会原样存：

- “Caroline went to the LGBTQ support group yesterday”

它可能存成：

- “Caroline attended a support group”
- “She joined an LGBTQ support meeting”
- “On May 8, Caroline talked about attending a support group”

如果编码层只接受字符串精确匹配，就会系统性低估 EXIST。

因此编码层判定必须支持三层匹配语义：

1. **字面匹配**
2. **结构匹配**
3. **语义匹配**

### 6.4 原则四：编码层应允许“多条记录联合证明”

某些系统不会把完整证据写成一条记录，而会拆开存。

例如：

- 记录 A：人物
- 记录 B：事件
- 记录 C：时间

单条记录都不足以证明证据存在，但联合起来可以。

所以 EncodingAgent 的判断对象不应只是一条条记录，而应是：

1. 单条记录
2. 小型候选集合
3. 组合后的证据片段

### 6.5 原则五：编码层结论必须保留来源

最终不能只给：

- `state=EXIST`

必须同时给：

1. 命中的 memory ids
2. 命中的文本片段
3. 命中依据
4. 为什么认为是存在/缺失/错误/歧义
5. 使用了哪些观测来源

### 6.6 原则六：编码层要支持“强适配”和“弱通用”双模式

你提出“尽可能减少适配器层工作量”是对的，但不能走极端。

所以建议编码层支持两种模式：

1. **强适配模式**
   - 适配器明确提供原生高召回候选
   - 适用于正式评测

2. **弱通用模式**
   - 框架内部提供基础混合检索
   - 适用于快速接系统、开发期、低成本对接

这样就能兼顾：

- 通用性
- 可比性
- 工程可落地性

## 7. 编码层的推荐总体方案

我建议把 EncodingAgent 拆成五个内部子阶段。

### 7.1 阶段 A：证据标准化

输入：

1. `query`
2. `f_key`
3. `evidence_texts`
4. `evidence_with_time`
5. `oracle_context`

输出一个统一的 `EvidenceSpec`，其中包括：

1. 事实槽位
   - 人物
   - 事件
   - 时间
   - 地点
   - 属性

2. 证据变体
   - 同义表达
   - 时间表达变体
   - 指代变体

3. 判定优先级
   - 哪些槽位必须命中
   - 哪些槽位允许缺失

这个阶段最好由 LLM 或规则+LLM 联合完成。

作用是把原始 gold evidence 从“文本”变成“可判定合同”。

### 7.2 阶段 B：系统记忆观测获取

输入：

1. `run_ctx`
2. memory-system adapter

输出一个 `MemoryObservationBundle`。

这个 bundle 不应只有一个全量 memory list，而应至少分成四类来源：

1. `full_memory_view`
   - 适配器导出的全库可见视图

2. `native_candidate_view`
   - 系统原生候选召回结果

3. `framework_candidate_view`
   - 框架内部混合检索得到的候选

4. `native_retrieval_shadow`
   - 从检索层复用来的同源召回片段

关键思想是：

> 编码层不是只看一个来源，而是看一个“观测束”。

这样可以减少“系统明明存了，但只因为一种观察方式没看到就判 MISS”的问题。

### 7.3 阶段 C：候选融合与分组

拿到多来源候选后，不要直接丢给 LLM。

应该先做候选整理：

1. 去重
2. 来源标注
3. 按 record / chunk / event / session 分组
4. 生成证据组合候选

例如输出：

- 单条候选
- 同 session 联合候选
- 同 subject 联合候选
- 同 timestamp 联合候选

因为真实证据往往不是单条命中的。

### 7.4 阶段 D：EncodingAgent 综合裁判

这是编码层真正的 Agent。

它的输入应该包含：

1. `query`
2. `task_type`
3. `EvidenceSpec`
4. `MemoryObservationBundle`
5. 候选融合结果
6. 适配器描述信息

它的输出至少应包括：

1. `encoding_state`
   - `EXIST`
   - `MISS`
   - `CORRUPT_AMBIG`
   - `CORRUPT_WRONG`
   - `DIRTY`

2. `defects`
   - `EM`
   - `EA`
   - `EW`
   - `DMP`

3. `matched_memory_ids`
4. `supporting_snippets`
5. `contradicting_snippets`
6. `reasoning_chain`
7. `confidence`
8. `observation_coverage`

其中最重要的是 `observation_coverage`：

它要明确说明：

- 本次编码判断到底看了哪些来源
- 有哪些来源不可见
- 有没有可能因为观测盲区而误判

### 7.5 阶段 E：编码层证据链压缩输出

为了后续 AttributionAgent 使用，编码层不能只输出原始大段文本。

必须再形成一个结构化摘要，例如：

1. 结论
2. 关键支持证据
3. 关键反驳证据
4. 可观测性限制
5. 风险标签

这一步的目的是给最终归因层一个可消费的“编码层证据摘要”。

## 8. 编码层的关键对象设计

为了把方案做扎实，我建议后续实现时引入下面几类中间对象。

### 8.1 EvidenceSpec

表示 gold evidence 的标准化结构。

建议字段：

1. `query`
2. `task_type`
3. `facts`
4. `fact_slots`
5. `evidence_texts`
6. `evidence_with_time`
7. `oracle_context`
8. `must_have_constraints`
9. `soft_constraints`
10. `negative_constraints`

### 8.2 MemoryObservation

表示一条来自系统的可观测记忆。

建议字段：

1. `memory_id`
2. `text`
3. `source_type`
4. `source_name`
5. `timestamp`
6. `speaker`
7. `session_id`
8. `embedding_meta`
9. `storage_meta`
10. `raw_payload_ref`

### 8.3 MemoryObservationBundle

表示一组编码层观测来源。

建议字段：

1. `full_memory_view`
2. `native_candidate_view`
3. `framework_candidate_view`
4. `retrieval_shadow_view`
5. `adapter_manifest`
6. `observability_notes`

### 8.4 EncodingAssessment

表示编码层最终标准输出。

建议字段：

1. `state`
2. `defects`
3. `confidence`
4. `matched_ids`
5. `supporting_snippets`
6. `missing_facts`
7. `contradictions`
8. `coverage_report`
9. `reasoning_chain`
10. `risk_flags`

## 9. 编码层如何真正判断“证据存在”

这是整个问题的核心。

我建议不要把“存在”理解成单一布尔值，而要把它拆成四层判定。

### 9.1 第一层：字面存在

问题：

- 是否存在文本上直接包含 gold evidence 的记录？

适用：

- JSON 存储
- 原文 chunk 存储
- 近似直存系统

优点：

- 最容易解释

缺点：

- 召回低
- 对表述变化极其敏感

### 9.2 第二层：结构存在

问题：

- 是否存在 metadata/field/value 组合，足以重构该证据？

例如：

- `subject=Caroline`
- `event=LGBTQ support group`
- `time=2023-05-08`

即使文本不完全一致，也应视为存在。

适用：

- KV 存储
- 图结构
- 表结构

### 9.3 第三层：语义存在

问题：

- 虽然没有字面或结构等值，但是否存在语义等价的记忆表达？

例如：

- “support group meeting”
- “LGBTQ support gathering”

这需要 LLM 参与。

### 9.4 第四层：组合存在

问题：

- 单条记录不足以证明，但多条联合后是否足够？

这一步尤其重要，因为很多长期记忆系统会拆散存储。

所以 EncodingAgent 应允许输出：

- `evidence_found_by = single_record`
- `evidence_found_by = structured_fields`
- `evidence_found_by = semantic_equivalence`
- `evidence_found_by = record_combination`

这样你最终就不只是知道“存在”，而是知道“以什么形式存在”。

## 10. 我建议的编码层判定流程

下面是一套更可执行的流程。

### Step 1：构建 gold evidence 合同

由 `query + evidence + oracle_context` 生成：

1. 核心事实
2. 必须命中槽位
3. 可接受变体
4. 负样本约束

### Step 2：让适配器导出系统可观测视图

至少支持：

1. 全量导出
2. 原生候选获取
3. 原生检索影子结果
4. 观测边界说明

### Step 3：框架内部补充弱混合召回

如果适配器只提供了有限候选，框架可以追加：

1. 关键词召回
2. 轻量语义召回
3. 时间对齐召回
4. 角色对齐召回

但这里要明确：

> 这一步是“补充观测”，不是最终裁决。

### Step 4：生成候选证据组合

把多条候选拼成可能的联合证据片段，再送判定。

### Step 5：调用 EncodingAgent 做最终判断

判断重点：

1. 是否命中了必须事实
2. 是否存在错误值
3. 是否只存在模糊指代
4. NEG 情况下是否出现不应有伪记忆

### Step 6：输出结构化编码证据链

输出不仅要有 `state/defects`，还要有：

1. 命中来源
2. 支持片段
3. 反例片段
4. 观测盲区
5. 风险提示

## 11. 检索层和生成层的 Agent 化方案

你说这两层问题不大，我同意，所以这里只给稳定方案定义。

### 11.1 RetrievalAgent

输入：

1. `query`
2. `gold evidence`
3. `C_original`

职责：

1. 判断标准证据是否出现在原生检索结果中
2. 判断排序是否过晚
3. 判断噪声是否过多
4. 输出 `HIT/MISS/NOISE`

输出：

1. `state`
2. `defects`
3. `matched_ids`
4. `hit_indices`
5. `rank_index`
6. `snr`
7. `supporting_snippets`
8. `reasoning_chain`

### 11.2 GenerationAgent

输入：

1. `query`
2. `A_online`
3. `A_oracle`
4. `A_gold`
5. `oracle_context`

职责：

1. 判断 `A_oracle` 是否正确
2. 判断 `A_online` 与 `A_oracle` 的差异
3. 判断失败属于 `GH/GF/GRF`

输出：

1. `state`
2. `defects`
3. `oracle_correct`
4. `online_correct`
5. `comparative_judgement`
6. `supporting_snippets`
7. `reasoning_chain`

## 12. 最终归因层：AttributionAgent 方案

我认为你这里非常值得从“简单代码合并”升级为“最终归因 Agent”。

### 12.1 为什么要单独做 AttributionAgent

因为最终归因不是简单 union：

1. 编码 MISS 时，检索 RF 可能应被抑制
2. 编码 EXIST + 检索 HIT + 生成 FAIL，主要责任应在生成
3. 编码 EXIST + 检索 MISS + 生成 PASS，主要责任应在检索
4. 编码 CORRUPT + 检索 HIT + 生成 FAIL，责任可能跨层

所以最终归因本质上是一个：

> **跨层证据整合与责任排序问题**

### 12.2 AttributionAgent 的输入

1. `EncodingAssessment`
2. `RetrievalAssessment`
3. `GenerationAssessment`
4. 原始 query
5. gold evidence
6. gold answer

### 12.3 AttributionAgent 的输出

1. `final_defects`
2. `primary_cause`
3. `secondary_causes`
4. `decision_trace`
5. `cross_probe_evidence_chain`
6. `actionable_diagnosis`

### 12.4 我建议的归因策略

先不要完全依赖一条 LLM 黑盒结论。

应该采取两层结构：

1. **规则约束层**
   - 保留你现在已有的基本逻辑门控
   - 例如 `enc=MISS` 时抑制 `RF`

2. **LLM 解释层**
   - 在规则约束后的结果空间里，生成最终解释与责任排序

这样做的好处是：

1. 保持结果稳定
2. 避免 LLM 自由发挥导致不一致
3. 同时能补足解释性证据链

## 13. 我建议的最终输出格式

我建议后续最终报告输出不再只是现在的：

1. `states`
2. `defects`
3. `probe_results`

而是升级为：

1. `encoding_assessment`
2. `retrieval_assessment`
3. `generation_assessment`
4. `attribution_assessment`
5. `evidence_chain`
6. `observability_report`

其中 `evidence_chain` 应明确记录：

1. 编码层用了哪些观测
2. 哪些证据命中
3. 哪些证据未命中
4. 检索层看到了什么
5. 生成层为什么通过/失败
6. 最终归因如何形成

## 14. 这个方案与当前代码的关系

如果结合当前代码现状来判断，我的结论是：

### 已经具备的部分

1. 三层 probe 骨架已经有了
2. adapter protocol 骨架已经有了
3. LLM judge 骨架已经有了
4. 最终归因结构已经有了雏形

### 还缺失的关键部分

1. 三探针还没有被正式抽象成三个 Agent
2. 编码层还没有完整的 `EvidenceSpec` 和 `MemoryObservationBundle`
3. 编码层还缺少“组合存在性判断”
4. 最终归因还偏规则拼接，缺少独立 AttributionAgent
5. 证据链还不够完整，不足以支撑强解释性

## 15. 我对编码层的最终建议

如果只抓最关键的一点，我的建议是：

> **编码层不要再被设计成“匹配器”，而要被设计成“证据存在性裁判 Agent”。**

具体来说：

1. 适配器负责导出多源观测
2. 框架负责构建统一证据合同
3. EncodingAgent 负责综合判断
4. 输出必须是结构化证据链，而不是单个状态码

这样做之后，你的三探针体系会更稳：

1. 编码层真的在回答“有没有存”
2. 检索层真的在回答“有没有取到”
3. 生成层真的在回答“给了证据能不能答对”
4. 归因层真的在回答“问题到底出在哪”

## 16. 推荐后续实施顺序

在不改代码的前提下，下一步我建议按下面顺序推进方案落地：

1. 先把三探针正式定义成四个 Agent 的文档合同
2. 先细化编码层中间对象：
   - `EvidenceSpec`
   - `MemoryObservation`
   - `MemoryObservationBundle`
   - `EncodingAssessment`
3. 再定义 AttributionAgent 的输入输出 schema
4. 最后再进入代码改造

## 17. 结论

你的方向是对的，而且比当前代码实现更完整。

当前代码已经在技术上接近这个方案，但还停留在：

- 三层 probe
- 适配器调用
- LLM 辅助裁决

而你真正要的是：

- 三层评估 Agent
- 一个最终归因 Agent
- 一套完整证据链标准
- 特别是一个能严肃回答“证据是否真实存在”的编码层方案

如果继续往下做，我建议下一步就专门写第二份文档：

**《EncodingAgent 详细技术设计（对象结构、输入输出 schema、判定流程、失败语义）》**

这会是后续改代码前最重要的一份规范文档。
