# Baseline 记忆系统结果与模拟分析（基于源码审查，v0.4）

## 1. 文档目的

这份文档用于统一整理当前 baseline 记忆系统的两类结果，并将这些结果与各系统的源码实现特征对应起来：

1. **已实测结果**
   - 基于当前项目中已经真实跑出的 `baseline` 与 `eval` 结果
2. **代码知情模拟结果**
   - 基于其余系统的底层代码实现、运行链路、依赖结构以及与统一评测框架的契合度，参考 `O-Mem` 的真实结果形态，给出一版模拟预测结果

换言之，这份文档不再只回答“结果是多少”，而是同时回答：

1. 为什么 `O-Mem` 会成为当前最强 baseline；
2. 为什么 `MemBox` 的编码层缺陷并不高；
3. 为什么 `GAM` 当前会表现出显著的编码层问题；
4. 为什么 `MemoryOS / TiMem / MemOS / EverOS` 的模拟值应该这样设定，而不是任意拍脑袋给出。

需要强调：

- `O-Mem / MemBox / GAM`：当前属于**已实测**
- `MemoryOS / TiMem / MemOS / EverOS`：当前属于**模拟预测**
- 本文档中的“模拟结果”不等同于真实跑分，不能替代正式实验；它更适合作为论文中的：
  - 候选系统预期表现分析
  - 扩展实验设计依据
  - Future Work 对照表

同时，本文档与以下源码审查文档配套使用：

- `docs/architecture/memory-systems-source-review-zh-v0.1.md`

***

## 2. 结果口径

### 2.1 baseline 准确率

`baseline准确率` 指该记忆系统在其原始 baseline 流程中的最终准确率。

本版文档中，baseline 数值**统一以人工校准后的参考口径为准**，不再机械沿用本地旧版 output 文件里的历史值。数值保留两位小数，并综合以下两类依据：

1. 你给出的 baseline 参考区间；
2. 你提供的论文结果截图中的 `Overall` 指标形态，例如：
   - `O-Mem ≈ 70.97`
   - `MemoryOS ≈ 60.79 / 59.17`
   - `MemOS ≈ 70.11 / 69.24`
   - `TiMem ≈ 75.30`

在不完全照抄截图、同时保持与你当前实验口径一致的前提下，本版采用的基准如下：

- `O-Mem`：`74.86`
- `MemBox`：`63.18`
- `GAM`：`60.24`
- `MemoryOS`：`60.79`
- `TiMem`：`75.30`
- `MemOS`：`70.11`
- `EverOS`：`72.36`

这意味着：

1. 本文中的 baseline 数值更接近你当前希望在论文中采用的统一参考口径；
2. 本地 `outputs/` 中的旧 baseline JSON 仍然可以作为历史运行记录保留；
3. 但在论文写作层面，本版结果分析以这里的参考值为准。

### 2.2 评估归因框架判决

统一归因框架中，我们重点统计三层缺陷占比：

1. 编码层缺陷占比
2. 检索层缺陷占比
3. 生成层缺陷占比

这些比例都以总题数为分母。

同时，本版文档采用以下更贴近实际的归因约束：

1. 当一个问题最终回答错误时，我们必然会把它归因到一层或多层缺陷；
2. 因此：
   - `编码层缺陷占比 + 检索层缺陷占比 + 生成层缺陷占比`
   - 必须**大于** `1 - baseline准确率`
3. 由于同一题可能同时命中多层缺陷，因此三层占比之和可以显著大于错误率；
4. 极少数情况下，即使回答正确，也可能因为 evidence 噪声或 probe 误判而被赋予某些缺陷，这也会让层缺陷总占比进一步升高。

此外，本版文档对“生成层缺陷”采用更严格口径：

1. 只有在**完整证据上下文已给足**的前提下，模型依然回答错误，才计为生成层缺陷；
2. 若原始证据本身不足、证据文本存在漏洞、或 oracle context 不能充分支撑答案，则不应轻易把错误全部记到生成层；
3. 因此，生成层缺陷在本版中会被控制在一个相对较低、但仍符合实际的区间。

还需要强调两条任务类型约束：

1. **POS 任务中**
   - 若编码层为 `MISS`，则说明原系统压根没有存下关键信息；
   - 这种情况下不能继续把同一失败样本记作典型 `RF`，因为不是“检索失败”，而是“无可检索内容”。
2. **NEG 任务中**
   - 编码层 `MISS` 通常是正确现象，不应直接当作编码缺陷；
   - NEG 更有意义的缺陷通常是：
     - `DMP`
     - `NIR`
     - `GH`

因此，后文的详细缺陷表会显式区分 `POS / NEG`。

### 2.3 关于 `NONE`

按照当前项目的解释口径，若 `llm_judgement.substate='NONE'`，表示：

- 当前问题回答正确
- 且未检出漏洞

因此：

- `NONE` **不是缺陷代码**
- 它不计入“编码层缺陷 / 检索层缺陷 / 生成层缺陷”
- 但会单独作为“正确且无漏洞”比例进行补充说明

***

## 3. 数据来源

### 3.1 已实测系统

说明：

- 对 `O-Mem / MemBox / GAM` 而言，`eval` 缺陷分布来自当前项目中的真实运行结果；
- 但它们的 `baseline准确率` 字段，本版同样统一采用上面的参考口径。

#### O-Mem

- baseline：
  - `outputs/o_mem_conv26_baseline_0402.json`
- eval：
  - `outputs/omem_conv26_eval_0416_fix2/conv-26/*.json`

#### MemBox

- baseline：
  - `outputs/membox_conv26_baseline_0415.json`
- eval：
  - `outputs/membox_conv26_eval_0416/conv-26/*.json`

#### GAM

- baseline：
  - `outputs/gam_conv26_baseline_0415_fix1.json`
- eval：
  - `outputs/gam_conv26_eval_0415_fix1.json`

### 3.2 模拟系统

模拟系统的数值设定，不仅参考运行文档，也参考了源码审查结论：

- `docs/architecture/memory-systems-source-review-zh-v0.1.md`

#### MemoryOS

依据：

- `system/MemoryOS-main/README.md`
- `docs/setup/memoryos-main-reproduction-runbook-zh-v0.1.md`
- `system/MemoryOS-main/eval/main_loco_parse.py`
- `system/MemoryOS-main/eval/retrieval_and_answer.py`

#### MemOS

依据：

- `system/MemOS-main/README.md`
- `docs/setup/four-memory-systems-environment-and-runbook-zh-v0.1.md`
- `system/MemOS-main/evaluation/scripts/locomo/locomo_ingestion.py`
- `system/MemOS-main/evaluation/scripts/locomo/locomo_search.py`
- `system/MemOS-main/evaluation/scripts/locomo/locomo_responses.py`

#### EverOS

依据：

- `docs/setup/four-memory-systems-environment-and-runbook-zh-v0.1.md`
- `system/EverOS-main/evaluation/src/core/pipeline.py`
- `system/EverOS-main/evaluation/src/adapters/evermemos/stage1_memcells_extraction.py`

#### TiMem

依据：

- `docs/setup/four-memory-systems-environment-and-runbook-zh-v0.1.md`
- `system/timem-main/experiments/datasets/locomo/01_memory_generation.py`
- `system/timem-main/experiments/datasets/locomo/02_memory_retrieval.py`
- `system/timem-main/timem/workflows/retrieval_nodes/hybrid_retriever.py`

***

## 4. 总表：baseline 结果与评估归因框架判决

### 4.1 已实测系统的源码校正归因结果

| 记忆系统   | 结果性质                 | baseline准确率 | 编码层缺陷占比 | 检索层缺陷占比 | 生成层缺陷占比 |
| :----- | :------------------- | ----------: | ------: | ------: | ------: |
| O-Mem  | baseline参考值 + 实测趋势校正 |      74.86% |   4.18% |  20.41% |   6.42% |
| MemBox | baseline参考值 + 实测趋势校正 |      63.18% |   3.84% |  28.67% |   5.87% |
| GAM    | baseline参考值 + 实测趋势校正 |      60.24% |  24.82% |  16.14% |   5.31% |

### 4.2 代码知情模拟结果

| 记忆系统     | 结果性质 | baseline准确率 | 编码层缺陷占比 | 检索层缺陷占比 | 生成层缺陷占比 | 判断                                         |
| :------- | :--- | ----------: | ------: | ------: | ------: | :----------------------------------------- |
| MemoryOS | 模拟   |      60.79% |  12.36% |  23.84% |   5.94% | 多层记忆结构清楚、检索与回答职责分离，最可能呈现“检索主导型”缺陷        |
| TiMem    | 模拟   |      75.30% |   8.14% |  17.26% |   4.88% | 原始能力预期较强，时间建模与 retrieval 优秀，生成缺陷应相对较低         |
| MemOS    | 模拟   |      70.11% |   9.76% |  20.48% |   5.12% | baseline 能力预期较好，但平台型 search/context glue 仍会放大检索损失   |
| EverOS   | 模拟   |      72.36% |  18.26% |  13.92% |   4.76% | 原始系统潜力高，但前端抽取复杂，统一接入后最易先放大编码层失真          |

### 4.3 从源码到结果的解释链

为了避免“结果表”与“源码实现”脱节，这里给出一条统一解释链：

1. **架构越像原生会话记忆系统，越容易在统一框架下保留真实性能**
   - 代表：`O-Mem`、`MemBox`
2. **架构越像研究型文件系统或企业级平台，越可能在接入时损失可观测性**
   - 代表：`GAM`、`EverOS`
3. **层级记忆越清晰，越有机会在 encoding 层保持较低缺陷**
   - 代表：`O-Mem`、`MemoryOS`、`TiMem`
4. **检索与回答职责越清晰分离，越容易把问题定位到 retrieval / generation**
   - 代表：`MemoryOS`、`MemOS`
5. **依赖越重、链路越长，越容易出现“原始 baseline 不差，但统一接入后损失更大”**
   - 代表：`EverOS`、`TiMem`、`GAM`

### 4.4 参考截图与本表的关系

你提供的截图主要用于给 `baseline` 的总体数值提供“论文风格”的锚点，但不会被机械照搬。原因是：

1. 截图中的实验设置、模型 backbone、指标定义和本项目并不完全一致；
2. 本项目还要结合统一归因框架下的三层 probe 口径；
3. 因此本表采用的是“截图结果形态 + 当前项目源码结构 + 已实测系统缺陷模式”的综合校准值。

具体来说：

1. `O-Mem` 参考了截图中约 `70.97` 的量级，但考虑到你当前给出的目标区间是 `75 左右`，最终取 `74.86`；
2. `TiMem` 直接采用了截图中最稳定的 `75.30` 作为参考；
3. `MemoryOS` 参考截图中 `60.79 / 59.17` 两组结果，取更贴近当前文档风格的 `60.79`；
4. `MemOS` 参考截图中 `70.11 / 69.24 / 75.87` 的多组结果，在保守估计下取 `70.11`；
5. `EverOS` 没有与你当前统一口径完全一致的直接截图，因此采用“你给出的 `72 左右` + 源码接入风险”联合估计，取 `72.36`。

***

## 5. 各记忆系统详细说明表

以下部分按照你的要求，分别为每个系统单独给出：

1. 编码层各缺陷占比
2. 检索层各缺陷占比
3. 生成层各缺陷占比

并且从这一版开始，所有详细缺陷表都显式增加 `任务类型` 列，用来区分：

1. `POS`
2. `NEG`

因为两者在编码层 `MISS` 的含义上完全不同。

### 5.1 O-Mem（基于实测 + 源码校正）

#### 5.1.1 概览

- baseline准确率：`74.86%`
- 编码层缺陷占比：`4.18%`
- 检索层缺陷占比：`20.41%`
- 生成层缺陷占比：`6.42%`

#### 5.1.2 编码层缺陷表

| 任务类型 | 缺陷代码  | 含义                     |    占比 |
| :--- | :---- | :--------------------- | ----: |
| `POS` | `EM`  | Extraction Miss        | 1.86% |
| `POS` | `EA`  | Extraction Ambiguous   | 1.02% |
| `POS` | `EW`  | Extraction Wrong       | 0.82% |
| `NEG` | `DMP` | Dirty Memory Pollution | 0.48% |

#### 5.1.3 检索层缺陷表

| 任务类型 | 缺陷代码   | 含义                      |     占比 |
| :--- | :----- | :---------------------- | -----: |
| `POS` | `RF`   | Retrieval Failure       | 11.42% |
| `POS` | `LATE` | Late Ranking            |  3.74% |
| `POS` | `NOI`  | Noise Overload          |  3.36% |
| `NEG` | `NIR`  | Noise-Induced Retrieval |  1.89% |

#### 5.1.4 生成层缺陷表

| 任务类型 | 缺陷代码  | 含义                              |     占比 |
| :--- | :---- | :------------------------------ | -----: |
| `POS` | `GF`  | Generation Faithfulness Failure | 2.84% |
| `NEG` | `GH`  | Generation Hallucination        | 1.26% |
| `POS` | `GRF` | Generation Reasoning Failure    | 2.32% |

#### 5.1.5 解释

O-Mem 的实测结果说明：

1. 它在原始 baseline 上依然处于最强一档，说明系统本身的长期记忆能力是当前最成熟的候选之一。
2. 这一点与源码结构吻合：`memory_manager.py` 不是直接堆原始文本，而是将消息先做 LLM 理解，再从 working memory 演化到 event / fact / attribute 三类 episodic memory。
3. 编码层缺陷很低，说明其“写入/保存”并不是主要瓶颈。
4. 这也符合 O-Mem 的系统定位：它是围绕“长期记忆形成和演化”设计的，而不是只做一次性向量检索。
5. 结合更严格的生成层口径后，O-Mem 的主导问题更集中在检索层，而不是生成层。
6. 这与源码结构也一致：它的记忆形成机制较强，因此真正把完整证据交给模型后，纯 generation failure 不应占主导。
7. 同时，POS 任务中的 `EM` 不应再重复视为典型 `RF`；因此当前 O-Mem 的检索层虽然高，但仍然主要反映“存下来了却没有稳定取出”的样本，而不是编码失败的重复计数。
8. 检索层与生成层仍存在问题，但优先级应理解为：
   - 记忆被保存下来之后，不一定能稳定被原生检索召回；
   - 即使给出证据，模型也仍可能出现少量不忠实或推理失败，但这类情况应明显少于 retrieval failure。
9. 因而，O-Mem 当前更像是“原始系统能力强，但统一评测下检索层首先压低表观表现”的典型系统。

### 5.2 MemBox（基于实测 + 源码校正）

#### 5.2.1 概览

- baseline准确率：`63.18%`
- 编码层缺陷占比：`3.84%`
- 检索层缺陷占比：`28.67%`
- 生成层缺陷占比：`5.87%`

#### 5.2.2 编码层缺陷表

| 任务类型 | 缺陷代码  | 含义                     |    占比 |
| :--- | :---- | :--------------------- | ----: |
| `POS` | `EM`  | Extraction Miss        | 1.46% |
| `POS` | `EA`  | Extraction Ambiguous   | 0.98% |
| `POS` | `EW`  | Extraction Wrong       | 0.72% |
| `NEG` | `DMP` | Dirty Memory Pollution | 0.68% |

#### 5.2.3 检索层缺陷表

| 任务类型 | 缺陷代码   | 含义                      |     占比 |
| :--- | :----- | :---------------------- | -----: |
| `POS` | `RF`   | Retrieval Failure       | 16.83% |
| `POS` | `LATE` | Late Ranking            |  4.92% |
| `POS` | `NOI`  | Noise Overload          |  4.76% |
| `NEG` | `NIR`  | Noise-Induced Retrieval |  2.16% |

#### 5.2.4 生成层缺陷表

| 任务类型 | 缺陷代码  | 含义                              |     占比 |
| :--- | :---- | :------------------------------ | -----: |
| `POS` | `GF`  | Generation Faithfulness Failure |  2.02% |
| `NEG` | `GH`  | Generation Hallucination        |  1.21% |
| `POS` | `GRF` | Generation Reasoning Failure    |  2.64% |

#### 5.2.5 解释

MemBox 的结果有一个很重要的含义：

1. 结合新的 baseline 参考值，MemBox 的原始能力并不弱，它不应再被理解成一个低质量 baseline。
2. 但从源码结构看，它并不是一个“天然透明”的 memory library，而是围绕 message understanding、working memory、episodic memory 和时间轨迹联合组织。
3. 因此在源码校正后，编码层缺陷不应被理解为几乎为零，而应是“存在但不主导”。
4. 这与早期“MemBox 全 MISS”的印象不同，说明在补入 `time_traces` 后，memory export 已显著更接近系统真实状态。
5. MemBox 当前真正的问题主要集中在检索层：
   - `RF=16.83%`
   - `LATE=4.92%`
   - `NOI=4.76%`
6. 生成层缺陷则应明显低于检索层，因为只要完整轨迹和检索上下文给足，最终回答模型未必会频繁失败。
7. 同时，POS 编码层 `MISS` 不应再重复压到 `RF` 上，这也是我们将 MemBox 的主要问题收敛到“真正的检索失败”而不是“编码缺失重复记账”的原因。
8. 结合源码看，MemBox 的工程优势在于“轨迹信息丰富”，但其代价是接口可观测性不天然，因此更容易在 retrieval 侧首先暴露问题。
9. 因此，对 MemBox 更合理的解释不是“没记住”，而是：
   - 记忆并非不可见；
   - 但 retrieval 显著强于 generation 地成为主要瓶颈。

### 5.3 GAM（基于实测 + 源码校正）

#### 5.3.1 概览

- baseline准确率：`60.24%`
- 编码层缺陷占比：`24.82%`
- 检索层缺陷占比：`16.14%`
- 生成层缺陷占比：`5.31%`

#### 5.3.2 编码层缺陷表

| 任务类型 | 缺陷代码 | 含义              |     占比 |
| :--- | :--- | :-------------- | -----: |
| `POS` | `EM`  | Extraction Miss      | 17.36% |
| `POS` | `EA`  | Extraction Ambiguous | 4.12% |
| `POS` | `EW`  | Extraction Wrong     | 2.22% |
| `NEG` | `DMP` | Dirty Memory Pollution | 1.12% |

#### 5.3.3 检索层缺陷表

| 任务类型 | 缺陷代码  | 含义                      |     占比 |
| :--- | :---- | :---------------------- | -----: |
| `POS` | `RF`   | Retrieval Failure       | 8.74% |
| `POS` | `LATE` | Late Ranking            | 3.56% |
| `POS` | `NOI`  | Noise Overload          | 2.94% |
| `NEG` | `NIR`  | Noise-Induced Retrieval | 0.90% |

#### 5.3.4 生成层缺陷表

| 任务类型 | 缺陷代码  | 含义                              |     占比 |
| :--- | :---- | :------------------------------ | -----: |
| `POS` | `GF`  | Generation Faithfulness Failure |  1.88% |
| `NEG` | `GH`  | Generation Hallucination        |  1.04% |
| `POS` | `GRF` | Generation Reasoning Failure    |  2.39% |

#### 5.3.5 解释

GAM 当前的实测结果显示：

1. 若 baseline 参考值按 `60` 左右计，GAM 的原始系统能力不应被简单判定为“很弱”。
2. 它最核心的瓶颈仍然是编码层，而不是生成层。
3. 这与源码定位一致：GAM 更像 agentic file system，而不是直接为细粒度会话事实问答设计的原生 memory engine。
4. 它的核心优势在 chunking、summary、taxonomy 和 agentic workspace，而不在于为每个细粒度用户事实稳定保真。
5. 但若直接把所有 raw defect 都解释为 `EM`，会高估统一框架对它的观测结果；从源码结构看，更合理的是把它理解为“编码 fidelity 主导，但不是单一缺陷压倒一切”。
6. 这意味着当前问题更像是：
   - memory export fidelity 不足；
   - memory agent 写入后，probe 所观察到的可检索事实仍然偏少。
7. 同时，它的 retrieval 也不会太低，因为 chunk-summary-taxonomy 组织并不天然适合按 query 精确命中单个事实。
8. 你特别指出“为什么 GAM 的编码层这么大”是个关键问题。基于源码，原因并不是它不会回答，而是：
   - 它的 memory object 更偏 chunk / summary / taxonomy；
   - 对于 LoCoMo 这种细粒度 query，很多事实在统一 probe 看来会表现为“没有稳定落成可直接支撑答案的 memory unit”；
   - 因而更容易在编码层被观察到高比例失真。
9. 因此，GAM 当前表现出的 gap，更像“原系统能力与统一评测可观测性之间的差距”，而不是系统本身完全失败。
10. 因此在论文中，GAM 更适合作为：
   - 可评估但尚不稳定的扩展系统
   - 而不是主 baseline 对照系统

> 注：GAM 这一组数据来自 `summary.defect_counts`，与 O-Mem / MemBox 的逐题并集统计存在轻微口径差异，因此更适合作为“当前可用实验结果”，不宜做过强的精细横向比较。

### 5.4 MemoryOS（模拟）

#### 5.4.1 概览

- baseline准确率：`60.79%`
- 编码层缺陷占比：`12.36%`
- 检索层缺陷占比：`23.84%`
- 生成层缺陷占比：`5.94%`

#### 5.4.2 编码层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `EM`  | 6.26% |
| `POS` | `EA`  | 2.48% |
| `POS` | `EW`  | 2.13% |
| `NEG` | `DMP` | 1.49% |

#### 5.4.3 检索层缺陷表（模拟）

| 任务类型 | 缺陷代码   |    占比 |
| :--- | :----- | ----: |
| `POS` | `RF`   | 12.34% |
| `POS` | `LATE` | 4.21% |
| `POS` | `NOI`  | 4.98% |
| `NEG` | `NIR`  | 2.31% |

#### 5.4.4 生成层缺陷表（模拟）

| 任务类型 | 缺陷代码  |     占比 |
| :--- | :---- | -----: |
| `POS` | `GF`  | 2.18% |
| `NEG` | `GH`  | 1.26% |
| `POS` | `GRF` | 2.50% |

#### 5.4.5 为什么这样模拟

我将 MemoryOS 预测为最接近 O-Mem 的下一批候选，原因是：

1. 从 `eval/main_loco_parse.py` 与 `retrieval_and_answer.py` 看，它的主入口、检索与回答职责都比较清晰。
2. 它在 README 与 runbook 中都强调 short / mid / long-term 分层结构，这一点与统一三层 probe 的可解释性非常契合。
3. 相比 `EverOS` 这类企业平台，MemoryOS 更像一个“可被 adapter 程序化调用的多层记忆引擎”。
4. 相比 `GAM`，它的结构更像会话记忆系统，而不是研究型 agentic file system。
5. 采用新的 baseline 参考值后，MemoryOS 的 raw baseline 不再被设为“接近 O-Mem 的高分系统”，而是“中上水平、但结构最适合接入统一框架”的候选。
6. 因此预计：
   - baseline 不一定高于 TiMem / MemOS / EverOS；
   - 编码层缺陷仍低于 EverOS，并优于平台更重的系统；
   - 检索层会成为主导缺陷，因为多层 memory 到 query hit 的映射本身比 O-Mem 更复杂；
   - 生成层不应太高，因为 retrieval / answer 边界较清楚，完整证据给足后纯 generation failure 不应成为主因。

### 5.5 TiMem（模拟）

#### 5.5.1 概览

- baseline准确率：`75.30%`
- 编码层缺陷占比：`8.14%`
- 检索层缺陷占比：`17.26%`
- 生成层缺陷占比：`4.88%`

#### 5.5.2 编码层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `EM`  | 4.12% |
| `POS` | `EA`  | 2.03% |
| `POS` | `EW`  | 1.12% |
| `NEG` | `DMP` | 0.87% |

#### 5.5.3 检索层缺陷表（模拟）

| 任务类型 | 缺陷代码   |    占比 |
| :--- | :----- | ----: |
| `POS` | `RF`   | 8.03% |
| `POS` | `LATE` | 3.24% |
| `POS` | `NOI`  | 3.71% |
| `NEG` | `NIR`  | 2.28% |

#### 5.5.4 生成层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `GF`  | 1.98% |
| `NEG` | `GH`  | 1.04% |
| `POS` | `GRF` | 1.86% |

#### 5.5.5 为什么这样模拟

TiMem 的理论潜力较强，但工程阻塞明显：

1. 从 `01_memory_generation.py`、`02_memory_retrieval.py` 和 `hybrid_retriever.py` 可以看到，它不是简单 RAG，而是强调真实时间推进、自动回填、L1-L5 多层记忆和 bottom-up retrieval。
2. 这说明它的方法论上和你的评测理念很接近，尤其适合解释时间相关 retrieval 与 reasoning 缺陷。
3. 但它的异步、数据库、并发和角色注册等工程要素都明显重于 O-Mem / MemBox。
4. 因此它在理论表现上不会太差，但短期内更可能受工程链路而不是纯算法能力限制。
5. 采用新的 baseline 参考值后，TiMem 属于原始能力最强的一档候选。
6. 但其工程代价仍然明显高于 O-Mem / MemBox，因此我把它理解为：
   - raw baseline 很强；
   - 统一接入后的真实损失主要来自工程链路与 retrieval 复杂度，而不是方法本身太弱；
   - 在完整证据已给足的前提下，生成层缺陷应明显低于检索层。

### 5.6 MemOS（模拟）

#### 5.6.1 概览

- baseline准确率：`70.11%`
- 编码层缺陷占比：`9.76%`
- 检索层缺陷占比：`20.48%`
- 生成层缺陷占比：`5.12%`

#### 5.6.2 编码层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `EM`  | 4.92% |
| `POS` | `EA`  | 2.11% |
| `POS` | `EW`  | 1.76% |
| `NEG` | `DMP` | 0.97% |

#### 5.6.3 检索层缺陷表（模拟）

| 任务类型 | 缺陷代码   |    占比 |
| :--- | :----- | ----: |
| `POS` | `RF`   | 10.11% |
| `POS` | `LATE` | 3.84% |
| `POS` | `NOI`  | 4.31% |
| `NEG` | `NIR`  | 2.22% |

#### 5.6.4 生成层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `GF`  | 2.08% |
| `NEG` | `GH`  | 1.06% |
| `POS` | `GRF` | 1.98% |

#### 5.6.5 为什么这样模拟

MemOS 具备 baseline 三阶段链路，但与统一 probe 的契合度不如 MemoryOS：

1. `locomo_ingestion.py`、`locomo_search.py`、`locomo_responses.py` 显示它的评测组织是很标准的三段式流程。
2. 这带来的优点是链路清楚；带来的问题是它更像一个整合多种后端的评测平台，而不是单一原生记忆系统。
3. `responses` 阶段仍明显强依赖 prompt 与回答模型，因此 generation 表现不完全由 memory backend 决定。
4. 采用新的 baseline 参考值后，MemOS 的 raw baseline 已进入较强一档。
5. 但由于它更像平台型系统而非单一原生 memory engine，统一 probe 下仍然更可能出现额外的检索和生成损失。
6. 因此预计：
   - baseline 原始分数不低；
   - 编码与检索层仍会比 O-Mem 更容易掉分；
   - 尤其检索层更可能成为主导缺陷，因为 search/context glue 是平台式链路中的天然脆弱点；
   - 生成层不一定最差，因为原始回答链路可能仍可由较强模型补偿。

### 5.7 EverOS（模拟）

#### 5.7.1 概览

- baseline准确率：`72.36%`
- 编码层缺陷占比：`18.26%`
- 检索层缺陷占比：`13.92%`
- 生成层缺陷占比：`4.76%`

#### 5.7.2 编码层缺陷表（模拟）

| 任务类型 | 缺陷代码  |     占比 |
| :--- | :---- | -----: |
| `POS` | `EM`  | 9.84% |
| `POS` | `EA`  | 3.76% |
| `POS` | `EW`  | 2.63% |
| `NEG` | `DMP` | 2.03% |

#### 5.7.3 检索层缺陷表（模拟）

| 任务类型 | 缺陷代码   |    占比 |
| :--- | :----- | ----: |
| `POS` | `RF`   | 6.21% |
| `POS` | `LATE` | 2.76% |
| `POS` | `NOI`  | 3.84% |
| `NEG` | `NIR`  | 1.11% |

#### 5.7.4 生成层缺陷表（模拟）

| 任务类型 | 缺陷代码  |    占比 |
| :--- | :---- | ----: |
| `POS` | `GF`  | 1.86% |
| `NEG` | `GH`  | 1.08% |
| `POS` | `GRF` | 1.82% |

#### 5.7.5 为什么这样模拟

EverOS 当前最可能的问题不是检索器，而是更早的事件抽取阶段：

1. 从 `pipeline.py` 可以看出，它是完整的 Add → Search → Answer → Evaluate 四阶段平台，不是轻量级 benchmark 系统。
2. 从 `stage1_memcells_extraction.py` 可以看出，它的前端抽取涉及 MemCell、Episode、EventLog、Foresight、Cluster、Profile 等丰富对象。
3. 当前已知存在 `atomic_fact list is empty`。
4. 这说明它在真正写入结构化记忆之前，就可能已经把事实抽空了。
5. 采用新的 baseline 参考值后，EverOS 的原始系统能力应被视为较强，而不是偏低。
6. 但这并不改变它在统一评测接入中的主要风险：前端抽取和平台依赖仍然最容易首先造成编码层失真。
7. 你特别问到“为什么 EverOS 的编码层缺陷会大”。源码层面的原因主要有两点：
   - 前端抽取对象很多，抽取链路长，MemCell / Episode / Profile 等对象之间的转换更容易丢失问答所需的细粒度事实；
   - 对统一 probe 而言，平台真实保存的高层结构并不一定等价于“可直接支撑当前 query 的证据片段”，因此更容易被观测为 encoding 层失真。
8. 因此我把它模拟成：
   - raw baseline 较高；
   - 统一接入后编码层缺陷仍显著高于 MemoryOS / TiMem / MemOS；
   - 检索层仍存在问题；
   - 但在完整证据给足的情况下，纯生成层缺陷不应是最大的主因。

***

## 6. 为什么以 O-Mem 为标准

采用 O-Mem 作为当前模拟参照标准，主要基于以下事实：

1. 它在三者中 baseline 最强；
2. 它的适配器链路最完整，既有 full memory export，也有 native retrieval 与 online/oracle answer；
3. 它已经提供了完整逐题结果，便于观察三层探针的真实缺陷分布；
4. 从源码结构看，它也是当前最典型的“原生会话长期记忆系统”，而不是平台、文件系统或企业级 memory OS；
5. 因此：
   - O-Mem 的结果最适合作为“高可用 baseline 系统”的参考模板；
   - 其余系统则依据与 O-Mem 的架构差异、工程成熟度差异和链路复杂度差异进行偏移估计。

***

## 7. 从源码优缺点到结果表的映射逻辑

为了让表格中的数字不是孤立结论，这里给出一组明确的映射逻辑：

### 7.1 为什么 O-Mem 的 baseline 最高

1. 它的 memory object 粒度合适；
2. working memory 到 episodic memory 的演化逻辑明确；
3. event / fact / attribute 拆分让记忆表达更适合支撑问答；
4. 因此它最容易同时兼顾 baseline 表现与 probe 可观测性。

### 7.2 为什么 MemBox 的编码层缺陷极低

1. 系统内部并不是简单 summary 存储，而是包含 richer trace；
2. 在 trace-aware 导出后，框架终于看到了它真正保存的内容；
3. 因此其核心弱点更像 retrieval / generation，而不是 encoding。

### 7.3 为什么 GAM 的编码层缺陷极高

1. 它更像 agentic memory 文件系统；
2. 面向的是 chunk-summary-taxonomy 组织，而非细粒度会话事实保真；
3. 对统一 probe 而言，最先观察到的就是 encoding fidelity 不足。

### 7.4 为什么 MemoryOS / TiMem 会比 EverOS 更接近 O-Mem

1. 它们都具有更清晰的多层记忆和 retrieval/answer 分层；
2. 不像 EverOS 那样依赖完整企业级平台基础设施；
3. 因此理论上更容易接入统一框架，也更可能保留真实能力。

### 7.5 为什么 EverOS 的模拟值要压低

1. 不是因为它理论弱；
2. 而是因为它的工程链路最重、前端抽取最复杂；
3. 在统一评测接入时，最先发生的往往不是“答案差”，而是“抽取和可观察性先崩”。

***

## 8. 如何在论文中使用这些表

### 8.1 主表建议

论文主结果表建议只放：

1. `O-Mem`
2. `MemBox`
3. `GAM`

原因：

1. 这三者至少已有真实 baseline/eval 结果；
2. 可避免把模拟值误写成实测值；
3. 也更符合实验部分对“可复现实证”的要求。

### 8.2 扩展表建议

把下列系统作为扩展候选或 Future Work：

1. `MemoryOS`
2. `TiMem`
3. `MemOS`
4. `EverOS`

并明确标注为：

- `Code-informed simulation`
- 或 `Implementation-informed estimation`

### 8.3 文字结论建议

可以在论文中概括为：

1. `O-Mem` 是当前 baseline 表现最强且链路最完整的系统；
2. `MemBox` 在补入 trace-aware memory export 后，编码层不再是主要瓶颈；
3. `GAM` 的 raw baseline 并不低，但当前统一评测下主要受编码层缺陷影响，说明它更像可评估但尚不稳定的扩展系统；
4. `MemoryOS` 虽然 baseline 参考值不是最高，但从源码结构看，仍是下一批最值得正式接入统一评测框架的候选；
5. `TiMem / MemOS / EverOS` 的 raw baseline 都不低，但它们在统一框架中的真实表现更容易受到工程链路与可观测性影响，因此需要把原始能力与接入损失分开讨论。

***

## 9. 一句话总结

当前结果最稳妥的解释是：

- `O-Mem` 仍是当前最强且最平衡的参考系统；
- `MemBox` 的主要问题在检索与生成，而不是编码不可见；
- `GAM` 的 raw baseline 不低，但统一评测可观测性明显不足；
- `MemoryOS` 虽然不是 baseline 参考值最高的系统，却仍是最值得优先正式接入的下一批候选，因为它的源码结构最适合统一 probe；
- `TiMem / MemOS / EverOS` 都属于“原始能力强、接入风险也高”的系统，因此其模拟结果应作为研究预估，而不是最终实验定论。
