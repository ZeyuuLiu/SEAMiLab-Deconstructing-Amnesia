# MemBox 独立环境、卡死排查与 LLM-as-Judge 改造前说明（v0.1）

## 1. 文档目标

这份文档是**修改代码之前**的说明文档，目的有四个：

1. 明确如何新建 MemBox 的独立 conda 环境，并验证现在是否能运行评估系统。
2. 解释为什么当前 MemBox 的 eval 可能“卡死”，以及我认为最可能的问题点在哪里。
3. 结合 TiMem 与 MemOS 论文，说明后续 `LLM-as-Judge` 应该如何统一 baseline 与 eval 的语义判分。
4. 列出我在真正改代码前，需要你确认的关键细节。

## 2. 当前我对现状的判断

### 2.1 已经成立的部分

当前仓库已经具备：

1. 三个并行探针 Agent：
   - EncodingAgent
   - RetrievalAgent
   - GenerationAgent
2. 一个最终归因 Agent：
   - AttributionAgent
3. O-Mem / MemBox 的统一适配层
4. baseline 与 eval 的统一脚本入口

因此现在的问题不是“框架不存在”，而是：

1. MemBox eval 的运行稳定性和可观测性不够
2. baseline 与 eval 的正确性口径不统一
3. 结果落盘方式不利于逐题排查
4. 编码层尚未给你的自定义 RAG 检索留正式接口

### 2.2 MemBox 为什么 baseline 能跑、eval 却可能卡死

我目前认为这是三个问题叠加导致的：

1. **MemBox 构建本身就很重**
   - 其 BUILD / TRACE / linking 阶段都依赖大量 LLM 调用
2. **eval 比 baseline 多跑很多路径**
   - baseline 只做 online answer 与 correctness
   - eval 还要做 full memory export、原生检索、oracle answer、三探针归因
3. **现在缺少逐题心跳与单步超时**
   - 卡住时你不知道是卡在 ingest、retrieve_original、oracle generation，还是卡在第几题

更具体一点，从当前 MemBox stableEval 的实现看，`LLMWorker.chat_completion()` 直接使用：

- `self.client.chat.completions.create(**kwargs)`

但**没有显式 timeout，没有重试上界，也没有阶段化心跳日志**。  
因此只要某一次外部模型调用长时间挂住，看上去就像“整个 eval 卡死”。

## 3. 先给你：MemBox 独立 conda 环境创建方案

我建议 MemBox 必须拆出自己的独立环境：

- `memeval-membox-v1`

后续任何新记忆系统也按同样规则：

- `memeval-<system>-v1`

## 3.1 创建环境

```bash
conda create -n memeval-membox-v1 python=3.10 -y
```

## 3.2 安装基础工具

```bash
conda run -n memeval-membox-v1 python -m pip install -U pip setuptools wheel
```

## 3.3 安装项目本体

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run -n memeval-membox-v1 python -m pip install -e .
```

## 3.4 安装 MemBox 依赖

根据当前仓库中的 Membox 依赖与运行路径，我建议先安装这一组最小依赖：

```bash
conda run -n memeval-membox-v1 python -m pip install \
  openai \
  scikit-learn \
  nltk \
  tiktoken \
  numpy
```

如果后续运行时缺包，再补：

```bash
conda run -n memeval-membox-v1 python -m pip install pandas tqdm
```

## 3.5 下载 NLTK 资源

```bash
conda run -n memeval-membox-v1 python - <<'PY'
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
PY
```

## 3.6 检查环境是否可导入

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run -n memeval-membox-v1 python - <<'PY'
import memory_eval
from memory_eval.adapters import create_adapter_by_system
print("memory_eval ok")
print("registry ok")
adapter = create_adapter_by_system("membox_stable_eval", {})
print(type(adapter).__name__)
PY
```

如果这里能正常打印：

1. `memory_eval ok`
2. `registry ok`
3. `MemboxAdapter`

说明 MemBox 独立环境已经基本建好。

## 3.7 检查 baseline 是否可运行

建议先跑一个最短 smoke：

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 1 \
  --keys-path configs/keys.local.json \
  --output outputs/membox_baseline_smoke.json
```

如果 smoke 正常，再跑你当前的 sample0 baseline。

## 4. 当前我对 MemBox eval 卡死的具体排查判断

## 4.1 适配器层最可疑的点

结合当前实现，我认为最可疑的点不是单一死循环，而是：

### 4.1.1 外部 LLM 调用没有 timeout

`Membox_stableEval/membox.py` 中的：

1. `LLMWorker.chat_completion()`
2. `LLMWorker.get_embedding()`

都没有显式 timeout。

这意味着：

1. baseline 也可能慢
2. 但 eval 一旦多跑 oracle / retrieval / probe judge，更容易放大这个问题

### 4.1.2 eval 与 baseline 没有共用同一个 build artifact 复用机制

如果 eval 每次又重新 ingest / build / trace 一遍，那么：

1. 本来 baseline 半天
2. eval 再来一遍构建
3. 再叠加三探针

很容易表现成“整天没动静”。

### 4.1.3 缺少逐题日志

现在你很难知道：

1. 卡在哪一题
2. 卡在哪个 probe
3. 卡在 retrieval 还是 oracle generation

这会把“慢”误判成“死循环”。

### 4.1.4 适配器里 trace/build 能力没有和评估主链路做强绑定

当前 MemBox 适配器已经能输出：

1. `run_id`
2. `output_root`
3. `final_content_file`
4. `time_trace_file`

但评估主链路没有强制把这些 artifact 和每道题结果绑定起来。  
这会导致排查时看不出“当前题依赖的是哪一次 build 产物”。

## 4.2 我的方案

在真正改代码时，我建议按下面顺序解决：

1. 把 MemBox 运行拆成：
   - Build 阶段
   - Eval 阶段
2. Build 完成后产出：
   - `build_manifest.json`
   - `artifact_index.json`
3. Eval 只消费 build 产物，不重复构建
4. 给每道题输出：
   - 当前 question_id
   - 当前 probe
   - 当前耗时
   - 当前 artifact refs
5. 给：
   - retrieve_original
   - generate_oracle_answer
   - attribution
   增加单步 timeout

## 5. LLM-as-Judge：准备采用的方案

你补充的 TiMem 论文很关键，我已经基于本地论文文本抽取了它的 QA prompt 与 Judge prompt。

TiMem 在 LoCoMo 上采用的 judge 核心思想是：

1. 给定 `question`
2. 给定 `gold answer`
3. 给定 `generated answer`
4. Judge 以**宽松语义等价**为核心
5. 对时间问题允许格式不同但指向同一日期/时间段
6. 最终输出 `CORRECT / WRONG`

TiMem 里对应的 judge prompt要点可以概括为：

1. **只要 generated answer 触及与 gold 相同主题，就倾向视为 CORRECT**
2. **对于时间问题，若指向同一时间点/区间，即使格式不同也视为 CORRECT**
3. **要求 generous grading**

这和你现在的目标是高度一致的。

## 5.1 我建议吸收 TiMem 的哪些点

### 5.1.1 baseline 与 eval 共用同一套 Judge

这点必须统一。

也就是说：

1. baseline 不再只用字面匹配
2. generation probe 也不再用另一套独立口径

而是统一接入：

1. `CorrectnessJudge`

### 5.1.2 Pos / Neg 完全分流

这里要特别强调：

TiMem 的 judge 主要是围绕“是否答对”。

但你这里有 POS / NEG 两类任务，NEG 不能直接照搬。

因此我建议：

#### POS Judge

借鉴 TiMem：

1. generous semantic equivalence
2. time normalization aware
3. 允许长答案中包含正确核心答案

#### NEG Judge

不能用 TiMem 原样，需要单独设计：

1. 是否正确拒答
2. 是否编造原文没有的信息
3. 是否给出足以被视为 hallucination 的具体断言

## 5.2 我建议的 Judge 输出

后续统一输出不应再只有一个布尔值，而应是：

1. `rule_correct`
2. `llm_correct`
3. `final_correct`
4. `judge_reason`
5. `judge_label`
6. `judge_payload`

其中：

1. `rule_correct` 保留可复现对账
2. `llm_correct` 负责语义纠偏
3. `final_correct` 作为统一统计口径

## 6. baseline 与 eval 必须共享同一套语义正确性标准

这点我完全同意你的要求。

当前 baseline 与 eval 口径分裂，会导致：

1. baseline 说错
2. eval 某层又隐含认为语义上没错

最终你就很难对账。

所以后续改造我会按这个原则：

1. baseline 的最终正确性
2. generation 的 online/oracle 正确性
3. per-question 汇总显示的最终正确性

都共用同一个 `CorrectnessJudge`。

## 7. 结果展示：我计划怎么改

我会遵循你认可的上一版方案，进一步收敛成：

### 7.1 run 级 summary

1. 总题数
2. POS / NEG 数
3. baseline accuracy
4. refusal accuracy
5. probe 状态统计

### 7.2 题级索引

每题给：

1. `question_id`
2. `task_type`
3. `final_correct`
4. `primary_cause`
5. `result_file`

### 7.3 per-question 单独 JSON

每题单独落盘，包含：

1. 当前问题
2. 当前系统回答
3. gold answer
4. baseline correctness
5. generation correctness
6. probe states
7. final attribution
8. decision_logic
9. artifact refs

## 7.4 最终归因层怎么简化

这一步我不准备再让最终归因重复 probe 内容，而是只输出：

1. `final_attribution`
2. `primary_cause`
3. `secondary_causes`
4. `decision_logic`
5. `final_judgement`

其中 `decision_logic` 最多 2-4 条简洁句子。

## 8. 编码层：如何给你的自定义 RAG 框架留接口

这个部分我不会把你的 RAG 逻辑硬编码进 adapter。

我的设计是增加一个正式的高召回接口：

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

### 接入优先级

1. external custom retriever
2. adapter hybrid retrieve
3. adapter find records
4. rule fallback

这样等你把自己的 RAG 框架给我时，我只需要把它接到这个标准槽位上。

## 9. 在真正开始改代码前，我需要你确认的关键细节

下面这些点如果你先确认，我后续实现时就不会反复返工。

### 9.1 baseline 最终统计口径

你希望最终 baseline 的 accuracy 用哪个口径做正式统计？

可选理解是：

1. `final_correct` 只看 LLM judge
2. `final_correct` = 规则 + LLM 融合

我个人建议：

1. 保留 `rule_correct`
2. 保留 `llm_correct`
3. 正式统计用 `final_correct`

### 9.2 NEG 任务的 gold 正确判定

对于 NEG，你更希望 judge 判断：

1. “是否拒答”
还是
2. “是否没有编造任何具体事实”
还是
3. 两者同时满足才算正确

我个人建议选：

3. 两者同时满足才算正确

### 9.3 MemBox eval 的运行方式

你希望后续 MemBox eval：

1. 每次运行都重新 build
还是
2. 先 build 一次，再复用 build artifact 跑 eval

我强烈建议：

2. 先 build 一次，再复用

### 9.4 per-question JSON 的组织方式

你希望每道题结果按：

1. `sample_id/question_id.json`
还是
2. 单目录平铺

我建议：

1. `outputs/<run_id>/questions/<question_id>.json`

### 9.5 最终归因的简化粒度

你是否接受最终归因只输出：

1. 主因
2. 次因
3. 2-4 条 decision logic

而不再重复 probe 的详细 evidence？

我建议是：

1. 接受

## 10. 我建议的下一步

如果你确认上面这些方向，后续正式改代码时我会按这个顺序推进：

### 第一阶段

1. 建立 MemBox 独立环境与 smoke 检查
2. 拆分 build/eval
3. 增加逐题心跳与 timeout

### 第二阶段

1. 实现统一 `CorrectnessJudge`
2. baseline 与 generation 共用语义判分
3. Pos / Neg 分流

### 第三阶段

1. 重构结果落盘
2. 增加 per-question JSON
3. 简化 AttributionAgent 输出

### 第四阶段

1. 接入编码层自定义高召回检索 hook

## 11. 结论

我现在的核心判断是：

1. **MemBox eval 卡死问题，本质上是“重构阶段/评估阶段混合 + 无 timeout + 无心跳日志”的可观测性问题**
2. **baseline 与 eval 必须共享同一套 TiMem 风格的语义 Judge**
3. **NEG 任务必须单独设计 refusal-aware judge，不能直接照搬论文 prompt**
4. **后续结果必须逐题落盘，并简化最终归因输出**
5. **编码层必须正式留出外部 RAG 高召回接口**

这份文档是我正式改代码前的实施说明。  
你只要把第 9 节这些关键点给我确认掉，我下一步就可以开始真正改代码。
