# GAM 与 MemOS 适配器设计蓝图（v0.1）

## 1. 文档目标

本文档只讨论两件事：

1. `GAM` 如何接入当前评估框架
2. `MemOS` 如何接入当前评估框架

目标不是立刻写代码，而是先把适配器应该长成什么样、优先实现哪些接口、每个接口到底映射原系统的哪一层逻辑说清楚。

---

## 2. 参考基线：O-Mem 适配器是怎么做的

当前项目里最成熟的参考对象是 `O-Mem` 适配器：

- [o_mem_adapter.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py)
- [base.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/base.py)

从 `O-Mem` 看，当前统一适配层真正需要的核心接口只有这些：

1. `ingest_conversation()`
2. `export_full_memory()`
3. `retrieve_original()`
4. `generate_online_answer()`
5. `generate_oracle_answer()`
6. `build_trace_for_query()`

其中 `O-Mem` 已经实现的关键方法位置是：

1. `ingest_conversation()`：[o_mem_adapter.py:L69](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py#L69)
2. `export_full_memory()`：[o_mem_adapter.py:L135](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py#L135)
3. `retrieve_original()`：[o_mem_adapter.py:L242](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py#L242)
4. `generate_oracle_answer()`：[o_mem_adapter.py:L323](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py#L323)
5. `generate_online_answer()`：[o_mem_adapter.py:L346](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/src/memory_eval/adapters/o_mem_adapter.py#L346)

所以，`GAM` 和 `MemOS` 适配时，不需要重新发明一套接口，而是：

- **尽量把各自原系统的“写入-检索-回答”链路映射到上面这 5 个核心方法。**

---

## 3. GAM 适配器设计

## 3.1 当前原系统结构

`GAM` 当前 LoCoMo 复现脚本入口是：

- [locomo_test.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research/eval/locomo_test.py)

这个脚本里已经把关键部件拆得很清楚：

1. `MemoryAgent`
2. `ResearchAgent`
3. `InMemoryMemoryStore`
4. `InMemoryPageStore`
5. `IndexRetriever`
6. `BM25Retriever`
7. `DenseRetriever`
8. `OpenAIGenerator`

对应位置可见：

- [locomo_test.py:L19-L34](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research/eval/locomo_test.py#L19-L34)
- [locomo_test.py:L299-L462](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research/eval/locomo_test.py#L299-L462)

这意味着 `GAM` 其实是非常适合做你当前统一评估适配器的，因为它内部天然就有：

1. memory store
2. page store
3. 原生 retriever
4. 最终 answer generator

---

## 3.2 建议的 `GAMAdapter` 运行态结构

建议 `run_ctx` 至少包含：

1. `sample_id`
2. `conversation_turns`
3. `session_chunks`
4. `memory_agent`
5. `memory_store`
6. `page_store`
7. `retrievers`
8. `research_agent`
9. `working_generator`
10. `artifact_refs`

其中：

### `session_chunks`

作用：

- 对应 `locomo_test.py` 里的 `build_session_chunks_for_sample()`

但适配器里不应依赖完整原始 sample 对象，而应根据输入的 conversation turns 重新构造 session chunk。

### `retrievers`

建议保留成列表，例如：

1. `index`
2. `bm25`
3. `dense`

这样后续 `retrieve_original()` 时可以保留不同检索器的来源标签。

---

## 3.3 `GAMAdapter` 的接口映射

### `ingest_conversation(sample_id, conversation)`

建议做的事：

1. 先把 turns 按 session 或时间段转成 chunk
2. 初始化：
   - `InMemoryMemoryStore`
   - `InMemoryPageStore`
3. 创建 `MemoryAgent`
4. 把 session chunks 喂给 `MemoryAgent`
5. 在 run_ctx 中保留：
   - `memory_store`
   - `page_store`
   - `memory_agent`

这一层本质上对应原系统的：

- 记忆写入 / 摘要生成 / page 构建

### `export_full_memory(run_ctx)`

建议优先导出两类视图：

1. `page_store` 中的 page
2. `memory_store` 中的 memory summary / memory objects

输出格式要统一成：

```python
{
  "id": "...",
  "text": "...",
  "meta": {...}
}
```

建议 `meta` 保留：

1. `source`: `gam_page_store` / `gam_memory_store`
2. `session_index`
3. `page_index`
4. `memory_type`

### `retrieve_original(run_ctx, query, top_k)`

这里不要直接走最终 `ResearchAgent` 的长链路推理，而应优先返回**原生候选**。

建议策略：

1. 依次调用：
   - `IndexRetriever`
   - `BM25Retriever`
   - `DenseRetriever`
2. 各自取 top-k
3. 合并成统一 `RetrievedItem`

每个候选都要保留：

1. `text`
2. `score`
3. `native_rank`
4. `retriever_type`

例如：

```python
meta = {
  "source": "gam_native_retrieval",
  "retriever_type": "bm25",
  "native_rank": 3,
}
```

### `generate_online_answer(run_ctx, query, top_k)`

这一层才调用 `ResearchAgent + working_generator`。

建议流程：

1. 先用 `retrieve_original()` 得到原生候选
2. 再调用 `ResearchAgent`
3. 生成 research summary
4. 用 working generator 生成最终 short answer

同时建议把这些内容存入 trace：

1. `retrieved_items`
2. `research_summary`
3. `final_answer`

### `generate_oracle_answer(run_ctx, query, oracle_context)`

这一层不要走检索器。

建议直接复用 `locomo_test.py` 里 answer prompt 的风格：

1. 给 working generator 提供 `oracle_context`
2. 生成 short answer

这样能最大化保持：

- online / oracle 只差在上下文来源

---

## 3.4 `GAMAdapter` 的难点

难点主要有三个：

### 难点一：脚本化实现，不是现成库 API

`GAM` 当前更多是研究脚本，不是稳定 SDK。

所以适配器最好不要继续从 `eval/locomo_test.py` 子进程调用，而应：

- 逐步把其中的核心组件直接 import 进适配器

### 难点二：session chunk 的重构

当前脚本是从 LoCoMo 原始 sample 构 chunk。

而你的适配器输入通常只有 normalized conversation。

所以需要补一个通用的 chunk builder。

### 难点三：多检索器并行结果的统一

你需要明确：

1. `retrieve_original()` 返回的是哪个 retriever 的结果
2. 还是多个 retriever 合并后的结果

我建议：

- 默认返回“多检索器合并 + 带来源标签”的结果

---

## 3.5 `GAMAdapter` 的实现优先级

建议分三版做：

### 第一版

1. `ingest_conversation`
2. `retrieve_original`
3. `generate_online_answer`

先跑 baseline。

### 第二版

1. `export_full_memory`
2. `generate_oracle_answer`

让 Encoding / Generation probe 可用。

### 第三版

1. `export_build_artifact`
2. `load_build_artifact`

如果后续要支持 build/eval 分离再补。

---

## 4. MemOS 适配器设计

## 4.1 当前原系统结构

`MemOS` 当前 LoCoMo baseline 核心不是一个统一类，而是三段式流水线：

1. ingestion
2. search
3. responses

关键脚本是：

1. [locomo_ingestion.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/locomo/locomo_ingestion.py)
2. [locomo_search.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/locomo/locomo_search.py)
3. [locomo_responses.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/locomo/locomo_responses.py)
4. [client.py](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/utils/client.py)

对 `memos-api` 来说，最关键的客户端就是：

- `MemosApiClient`
- `MemosApiOnlineClient`

位置：

- [client.py:L145-L197](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/utils/client.py#L145-L197)
- [client.py:L198-L260](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation/scripts/utils/client.py#L198-L260)

这其实给适配器提供了非常明确的切入点：

1. `add()`
2. `search()`

---

## 4.2 建议的 `MemOSAdapter` 运行态结构

建议 `run_ctx` 至少保留：

1. `sample_id`
2. `speaker_a`
3. `speaker_b`
4. `speaker_a_user_id`
5. `speaker_b_user_id`
6. `conversation_id`
7. `client`
8. `ingested_messages`
9. `added_memories`
10. `artifact_refs`

其中最重要的是：

### `speaker_a_user_id` / `speaker_b_user_id`

因为 `MemOS` 官方脚本就是按说话人分别建 memory 空间。

### `conversation_id`

对 `memos-api` 尤其重要，因为 `add()` 接口里就显式使用了：

```python
conversation_id
```

---

## 4.3 `MemOSAdapter` 的接口映射

### `ingest_conversation(sample_id, conversation)`

建议流程：

1. 规范化 turns
2. 依据说话人拆成：
   - `speaker_a_messages`
   - `speaker_b_messages`
3. 计算：
   - `speaker_a_user_id`
   - `speaker_b_user_id`
   - `conversation_id`
4. 调用 `MemosApiClient.add()`

这一层直接对应官方 `locomo_ingestion.py` 的核心逻辑。

最好在 run_ctx 中保留：

1. 原始 message payload
2. `add()` 的返回值 `added_memories`

这样后续 `export_full_memory()` 就有机会直接复用。

### `export_full_memory(run_ctx)`

优先级建议如下：

#### 第一优先级

直接利用 `add()` 返回的 `added_memories`

如果返回值里已经包含：

1. memory id
2. memory text
3. memory meta

那就直接映射成统一 memory view。

#### 第二优先级

如果 `add()` 返回不完整，则可以退一步：

1. 调用一次空 query 或通用 query 的 `search()`
2. 把返回的 memory detail 列表作为当前可观察 memory view

#### 第三优先级

再退一步时，可以把 ingestion 时实际送给系统的 message 自身当成 fallback memory view。

### `retrieve_original(run_ctx, query, top_k)`

这一层非常清晰，直接调用：

1. `client.search(query, speaker_a_user_id, top_k)`
2. `client.search(query, speaker_b_user_id, top_k)`

再把两边结果合并成统一列表。

每条结果要保留：

1. `speaker_side`: `speaker_a` / `speaker_b`
2. `native_rank`
3. `score` 或原始返回中的相似度字段
4. `memory_type`

例如：

```python
meta = {
  "source": "memos_native_retrieval",
  "speaker_side": "speaker_a",
  "native_rank": 0,
  "raw_payload": ...
}
```

### `generate_online_answer(run_ctx, query, top_k)`

建议不要一开始就直接复刻整份 `locomo_responses.py` 脚本，而是抽它的最核心逻辑：

1. 先调 `retrieve_original()`
2. 把检索结果拼成官方 `context`
3. 复用官方 `ANSWER_PROMPT_MEMOS`
4. 调一个 OpenAI-compatible LLM 生成答案

这和官方 baseline 的语义是一致的。

### `generate_oracle_answer(run_ctx, query, oracle_context)`

这一层不需要再调用 `search()`，只需要：

1. 复用 `ANSWER_PROMPT_MEMOS`
2. 把 `context` 换成 `oracle_context`
3. 调同一个 answer generator

这样能让：

- online / oracle 的对比只差在 context 来源

---

## 4.4 `MemOSAdapter` 的难点

### 难点一：官方是流水线脚本，不是单函数接口

所以最好的方案不是继续 shell 调三段脚本，而是：

- 直接把 `client.py` 的 `MemosApiClient` 收进适配器

### 难点二：memory export 可能没有现成官方 API

如果 `memos-api` 没有明确“导出全部 memory”的接口，那么 `export_full_memory()` 需要：

1. 优先复用 `add()` 返回
2. 不行再退到 `search()` 近似视图
3. 再不行就退到 ingestion echo

### 难点三：baseline 与 eval 的边界

`MemOS` 官方 baseline 的 search 和 response 本来就是两段脚本。

而你的评估框架希望的是：

1. `retrieve_original()`
2. `generate_online_answer()`

所以适配器必须把官方脚本拆回函数级接口。

---

## 4.5 `MemOSAdapter` 的实现优先级

### 第一版

1. `ingest_conversation`
2. `retrieve_original`
3. `generate_online_answer`

先把 baseline 接进来。

### 第二版

1. `export_full_memory`
2. `generate_oracle_answer`

让三层 probe 都能工作。

### 第三版

1. `export_build_artifact`
2. `load_build_artifact`

因为 `MemOS` 非常适合做 build / eval 分离。

---

## 5. 两个适配器的共同实现建议

## 5.1 family / flavor 命名

建议统一风格：

1. `GAMAdapter.family = "gam"`
2. `MemOSAdapter.family = "memos"`

后续如果需要稳定复现实验版本，可以再加：

1. `gam_stable_eval`
2. `memos_stable_eval`

---

## 5.2 trace 与 artifact

建议两者都实现：

1. `build_trace_for_query()`
2. `export_build_artifact()`

因为这两类系统都很适合把“原生检索结果、回答上下文、运行配置”保存下来。

### `GAM`

artifact 重点保存：

1. pages
2. memory_state
3. retriever config
4. generator config

### `MemOS`

artifact 重点保存：

1. `speaker_a_user_id`
2. `speaker_b_user_id`
3. `conversation_id`
4. `added_memories`
5. env/config snapshot

---

## 5.3 统一原则

无论是 `GAM` 还是 `MemOS`，都建议遵守同一个原则：

- **优先调用原系统真实接口，不要在适配器里重新发明一个伪 baseline。**

也就是说：

1. 检索必须尽量走原系统原生 `search/retriever`
2. 回答必须尽量复用原系统官方 prompt / generator
3. memory export 如果没有官方接口，再逐层 fallback

---

## 6. 推荐实现顺序

建议你后面真正开始写代码时按这个顺序：

1. `GAMAdapter` 第一版
2. `MemOSAdapter` 第一版
3. `GAMAdapter` 第二版
4. `MemOSAdapter` 第二版

因为：

1. `GAM` 更像纯 Python 研究系统，切函数接口更直接
2. `MemOS` 虽然 client 清晰，但 memory export 的 fallback 设计要更仔细

---

## 7. 一句话总结

如果把这两套适配方案压缩成一句话：

1. **GAM**
   - 直接把 `MemoryAgent + Retriever + ResearchAgent + WorkingGenerator` 映射到统一评测接口

2. **MemOS**
   - 直接把 `MemosApiClient.add/search + 官方 response prompt` 映射到统一评测接口

二者都不应该继续依赖完整 shell 脚本链路，而应尽快下沉到 Python 级函数调用。
