# O-Mem 在 `locomo10.json` 上的复现与严格归因报告

**文档性质**：运行方法、参数说明、结果记录与分析报告。  
**当前状态**：方法与设置已确认；长任务结果仍在生成中，结果节待补齐。  
**运行环境**：`omem-paper100`

---

## 1. 目标

本报告分两部分：

1. **O-Mem 本体复现**
   - 在 `data/locomo10.json` 上运行 O-Mem 原生在线问答链路。
   - 不掺入三探针归因逻辑，只看原系统 `A_online` 的效果。

2. **严格归因评测**
   - 使用 O-Mem 适配器接入三探针框架。
   - 在 strict LLM-only 模式下，对 `locomo10.json` 的首个样本先做真实归因。

---

## 2. 本次使用的入口与产物

### 2.1 O-Mem baseline-only 复现

入口脚本：

- `scripts/run_omem_two_stage_eval.py`

本次实际命令语义：

- `--baseline-only`
- `--dataset data/locomo10.json`
- `--limit-questions 100`
- `--correct-sample-count 0`
- `--top-k 5`
- `--retrieval-pieces 15`
- `--retrieval-drop-threshold 0.1`
- `--working-memory-max-size 20`
- `--episodic-memory-refresh-rate 5`
- `--omem-root system/O-Mem-StableEval`

目标输出文件：

- `outputs/omem_locomo10_baseline_only.json`

运行中的 memory cache 实际落盘路径：

- `/home/4T/liuzeyu/outputs/omem_locomo10_baseline_memory`

说明：

- 该脚本已新增 `--baseline-only`，用于先复现 O-Mem 本体效果，再单独做归因。
- 当前 `memory_dir` 的解析是相对当前 shell 工作目录的，因此本次 cache 实际写到了 `/home/4T/liuzeyu/outputs/` 下，而不是项目内 `outputs/`。

### 2.2 单样本严格归因

入口脚本：

- `scripts/run_omem_stable_smoke_once.py`

本次实际样本：

- `sample_id = conv-26`
- `question_index = 0`
- `question_id = conv-26:0`
- `question = "When did Caroline go to the LGBTQ support group?"`

目标输出文件：

- `outputs/omem_strict_attr_conv26_q0.json`

运行中的 memory cache 实际落盘路径：

- `/home/4T/liuzeyu/outputs/omem_strict_attr_conv26_q0_memory`

---

## 3. O-Mem 运行参数说明

本次 O-Mem 运行超参数来自两处：

1. `src/memory_eval/adapters/o_mem_adapter.py` 中的 `OMemAdapterConfig`
2. 调用脚本显式传入的 CLI 参数

### 3.1 本次实际使用值

| 参数 | 值 | 来源 |
|------|----|------|
| `llm_model` | `gpt-4o-mini` | 脚本参数 / `keys.local.json` |
| `embedding_model_name` | `Qwen/Qwen3-Embedding-0.6B` | 脚本参数 |
| `retrieval_pieces` | `15` | 显式传参 |
| `retrieval_drop_threshold` | `0.1` | 显式传参 |
| `working_memory_max_size` | `20` | 显式传参 |
| `episodic_memory_refresh_rate` | `5` | 显式传参 |
| `async_call_timeout_sec` | `180` | smoke 脚本中固定 |
| `use_real_omem` | `true` | 显式传参 |
| `allow_fallback_lightweight` | `false` | 显式传参 |
| `omem_root` | `system/O-Mem-StableEval` | 显式传参 |

### 3.2 与 O-Mem 原始脚本默认值的关系

从 `system/O-Mem-StableEval/locomo_experiment_retrieval_optimize_ablation_study.py` 可见：

- `working_memory_max_size` 默认 `20`
- `episodic_memory_refresh_rate` 默认 `5`
- `number_of_retrieval_pieces` 默认 `10`
- `drop_threshold` 默认 `0.1`

本次适配器/运行脚本中唯一显著不同的是：

- `retrieval_pieces = 15`

这也是当前仓库 runbook 中推荐的稳定值。  
适配器内部还做了一个安全约束：

- `number_of_retrieval_pieces = max(10, retrieval_pieces)`

所以只要传值不小于 `10`，不会触发额外缩放。

---

## 4. 三探针严格评测配置

本次 strict profile 使用：

| 配置项 | 值 |
|------|----|
| `use_llm_assist` | `true` |
| `require_llm_judgement` | `true` |
| `disable_rule_fallback` | `true` |
| `strict_adapter_call` | `true` |
| `require_online_answer` | `true` |
| `tau_rank` | `5` |
| `tau_snr` | `0.2` |
| `neg_noise_score_threshold` | `0.15` |
| `encoding_merge_native_retrieval` | `true` |
| `encoding_native_retrieval_top_k` | `20` |

此外，本轮还补了两点实现收紧：

1. **检索 probe**
   - 将 `rank_index`、`hit_indices`、`snr` 作为辅助诊断量显式传给 retrieval LLM probe。
   - strict 下它们只作为 LLM 输入和 attrs，不再直接决定最终缺陷。

2. **生成 probe**
   - strict 下 NEG 样本的 `GH` 也要求由 LLM 合法输出支撑，不能仅靠规则直接给出。

---

## 5. 运行环境与当前性能解释

### 5.1 环境

- Conda 环境：`omem-paper100`
- Python：`3.10`
- O-Mem runtime：`system/O-Mem-StableEval`

### 5.2 GPU 现状

当前机器上 `nvidia-smi` 可以看到多张 `Tesla V100-SXM2-32GB`，但在 `omem-paper100` 中：

- `torch.cuda.device_count() == 8`
- `torch.cuda.is_available() == False`

直接原因是：

- 当前 PyTorch / CUDA 构建与机器上的 NVIDIA driver 版本不匹配
- `torch` 报错：driver too old

这意味着本次 O-Mem 实际运行走的是 **CPU 路径**。  
因此：

- 复现速度会显著慢于可用 GPU 的历史运行
- 单样本 strict smoke 都会花较长时间
- 这不会改变三探针逻辑定义，但会显著影响吞吐

---

## 6. 当前运行状态

### 6.1 Baseline-only 复现

状态：

- 已启动
- 已成功创建 `conv-26` 的真实 O-Mem memory cache
- 最终 JSON 结果仍在等待落盘

当前已观察到的 cache 文件示例：

- `user_working_memory_0.json`
- `agent_working_memory_0.json`
- `user_topic_episodic_memory_0.json`
- `agent_topic_episodic_memory_0.json`
- `user_attribute_episodic_memory_0.json`
- `agent_attribute_episodic_memory_0.json`

### 6.2 单样本严格归因

状态：

- 已启动
- 已成功创建 `conv-26` 的真实 O-Mem memory cache
- 最终 JSON 结果仍在等待落盘

---

## 7. 结果记录（待任务完成后补齐）

### 7.1 O-Mem baseline-only

待补：

- `total_questions`
- `correct`
- `incorrect`
- `accuracy`
- 分 category 统计
- 与图中 O-Mem / Ours 的相对位置说明

### 7.2 `conv-26:0` 严格归因

待补：

- `enc / ret / gen` 三层状态
- 最终缺陷集合
- probe 级证据
- 与历史非严格 smoke 的差异

---

## 8. 风险与解释边界

1. `locomo10.json` 是小规模切片，不等于论文中的完整 LoCoMo 评测集，因此结果只能作为**当前实现状态的实测复现**，不能直接等价替代论文表格。
2. 当前 `omem-paper100` 中 `torch` 无法启用 CUDA，会显著放慢 O-Mem。
3. 本轮 baseline-only 与 strict attribution 是分开跑的，这是有意设计：
   - 先复现 O-Mem 本体
   - 再跑归因框架
   这样能避免把“系统本体效果”和“归因框架解释”混成一个结论。

---

## 9. 后续补充项

待当前长任务结束后，本报告将补充：

1. baseline-only 的真实结果摘要
2. `conv-26:0` 严格归因 JSON 解析
3. 对当前 O-Mem 配置是否偏离仓库默认稳定配置的结论
4. 是否需要进一步修复 GPU/driver 对齐来提升吞吐
