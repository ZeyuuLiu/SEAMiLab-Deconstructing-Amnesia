# 0407 运行结果详细分析报告（v0.1）

## 1. 文档目的

本文档用于对 0407 这一轮真实运行结果做系统性分析，重点回答以下问题：

1. 为什么当前最终准确率仍然偏低
2. “准确率低”到底是 judge 导致，还是系统本身链路存在问题
3. O-Mem 与 MemBox 在这轮结果里分别暴露出了什么主要问题
4. 三层探针与最终正确率之间到底应该如何一起解读

本文档聚焦的是**结果分析报告**，不是代码实现报告。

---

## 2. 本次分析对象

本次主要分析以下四个结果文件：

### 2.1 O-Mem

1. `outputs/o_mem_conv26_baseline_0407.json`
2. `outputs/o_mem_conv26_eval_0407.json`
3. `outputs/o_mem_conv26_eval_0407/conv-26/*.json`

### 2.2 MemBox

1. `outputs/membox_conv26_baseline_0407.json`
2. `outputs/membox_conv26_eval_0407.json`
3. `outputs/membox_conv26_eval_0407/conv-26/*.json`

---

## 3. 总体结论先说清楚

这轮 0407 结果最重要的结论有四条：

1. **O-Mem 明显强于 MemBox**
   - O-Mem eval 最终准确率为 `0.5578`
   - MemBox eval 最终准确率为 `0.1307`

2. **当前低准确率不能简单归因为“LLM-as-Judge 过于严格”**
   - 有些题上 judge 偏严格
   - 但也有不少题上 judge 明显偏宽松
   - 更准确的说法是：**judge 在 NEG / refusal / 语义近邻噪声题上不稳定**

3. **MemBox 的核心问题不是 judge，而是编码层与检索层和当前 probe 明显失配**
   - 编码层 `MISS = 199`
   - 检索层对 POS 几乎全部 `MISS`
   - 这说明其低分主要来自链路前两层，而不是只来自最后判分

4. **O-Mem 的问题则是多层累计损失叠加 judge 摇摆**
   - 它不是某一层完全失效
   - 而是编码、检索、生成都在掉点
   - 同时最终 correctness judge 在部分 NEG 题上前后口径不稳

---

## 4. 结果概览

## 4.1 baseline / eval 总体数字

### O-Mem

1. baseline：
   - `final_correct = 111`
   - `final_accuracy = 0.5578`

2. eval：
   - `final_correct = 111`
   - `final_accuracy = 0.5578`
   - `pos_final_accuracy = 0.5649`
   - `neg_final_accuracy = 0.5333`

### MemBox

1. baseline：
   - `final_correct = 30`
   - `final_accuracy = 0.1508`

2. eval：
   - `final_correct = 26`
   - `final_accuracy = 0.1307`
   - `pos_final_accuracy = 0.1299`
   - `neg_final_accuracy = 0.1333`

## 4.2 这组数字意味着什么

### 对 O-Mem

O-Mem 的 baseline 与 eval 最终准确率相同，说明：

1. 评测链路并没有显著“抬高”或“压低”它的 online 最终答对率
2. eval 的价值主要体现在分层诊断，而不是最终 accuracy 本身提升

### 对 MemBox

MemBox 的 baseline 和 eval 都非常低，并且 eval 比 baseline 更低，说明：

1. 不是“只有 probe 很差，但 online 最终答得很好”
2. 而是系统 online 回答本身就已经偏弱
3. probe 进一步告诉我们：问题主要集中在编码和检索，而不是纯生成能力

---

## 5. 当前低准确率到底是不是 judge 太严格

## 5.1 结论：不是单纯“太严格”，而是“口径不稳定”

很多人看到准确率低，第一反应是：

- 是不是 judge 太严格了？

这轮结果显示，这个判断只说对了一半。

### 一方面，judge 确实有偏严格的样本

例如 O-Mem 的 `conv-26:196`：

1. 这是 NEG 题
2. online 回答是：
   - `There is no information about Caroline's reaction to her children enjoying the Grand Canyon.`
3. 从规则上说，这是一种拒答式回答
4. `rule_correct = true`
5. 但 `llm_correct = false`
6. 最终 online correctness 被判错

这说明 judge 会受到检索到的近义噪声影响，把某些本来接近合理拒答的答案判成错误。

### 另一方面，judge 也有偏宽松甚至不稳定的样本

例如 O-Mem 的 `conv-26:197`：

1. 这是 NEG 题
2. online 回答是：
   - `spent time in nature`
3. 这显然不是拒答，更像是根据噪声内容猜了一个答案
4. 但 `llm_correct = true`
5. 最终 online correctness 被判对

同一题里，oracle 回答反而是：

- `No information available.`

但 oracle 被判错。

这说明当前 judge 在 NEG 场景下，并不是简单地“偏严格”，而是：

1. 对 refusal 的允许范围不稳定
2. 对近义噪声内容的放行尺度不稳定
3. 对 online 与 oracle 两路的语义边界也不完全一致

因此，本轮结果更准确的表述应当是：

- **当前最终准确率明显受到 mandatory correctness LLM judge 的影响，但该影响不是单向“变严格”，而是对 NEG / refusal / 语义相近题表现出不稳定。**

---

## 6. O-Mem 结果分析

## 6.1 O-Mem 的高层表现

O-Mem eval summary 显示：

1. `enc`：
   - `EXIST = 98`
   - `CORRUPT_WRONG = 20`
   - `MISS = 81`

2. `ret`：
   - `HIT = 82`
   - `MISS = 72`
   - `NOISE = 45`

3. `gen`：
   - `PASS = 117`
   - `FAIL = 82`

4. 缺陷统计：
   - `RF = 36`
   - `EM = 36`
   - `GH = 39`
   - `GRF = 29`
   - `EW = 20`
   - `LATE = 15`
   - `NOI = 10`

## 6.2 如何理解这些数字

这说明 O-Mem 不是一个“某层完全坏掉”的系统。

更准确地说：

1. 它的编码层能命中不少题，但并不稳定
2. 检索层既有真实 HIT，也有大量 MISS 和 NEG 噪声
3. 生成层整体比前两层更稳，但仍有不少 FAIL

也就是说，O-Mem 的问题是：

- **三层都有损失，但链路总体仍然可对齐、可解释**

这与 MemBox 形成了鲜明对比。

## 6.3 O-Mem 的典型正确样本

`conv-26:0` 是一个标准的理想样本：

1. online 回答正确
2. oracle 回答正确
3. 编码层 `EXIST`
4. 检索层 `HIT`
5. 生成层 `PASS`

同时，这个样本也体现出当前框架一个很好的地方：

1. 编码层 `coverage_report` 里已经记录了：
   - `query_retrieval_shadow_count = 20`
   - `f_key_retrieval_shadow_count = 20`
2. 这说明编码层并不是只看静态 memory export
3. 而是已经把“系统面向 question/f_key 的原生检索视角”并入了证据束

因此，O-Mem 的 good case 能够很好说明：

- 当前三层评测框架在 O-Mem 上是能形成闭环的

## 6.4 O-Mem 的主要问题

O-Mem 当前最主要的问题不是单一缺陷，而是三类问题叠加：

### 问题一：编码层并不稳

`enc.MISS = 81` 和 `enc.CORRUPT_WRONG = 20` 说明：

1. 系统并不是总能把关键事实稳定保存在可识别位置
2. 部分事实存在“存了，但值不完全对”的情况

### 问题二：NEG 检索噪声明显

`ret.NOISE = 45` 基本覆盖了全部 NEG。

这意味着：

1. O-Mem 对 NEG query 往往还是会找出一些语义相近内容
2. 这些内容不是真正 gold evidence
3. 但足以诱导模型回答

### 问题三：judge 在 NEG 上存在摇摆

有的拒答会被打错，有的编造会被放过。

所以 O-Mem 当前报告层面最准确的说法是：

- **真实链路存在编码与检索损失，同时最终 correctness judge 对 NEG 结果的统计也有波动。**

---

## 7. MemBox 结果分析

## 7.1 MemBox 的高层表现

MemBox eval summary 显示：

1. `enc`：
   - `MISS = 199`

2. `ret`：
   - `MISS = 154`
   - `NOISE = 45`

3. `gen`：
   - `PASS = 130`
   - `FAIL = 69`

4. 缺陷统计：
   - `EM = 154`
   - `NIR = 45`
   - `GH = 37`
   - `GRF = 22`
   - `GF = 10`

## 7.2 这组统计的关键含义

MemBox 最重要的问题非常集中：

- **编码层 199/199 全 MISS**

这不是“表现差一点”，而是：

1. 当前 encoding probe 基本无法在 MemBox 视图中识别出目标事实
2. 说明 probe 与 MemBox 的内部记忆表示之间仍然存在严重失配
3. 所以 MemBox 当前低分不是单纯的 judge 结果，而是上游层面先天吃亏

## 7.3 为什么说 MemBox 主要是前两层失配

看 `conv-26:0`：

1. online 回答：
   - `No mention of a support group.`
2. oracle 回答：
   - `7 May 2023`
3. `enc = MISS`
4. `ret = MISS`
5. `gen = PASS`

这个组合非常典型。

它说明：

1. 如果直接问系统，它答不出来
2. 但如果给足 oracle context，它是能答对的
3. 因此问题不在“生成模型完全不会答”
4. 而在“系统没有把正确证据有效编码/检到”

## 7.4 MemBox 结果不应被误读为“系统完全坏掉”

虽然 MemBox 分数很低，但 `gen.PASS = 130` 其实给出了一条非常重要的信息：

1. MemBox 的在线回答弱，不等于它的 underlying 语言模型完全没能力
2. 真实瓶颈更靠前
3. 当前更像是：
   - build 后的 box 表示对 probe 不够友好
   - native retrieval 输出和目标事实对齐度不高
   - 结果导致 online answer 拿不到真正该用的证据

因此，MemBox 这轮结果的正确报告方式不是：

- “MemBox 生成很差”

而是：

- **MemBox 在当前评测定义下，主要失效点位于编码与检索；oracle 条件下生成能力仍有相当比例可用。**

---

## 8. 为什么说三层探针和最终正确率不是一回事

这轮结果里最容易被误解的一点是：

- 为什么有些题 `gen = PASS`，但最终 `final_correct = false`？

原因是：

1. `gen` 探针判断的是：
   - 给系统完美 oracle context 之后，它会不会答对
2. `final_correct` 判断的是：
   - 系统真实 online answer 是否被 correctness judge 判为正确

因此：

### 一个题可以出现如下组合

1. `enc = MISS`
2. `ret = MISS`
3. `gen = PASS`
4. `final_correct = false`

这个组合的含义不是矛盾，而是：

1. 生成能力没有问题
2. 问题在前面的编码或检索
3. 所以 online answer 没拿到足够证据，最终答错

这正是三层框架的价值所在：

- **不是只告诉你“错了”，而是告诉你“为什么错”。**

---

## 9. 当前这份结果报告里应该如何描述 judge 的影响

建议不要写成：

- “准确率低主要因为 judge 太严格”

更合适的表述是：

### 推荐说法

1. 当前最终准确率由 `generation_correctness.online.final_correct` 直接决定
2. 因此 correctness LLM judge 会显著影响最终 accuracy
3. 但 judge 的影响不是单向“更严格”
4. 从样本看，它在 NEG / refusal / 语义相近噪声场景中表现出明显不稳定
5. 对 O-Mem，它放大了部分 NEG 题统计波动
6. 对 MemBox，judge 会影响最终分数，但不是造成其低分的主因，主因仍是编码/检索层失配

---

## 10. 可以直接写进正式报告的最终结论

如果要把本轮结果写成正式分析段落，建议可以概括为：

### 结论一

O-Mem 在 0407 结果中明显优于 MemBox，说明其记忆表示、原生检索和在线回答链路与当前三层评测框架具有更高的一致性。

### 结论二

MemBox 的主要瓶颈不是生成层，而是编码层与检索层。其 `enc = MISS (199/199)` 表明当前 probe 仍难以在 box 级摘要视图中恢复目标事实，`ret` 层的 POS 普遍 MISS、NEG 普遍 NOISE 进一步说明 query-facing evidence 与 gold fact 对齐不足。

### 结论三

当前 correctness judge 对最终 accuracy 影响显著，但从样本看并非简单“过严”，而是在 NEG / refusal / 语义相近噪声场景中存在明显不稳定性。因此，本轮低准确率应被解释为：

- **mandatory correctness LLM judge 与上游三层链路真实失配共同作用的结果。**

### 结论四

三层探针与最终正确率分别承担不同职责：前者用于定位错误责任层，后者用于统计系统 online 最终答题表现。两者不一致并不意味着框架矛盾，恰恰说明框架能够区分“能力存在”和“链路可达”这两个层面。
