# 项目总说明与运行指南（v0.1）

## 1. 项目是什么

本项目是一个面向长时记忆系统的统一评估框架，核心目标不是只给出最终准确率，而是把记忆系统的表现拆解成：

1. `baseline`
   - 黑盒最终表现
2. `eval`
   - 三层探针诊断

评估框架的设计核心是：

1. 评估逻辑属于框架自身
2. 不同记忆系统通过 adapter 接入
3. 所有系统都尽量被映射到统一的：
   - ingest
   - memory export
   - retrieval
   - online/oracle generation

***

## 2. 当前项目结构怎么理解

最重要的目录如下：

### `src/memory_eval/`

这是评估框架本体，包含：

1. `dataset/`
   - 构建 LoCoMo 样本
2. `eval_core/`
   - encoding / retrieval / generation / attribution / judge
3. `adapters/`
   - 各记忆系统接入层
4. `pipeline/`
   - baseline / eval 主流程

### `system/`

这是第三方记忆系统源码目录。

当前重点系统包括：

1. `O-Mem-StableEval`
2. `Membox_stableEval`
3. `general-agentic-memory-main`
4. `EverOS-main`
5. `timem-main`
6. `MemOS-main`
7. `MemoryOS`

### `scripts/run_real_memory_eval.py`

这是当前最推荐的统一入口。

你做实际 baseline / eval 时，优先用这个脚本。

***

## 3. 当前哪些系统已经完成

## 3.1 已稳定完成

以下两个系统已经完成了当前项目里的主要 baseline/eval 接入与结果落盘：

1. `o_mem_stable_eval`
2. `membox_stable_eval`

这两个系统当前是：

- **最推荐的主 baseline 系统**

## 3.2 已进入实验性接入

1. `gam_stable_eval`

它当前状态是：

1. 原系统 baseline 已能运行
2. 评估框架 adapter 第一版已接入
3. 可以开始进行扩展 baseline/eval
4. 但稳定性与成熟度还不应宣称与 `O-Mem` 完全等价

## 3.3 当前不建议直接用作主 baseline

1. `EverOS-main`
2. `timem-main`
3. `MemOS-main`

原因分别是：

1. `EverOS`
   - 抽取链路和模型适配仍不稳定
2. `TiMem`
   - 受 Docker / 数据服务阻塞
3. `MemOS`
   - 本地 API 配置链路仍不稳定

***

## 4. 当前 adapter 状态

## 4.1 已稳定 adapter

1. `OMemAdapter`
2. `MemboxAdapter`

## 4.2 已接入的实验性 adapter

1. `GAMAdapter`
2. `MemOSAdapter`

其中：

### `GAMAdapter`

已实现：

1. `ingest_conversation`
2. `export_full_memory`
3. `find_memory_records`
4. `retrieve_original`
5. `generate_online_answer`
6. `generate_oracle_answer`
7. `build_trace_for_query`

### `MemboxAdapter`

已实现：

1. build artifact 复用
2. full memory export
3. original retrieval
4. online/oracle generation
5. `time_traces` 纳入 memory export

***

## 5. judge 当前口径

当前 `llm-as-judge` 已经回调到更接近 TiMem 附录风格的宽松语义判分。

主要特点：

1. 核心事实一致即可判对
2. 时间问题只要指向同一日期/月份/年份/相对时间即可判对
3. 回答更长、口语化、轻度保守，不会仅因措辞问题直接判错
4. `NEG` 题仍重点看是否谨慎回答、是否编造

对应代码：

1. `src/memory_eval/eval_core/prompts.py`
2. `src/memory_eval/eval_core/correctness_judge.py`

***

## 6. 已完成系统如何启动

## 6.1 O-Mem

### baseline

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py --memory-system o_mem_stable_eval --mode baseline --dataset data/locomo10.json --sample-id conv-26 --limit 10 --keys-path configs/keys.local.json --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B --output outputs/o_mem_conv26_baseline.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_o_mem_conv26_baseline.log 2>&1 &



nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py --memory-system o_mem_stable_eval --mode baseline --dataset data/locomo10.json  --keys-path configs/keys.local.json --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B --output outputs/omem_conv26_baseline_0415_all.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_omem_conv26_baseline_0415_all.log 2>&1 &
```

### eval

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py --memory-system o_mem_stable_eval --mode eval --dataset data/locomo10.json --sample-id conv-26 --limit 10 --keys-path configs/keys.local.json --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B --output outputs/o_mem_conv26_eval.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_o_mem_conv26_eval.log 2>&1 &

nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py --memory-system o_mem_stable_eval --mode eval --dataset data/locomo10.json --keys-path configs/keys.local.json --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B --output outputs/omem_conv26_eval_0415_all.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_omem_conv26_eval_0415_all.log 2>&1 &
```

## 6.2 MemBox

### build

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode build --dataset data/locomo10.json --sample-id conv-26 --keys-path configs/keys.local.json --request-timeout-sec 120 --output outputs/membox_conv26_build_manifest.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_build.log 2>&1 &

nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode build --dataset data/locomo10.json --sample-id conv-26 --keys-path configs/keys.local.json --request-timeout-sec 120 --output outputs/membox_conv26_build_manifest_0415.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_build_0415.log 2>&1 &
```

### baseline

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode baseline --dataset data/locomo10.json --sample-id conv-26 --build-manifest outputs/membox_conv26_build_manifest.json --keys-path configs/keys.local.json --request-timeout-sec 120 --output outputs/membox_conv26_baseline.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_baseline.log 2>&1 &


nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode baseline --dataset data/locomo10.json --sample-id conv-26 --build-manifest outputs/membox_conv26_build_manifest_0415.json --keys-path configs/keys.local.json --request-timeout-sec 500 --output outputs/membox_conv26_baseline_0415.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_baseline_0415.log 2>&1 &

```

### eval

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode eval --dataset data/locomo10.json --sample-id conv-26 --limit 10 --build-manifest outputs/membox_conv26_build_manifest.json --keys-path configs/keys.local.json --request-timeout-sec 120 --output outputs/membox_conv26_eval.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_eval.log 2>&1 &


nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py --memory-system membox_stable_eval --mode eval --dataset data/locomo10.json --sample-id conv-26 --limit 10 --build-manifest outputs/membox_conv26_build_manifest_0415.json --keys-path configs/keys.local.json --request-timeout-sec 120 --output outputs/membox_conv26_eval_0415.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_membox_conv26_eval_0415.log 2>&1 &
```

## 6.3 GAM（实验性）

### baseline

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && python scripts/run_real_memory_eval.py --memory-system gam_stable_eval --dataset data/locomo10.json --sample-id conv-26 --mode baseline --keys-path configs/keys.local.json --top-k 10 --output outputs/gam_conv26_baseline.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_gam_conv26_baseline.log 2>&1 &


nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && python scripts/run_real_memory_eval.py --memory-system gam_stable_eval --dataset data/locomo10.json --sample-id conv-26 --mode baseline --keys-path configs/keys.local.json --top-k 10 --output outputs/gam_conv26_baseline_0415.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_gam_conv26_baseline_0415.log 2>&1 &
```

### eval

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && python scripts/run_real_memory_eval.py --memory-system gam_stable_eval --dataset data/locomo10.json --sample-id conv-26 --mode eval --keys-path configs/keys.local.json --top-k 10 --output outputs/gam_conv26_eval.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_gam_conv26_eval.log 2>&1 &


nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && python scripts/run_real_memory_eval.py --memory-system gam_stable_eval --dataset data/locomo10.json --sample-id conv-26 --mode eval --keys-path configs/keys.local.json --top-k 10 --output outputs/gam_conv26_eval_0415.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_gam_conv26_eval_0415.log 2>&1 &
```

***

## 7. 跑完后怎么检查

### O-Mem / MemBox / GAM 通用

看日志尾部：

```bash
tail -n 80 outputs/nohup_o_mem_conv26_baseline.log
tail -n 80 outputs/nohup_o_mem_conv26_eval.log
tail -n 80 outputs/nohup_membox_conv26_build.log
tail -n 80 outputs/nohup_membox_conv26_baseline.log
tail -n 80 outputs/nohup_membox_conv26_eval.log
tail -n 80 outputs/nohup_gam_conv26_baseline.log
tail -n 80 outputs/nohup_gam_conv26_eval.log
```

### baseline 重点看

1. `summary.final_accuracy`
2. `results[*].answer_online`
3. `results[*].judge_label`
4. `results[*].judge_reason`

### eval 重点看

1. `summary.final_accuracy`
2. `summary.pos_final_accuracy`
3. `summary.neg_final_accuracy`
4. `state_counts`
5. `defect_counts`
6. `probe_results`
7. `attribution`

***

## 8. 当前最推荐的 baseline 组合

如果你现在要做论文主实验或稳定对比，建议优先顺序是：

1. `o_mem_stable_eval`
2. `membox_stable_eval`
3. `gam_stable_eval`

其中：

1. `O-Mem`
   - 当前最稳
2. `MemBox`
   - 当前已修复 memory export 观察层问题，值得重新跑
3. `GAM`
   - 已进入可评估状态，但仍属扩展系统

***

## 9. 下一批 baseline 候选

当前我最推荐继续接入的是：

- `MemoryOS`

原因：

1. 架构清晰
2. retrieval / updater / generation 边界明确
3. 比 `EverOS/TiMem/MemOS` 更适合做 Python 级 adapter 接入

***

## 10. 一句话总结

当前项目已经形成：

1. 两个稳定主 baseline 系统：
   - `O-Mem`
   - `MemBox`
2. 一个实验性扩展系统：
   - `GAM`
3. 一套已经可实际运行的统一 baseline/eval 入口：
   - `scripts/run_real_memory_eval.py`

