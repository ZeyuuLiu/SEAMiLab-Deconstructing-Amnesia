# baseline、归因 Agent 与 LLM-as-Judge 说明补充（v0.1）

## 1. 文档目的

这份文档用于补充说明当前评测报告里容易被误读的三个点：

1. baseline 结果与评测框架之间到底是什么关系
2. 最终归因 Agent 现在在做什么，以及希望它以后输出成什么样
3. LLM-as-Judge 的 prompt 应该如何参考 TiMem 的做法进行描述

这份文档是**解释性文档**，不涉及本轮代码修改。

---

## 2. 关于 baseline：需要先澄清的边界

## 2.1 baseline 的“低准确率”不能直接归因给三层评测框架

这是目前最需要先说清楚的一点。

当前 baseline 的本质是：

1. 由原始记忆系统自己完成
   - 记忆写入
   - 原生检索
   - 在线回答

2. 评测框架在 baseline 阶段做的事情主要是：
   - 调用系统原生 `generate_online_answer`
   - 记录结果
   - 用 correctness judge 做最终对错判定
   - 落盘为统一 JSON 结构

因此，baseline 的低准确率不能被简单表述为：

- “是因为我们的三层评测框架有问题，所以 baseline 很低”

更准确的说法应该是：

- **baseline 的回答生成过程本身与三层探针无关，但 baseline 的最终正确率统计仍然受到 correctness judge 口径影响。**

也就是说：

### 与评测框架无关的部分

1. 原系统怎么存
2. 原系统怎么检
3. 原系统怎么答

### 与评测框架有关的部分

1. 我们如何统一记录结果
2. 我们如何做最终 correctness 判定
3. 我们如何把结果写成 summary / per-question JSON

因此，报告里如果要严谨表述，建议写成：

- **baseline 低准确率主要反映原记忆系统在线回答链路的表现，但该准确率数值本身仍受统一 correctness judge 影响，因此不能完全视为“脱离评测框架的纯原生分数”。**

---

## 2.2 为什么 eval 和 baseline 不能混成一个概念

baseline 和 eval 在当前项目中的职责不同：

### baseline

它回答的是：

- 原系统直接在线回答时，最终能答对多少题

### eval

它回答的是：

1. 原系统有没有把信息写进去
2. 原系统有没有把该信息检出来
3. 给足证据后它会不会答
4. 最终最主要的问题层在哪里

所以：

1. baseline 更接近“黑盒最终表现”
2. eval 更接近“可解释的细粒度诊断”

报告中不应把 baseline 的低准确率，直接拿来证明某一层 probe 好或不好。

---

## 3. 关于最终归因 Agent：当前版本与期望版本

## 3.1 当前版本的归因 Agent 在做什么

当前归因 Agent 的逻辑本质上是：

- 根据编码层、检索层、生成层三个探针的状态，找出**最早、最主要**的问题层

当前它输出的核心内容主要包括：

1. `primary_cause`
2. `secondary_causes`
3. `decision_logic`
4. `final_judgement`

这套输出有一个优点：

- 结构清晰，便于程序汇总统计

但也有一个明显不足：

- **对人不够直观**

因为现在很多结果更像标签，而不是自然语言解释。

---

## 3.2 我们真正希望的归因输出形式

你提出的方向是非常合理的：

- 最终归因 Agent 应该能**用完整的话**描述当前记忆系统在这个 query 上到底出了什么问题

这意味着最终归因不应只停留在：

1. `encoding`
2. `retrieval`
3. `generation`

这样的层级标签上，而应该扩展成完整说明句。

例如，理想中的输出可以写成下面这种风格：

### 示例一：编码失败型

> 当前记忆系统没有在可观察记忆中保留与该问题相关的关键事实，因此编码层判为 MISS；由于上游记忆痕迹缺失，后续检索也无法稳定命中有效证据，最终在线回答只能依赖不充分信息作答。

### 示例二：检索失败型

> 当前记忆系统内部已经存在与该问题相关的记忆线索，但原生检索没有把关键事实在高位返回，导致检索层判为 MISS/LATE；生成模型在缺乏足够证据的情况下未能稳定给出正确答案，因此主要问题位于检索层。

### 示例三：NEG 噪声型

> 当前问题属于 NEG 场景，系统不应检出会诱导回答的伪相关内容；但原生检索返回了语义相近的噪声记忆，造成检索层判为 NOISE，并进一步诱导在线回答产生猜测式输出，因此主要问题是 NEG 检索噪声控制不足。

### 示例四：生成失败型

> 当前记忆系统已经写入并检索到了与问题相关的关键信息，但在给定有效证据的情况下仍未能生成正确答案，说明问题主要位于生成层的忠实性或推理阶段。

---

## 3.3 建议的归因 Agent 输出升级方向

建议后续把最终归因输出分成两层：

### 第一层：结构化字段

保留现有字段，便于程序统计：

1. `primary_cause`
2. `secondary_causes`
3. `probe_states`
4. `probe_defects`

### 第二层：自然语言叙述字段

新增类似字段：

1. `narrative_summary`
2. `narrative_short`
3. `narrative_detailed`

建议格式如下：

### `narrative_short`

一句话版本，适合表格或 summary：

> 该题的主要问题在检索层：系统已编码相关信息，但未能将关键证据在高位检出，导致在线回答错误。

### `narrative_detailed`

完整版本，适合逐题报告：

> 对于该 query，编码层显示系统中已存在与目标事实相关的记忆痕迹，但检索层结果表明原生检索未能返回关键证据，且检索结果中包含较强噪声。由于在线回答缺乏充分支撑，生成模型最终给出了错误答案。综合三层探针结果，主要问题定位于检索层，生成层错误属于上游证据缺失带来的次生后果。

这样做的价值是：

1. 对人类阅读更友好
2. 更适合写结果分析报告
3. 更适合直接写入论文或实验案例分析

---

## 4. 关于 LLM-as-Judge：文档层建议如何描述

## 4.1 当前结论：不要把问题说成“只是太严格”

从现有结果看，当前 LLM-as-Judge 的问题不能简单写成：

- “它太严格了”

更准确的描述应当是：

- **当前 judge 在 NEG / refusal / 语义近邻噪声场景中存在明显的不稳定性。**

因为在现有结果里同时出现了两类样本：

1. 拒答本来接近合理，但被判错
2. 含噪猜测答案本来应该判错，但被放过

所以它的问题更像是：

1. refusal 的判定边界不稳定
2. NEG 场景下“语义接近但并非 gold”时的宽严尺度不稳定
3. online / oracle 两路在个别题上的放行标准不完全一致

---

## 4.2 TiMem 风格 prompt 的关键思想

你要求 prompt 参考 `docs/2601.02845v1-TiMem.pdf`，这个方向是合理的。

从 TiMem 的评估思路出发，文档里建议把 judge 的核心原则描述成下面三条：

### 原则一：对语义等价保持宽松

只要生成答案与 gold answer 指向同一事实，就应判为正确，而不要求字面完全一致。

### 原则二：对时间问题允许表达形式差异

如果回答表达的是同一时间点、同一日期或同一时间区间，即使写法不同，也应判为正确。

例如：

1. `7 May 2023`
2. `May 7th, 2023`
3. `on May 7`

这些在本质上是同一时间表达，应视为一致。

### 原则三：输出必须稳定、简洁、可解析

judge 不应返回长段自由文本，而应返回稳定的结构化结果，例如：

1. `CORRECT`
2. `WRONG`

或者 JSON：

```json
{"label": "CORRECT"}
```

这样更利于大规模自动评测。

---

## 4.3 文档中推荐使用的 judge prompt 描述

如果要在方案文档或实验报告中描述 judge prompt，可以采用下面这种说法：

> 我们在 correctness judge 的设计上参考 TiMem 的评估思想，采用“宽松语义等价”原则：只要生成答案与 gold answer 在事实层面表达一致，即判为正确，而不要求完全字面匹配。对于时间类问题，judge 允许不同日期格式、相对时间表达与标准日期之间的等价映射。最终 judge 输出统一的结构化标签，以保证大规模评测时的稳定性与可解析性。

如果需要更具体一点，可以进一步写为：

> 给定问题、gold answer 和生成答案后，judge 需要判断生成答案是否与 gold answer 指向同一核心事实。对时间问题，若两者指向同一具体时间点或时间区间，即便表达形式不同，也视为正确；对一般事实问题，只要答案触及同一主题且不引入关键性错误，即可判为正确。judge 最终仅返回结构化标签，以降低自由文本输出带来的判定漂移。

---

## 4.4 文档里推荐附上的 TiMem 风格 prompt 样式

如果你想在后续方案文档中附一个示意 prompt，可以使用下面这种表达方式：

```text
You are an expert grader that determines whether a generated answer matches a gold answer.

You will be given:
1. a question
2. a gold answer
3. a generated answer

Be generous in grading:
- If the generated answer expresses the same underlying fact as the gold answer, label it CORRECT.
- For temporal questions, if the generated answer refers to the same date or time period as the gold answer, label it CORRECT even if the wording differs.
- If the generated answer introduces a different fact, an unsupported guess, or misses the required fact, label it WRONG.

Return only JSON:
{"label":"CORRECT"} or {"label":"WRONG"}
```

这类 prompt 的核心不是“无限放宽”，而是：

1. 对真正语义等价保持宽容
2. 对编造和偏题保持严格
3. 对输出格式保持可解析

---

## 5. 当前建议写进报告的正式表述

如果你现在要把这部分写进说明文档或论文报告，我建议直接使用下面这段概括：

> 需要强调的是，baseline 结果主要反映原记忆系统自身的在线回答表现，而非三层评测框架对系统行为的干预结果。评测框架在 baseline 阶段主要承担统一调用、记录与 correctness 判定的职责，因此 baseline 的低准确率不能直接归因于三层探针本身，但最终准确率统计仍会受到统一 judge 口径影响。另一方面，当前归因 Agent 已能够给出主要责任层，但后续更理想的方向是将三层探针结果进一步整合为自然语言叙述，使系统能够直接用完整句子解释“该 query 上当前记忆系统具体出现了什么问题”。在 judge 设计上，则建议参考 TiMem 的宽松语义等价思路，对同义事实与时间表达保持宽容，同时严格区分真实匹配与噪声诱导式猜测。  

---

## 6. 一句话总结

这部分目前最应强调的三个结论是：

1. **baseline 低准确率不能直接等同于评测框架失败**
2. **最终归因 Agent 应从标签式输出升级为完整自然语言解释**
3. **LLM-as-Judge 的 prompt 应参考 TiMem 的宽松语义等价原则，而不是简单做严格字面匹配**
