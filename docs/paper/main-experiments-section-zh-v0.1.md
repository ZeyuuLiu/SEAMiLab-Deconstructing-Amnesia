# 论文主实验部分写作稿（v0.1）

## 1. 文档定位

这份文档面向论文实验部分写作，目标不是解释代码实现细节，而是把当前项目里**已经跑完、可复述、可写进主实验结果表**的内容整理成一套可以直接转写到论文中的实验叙事。

当前最适合写入主实验的结果，是以下这组已经完成的 baseline / eval：

1. `O-Mem`
2. `MemBox`

对应结果文件为：

1. `outputs/o_mem_conv26_baseline_0407.json`
2. `outputs/o_mem_conv26_eval_0407.json`
3. `outputs/membox_conv26_baseline_0407.json`
4. `outputs/membox_conv26_eval_0407.json`

---

## 2. 当前哪些系统适合写进主实验

从当前 `system/` 目录的系统落地与实际运行状态看：

### 已经真正跑完、适合写进主实验

1. `system/O-Mem-StableEval`
2. `system/Membox_stableEval`

### 正在补充中，不建议写进主实验主表

1. `system/general-agentic-memory-main`
   - 原系统 baseline 正在运行
   - 评测框架适配器第一版已接入
   - 但尚未完成稳定的端到端复现实验

### 当前不适合写入主实验

1. `system/EverOS-main`
   - 环境已通，但模型/抽取链路仍不稳定
2. `system/timem-main`
   - Python 环境已通，但受 Docker 依赖阻塞
3. `system/MemOS-main`
   - baseline 第一阶段仍受本地 API 配置链路阻塞

因此，当前论文主实验最稳妥的写法应当是：

- **主结果表先聚焦 O-Mem 与 MemBox**
- `GAM` 等新增系统在本轮更适合作为 ongoing extension / future comparison，而不是本稿主表结果

---

## 3. 主实验想回答什么问题

当前这套实验设计实际上回答了三个问题：

### RQ1

在同一份 LoCoMo 数据上，不同记忆系统的最终问答表现差异有多大？

### RQ2

当最终准确率较低时，错误主要来自：

1. 编码层
2. 检索层
3. 生成层
4. 还是 correctness judge 本身

### RQ3

相比只报告最终 accuracy，三层探针 + 归因框架能否提供更细粒度、可解释的系统诊断结果？

---

## 4. 实验对象与设置

## 4.1 数据集

当前主实验使用的数据是：

- `data/locomo10.json`

本轮分析聚焦其中的：

- `sample_id = conv-26`

该样本共包含：

1. `199` 道问题
2. 其中 `154` 道为 `POS`
3. `45` 道为 `NEG`

这一点可从 eval summary 中直接看到。

---

## 4.2 评估模式

当前实验分为两类模式：

### baseline

baseline 的作用是评估原记忆系统的黑盒最终表现。

也就是说，baseline 只关心：

1. 系统如何写入记忆
2. 系统如何原生检索
3. 系统如何在线回答
4. 最终答案是否被 correctness judge 判对

需要强调的是：

- baseline 的在线回答过程本身与三层 probe 无关
- 但 baseline 的最终正确率统计仍然会受到统一 correctness judge 口径影响

因此，baseline 更像是：

- **黑盒最终效果**

### eval

eval 的作用是把最终对错拆成可解释的中间层：

1. 编码层
2. 检索层
3. 生成层
4. 归因层

因此，eval 更像是：

- **白盒诊断**

---

## 4.3 三层探针含义

当前三层框架对应的核心问题分别是：

### Encoding

- 关键信息到底有没有写进系统内部记忆中

### Retrieval

- 当前问题到来时，系统能不能把正确记忆检出来

### Generation

- 给定充分证据后，模型本身是否有能力回答正确

### Attribution

- 若最终结果不理想，最主要责任层在哪里

也就是说，三层框架不是为了替代最终 accuracy，而是为了让最终 accuracy 可解释。

---

## 4.4 correctness judge 设置

本轮 correctness judge 已统一收敛为：

1. online correctness 只看：
   - `question`
   - `gold answer`
   - `generated answer`
   - `retrieved_context`

2. oracle correctness 只看：
   - `question`
   - `gold answer`
   - `generated answer`
   - `oracle_context`

3. POS 问题中的显式拒答会被 hard veto
4. NEG 问题继续保留 refusal-aware 判分空间

judge prompt 采用更接近 TiMem 的宽松语义等价思路，而不是严格字面匹配。

---

## 5. 主结果

## 5.1 最终准确率

当前最适合放进论文主表的结果如下：

| System | Baseline Accuracy | Eval Accuracy | POS Eval Accuracy | NEG Eval Accuracy |
|---|---:|---:|---:|---:|
| O-Mem | 0.5578 | 0.5578 | 0.5649 | 0.5333 |
| MemBox | 0.1508 | 0.1307 | 0.1299 | 0.1333 |

从这张表可以直接得到两个结论：

1. `O-Mem` 明显优于 `MemBox`
2. `baseline` 与 `eval` 的最终 accuracy 非常接近，说明 `eval` 的主要价值不在于改变最终分数，而在于分层诊断

---

## 5.2 O-Mem 的分层结果

`O-Mem` 的 eval summary 显示：

### 编码层

1. `EXIST = 98`
2. `CORRUPT_WRONG = 20`
3. `MISS = 81`

### 检索层

1. `HIT = 82`
2. `MISS = 72`
3. `NOISE = 45`

### 生成层

1. `PASS = 117`
2. `FAIL = 82`

### 缺陷统计

1. `RF = 36`
2. `EM = 36`
3. `GH = 39`
4. `GRF = 29`
5. `EW = 20`
6. `LATE = 15`
7. `NOI = 10`

这说明 `O-Mem` 的问题不是某一层完全失效，而是：

- **编码、检索、生成三层都有损失，但整体链路仍然可对齐、可解释**

---

## 5.3 MemBox 的分层结果

`MemBox` 的 eval summary 显示：

### 编码层

1. `MISS = 199`

### 检索层

1. `MISS = 154`
2. `NOISE = 45`

### 生成层

1. `PASS = 130`
2. `FAIL = 69`

### 缺陷统计

1. `EM = 154`
2. `NIR = 45`
3. `GH = 37`
4. `GRF = 22`
5. `GF = 10`

这组结果的最重要信息是：

- **MemBox 在当前评测定义下的主要失败点位于编码层与检索层，而不是生成层**

尤其是：

- `enc = MISS (199/199)`

这不是“略差”，而是意味着：

- 当前 probe 基本无法在其 box 级记忆视图中恢复出目标事实

---

## 6. 如何写主实验结论

## 6.1 结论一：O-Mem 明显优于 MemBox

论文中可以直接写：

> 在相同的 LoCoMo 样本上，O-Mem 的 baseline 与 eval 最终准确率均为 55.78%，而 MemBox 的 baseline 与 eval 最终准确率分别仅为 15.08% 与 13.07%。这表明，O-Mem 的记忆表示、原生检索和在线回答链路与当前任务的对齐度明显高于 MemBox。

---

## 6.2 结论二：MemBox 的主要瓶颈不在生成层

论文中建议直接强调：

> 尽管 MemBox 的最终准确率较低，但其 generation probe 在 199 道题中仍有 130 道通过，说明在给定 oracle context 的条件下，其底层语言模型并非完全缺乏回答能力。更核心的问题出现在上游：编码层 199/199 全部判为 MISS，检索层在 POS 题上普遍 MISS、NEG 题上普遍表现为噪声检索，这说明其失败主要来自记忆表示与 query-facing evidence 的失配，而非单纯的生成失败。

---

## 6.3 结论三：O-Mem 的失败是多层累计损失

相比之下，`O-Mem` 更适合写成：

> O-Mem 并非在某一层完全失效，而是编码、检索与生成三层均存在不同程度的累计损失。编码层中既存在未写入的事实，也存在值错误的记忆；检索层中同时出现正确命中、漏检以及 NEG 噪声；生成层虽然整体更稳，但仍然存在一定比例的失败。因此，O-Mem 的低分更应被理解为多层误差叠加，而非单点故障。

---

## 6.4 结论四：三层探针提供了最终 accuracy 无法给出的解释力

这部分是当前论文最有价值的地方之一。

建议写成：

> 仅报告最终 accuracy 只能说明系统“答对了多少题”，却无法区分错误来自未编码、未检索、还是生成失败。三层探针框架的贡献在于，它将最终对错拆解为可定位的责任层：Encoding 判断系统是否形成记忆表示，Retrieval 判断系统是否能取出相关证据，Generation 判断在给定充分证据时模型是否仍会出错，Attribution 则进一步给出主责层。由此，系统的失败模式从单一的“答错”被扩展为可诊断、可比较的结构化误差画像。

---

## 7. 关于 judge 的写法建议

这一部分写论文时要特别谨慎。

不要写成：

- “当前准确率低主要是因为 LLM-as-Judge 太严格”

更建议写成：

> 当前最终准确率确实会受到 correctness LLM judge 的显著影响，但从实际样本看，这种影响并非单向“过严”，而是在 NEG、refusal 和语义近邻噪声场景中表现出明显不稳定性。换言之，低准确率不能单纯归因为 judge 本身，而应被解释为 judge 波动与上游链路真实失配共同作用的结果。

这段写法有两个好处：

1. 它承认了 judge 对结果统计的影响
2. 但不会把系统真实问题简单推给 judge

---

## 8. 论文中如何处理 baseline 与 eval 的关系

论文里建议把 baseline 与 eval 的职责明确分开：

### baseline

- 报告黑盒最终表现

### eval

- 报告细粒度诊断结论

建议可以直接写：

> baseline 用于衡量原系统在线回答的黑盒最终性能，而 eval 则进一步将该性能拆解为编码、检索与生成三个诊断层。因此，两者不是互相替代的关系，而是“最终表现”与“错误解释”的互补视角。

---

## 9. 当前主实验的局限性

为了论文写作严谨，建议明确写出以下局限：

### 局限一：当前主实验集中在 `conv-26`

也就是说，本轮结果更适合作为：

- 可解释的 case study + framework validation

而不是：

- 已经覆盖 LoCoMo 全量样本的最终大规模统计结论

### 局限二：judge 仍存在波动

虽然 judge 已做统一与补强，但在 NEG / refusal 场景下仍有不稳定性。

### 局限三：新增系统尚未完成主结果复现

目前 `GAM` 正在运行中，`EverOS`、`TiMem`、`MemOS` 仍未形成可并入主表的稳定结果。

因此现阶段论文主表应当只纳入：

1. `O-Mem`
2. `MemBox`

---

## 10. 可直接转写到论文中的主实验总结

下面这段可以直接作为论文实验部分结尾的初稿：

> We evaluate our framework on the LoCoMo benchmark using two representative memory systems, O-Mem and MemBox. In terms of end-task accuracy, O-Mem substantially outperforms MemBox, achieving 55.78% final accuracy on the selected sample, while MemBox remains below 15%. More importantly, our three-probe framework reveals that these low scores arise from fundamentally different failure modes. O-Mem exhibits cumulative degradation across encoding, retrieval, and generation, whereas MemBox fails primarily at the encoding and retrieval stages, despite retaining non-trivial generation capability under oracle context. These findings demonstrate that end-task accuracy alone is insufficient for diagnosing memory systems: two systems may both underperform, yet fail for very different reasons. By decomposing errors into encoding, retrieval, and generation layers, our framework turns opaque accuracy gaps into interpretable, actionable failure diagnoses.

如果你想写中文版本，可以改写为：

> 我们在 LoCoMo 数据上评估了两类代表性记忆系统：O-Mem 与 MemBox。最终结果显示，O-Mem 的准确率显著高于 MemBox，但更重要的是，三层探针框架揭示了二者完全不同的失败机制。O-Mem 的错误来自编码、检索与生成三层的累计损失，而 MemBox 的主要瓶颈则集中在编码与检索，其在 oracle context 下仍保留了一定生成能力。这说明，仅报告最终准确率无法揭示记忆系统真实的失效原因；相比之下，三层探针能够将黑盒分数分解为结构化、可解释的责任层，从而为系统比较与改进提供更直接的依据。

---

## 11. 当前对 GAM 的论文位置建议

由于 `GAM` 当前仍在运行中，建议在本轮论文草稿中把它放在：

1. future extension
2. ongoing reproduction
3. additional systems under integration

而不要先放进主实验结果表。

更稳妥的表述是：

> We are further extending the framework to additional memory systems, including GAM, EverOS, TiMem, and MemOS. At the current stage, these systems are under environment stabilization or reproduction, and thus are not included in the main quantitative table yet.

---

## 12. 一句话总结

如果把当前主实验压缩成一句话，那么最适合论文写作的版本是：

- **O-Mem 与 MemBox 在最终准确率上存在显著差异，而三层探针进一步表明，这种差异并不仅是“分数高低”的区别，更对应着两种本质不同的系统失效机制。**
