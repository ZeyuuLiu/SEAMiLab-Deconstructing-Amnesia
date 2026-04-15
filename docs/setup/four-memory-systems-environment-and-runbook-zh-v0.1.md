# 四个新增记忆系统环境状态与运行说明（v0.1）

## 1. 文档目标

这份文档用于统一说明以下四个记忆系统当前的环境搭建结果、可运行状态、已知阻塞点以及正式 `nohup` 运行命令：

1. `EverOS`
2. `General Agentic Memory`
3. `TiMem`
4. `MemOS`

本文档强调的是**当前真实进度**，不是理想状态。

---

## 2. 总体进度

截至当前，四个系统的状态如下：

### 2.1 已完成 conda 环境创建

以下环境已经创建成功：

1. `memeval-everos-v1`
2. `memeval-gam-v1`
3. `memeval-timem-v1`
4. `memeval-memos-v1`

### 2.2 当前可用性结论

#### EverOS

状态：

- **环境已创建，CLI 可启动，但官方 LoCoMo smoke 仍存在运行配置/模型适配阻塞**

#### GAM

状态：

- **环境已创建，核心依赖和研究模块可导入，LoCoMo 脚本已实际进入执行**

#### TiMem

状态：

- **环境已创建，Python 侧依赖和核心模块可导入，但完整复现仍受 Docker 依赖阻塞**

#### MemOS

状态：

- **环境已创建，baseline 三阶段脚本入口可启动；当前采用 baseline 轻量版环境，不包含完整 eval 重依赖**

---

## 3. 逐系统状态说明

## 3.1 EverOS

## 3.1.1 已完成内容

已经完成：

1. `conda` 环境创建
2. Python 入口可用
3. `evaluation.cli --help` 可正常启动
4. 项目根目录 `.env` 已补入最小运行配置
5. `evaluation/config/systems/evermemos.yaml` 已调整为：
   - `LLM_MODEL` 从环境变量读取
   - `search.mode = lightweight`

## 3.1.2 当前已定位的问题

当前 EverOS 不再是“环境没装好”的问题，而是：

### 问题一：默认模型与当前渠道不兼容

原始官方配置默认写的是：

1. `openai/gpt-4.1-mini`
2. `Qwen/Qwen3-Embedding-4B`

而你当前渠道实际支持的是：

1. `gpt-4o-mini`
2. `text-embedding-3-small`

这个问题我已经做了第一轮配置修正。

### 问题二：max_tokens 过大

已定位到：

- 原始配置会给 `gpt-4o-mini` 传 `32768`

而该模型最多支持：

- `16384`

这个问题已经修成：

```text
LLM_MAX_TOKENS=16384
```

### 问题三：最小 add smoke 仍出现 `atomic_fact list is empty`

这说明：

1. 环境链路已经走进了真实业务逻辑
2. 但当前模型/提示词/最小消息规模组合下，事件抽取结果为空

所以当前 EverOS 的结论是：

- **环境已就绪，但官方 baseline 仍存在模型适配层面的运行阻塞**

## 3.1.3 当前建议

EverOS 现在不建议你直接跑全量正式 baseline。

更建议先在后续单独做两件事之一：

1. 换更稳定的主模型
2. 单独继续调它的 event extraction / memory extraction 配置

## 3.1.4 当前 `.env` 关键配置

当前已写入：

```text
MONGODB_HOST=127.0.0.1
MONGODB_PORT=27017
LLM_MODEL=gpt-4o-mini
LLM_MAX_TOKENS=16384
VECTORIZE_MODEL=text-embedding-3-small
RERANK_MODEL=text-embedding-3-small
```

## 3.1.5 如果你仍想自己尝试跑的 `nohup`

注意：

- 这条命令当前**不保证最终成功**
- 主要目的是让你在自己的终端环境继续验证 EverOS

```bash
mkdir -p /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs

nohup conda run --no-capture-output -n memeval-everos-v1 \
  python -m evaluation.cli \
  --dataset locomo \
  --system evermemos \
  --smoke \
  --smoke-messages 10 \
  --smoke-questions 3 \
  --from-conv 0 \
  --to-conv 1 \
  --run-name smoke \
  > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/everos_locomo_smoke.log 2>&1 &
```

---

## 3.2 General Agentic Memory（GAM）

## 3.2.1 已完成内容

已经完成：

1. `conda` 环境创建
2. `requirements.txt` 安装
3. editable 安装
4. `gam_research` 模块可导入
5. LoCoMo 脚本已实际进入执行阶段

## 3.2.2 已定位的运行约束

GAM 当前最大的运行约束不是依赖缺失，而是：

1. 运行目录必须位于 `research/`
2. 需要把 `research/` 注入 `PYTHONPATH`

如果不处理这点，会出现：

- `ModuleNotFoundError: No module named 'gam_research'`

这个问题已经定位清楚，因此后续正式命令只要带上正确的 `cwd + PYTHONPATH` 即可。

## 3.2.3 当前状态结论

GAM 当前可以视为：

- **环境已就绪，可进入正式 baseline 复现**

## 3.2.4 正式 `nohup` 命令

```bash
mkdir -p /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs

nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research && export PYTHONPATH=/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research${PYTHONPATH:+:$PYTHONPATH} && python - <<'"'"'PY'"'"'
import json, os, subprocess
from pathlib import Path
obj = json.loads(Path("/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/configs/keys.local.json").read_text(encoding="utf-8-sig"))
cmd = [
    "conda", "run", "--no-capture-output", "-n", "memeval-gam-v1",
    "python", "eval/locomo_test.py",
    "--data", "/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json",
    "--outdir", "/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/gam_locomo_baseline",
    "--start-idx", "0",
    "--memory-api-key", obj["api_key"], "--memory-base-url", obj["base_url"], "--memory-model", obj.get("model", "gpt-4o-mini"), "--memory-api-type", "openai",
    "--research-api-key", obj["api_key"], "--research-base-url", obj["base_url"], "--research-model", obj.get("model", "gpt-4o-mini"), "--research-api-type", "openai",
    "--working-api-key", obj["api_key"], "--working-base-url", obj["base_url"], "--working-model", obj.get("model", "gpt-4o-mini"), "--working-api-type", "openai",
]
subprocess.run(cmd, cwd=os.getcwd(), env=os.environ.copy(), check=False)
PY' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/gam_locomo_baseline.log 2>&1 &
```

---

## 3.3 TiMem

## 3.3.1 已完成内容

已经完成：

1. `conda` 环境创建
2. `requirements.txt` 安装
3. editable 安装
4. `timem` / `sqlalchemy` / `qdrant_client` 可导入

## 3.3.2 当前阻塞点

TiMem 当前的阻塞点已经非常明确：

- **Docker 数据服务不可用**

也就是说：

1. Python 环境不是问题
2. 代码导入不是问题
3. 真正卡住的是它需要数据库与向量服务

## 3.3.3 当前状态结论

TiMem 当前可以视为：

- **Python 环境已就绪，但完整 baseline 复现被 Docker 阻塞**

## 3.3.4 后续正式命令

等你后续有 Docker 条件时，可以按三阶段运行：

### generation

```bash
nohup conda run --no-capture-output -n memeval-timem-v1 \
  python experiments/datasets/locomo/01_memory_generation.py \
  > outputs/system_repro_logs/timem_locomo_generation.log 2>&1 &
```

### retrieval

```bash
nohup conda run --no-capture-output -n memeval-timem-v1 \
  python experiments/datasets/locomo/02_memory_retrieval.py \
  > outputs/system_repro_logs/timem_locomo_retrieval.log 2>&1 &
```

### evaluation

```bash
nohup conda run --no-capture-output -n memeval-timem-v1 \
  python experiments/datasets/locomo/03_evaluation.py --data-dir logs/locomo \
  > outputs/system_repro_logs/timem_locomo_eval.log 2>&1 &
```

---

## 3.4 MemOS

## 3.4.1 已完成内容

已经完成：

1. `conda` 环境创建
2. `poetry` 安装
3. 发现官方 `--extras all --with eval` 对当前目标过重
4. 改成 baseline 轻量版安装：
   - `pip install -e .`
   - `pandas`
   - `python-dotenv`
   - `tqdm`
5. `locomo_ingestion.py --help` 可启动
6. `locomo_search.py --help` 可启动
7. `locomo_responses.py --help` 可启动

## 3.4.2 当前状态结论

MemOS 当前可以视为：

- **baseline 三阶段环境已就绪**

这里的 baseline 三阶段指的是：

1. ingestion
2. search
3. responses

而不是完整官方五阶段中的：

4. eval
5. metric

## 3.4.3 这几个阶段分别是什么意思

MemOS 官方 LoCoMo 流水线共有五个阶段：

### ingestion

作用：

1. 把 LoCoMo 对话按 session 切开
2. 给每个说话人构造独立 user_id
3. 调原始记忆系统的 `add()` 接口写入记忆

这一阶段的本质是：

- 把原始对话真正写进记忆系统

### search

作用：

1. 遍历每个 QA 问题
2. 对两个说话人的 memory 分别做原生检索
3. 把检索结果拼成后续回答所需的上下文 `context`
4. 保存为中间搜索结果 JSON

这一阶段得到的是：

- 原系统针对每个 query 的原生检索证据

### responses

作用：

1. 读取 `search` 阶段保存的 `context`
2. 用统一回答 prompt 调 LLM
3. 为每道题生成最终 answer
4. 保存为 responses JSON

这一阶段得到的是：

- 基于原生检索上下文的最终回答

### eval

作用：

1. 把生成答案与 golden answer 做自动评估
2. 生成 judged/eval 结果

### metric

作用：

1. 汇总整体指标
2. 输出最终表格或结果文件

所以如果你当前只想先复现 baseline 核心链路，最重要的是前三步：

1. `ingestion`
2. `search`
3. `responses`

## 3.4.4 为什么这样处理

因为你当前的目标是：

- 先把环境搭好
- 先跑 baseline

而 `locomo_eval.py` 会额外引入：

1. `bert-score`
2. `torch`
3. `sentence-transformers`

这些对“先跑 baseline”并不是必须。

## 3.4.5 baseline 三阶段正式 `nohup` 命令

### ingestion

```bash
mkdir -p /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs

nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation && conda run --no-capture-output -n memeval-memos-v1 python scripts/locomo/locomo_ingestion.py --lib memos-api --version baseline --workers 10' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/memos_locomo_ingestion.log 2>&1 &
```

### search

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation && conda run --no-capture-output -n memeval-memos-v1 python scripts/locomo/locomo_search.py --lib memos-api --version baseline --top_k 20 --workers 10' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/memos_locomo_search.log 2>&1 &
```

### responses

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation && conda run --no-capture-output -n memeval-memos-v1 python scripts/locomo/locomo_responses.py --lib memos-api --version baseline' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/memos_locomo_responses.log 2>&1 &
```

### 如果后续你要完整官方五阶段

那时再补：

1. `locomo_eval.py`
2. `locomo_metric.py`

以及对应重依赖即可。

---

## 4. 当前真实完成进度

如果用最简洁的话总结当前进度，可以写成：

### 已完成

1. 四个系统的 conda 环境都已创建
2. `GAM` 环境已到可正式 baseline 运行状态
3. `TiMem` 的 Python 环境已就绪，Docker 仍是唯一主要阻塞
4. `MemOS` 的 baseline 三阶段环境已到可正式运行状态
5. `EverOS` 的环境、CLI 与基础配置已就绪，但官方 baseline 仍存在模型/提示词适配问题

### 尚未完成

1. `EverOS` 还没有达到“可直接稳定正式跑完”的状态
2. `TiMem` 由于没有 Docker，无法进入完整复现
3. `MemOS` 还未补完整官方 `eval/metric` 阶段的重依赖

---

## 5. 当前最建议你立刻执行的命令

如果你现在要开始正式跑，建议顺序如下：

### 第一优先级：GAM

它目前最接近“环境就绪即可直接跑正式 baseline”。

### 第二优先级：MemOS baseline 三阶段

它目前已经能跑官方 baseline 的前三步。

### 暂缓：EverOS

它目前仍建议继续处理模型/抽取配置后再跑正式量。

### 暂缓：TiMem

等你能提供 Docker 环境后再启动。

---

## 6. 与统一评测适配器的衔接

这轮环境工作完成后，后续进入统一评测框架适配时，建议顺序是：

1. `GAM`
2. `MemOS`
3. `EverOS`
4. `TiMem`

对应的详细方案见：

- [new-memory-systems-adapter-plan-zh-v0.1.md](file:///home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/docs/architecture/new-memory-systems-adapter-plan-zh-v0.1.md)

---

## 7. 一句话总结

当前四个系统里：

1. **GAM 已经最接近可直接正式复现**
2. **MemOS 已经达到 baseline 三阶段可运行**
3. **TiMem 的 Python 环境已完成，但 Docker 是硬阻塞**
4. **EverOS 的环境已通，但官方 baseline 仍需要继续做模型/配置适配**
