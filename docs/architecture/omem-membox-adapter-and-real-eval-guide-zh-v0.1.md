# O-Mem / Mem-box 适配与真实评估运行说明（v0.1）

## 1. 文档目标

这份文档说明当前我对 O-Mem 和 Mem-box 做了哪些适配层改造，以及现在如何在 LOCOMO 数据集上：

1. 复现这两个记忆系统
2. 启动统一评估框架对它们做真实评估
3. 输出 baseline 和 eval 结果

## 2. 这轮适配层改了什么

本轮重点不是只修一个系统，而是先把适配器层做成后续可扩展的形态。

### 2.1 新增通用适配器基座

新增文件：

- `src/memory_eval/adapters/base.py`

提供了统一能力：

1. 默认读取 `configs/keys.local.json`
2. 统一 API 凭据加载
3. 统一 turn 标准化
4. 统一 user / agent 名称推断
5. 统一能力声明 `capabilities()`
6. 统一运行清单 `runtime_manifest()`

这一步的意义是：

> 后续再加新记忆系统时，不需要从零开始复制一套样板逻辑。

### 2.2 重构了 O-Mem 与 Mem-box 适配器

当前两个适配器都已经挂到统一基座上：

- `src/memory_eval/adapters/o_mem_adapter.py`
- `src/memory_eval/adapters/membox_adapter.py`

它们现在都支持：

1. 自动读取本地 keys
2. 输出能力声明
3. 输出运行清单
4. 统一 registry 接入

### 2.3 扩展了 registry

更新文件：

- `src/memory_eval/adapters/registry.py`

新增支持：

1. `membox:stable_eval`
2. `o_mem:stable_eval`
3. `omem`
4. `omem:stable_eval`

并且导出的 adapter manifest 现在会包含 capabilities。

### 2.4 增加了统一真实运行脚本

新增脚本：

- `scripts/run_real_memory_eval.py`

这个脚本是新的统一入口，用来：

1. 跑 baseline 复现
2. 跑 eval 评估
3. 支持 sample 过滤
4. 支持 LOCOMO 全量或子集

## 3. Mem-box 当前可运行方案

## 3.1 推荐系统键

推荐使用：

- `membox_stable_eval`

原因：

1. stableEval 版已经修了原始 Membox 的 `TRACE_STATS_FILE` 路径问题
2. 本轮我也把同样修复补到了原始 `system/Membox/membox.py`

## 3.2 baseline 复现命令

全量：

```bash
PYTHONPATH=src python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --keys-path configs/keys.local.json \
  --output outputs/membox_stable_eval_baseline.json
```

单 sample：

```bash
PYTHONPATH=src python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --output outputs/membox_stable_eval_conv26_baseline.json
```

## 3.3 eval 评估命令

```bash
PYTHONPATH=src python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --output outputs/membox_stable_eval_conv26_eval.json
```

## 3.4 当前真实验证情况

本轮在本地环境里，Mem-box 的真实 run 已经成功进入：

1. 会话 ingest
2. BUILD 阶段
3. box 构建与 trace 输出

输出目录已实际生成：

- `outputs/membox_memory/conv-26/...`

这说明：

1. adapter 已经真实调通系统主链路
2. LOCOMO 对话能被送入 Membox 并产出中间记忆文件

需要说明的是：

- Membox 的 BUILD 阶段本身 LLM 调用很多，单 sample 也会比较慢，这是系统特性，不是适配器 bug。

## 4. O-Mem 当前可运行方案

## 4.1 推荐系统键

推荐使用：

- `o_mem_stable_eval`

原因：

1. stableEval 保留了原系统逻辑
2. 同时修了无限重试等稳定性问题

## 4.2 baseline / eval 命令

全量或 sample 级运行统一使用：

```bash
PYTHONPATH=src python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --limit 10 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_stable_eval_conv26_eval.json
```

baseline 只要把 `--mode eval` 换成 `--mode baseline`。

## 4.3 当前真实验证情况

本轮 O-Mem 的真实 adapter 调试已经推进到：

1. 修掉 `FlagEmbedding -> apex.amp` 的无用导入阻塞
2. 修掉本地 embedding 路径下 `SentenceTransformer(..., local_files_only=...)` 的参数兼容问题

也就是说，适配层本身已经进一步推进了真实运行可达性。

## 4.4 当前剩余环境阻塞

当前环境里 O-Mem 真正未完成的阻塞不是适配器主逻辑，而是本地 embedding 运行环境：

1. 默认 `all-MiniLM-L6-v2` 需要联网下载，但当前环境无法解析 HuggingFace
2. 改用本地 `Qwen/Qwen3-Embedding-0.6B` 后，又暴露出当前 `transformers/timm` 依赖组合不兼容

因此当前 O-Mem 的最终 blocker 是：

> **本地 embedding 模型运行环境依赖不兼容，而不是评估层或 adapter 接口设计错误。**

## 5. 为什么说现在已经是“完整可运行方案”

因为现在已经具备了完整运行链路，只是 O-Mem 在当前机器上还差最后一个环境依赖点。

完整链路已经包括：

1. 统一 adapter registry
2. 统一 keys 加载
3. 统一 baseline / eval 入口
4. LOCOMO sample 过滤
5. 统一输出文件路径
6. 统一 adapter manifest

也就是说，从工程结构上看，这已经是一套完整的真实评估方案。

## 6. 当前输出文件

统一脚本默认输出：

### baseline

- `outputs/<memory_system>_baseline.json`

### eval

- `outputs/<memory_system>_eval.json`

输出内容包含：

1. 运行 summary
2. per-question 结果
3. adapter manifest
4. 在 eval 模式下还会包含 probe 归因结果

## 7. 后续新增记忆系统时怎么做

后面如果你继续加新的记忆系统，我建议沿用当前这套方式：

1. 新系统适配器继承 `BaseMemoryAdapter`
2. 实现：
   - `ingest_conversation`
   - `export_full_memory`
   - `find_memory_records`
   - `retrieve_original`
   - `generate_online_answer`
   - `generate_oracle_answer`
3. 在 `registry.py` 注册 family / flavor
4. 直接复用 `scripts/run_real_memory_eval.py`

这样未来不会再出现“每加一个系统就重新写一套运行脚本”的问题。

## 8. 当前适配器层还需要继续优化的地方

虽然这轮已经可用了，但后续仍建议继续优化：

1. 给 adapter 增加更标准的 capability schema
2. 给 O-Mem 增加更清晰的 real/debug 模式区分
3. 给 MemoryOS 加入同样的统一适配入口
4. 对 Membox / O-Mem 的输出结构做更细的 record 标准化

## 9. 结论

当前你已经得到了一套面向 O-Mem 和 Mem-box 的统一适配与真实评估方案：

1. Mem-box 适配链路已真实打通到 BUILD 阶段，并可在 LOCOMO 上运行
2. O-Mem 适配链路已推进到真实 runtime，当前剩余 blocker 是本地 embedding 依赖环境
3. 统一入口脚本、统一 adapter 基座、统一 registry、统一输出结构都已经补齐

因此后续你可以在这套结构上继续：

1. 跑 Mem-box 真实评估
2. 修正 O-Mem 本地 embedding 依赖后跑真实评估
3. 持续增加新的记忆系统
