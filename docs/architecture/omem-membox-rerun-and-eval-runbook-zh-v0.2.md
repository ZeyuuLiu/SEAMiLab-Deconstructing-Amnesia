# O-Mem / MemBox 重跑复现与评估运行手册（v0.2）

## 1. 文档目标

这份文档用于说明当前仓库代码已经完成哪些关键改造，以及现在应该如何重新跑：

1. O-Mem 的复现与评估
2. MemBox 的复现与评估
3. MemBox 的 build / baseline / eval 分离链路
4. 评估结果的查看方式

这份手册对应当前仓库里已经落地的最新实现，而不是旧版方案说明。

## 2. 当前推荐入口

当前统一入口脚本是：

- `scripts/run_real_memory_eval.py`

它现在支持三种运行模式：

1. `build`
2. `baseline`
3. `eval`

其中：

- O-Mem 主要使用 `baseline` / `eval`
- MemBox 推荐使用 `build -> baseline/eval`

## 3. 当前代码已经落地的关键能力

本次代码层已经真正落地了以下改造：

### 3.1 统一 CorrectnessJudge

baseline 与 generation 层现在共享同一套语义正确性判分逻辑：

1. `rule_correct`
2. `llm_correct`
3. `final_correct`
4. `judge_label`
5. `judge_reason`

其中：

- 最终统计口径看 `final_correct`
- `rule_correct` 仅保留作对账参考

### 3.2 MemBox build / eval 分离

MemBox 适配器现在已经支持：

1. 导出 build artifact
2. 从 build artifact 重建 runtime
3. baseline / eval 复用同一份 build 产物

所以现在推荐流程不再是每次 `eval` 都重新 build，而是：

1. 先 `build`
2. 再 `baseline`
3. 再 `eval`

## 3.3 评估结果三层落盘

`eval` 模式现在会同时生成：

1. 聚合结果文件
2. `run_summary.json`
3. `question_index.json`
4. 每题单独 JSON

如果你输出路径是：

- `outputs/membox_conv26_eval.json`

那么还会额外得到目录：

- `outputs/membox_conv26_eval/`

其中结构类似：

1. `run_summary.json`
2. `question_index.json`
3. `conv-26/<question_id>.json`

这和你要求的 `<run_id>/sample_id/question_id.json` 组织方式一致。

### 3.4 简化最终归因输出

最终归因层现在不再重复三层 probe 的大段 evidence，而是收敛为：

1. `final_attribution`
2. `primary_cause`
3. `secondary_causes`
4. `decision_logic`
5. `final_judgement`

### 3.5 编码层外部高召回检索接口

编码层现在预留了标准高召回接口，后续你自己的 RAG 检索框架可以通过外部 retriever 注入。

当前优先级顺序是：

1. external high-recall retriever
2. adapter native hybrid retrieval
3. adapter find-memory-records
4. rule fallback

## 4. 运行前准备

## 4.1 推荐系统键

建议统一使用 stableEval 变体：

- O-Mem：`o_mem_stable_eval`
- MemBox：`membox_stable_eval`

## 4.2 API 凭据文件

默认读取：

- `configs/keys.local.json`

文件中至少应包含：

1. `api_key`
2. `base_url`
3. 可选 `model`

## 4.3 推荐环境

建议维持一系统一环境：

- `memeval-omem-v1`
- `memeval-membox-v1`

如果你当前实际环境名不同，只需要把下面命令里的环境名替换掉即可。

## 5. O-Mem 重跑方法

## 5.1 O-Mem baseline

前台运行：

```bash
conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_baseline.json
```

后台运行：

```bash
nohup conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_baseline.json \
  > outputs/nohup_o_mem_conv26_baseline.log 2>&1 &
```

## 5.2 O-Mem eval

前台运行：

```bash
conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_eval.json
```

后台运行：

```bash
nohup conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_eval.json \
  > outputs/nohup_o_mem_conv26_eval.log 2>&1 &
```

## 5.3 O-Mem 运行说明

O-Mem 当前不需要额外 build manifest。

原因是：

1. 当前 build / artifact 复用重点是 MemBox
2. O-Mem 本身主要直接走 baseline / eval 即可

## 6. MemBox 重跑方法

## 6.1 第一步：先 build

前台运行：

```bash
conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode build \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_build_manifest.json
```

后台运行：

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode build \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_build_manifest.json \
  > outputs/nohup_membox_conv26_build.log 2>&1 &
```

build 完成后，你会得到：

- `outputs/membox_conv26_build_manifest.json`

这个文件就是后续 baseline / eval 要复用的 build artifact 清单。

## 6.2 第二步：复用 build artifact 跑 baseline

前台运行：

```bash
conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --build-manifest outputs/membox_conv26_build_manifest.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_baseline.json
```

后台运行：

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --build-manifest outputs/membox_conv26_build_manifest.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_baseline.json \
  > outputs/nohup_membox_conv26_baseline.log 2>&1 &
```

## 6.3 第三步：复用 build artifact 跑 eval

前台运行：

```bash
conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --build-manifest outputs/membox_conv26_build_manifest.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_eval.json
```

后台运行：

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --build-manifest outputs/membox_conv26_build_manifest.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_eval.json \
  > outputs/nohup_membox_conv26_eval.log 2>&1 &
```

## 6.4 为什么现在 MemBox 必须这样跑

因为当前代码已经按你确认的方案改成：

1. build 与 eval 分离
2. baseline 与 eval 可复用同一份 build 产物
3. 避免每次 eval 重新 build 一遍
4. 更容易区分到底是 build 慢，还是 eval 某题卡住

## 7. 如何查看运行进度

因为脚本现在增加了逐题心跳输出，所以日志里会出现：

### baseline

1. `baseline_question_start`
2. `baseline_question_done`

### eval

1. `eval_question_start`
2. `eval_question_done`
3. `eval_question_error`

### build

1. `build_done`

查看方式：

```bash
tail -f outputs/nohup_o_mem_conv26_eval.log
```

或：

```bash
tail -f outputs/nohup_membox_conv26_eval.log
```

## 8. 如何看结果文件

## 8.1 baseline 输出

baseline 输出是单个聚合文件，例如：

- `outputs/o_mem_conv26_baseline.json`
- `outputs/membox_conv26_baseline.json`

每题会包含：

1. `answer_online`
2. `rule_correct`
3. `llm_correct`
4. `final_correct`
5. `judge_label`
6. `judge_reason`

## 8.2 eval 输出

如果 eval 输出是：

- `outputs/o_mem_conv26_eval.json`

那么还会附带目录：

- `outputs/o_mem_conv26_eval/`

其中包括：

1. `run_summary.json`
2. `question_index.json`
3. `conv-26/<question_id>.json`

每题 JSON 会包含：

1. 当前问题
2. gold answer
3. online answer
4. oracle answer
5. generation correctness
6. probe states
7. probe defects
8. final attribution
9. decision logic
10. artifact refs

## 9. CLI 参数说明

当前最常用参数如下：

### 通用参数

1. `--memory-system`
2. `--mode`
3. `--dataset`
4. `--sample-id`
5. `--limit`
6. `--output`
7. `--keys-path`

### O-Mem 常用参数

1. `--embedding-model-path`

### MemBox 常用参数

1. `--build-manifest`
2. `--request-timeout-sec`

### CorrectnessJudge 相关参数

1. `--allow-correctness-rule-fallback`

如果不加这个参数，默认会要求 correctness judge 使用 LLM 语义判分。

## 10. 当前推荐重跑顺序

如果你现在要重新完整检查两套系统，我建议按下面顺序：

1. O-Mem baseline
2. O-Mem eval
3. MemBox build
4. MemBox baseline
5. MemBox eval

原因是：

1. O-Mem 不依赖 build manifest，可先快速检查
2. MemBox 先 build 再评估，最符合当前实现

## 11. 已知注意事项

### 11.1 O-Mem

如果 O-Mem 跑不起来，优先排查：

1. embedding 模型路径
2. torch / transformers / flash-attn 兼容性
3. 当前 conda 环境是否是 O-Mem 专属环境

### 11.2 MemBox

如果 MemBox 很慢，先分清：

1. 是 build 阶段慢
2. 还是 baseline / eval 阶段慢

现在由于 build 已分离，不要再把“build 很慢”误判成“eval 卡死”。

## 12. 总结

当前仓库里，O-Mem 与 MemBox 的重跑入口已经统一收敛到同一个脚本：

- `scripts/run_real_memory_eval.py`

最新推荐方式是：

1. O-Mem 直接跑 `baseline` / `eval`
2. MemBox 严格按 `build -> baseline -> eval`
3. baseline 与 generation 统一走 CorrectnessJudge
4. eval 结果按 run summary + question index + per-question JSON 查看

如果你接下来重新跑出新日志或新结果文件，我可以继续直接帮你逐个检查输出是否正常。
