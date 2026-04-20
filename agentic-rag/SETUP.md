# Agentic RAG 环境配置与部署教程

本目录计划在 **`/DATA/disk4/workspace/zhongjian/memory`** 下搭建 **Agentic RAG**，组件如下：

| 组件 | 选型 | 你本地的模型路径 |
|------|------|------------------|
| 主 LLM | **vLLM** 提供 OpenAI 兼容 API | `SEAMiLab-Deconstructing-Amnesia-main/Qwen/Qwen3-8B` |
| Embedding | **Qwen3-Embedding-0.6B**（本地加载） | `cache/models/Qwen/Qwen3-Embedding-0___6B` |
| 向量库 | **Qdrant** | HTTP 默认 `6333` |
| Agent | **LangChain + LangGraph** | 应用代码在本仓库后续补充 |

> **说明**：`Qwen3-Embedding-0___6B` 是 Hugging Face 缓存目录命名（`0.6B` → `0___6B`），加载时把该目录作为**本地路径**即可。

---

## 一、配置清单（Checklist）

### 1. 硬件与系统

- **GPU**：Qwen3-8B 用 vLLM 推理，建议 **≥16GB 显存**（FP16/BF16）；若显存不足需使用量化或减小 `max-model-len`。
- **CUDA / 驱动**：与 **PyTorch、vLLM** 预编译 wheel 版本一致（安装前用 `nvidia-smi` 确认驱动）。
- **磁盘**：模型与缓存放在 **`/DATA/disk4/...`**，勿用默认家目录/系统盘（见下文环境变量）。

### 2. 软件版本（建议）

| 软件 | 说明 |
|------|------|
| Python | **3.10+**（3.11 常用） |
| Conda | 可选；`pkgs_dirs`、环境 `--prefix` 指到数据盘 |
| Docker | 可选；用于一键起 **Qdrant** |
| transformers | **≥4.51.0**（Qwen3 要求，否则 `KeyError: 'qwen3'`） |
| sentence-transformers | **≥3.0.0**（与 README 推荐一致） |

### 3. 服务与端口（默认）

| 服务 | 端口 | 用途 |
|------|------|------|
| vLLM OpenAI API | **8000** | Chat/Completion，供 LangChain `ChatOpenAI` |
| Qdrant REST | **6333** | 向量检索 |
| Qdrant gRPC | 6334 | 可选 |

### 4. 环境变量（核心）

在 `~/.bashrc` 或项目 `env` 文件中设置（**路径按你机器调整**）：

```bash
# 缓存统一到数据盘，避免撑爆系统盘
export HF_HOME=/DATA/disk4/workspace/zhongjian/memory/.cache/huggingface
export TRANSFORMERS_CACHE="${HF_HOME}/transformers"
export PIP_CACHE_DIR=/DATA/disk4/workspace/zhongjian/memory/.cache/pip
```

应用侧（见 `env.example`）：

- **`VLLM_BASE_URL`**：`http://127.0.0.1:8000/v1`
- **`EMBEDDING_MODEL_PATH`**：指向本地 Qwen3-Embedding 目录
- **`QDRANT_URL`**：`http://127.0.0.1:6333`
- **`EMBEDDING_DIM`**：`1024`（Qwen3-Embedding-0.6B 默认满维；若使用 MRL 更小维度，需与建库时一致）

### 5. Python 依赖（应用侧）

见本目录 **`requirements.txt`**。**vLLM** 需按 CUDA 版本单独安装（见下文），不要与 torch 版本混装冲突。

---

## 二、部署步骤

### Step 1：Conda 环境（推荐放在数据盘）

```bash
mkdir -p /DATA/disk4/workspace/zhongjian/memory/envs
conda create --prefix /DATA/disk4/workspace/zhongjian/memory/envs/agentic-rag python=3.11 -y
conda activate /DATA/disk4/workspace/zhongjian/memory/envs/agentic-rag
```

配置 conda 包缓存到数据盘（若尚未配置）：

```bash
conda config --add pkgs_dirs /DATA/disk4/workspace/zhongjian/memory/.cache/conda-pkgs
```

### Step 2：安装 PyTorch（按官网选择 CUDA 版本）

在 [PyTorch 官网](https://pytorch.org/get-started/locally/) 选择与你驱动匹配的命令，例如 CUDA 12.x：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Step 3：安装 vLLM

vLLM 与 PyTorch/CUDA 绑定紧密，请 **只选一种** 官方推荐方式安装（见 [vLLM 文档](https://docs.vllm.ai/en/latest/getting_started/installation.html)）：

```bash
pip install vllm
```

若冲突，可单独建一个 **仅用于推理** 的 conda 环境只跑 vLLM，应用与 embedding 用另一个环境（通过 HTTP 调用 vLLM）。

### Step 4：启动 vLLM（Qwen3-8B，本地路径）

将 `MODEL_PATH` 换成你的绝对路径：

```bash
export MODEL_PATH=/DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/Qwen/Qwen3-8B

python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --served-model-name Qwen3-8B \
  --dtype auto \
  --max-model-len 8192 \
  --host 0.0.0.0 \
  --port 8000
```

参数说明：

- **`--served-model-name`**：OpenAI API 里的 `model` 名称，需与客户端配置的 `VLLM_MODEL_NAME` 一致。
- **`--max-model-len`**：显存不足时可改为 `4096` 等。
- 多卡可加 **`--tensor-parallel-size N`**。

验证：

```bash
curl http://127.0.0.1:8000/v1/models
```

   ### Step 5：启动 Qdrant

   **方式 A：Docker（推荐）**

   ```bash
   docker run -d --name qdrant \
   -p 6333:6333 -p 6334:6334 \
   -v /DATA/disk4/workspace/zhongjian/memory/qdrant_storage:/qdrant/storage \
   qdrant/qdrant
   ```

   **方式 B：二进制 / 系统服务**  
   见 [Qdrant 文档](https://qdrant.tech/documentation/guides/installation/)。

   **方式 C：无管理员权限（用户目录部署，推荐无 Docker 时）**

   不需要 `apt install` / Docker，只在你有写权限的目录里下载官方预编译二进制即可（[GitHub Releases](https://github.com/qdrant/qdrant/releases)）。

   ```bash
   # 安装目录与数据目录（可改成你的数据盘路径，如 /DATA/disk4/...）
   export QDRANT_ROOT="${QDRANT_ROOT:-/DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/agentic-rag/opt/qdrant}"
   export QDRANT_STORAGE="${QDRANT_STORAGE:-/DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/agentic-rag/qdrant_storage}"
   mkdir -p "$QDRANT_ROOT" "$QDRANT_STORAGE"
   cd "$QDRANT_ROOT"

   # 版本号可到 Releases 核对。x86_64 Linux 建议优先用 **musl** 包（静态链接，不依赖系统 glibc，旧系统也可用）
   export QDRANT_VER="v1.17.1"
   # 直连慢或失败时见下方「国内下载」
   curl -fL -O "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VER}/qdrant-x86_64-unknown-linux-musl.tar.gz"
   tar -xzf "qdrant-x86_64-unknown-linux-musl.tar.gz"
   # 若你确定系统 glibc 很新（如 ≥2.38），可改用 qdrant-x86_64-unknown-linux-gnu.tar.gz

   # 数据落在用户可写路径；监听端口默认 6333（若被占用需改配置或环境变量）
   export QDRANT__STORAGE__STORAGE_PATH="$QDRANT_STORAGE"
   # 仅本机访问可省略；若要从其它机器访问该节点，需监听 0.0.0.0 并自行注意防火墙/安全组
   export QDRANT__SERVICE__HOST="${QDRANT__SERVICE__HOST:-0.0.0.0}"

   ./qdrant
   ```

   **国内下载 GitHub Release 较慢时**，可任选：

   1. **HTTP(S) 代理**（若你已有）：`export https_proxy=http://主机:端口`，再执行上面的 `curl`。
   2. **第三方 GitHub 文件加速前缀**（域名可能随时间变化，仅作备选；自行评估信任与可用性）：把原始 URL 接到镜像前缀后，例如  
      `curl -fL -O "https://mirror.ghproxy.com/https://github.com/qdrant/qdrant/releases/download/${QDRANT_VER}/qdrant-x86_64-unknown-linux-musl.tar.gz"`  
      若 404 或失败，换其它公开镜像或改回官方 URL。
   3. **本机浏览器** 打开 [Releases](https://github.com/qdrant/qdrant/releases) 下载对应 `tar.gz`，再用 **`scp`** / **`rsync`** 传到服务器 `QDRANT_ROOT` 后执行 `tar -xzf`。

   长期运行时建议 **`tmux` / `screen` / `nohup ... &`**，避免 SSH 断开后进程退出。ARM 服务器请用 **`qdrant-aarch64-unknown-linux-musl.tar.gz`**。

   **若运行 `./qdrant` 报错 `GLIBC_2.xx not found`（常见于 Ubuntu 22.04 等较旧 glibc）**：说明当前用的是 **gnu** 包，与系统 glibc 版本不匹配。请**删除旧二进制**，改下载 **`qdrant-x86_64-unknown-linux-musl.tar.gz`** 解压后再运行（与 SETUP 默认一致）。

   验证：`http://127.0.0.1:6333/collections` 可访问（远程机器上可先 `curl -s http://127.0.0.1:6333/collections`）。

   ### Step 6：安装应用依赖（LangChain / LangGraph / Qdrant 客户端）

   在 **agent 所在环境**（可与 vLLM 同环境，或分开）：

   ```bash
   cd /DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/agentic-rag
   pip install -r requirements.txt
   ```

   本仓库已实现 **LangGraph ReAct + 检索工具**（见 `agentic_rag/` 与 `main.py`）。配置好 `.env` 后：

   ```bash
   cp env.example .env   # 编辑路径与端口
   python main.py ingest sample_docs --recreate
   python main.py chat
   ```

   详见 **[README.md](./README.md)**。

### Step 7：Embedding（Qwen3-Embedding-0.6B）

不在此文档中强制单独进程；**推荐**在写索引/检索的 Python 进程里用 **SentenceTransformer** 加载本地目录：

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "/DATA/disk4/workspace/zhongjian/memory/cache/models/Qwen/Qwen3-Embedding-0___6B"
)
# 检索 query 建议使用 prompt，见模型 README
emb = model.encode(["示例文本"], prompt_name="query")
```

- 与 vLLM **争 GPU** 时：可让 embedding 用 **`device="cpu"`** 或指定 **`cuda:1`**（视机器而定）。
- 创建 Qdrant collection 时，向量维度设为 **1024**（与默认满维一致）；若改 MRL 维度，建库与检索必须相同。

### Step 8：LangChain / LangGraph 对接要点

1. **Chat 模型**：使用 **`ChatOpenAI`**（`langchain-openai`），配置：
   - `base_url=http://127.0.0.1:8000/v1`
   - `api_key="EMPTY"`（或任意占位）
   - `model="Qwen3-8B"`（与 `--served-model-name` 一致）

2. **向量库**：使用 **`langchain_qdrant.Qdrant`** + `QdrantClient(url=...)`，embedding 传入基于 `SentenceTransformer` 的 **`langchain_community.embeddings.HuggingFaceEmbeddings`** 或自定义 `Embeddings` 包装类。

3. **Agentic RAG**：用 **LangGraph** 编排节点：检索 →（可选重排）→ 带工具调用的 LLM；工具可包含「再检索」「计算器」等。

---

## 三、路径速查（你当前工作区）

| 用途 | 绝对路径 |
|------|----------|
| Qwen3-8B | `/DATA/disk4/workspace/zhongjian/memory/SEAMiLab-Deconstructing-Amnesia-main/Qwen/Qwen3-8B` |
| Qwen3-Embedding-0.6B | `/DATA/disk4/workspace/zhongjian/memory/cache/models/Qwen/Qwen3-Embedding-0___6B` |

---

## 四、常见问题

1. **`KeyError: 'qwen3'`**  
   升级 `transformers>=4.51.0`。

2. **vLLM OOM**  
   降低 `max-model-len`、使用量化（如 AWQ，需对应权重）、或 `tensor parallel`。

3. **Qdrant 维度不匹配**  
   删除集合并用与当前 embedding 输出一致的 `vector_size` 重建 collection。

4. **系统盘满**  
   确保 `HF_HOME`、`PIP_CACHE_DIR`、`conda pkgs_dirs`、conda 环境 `--prefix` 均在数据盘。

---

## 五、下一步

在本目录中补充：**文档加载 → 切分 → 写入 Qdrant → LangGraph 状态机（检索+生成+工具）** 的可运行示例代码；需要时可再增加 `docker-compose.yml` 统一管理 Qdrant 与可选服务。

复制环境变量模板：

```bash
cp env.example .env
# 编辑 .env 后，在代码中用 python-dotenv 加载
```
