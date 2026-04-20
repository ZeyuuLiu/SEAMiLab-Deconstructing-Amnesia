# conv-26 上 O-Mem 与 MemBox 的评测结果分析

## 1. 实验对象与结果来源

本文分析基于 `conv-26` 的两组真实逐题评测产物：

- O-Mem：`outputs/omem_conv26_eval_0416_fix2`
- MemBox：`outputs/membox_conv26_eval_0416`

两组结果均为逐题 JSON 落盘结果，而非仅日志或中间缓存。为保证口径一致，我们进一步基于逐题结果自动生成了统一汇总：

- `outputs/conv26_eval_0416_report_v2/omem_eval_summary.json`
- `outputs/conv26_eval_0416_report_v2/membox_eval_summary.json`
- `outputs/conv26_eval_0416_report_v2/conv26_eval_report.md`

需要强调的是，本轮结果主要用于诊断评测链路与系统失效模式，而不适合直接作为论文最终主结果表。原因在于，两套系统的评测过程都受到 generation strict mode 契约问题的显著影响，导致大量样本在最终归因前即被标记为 `EVAL_ERROR`。

## 2. 总体结果

### 2.1 O-Mem

- 总题数：160
- `EVAL_ERROR`：103
- 错误率：64.38%
- 非错误样本中主要归因：
  - generation：38
  - retrieval：15
  - encoding：4

三层状态分布如下：

- Encoding：`EXIST=48`，`MISS=7`，`CORRUPT_AMBIG=1`，`CORRUPT_WRONG=1`
- Retrieval：`HIT=30`，`MISS=27`
- Generation：`FAIL=57`

高频缺陷包括：

- `GRF=29`
- `GF=24`
- `RF=20`
- `NOI=10`
- `LATE=8`

### 2.2 MemBox

- 总题数：97
- `EVAL_ERROR`：70
- 错误率：72.16%
- 非错误样本中主要归因：
  - generation：16
  - retrieval：11

三层状态分布如下：

- Encoding：`EXIST=27`
- Retrieval：`MISS=18`，`HIT=9`
- Generation：`FAIL=27`

高频缺陷包括：

- `RF=18`
- `GF=14`
- `GRF=13`
- `NOI=7`
- `LATE=5`

## 3. 关键观察

### 3.1 两套系统都不是“没有跑出来”，而是“跑出来了，但被评测器大量中断”

O-Mem 与 MemBox 都已经实际落下大量逐题结果。这说明问题不在于系统完全无法运行，而在于评测流程在后半段存在稳定性和契约一致性问题。

其中最主要的共同报错模式是：

`generation strict mode: POS failure requires llm_judgement.substate in {GF, GRF}, got 'NONE'`

这一点具有决定性意义。它说明：

- judge 已经完成了语义判断；
- judge 同时认为答案是 grounded 的；
- 但 generation strict mode 的后处理逻辑不接受 `substate='NONE'` 这一返回；
- 因而大量样本被整体视为运行时错误，而不是进入正常的 correctness / attribution 统计。

换言之，当前实验结果混合了“系统能力问题”和“评测链路问题”，二者尚未被有效解耦。

### 3.2 O-Mem 的真实失败模式主要集中在 generation 与 retrieval，而不是 encoding 全面崩溃

在 O-Mem 中，成功走完整个评测流程的样本并不支持“编码层普遍失败”这一结论。相反，`enc=EXIST` 是最主要状态，说明多数问题的核心事实在可观察记忆中仍可找到痕迹。

相比之下，O-Mem 更突出的真实失效模式是：

- generation 失败较多，表现为 `GF`、`GRF` 等生成层缺陷；
- retrieval 层存在较多 `RF` 与 `NOI`，说明系统在“记住了”之后，并不能稳定地把相关内容检索到正确位置；
- 极少数样本才真正体现为 encoding 层缺陷。

因此，对 O-Mem 而言，更合理的结论是：

> 当前问题并非“没有写入记忆”，而更像是“写入后无法稳定检索，或者 oracle / generation 判定链条未能正确承接可用证据”。

### 3.3 MemBox 当前最显著的问题仍然是评测链路阻塞，而不是记忆内容本身全 MISS

MemBox 的成功样本中，编码层状态全部为 `EXIST`，这与早先“MemBox 全部 MISS”这一怀疑并不一致。当前结果反而表明：

- 编码层至少在相当一部分样本中是可观察的；
- 真实的非异常失败主要集中在 retrieval 和 generation；
- 但更大规模的问题仍然是 generation strict mode 的运行时拦截。

因此，目前不能从这批结果中得出“MemBox 记不住内容”的结论。更准确的说法应该是：

> MemBox 当前结果首先反映了评测器的 strict-mode 契约不兼容，其次才是 retrieval / generation 层面的系统性不足。

### 3.4 绝对正确率在当前阶段没有可解释性

两套系统当前汇总中 `online_final_correct` 与 `oracle_final_correct` 都为 0，这一现象本身并不能被直接解释为系统完全失效。原因在于：

- 大量样本在最终 correctness 统计前已转为 `EVAL_ERROR`；
- 某些非异常样本中，`online answer` 从语义上明显合理，但由于 oracle 链路或 strict-mode 后处理被判为失败；
- 也存在网络异常和非 JSON LLM 输出等外部问题，进一步污染了最终统计。

因此，现阶段的 `final_accuracy=0` 更适合被视为“评测链路故障下的退化表象”，而不是系统真实回答能力的可信测量。

## 4. 代表性现象

### 4.1 O-Mem：online answer 看似合理，但仍被 generation 判错

例如问题 “When did Melanie paint a sunrise?” 中：

- `enc=EXIST`
- `ret=HIT`
- online answer 为 `8 May 2022`
- gold answer 为 `2022`

从语义上看，online answer 比 gold 更具体，并不应自然视为错误。但当前结果仍落入 generation failure。这说明当前 generation / oracle 判断链条存在明显的不稳定性。

### 4.2 MemBox：judge 已经判为语义正确，但 strict mode 仍将其视为错误

例如问题 “When did Caroline go to the LGBTQ support group?” 中，judge 实际已经给出 grounded 且语义匹配的结论，但由于 `substate='NONE'`，整题依旧被强行转为 `RuntimeError`。

这表明当前 strict-mode 的后处理设计过于刚性，正在覆盖掉 judge 自身已经给出的有效语义判断。

## 5. 对论文写作的建议表述

如果在论文中引用这批结果，建议采用如下口径：

1. 将其作为“评测框架稳定性审计”和“系统失效模式剖析”的案例，而不是最终主表结果。
2. 明确指出：当前结果揭示出统一评测框架中 generation strict mode 与 judge 输出契约之间的不一致，这一问题同时影响了 O-Mem 与 MemBox。
3. 在对系统能力的描述中，避免写成“系统完全无法记忆”；更合适的表述是：
   - O-Mem 主要暴露出 retrieval / generation 承接链条不稳定；
   - MemBox 当前更主要受评测流程的 strict-mode 运行时错误影响。
4. 在展示数字时，应同步给出 `EVAL_ERROR` 占比，否则读者会误把 `accuracy=0` 理解为系统本身的真实性能。

## 6. 当前可得的稳健结论

基于这两组真实逐题结果，可以得到以下较稳健的结论：

- O-Mem 与 MemBox 都已经完成了相当规模的逐题落盘，因此问题不是“没跑出来”。
- 两套系统都受到 generation strict mode 契约问题的显著影响，这是当前评测链路中的共同瓶颈。
- O-Mem 在非异常样本中显示出更多 retrieval / generation 层面的真实失败。
- MemBox 在非异常样本中并未表现出编码层普遍不可见，相反编码层多为 `EXIST`。
- 因此，在修复 strict-mode 契约之前，这批结果更适合作为调试与分析证据，而不适合作为最终论文主结论。

## 7. 后续工作

最优先的后续工作有三项：

1. 修复 generation strict mode 对 `llm_judgement.substate='NONE'` 的处理逻辑；
2. 将网络错误与 JSON 解析错误从系统能力评测中隔离出去；
3. 在排除 `EVAL_ERROR` 后，重新统计 O-Mem 与 MemBox 的真实 encoding / retrieval / generation 失败结构。

完成上述步骤后，再生成主实验表格，结果才具有论文层面的可解释性与可比较性。
