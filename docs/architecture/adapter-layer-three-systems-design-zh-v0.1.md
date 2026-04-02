# 三种记忆系统的适配器层设计说明（不修改现有适配器代码）

## 1. 文档目标

这份文档只做适配器层设计分析，不修改适配器代码。

目标有三个：

1. 结合 `system/` 下三种记忆系统，给出统一适配器层设计
2. 说明当前已有适配器的不足与问题
3. 给出后续适配器重构方向，但暂不实施代码修改

当前讨论对象为：

1. `system/Membox`
2. `system/O-Mem`
3. `system/MemoryOS`

## 2. 适配器层到底要解决什么问题

评估层要对三种记忆系统做统一评测，但三者底层结构完全不同：

1. 记忆单元不同
2. 检索机制不同
3. 生成路径不同
4. 数据导出方式不同
5. 有些系统调用生成时还会反向写回记忆

所以适配器层的职责，不是简单做 import，而是要完成：

1. 系统内部状态的可观测化
2. 系统原生检索结果的标准化
3. 系统生成路径的纯评测化
4. 系统能力边界的显式声明

## 3. 三种系统的结构差异

## 3.1 Membox

Membox 的核心特点是：

1. 对话切盒
2. 对 box 做主题、关键词、事件抽取
3. 通过 trace linking 建立跨盒连接
4. 检索时通过多种内容一起排序
5. 生成时把 top-N box 拼进 QA prompt

对评测层而言，Membox 的优点是：

1. 记忆单元比较清晰
2. 检索输出比较显式
3. native path 比较容易适配

## 3.2 O-Mem

O-Mem 的核心特点是：

1. working memory
2. episodic memory
3. persona memory
4. 增量 receive_message 写入
5. retrieve_from_memory_soft_segmentation 负责原生检索
6. generate_system_response 负责生成

对评测层而言，O-Mem 的特点是：

1. 分层记忆结构明显
2. 原生检索结果包含多通道内容
3. 适合做编码层与检索层联合观测

但问题是：

1. 当前适配器里同时存在 real 与 lightweight 两种模式
2. fallback 模式并不等价于原生系统行为

## 3.3 MemoryOS

MemoryOS 的核心特点是：

1. short-term memory
2. mid-term memory
3. long-term memory
4. retriever 并行返回多类上下文
5. `get_response()` 在生成完之后还会写回记忆

对评测层而言，MemoryOS 最大的问题不是结构复杂，而是：

> 它的原生回答路径存在副作用。

这意味着如果直接把 `get_response()` 当成评测接口，就可能污染系统状态，影响公平性与可复现性。

## 4. 当前适配器层覆盖情况

当前仓库已经接入：

1. Membox
2. O-Mem

但还没有接入：

1. MemoryOS

也就是说，现在适配器层不是“三系统统一接入”状态，而是“**两系统已接入，一系统缺失**”状态。

## 5. 当前适配器层存在的问题

我认为现在适配器层主要有七个问题。

## 5.1 问题一：MemoryOS 完全缺失

这是最直接的问题。

当前框架虽然在设计上面向多个记忆系统，但实际上还没有做到对 `system/MemoryOS` 的正式适配。

所以当前评测层并没有真正覆盖 `system/` 下的全部三种系统。

## 5.2 问题二：没有统一的 Base Adapter

当前 O-Mem 和 Membox 都各自实现了完整流程，但公共逻辑没有抽出来。

例如很多适配器共性问题都没有统一抽象：

1. turn normalize
2. trace build
3. error wrapping
4. manifest export
5. retrieval item normalize

这会导致后续继续接入 MemoryOS 时，很容易再复制第三份相似样板代码。

## 5.3 问题三：没有能力声明机制

现在评估层默认假设 adapter 都有全部能力，但实际上不同系统可能存在差异：

1. 有的系统能完整导出全量记忆
2. 有的系统只能高召回查候选
3. 有的系统 native generation 有副作用
4. 有的系统可能没有真正意义上的 oracle path

如果没有能力声明，评估层就无法知道：

> “这是系统确实没有这个能力，还是适配器还没实现？”

## 5.4 问题四：O-Mem 的 fallback 语义不够纯

当前 O-Mem 适配器中存在 lightweight / fallback 路径。

这对开发调试是有帮助的，但对正式评测而言会产生两个问题：

1. fallback 路径并不等于真实系统
2. 真实模式与 fallback 模式混在一个 adapter 里，语义容易混淆

更合理的方式应该是：

1. 明确区分 native adapter
2. 明确区分 debug adapter

## 5.5 问题五：MemoryOS 原生生成有副作用

如果直接把 MemoryOS 的原生 `get_response()` 接进生成层，会有问题：

1. 一次评测会改变系统内部记忆状态
2. 之后的样本再评测时环境已经变了
3. oracle / online 对比不再是纯比较

这会直接破坏评测公平性。

因此 MemoryOS 的 adapter 必须额外处理：

1. 无副作用生成
2. 或 clone-state 生成
3. 或生成后回滚

## 5.6 问题六：统一 memory record 模型还不够清楚

虽然当前评估层使用了：

1. `{id, text, meta}`

这样的通用结构，但这还是偏“最低限度可跑通”，还不够成为强标准。

因为三种系统的记忆单元差异很大：

1. Membox 是 box
2. O-Mem 是 working/episodic/persona 多通道
3. MemoryOS 是短中长三层和知识对象

所以未来需要一个更清楚的统一 record 结构。

## 5.7 问题七：适配器与评测层的边界还不够显式

现在协议里已经定义了几个核心方法，但还没有真正把：

1. 可观测性
2. 原生检索
3. 纯评测生成
4. 系统能力边界

完整拆开来。

这会导致某些系统为了接入评估层，被迫在 adapter 内做过多“隐式补偿”。

## 6. 我建议的统一适配器层设计

我建议未来的适配器层采用“三层结构”。

## 6.1 第一层：统一抽象基座

新增一个抽象基类，例如：

1. `BaseMemoryAdapter`

它负责统一以下公共能力：

1. 对话 turn 标准化
2. 运行态上下文容器
3. 错误包装
4. manifest 输出
5. retrieval item 标准化

这层不处理系统差异，只处理公共流程。

## 6.2 第二层：系统专属 native adapter

每个系统各自实现一份：

1. `MemboxAdapter`
2. `OMemAdapter`
3. `MemoryOSAdapter`

它们只负责系统特有逻辑：

1. native ingest
2. native export memory
3. native retrieval
4. native online generation
5. native oracle generation

## 6.3 第三层：flavor 变体层

有些系统会有不同后端或实验版本。

例如未来可能出现：

1. `memoryos:pypi`
2. `memoryos:chromadb`
3. `o_mem:stable_eval`
4. `o_mem:debug_lightweight`

这时 registry 不应该直接堆很多 builder 分支，而应该把“系统家族”和“变体”拆开管理。

## 7. 推荐的统一能力合同

未来适配器层不仅要提供方法，还应该提供能力声明。

例如每个 adapter 应显式给出：

1. `supports_full_memory_export`
2. `supports_native_retrieval`
3. `supports_oracle_generation`
4. `supports_online_generation`
5. `supports_read_only_generation`
6. `supports_high_recall_candidates`

这样评估层在运行时就知道：

1. 哪些能力可用
2. 哪些路径必须禁用
3. 哪些路径只能调试使用

## 8. 推荐的统一数据模型

我建议未来适配器层统一输出一个 richer 的 memory record。

例如：

1. `memory_id`
2. `text`
3. `channel`
4. `layer`
5. `timestamp`
6. `speaker`
7. `session_id`
8. `source_system`
9. `storage_kind`
10. `meta`

这样三种系统就能统一映射：

### Membox

- `channel=box`
- `layer=trace_box`

### O-Mem

- `channel=working/episodic/persona`
- `layer=memory_chain`

### MemoryOS

- `channel=short/mid/long`
- `layer=memoryos`

## 9. 三个系统分别应该如何适配

## 9.1 MemboxAdapter 设计建议

Membox 适配器应重点保留：

1. box 级记忆视图
2. native retrieval 排序结果
3. native QA 生成路径

Membox 的适配重点不是“能不能接入”，而是：

1. 怎么把 box、event、trace 这些结构信息在 `meta` 里保留下来
2. 让编码层可以充分利用这些结构信息

## 9.2 OMemAdapter 设计建议

O-Mem 适配器应重点区分两件事：

1. native real path
2. debug lightweight path

正式评测建议：

1. 只承认 native real path
2. fallback 路径必须显式标记为 debug

同时 O-Mem 的适配器很适合支持 richer 的 memory observation：

1. working memory 记录
2. episodic message
3. persona attribute
4. persona fact

因为它天然就是多通道记忆系统。

## 9.3 MemoryOSAdapter 设计建议

MemoryOS 适配时最重要的不是简单把接口打通，而是解决副作用问题。

建议原则：

1. `ingest` 走原生 add/write 路径
2. `retrieve_original` 走 Retriever 原生上下文输出
3. `generate_online_answer` 必须是无副作用版本
4. `generate_oracle_answer` 必须支持完美上下文注入且无写回

如果做不到无副作用生成，那么就不能直接把当前原生方法当正式评测路径。

## 10. MemoryOSAdapter 的推荐落地方式

如果未来实现 MemoryOSAdapter，我建议最小落地方案如下。

### 10.1 ingest

把 conversation turn 按 user/assistant 配对，调用系统的写入接口构建运行态。

### 10.2 export_full_memory

分别导出：

1. short-term
2. mid-term
3. user long-term knowledge
4. assistant knowledge

统一映射成 record list。

### 10.3 retrieve_original

直接复用原生 Retriever 的多通道结果，并保留来源标签。

### 10.4 generate_online_answer

不能直接使用有写回副作用的主流程，必须拆一个 read-only 版本。

### 10.5 generate_oracle_answer

应构造一个完美证据上下文的只读生成路径。

## 11. 当前适配器层的重构建议

这里给出后续建议，但暂不修改代码。

## 11.1 第一阶段：补文档与能力声明

先不改 adapter 代码，只做：

1. 统一 adapter capability 文档
2. 统一 adapter manifest 字段
3. 标注哪些 adapter 是正式评测路径，哪些只是 debug 路径

## 11.2 第二阶段：抽 BaseMemoryAdapter

把公共流程抽到基座类中。

## 11.3 第三阶段：接入 MemoryOSAdapter

补齐第三套系统接入。

## 11.4 第四阶段：统一 richer memory record

让编码层的 EncodingAgent 能真正利用多系统结构信息。

## 11.5 第五阶段：和四个评估 Agent 对齐

未来适配器层最好和四个 Agent 明确对齐：

1. EncodingAgent 需要怎样的观测
2. RetrievalAgent 需要怎样的 native output
3. GenerationAgent 需要怎样的只读生成
4. AttributionAgent 需要怎样的 manifest 与 coverage 信息

## 12. 我对当前适配器层的总体判断

我的整体判断是：

1. 现有适配器层不是不可用
2. 但它仍然处于“局部接通”阶段
3. 距离“统一、稳健、可扩展”的三系统适配层还有明显差距

尤其是两个问题最关键：

1. MemoryOS 未接入
2. 缺少统一基座和能力声明

## 13. 结论

如果你后续要把整个项目真正做成一个“面向多个长期记忆系统的统一评估框架”，那么适配器层必须升级。

我建议未来的方向是：

1. 统一抽象基座
2. 系统专属 native adapter
3. 明确能力声明
4. 统一 richer record 模型
5. 单独解决 MemoryOS 的无副作用生成问题

当前阶段最合理的策略不是马上大改适配器代码，而是：

> **先把适配器层设计原则、问题清单、三系统映射方法写清楚，再进入代码重构。**
