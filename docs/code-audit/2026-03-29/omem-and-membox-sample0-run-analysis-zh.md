# O-Mem 与 Membox 在 `locomo10.json` sample0 上的运行结果分析

**文档性质**：运行结果与问题分析报告。  
**范围**：本次仅分析 `locomo10.json` 中 `sample0 = conv-26` 的**首个问题**，即 `conv-26:0`，并对照 O-Mem 与 Membox 两个记忆系统当前的运行状态。  
**结论先行**：

- **O-Mem**
  - baseline 成功
  - 严格归因成功
  - 当前已经可以给出完整 probe 结果
- **Membox**
  - baseline 失败
  - 严格归因失败
  - 两条都死在 Membox 内部同一个路径字段 bug 上

---

## 1. 本次分析涉及的产物

### 1.0 粒度说明

本次所有结果都只是：

- `sample0 = conv-26`
- 第 `0` 个问题
- 即 `conv-26:0`

它们**不是**：

- 完整 `conv-26` 的所有问题结果
- 也不是完整 `locomo10.json` 的总体结果

因此，本文结论的含义是：

- 当前系统在 `sample0` 的第一题上的真实运行状态与问题定位

### 1.1 O-Mem

#### baseline

- 结果文件：`outputs/omem_locomo10_sample1_baseline_only.json`
- 日志文件：`outputs/logs/omem_locomo10_sample1_baseline_only.log`

#### strict attribution

- 结果文件：`outputs/omem_strict_attr_conv26_q0.json`
- 日志文件：`outputs/logs/omem_strict_attr_conv26_q0.log`

#### 历史旧结果

- `outputs/omem_stable_smoke_conv30_q0_after_fix.json`

该文件是更早的一次历史结果，不代表本轮 `conv-26:0` 的最终状态，但可作为对照参考。

### 1.2 Membox

#### baseline

- 日志文件：`outputs/logs/membox_baseline_conv26_q0.log`
- **无结果 JSON**

#### strict attribution

- 日志文件：`outputs/logs/membox_eval_conv26_q0.log`
- **无结果 JSON**

---

## 2. O-Mem 结果分析

## 2.1 O-Mem baseline：成功

结果文件 `outputs/omem_locomo10_sample1_baseline_only.json` 显示：

- `total_questions = 1`
- `correct = 1`
- `accuracy = 1.0`

对应的单题为：

- `question_id = conv-26:0`
- `question = When did Caroline go to the LGBTQ support group?`
- `answer_gold = 7 May 2023`
- `answer_online = 7 May 2023`

也就是说，**O-Mem 本体在 sample0 上的在线回答是正确的**。

证据如下：

```50:70:outputs/omem_locomo10_sample1_baseline_only.json
"baseline_summary": {
  "total_questions": 1,
  "correct": 1,
  "incorrect": 0,
  "accuracy": 1.0
},
"baseline_rows": [
  {
    "question_id": "conv-26:0",
    "sample_id": "conv-26",
    "task_type": "POS",
    "question": "When did Caroline go to the LGBTQ support group?",
    "answer_gold": "7 May 2023",
    "answer_online": "7 May 2023",
    "correct": true
  }
]
```

### baseline 的解释

这说明：

1. O-Mem 复现链路本身是通的；
2. GPU 修复后的运行环境已经足够支持 O-Mem 完成 sample0 的真实在线问答；
3. 在这个问题上，O-Mem 不只是“能跑”，而且答对了。

日志最后也正常结束：

```2780:2787:outputs/logs/omem_locomo10_sample1_baseline_only.log
Two-stage O-Mem evaluation finished.
Output: /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/omem_locomo10_sample1_baseline_only.json
Baseline accuracy: 1.0000 (1/1)
Attribution phase skipped (--baseline-only).
```

日志末尾的 `numpy Mean of empty slice` warning 存在，但它**不是致命错误**，因为任务已经成功输出结果。它更像是某个空集合统计时的边角 warning，后续值得清理，但不影响当前 baseline 结论。

---

## 2.2 O-Mem strict attribution：成功

这次最重要的进展是：

- 修完 O-Mem StableEval 内部 `KeyError` 后
- `conv-26:0` 的严格归因已经成功跑出结果

结果文件为：

- `outputs/omem_strict_attr_conv26_q0.json`

最终 probe 状态是：

- `enc = EXIST`
- `ret = HIT`
- `gen = PASS`
- `defects = []`

证据如下：

```94:103:outputs/omem_strict_attr_conv26_q0.json
"attribution_result": {
  "question_id": "conv-26:0",
  "sample_id": "conv-26",
  "task_type": "POS",
  "states": {
    "enc": "EXIST",
    "ret": "HIT",
    "gen": "PASS"
  },
  "defects": [],
```

### probe 级分析

#### 编码层

- 状态：`EXIST`
- 缺陷：无
- 证据：找到了真正对应的记忆条目 `user_episodic-1-2`

```105:130:outputs/omem_strict_attr_conv26_q0.json
"enc": {
  "probe": "enc",
  "state": "EXIST",
  "defects": [],
  "evidence": {
    "candidate_count": 119,
    "matched_candidate_ids": [
      "user_episodic-1-2"
    ],
    "evidence_snippets": [
      "1:56 pm on 8 May, 2023 | Caroline: I went to a LGBTQ support group yesterday and it was so powerful."
    ],
    "llm_encoding_judgement": {
      "encoding_state": "EXIST"
    }
  }
}
```

这说明在当前严格框架下，编码层已经成功判定：

- O-Mem 确实存下了回答此题所需的关键证据
- 且这个判断是基于 `Q + gold evidence + candidate set` 的 LLM probe，而不是规则降级

#### 检索层

- 状态：`HIT`
- 缺陷：无
- 命中位置：`rank_index = 1`
- LLM 明确认为 gold evidence 在第一个检索项中就出现了

```134:228:outputs/omem_strict_attr_conv26_q0.json
"ret": {
  "probe": "ret",
  "state": "HIT",
  "defects": [],
  "evidence": {
    "hit_indices": [1],
    "llm_judgement": {
      "retrieval_state": "HIT",
      "defects": [],
      "matched_ids": ["ctx-0"]
    }
  },
  "attrs": {
    "rank_index": 1,
    "snr": 0.14788732394366197,
    "hit_count": 1
  }
}
```

这里值得特别注意：

- `snr = 0.1478...` 实际上低于默认 `tau_snr = 0.2`
- 但 strict 模式下，`snr` 只是 diagnostics attrs，不再自动补 `NOI`
- LLM 最终判断是 `HIT` 且无缺陷

这正好说明当前严格 probe 设计的目标已经兑现：

- 数学指标仍然保留
- 但最终缺陷由 probe-LLM 自己裁决

#### 生成层

- 状态：`PASS`
- 缺陷：无
- `A_online = 7 May 2023`
- `A_oracle = 7 May 2023`
- `A_gold = 7 May 2023`

```231:272:outputs/omem_strict_attr_conv26_q0.json
"gen": {
  "probe": "gen",
  "state": "PASS",
  "defects": [],
  "evidence": {
    "answer_online": "7 May 2023",
    "answer_oracle": "7 May 2023",
    "answer_gold": "7 May 2023",
    "online_correct": true,
    "oracle_correct": true,
    "comparative_judgement": {
      "online_vs_gold": "EQUAL",
      "oracle_vs_gold": "EQUAL",
      "online_vs_oracle": "EQUAL"
    }
  }
}
```

这意味着：

- 原链路输出正确
- 完美上下文输出也正确
- 没有生成层问题

### O-Mem 这轮的总体结论

在 `conv-26:0` 这个 sample0 单题上，O-Mem 当前表现是：

- 本体答对
- 编码层正确存储
- 检索层正确命中
- 生成层正确回答

也就是说，**这是一个标准的“无缺陷正例”**。

---

## 2.3 O-Mem 历史旧结果与当前结果的对比

更早的历史结果 `outputs/omem_stable_smoke_conv30_q0_after_fix.json` 中，曾出现：

- `enc = MISS`
- `ret = HIT`
- `gen = FAIL`
- `defects = [EM, GRF]`

```98:106:outputs/omem_stable_smoke_conv30_q0_after_fix.json
"states": {
  "enc": "MISS",
  "ret": "HIT",
  "gen": "FAIL"
},
"defects": [
  "EM",
  "GRF"
]
```

而本轮 `conv-26:0` 的结果则是：

- `enc = EXIST`
- `ret = HIT`
- `gen = PASS`
- `defects = []`

这两者不矛盾，主要说明：

1. 不同样本确实会暴露不同层的不同问题；
2. 你当前的严格三探针已经能把“干净正例”和“多缺陷反例”区分开；
3. O-Mem 本体并不是统一好或统一坏，而是 sample-dependent。

---

## 3. Membox 结果分析

## 3.1 Membox baseline：失败

日志文件：

- `outputs/logs/membox_baseline_conv26_q0.log`

没有生成：

- `outputs/membox_baseline_conv26_q0.json`

但这次失败发生得很晚：

- `MemoryBuilder` 已完成
- `TraceLinker` 已完成
- 已经构建出了 `68` 个 boxes
- 已经生成了 `110` 条 traces

日志证据：

```2:8:outputs/logs/membox_baseline_conv26_q0.log
🏗️  [BUILD] Processing 1 Conversations...
   Building Sample 0...
✅ [BUILD] Checkpoint saved: +68 boxes (appended)
ℹ️ Build stats | boxes=68 msgs=419 ...
✅ Trace saved for sample 0 (110 traces)
✅ Trace linking completed. Output -> .../time_traces.jsonl
ℹ️ Trace LLM stats | calls=295 ...
```

真正失败点在这里：

```9:20:outputs/logs/membox_baseline_conv26_q0.log
Traceback (most recent call last):
  File ".../scripts/run_membox_baseline_once.py", line 128, in main
    run_ctx = adapter.ingest_conversation(sample.sample_id, conv)
  File ".../src/memory_eval/adapters/membox_adapter.py", line 70, in ingest_conversation
    linker.run()
  File ".../system/Membox/membox.py", line 1028, in run
    os.makedirs(os.path.dirname(Config.TRACE_STATS_FILE), exist_ok=True)
  File ".../os.py", line 225, in makedirs
    mkdir(name, mode)
FileNotFoundError: [Errno 2] No such file or directory: ''
```

## 3.2 Membox strict eval：失败

严格评测日志：

- `outputs/logs/membox_eval_conv26_q0.log`

同样没有生成：

- `outputs/membox_eval_conv26_q0.json`

而且失败点和 baseline 完全一致：

```9:20:outputs/logs/membox_eval_conv26_q0.log
Traceback (most recent call last):
  File ".../scripts/run_membox_eval_smoke_once.py", line 68, in main
    run_ctx = adapter.ingest_conversation(sample.sample_id, conv)
  File ".../src/memory_eval/adapters/membox_adapter.py", line 70, in ingest_conversation
    linker.run()
  File ".../system/Membox/membox.py", line 1028, in run
    os.makedirs(os.path.dirname(Config.TRACE_STATS_FILE), exist_ok=True)
  File ".../os.py", line 225, in makedirs
    mkdir(name, mode)
FileNotFoundError: [Errno 2] No such file or directory: ''
```

所以这不是：

- baseline 和 strict 分别有不同 bug

而是：

- **Membox 内部同一个路径配置 bug 阻断了两个入口**

---

## 3.3 Membox 的真正根因

根因在 `system/Membox/membox.py` 的 `Config.apply_run_id()`。

类初始定义时有：

```17:37:system/Membox/membox.py
class Config:
    ...
    TRACE_STATS_FILE = os.path.join(OUTPUT_DIR, "trace_stats.jsonl")
```

但在 `apply_run_id()` 里，虽然重写了很多路径：

```269:285:system/Membox/membox.py
def apply_run_id(cls, run_id: str | None):
    ...
    cls.FINAL_CONTENT_FILE = os.path.join(cls.OUTPUT_DIR, "final_boxes_content.jsonl")
    cls.VECTOR_DIR = os.path.join(cls.OUTPUT_DIR, "vector_store")
    cls.SIMPLE_RETRIEVAL_JSONL = os.path.join(cls.OUTPUT_DIR, "simple_retrieval.jsonl")
    cls.SIMPLE_RETRIEVAL_CSV = os.path.join(cls.OUTPUT_DIR, "simple_retrieval.csv")
    cls.GENERATION_RESULT_FILE = os.path.join(cls.OUTPUT_DIR, "generation_results.jsonl")
    cls.GENERATION_REPORT_CSV = os.path.join(cls.OUTPUT_DIR, "report_generation_qa.csv")
    cls.TOKEN_LOG_FILE = os.path.join(cls.OUTPUT_DIR, "token_stream.jsonl")
    cls.BUILD_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, "trace_build_process.jsonl")
    cls.TIME_TRACE_FILE = os.path.join(cls.OUTPUT_DIR, "time_traces.jsonl")
    cls.TRACE_PROMPT_LOG_FILE = os.path.join(cls.OUTPUT_DIR, "trace_prompts.jsonl")
    cls.BUILD_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "build_stats.jsonl")
    cls.GEN_SUMMARY_FILE = os.path.join(cls.OUTPUT_DIR, "generation_metrics_summary.jsonl")
```

它**漏掉了**：

- `TRACE_STATS_FILE`

结果就是：

- `Config.TRACE_STATS_FILE` 仍然停留在类初始阶段的旧值
- 由于初始 `OUTPUT_DIR` 为空串，`TRACE_STATS_FILE` 实际退化成了一个没有目录前缀的相对路径
- 然后 `TraceLinker.run()` 再去做：

```1028:1029:system/Membox/membox.py
os.makedirs(os.path.dirname(Config.TRACE_STATS_FILE), exist_ok=True)
with open(Config.TRACE_STATS_FILE, "a", encoding="utf-8") as f:
```

此时：

- `os.path.dirname(Config.TRACE_STATS_FILE) == ""`

所以 `os.makedirs("")` 直接抛出：

- `FileNotFoundError: [Errno 2] No such file or directory: ''`

这就是 Membox 本轮两个任务都失败的直接原因。

### 为什么这是个很“干净”的 bug

这个 bug 有几个很好的特点：

1. 根因单一
2. 可复现稳定
3. 与三探针评估框架无关
4. 与适配器主逻辑无关
5. 修复面很小，只要补上 `TRACE_STATS_FILE = os.path.join(cls.OUTPUT_DIR, "trace_stats.jsonl")` 即可

也就是说，**Membox 当前的问题不是“系统设计不通”，而是一个配置重写遗漏 bug。**

---

## 4. O-Mem 与 Membox 当前状态对比

| 维度 | O-Mem | Membox |
|------|-------|--------|
| baseline 单样本运行 | 成功 | 失败 |
| strict 单样本评测 | 成功 | 失败 |
| 是否产出 baseline JSON | 是 | 否 |
| 是否产出评测 JSON | 是 | 否 |
| 失败点位置 | 无 | `system/Membox/membox.py` 路径配置 |
| 失败类型 | 无 | 内部 `Config.apply_run_id()` 漏更新 `TRACE_STATS_FILE` |
| 对评测框架影响 | 已可用 | 尚未进入 probe 评测阶段 |

---

## 5. 当前可以得出的结论

## 5.1 O-Mem

当前可以明确说：

- `O-Mem` 已经能够在 `locomo10.json` 的 sample0 上完成真实复现；
- 并且能够在严格三探针框架下完成完整归因；
- 在 `conv-26:0` 这个样本上，结果是一个**完全健康的正例**：
  - `enc=EXIST`
  - `ret=HIT`
  - `gen=PASS`
  - `defects=[]`

## 5.2 Membox

当前可以明确说：

- `Membox` 已经能完成大部分 build/trace 过程；
- 说明它的主体系统不是完全跑不通；
- 但由于 `TRACE_STATS_FILE` 路径 bug，它目前还不能完成 baseline 和 strict eval 的最终落盘；
- 因此你现在**还不能**对 Membox 在 sample0 上的真实效果做最终结论。

---

## 6. 下一步建议

优先级建议如下：

1. 先修 `system/Membox/membox.py` 的 `Config.apply_run_id()`，补上 `TRACE_STATS_FILE`
2. 重新跑：
   - `membox_baseline_conv26_q0`
   - `membox_eval_conv26_q0`
3. 等 Membox 两条都成功产出 JSON 后，再做和 O-Mem 的横向对比分析

如果继续做，我建议下一步就直接修这个 `TRACE_STATS_FILE` 漏更新问题，然后重新跑 Membox 的 sample0 baseline 和 strict eval。
