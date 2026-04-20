# 评估框架、适配器状态与 Baseline 候选系统说明（v0.1）

## 1. 文档目标

这份文档用于统一说明当前三件事：

1. `llm-as-judge` 的当前口径与最近一次回调
2. `GAM` 与 `MemBox` 适配器在当前评估框架中的实现状态
3. `system/` 目录内哪些系统适合纳入 baseline，对哪些系统应暂缓

---

## 2. judge 当前口径

## 2.1 为什么要回调

本轮之前的 correctness judge 比较严格，主要体现在：

1. prompt 文案中对 `POS` 题的拒答/保守回答约束过强
2. `correctness_judge.py` 中额外对 `POS refusal` 做了 `_hard_veto()`

这会导致：

1. 即使 LLM judge 认为语义上是对的
2. 只要回答措辞保守或带轻度拒答痕迹
3. 仍可能被强行判错

这与 TiMem 附录展示的宽松语义等价风格不一致，也比 `0401/0402` 那一版更强硬。

## 2.2 当前怎么改的

当前已经做了两类调整：

### prompt 层

在 `src/memory_eval/eval_core/prompts.py` 中：

1. 不再写“参考 TiMem 论文的方法”
2. 而是把宽松判分规则直接展开成正文
3. 明确：
   - 核心事实一致即可算对
   - 时间问题只要指向同一日期/月份/年份/相对时间即可算对
   - 更长、更口语化、更保守的答案，不应仅因措辞不同被判错
   - `NEG` 场景下才重点关注谨慎回答与编造

### 规则层

在 `src/memory_eval/eval_core/correctness_judge.py` 中：

1. 当 `LLM judge` 可用时，最终正确性以 `llm_correct` 为主
2. 不再对 `POS refusal` 做额外 hard veto

因此当前 judge 的整体风格已经更接近：

- `TiMem appendix` 展示的 `CORRECT / WRONG` 宽松语义等价判分

---

## 3. GAM 适配器当前状态

## 3.1 已完成内容

`GAM` 当前已经接入你自己的评估框架，适配器文件为：

- `src/memory_eval/adapters/gam_adapter.py`

已实现的核心接口包括：

1. `ingest_conversation()`
2. `export_full_memory()`
3. `find_memory_records()`
4. `hybrid_retrieve_candidates()`
5. `retrieve_original()`
6. `generate_online_answer()`
7. `generate_oracle_answer()`
8. `build_trace_for_query()`
9. `export_build_artifact()`

## 3.2 当前接线策略

当前 `GAMAdapter` 的实现思路是：

1. ingest 阶段直接接 `MemoryAgent`
2. memory export 同时读：
   - `memory_store`
   - `page_store`
3. retrieval 阶段优先走：
   - `IndexRetriever`
   - keyword fallback
4. online answer 走：
   - `ResearchAgent`
   - `working generator`
5. oracle answer 直接喂 `oracle_context`

## 3.3 最近补的关键修正

这轮又补了两个重要问题：

1. `build_trace_for_query()` 现在已经按 `AdapterTrace` 标准字段返回：
   - `memory_view`
   - `retrieved_items`
   - `answer_online`
   - `answer_oracle`
   - `raw_trace`
2. `retrieved_items` 现在会标准化成 `RetrievedItem`

这使得 `GAM` 不只是“能注册”，而是更接近：

- 真正可进入 `baseline` / `eval` 主链路

## 3.4 当前结论

对于当前项目，`GAM` 可以视为：

- **已进入可评估状态**

但仍需注意：

1. 它的原始 baseline 依赖更重的检索器配置
2. 当前适配器采用的是“先保评测接口稳定，再逐步提升原始 fidelity”的路线

也就是说：

- 现在适合纳入 baseline 扩展实验
- 但还不应宣称其适配成熟度已完全等同于 `O-Mem`

---

## 4. MemBox 适配器当前状态

## 4.1 已完成内容

`MemBox` 当前适配器文件为：

- `src/memory_eval/adapters/membox_adapter.py`

它已经支持：

1. build / baseline / eval 复用 build artifact
2. export full memory
3. original retrieval
4. online / oracle generation

## 4.2 为什么之前会出现 `enc.MISS = 199`

经过重新审查，当前更合理的结论是：

- **这不太像系统本身 199 题全没记住**
- 更像是 adapter 导出的 memory view 不完整

具体来说：

1. 原系统不仅输出 `final_content.jsonl`
2. 还输出 `time_traces.jsonl`
3. `time_traces.jsonl` 中包含很多 probe 真正需要的事件链级事实
4. 但此前 adapter 只导出了 box 级聚合文本，没有导出 trace 级事件链

因此编码探针看到的是：

- box 级长文本

却看不到：

- trace 级原子事件链

于是很多本来“系统有保存”的事实，被误判成 `MISS/EM`。

## 4.3 当前怎么修的

本轮在 `membox_adapter.py` 中已经补了：

1. `export_full_memory()` 同时导出：
   - `box-*`
   - `trace-*`
2. `find_memory_records()` 新增对以下字段的匹配：
   - `entries_text`
   - `events`

这意味着当前编码探针在 `MemBox` 上看到的 memory corpus，已经更接近系统真实保留的事件层记忆。

## 4.4 当前结论

`MemBox` 当前已经进入：

- **接口修正后，应重新跑 eval 进行验证**

因此，当前最重要的不是继续猜，而是：

1. 用新 adapter 重跑 `MemBox eval`
2. 观察 `enc.MISS = 199` 是否显著下降

---

## 5. 当前适合纳入 baseline 的系统

从当前 `system/` 目录与环境状态来看，最适合纳入 baseline 的系统分为三档。

## 5.1 第一档：已稳定

1. `O-Mem-StableEval`
2. `Membox_stableEval`

原因：

1. 已有稳定 baseline / eval 结果
2. 已经接入当前评估框架
3. 结果可直接用于论文主实验

## 5.2 第二档：可进入扩展 baseline

1. `general-agentic-memory-main`

原因：

1. 原系统 baseline 已经能实际运行
2. 当前项目里 `GAMAdapter` 第一版已接入
3. 其 research 代码直接暴露：
   - `MemoryAgent`
   - `ResearchAgent`
   - `Retriever`
4. 很适合用来扩展对比实验

## 5.3 第三档：建议作为下一批候选，但暂不直接纳入

### `MemoryOS`

这是当前我额外最推荐关注的候选系统。

原因：

1. README 明确给出了：
   - short-term
   - mid-term
   - long-term
   - retriever
   - updater
   - generation
2. 架构清晰，概念层次非常适合与你的三层 probe 对齐
3. 自带 `eval/` 目录，且项目文档对 LoCoMo reproduction 有明确指向
4. 总体代码形态比 `EverOS/TiMem/MemOS` 更像“可被适配器直接调用的 Python memory library”

因此，`MemoryOS` 很适合成为：

- **下一批 baseline 候选中的优先级最高者**

---

## 6. 当前不建议作为 baseline 的系统

## 6.1 EverOS

问题不是环境，而是：

1. 模型/抽取链路还不稳定
2. `atomic_fact` 抽取为空的问题尚未彻底解决

## 6.2 TiMem

主要阻塞：

1. Docker / 数据服务依赖较重
2. 更适合在环境稳定后再做 build/eval 分离接入

## 6.3 MemOS

主要阻塞：

1. 本地 API 配置链路仍不稳定
2. 当前不适合作为主 baseline 候选

---

## 7. README 应当传达的当前状态

对于仓库 README，当前最重要的状态信息应当是：

1. 主稳定系统：
   - `o_mem_stable_eval`
   - `membox_stable_eval`
2. 实验性已接入系统：
   - `gam_stable_eval`
3. 当前最推荐的新增 baseline 候选：
   - `MemoryOS`

同时要强调：

1. `MemBox` 新版本已补 `time_traces` 进入 memory export
2. `judge` 已经回调到更接近 TiMem 风格

---

## 8. 一句话总结

当前项目中：

1. `O-Mem` 与 `MemBox` 仍是最稳定的 baseline 主系统
2. `GAM` 已进入可评估的扩展系统阶段
3. `MemBox` 的 `enc.MISS = 199` 更像是 adapter memory export 漏导 trace，而非系统本身完全失忆
4. `MemoryOS` 是当前最值得作为下一批 baseline 候选继续接入的系统
