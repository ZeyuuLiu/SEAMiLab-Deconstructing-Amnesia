# MemoryOS-main 环境配置与复现指南（v0.1）

## 1. 当前状态

我已经完成了 `system/MemoryOS-main` 的第一轮复现准备工作，但还没有替你启动任何长时间安装或长时间运行任务。<mccoremem id="01KP8DAZAAXKB8J8VVP0AC16CG" />

本轮已经完成的代码准备包括：

1. `eval/utils.py`
   - 改为从环境变量读取：
     - `MEMORYOS_API_KEY`
     - `MEMORYOS_BASE_URL`
     - `MEMORYOS_CHAT_MODEL`
     - `MEMORYOS_EMBED_MODEL`
2. `eval/main_loco_parse.py`
   - 支持命令行参数：
     - `--dataset`
     - `--output`
     - `--memory-dir`
     - `--sample-id`
     - `--limit`
3. `eval/mid_term_memory.py`
   - 改为从环境变量构造 OpenAI client
4. `eval/dynamic_update.py`
   - 改为使用默认 chat model 配置
5. `eval/evalution_loco.py`
   - 支持 `--input` 指定结果文件路径

这些改动的目的，是让 `MemoryOS-main` 不再依赖写死的空 `api_key`、固定 `base_url` 和固定数据路径，从而能够在你当前机器上进行更稳定的原始复现。

---

## 2. 复现链路怎么理解

`MemoryOS-main` 当前的原始 LoCoMo 复现链路是两段式：

### 第一步：生成回答结果

入口脚本：

- `system/MemoryOS-main/eval/main_loco_parse.py`

作用：

1. 读取 `locomo10.json`
2. 把对话写入 short / mid / long term memory
3. 对每个问题检索并生成 system answer
4. 输出：
   - `all_loco_results.json`

### 第二步：统计评估

入口脚本：

- `system/MemoryOS-main/eval/evalution_loco.py`

作用：

1. 读取上一步生成的 `all_loco_results.json`
2. 计算每个 category 的平均 F1

这说明：

- `MemoryOS-main` 当前提供的是**原系统自己的 baseline 流程**
- 还不是你当前评估框架中的三层 probe 接入版本

---

## 3. 环境安装建议

`MemoryOS-main` 当前依赖比较重，尤其是：

1. `sentence-transformers`
2. `transformers`
3. `FlagEmbedding`
4. `faiss-gpu`

为了提升安装成功率，我建议先用一个单独的 conda 环境。

建议环境名：

- `memeval-memoryos-v1`

---

## 4. 推荐安装命令

注意：

- 以下命令是给你本地执行的 `nohup` 版本
- 我不会替你直接启动长安装任务 <mccoremem id="01KP8DAZAAXKB8J8VVP0AC16CG" />

### 4.1 创建 conda 环境

```bash
nohup bash -lc 'conda create -y -n memeval-memoryos-v1 python=3.10' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_create_env.log 2>&1 &
```

### 4.2 安装基础依赖

如果你机器上 GPU / CUDA 环境不稳定，建议优先尝试 `faiss-cpu`，不要一开始就强装 `faiss-gpu`。

更稳的第一版安装命令：

```bash
nohup bash -lc 'conda run --no-capture-output -n memeval-memoryos-v1 python -m pip install -U pip setuptools wheel && conda run --no-capture-output -n memeval-memoryos-v1 python -m pip install numpy==1.24.* sentence-transformers>=2.7.0,<3.0.0 transformers>=4.51.0 openai httpx[socks] flask>=2.0.0,<3.0.0 python-dotenv>=0.19.0,<2.0.0 typing-extensions>=4.0.0,<5.0.0 regex>=2022.1.18 faiss-cpu' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_install_base.log 2>&1 &
```

### 4.3 如果后续需要 BGE-M3，再补 FlagEmbedding

```bash
nohup bash -lc 'conda run --no-capture-output -n memeval-memoryos-v1 python -m pip install -U FlagEmbedding' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_install_flagembedding.log 2>&1 &
```

---

## 5. 正式复现前的运行环境变量

在运行 `main_loco_parse.py` 之前，需要提供至少以下环境变量：

1. `MEMORYOS_API_KEY`
2. `MEMORYOS_BASE_URL`
3. `MEMORYOS_CHAT_MODEL`

推荐值：

1. `MEMORYOS_CHAT_MODEL=gpt-4o-mini`
2. `MEMORYOS_EMBED_MODEL=all-MiniLM-L6-v2`

如果你希望直接复用当前项目的 `configs/keys.local.json`，最稳妥的方式是用一段内联 Python 从文件中读取后再 export。

---

## 6. 运行原始复现

### 6.1 先跑生成结果

下面这条命令会：

1. 读取 `configs/keys.local.json`
2. 注入 `MEMORYOS_API_KEY / MEMORYOS_BASE_URL / MEMORYOS_CHAT_MODEL`
3. 只跑 `conv-26`
4. 结果输出到 `outputs/memoryos_conv26_results.json`
5. 中间记忆文件输出到 `outputs/memoryos_conv26_memory/`

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemoryOS-main/eval && export MEMORYOS_API_KEY=$(python - <<'"'"'PY'"'"'
import json
from pathlib import Path
obj=json.loads(Path("/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/configs/keys.local.json").read_text(encoding="utf-8-sig"))
print(obj["api_key"])
PY
) && export MEMORYOS_BASE_URL=$(python - <<'"'"'PY'"'"'
import json
from pathlib import Path
obj=json.loads(Path("/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/configs/keys.local.json").read_text(encoding="utf-8-sig"))
print(obj["base_url"])
PY
) && export MEMORYOS_CHAT_MODEL=$(python - <<'"'"'PY'"'"'
import json
from pathlib import Path
obj=json.loads(Path("/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/configs/keys.local.json").read_text(encoding="utf-8-sig"))
print(obj.get("model","gpt-4o-mini"))
PY
) && export MEMORYOS_EMBED_MODEL=all-MiniLM-L6-v2 && conda run --no-capture-output -n memeval-memoryos-v1 python main_loco_parse.py --dataset /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json --sample-id conv-26 --output /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/memoryos_conv26_results.json --memory-dir /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/memoryos_conv26_memory' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_conv26_parse.log 2>&1 &
```

### 6.2 再跑官方评估

这一步只依赖上一步生成的结果文件：

```bash
nohup bash -lc 'cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemoryOS-main/eval && conda run --no-capture-output -n memeval-memoryos-v1 python evalution_loco.py --input /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/memoryos_conv26_results.json' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_conv26_eval.log 2>&1 &
```

---

## 7. 运行后怎么看结果

### 看生成阶段日志

```bash
tail -n 80 /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_conv26_parse.log
```

### 看评估阶段日志

```bash
tail -n 80 /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/nohup_memoryos_conv26_eval.log
```

### 看结果文件

```bash
python -m json.tool /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/memoryos_conv26_results.json | head -n 80
```

---

## 8. 当前我对 MemoryOS-main 的判断

在当前项目里，`MemoryOS-main` 比 `EverOS`、`TiMem`、`MemOS` 更适合作为下一批 baseline 候选，原因是：

1. 它有明确的 short / mid / long-term memory 分层
2. 原始 baseline 链路比较清楚
3. 代码结构更适合后续被抽成 adapter

但要注意：

1. 当前这一步只是在做**原始系统复现准备**
2. 还没有把 `MemoryOS-main` 接进你自己的三层 probe 框架

---

## 9. 一句话总结

我已经把 `MemoryOS-main` 的原始复现入口改成了可配置版本；接下来你只需要按本文档里的 `nohup` 命令本地执行环境安装与 parse/eval 流程，然后把日志和结果给我，我再继续推进下一步适配器接入。 
