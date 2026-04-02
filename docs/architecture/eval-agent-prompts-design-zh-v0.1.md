# 评估层四个 Agent 的 Prompt 设计说明（v0.1）

## 1. 文档目标

这份文档专门说明当前评估层四个 Agent 的 prompt 设计。

目标是明确：

1. 每个 Agent 使用什么 prompt
2. Prompt 在代码中的具体位置
3. Pos 与 Neg 任务为什么必须分开处理
4. 每个 prompt 的输入、输出和判定重点是什么

## 2. Prompt 代码位置

当前所有 Agent prompt 统一收敛在：

- `src/memory_eval/eval_core/prompts.py`

调用位置主要在：

- `src/memory_eval/eval_core/llm_assist.py`
- `src/memory_eval/eval_core/attribution_agent.py`

也就是说：

1. `prompts.py` 负责定义 prompt 文本
2. `llm_assist.py` 负责把 prompt 发给大模型并解析 JSON
3. 各 Agent 通过 `llm_assist.py` 间接使用这些 prompt

## 3. 为什么必须区分 Pos 与 Neg

这是整个评估层最重要的前提之一。

### 3.1 Pos 任务

Pos 表示：

1. 当前 query 在原文中有证据支撑
2. 系统应当存储该证据
3. 系统应当检索到该证据
4. 系统应当基于证据正确回答

所以 Pos 的目标是：

1. 找到证据
2. 判断证据质量
3. 判断是否答对

### 3.2 Neg 任务

Neg 表示：

1. 当前 query 在原文中没有相关证据支撑
2. 系统应当拒答
3. 记忆系统不应存有伪相关支撑
4. 检索层不应召回足以误导回答的噪声
5. 生成层不应编造答案

所以 Neg 的目标不是“找证据”，而是：

1. 判断系统是否错误地存了伪记忆
2. 判断系统是否错误地检索了误导内容
3. 判断系统是否错误地生成了幻觉答案

因此 Pos 与 Neg 的 prompt 逻辑必须分离，否则模型很容易把：

- “没找到证据”

和

- “本来就不该找到证据”

混为一谈。

## 4. EncodingAgent 的 Prompt

## 4.1 Pos Prompt

代码位置：

- `build_encoding_pos_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断 gold evidence 是否真实存在于记忆中
2. 允许语义等价、格式变化、多条记录联合支撑
3. 区分：
   - `EXIST`
   - `MISS`
   - `CORRUPT_AMBIG`
   - `CORRUPT_WRONG`

输出 JSON 要点：

1. `encoding_state`
2. `defects`
3. `confidence`
4. `matched_candidate_ids`
5. `reasoning`
6. `evidence_snippets`
7. `missing_facts`

## 4.2 Neg Prompt

代码位置：

- `build_encoding_neg_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断系统是否错误存入了可支撑回答的伪记忆
2. 若存在伪记忆，输出 `DIRTY + DMP`
3. 若不存在此类伪记忆，输出 `MISS`

这里 Neg 的关键不是“找不到证据”，而是：

> **判断系统是否被污染。**

## 5. RetrievalAgent 的 Prompt

## 5.1 Pos Prompt

代码位置：

- `build_retrieval_pos_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断原生检索结果中是否实质包含 gold evidence
2. 判断排序是否过晚
3. 判断噪声是否过大

输出 JSON 要点：

1. `retrieval_state`
2. `defects`
3. `matched_ids`
4. `reasoning`
5. `evidence_snippets`

Pos 检索层关心的是：

1. 找没找到
2. 排得够不够前
3. 有没有被噪声淹没

## 5.2 Neg Prompt

代码位置：

- `build_retrieval_neg_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断原生检索结果是否产生了足以诱导错误回答的噪声
2. 若有误导性噪声，输出 `NOISE + NIR`
3. 否则输出 `MISS`

Neg 检索层不问“有没有正确证据”，而问：

> **有没有危险噪声。**

## 6. GenerationAgent 的 Prompt

生成层目前分成两类 prompt：

1. oracle correctness prompt
2. online/oracle/gold comparison prompt

## 6.1 Pos Oracle Prompt

代码位置：

- `build_generation_pos_answer_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断在完美证据上下文下，`A_oracle` 是否正确
2. 若错误，区分：
   - `GF`
   - `GRF`

## 6.2 Neg Oracle Prompt

代码位置：

- `build_generation_neg_answer_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断在完美上下文下，系统是否仍然没有拒答
2. 若没有拒答而是编造内容，则判为 `GH`

## 6.3 Pos Comparison Prompt

代码位置：

- `build_generation_pos_comparison_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 同时比较 `A_online / A_oracle / A_gold`
2. 判断 online 和 oracle 各自是否正确
3. 给出生成层 PASS/FAIL 结论

## 6.4 Neg Comparison Prompt

代码位置：

- `build_generation_neg_comparison_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

职责：

1. 判断 `A_online` 和 `A_oracle` 是否都体现拒答
2. 若任一答案编造具体信息，则视为 `GH`

Neg 生成层本质上是在判：

> **系统有没有在“不该回答”的情况下硬答。**

## 7. AttributionAgent 的 Prompt

代码位置：

- `build_attribution_prompt(...)`
- 文件：`src/memory_eval/eval_core/prompts.py`

调用位置：

- `llm_judge_attribution(...)`
- `src/memory_eval/eval_core/llm_assist.py`

作用：

1. 综合编码、检索、生成三个探针结果
2. 输出：
   - `primary_cause`
   - `secondary_causes`
   - `decision_trace`
   - `summary`

这里的 prompt 仍然保留原始逻辑约束：

1. 编码层判断有没有存
2. 检索层判断有没有取到
3. 生成层判断给了证据能不能答对

它不是让模型自由发挥，而是在三层结果基础上做责任排序和解释。

## 8. 当前 Prompt 设计原则

当前 prompt 设计遵循五个原则。

### 8.1 明确任务语义

每个 prompt 开头都会明确说明当前是：

1. Pos
2. Neg

避免任务语义混淆。

### 8.2 明确 Agent 职责

每个 prompt 都会强调：

1. 这个 Agent 到底在判断什么
2. 它不应该越权判断什么

### 8.3 输出严格 JSON

所有 prompt 都要求严格 JSON，便于解析和测试。

### 8.4 保留原始逻辑

prompt 设计不是在重写你的指标逻辑，而是在自然语言层面更清楚地表达原始逻辑。

### 8.5 Pos/Neg 完全分流

这是最重要的原则：

1. Pos 判断“有没有正确证据”
2. Neg 判断“有没有不该有的支撑/噪声/编造”

## 9. 当前 Prompt 设计的价值

这次 prompt 重构最大的价值在于：

1. 把原来零散的 judge prompt 集中管理
2. 把 Pos/Neg 差异写清楚
3. 让四个 Agent 各自有清晰的语言合同
4. 为后续继续优化 prompt 提供固定位置

## 10. 结论

当前评估层的 prompt 已经完成如下收敛：

1. 所有 Agent prompt 统一放在 `prompts.py`
2. Pos 与 Neg 明确分流
3. Encoding、Retrieval、Generation、Attribution 四个 Agent 都有自己的专属 prompt
4. 这些 prompt 已经接入当前 LLM judge 调用链

因此后续如果你还要继续优化 prompt，最主要的编辑位置就是：

- `src/memory_eval/eval_core/prompts.py`
