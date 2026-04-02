# 评估框架下一步解决方案与改造说明（v0.1）

## 1. 文档目标

这份文档只做方案说明，不修改代码。

目标是围绕当前你提出的五个问题，给出一套更清晰、后续可落地的改造方案：

1. 为什么 MemBox 现在 baseline 能跑、eval 却会卡死。
2. 为什么 baseline 不能继续只用字符串匹配，必须引入 LLM-as-judge。
3. 为什么 generation 层也必须统一采用语义判分，而不是字面判分。
4. eval 结果应该怎么展示、怎么简化归因、怎么逐题落盘。
5. 编码层如何给你自己的 RAG 框架留接口。

## 2. 当前现状总结

结合当前代码与现有结果文件，我对现状的判断如下：

### 2.1 框架主干已经成立

当前已经具备：

1. 三个并行探针 Agent：
   - EncodingAgent
   - RetrievalAgent
   - GenerationAgent
2. 一个最终归因 Agent：
   - AttributionAgent
3. 统一运行入口：
   - `scripts/run_real_memory_eval.py`
4. 统一适配器层：
   - O-Mem
   - MemBox

所以评估框架本身并不是空白，问题主要在：

1. 评判口径
2. 运行稳定性
3. 结果组织
4. 对外扩展接口

### 2.2 baseline 与 eval 现在是两套口径

当前 baseline 更像：

1. 跑系统
2. 取在线答案
3. 用规则或简单比较给对错

当前 eval 更像：

1. 跑系统
2. 进行三探针归因
3. 输出复杂 probe-level 结果

这会导致一个核心问题：

> baseline 与 eval 并没有共享同一套“语义正确性判断标准”。

### 2.3 MemBox 的 eval 卡死问题不能只从评估层看

当前 MemBox baseline 已经能运行，并且 sample0 需要较长时间，这本身说明：

1. MemBox 的构建阶段非常重
2. 它内部有大量 LLM 调用
3. 一旦缺少细粒度日志与超时保护，就容易表现成“卡死”

所以它并不一定真的是死锁，也可能是：

1. 构建阶段超慢
2. 某次 API 调用长时间挂起
3. trace/link 阶段没有心跳日志
4. eval 入口在 ingest 后没有逐题进度输出

## 3. 问题一：MemBox 没有独立环境，baseline 能跑，eval 卡死

## 3.1 我对问题的判断

这类问题大概率不是单一原因，而是三个因素叠加：

### 3.1.1 环境未隔离

MemBox 与 O-Mem 混在同一环境里时，很容易出现：

1. 依赖版本漂移
2. OpenAI/embedding/client 包冲突
3. NLTK / sklearn / torch / transformers 相互污染

即使 baseline 能跑，也不代表 eval 运行路径完全等价。

### 3.1.2 eval 的运行链更长

baseline 当前只做：

1. ingest
2. online answer
3. correctness

但 eval 还会继续做：

1. export full memory
2. retrieve original
3. generate oracle answer
4. 三探针归因

这意味着 eval 比 baseline 调用了更多路径，任何一个环节挂住都会表现成“整条任务没有输出”。

### 3.1.3 当前日志粒度不够

现在主要日志更偏系统构建日志，而不是评估流程日志。

所以一旦卡住，你只能看到：

1. 前面在 BUILD/TRACE
2. 后面没输出了

但不知道卡在：

1. ingest
2. retrieve_original
3. generate_oracle_answer
4. 第几道题
5. 哪个 probe

## 3.2 解决方案

我建议把 MemBox 的运行路径拆成两个阶段。

### 阶段 A：Memory Build 阶段

只负责：

1. ingest conversation
2. build boxes
3. trace link
4. 产出 memory artifacts

输出：

1. `run_ctx`
2. `artifact_index`
3. `build_manifest`

### 阶段 B：Evaluation 阶段

只负责：

1. 读取 build 产物
2. 按题执行 baseline 或 eval
3. 逐题落盘

这样可以把：

1. 系统构建问题
2. 评估流程问题

分开排查。

## 3.3 建议的运行改造点

后续代码应增加：

1. **逐题心跳日志**
   - 当前 question_id
   - 当前 probe
   - 当前耗时
2. **单题超时**
   - retrieve timeout
   - oracle generation timeout
   - attribution timeout
3. **build / eval 分离入口**
4. **每一步 artifact index**

## 3.4 推荐的环境方案

MemBox 必须有自己的独立 conda 环境：

1. `memeval-membox-v1`

并且后续任何新系统都应采用：

1. `memeval-<system>-v1`

这种一系统一环境的策略。

## 4. 问题二：baseline 最终结果必须采用 LLM-as-judge

## 4.1 当前问题

现在 baseline 的对错判断过于字面。

例如：

1. 时间表达不同
2. 语义等价表达不同
3. 更短或更自然的回答
4. 同义词
5. 抽象程度不同

都会被错误判成 false。

这会带来系统性偏差：

> 系统其实答对了，但 baseline 把它判错。

## 4.2 解决方案：引入统一 CorrectnessJudge

我建议新增一个独立层：

1. `CorrectnessJudge`

统一负责 baseline 和 generation 的最终语义正确性判断。

### 这个 Judge 的输入

1. `task_type`
2. `question`
3. `answer_gold`
4. `answer_pred`
5. 可选 `oracle_context`
6. 可选 `retrieved_context`

### 输出

1. `rule_correct`
2. `llm_correct`
3. `final_correct`
4. `judgement_reason`
5. `semantic_equivalence_type`
6. `judge_payload`

## 4.3 Pos 与 Neg 必须分流

### POS

POS 任务下，judge 问题是：

1. 预测答案是否与 gold 在语义上等价？

### NEG

NEG 任务下，judge 问题不是：

1. 预测答案是否和 gold 模板一样？

而是：

1. 系统是否成功拒答？
2. 是否编造了原文没有的信息？

所以 NEG judge 必须是：

1. refusal-aware
2. hallucination-aware

## 4.4 baseline 的最终推荐口径

我建议 baseline 最终不再只输出一个 `correct: true/false`，而是输出：

1. `rule_correct`
2. `llm_correct`
3. `final_correct`
4. `judge_reason`

其中：

1. `rule_correct` 用于可复现对账
2. `llm_correct` 用于语义补判
3. `final_correct` 作为最终统计口径

## 5. 问题三：generation 层同样需要语义判分

## 5.1 当前问题

你说得对，generation 层现在虽然有 Agent 化结构，但“最终这个回答算不算正确”仍没有完全做到统一语义判别。

这会导致两个问题：

1. `A_oracle` 与 `A_gold` 语义等价却被判错
2. `A_online` 与 `A_gold` 语义等价却没有进入最终正确统计

## 5.2 解决方案

generation 层应统一接入刚才说的 `CorrectnessJudge`。

### 对 `A_oracle`

判断：

1. `oracle_correct_semantic`

### 对 `A_online`

判断：

1. `online_correct_semantic`

### 再结合 probe 逻辑输出

1. `PASS / FAIL`
2. `GF / GRF / GH`

## 5.3 generation 的正确口径

我建议 generation 层区分两个层次：

### 层次一：任务正确性

1. 最终回答是否正确

### 层次二：归因正确性

1. 为什么错
2. 是没用上下文，还是推理失败，还是幻觉

这两层不能混。

## 6. 问题四：eval 结果展示、归因简化、逐题单独落盘

## 6.1 当前问题

当前 eval 结果存在三个可读性问题：

1. 顶层 JSON 太大
2. 每道题被埋在 `results[]` 里，不好单独看
3. AttributionAgent 输出重复了很多 probe 已经有的信息

## 6.2 解决方案：结果拆成三层

我建议 eval 结果改成三层产物。

### 第一层：run 级 summary

文件：

1. `run_summary.json`

内容：

1. 运行配置
2. task count
3. defect count
4. final accuracy / refusal rate / probe stats

### 第二层：题级结果索引

文件：

1. `question_index.json`

内容：

1. question_id
2. task_type
3. final_correct
4. primary_cause
5. per-question 文件路径

### 第三层：逐题详细结果

目录：

1. `questions/<question_id>.json`

内容：

1. 当前问题
2. 当前系统回答
3. 当前正确/错误判断
4. 三探针状态
5. 最终归因结果
6. 简洁的判别逻辑
7. 如需深挖，再附详细 evidence

## 6.3 AttributionAgent 的简化方向

你说得非常对：

> 最终归因不应该重复前三个 probe 已经说过的内容。

我建议最终归因层以后只保留：

1. `final_attribution`
2. `primary_cause`
3. `secondary_causes`
4. `decision_logic`
5. `final_judgement`

其中 `decision_logic` 最好是 2-4 条简洁结论，例如：

1. 编码层未写入关键事实
2. 检索层未召回 gold evidence
3. 生成层在完美上下文下仍失败

不要再把 probe 大段 evidence 复制一遍。

## 6.4 我建议每题文件的结构

每一道题单独一个 JSON，建议字段如下：

1. `question_id`
2. `sample_id`
3. `task_type`
4. `question`
5. `answer_gold`
6. `answer_online`
7. `baseline_correctness`
8. `generation_correctness`
9. `probe_states`
10. `probe_defects`
11. `final_attribution`
12. `decision_logic`
13. `artifact_refs`

## 7. 问题五：编码层需要给你的自定义 RAG 框架留接口

## 7.1 当前问题

现在编码层虽然已经有：

1. `export_full_memory`
2. `find_memory_records`
3. `hybrid_retrieve_candidates`

但这些还不够成为你未来自定义 RAG 框架的标准接入点。

## 7.2 解决方案：新增 HighRecall Retrieval Hook

我建议编码层正式增加一个可插拔接口，例如：

1. `EncodingHighRecallRetriever`

### 接口输入

1. `query`
2. `f_key`
3. `evidence_texts`
4. `memory_corpus`
5. 可选 `metadata`

### 接口输出

1. 高召回候选列表
2. 候选分数
3. 检索诊断信息

## 7.3 接入方式

我建议用两层方式接入：

### 适配器可实现

如果某个记忆系统自己已经有原生高召回检索，就走：

1. adapter native high-recall

### 外部自定义可注入

如果你要接自己的 RAG 框架，就走：

1. external retriever hook

优先级可以设计成：

1. external custom retriever
2. adapter hybrid retrieve
3. adapter find records
4. rule fallback

## 7.4 为什么这个接口重要

因为你后面要做的不是单纯替换一个函数，而是：

> 用你自己的 RAG 方式去扫描原始记忆系统全量数据库。

这意味着编码层必须提前有一个“高召回候选提供者”的标准槽位。

## 8. 我建议的整体改造顺序

如果后续开始改代码，我建议按下面顺序推进。

### 第一阶段

先解决运行稳定性：

1. MemBox 独立环境
2. build/eval 分离
3. 逐题心跳日志
4. 单题超时与 fail-fast

### 第二阶段

统一正确性判断：

1. baseline 引入 LLM-as-judge
2. generation 引入统一 CorrectnessJudge
3. Pos / Neg 完全分流

### 第三阶段

重构结果输出：

1. run_summary
2. question_index
3. per-question json
4. 简化 AttributionAgent 输出

### 第四阶段

开放编码层接口：

1. 引入自定义 high-recall retriever hook
2. 给你的 RAG 框架留正式入口

## 9. 我对最终目标架构的理解

我理解你真正想要的不是“一个能跑的 eval JSON”，而是一个：

1. **能稳定运行**
2. **能语义判分**
3. **能逐题审阅**
4. **能最终归因**
5. **能接入未来更多记忆系统**
6. **能让你替换编码层高召回检索**

的统一评估框架。

所以后续代码改造的目标不应该只是：

1. 修一个 MemBox 卡死问题
2. 修一个字符串误判问题

而应该是：

> **把当前评估框架升级成“运行稳定 + 语义判分 + 逐题可解释 + 可扩展接口”的正式系统。**

## 10. 结论

对于你现在提出的五点，我的结论非常明确：

1. **MemBox eval 卡死问题本质上是运行稳定性与可观测性问题**
2. **baseline 必须引入 LLM-as-judge**
3. **generation 层也必须统一做语义正确性判断**
4. **eval 结果必须按 run / index / per-question 三层落盘，并简化最终归因**
5. **编码层必须正式留出自定义 RAG 高召回接口**

如果你认可这个方向，下一步我建议我继续给你写第二份更细的文档：

**《CorrectnessJudge 与逐题结果落盘详细技术设计》**

这会直接把：

1. baseline 的 LLM-as-judge
2. generation 的语义判分
3. per-question JSON schema

都落到可实施的技术规格上。
