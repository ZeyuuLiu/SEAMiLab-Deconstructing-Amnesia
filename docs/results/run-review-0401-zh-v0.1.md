# 0401 运行结果复核与后续代码完善建议（v0.1）

## 1. 文档目的

本文档用于复核以下五个命令对应的实际运行结果，并在**不修改代码**的前提下，给出：

1. 当前运行是否成功
2. 结果是否可信、是否存在异常
3. O-Mem 与 MemBox 各自暴露出的主要问题
4. 下一步应如何修改代码来继续完善评测框架

本次复核基于工作目录：

- `/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia`

## 2. 本次检查对象

### 2.1 O-Mem

1. `outputs/o_mem_conv26_baseline_0401.json`
2. `outputs/nohup_o_mem_conv26_baseline_0401.log`
3. `outputs/o_mem_conv26_eval_0401.json`
4. `outputs/o_mem_conv26_eval_0401/`
5. `outputs/nohup_o_mem_conv26_eval_0401.log`

### 2.2 MemBox

1. `outputs/membox_conv26_build_manifest_0401.json`
2. `outputs/nohup_membox_conv26_build_0401.log`
3. `outputs/membox_conv26_baseline_0401.json`
4. `outputs/nohup_membox_conv26_baseline_0401.log`
5. `outputs/membox_conv26_eval_0401.json`
6. `outputs/membox_conv26_eval_0401/`
7. `outputs/nohup_membox_conv26_eval_0401.log`

## 3. 总体结论

本次 0401 运行与之前 0331 那轮最大的区别是：**五个命令现在都已经跑通并且确实产出了结果文件**，尤其是 MemBox 的 `eval` 不再像之前那样静默失败。这说明你当前实现的 build/eval 分离、artifact 复用、逐题日志与逐题 JSON 落盘已经真正起效。

但从“结果质量”和“代码设计完整度”角度看，仍然存在几个明显问题：

1. O-Mem baseline 与 eval 在同一批 10 道题上的最终正确率从 0.9 提升到 1.0，看起来合理，但仍缺少对 warning 与异常迹象的结构化归档。
2. MemBox baseline 在 `conv-26` 全量 199 题上达到了 0.683 的最终正确率，远高于之前归档文档里 0.09 左右的结果，这说明当前 LLM-as-Judge 和 build 复用已经显著改变了统计口径。
3. MemBox eval 在前 10 题上虽然成功运行，但呈现出一个非常尖锐的问题：**编码层 10/10 全部 MISS，检索层 10/10 全部 MISS，而最终仍有 7/10 被判为 final correct**。这说明框架虽然能跑，但“MemBox 在线回答 / oracle 上下文 / correctness judge / 最终归因”之间仍存在明显张力，需要继续改代码完善。

## 4. O-Mem 结果复核

## 4.1 baseline 是否成功

成功。

证据如下：

1. `outputs/o_mem_conv26_baseline_0401.json` 存在
2. `summary.count = 10`
3. `summary.final_correct = 9`
4. `summary.final_accuracy = 0.9`

这表明 O-Mem baseline 这次确实对 `conv-26` 的前 10 道题完成了运行，且没有中途中断。

## 4.2 baseline 结果如何

整体结果较好，但并非没有问题。

### 好的方面

1. 10 题中 9 题被 LLM judge 判为正确
2. 多道题体现出语义判分比字符串匹配更合理，例如：
   - `counseling and mental health` 对应 `Psychology, counseling certification`
   - `last week` 对应 `the week before 9 June 2023`
3. 说明统一 CorrectnessJudge 的接入是有效的

### 需要警惕的方面

有几道题显示 LLM judge 已经比较宽松，例如：

1. `question_id = conv-26:8`
   - gold：`The week before 9 June 2023`
   - online：`9 June 2023`
   - 最终仍判为 correct
2. 这说明当前 correctness judge 在某些时间表达题上可能存在“语义放宽过度”的倾向

因此，O-Mem baseline 的结论是：

- 运行成功
- 结果整体合理
- 但 correctness judge 对时间型表达存在潜在宽松风险

## 4.3 eval 是否成功

成功。

证据如下：

1. `outputs/o_mem_conv26_eval_0401.json` 存在
2. `outputs/o_mem_conv26_eval_0401/` 目录存在
3. `summary.total = 10`
4. `summary.ok = 10`
5. `summary.errors = 0`
6. 日志中逐题输出了 `eval_question_start` / `eval_question_done`

这说明新的 eval pipeline 在 O-Mem 上已经形成完整闭环。

## 4.4 eval 结果如何

### 总体统计

1. `final_accuracy = 1.0`
2. `enc` 层：
   - `EXIST = 5`
   - `MISS = 3`
   - `CORRUPT_WRONG = 2`
3. `ret` 层：
   - `HIT = 7`
   - `MISS = 3`
4. `gen` 层：
   - `PASS = 9`
   - `FAIL = 1`

### 说明

这组结果说明 O-Mem 当前并不是“完美系统”，而是：

1. 编码层仍然是最主要瓶颈
2. 检索层次之
3. 生成层整体最稳定

这与之前你和我对 O-Mem 的判断是一致的，也与三层框架的设计初衷一致：**不是只看最后答对没有，而是要知道问题主要卡在哪一层**。

### 逐题样例说明

以 `conv-26:0` 为例：

1. `answer_online = 7 May 2023`
2. `answer_oracle = 7 May 2023`
3. `enc = EXIST`
4. `ret = HIT`
5. `gen = PASS`
6. 但 `ret` 仍被打了 `NOI`

这说明 O-Mem 并不是没有噪声，而是在噪声存在的情况下仍答对了。这是很有价值的分析信号。

## 4.5 O-Mem 当前主要问题

1. baseline 和 eval 中都能看到大量底层记忆更新日志，但没有结构化汇总
2. 代码侧没有把 warning、重试和异常倾向系统化写入最终 summary
3. 对 correctness judge 的时间表达宽松问题缺少额外约束

## 5. MemBox 结果复核

## 5.1 build 是否成功

成功。

证据如下：

1. `outputs/membox_conv26_build_manifest_0401.json` 存在
2. `count = 1`
3. artifact 中包含：
   - `sample_id`
   - `run_id`
   - `raw_data_path`
   - `output_root`
   - `config_snapshot`
4. `nohup_membox_conv26_build_0401.log` 中出现：
   - `Checkpoint saved`
   - `Trace saved`
   - `Trace linking completed`
   - `build_done`

说明当前 build artifact 机制已经成功落地。

## 5.2 baseline 是否成功

成功。

证据如下：

1. `outputs/membox_conv26_baseline_0401.json` 存在
2. `summary.count = 199`
3. `summary.final_correct = 136`
4. `summary.final_accuracy = 0.6834`
5. 日志中持续输出 `baseline_question_start` / `baseline_question_done`

这说明 MemBox baseline 这次不只是“能跑一点”，而是已经对 `conv-26` 的 199 题完整跑完。

## 5.3 baseline 结果如何

### 表面结果

从数字上看，这次结果明显优于之前旧结果：

1. 之前归档文档中的 MemBox baseline 准确率大约只有 0.09
2. 当前 0401 baseline 达到 0.6834

这说明：

1. 统一 CorrectnessJudge 的接入起了很大作用
2. build artifact 复用使运行链路稳定了很多
3. 当前系统不再被大量字符串匹配误伤

### 但这里有明显风险

从结果内容看，出现了大量如下模式：

1. `answer_online = "No evidence found."`
2. 但 `final_correct = true`

比如：

1. `conv-26:6`
2. `conv-26:7`
3. `conv-26:8`
4. 后续很多题目都存在类似情况

这说明当前 correctness judge 在某些题目上已经不仅是“语义宽松”，而是**可能把“拒答式回答”判成了 POS 正确**。这会显著抬高 MemBox baseline 的最终得分。

因此，MemBox baseline 的正确结论不是“系统已经很好”，而是：

1. 运行成功
2. LLM-as-Judge 统计口径真正生效
3. 但 judge 对 POS 题的拒答容忍度过高，导致结果可能虚高

## 5.4 eval 是否成功

成功。

这点非常关键，因为它和之前 0331 的静默失败不同。

证据如下：

1. `outputs/membox_conv26_eval_0401.json` 存在
2. `outputs/membox_conv26_eval_0401/` 目录存在
3. `summary.total = 10`
4. `summary.ok = 10`
5. `summary.errors = 0`
6. 日志逐题完整输出，最后打印 `{"ok": true, ...}`

说明：

1. MemBox eval 已经不再“卡死”
2. build/eval 分离改造是有效的
3. 逐题日志与逐题 JSON 落盘已经把可观测性问题大幅改善

## 5.5 eval 结果如何

### 总体统计

1. `final_accuracy = 0.7`
2. `enc.MISS = 10`
3. `ret.MISS = 10`
4. `gen.PASS = 8`
5. `gen.FAIL = 2`
6. `primary_cause` 几乎全部为 `encoding`

### 这是最值得注意的地方

这组结果说明：

1. 在前 10 道题里，MemBox 被编码层判定为 10/10 全部没有正确编码到目标记忆
2. 检索层也 10/10 全部 MISS
3. 但最终仍有 7/10 被判为 final correct

这并不是正常的“分层一致”表现，而是表明当前系统存在明显的**层间语义不一致**：

1. 编码层和检索层认为系统没有拿到正确证据
2. 生成层或 correctness judge 却认为最终答案正确

### 典型例子

`conv-26:0`：

1. `answer_online = "No evidence found."`
2. `answer_oracle = "7 May 2023"`
3. `enc = MISS`
4. `ret = MISS`
5. `gen = PASS`
6. `online.final_correct = true`

更严重的是，judge reason 写的是：

- “The generated answer indicates that Caroline attended the LGBTQ support group 'yesterday' relative to the date mentioned in the OracleContext (8 May 2023), which corresponds to 7 May 2023.”

但在线回答实际只是：

- `No evidence found.`

这说明当前判分路径很可能发生了**online answer 与 oracle context / oracle answer 混淆**，或者 prompt 设计允许 judge 从 oracle context 反推正确答案，从而把拒答也判成 correct。

## 5.6 MemBox 当前主要问题

### 问题一：CorrectnessJudge 对 POS 题拒答过宽

这是目前最明显的问题。

表现为：

1. 在线回答是“无证据”“未提及”“未找到”
2. 但在 POS 问题中仍被判为 final correct

影响：

1. baseline 得分虚高
2. eval 的 generation 正确率虚高
3. 归因结果与最终统计口径失真

### 问题二：judge 可能被 oracle context 污染

从 `conv-26:0` 的逐题 JSON 看，judge 似乎不是只依据 `answer_online` 与 `answer_gold` 判断，而是借助了 oracle context 中的信息进行反推。

影响：

1. online correctness 不再代表“系统真实在线回答对不对”
2. 而变成“如果结合 oracle context，这个回答能不能被解释成对”
3. 这会破坏 baseline 与 eval 的真实性

### 问题三：编码 / 检索 / 生成层之间的语义没有完全对齐

表现为：

1. `enc = MISS`
2. `ret = MISS`
3. `gen = PASS`
4. `final_correct = true`

这种现象在极少数题里可以存在，但在 10 题里大规模出现，说明框架仍有口径不一致问题。

### 问题四：baseline 缺少与 eval 同等级的逐题结构化产物

当前 baseline 只有聚合 JSON，没有：

1. `run_summary.json`
2. `question_index.json`
3. 每题单独 JSON

这会导致一旦 baseline 结果异常，很难像 eval 一样快速定位某一题到底发生了什么。

## 6. 当前代码最需要修改的方向

下面是我建议的下一步代码完善方向，按优先级排序。

### 6.1 第一优先级：收紧 CorrectnessJudge 的 POS 判定规则

需要做的事情：

1. 对 POS 问题增加“拒答式文本”显式惩罚规则
2. 当在线回答是：
   - `No evidence found`
   - `Not mentioned`
   - `No information available`
   - `No memory found`
   - 其他类似拒答模板
3. 即使 judge 认为它和 oracle context 有语义关联，也不应直接判为 POS 正确

建议修改位置：

- `src/memory_eval/eval_core/correctness_judge.py`
- `src/memory_eval/eval_core/prompts.py`
- `src/memory_eval/eval_core/llm_assist.py`

### 6.2 第二优先级：把 online correctness 与 oracle correctness 完全隔离

当前最大风险是 online judge 被 oracle context 污染。

建议原则：

1. `online_correctness` 判断时，不应使用会泄露 gold 事实的 oracle context
2. `oracle_correctness` 才能使用 oracle context
3. online judge 只能看：
   - question
   - gold answer
   - online answer
   - 必要时少量允许的任务定义

否则就会出现“系统明明没答出来，但 judge 帮它脑补成对”的问题。

### 6.3 第三优先级：让 baseline 也生成逐题 JSON

建议 baseline 对齐 eval 的落盘方式，至少增加：

1. `run_summary.json`
2. `question_index.json`
3. `<run_id>/sample_id/question_id.json`

这样好处是：

1. baseline 与 eval 结构统一
2. judge 误判时更容易定位
3. 论文实验分析也更方便直接引用逐题文件

建议修改位置：

- `scripts/run_real_memory_eval.py`

### 6.4 第四优先级：让 baseline 具备单题异常隔离

当前 `run_baseline()` 没有像 eval 那样对单题异常做 `try/except`。

这意味着：

1. 如果第 80 题出错
2. baseline 整轮可能直接中断
3. 并且没有标准化错误文件

建议：

1. baseline 也逐题捕获异常
2. 失败题单独记录
3. summary 中加入 errors 数

### 6.5 第五优先级：MemBox 适配器不要静默吞掉远程异常

当前 `membox_adapter.py` 中：

1. embedding 异常直接返回零向量
2. chat 异常直接返回空串或空 JSON

这虽然提升了“任务不崩”的概率，但副作用非常大：

1. 会把 API 故障伪装成模型弱回答
2. 会进一步污染 judge 和归因结果

建议：

1. 至少把异常类型和异常阶段写入日志或 result metadata
2. 不要完全静默
3. 在 strict 模式下应允许失败显式暴露

建议修改位置：

- `src/memory_eval/adapters/membox_adapter.py`

## 7. 对这次 0401 结果的最终判断

### O-Mem

可以认为：

1. 运行成功
2. baseline 与 eval 都基本可信
3. 三层归因也具有较强解释力
4. 当前主要是继续优化 correctness judge 边界和日志汇总

### MemBox

可以认为：

1. build 成功
2. baseline 成功
3. eval 成功
4. build/eval 分离方案已经跑通

但是：

1. 当前结果**不能直接认为已经完全可信**
2. 最大问题不是“能不能跑”，而是“judge 是否把 POS 的拒答误判成了正确”
3. 所以下一步重点不应再是修启动问题，而应转向**修判分口径与层间一致性**

## 8. 建议的下一步顺序

建议你后续按这个顺序推进代码修改：

1. 先修 CorrectnessJudge 的 POS 拒答误判问题
2. 再修 online correctness 与 oracle correctness 的上下文隔离
3. 再给 baseline 补齐逐题 JSON 与错误隔离
4. 最后再增强 MemBox 适配器的异常可观测性

## 9. 总结

0401 这一轮结果说明，你当前的评测框架已经从“是否能跑通”阶段进入到了“结果是否足够可信、是否足够严谨”的阶段。

最核心的好消息是：

1. O-Mem baseline / eval 跑通
2. MemBox build / baseline / eval 也都跑通
3. build artifact 复用和逐题日志机制已经生效

最核心的问题是：

1. MemBox 当前的 `final_correct` 很可能存在虚高
2. 原因不是框架崩溃，而是 correctness judge 与 oracle 信息边界还不够严格

因此，下一步的重点不再是“修能不能跑”，而是“修判分真实性与三层评测的一致性”。
