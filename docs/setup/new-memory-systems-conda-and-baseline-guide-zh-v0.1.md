# 新记忆系统 conda 环境与 baseline 复现指南（v0.1）

## 1. 文档目标

这份文档用于支持以下任务：

1. 为四个新增记忆系统分别建立独立 conda 环境
2. 先跑通各自官方或近官方的 LoCoMo baseline / reproduction 流程
3. 为后续接入统一评测框架适配器做准备

本轮目标仅到这里为止：

1. **环境搭建**
2. **原系统 baseline 复现**

暂时**不涉及**：

1. 统一适配器编写
2. 三层探针接入
3. 最终归因评测

---

## 2. 四个系统的复现形态差异

这四个系统并不是同一种复现方式，必须分开处理：

### 2.1 EverOS

特点：

1. 自带统一 evaluation CLI
2. 官方文档直接提供 LoCoMo 运行方式
3. 更接近“官方 benchmark pipeline”

### 2.2 General Agentic Memory（GAM）

特点：

1. 使用独立的 `research/eval/locomo_test.py`
2. 需要三套 LLM 角色配置：
   - memory
   - research
   - working
3. 更像研究脚本型 baseline

### 2.3 TiMem

特点：

1. 是显式的三阶段实验流程：
   - memory generation
   - memory retrieval
   - evaluation
2. 需要先把 `locomo10.json` 切成 `locomo10_smart_split`
3. 本地版本依赖数据库服务

### 2.4 MemOS

特点：

1. 官方提供 `evaluation/scripts/run_locomo_eval.sh`
2. baseline 是五阶段官方流水线：
   - ingestion
   - search
   - responses
   - eval
   - metric
3. 如果跑 `memos-api`，通常需要先起本地 API 服务

---

## 3. 总体策略

建议按下面顺序推进：

1. 先完成四个环境搭建
2. 先做每个系统的 smoke / 单轮验证
3. 再执行长时间 baseline 正式命令
4. 你跑完 `nohup` 任务后把日志和结果给我
5. 我再继续分析并开始适配器设计

这样做的原因是：

1. 四个系统依赖差异很大
2. TiMem / MemOS 还涉及服务组件
3. 直接上全量 baseline，排错成本很高

---

## 4. 通用前提

以下前提适用于四个系统：

### 4.1 建议目录

项目根目录：

```bash
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
```

四个系统目录：

```bash
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/EverOS-main
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main
```

### 4.2 建议准备的 API 环境变量

至少建议统一准备：

```bash
export OPENAI_API_KEY="你的key"
export OPENAI_BASE_URL="你的base_url"
```

如果你实际用的是兼容 OpenAI 的代理接口，也可以写成：

```bash
export OPENAI_API_KEY="你的key"
export OPENAI_BASE_URL="https://你的兼容接口/v1"
```

### 4.3 建议统一日志目录

```bash
mkdir -p /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs
```

---

## 5. EverOS

## 5.1 环境判断

从仓库内容看，EverOS：

1. `pyproject.toml` 要求 Python `>=3.12,<3.13`
2. evaluation 文档推荐使用 `uv`
3. LoCoMo 入口是：
   - `python -m evaluation.cli --dataset locomo --system evermemos`

因此建议：

1. conda 环境使用 Python 3.12
2. 环境内安装 `uv`
3. 再安装项目本体和 evaluation 依赖

## 5.2 conda 环境命令

```bash
conda create -n memeval-everos-v1 python=3.12 -y
conda activate memeval-everos-v1

cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/EverOS-main

pip install -U pip setuptools wheel uv
pip install -e .
pip install rich requests mem0ai zep-cloud
```

## 5.3 数据准备

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/EverOS-main
mkdir -p evaluation/data/locomo
cp /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json evaluation/data/locomo/locomo10.json
```

## 5.4 环境变量准备

EverOS evaluation README 提到需要主项目 `.env` 中的变量。最少建议先补：

```bash
export LLM_API_KEY="$OPENAI_API_KEY"
export LLM_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
export VECTORIZE_API_KEY="$OPENAI_API_KEY"
export RERANK_API_KEY="$OPENAI_API_KEY"
```

如果仓库自带 `.env` 模板，建议你按模板补齐。

## 5.5 smoke baseline 命令

先跑一个轻量 smoke：

```bash
conda activate memeval-everos-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/EverOS-main

python -m evaluation.cli --dataset locomo --system evermemos --smoke
```

## 5.6 正式 baseline nohup 命令

如果 smoke 通过，再跑正式命令：

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-everos-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/EverOS-main
export LLM_API_KEY="$OPENAI_API_KEY"
export LLM_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
export VECTORIZE_API_KEY="$OPENAI_API_KEY"
export RERANK_API_KEY="$OPENAI_API_KEY"
python -m evaluation.cli --dataset locomo --system evermemos
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/everos_locomo_baseline.log 2>&1 &
```

## 5.7 结果检查

重点看：

1. `evaluation/results/`
2. baseline 最终 summary
3. log 里是否出现依赖缺失或 API 配置错误

---

## 6. General Agentic Memory（GAM）

## 6.1 环境判断

从仓库内容看，GAM：

1. 官方安装方式是 `pip install -r requirements.txt` 和 `pip install -e .`
2. LoCoMo baseline 入口是：
   - `research/eval/locomo_test.py`
3. 需要三组模型参数：
   - memory
   - research
   - working

建议：

1. conda 环境使用 Python 3.10
2. 如果启用 BM25，最好补 Java

## 6.2 conda 环境命令

```bash
conda create -n memeval-gam-v1 python=3.10 -y
conda activate memeval-gam-v1

conda install -c conda-forge openjdk=21 -y

cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main

pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
python -m nltk.downloader punkt wordnet
```

## 6.3 数据准备

GAM 直接接受 LoCoMo JSON 路径，因此无需额外复制数据，只要直接使用主项目数据即可：

```bash
/home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json
```

## 6.4 smoke baseline 命令

先跑 1 个样本做 smoke：

```bash
conda activate memeval-gam-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research

python eval/locomo_test.py \
  --data /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json \
  --outdir /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/gam_locomo_smoke \
  --start-idx 0 \
  --end-idx 1 \
  --memory-api-key "$OPENAI_API_KEY" \
  --memory-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --memory-model "gpt-4o-mini" \
  --memory-api-type "openai" \
  --research-api-key "$OPENAI_API_KEY" \
  --research-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --research-model "gpt-4o-mini" \
  --research-api-type "openai" \
  --working-api-key "$OPENAI_API_KEY" \
  --working-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --working-model "gpt-4o-mini" \
  --working-api-type "openai"
```

## 6.5 正式 baseline nohup 命令

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-gam-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/general-agentic-memory-main/research
python eval/locomo_test.py \
  --data /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json \
  --outdir /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/gam_locomo_baseline \
  --start-idx 0 \
  --memory-api-key "$OPENAI_API_KEY" \
  --memory-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --memory-model "gpt-4o-mini" \
  --memory-api-type "openai" \
  --research-api-key "$OPENAI_API_KEY" \
  --research-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --research-model "gpt-4o-mini" \
  --research-api-type "openai" \
  --working-api-key "$OPENAI_API_KEY" \
  --working-base-url "${OPENAI_BASE_URL:-https://api.openai.com/v1}" \
  --working-model "gpt-4o-mini" \
  --working-api-type "openai"
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/gam_locomo_baseline.log 2>&1 &
```

## 6.6 结果检查

重点看：

1. `outputs/gam_locomo_baseline`
2. 每题输出文件
3. 是否有 `SentenceTransformer` / `FlagEmbedding` / `pyserini` 相关依赖错误

---

## 7. TiMem

## 7.1 环境判断

TiMem 与前两个系统差异最大。

它的 LoCoMo baseline 更接近完整实验复现链：

1. 先切分原始 `locomo10.json`
2. 再跑 memory generation
3. 再跑 memory retrieval
4. 最后跑 evaluation

另外，本地 self-hosted 版本需要数据库服务。

## 7.2 conda 环境命令

```bash
conda create -n memeval-timem-v1 python=3.10 -y
conda activate memeval-timem-v1

cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main

pip install -U pip setuptools wheel
pip install -r requirements.txt
pip install -e .
python -m nltk.downloader punkt wordnet omw-1.4
```

## 7.3 启动 TiMem 依赖服务

TiMem README 显示本地版需要先起数据库服务：

```bash
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main/migration
docker-compose up -d
```

## 7.4 环境变量建议

最少准备：

```bash
export OPENAI_API_KEY="你的key"
export TIMEM_DATASET_PROFILE=default
export DATABASE_URL="postgresql://timem:password@localhost:5432/timem"
export QDRANT_URL="http://localhost:6333"
```

如果仓库有 `.env` 模板，建议同步写入。

## 7.5 数据预处理

TiMem 的 LoCoMo 实验依赖 `data/locomo10_smart_split`。

先把主项目的 `locomo10.json` 切分过去：

```bash
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main

python experiments/dataset_utils/dataset_splitter.py \
  --locomo-input /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json \
  --locomo-output-dir data/locomo10_smart_split
```

## 7.6 smoke 运行建议

TiMem 的 `01_memory_generation.py` 和 `02_memory_retrieval.py` 都偏长，建议先分别单独跑一次前置检查：

```bash
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main

python experiments/datasets/locomo/01_memory_generation.py
```

如果 generation 正常结束，再跑：

```bash
python experiments/datasets/locomo/02_memory_retrieval.py
```

最后再跑：

```bash
python experiments/datasets/locomo/03_evaluation.py --data-dir logs/locomo
```

## 7.7 正式 nohup 命令

### memory generation

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main
export TIMEM_DATASET_PROFILE=default
python experiments/datasets/locomo/01_memory_generation.py
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/timem_locomo_generation.log 2>&1 &
```

### memory retrieval

等 generation 完成后再跑：

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main
export TIMEM_DATASET_PROFILE=default
python experiments/datasets/locomo/02_memory_retrieval.py
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/timem_locomo_retrieval.log 2>&1 &
```

### evaluation

等 retrieval 完成后再跑：

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-timem-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/timem-main
python experiments/datasets/locomo/03_evaluation.py --data-dir logs/locomo
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/timem_locomo_eval.log 2>&1 &
```

## 7.8 结果检查

重点看：

1. `logs/locomo`
2. `memory_retrieval_eval_data_*.json`
3. `03_evaluation.py` 生成的最终结果
4. generation / retrieval 日志里是否有数据库连接错误

---

## 8. MemOS

## 8.1 环境判断

MemOS 官方 evaluation README 给出的方式是：

1. 使用 Poetry 安装
2. 进入 `evaluation/`
3. 跑 `scripts/run_locomo_eval.sh`

同时，如果使用 `memos-api` 本地服务，通常还要先启动本地 API。

## 8.2 conda 环境命令

```bash
conda create -n memeval-memos-v1 python=3.10 -y
conda activate memeval-memos-v1

cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main

pip install -U pip setuptools wheel poetry
poetry config virtualenvs.create false
poetry install --extras all --with eval
```

## 8.3 数据准备

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main
mkdir -p evaluation/data/locomo
cp /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/data/locomo10.json evaluation/data/locomo/locomo10.json
```

## 8.4 本地 API 服务

如果你打算先跑本地 `memos-api`，建议先起服务：

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-memos-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main
uvicorn memos.api.server_api:app --host 0.0.0.0 --port 8001 --workers 8
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/memos_api_server.log 2>&1 &
```

然后在 `evaluation/.env` 中至少补：

```bash
MEMOS_URL="http://127.0.0.1:8001"
OPENAI_API_KEY="你的key"
OPENAI_BASE_URL="你的base_url"
```

## 8.5 smoke 建议

MemOS 官方没有像 EverOS 那样明确的 smoke 命令，建议先跑单阶段检查：

```bash
conda activate memeval-memos-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation

python scripts/locomo/locomo_ingestion.py --lib memos-api --version smoke --workers 1
```

如果 ingestion 正常，再顺次检查：

```bash
python scripts/locomo/locomo_search.py --lib memos-api --version smoke --top_k 20 --workers 1
python scripts/locomo/locomo_responses.py --lib memos-api --version smoke
python scripts/locomo/locomo_eval.py --lib memos-api --version smoke --workers 1 --num_runs 1
python scripts/locomo/locomo_metric.py --lib memos-api --version smoke
```

## 8.6 正式 baseline nohup 命令

```bash
nohup bash -lc '
source ~/miniconda3/etc/profile.d/conda.sh || source ~/anaconda3/etc/profile.d/conda.sh
conda activate memeval-memos-v1
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/system/MemOS-main/evaluation
bash scripts/run_locomo_eval.sh
' > /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/outputs/system_repro_logs/memos_locomo_baseline.log 2>&1 &
```

## 8.7 结果检查

重点看：

1. `evaluation/results/locomo/`
2. `memos-api_locomo_search_results.json`
3. `memos-api_locomo_responses.json`
4. `memos-api_locomo_judged.json`
5. `memos-api_locomo_results.xlsx`

---

## 9. 推荐执行顺序

强烈建议按下面顺序逐个推进，而不是四个系统一起启动：

1. EverOS
2. GAM
3. MemOS
4. TiMem

原因：

1. EverOS 和 GAM 相对最像“直接脚本复现”
2. MemOS 需要本地 API 服务
3. TiMem 依赖最多，且是多阶段链路

---

## 10. 我建议你现在就执行的命令

如果你想先最快推进，我建议优先做这四步：

### 第一步：先建环境

按上面第 5 到第 8 节，分别创建：

1. `memeval-everos-v1`
2. `memeval-gam-v1`
3. `memeval-timem-v1`
4. `memeval-memos-v1`

### 第二步：先做轻量 smoke

按下面顺序：

1. EverOS `--smoke`
2. GAM `--start-idx 0 --end-idx 1`
3. MemOS `locomo_ingestion.py --version smoke`
4. TiMem `dataset_splitter.py`

### 第三步：再跑长时间 baseline

长任务统一用上面给出的 `nohup` 命令。

### 第四步：跑完后把这些文件给我

请把以下内容发我：

1. 四个 baseline 的日志尾部
2. 四个 baseline 的结果目录结构
3. 如果失败，贴第一处报错

---

## 11. 当前阶段的交付边界

到你完成这一轮之后，我们再继续做下面三件事：

1. 检查四个系统 baseline 是否真正复现成功
2. 确定每个系统的 native ingest / retrieval / online answer 入口
3. 再开始写统一评测适配器

因此，当前这份文档的定位非常明确：

- **先把环境搭好，先把 baseline 跑通。**

---

## 12. 一句话总结

当前最稳妥的推进方式是：

1. 每个系统独立 conda 环境
2. 先 smoke
3. 再 `nohup` 跑 baseline
4. 你跑完把日志和结果给我
5. 我再继续帮你做复现诊断和统一适配器设计
