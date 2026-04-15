# 三层探针与归因 Agent 详细说明文档（v0.1）

## 1. 文档目的

本文档专门回答以下几个问题：

1. 编码层、检索层、生成层三层探针的输入输出分别是什么
2. 三层探针各自的判断逻辑是什么
3. `probe_states`、`probe_defects`、`generation_correctness`、`final_attribution` 之间是什么关系
4. 最终归因 Agent 到底是如何做决策的
5. 为什么某些题会出现“三层不差但 final_correct 低”或者“某层差但最终答对”的现象

这份文档的目标是让你之后看任何一个 `outputs/*eval*/conv-26/*.json` 文件时，都能知道每个字段在表达什么。

---

## 2. 整体执行流程

## 2.1 单题评测的总体结构

对于每一道题，评测框架会做四件事：

1. 先由适配器从原记忆系统中取出：
   - memory view
   - native retrieval
   - online answer
   - oracle answer

2. 并行运行三个探针：
   - EncodingAgent
   - RetrievalAgent
   - GenerationAgent

3. 再把三层结果交给 AttributionAgent

4. 最后把这些结果写成逐题 JSON

这条并行主链路的入口在：

- `src/memory_eval/eval_core/engine.py`

对应逻辑可以概括成：

1. `f_enc = encoding_agent.evaluate_with_adapter(...)`
2. `f_ret = retrieval_agent.evaluate_with_adapter(...)`
3. `f_gen = generation_agent.evaluate_with_adapter(...)`
4. `attribution_agent.attribute(sample, enc, ret, gen, cfg)`

---

## 2.2 逐题 JSON 最终结构

每题最终 JSON 里最重要的几块是：

1. `generation_correctness`
2. `probe_states`
3. `probe_defects`
4. `probe_results`
5. `final_attribution`
6. `artifact_refs`

它们分别承担不同职责：

### `generation_correctness`

它表达的是：

- online / oracle 最终答案各自是否被 correctness judge 判对

### `probe_states`

它表达的是：

- 三层探针各自的状态标签

### `probe_defects`

它表达的是：

- 每层对应的缺陷代码

### `probe_results`

它表达的是：

- 每层做出该判断时用到的证据与解释

### `final_attribution`

它表达的是：

- 三层里面谁是最主要责任层

---

## 3. 编码层探针

## 3.1 编码层要回答什么问题

编码层不是看系统最后答对没有，而是回答一个更早的问题：

- **系统内部到底有没有形成支撑当前问题的记忆表示？**

也就是说，它评估的是“写进去了没有”，而不是“最后答出来没有”。

---

## 3.2 编码层输入是什么

编码层核心输入结构有两部分：

### 第一部分：`EvidenceSpec`

它描述这道题“理论上应该被记住的内容”。

主要字段包括：

1. `query`
2. `task_type`
3. `f_key`
4. `evidence_texts`
5. `evidence_with_time`
6. `oracle_context`
7. `must_have_constraints`

你可以把它理解成：

- 这是这道题的 gold 记忆需求描述

### 第二部分：`MemoryObservationBundle`

它描述系统当前可观察到的“实际记忆证据”。

主要字段包括：

1. `full_memory_view`
2. `native_candidate_view`
3. `framework_candidate_view`
4. `native_retrieval_shadow`
5. `combined_candidates`
6. `candidate_groups`
7. `coverage_report`

你可以把它理解成：

- 这是系统当前内部到底留下了什么痕迹

---

## 3.3 编码层是怎么采集证据的

编码层采集证据时不是只看一种来源，而是会合并多种视角：

### 视角一：全量 memory export

来自：

- `export_full_memory(run_ctx)`

含义：

- 直接看系统目前有哪些记忆条目

### 视角二：系统原生候选

来自：

1. `find_memory_records(...)`
2. `hybrid_retrieve_candidates(...)`
3. 外部 high recall retriever

含义：

- 看系统或评测框架是否已有较强候选集合

### 视角三：native retrieval shadow

这是本轮特别补强的部分。

现在编码层会额外调两次原系统原生检索：

1. 用 `question`
2. 用 `f_key` 拼出来的检索串

然后把两次结果并入编码层证据束。

这就是你在 `coverage_report` 里看到：

1. `query_retrieval_shadow_count`
2. `f_key_retrieval_shadow_count`

的原因。

它们的意义分别是：

1. 当前 query 视角下，系统能主动调出的记忆数
2. 关键事实视角下，系统能主动调出的记忆数

---

## 3.4 编码层输出状态是什么

### POS 任务

编码层可能输出：

1. `EXIST`
2. `MISS`
3. `CORRUPT_AMBIG`
4. `CORRUPT_WRONG`

#### 含义

1. `EXIST`
   - 关键事实能在候选中找到

2. `MISS`
   - 找不到任何能支撑关键事实的候选

3. `CORRUPT_AMBIG`
   - 只找到部分事实，且文本本身带歧义

4. `CORRUPT_WRONG`
   - 只找到部分事实，但值错了或信息被写坏了

### NEG 任务

编码层可能输出：

1. `MISS`
2. `DIRTY`

#### 含义

1. `MISS`
   - 没发现支撑禁止事实的伪记忆

2. `DIRTY`
   - 发现了足以诱导回答的脏记忆

---

## 3.5 编码层缺陷代码怎么理解

常见编码层缺陷：

1. `EM`
   - Encoding Miss

2. `EA`
   - Encoding Ambiguous

3. `EW`
   - Encoding Wrong

4. `DMP`
   - Dirty Memory Present

因此：

- `enc = MISS + EM`

表示：

- 该题需要的关键信息没有在可识别记忆里找到

---

## 4. 检索层探针

## 4.1 检索层要回答什么问题

检索层回答的问题是：

- **系统面对当前问题时，能不能把正确记忆从已有记忆中取出来？**

所以它看的不是“有没有存”，而是“能不能取到”。

---

## 4.2 检索层输入是什么

检索层的核心输入是：

1. `question`
2. `retrieved_items`
3. `f_key`
4. `task_type`
5. `evidence_texts`

这里最重要的是：

### `retrieved_items`

它表示：

- 原记忆系统真实返回的原生检索结果 `C_original`

因此检索层评估的是：

- **原系统真正检到了什么**

而不是框架自己额外脑补出来的候选。

---

## 4.3 检索层是怎么判断的

### POS 任务

它主要看三件事：

1. `f_key` 是否命中
2. 命中的 rank 是否太靠后
3. 命中集合里噪声是否太大

因此会计算：

1. `rank_index`
2. `hit_indices`
3. `snr`

### NEG 任务

NEG 任务不是看“是否命中 gold evidence”，而是看：

- 有没有检出足以误导模型回答的伪相关噪声

所以 NEG 重点看：

1. top item score
2. 是否存在高误导噪声

---

## 4.4 检索层输出状态是什么

### POS 任务

输出可能是：

1. `HIT`
2. `MISS`
3. `NOISE`

#### 含义

1. `HIT`
   - 找到了该找的内容

2. `MISS`
   - 没有找出关键事实

3. `NOISE`
   - 理论上更少见，通常表示结果高度偏噪

### NEG 任务

输出可能是：

1. `MISS`
2. `NOISE`

#### 含义

1. `MISS`
   - 没有检出危险噪声

2. `NOISE`
   - 检出了会诱导回答的伪相关噪声

---

## 4.5 检索层缺陷代码怎么理解

常见检索层缺陷：

1. `LATE`
   - 相关内容找到了，但排得太后

2. `NOI`
   - 噪声较大，但仍可算 HIT

3. `NIR`
   - NEG 下的误导性噪声检索

4. `RF`
   - Retrieval Failure

注意一点：

`RF` 不是一开始就直接由 retrieval probe 输出的，而是归因层会根据编码层状态进行门控补充：

1. 如果 retrieval 是 `MISS`
2. 且 encoding 不是 `MISS`
3. 且任务是 POS
4. 那么归因层会额外补 `RF`

这意味着：

- `RF` 更接近最终归因意义上的“检索失败”，不是纯底层原始信号

---

## 5. 生成层探针

## 5.1 生成层要回答什么问题

生成层不是简单地看系统 online 答案，而是同时看两路：

1. online answer
2. oracle answer

它要回答的问题是：

- **如果把完美证据给系统，它还有没有能力答对？**

因此，生成层更像是在测：

- 生成能力本身是否足够

而不是只测最终在线效果。

---

## 5.2 生成层输入是什么

生成层核心输入包括：

1. `question`
2. `oracle_context`
3. `answer_online`
4. `answer_oracle`
5. `answer_gold`
6. `task_type`
7. `retrieved_context`

其中最关键的是：

### `answer_online`

系统真实在线回答

### `answer_oracle`

在给定 oracle_context 后，系统生成的回答

### `retrieved_context`

系统真实检到的上下文，用于 online correctness judge

---

## 5.3 生成层是怎么判断的

生成层内部会分别做两次 correctness 判定：

### online correctness

输入：

1. question
2. answer_gold
3. answer_online
4. retrieved_context

意义：

- 真实系统在线回答答得对不对

### oracle correctness

输入：

1. question
2. answer_gold
3. answer_oracle
4. oracle_context

意义：

- 如果给足理想证据，它能不能答对

---

## 5.4 生成层输出状态是什么

生成层状态只有两种：

1. `PASS`
2. `FAIL`

但这里有一个非常关键的点：

### `gen = PASS` 的判定依据

`gen = PASS` 不是看 online answer 对不对，而是看：

- `oracle_correct = true`

这意味着：

1. 只要给足 oracle context 后系统能答对
2. 即使 online answer 错了
3. `gen` 仍然可以是 `PASS`

所以你看到：

1. `enc = MISS`
2. `ret = MISS`
3. `gen = PASS`
4. `final_correct = false`

这不是矛盾，而是：

1. 生成能力在
2. 但上游链路没把证据送到位

---

## 5.5 生成层缺陷代码怎么理解

常见生成层缺陷：

1. `GH`
   - Generation Hallucination

2. `GF`
   - Generation Faithfulness 问题

3. `GRF`
   - Generation Reasoning Failure

简化理解：

1. `GH`
   - NEG 该拒答却编了

2. `GF`
   - 有上下文但没忠实使用

3. `GRF`
   - 看到了上下文但推理错了

---

## 6. `generation_correctness` 和 `gen` 的关系

这是最容易混淆的一点。

### `generation_correctness.online.final_correct`

它表示：

- 系统真实 online answer 是否被最终 judge 判对

### `generation_correctness.oracle.final_correct`

它表示：

- 给了 oracle context 后，oracle answer 是否被判对

### `probe_states.gen`

它表示：

- 生成层能力是否通过

当前实现下，基本等价于：

- 看 oracle correctness 是否通过

因此：

1. `final_correct`
   - 是最终表现指标

2. `gen`
   - 是生成能力诊断指标

两者不是同一个概念。

---

## 7. 归因 Agent 是怎么做决策的

## 7.1 归因 Agent 的任务

归因 Agent 不负责重新判 online answer 对错。

它的职责是：

- **根据三层探针结果，判断哪个层最该为这道题的问题负责。**

---

## 7.2 归因 Agent 的输入

归因 Agent 的输入很简单：

1. `sample`
2. `enc`
3. `ret`
4. `gen`
5. `cfg`

也就是说，它只看三层探针的结果，不自己再访问原系统。

---

## 7.3 归因 Agent 的主决策顺序

当前主规则是一个很清晰的优先级链：

1. 如果 encoding 有问题
   - 归因给 `encoding`

2. 否则如果 retrieval 有问题
   - 归因给 `retrieval`

3. 否则如果 generation 有问题
   - 归因给 `generation`

4. 否则
   - `none`

这是一种“最早失败层优先”的思想。

因为如果编码层根本没写进去，那么后面检不到、答不出都只是后果。

---

## 7.4 归因 Agent 的输出是什么

归因 Agent 最终产出：

1. `primary_cause`
2. `secondary_causes`
3. `decision_logic`
4. `final_judgement`

### `primary_cause`

最主要责任层：

1. `encoding`
2. `retrieval`
3. `generation`
4. `none`

### `secondary_causes`

除主因之外，仍然存在问题的其他层

### `decision_logic`

给人的可读解释，比如：

1. 编码层状态为 MISS
2. 检索层状态为 NOISE
3. 生成层状态为 FAIL

### `final_judgement`

这是很重要但常被忽略的字段。

它不是责任层，而是最终结果归纳：

1. `system_answer_correct`
2. `system_answer_wrong_but_oracle_answer_correct`
3. `oracle_answer_incorrect`

---

## 7.5 为什么会出现“primary_cause = encoding，但 system_answer_correct”

这是很多第一次看结果的人会困惑的地方。

例如：

1. 某题 `primary_cause = encoding`
2. 但 `final_judgement = system_answer_correct`

这并不矛盾。

它表达的是：

1. 从链路角度看，最早的问题层是编码层
2. 但系统最后仍然答对了
3. 这可能是因为：
   - 检索拿到了近似噪声但刚好够用
   - 模型依靠模糊证据猜对了
   - judge 对该题在线答案放行了

所以：

- `primary_cause` 是链路归因
- `final_judgement` 是结果表现

这两个字段本来就可以不一致。

---

## 8. 如何正确阅读单题 JSON

建议你以后看单题结果时按下面顺序读：

## 第一步：看 `generation_correctness`

先看：

1. online 对不对
2. oracle 对不对

这一步回答的是：

- 系统最后答没答对
- 给足证据后还能不能答对

## 第二步：看 `probe_states`

再看：

1. `enc`
2. `ret`
3. `gen`

这一步回答的是：

- 问题大致卡在哪一层

## 第三步：看 `probe_results`

重点看：

1. `enc.coverage_report`
2. `ret.top_items`
3. `gen.retrieved_context`
4. `gen.online_correctness`
5. `gen.oracle_correctness`

这一步回答的是：

- 每层为什么会给出当前状态

## 第四步：看 `final_attribution`

最后看：

1. `primary_cause`
2. `secondary_causes`
3. `decision_logic`
4. `final_judgement`

这一步回答的是：

- 这题最终该怎么归因总结

---

## 9. 为什么这套框架对结果分析有价值

如果只看最终 accuracy，你只能知道：

- 这题答对了还是答错了

但你不知道：

1. 是根本没存进去
2. 还是存进去了但没检到
3. 还是检到了但生成失败
4. 还是系统答得其实还行，只是 judge 没放过

三层探针 + 归因 Agent 的价值就在于：

- **把“最终对错”拆成“编码、检索、生成、归因”四个可解释层次。**

这也是为什么同一题里可能出现：

1. online 最终错
2. 但 gen = PASS
3. primary_cause = retrieval

因为它真正表达的是：

- 模型会答，但系统没把正确证据送到它面前

---

## 10. 一句话总结

如果要把这套机制压缩成一句话，可以这样理解：

1. **Encoding**
   - 记住了没有

2. **Retrieval**
   - 找出来没有

3. **Generation**
   - 给足证据后会不会答

4. **Attribution**
   - 这题最该怪哪一层

而最终 accuracy 则只是：

- 系统真实 online answer 最后有没有被 judge 判对

因此，三层探针不是为了替代最终 accuracy，而是为了让最终 accuracy 变得可解释。
