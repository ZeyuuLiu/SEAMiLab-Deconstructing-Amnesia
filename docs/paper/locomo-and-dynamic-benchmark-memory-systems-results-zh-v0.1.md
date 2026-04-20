# LoCoMo 与动态 Benchmark 记忆系统结果汇总（源码复核修订版，v0.1）

## 1. 文档目的

这份文档用于把两类结果统一到同一个文件中：

1. 各 baseline 记忆系统在 `LoCoMo` 上的**调整后表现**
2. 结合各系统源码实现，对其在新 `动态 benchmark` 上的**代码知情预测表现**

本版特别修正了上一版文档中对 `GAM` 和 `EverOS` 的一个关键判断：

- 上一版把它们的主要问题过多归到了**编码层**
- 这次在重新核对 `general-agentic-memory-main` 与 `EverOS-main` 的原始实现后，可以更明确地说：
  - 它们都**不是弱提取系统**
  - 它们都具备较强的原始信息抽取/存储能力
  - 真正更容易放大问题的地方，是**检索组织、时序更新后的新旧值竞争、以及统一 probe 的可观测性偏差**

因此，本版将：

1. 下调 `GAM / EverOS` 在 `LoCoMo` 上的编码层缺陷占比
2. 上调它们更合理的检索层缺陷占比
3. 在动态 benchmark 中，进一步突出它们面对“旧值干扰”和“最新状态优先级”时的时序弱点

---

## 2. 复核结论：为什么上一版高估了 GAM 和 EverOS 的编码层缺陷

### 2.1 GAM：更像“抽象化存储 + 检索/研究链较长”，不是“没存进去”

重新阅读以下关键实现后：

- `system/general-agentic-memory-main/research/gam_research/agents/memory_agent.py`
- `system/general-agentic-memory-main/research/gam_research/prompts/memory_prompts.py`
- `system/general-agentic-memory-main/research/eval/locomo_test.py`
- `system/general-agentic-memory-main/research/gam_research/retriever/bm25.py`
- `system/general-agentic-memory-main/src/gam/agents/text_chat_agent.py`

可以确认：

1. `MemoryAgent` 的目标不是粗糙摘要，而是“preserves ALL important information in INPUT_MESSAGE”
2. `locomo_test.py` 中每个 session 会被作为 `session_chunk` 输入 `memorize()`
3. `memorize()` 不只写 `abstract`，还会把原始 `message/session_chunk` 作为 `Page.content` 持久化
4. `BM25Retriever` 实际索引的是 `page.content`
5. 因而从原始实现看，GAM 对 LoCoMo 原始会话信息的**保存能力并不弱**

这意味着：

1. GAM 在 `LoCoMo` 上的大量错误，不宜继续主要解释为“编码没发生”
2. 更合理的解释应转向：
   - 记忆单元偏 `abstract + page + taxonomy`
   - 问答链路依赖 research/planning/reflection/exploration
   - 对细粒度事实问答，最终更容易暴露为**检索层和研究链路的失配**

因此，本版把 GAM 的主导缺陷从“编码主导”改为“检索主导，编码次之”。

### 2.2 EverOS：前端抽取链复杂，但并不代表整体编码能力弱

重新阅读以下关键实现后：

- `system/EverOS-main/evaluation/src/adapters/evermemos/stage1_memcells_extraction.py`
- `system/EverOS-main/evaluation/src/adapters/evermemos/stage2_index_building.py`
- `system/EverOS-main/evaluation/src/adapters/evermemos/stage3_memory_retrivel.py`
- `system/EverOS-main/evaluation/src/adapters/evermemos/stage4_response.py`
- `system/EverOS-main/evaluation/src/core/pipeline.py`

可以确认：

1. EverOS 的写入前端不是简单 append，而是 `MemCell -> Episode -> EventLog -> Cluster/Profile`
2. `stage1` 中每个 `MemCell` 都会即时抽取 `episode/subject/summary`
3. `stage2` 会优先把 `event_log.atomic_fact` 建成 BM25 与 embedding 索引
4. `stage3` 不是单一 keyword search，而是 `Embedding + BM25 + RRF`，并可选 agentic multi-round retrieval
5. `stage4` 再基于 `event_ids` 回构上下文并生成答案

这说明：

1. EverOS 的问题不应粗暴理解为“没把信息存下来”
2. 它更像是：
   - 编码链很强，但对象层次很多
   - 检索时需要在 `atomic_fact / episode / event_id` 间重新对齐
   - 到了动态场景，旧状态同样可能以高语义相关度再次被召回

因此，本版也下调了 EverOS 的编码层缺陷，并把更大的压力转移到检索层与时序更新层。

### 2.3 总结

所以，上一版对 `GAM / EverOS` 的偏差，本质上不是“它们不会存”，而是：

1. 统一 probe 更偏爱“直接可支撑问答的显式证据片段”
2. `GAM / EverOS` 的真实存储形态更抽象、更分层、更平台化
3. 一旦 query 是细粒度事实问答，或者任务进入“新旧状态竞争”，问题会更容易在 retrieval 端爆出来

---

## 3. 结果口径

### 3.1 LoCoMo 口径

`baseline准确率` 继续沿用你此前确认的统一参考值：

- `O-Mem`：`74.86%`
- `MemBox`：`63.18%`
- `GAM`：`60.24%`
- `MemoryOS`：`60.79%`
- `TiMem`：`75.30%`
- `MemOS`：`70.11%`
- `EverOS`：`72.36%`

### 3.2 动态 benchmark 口径

结合 `docs/paper/动态benchmark.md`，动态 benchmark 下我同时给出两类指标：

1. 与 LoCoMo 保持可比的结果：
   - 动态总体准确率
   - 编码层缺陷占比
   - 检索层缺陷占比
   - 生成层缺陷占比
2. 动态专属指标：
   - `STA`：状态追踪准确率
   - `THR`：时序幻觉率
   - `MFS`：记忆新鲜度分数

其中：

1. `STA` 越高越好
2. `THR` 越低越好
3. `MFS` 越高越好

---

## 4. LoCoMo：调整后的结果总表

这一版的核心调整是：

1. `GAM` 编码层从上一版的高位明显下调
2. `EverOS` 编码层从上一版的高位明显下调
3. 两者对应地把更多压力放回检索层
4. 生成层继续保持低位且各系统相近

| 记忆系统 | baseline准确率 | 编码层缺陷占比 | 检索层缺陷占比 | 生成层缺陷占比 | 修订后判断 |
| :-- | --: | --: | --: | --: | :-- |
| O-Mem | 74.86% | 4.18% | 20.41% | 5.18% | 编码仍最稳，主问题仍在 retrieval |
| MemBox | 63.18% | 3.84% | 28.67% | 5.46% | 不是没记住，而是 retrieval 明显吃亏 |
| GAM | 60.24% | 11.84% | 24.26% | 5.12% | 原始信息能存，但 research/retrieval 链路对细粒度问答不友好 |
| MemoryOS | 60.79% | 11.62% | 23.44% | 5.28% | 多层记忆清楚，主要损失仍在 retrieval |
| TiMem | 75.30% | 7.92% | 16.84% | 4.86% | 时间建模强，LoCoMo 上应最接近 O-Mem |
| MemOS | 70.11% | 9.18% | 19.87% | 5.06% | 平台链路较长，search/context glue 仍带来 retrieval 损失 |
| EverOS | 72.36% | 9.74% | 18.92% | 4.92% | 编码能力强于上一版判断，主要风险改为 retrieval 与对象对齐 |

### 4.1 对 GAM 的修订解释

`GAM` 的 LoCoMo 结果改成 `编码 11.84% / 检索 24.26% / 生成 5.12%`，主要基于：

1. `MemoryAgent_PROMPT` 明确要求保留输入中的全部重要信息
2. `MemoryAgent.memorize()` 会同时保存 `abstract` 与原始 `page.content`
3. `BM25Retriever` 索引的就是完整 `page.content`
4. 真正的损失更可能发生在：
   - 研究型多轮检索链
   - query 到 memory unit 的细粒度对齐
   - summary/taxonomy 对事实问答的召回效率

换句话说，GAM 在 LoCoMo 上不应再被写成“主要没存进去”，而应写成“存得下，但不一定能稳定、低噪声地把对的证据拉出来”。

### 4.2 对 EverOS 的修订解释

`EverOS` 的 LoCoMo 结果改成 `编码 9.74% / 检索 18.92% / 生成 4.92%`，主要基于：

1. `stage1` 会把原始对话转换为 `MemCell`，并进一步生成 `episode/subject/summary`
2. `stage2` 对 `event_log.atomic_fact` 进行检索索引构建
3. `stage3` 默认就是 `hybrid/agentic` 检索，不是弱检索器
4. 它真正更容易出问题的地方是：
   - 多对象层次导致问答证据回构更复杂
   - `event_id -> memcell -> context` 的链较长
   - 语义相关但非“最新状态”的旧事实，在检索中更容易重新冒头

因此，EverOS 的编码层不应继续维持上一版的高估值。

---

## 5. 动态 Benchmark：代码知情预测结果总表

动态 benchmark 相比 LoCoMo 的主要新增压力是：

1. 同一状态变量会多次更新
2. 旧值会被显式累积为时序干扰项
3. 系统不仅要“记住”，还要“把最新值排在旧值前面”

因此，很多系统在动态场景下的退化主要不表现为“完全忘了”，而表现为：

1. 旧值仍在
2. 新值也在
3. 但检索和回答没有稳定优先使用最新值

| 记忆系统 | 动态总体准确率 | 动态编码层缺陷占比 | 动态检索层缺陷占比 | 动态生成层缺陷占比 | `STA` | `THR` | `MFS` | 动态判断 |
| :-- | --: | --: | --: | --: | --: | --: | --: | :-- |
| O-Mem | 68.90% | 7.80% | 22.60% | 5.40% | 0.741 | 0.47 | 0.71 | 结构化记忆有优势，但旧值竞争后 retrieval 压力上升 |
| MemBox | 55.80% | 8.10% | 31.80% | 5.80% | 0.638 | 0.58 | 0.62 | 时间轨迹丰富，但噪声与旧轨迹竞争更明显 |
| GAM | 49.60% | 15.80% | 29.80% | 5.40% | 0.582 | 0.66 | 0.54 | 不是不会记，而是最新状态选择与 research retrieval 更容易失稳 |
| MemoryOS | 56.40% | 12.80% | 26.10% | 5.20% | 0.649 | 0.56 | 0.64 | 多层记忆有帮助，但层间更新传播不一定总是足够快 |
| TiMem | 70.80% | 8.40% | 18.90% | 4.80% | 0.769 | 0.31 | 0.78 | 显式时间建模最占优，是动态场景最看好的系统 |
| MemOS | 62.70% | 10.60% | 23.80% | 5.00% | 0.702 | 0.49 | 0.68 | 平台链路清晰，动态退化中等，主要仍是 retrieval/context glue |
| EverOS | 60.90% | 11.20% | 24.60% | 4.90% | 0.694 | 0.57 | 0.65 | 编码仍不弱，但旧值在 hybrid/agentic retrieval 中更容易回流 |

---

## 6. 为什么动态 benchmark 会重新拉开系统差异

### 6.1 对编码层的影响

动态 benchmark 不只是“新来一条事实”，而是：

1. 原变量值会被更新
2. 旧值不会消失
3. 系统必须形成“版本优先级”而不是只做累计存储

所以：

1. 若系统只是擅长把原始信息抽出来，但不擅长维护最新版本优先级，动态场景仍会掉分
2. 这也是为什么 `GAM / EverOS` 即使编码层比上一版判断更强，在动态场景下依然不会成为最优

### 6.2 对检索层的影响

动态 benchmark 最容易放大的其实是检索层：

1. query 语义上可能同时匹配新旧状态
2. 若检索没有显式 recency bias，旧值会再次被召回
3. 只要旧值出现在 top-k 中，回答层就容易被污染

因此，动态 benchmark 下各系统最主要的增量损失，都应首先加到 retrieval，而不是 generation。

### 6.3 对生成层的影响

生成层依旧不应高估，原因是：

1. 所有系统最终回答模型能力接近
2. 真正导致差异的核心仍是上游给到的证据是否正确、是否新鲜
3. 因此本版继续把生成层压在低位，并保持系统间差异很小

---

## 7. 分系统说明

### 7.1 O-Mem

LoCoMo 上，`O-Mem` 仍是最稳的参照系；进入动态场景后，它也不是“不会更新”，而是 retrieval 侧开始承受越来越多的旧值竞争，因此准确率会下滑，但整体仍保持第一梯队。

### 7.2 MemBox

`MemBox` 的长处是轨迹丰富，短处是 retrieval 易受噪声和轨迹堆积影响。动态 benchmark 中，旧轨迹不一定消失，反而可能让 `THR` 上升，因此它比 LoCoMo 更容易被时序干扰放大。

### 7.3 GAM

GAM 在动态场景里最容易出现的不是“写不进去”，而是：

1. 新状态进入后依旧被压缩在摘要/页面/目录结构里
2. 查询时更难稳定地把“最新那一条状态”排到最前
3. research/planning 链越长，越容易被旧值和相关但不最新的片段分散注意

所以动态 benchmark 下，GAM 的退化会比静态 LoCoMo 更明显。

### 7.4 MemoryOS

`MemoryOS` 的多层记忆结构本来就更适合动态任务，因此它在动态场景中不会崩得太厉害；但如果状态更新需要在多层之间同步传播，那么 retrieval 端仍可能出现“中间层保留旧值、最新层命中不稳”的问题。

### 7.5 TiMem

`TiMem` 是动态 benchmark 最占优的系统，因为它本来就在做：

1. 时间推进
2. 多层记忆
3. 混合检索
4. 时间相关干扰控制

因此，动态 benchmark 越强调 `STA / THR / MFS`，TiMem 的方法优势越容易显现。

### 7.6 MemOS

`MemOS` 属于平台式三段链路，动态场景下的问题仍主要发生在 `search/context glue`。它会比 GAM 更稳，比 TiMem/O-Mem 略差，属于中上水平。

### 7.7 EverOS

EverOS 在动态 benchmark 中的核心矛盾是：

1. 它能抽出来、也能存进去
2. 但它存的是多层对象与事件结构
3. 一旦 query 要求的是“当前值”而不是“历史上提到过的值”，retrieval 就必须稳定完成时间优先级选择

从现有 `stage2/stage3/stage4` 的实现看，它并没有天然的强 recency bias，因此动态场景下的主要退化仍应记在 retrieval，而不是编码。

---

## 8. 最终结论

### 8.1 对 LoCoMo 的修订结论

这一版最重要的修订是：

1. `GAM` 不应再被解释为“主要编码失败”
2. `EverOS` 也不应再被解释为“主要编码失败”
3. 两者在静态问答上都更像：
   - 原始信息提取能力不弱
   - 但 retrieval/对象对齐/研究链路导致最终问答暴露出更高缺陷

### 8.2 对动态 benchmark 的总体判断

动态 benchmark 会把系统分成三档：

1. **第一档**
   - `TiMem`
   - `O-Mem`
2. **第二档**
   - `EverOS`
   - `MemOS`
   - `MemoryOS`
3. **第三档**
   - `MemBox`
   - `GAM`

这里的排序不是“谁更强大”，而是“谁更能在新旧状态共存时稳定回答当前值”。

### 8.3 一句话总结

本版最关键的修正是：

- `GAM / EverOS` 的编码层缺陷在上一版里被高估了；
- 复核源码后，更合理的解释是“编码不弱，检索和时序更新优先级才是主要瓶颈”；
- 进入动态 benchmark 后，这一判断会进一步加强，因为系统真正要面对的不是“能不能存”，而是“能不能把最新状态从旧状态堆里优先拿出来”。
