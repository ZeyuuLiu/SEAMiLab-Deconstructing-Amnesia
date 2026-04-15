# 新增记忆系统统一适配器层设计说明（v0.1）

## 1. 文档目标

这份文档用于说明在以下四个新增记忆系统完成官方 baseline 复现之后，如何把它们接入当前自己的统一评估框架：

1. `EverOS`
2. `General Agentic Memory`
3. `TiMem`
4. `MemOS`

本文档只给设计方案，不修改任何代码。

---

## 2. 适配目标

当前你的评估框架已经能稳定支持：

1. build / baseline / eval 三种模式
2. Encoding / Retrieval / Generation 三层探针
3. 最终归因与逐题落盘

因此新增适配器时，目标不是“把原系统重写一遍”，而是尽量从原系统中提取出四类统一能力：

1. **ingest / build**
   - 把完整对话写入原系统

2. **memory export**
   - 尽可能导出当前系统内部的记忆视图

3. **native retrieval**
   - 给定 query，返回原系统自己的检索结果

4. **online / oracle answer**
   - 原系统在线回答
   - 给定 oracle context 后的受控回答

---

## 3. 统一适配接口的核心思路

从你当前代码结构看，统一适配器的核心实际上已经比较清晰：

1. `ingest_conversation()`
2. `export_full_memory()`
3. `retrieve_original()`
4. `generate_online_answer()`
5. `generate_oracle_answer()`
6. `export_build_artifact()`
7. `load_build_artifact()`
8. `build_trace_for_query()`

新增系统适配时，关键不是每个系统都要百分百实现所有高级能力，而是：

- **尽量把原系统真实具备的能力如实映射到这套统一接口上**

---

## 4. 适配优先级建议

建议按下面的顺序做：

### 第一阶段：先支持 baseline

目标：

1. 能 ingest/build
2. 能做 online answer
3. 能做最基础的原生 retrieval
4. 能跑 `run_real_memory_eval.py --mode baseline`

这是最重要的一步。

### 第二阶段：再补齐 eval

目标：

1. `export_full_memory()` 尽可能导出结构化 memory view
2. `retrieve_original()` 保留原始 rank / score / source
3. `generate_oracle_answer()` 接到统一 generation probe

### 第三阶段：再做 build / eval 分离

对于像 MemOS / TiMem 这样本身阶段很重的系统，再补：

1. `export_build_artifact()`
2. `load_build_artifact()`
3. build-manifest 复用

---

## 5. 四个系统分别应该怎么适配

## 5.1 EverOS

## 5.1.1 当前官方复现形态

EverOS 当前更像是一个完整 evaluation pipeline：

1. `stage1_memcells_extraction`
2. `stage2_index_building`
3. `stage3_memory_retrivel`
4. `stage4_response`
5. `stage5_eval`

以及统一入口：

```bash
python -m evaluation.cli --dataset locomo --system evermemos
```

## 5.1.2 适配难点

EverOS 的难点不在接口，而在它内置的依赖假设比较重：

1. `.env` 强依赖
2. MongoDB 依赖
3. embedding / rerank 服务依赖
4. 官方 pipeline 本身就不是为外部适配器精简设计的

## 5.1.3 建议适配策略

EverOS 适配建议不要一开始就直接绑死到官方 `evaluation.cli`。

更稳的做法是：

### baseline 侧

优先从内部核心组件抽出：

1. 对话写入入口
2. query 检索入口
3. 最终 response 入口

这样可以绕过整套官方多阶段 pipeline 的非必要包装层。

### eval 侧

编码层优先尝试导出：

1. memcell 列表
2. event log
3. episode memory
4. 已建索引中的基础条目文本

如果全量导出过重，则先退一步：

- 以 stage1 / stage2 的中间产物作为 `export_full_memory()` 的替代视图

### 建议接口映射

1. `ingest_conversation()`
   - 对应 stage1 + stage2 的最小组合

2. `retrieve_original()`
   - 对应 stage3 的 query 检索输出

3. `generate_online_answer()`
   - 对应 stage4 response

4. `export_full_memory()`
   - 优先从 memcell / event log / memory index 中间文件导出

---

## 5.2 General Agentic Memory（GAM）

## 5.2.1 当前官方复现形态

GAM 的官方 LoCoMo baseline 更接近单脚本研究原型：

```bash
python eval/locomo_test.py ...
```

它需要三套模型角色：

1. memory
2. research
3. working

## 5.2.2 适配难点

GAM 的难点主要有两个：

1. 仓库运行强依赖 `research/` 工作目录和 `PYTHONPATH`
2. 其 memory / retrieval / answer 经常写在同一个 research workflow 里，不一定天然拆层

## 5.2.3 建议适配策略

GAM 是四个系统里最适合先做适配器的之一。

原因是：

1. Python 研究代码比较直接
2. baseline 已经是脚本化流程
3. 原生检索和回答逻辑更容易从代码里拆出来

### baseline 适配建议

直接包装其单题执行过程：

1. ingest 对话
2. 调原生 memory 模块
3. 调 research / working 链路产生答案

### eval 适配建议

重点优先补两个能力：

1. 从 memory 模块导出内部记忆对象
2. 从 research 阶段输出原生检索候选

### 建议接口映射

1. `ingest_conversation()`
   - 初始化 memory state

2. `retrieve_original()`
   - research pipeline 内的原生候选集

3. `generate_online_answer()`
   - 最终 working answer

4. `export_full_memory()`
   - memory 模块内部维护的 memory objects / summary / facts

---

## 5.3 TiMem

## 5.3.1 当前官方复现形态

TiMem 是标准的三阶段实验流程：

1. `01_memory_generation.py`
2. `02_memory_retrieval.py`
3. `03_evaluation.py`

并且依赖 Docker 起数据库服务。

## 5.3.2 适配难点

TiMem 的最大难点是：

1. 它本身已经是一套完整实验框架
2. 而不是一个单纯的 memory agent library
3. 它内部状态与数据库耦合更重

因此，TiMem 更像是：

- “实验系统接实验系统”

而不是：

- “业务记忆系统接评测系统”

## 5.3.3 建议适配策略

TiMem 适配建议不要急着做在线细粒度单题调用。

更合理的方式是：

### 第一阶段

先用它的阶段性文件结果做离线适配：

1. memory generation 结果
2. memory retrieval 结果
3. final answer / eval 中间文件

### 第二阶段

再逐步抽象出在线接口：

1. `build` 对应 memory generation
2. `retrieve_original()` 对应 retrieval 阶段
3. `generate_online_answer()` 对应其在线 answer 输出

### 建议接口映射

1. `export_build_artifact()`
   - 尤其适合 TiMem

2. `load_build_artifact()`
   - 用于 generation / retrieval 复用

3. `export_full_memory()`
   - 优先从 memory generation 中间文件导出

因此，TiMem 会是最适合做 **build/eval 分离型适配器** 的系统之一。

---

## 5.4 MemOS

## 5.4.1 当前官方复现形态

MemOS 官方 LoCoMo 评测是典型五阶段流水线：

1. ingestion
2. search
3. responses
4. eval
5. metric

## 5.4.2 适配难点

MemOS 的难点主要有两个：

1. 官方评测脚本是流水线型，不是面向单题函数调用型
2. 如果走 `memos-api`，还要考虑本地服务状态

## 5.4.3 建议适配策略

MemOS 的适配路线和当前 `MemBox` 很像：

### baseline 侧

先让适配器包装：

1. ingestion/build
2. search
3. response

### eval 侧

优先想办法拿到：

1. memory objects
2. search top-k
3. online response

### build/eval 分离

MemOS 很适合像 MemBox 一样做：

1. build 阶段先构建 memory state
2. baseline / eval 复用 build artifact

### 建议接口映射

1. `ingest_conversation()`
   - 对应 ingestion

2. `retrieve_original()`
   - 对应 search 结果

3. `generate_online_answer()`
   - 对应 responses

4. `export_build_artifact()`
   - 对应 ingestion 后的索引或 session state

---

## 6. 统一适配器层建议的目录组织

建议后续在你当前项目中保持如下结构风格：

```text
src/memory_eval/adapters/
  everos_adapter.py
  gam_adapter.py
  timem_adapter.py
  memos_adapter.py
```

每个适配器建议包含三类方法：

### 第一类：最小运行接口

1. `ingest_conversation`
2. `retrieve_original`
3. `generate_online_answer`

### 第二类：评测增强接口

1. `export_full_memory`
2. `generate_oracle_answer`
3. `build_trace_for_query`

### 第三类：分阶段复用接口

1. `export_build_artifact`
2. `load_build_artifact`

---

## 7. 适配实现顺序建议

建议按下面顺序真正开始写代码：

## 第一步：GAM

原因：

1. Python 结构最直接
2. baseline 脚本入口明确
3. 依赖相对容易控制

## 第二步：MemOS

原因：

1. 官方 LoCoMo 流水线最标准
2. 适合 build / eval 分离建模

## 第三步：EverOS

原因：

1. 官方能力强，但依赖假设更重
2. 适配时要处理 .env / MongoDB / embedding/rerank 服务

## 第四步：TiMem

原因：

1. 更重实验系统
2. 适合最后再做 build artifact 型离线适配

---

## 8. 每个适配器最先应该交付什么

最小可用版本不要求一步到位。

建议每个新适配器第一版只交付：

1. `baseline` 可跑
2. `retrieve_original()` 可拿到 top-k
3. `generate_online_answer()` 可用
4. `export_full_memory()` 至少返回一个可观察 memory view

只要做到这一步，就已经可以：

1. 跑 baseline
2. 跑基本 eval
3. 看编码层和检索层的初步表现

后续再逐渐补：

1. `generate_oracle_answer()`
2. `artifact_refs`
3. build-manifest 分离

---

## 9. 当前最重要的现实约束

在真正写适配器之前，需要先接受一个现实：

这四个系统并不是统一 API 设计出来的，它们对“memory”的定义差异很大。

因此适配目标不应该是：

- 强行让四个系统长成一样

而应该是：

- **在保留各自原生行为的前提下，尽量映射到同一评测抽象层**

这也是为什么当前三层框架特别重要：

1. 编码层只关心有没有留下可用记忆痕迹
2. 检索层只关心原系统有没有把相关记忆取出来
3. 生成层只关心在证据给定后会不会答

这套抽象恰好可以减少对不同系统内部实现差异的敏感性。

---

## 10. 一句话总结

这四个新系统后续适配的总体策略应当是：

1. **先跑通官方 baseline**
2. **再抽取 ingest / retrieval / answer 三个最小公共接口**
3. **再补 memory export 与 build artifact**
4. **最后接入三层探针和最终归因**

其中实现顺序建议为：

1. `GAM`
2. `MemOS`
3. `EverOS`
4. `TiMem`

这样能最大化降低前期适配成本，并且更快得到第一批可解释评测结果。
