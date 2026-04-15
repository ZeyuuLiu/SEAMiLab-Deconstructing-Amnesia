# 评测框架后续改造方案文档（v0.2）

## 1. 文档目标

这份文档是在当前 0401 运行结果复核基础上形成的**新方案文档**。

目标不是立刻改代码，而是先把以下四件事彻底说清楚：

1. MemBox 现在到底是怎么工作的，为什么它可以 build 和 eval 分离
2. 当前 MemBox 编码层为什么会出现明显异常，以及编码层后续应该如何补强输入
3. 当前 LLM-as-Judge 为什么还不够好，应该如何参考 TiMem 重新设计
4. 结合当前整体代码，下一步还缺哪些关键内容没有补齐

## 2. 当前结论先说清楚

### 2.1 关于 MemBox：build / eval 分离本身不是信息丢失根因

当前 MemBox 可以 build 和 eval 分离，是因为它本来就有明显的“两阶段结构”：

1. 第一阶段是把完整对话导入系统，并构建内部 memory boxes
2. 第二阶段是针对具体 query，从已有 memory boxes 中检索并回答

因此：

- **build / eval 分离是顺着 MemBox 原始工作流做的工程化拆分**
- **不是因为评测框架强行把系统拆坏了**

真正可能造成信息丢失的地方，不是“分离”本身，而是：

1. build 阶段本身就把原始对话压缩成 box 级摘要
2. 评测编码层当前拿到的不是原始对话，而是压缩后的 final boxes
3. 编码层尚未充分纳入 MemBox 原生面向 query 的检索结果作为补充输入

### 2.2 关于编码层：当前 MemBox 的问题大概率不是单一原因

MemBox eval 中出现了：

1. 编码层 10/10 全部 MISS
2. 检索层 10/10 全部 MISS
3. 但 final correctness 仍然有不少题为 true

这说明当前问题不是“某一个点坏了”，而是至少有三部分叠加：

1. 编码层输入不够强，看到的主要是 final box 摘要视图
2. 编码层没有充分利用原始记忆系统面向当前 query 的原生检索结果
3. LLM-as-Judge 当前存在 POS 拒答误判和 online / oracle 混淆风险

### 2.3 关于整体方向：后续必须进一步强化“通用评测抽象”

你的核心要求非常明确：

1. 三层评测框架的意义，不是服务于 O-Mem 或 MemBox 两个系统
2. 而是要尽可能抽象出所有长期记忆系统的共性链路
3. 这样后续引入新系统时，仍然可以被纳入同一套细粒度归因框架

因此，后续代码改造要坚持一个原则：

- **优先补“通用能力”，避免继续堆叠“单系统补丁”**

## 3. MemBox 的具体逻辑与 build / eval 分离解释

## 3.1 当前 MemBox 在评测框架中的工作流程

当前 `MemboxAdapter` 的工作过程可以概括为：

### 第一步：标准化对话

评测框架先把样本对话标准化成 turn 列表，再重新整理成 MemBox 需要的：

1. `session_1`
2. `session_2`
3. ...

以及对应时间字段。

### 第二步：build memory boxes

之后 MemBox stableEval 运行时会：

1. 遍历会话中的消息
2. 使用 LLM 判断当前消息是否继续并入现有 memory box
3. 如果不应并入，则封箱并新建 box
4. 在 box 完成后抽取：
   - `content_text`
   - `topic_kw_text`
   - `events_text`

最终形成 `final_boxes_content.jsonl` 之类的构建结果。

### 第三步：加载原生检索器

构建完成后，`SimpleRetriever` 会读取 final box 文件，并对：

1. `content_text`
2. `events_text`
3. `topic_kw_text`

拼接后的文本做 embedding 检索。

### 第四步：baseline / eval 复用 build 产物

在 baseline 或 eval 阶段，不再重复 build，而是：

1. 读取 build manifest
2. 重建 worker
3. 重建 retriever
4. 复用同一份 final boxes 做 query 级问答和评测

这就是现在 build / eval 分离能够成立的原因。

## 3.2 为什么 build / eval 分离在逻辑上是合理的

因为对 MemBox 来说，memory build 是“面向整段对话的一次性准备过程”，而 query answering 是“在固定 memory 状态上针对不同问题的多次执行过程”。

换句话说：

1. build 是 conversation-level
2. eval 是 question-level

这两者天然就是不同粒度。

因此，将它们分离后：

1. 可以避免每一道题都重复构建 memory box
2. 可以让 baseline 和 eval 共用同一份构建结果
3. 可以把“构建太慢”和“评测出错”两个问题彻底拆开

## 3.3 build / eval 分离会不会导致信息丢失

**结论：分离本身不是主因，真正的信息损失发生在 build 内部的摘要化与结构化过程中。**

更准确地说，风险点有三层：

### 风险点一：原始对话被压缩成 box 级表示

在 build 阶段，原始 utterance 并不是被逐句原样保存，而是被压缩为：

1. `content_text`
2. `topic_kw_text`
3. `events_text`

因此，以下信息天然可能丢失或弱化：

1. 原始措辞
2. 局部时序细节
3. 说话人边界
4. 细粒度上下文依赖

### 风险点二：会话重组可能影响边界

当前适配器在导入时会基于 timestamp 重建 session。如果 timestamp 缺失、粒度不够或格式不稳定，原始会话边界可能被弱化。

### 风险点三：编码层当前看到的输入还不够强

现在编码层主要依赖：

1. `export_full_memory()` 导出的 final box 视图
2. 适配器当前实现返回的候选
3. 框架侧已有的 fallback

这意味着编码层更多是在看“build 之后系统留下了什么”，而不是“系统面对当前 query 时，会从自己的原生机制里找出什么”。

所以真正的问题不是：

- “build 之后不能 eval”

而是：

- “build 之后 eval 看到的编码层输入还不够接近系统原生 query-facing memory evidence”

## 4. 编码层为什么可能对 MemBox 判断过差

## 4.1 当前编码层为什么可能有系统性偏差

你的判断是对的：**编码层本身也应该尽可能借助原始记忆系统的检索能力来观察记忆是否存在。**

因为从评测角度看，编码层要回答的问题不是一个纯静态问题，而是：

- “这个系统内部到底有没有形成可被后续使用的有效记忆表示？”

如果我们只看 final box 的摘要内容，而不看系统针对当前 query 会如何调出相关 box，那么编码层就可能低估系统内部已经形成但表达较隐式的记忆。

对于 MemBox 这种经过压缩和重组的记忆系统，这个问题会更严重。

## 4.2 当前编码层缺的不是“是否检索”，而是“检索证据层次不够丰富”

现在编码层已经具备一些候选来源，但还不够：

1. 它有全量 memory view
2. 它有外部高召回检索接口
3. 它有部分 adapter native retrieval shadow

但对于 MemBox 来说，仍缺少两个很关键的输入：

### 输入一：原系统基于当前 query 的原生检索内容

这部分非常重要，因为它直接代表：

- 如果用户现在问这个问题，MemBox 自己会拿出哪些 box / 内容作为答案依据

这应该被保留为编码层输入的一部分，而不是只放在检索层。

原因是：

1. 对某些压缩型记忆系统来说，“能被原生 query 检到”本身就是编码成功的重要证据
2. 如果编码层完全不看这个视角，就可能把“弱显式但可检索”的记忆误判成 MISS

### 输入二：基于 `f_key` 的目标事实定向检索内容

你的建议也非常关键：

1. 当前 query 本身可能比较自然、比较模糊
2. 但 `f_key` 往往更贴近 gold evidence 的关键事实表达

因此，编码层可以在保留原始 query 检索之外，再做一条：

1. 用 `question`
2. 用 `f_key`
3. 或用 `question + f_key`

分别调用原生检索，形成“目标事实定向检索证据”。

这样做的意义是：

1. query 检索更贴近真实运行时行为
2. f-key 检索更贴近“系统内部是否真的存了这条事实”

两者结合后，编码层判断会更稳。

## 4.3 编码层后续推荐的新输入结构

我建议后续把编码层输入扩展为 5 类证据并统一入 bundle：

### 第一类：全量 memory export

用于观察系统 build 后到底留下了什么。

### 第二类：原系统基于当前 query 的原生检索结果

用于观察系统会不会把相关记忆当成与当前问题相关的内容取出来。

### 第三类：原系统基于 `f_key` 的目标事实检索结果

用于观察系统内部有没有面向 gold fact 的可触达记忆。

### 第四类：框架侧高召回候选

包括你后续自己的 RAG 检索方法。

### 第五类：原生检索 shadow / 排名诊断信息

用于观察“有无命中”和“命中排序是否过晚”。

## 4.4 对编码层的方案性结论

因此，我的方案判断是：

1. **是的，当前 MemBox 编码层结果过差，编码输入不够强是一个重要原因**
2. 但它不是唯一原因
3. 后续应该把“原生 query 检索结果”和“f-key 定向检索结果”都并入编码层输入
4. 这样改不只是为了 MemBox，而是对所有压缩型、摘要型、结构化型记忆系统都成立

## 5. 参考 TiMem 重新设计 LLM-as-Judge 的方案

## 5.1 当前方案为什么让人不满意

你现在不满意是完全合理的，问题主要有三个：

### 问题一：当前 judge 过于宽松

特别是在 POS 题中，出现了：

1. `No evidence found`
2. `Not mentioned`
3. 类似拒答回答

却仍被判为 correct 的情况。

### 问题二：online correctness 与 oracle correctness 边界不够严格

当前系统里存在 judge 可能利用 oracle context 来“帮在线回答脑补正确”的风险。

### 问题三：judge 只给 final boolean，不够细

虽然现在已经有 `rule_correct / llm_correct / final_correct`，但仍然缺：

1. refusal quality
2. fabricated content
3. temporal equivalence
4. partial match
5. unsupported-but-plausible answer

## 5.2 TiMem 给我们的真正启发是什么

从 TiMem 论文附录里的 judge prompt 可以提炼出三个核心思想：

### 启发一：语义等价要宽松，而不是字面严格

TiMem 明确要求：

1. 只要 generated answer 触及与 gold 相同主题，就倾向认为 CORRECT
2. 时间问题允许不同格式、不同相对表达，只要指向同一时间即可

### 启发二：judge 应尽量简洁、单目标

TiMem 的 judge 不是复杂多任务 prompt，而是集中回答：

- 这条 generated answer 对于这个 gold，到底算 CORRECT 还是 WRONG

### 启发三：judge 要服务于可重复统计

TiMem 最终只落一个清晰标签，便于直接用于 benchmark accuracy 统计。

## 5.3 但我们不能直接照抄 TiMem

原因是 TiMem 的 judge 场景和我们当前框架还不完全一样。

TiMem 更像是：

1. 黑箱答案评测
2. generous semantic equivalence

而我们现在还需要：

1. baseline 与 eval 共用
2. POS / NEG 分流
3. online 与 oracle 分流
4. 服务三层归因，而不只是最终 accuracy

所以我们的正确做法应该是：

- **以 TiMem 的 generous semantic equivalence 为核心**
- **再加上我们自己的 POS / NEG 和 online / oracle 结构化约束**

## 5.4 我建议的新 Judge 结构

## 第一层：唯一 correctness 真源层

后续应该只有一个统一的 `CorrectnessJudge` 负责：

1. baseline 的 online correctness
2. eval 中 generation 的 online correctness
3. eval 中 generation 的 oracle correctness

也就是说：

- “答案到底对不对”只能由这一个 judge 说了算

generation agent 不应再额外拥有另一套“答对/答错真源”。

## 第二层：online / oracle 严格隔离

### online correctness

输入只允许包含：

1. question
2. gold answer
3. online answer
4. task type
5. 可选少量 task instruction

**不允许直接给 oracle context。**

### oracle correctness

输入可以包含：

1. question
2. gold answer
3. oracle answer
4. oracle context

这样才能避免 online judge 被 oracle 泄露污染。

## 第三层：POS / NEG 分流

### POS judge

TiMem 风格的 generous semantic equivalence 应主要用于 POS：

1. 语义同义
2. 时间等价
3. 指代等价
4. 更长表达但主题一致

但需要新增一个强规则：

- 如果回答是显式拒答模板，则 POS 不能直接判 correct

### NEG judge

NEG 不能只看“和 gold 模板像不像”，而应判断：

1. 是否成功拒答
2. 是否编造了 unsupported fact
3. 是否虽然含糊，但仍泄露了虚假肯定信息

因此 NEG judge 应该是 refusal-aware 的。

## 第四层：结构化输出

我建议新的 judge 输出改为：

1. `label`
   - `CORRECT`
   - `WRONG`
2. `reason`
3. `semantic_match`
4. `temporal_match`
5. `refusal_expected`
6. `refusal_present`
7. `fabricated`
8. `fallback_used`

其中：

- `final_correct` 仍然由 `label == CORRECT` 得到
- 其余字段服务于分析和 debug

## 5.5 Judge prompt 的推荐方向

推荐做成两个 prompt：

### Prompt A：POS correctness judge

核心原则：

1. generous
2. semantic-equivalence-oriented
3. time-equivalence-aware
4. explicit refusal is not correct for POS

### Prompt B：NEG correctness judge

核心原则：

1. refusal-aware
2. hallucination-aware
3. unsupported-fact-sensitive
4. 不要求和 gold 模板逐字一致

## 5.6 与当前 generation failure judge 的关系

后续 generation 层里应该拆成两件事：

### 事情一：判断答对没有

交给统一 `CorrectnessJudge`

### 事情二：判断为什么没答对

交给 generation failure analysis：

1. GF
2. GRF
3. GH

这样才不会出现：

1. 一个 prompt 说正确
2. 另一个 prompt 又在另一个口径下说失败

## 6. 现在整体代码还差哪些内容

下面是我重新检查后的缺口清单。

## 6.1 Judge 相关缺口

### 缺口一：correctness 真源还没有彻底统一

现在 correctness judge 和 generation 专属 LLM judge 仍然双轨并存。

### 缺口二：online / oracle 还没有完全隔离

这是现在最危险的口径问题。

### 缺口三：NEG judge 结构太弱

还没有 refusal-aware 的结构化输出。

### 缺口四：retrieved_context 还没有真正接入 judge 主链

接口有，但主链没有真正把检索到的上下文喂进去。

## 6.2 编码层相关缺口

### 缺口一：MemBox 编码层尚未把原生 query 检索结果系统性并入输入

### 缺口二：尚未把基于 `f_key` 的目标事实定向检索并入输入

### 缺口三：当前高召回接口虽然存在，但尚未形成“原生检索 + 外部高召回 + 定向事实检索”的统一证据束

## 6.3 baseline 相关缺口

### 缺口一：baseline 没有像 eval 那样的逐题 JSON 体系

### 缺口二：baseline 还缺单题异常隔离与标准化 error 索引

### 缺口三：baseline 缺少完整的 run summary / question index / artifact refs

## 6.4 MemBox 可观测性缺口

### 缺口一：adapter 里仍然存在静默吞异常的路径

例如：

1. embedding 异常直接零向量
2. chat 异常直接空串

### 缺口二：没有把底层异常显式带入最终结果

### 缺口三：没有 probe 级耗时与 judge 元数据落盘

## 6.5 评测栈一致性缺口

### 缺口一：attribution 仍然允许 LLM 过度参与主因覆盖

### 缺口二：旧的 trace 协议路径仍未完全清理

### 缺口三：LLM judge 相关测试仍然不够

当前测试更偏 rule path，没有充分覆盖：

1. POS judge
2. NEG judge
3. online / oracle 隔离
4. judge fallback
5. judge 与 generation subtype 一致性

## 7. 下一步推荐改造顺序

我建议后续严格按下面顺序改：

### 第一阶段：先修 judge 真源

1. 统一 correctness 真源
2. 严格分离 online / oracle
3. 重新设计 POS / NEG judge prompt

### 第二阶段：补强编码层证据束

1. 加入 query 原生检索结果
2. 加入 `f_key` 定向原生检索结果
3. 统一编码层 evidence bundle

### 第三阶段：补 baseline 可观测性

1. baseline per-question JSON
2. baseline question index
3. baseline error isolation

### 第四阶段：补异常透明度与测试

1. 减少 adapter 静默吞异常
2. 增加 judge 元数据落盘
3. 增加 LLM judge 相关测试

## 8. 最终结论

这次重新梳理后的核心判断是：

1. MemBox 能 build / eval 分离，是因为它本来就是“conversation-level build + question-level answering”的两阶段系统
2. build / eval 分离本身不是信息丢失主因，真正的问题是 build 内部摘要化以及编码层输入不够强
3. 你对编码层的担心是成立的：后续必须把“原系统 query 原生检索结果”和“基于 f-key 的定向检索结果”都并入编码层输入
4. 当前 LLM-as-Judge 确实还不够好，应该参考 TiMem 的 generous semantic equivalence，但不能直接照搬，必须进一步做 POS / NEG 分流和 online / oracle 隔离
5. 当前整体代码已经从“能不能跑”阶段进入“口径是否统一、结果是否可信、通用性是否足够”阶段，后续重点应放在统一 judge、补强编码层输入和增强整体一致性上
