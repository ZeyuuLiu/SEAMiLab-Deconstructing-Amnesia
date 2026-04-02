# O-Mem GPU 运行说明与带日志标准重跑命令

**文档性质**：运行说明与运维规范。  
**范围**：说明如何在服务器上让 O-Mem / 评测任务优先跑到 GPU，以及如何使用 `nohup + 独立日志` 标准化重跑。  
**当前阶段**：文档已根据本轮实际修复结果更新。

---

## 1. 当前问题结论

当前服务器上虽然能看到多张 `Tesla V100-SXM2-32GB`，但最初在 `omem-paper100` 环境里：

```bash
conda run -n omem-paper100 python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.device_count())"
```

最初实际观测结果是：

- `torch.cuda.device_count() == 8`
- `torch.cuda.is_available() == False`

并且 `torch` 给出的关键提示是：

- `The NVIDIA driver on your system is too old`

这意味着：

1. 服务器本身**有 GPU**；
2. 当前 `omem-paper100` 环境中的 **PyTorch / CUDA 构建与服务器驱动版本不兼容**；
3. 因此 O-Mem 当时实际走的是 **CPU 路径**，这就是 ingest 和单样本 strict smoke 很慢的直接原因。

---

## 2. 本轮已经完成的修复

### 2.1 环境修复

`omem-paper100` 中原本是：

- `torch 2.11.0+cu130`

本轮已切换为：

- `torch 2.5.1+cu124`

这是一条与当前服务器驱动更兼容的稳定线。

### 2.2 O-Mem runtime GPU 自举

已新增：

- `system/O-Mem-StableEval/memory_chain/_gpu_runtime.py`
- `system/O-Mem/memory_chain/_gpu_runtime.py`

并在以下入口导入最早阶段调用：

- `system/O-Mem-StableEval/memory_chain/__init__.py`
- `system/O-Mem/memory_chain/__init__.py`

作用：

1. 在 `torch` 导入前优先预加载当前 conda 环境里的 CUDA wheel 动态库；
2. 避免 `libcusparse.so.12` 去错误链接系统里的 `/usr/local/cuda-12.1/lib64/libnvJitLink.so.12`；
3. 让 `memory_chain` 相关运行路径无需手工设置 `LD_LIBRARY_PATH` 就能正常使用 GPU。

### 2.3 适配器与脚本修复

已修改：

- `src/memory_eval/adapters/o_mem_adapter.py`
- `scripts/run_omem_two_stage_eval.py`
- `scripts/run_omem_stable_smoke_once.py`

新增能力：

1. `OMemAdapterConfig` 支持：
   - `device`
   - `auto_select_cuda`
2. 适配器可自动选择**最空闲的 GPU**
3. 如果 embedding 模型路径是本地目录，则自动使用 `local_files_only=True`
4. `SentenceTransformer` 在构造时直接接收目标 `device`，避免默认先落到 `cuda:0` 再 OOM

---

## 3. 修复后验证结果

### 3.1 Torch 验证

已验证：

```bash
2.5.1+cu124
12.4
True
Tesla V100-SXM2-32GB
```

结论：

- `torch.cuda.is_available() == True`
- GPU 已恢复可用

### 3.2 O-Mem runtime 验证

已验证：

- `system/O-Mem-StableEval/memory_chain` 可正常导入
- `scripts/audit_o_mem_adapter.py` 已重新通过

### 3.3 Embedding 落卡验证

已验证以下路径可成功在指定卡加载：

```bash
cuda_available True
device cuda:3
param_device cuda:3
```

### 3.4 自动选卡验证

适配器当前实测自动选卡结果：

```bash
cuda:3
```

这与服务器当前显存占用一致，因为 `GPU 3/4/5` 基本空闲，而 `GPU 0/1` 已高度占用。

---

## 4. 为什么这会直接影响 O-Mem

O-Mem 这条链路的耗时主要来自两部分：

1. **Embedding 编码**
   - `SentenceTransformer(...)`
   - 会对大量文本片段做向量化

2. **LLM-heavy 的记忆写入 / 路由 / 检索 / 回答**
   - `receive_message(...)`
   - `retrieve_from_memory_soft_segmentation(...)`
   - `generate_system_response(...)`

对于 `conv-26` 这种长会话，当前数据规模是：

- `turn_count = 419`
- `qa_count = 199`

所以即便只跑 `conv-26:0` 这一题，也要先完成整段 419-turn 对话的 O-Mem ingest。  
如果 embedding 不能用 GPU，这个成本会明显放大。

---

## 5. 后续切到 GPU 的原则

本项目后续如果要让 O-Mem 跑在服务器 GPU 上，建议遵守以下原则：

### 5.1 先修环境，再排业务逻辑

优先级应该是：

1. **先修环境**
2. 再复验 `torch.cuda.is_available()`
3. 再跑 O-Mem

不建议一边改业务代码一边排 GPU，因为那样很难区分：

- 是环境问题；
- 还是代码逻辑问题；
- 还是 O-Mem 本身耗时。

### 5.2 两类环境级解决方案

#### 方案 A：升级服务器 NVIDIA driver

让服务器 driver 与环境中的 PyTorch/CUDA 构建相匹配。

#### 方案 B：在 `omem-paper100` 中重装与当前 driver 兼容的 PyTorch

保持服务器 driver 不变，只调整 `omem-paper100` 中的 `torch` / CUDA 轮子。

当前本轮已采用并完成的是：

- **方案 B**

---

## 6. GPU 切换前必须做的检查

### 6.1 服务器 GPU 状态

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader
```

### 6.2 环境里的 PyTorch 可见性

```bash
conda run -n omem-paper100 python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.device_count())"
```

### 6.3 O-Mem 适配器审计

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run -n omem-paper100 python scripts/audit_o_mem_adapter.py
```

如果 6.1 到 6.3 任一项失败，不建议直接开始长任务。

---

## 7. GPU 成功启用的验收标准

至少满足：

1. `torch.cuda.is_available() == True`
2. `memory_chain` 可导入
3. `SentenceTransformer(..., device='cuda:X', local_files_only=True)` 能正常落到指定 GPU
4. `scripts/audit_o_mem_adapter.py` 通过

---

## 8. 后续两条任务的标准重跑命令

下面给出的是建议采用的标准命令，特点是：

- 使用 `nohup`
- 使用绝对路径
- 单独写日志
- 单独写 PID 文件
- 结果文件、日志文件、memory cache 路径全部固定
- 明确指定 GPU，避免默认落到高占用卡

假设项目根目录是：

- `/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia`

建议先创建日志目录：

```bash
mkdir -p /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs
```

### 8.1 任务一：O-Mem baseline-only 复现

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run -n omem-paper100 python -u scripts/run_omem_two_stage_eval.py \
  --dataset data/locomo10.json \
  --output outputs/omem_locomo10_baseline_only.json \
  --limit-questions 100 \
  --correct-sample-count 0 \
  --baseline-only \
  --fkey-source rule \
  --top-k 5 \
  --tau-rank 5 \
  --tau-snr 0.2 \
  --neg-noise-threshold 0.15 \
  --max-workers 3 \
  --omem-llm-model gpt-4o-mini \
  --judge-model gpt-4o-mini \
  --eval-llm-model gpt-4o-mini \
  --llm-temperature 0.0 \
  --api-key "$(python - <<'"'"'PY'"'"'
import json
print(json.load(open("configs/keys.local.json", encoding="utf-8-sig"))["api_key"])
PY
)" \
  --base-url "$(python - <<'"'"'PY'"'"'
import json
print(json.load(open("configs/keys.local.json", encoding="utf-8-sig"))["base_url"])
PY
)" \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --memory-dir /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/omem_locomo10_baseline_memory \
  --retrieval-pieces 15 \
  --retrieval-drop-threshold 0.1 \
  --working-memory-max-size 20 \
  --episodic-memory-refresh-rate 5 \
  --omem-root /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/O-Mem-StableEval \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_locomo10_baseline_only.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_locomo10_baseline_only.pid
```

### 8.2 任务二：评估框架对 O-Mem 的单样本严格归因

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run -n omem-paper100 python -u scripts/run_omem_stable_smoke_once.py \
  --sample-id conv-26 \
  --question-index 0 \
  --output outputs/omem_strict_attr_conv26_q0.json \
  --memory-dir /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/omem_strict_attr_conv26_q0_memory \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_strict_attr_conv26_q0.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_strict_attr_conv26_q0.pid
```

如果你希望脚本自动选卡，而不是固定 `cuda:3`，可以去掉 `--device cuda:3`，保留默认行为。

---

## 9. 如何判断任务是否结束、是否成功

### 9.1 看 PID 是否仍存在

```bash
cat /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_strict_attr_conv26_q0.pid
ps -p "$(cat /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_strict_attr_conv26_q0.pid)"
```

### 9.2 看日志最后几行

```bash
tail -n 50 /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_strict_attr_conv26_q0.log
```

### 9.3 看目标 JSON 是否存在

```bash
ls -lh /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/omem_strict_attr_conv26_q0.json
ls -lh /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/omem_locomo10_baseline_only.json
```

判定规则：

- **成功**：进程结束，且目标 JSON 存在
- **失败**：进程结束，但目标 JSON 不存在
- **仍在运行**：进程还在

---

## 10. 当前状态说明

- GPU 与 `memory_chain` 自举链路以仓库内 `system/O-Mem-StableEval` 为准；长任务前建议仍做第 6 节自检。
- **更完整的一键命令见第 11 节**（含 sample0 全题、全量 locomo10、Membox）。

---

## 11. 记忆系统复现与评估：`nohup` 标准命令（自管执行）

以下命令均在**项目根目录**执行。请先：

```bash
export ROOT=/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
mkdir -p "$ROOT/outputs/logs"
cd "$ROOT"
```

说明：

- **`sample0`** 在 `locomo10.json` 中对应 **`sample_id=conv-26`**（该对话约 **199** 道题，不是一题）。
- 脚本会从 `configs/keys.local.json` 读 API；也可自行加 `--api-key` / `--base-url` 覆盖。
- **`--device cuda:X`**：请按 `nvidia-smi` 换一张空闲卡；若希望自动选卡，可去掉 `--device` 行（与适配器默认一致）。
- 使用 **`conda run --no-capture-output`** 可避免日志长时间缓冲不刷新。

### 11.1 O-Mem：sample0 全对话 + **全部问题** baseline（Table 2 风格汇总）

**输出**：`outputs/omem_baseline_conv26_all.json`  
**日志 / PID**：`outputs/logs/omem_baseline_conv26_all.log`、`.pid`  
**记忆缓存**：`outputs/omem_baseline_conv26_all_memory/`

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_omem_locomo10_baseline.py \
  --sample-id conv-26 \
  --output outputs/omem_baseline_conv26_all.json \
  --memory-dir outputs/omem_baseline_conv26_all_memory \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --omem-root /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/O-Mem-StableEval \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_baseline_conv26_all.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_baseline_conv26_all.pid
```

**结束判定**：`ps` 查 PID 已退出，且存在上述 JSON；日志末尾有 `[DONE]` 与 `GLOBAL RESULTS`。

### 11.2 O-Mem：**locomo10 全量**（10 个 sample）baseline 复现

不传 `--sample-id` 即按数据文件顺序处理全部对话（每对话 ingest 一次，再跑该对话全部问题）。

**输出**：`outputs/omem_locomo10_baseline_full.json`

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_omem_locomo10_baseline.py \
  --output outputs/omem_locomo10_baseline_full.json \
  --memory-dir outputs/omem_locomo10_baseline_full_memory \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --omem-root /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/O-Mem-StableEval \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_locomo10_baseline_full.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_locomo10_baseline_full.pid
```

### 11.3 O-Mem：三探针 **严格归因**（sample0 = conv-26，**全部问题**）

每题多次 LLM 调用，耗时会明显长于 baseline；**199 题**建议单独一条任务。

**输出**：`outputs/omem_attr_conv26_all.json`  
**记忆缓存**：`outputs/omem_attr_conv26_all_memory/`

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_omem_sample_attribution.py \
  --sample-id conv-26 \
  --output outputs/omem_attr_conv26_all.json \
  --memory-dir outputs/omem_attr_conv26_all_memory \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --omem-root /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/O-Mem-StableEval \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_attr_conv26_all.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_attr_conv26_all.pid
```

**结束判定**：进程结束且 JSON 存在；`summary.attributed` 接近总题数；`errors` 非空时需打开 JSON 看具体 `question_id`。

### 11.4 O-Mem：旧版「两阶段」脚本（前 N 题 baseline-only / 带抽样归因）

`run_omem_two_stage_eval.py` 按**扁平题序**取前 `limit_questions` 条，**不是**「单 sample 全题」语义。全量约 **1986** 题时请设 `--limit-questions 3000`（或更大）。

**仅 baseline（示例：全量题）**：先在 shell 里读出 key（避免 nohup 里嵌套引号），再启动：

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
export OMEM_API_KEY=$(python3 -c "import json; print(json.load(open('configs/keys.local.json',encoding='utf-8-sig'))['api_key'])")
export OMEM_BASE_URL=$(python3 -c "import json; print(json.load(open('configs/keys.local.json',encoding='utf-8-sig'))['base_url'])")

nohup env OMEM_API_KEY="$OMEM_API_KEY" OMEM_BASE_URL="$OMEM_BASE_URL" bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_omem_two_stage_eval.py \
  --dataset data/locomo10.json \
  --output outputs/omem_two_stage_baseline_full.json \
  --limit-questions 3000 \
  --correct-sample-count 0 \
  --baseline-only \
  --api-key "$OMEM_API_KEY" \
  --base-url "$OMEM_BASE_URL" \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --memory-dir outputs/omem_two_stage_baseline_full_memory \
  --omem-root /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/O-Mem-StableEval \
  --device cuda:3
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_two_stage_baseline_full.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/omem_two_stage_baseline_full.pid
```

说明：`nohup env ... bash -lc '...'` 内层单引号子 shell **不会**继承你当前 shell 的 `OMEM_API_KEY`，因此上面把 key 写在 `env VAR=... bash -lc` 里传入；若仍报错，可改为把 `--api-key` / `--base-url` 直接替换成明文（注意不要提交到 git）。

### 11.5 Membox（`Membox_stableEval`）：sample0 全题 baseline

依赖：`pip install nltk`（Membox 内 BLEU 用 NLTK），且 `nltk` 数据需可用（首次可能下载）。

**输出**：`outputs/membox_baseline_conv26_all.json`

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_locomo_sample_baseline.py \
  --sample-id conv-26 \
  --membox-root system/Membox_stableEval \
  --output outputs/membox_baseline_conv26_all.json \
  --memory-dir outputs/membox_baseline_conv26_all_memory
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/membox_baseline_conv26_all.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/membox_baseline_conv26_all.pid
```

### 11.5.1 Membox：sample0 全题 **三探针归因**（`conv-26`，约 199 题）

读 `configs/keys.local.json`；embedding 走 API（默认 `text-embedding-3-small`，可用 `--embedding-model` 覆盖）。

**输出**：`outputs/membox_attr_conv26_all.json`

```bash
nohup bash -lc '
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia && \
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_sample_attribution.py \
  --sample-id conv-26 \
  --membox-root system/Membox_stableEval \
  --output outputs/membox_attr_conv26_all.json \
  --memory-dir outputs/membox_attr_conv26_all_memory
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/membox_attr_conv26_all.log 2>&1 & echo $! > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/logs/membox_attr_conv26_all.pid
```

更完整的 Membox 说明见：`docs/code-audit/2026-03-29/membox-locomo-repro-and-eval-zh.md`。

### 11.6 Membox：单题 smoke（验证 fork 是否可跑）

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_baseline_once.py \
  --sample-id conv-26 --question-index 0 \
  --membox-root system/Membox_stableEval \
  --output outputs/membox_stableeval_smoke_conv26_q0.json \
  --memory-dir outputs/membox_stableeval_smoke_conv26_q0_memory
```

### 11.7 通用：查看进度与结束

```bash
ROOT=/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
tail -f "$ROOT/outputs/logs/omem_baseline_conv26_all.log"   # 按需换日志名
ps -p "$(cat "$ROOT/outputs/logs/omem_baseline_conv26_all.pid")"
```

---

**Membox 修复说明（论文方法不变）**：`docs/code-audit/2026-03-29/membox-stableeval-repair-doc-zh.md`
