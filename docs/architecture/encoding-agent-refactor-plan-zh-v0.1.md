# EncodingAgent 后续代码重构方案（v0.1）

## 1. 文档目标

这份文档回答的问题不是“EncodingAgent 应该长什么样”，而是：

> **在当前仓库代码基础上，后续应该如何一步一步重构，才能把 EncodingAgent 方案真正落地。**

这是一份**重构路线图文档**，不是立即实施的改动说明。

目标有四个：

1. 明确当前代码中的最佳切入点
2. 给出最小侵入式重构路径
3. 降低对现有 pipeline / engine / adapter 的破坏风险
4. 为后续实际编码阶段提供施工顺序

## 2. 当前代码现状总结

从当前实现看，编码层能力已经不是空白，而是一个“骨架已在、结构未成型”的状态。

当前已经具备：

1. `EvalSample`
2. `EvaluatorConfig`
3. `evaluate_encoding_probe_with_adapter(...)`
4. `evaluate_encoding_probe(...)`
5. `export_full_memory(...)`
6. `find_memory_records(...)`
7. `hybrid_retrieve_candidates(...)`
8. `ProbeResult`

当前缺失的不是“功能入口”，而是：

1. 没有中间对象
2. 没有观测束对象
3. 没有组合存在性判断框架
4. 没有覆盖率报告
5. 没有正式的 EncodingAgent 结构

所以重构重点不是大拆大建，而是：

> **把当前散落在 `encoding.py` 里的逻辑组织起来。**

## 3. 重构原则

我建议后续重构严格遵循下面七条原则。

### 3.1 原则一：先收敛编码层内部，不先改引擎层

当前 `engine.py` 的职责比较单纯：

1. 并行调度三探针
2. 做轻量归因收敛

如果一开始就改 engine，会导致影响面太大。

因此重构第一阶段应只动编码层内部，把调用入口保持不变。

### 3.2 原则二：先引入中间对象，再升级行为

如果直接往现有 `encoding.py` 里继续堆功能，只会越来越难维护。

更稳妥的做法是先引入：

1. `EvidenceSpec`
2. `MemoryObservation`
3. `MemoryObservationBundle`
4. `CandidateGroup`
5. `EncodingAssessment`

先把“数据结构组织问题”解决，再解决“裁决能力升级问题”。

### 3.3 原则三：对外接口尽量不变

至少在前两个阶段，下面这些接口建议保持不变：

1. `evaluate_encoding_probe_with_adapter(...)`
2. `evaluate_encoding_probe(...)`
3. `ProbeResult`

这样可以保证：

1. `engine.py` 不需要同步大改
2. `pipeline/runner.py` 不需要同步大改
3. 现有脚本测试不至于全部失效

### 3.4 原则四：适配器协议先不扩张

当前 `adapter_protocol.py` 已经具备基本能力：

1. `export_full_memory`
2. `find_memory_records`
3. `hybrid_retrieve_candidates`
4. `retrieve_original`

在第一阶段不建议立刻新增很多 adapter 方法。

更稳妥的做法是：

1. 优先复用现有协议
2. 把新需求先写入 `adapter_manifest` 或可选字段
3. 等编码层内部结构稳定后，再考虑升级协议

### 3.5 原则五：规则路径与严格路径分离

当前代码里 strict path 和 fallback path 仍然混在一起。

后续要做 Agent 化，必须把两种模式拆开：

1. 正式评测路径
2. 调试兼容路径

否则 EncodingAgent 的设计会一直被旧逻辑拖累。

### 3.6 原则六：先可解释，再更智能

编码层最重要的第一步不是做更复杂的 semantic magic，而是保证：

1. 看了哪些观测
2. 为什么判 EXIST/MISS
3. 哪些片段支持
4. 哪些片段反驳
5. 哪些地方不可见

所以早期阶段应优先做证据链质量，而不是追求复杂 LLM trick。

### 3.7 原则七：每一步都应可回滚

每个阶段都要保持：

1. 小步改造
2. 可运行
3. 可测试
4. 可回滚

不能一次性“改成全新架构”，否则风险太高。

## 4. 当前最佳重构切点

我建议把 `encoding.py` 视为当前的核心切点。

### 4.1 第一切点：观测获取逻辑

当前这部分主要集中在：

1. `export_full_memory`
2. `hybrid_retrieve_candidates`
3. `find_memory_records`
4. `retrieve_original` 合并
5. fallback 扫描

问题在于：

1. 这些逻辑耦合在一个函数里
2. 候选来源信息没有被系统保留
3. 观测覆盖率没有被单独建模

所以这部分最适合被抽到：

1. `encoding_observation.py`

### 4.2 第二切点：存在性裁判逻辑

当前 `evaluate_encoding_probe(...)` 同时做了：

1. 候选处理
2. LLM judge
3. 规则 fallback
4. 缺陷映射

这部分最适合被抽到：

1. `encoding_agent.py`

### 4.3 第三切点：结果映射逻辑

当前内部判断直接产出 `ProbeResult`，这让很多信息丢掉了。

所以应该新增：

1. `EncodingAssessment`
2. `EncodingResultMapper`

这样内部可以更丰富，外部仍兼容原接口。

## 5. 推荐目标目录结构

后续如果进入编码阶段，我建议把编码层拆成下面的结构：

1. `src/memory_eval/eval_core/encoding.py`
   - 保留对外兼容入口
2. `src/memory_eval/eval_core/encoding_types.py`
   - 放 dataclass 和 schema
3. `src/memory_eval/eval_core/encoding_observation.py`
   - 负责观测获取与 bundle 构建
4. `src/memory_eval/eval_core/encoding_fusion.py`
   - 负责多源候选融合与组合候选生成
5. `src/memory_eval/eval_core/encoding_agent.py`
   - 负责最终裁决
6. `src/memory_eval/eval_core/encoding_mapper.py`
   - 负责映射到 `ProbeResult`
7. 可选：`src/memory_eval/eval_core/encoding_prompts.py`
   - 负责 LLM prompt/schema 组织

这种拆法的好处是：

1. 每层职责清楚
2. 单元测试容易做
3. 未来改 prompt 不会污染主逻辑
4. 未来引入 AttributionAgent 时更自然

## 6. 分阶段重构路线图

我建议按五个阶段推进。

## 6.1 第一阶段：对象化，不改行为

目标：

1. 引入中间对象
2. 保持功能行为基本不变
3. 不破坏现有入口

### 本阶段新增内容

1. `EvidenceSpec`
2. `MemoryObservation`
3. `MemoryObservationBundle`
4. `EncodingAssessment`

### 本阶段具体动作

1. 在 `encoding_types.py` 中定义 dataclass
2. 在 `encoding.py` 内部新增私有函数：
   - `build_evidence_spec(...)`
   - `build_memory_observation_bundle(...)`
3. 仍然返回原来的 `ProbeResult`

### 本阶段不做的事

1. 不改 `engine.py`
2. 不改 `pipeline/runner.py`
3. 不改 adapter 协议
4. 不大改 llm prompt

### 本阶段收益

1. 先把结构理顺
2. 后续改行为更安全

## 6.2 第二阶段：抽离 ObservationCollector

目标：

1. 把观测获取逻辑从 `encoding.py` 抽出来
2. 正式建立“多源观测束”

### 本阶段具体动作

1. 新建 `encoding_observation.py`
2. 抽离：
   - `export_full_memory`
   - `hybrid_retrieve_candidates`
   - `find_memory_records`
   - `retrieve_original shadow merge`
3. 输出 `MemoryObservationBundle`

### 本阶段要重点新增的能力

1. 候选来源打标
2. coverage report
3. observability notes

### 本阶段收益

1. 编码层第一次真正拥有“我看到了什么”的建模能力

## 6.3 第三阶段：抽离 EncodingAgent

目标：

1. 把存在性裁判从入口函数中抽出来
2. 形成明确的 Agent 核心

### 本阶段具体动作

1. 新建 `encoding_agent.py`
2. 引入：
   - `EvidenceNormalizer`
   - `CandidateFusionEngine`
   - `ExistenceJudge`
   - `EvidenceCompressor`
3. 输出 `EncodingAssessment`

### 本阶段关键能力

1. 组合候选
2. 多来源综合判断
3. 更丰富的证据链

### 本阶段收益

1. 编码层真正完成从 probe function 到 agent core 的转变

## 6.4 第四阶段：严格路径与调试路径分离

目标：

1. 把正式评测路径和 fallback 路径明确拆开

### 本阶段具体动作

1. 在 `EvaluatorConfig` 或专门 config 中明确 profile
2. 将 `strict llm path` 与 `debug fallback path` 分支独立
3. 对外文档明确：
   - 什么配置用于正式报告
   - 什么配置只用于开发调试

### 本阶段收益

1. 避免未来行为越来越混乱
2. 保证实验结论稳定

## 6.5 第五阶段：与 AttributionAgent 对齐

目标：

1. 让编码层输出天然适配最终归因层

### 本阶段具体动作

1. 在 `ProbeResult.evidence` 中加入标准字段：
   - `coverage_report`
   - `matched_ids`
   - `supporting_snippets`
   - `contradicting_snippets`
   - `risk_flags`
2. 定义供 AttributionAgent 直接消费的摘要结构

### 本阶段收益

1. 后续做最终归因 Agent 时，不需要回头重构编码层输出

## 7. 详细施工顺序

如果后面真正开始改代码，我建议按下面这个顺序实施。

### Step 1

新增 `encoding_types.py`

只做 dataclass，不改逻辑。

### Step 2

在 `encoding.py` 内部引入 `EvidenceSpec` 和 `MemoryObservationBundle`，但先仍然沿用现有流程。

### Step 3

把观测采集逻辑迁移到 `encoding_observation.py`。

### Step 4

把存在性判定迁移到 `encoding_agent.py`。

### Step 5

引入 `EncodingAssessment`，再统一映射到 `ProbeResult`。

### Step 6

为组合候选和 coverage report 加测试。

### Step 7

最后再考虑是否调整 `engine.py`、`AttributionResult` 和最终汇总结构。

## 8. 推荐新增测试

后续改代码时，我建议新增四组测试。

## 8.1 类型与结构测试

测试：

1. `EvidenceSpec` 构建正确
2. `MemoryObservationBundle` 来源标注正确
3. `EncodingAssessment -> ProbeResult` 映射正确

## 8.2 观测覆盖测试

测试：

1. full memory only
2. native candidates only
3. merged observations
4. missing observation path

## 8.3 存在性判定测试

测试：

1. literal exist
2. structured exist
3. semantic exist
4. compositional exist
5. ambiguous corrupt
6. wrong corrupt
7. negative dirty

## 8.4 严格模式测试

测试：

1. LLM 返回非法 JSON
2. observation 缺失
3. adapter 异常
4. fallback 被禁用

## 9. 当前最需要保守处理的风险

这里我认为有五类风险需要特别注意。

### 9.1 风险一：改动面过大

如果一开始就修改：

1. engine
2. pipeline
3. adapters
4. encoding

会让问题失控。

所以第一阶段必须只动 encoding 内部。

### 9.2 风险二：外部接口破坏

如果过早把 `ProbeResult` 替换成全新结构，整个仓库都会受影响。

所以建议：

1. 对内新对象
2. 对外老接口

### 9.3 风险三：适配器协议扩张过快

不同系统适配器已经是复杂点。

如果现在立即强制每个 adapter 提供一堆新方法，会严重增加接入成本。

所以前两阶段应尽量在框架侧完成升级。

### 9.4 风险四：LLM prompt 漂移

如果一边改结构、一边疯狂改 prompt，很难定位问题。

所以重构早期建议：

1. 先稳定对象结构
2. 再逐步升级 prompt 设计

### 9.5 风险五：测试覆盖不足

编码层最难的地方不在 happy path，而在边界样本：

1. 时间格式变化
2. 指代模糊
3. 多条组合
4. NEG 污染

如果没有专项测试，后续很容易“看起来更高级，实则更脆弱”。

## 10. 与当前其他模块的关系

## 10.1 对 engine 的影响

前四个阶段建议不改 engine。

原因：

1. engine 目前只是调度器
2. 编码层 Agent 化不需要先改并发模型

## 10.2 对 retrieval / generation 的影响

第一阶段不改。

但编码层完成后，可以把同样的方法迁移到：

1. RetrievalAgent
2. GenerationAgent

即先完成编码层模板，再推广到其他层。

## 10.3 对 adapter 的影响

前两阶段不强制改协议。

更推荐的做法是：

1. 先利用现有方法构造 bundle
2. 再通过 `adapter_manifest` 扩展描述能力
3. 未来若必要，再扩协议

## 11. 推荐的代码改造优先级

如果你后续真的开始让我动代码，我建议严格按以下优先级：

1. `encoding_types.py`
2. `encoding_observation.py`
3. `encoding_agent.py`
4. `encoding.py` 兼容入口改造
5. 编码层测试
6. `llm_assist.py` 精细化
7. 最后才考虑 engine / attribution 层升级

## 12. 两个可选实施策略

这里我给你两个实施策略。

### 策略 A：保守重构

特点：

1. 小步
2. 风险低
3. 兼容强

做法：

1. 只新增文件
2. 保留现有入口函数
3. 不动 pipeline / engine

适合：

1. 你希望尽快获得一个可用版本
2. 你不想一次性重构太大

### 策略 B：结构重构

特点：

1. 更彻底
2. 后续更优雅
3. 风险更高

做法：

1. 直接把 probe 级函数改成 agent 级类
2. 同步升级 attribution 输出结构
3. 提前为四 Agent 架构铺路

适合：

1. 你准备接受较大改动
2. 你想从编码层开始，逐步升级整个评估层

我的建议是：

> **先走策略 A，等 EncodingAgent 跑稳后再局部向策略 B 过渡。**

## 13. 建议的里程碑

后续实施时，可以按下面四个里程碑推进。

### M1：对象化完成

标志：

1. 新 dataclass 已落地
2. 当前功能未退化

### M2：观测束完成

标志：

1. 编码层输出 coverage report
2. 候选来源可追踪

### M3：EncodingAgent 核心完成

标志：

1. 组合存在性判断完成
2. 内部结果使用 `EncodingAssessment`

### M4：可对接 AttributionAgent

标志：

1. 编码层输出标准化证据链摘要
2. 后续可无缝接最终归因 Agent

## 14. 结论

我的总体建议非常明确：

> **不要把后续工作理解成“继续往 `encoding.py` 里打补丁”，而要把它理解成一次分阶段、可回滚、最小侵入的 Agent 化重构。**

最重要的不是一下子把所有功能都写完，而是先做三件事：

1. 建立中间对象
2. 建立观测束
3. 把裁决和观测拆开

只要这三件事做成，后续：

1. 组合存在性判断
2. 更强的 LLM 裁判
3. AttributionAgent
4. 最终指标聚合

都会变得自然得多。
