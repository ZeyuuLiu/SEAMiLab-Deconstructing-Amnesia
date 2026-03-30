# Membox_stableEval 修复说明文档

> 日期: 2026-03-29  
> 目标: 在保留原论文记忆系统方法的前提下，修复 Membox 使其能够运行 baseline 以及三探针归因评测

---

## 1. 背景

`system/Membox` 是原始论文的记忆系统实现。在实际运行中发现了一个**路径配置 bug** 导致程序崩溃，无法完成 Trace 阶段。

为了保护原始代码不被修改，我们创建了 `system/Membox_stableEval` 作为稳定评测副本。**只在此副本中进行最小必要修复**，不改动任何记忆系统的核心算法逻辑。

---

## 2. Bug 分析

### 2.1 错误现象

运行 Membox baseline 或 evaluation 时，在 `TraceLinker.run()` 阶段抛出:

```
FileNotFoundError: [Errno 2] No such file or directory: ''
```

### 2.2 根因定位

`Membox/membox.py` 中的 `Config` 类在初始化时定义了多个输出路径：

```python
class Config:
    OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, "default")
    TRACE_STATS_FILE = os.path.join(OUTPUT_DIR, "trace_stats.jsonl")  # 初始值
    BUILD_STATS_FILE = os.path.join(OUTPUT_DIR, "build_stats.jsonl")
    # ... 其他路径
```

当通过 `Config.apply_run_id(run_id)` 切换到实际运行目录时，该方法更新了几乎所有路径变量，**唯独遗漏了 `TRACE_STATS_FILE`**：

```python
@classmethod
def apply_run_id(cls, run_id):
    cls.OUTPUT_DIR = os.path.join(cls.OUTPUT_BASE_DIR, rid)
    cls.FINAL_CONTENT_FILE = os.path.join(cls.OUTPUT_DIR, ...)
    cls.BUILD_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, ...)
    cls.TIME_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, ...)
    cls.TRACE_PROMPT_LOG_FILE = os.path.join(cls.OUTPUT_DIR, ...)
    # ❌ 缺少: cls.TRACE_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "trace_stats.jsonl")
    cls.BUILD_STATS_FILE = os.path.join(cls.OUTPUT_DIR, ...)
    cls.GEN_SUMMARY_FILE = os.path.join(cls.OUTPUT_DIR, ...)
```

因此 `TRACE_STATS_FILE` 仍保留初始值（依赖初始 `OUTPUT_DIR`），当初始 `OUTPUT_DIR` 路径不存在时，`os.makedirs(os.path.dirname(Config.TRACE_STATS_FILE))` 收到空字符串，导致 `FileNotFoundError`。

### 2.3 使用位置

`TRACE_STATS_FILE` 仅在 `TraceLinker.run()` 末尾使用：

```python
os.makedirs(os.path.dirname(Config.TRACE_STATS_FILE), exist_ok=True)
# 追加写入 trace 统计 JSON
```

---

## 3. 修复方案

### 3.1 唯一修改点

在 `Membox_stableEval/membox.py` 的 `Config.apply_run_id()` 方法中，添加一行：

```python
cls.TRACE_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "trace_stats.jsonl")
```

位置在 `cls.TRACE_PROMPT_LOG_FILE` 之后、`cls.BUILD_STATS_FILE` 之前。

### 3.2 修改对原论文方法的影响

| 维度 | 影响 |
|------|------|
| 记忆构建算法 (MemoryBuilder) | **无影响** — 不涉及 |
| Trace 链接算法 (TraceLinker) | **无影响** — 仅修复了输出文件的路径，算法逻辑完全未改 |
| 检索算法 (SimpleRetriever) | **无影响** — 不涉及 |
| 答案生成算法 (AnswerGenerator) | **无影响** — 不涉及 |
| LLM 调用参数/Prompt | **无影响** — 无任何 prompt 或模型参数变更 |
| 超参数 | **无影响** — 未修改任何 Config 中的数值参数 |

**结论：该修复仅为路径配置 bug 的一行 fix，完全不改变论文记忆系统的任何方法或行为。**

### 3.3 Diff 确认

```diff
--- system/Membox/membox.py
+++ system/Membox_stableEval/membox.py
@@ -280,6 +280,7 @@
         cls.BUILD_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, "trace_build_process.jsonl")
         cls.TIME_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, "time_traces.jsonl")
         cls.TRACE_PROMPT_LOG_FILE = os.path.join(cls.OUTPUT_DIR, "trace_prompts.jsonl")
+        cls.TRACE_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "trace_stats.jsonl")
         cls.BUILD_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "build_stats.jsonl")
         cls.GEN_SUMMARY_FILE = os.path.join(cls.OUTPUT_DIR, "generation_metrics_summary.jsonl")
         os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
```

---

## 4. Membox 系统流水线概览

| 阶段 | 组件 | 功能 |
|------|------|------|
| **build** | `MemoryBuilder` | 读取原始对话，拆分为记忆 box，调用 LLM 提取主题/关键词/事件 |
| **trace** | `TraceLinker` | 读取 box，用嵌入相似度 + LLM 筛选，将事件聚类为 trace |
| **retrieve** | `SimpleRetriever` | 对 QA 问题，用嵌入余弦相似度从 box 中排序检索 |
| **generate** | `AnswerGenerator` | 用 top-N box 内容 + trace 增强构建上下文，调用 LLM 生成答案 |

所有 LLM 调用通过 `LLMWorker`（OpenAI SDK），受 `Config.API_KEY`, `Config.BASE_URL`, `Config.LLM_MODEL`, `Config.EMBEDDING_MODEL` 控制。

---

## 5. 如何运行

### 5.1 Baseline（单 sample 验证）

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia

conda run -n omem-paper100 python scripts/run_membox_baseline_once.py \
    --sample-id conv-26 \
    --question-index 0 \
    --membox-root system/Membox_stableEval \
    --output outputs/membox_stableeval_baseline_conv26_q0.json \
    --memory-dir outputs/membox_stableeval_baseline_conv26_q0_memory
```

### 5.2 三探针归因（单 sample 验证）

```bash
conda run -n omem-paper100 python scripts/run_membox_eval_smoke_once.py \
    --sample-id conv-26 \
    --question-index 0 \
    --membox-root system/Membox_stableEval \
    --output outputs/membox_stableeval_eval_conv26_q0.json \
    --memory-dir outputs/membox_stableeval_eval_conv26_q0_memory
```

---

## 6. 后续计划

1. 验证上述单问题 baseline 和 eval 能跑通
2. 扩展 Membox 相关脚本支持全 sample 多问题模式（类似 O-Mem 的 `run_omem_locomo10_baseline.py`）
3. 在 locomo10 sample0 上跑 Membox 全量 baseline 和三探针归因
