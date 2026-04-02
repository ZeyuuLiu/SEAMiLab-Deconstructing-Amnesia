# Membox 在 LoCoMo 上的复现与评测说明

## 1. 当前状态（简要）

| 项目 | 说明 |
|------|------|
| **代码 Bug** | 原版 `system/Membox` 在 `Config.apply_run_id()` 中未更新 `TRACE_STATS_FILE`，Trace 阶段会 `FileNotFoundError`。已在 **`system/Membox_stableEval`** 中仅增加一行路径修复，**不改动**记忆算法与 Prompt。 |
| **适配器** | `src/memory_eval/adapters/membox_adapter.py`：`MemboxAdapter` 实现 `EncodingAdapterProtocol` / `RetrievalAdapterProtocol` / `GenerationAdapterProtocol`。未配置 `api_key` / `base_url` 时会在 `ingest_conversation` **显式报错**，避免静默失败。 |
| **默认根目录** | 不传 `membox_root` 时，适配器默认使用 **`Membox_stableEval`**（稳定评测 fork）。若要用论文原版目录，请显式传 `--membox-root system/Membox`（需自行接受上述路径 bug 风险）。 |
| **凭证** | 与 O-Mem 一致：优先读 `configs/keys.local.json`；也可用环境变量 `MEMORY_EVAL_API_KEY`、`MEMORY_EVAL_BASE_URL`（见 `load_runtime_credentials`）；命令行 `--api-key` / `--base-url` 优先级更高。 |
| **依赖** | `nltk`（BLEU 需 `punkt`）；脚本会在首次需要时尝试 `nltk.download`。另需：`openai`、`scikit-learn`、`tiktoken` 等（Membox 本体依赖）。 |

## 2. 环境准备

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda activate omem-paper100   # 或你用于本项目的 env
pip install openai scikit-learn nltk tiktoken numpy
```

配置 `configs/keys.local.json`（至少含 `api_key`、`base_url`；`model` 为可选默认 LLM）：

```json
{
  "api_key": "sk-...",
  "base_url": "https://你的兼容 OpenAI 网关/v1",
  "model": "gpt-4o-mini"
}
```

Membox 默认使用 **`Config.EMBEDDING_MODEL = text-embedding-3-small`**（与 OpenAI 兼容的 embedding API）。若你的网关不支持该模型，需在 `MemboxAdapterConfig` 中传入 `embedding_model`（或通过后续扩展脚本参数）；当前脚本默认与 Membox 论文配置一致。

## 3. LoCoMo 上「复现」——在线 QA baseline

### 3.1 单题 smoke（验证环境与 fork）

```bash
cd /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_baseline_once.py \
  --sample-id conv-26 \
  --question-index 0 \
  --output outputs/membox_smoke_conv26_q0.json \
  --memory-dir outputs/membox_smoke_conv26_q0_memory
```

默认 `--membox-root` 指向 **`Membox_stableEval`**（可不写）。

### 3.2 单个 sample 全题（sample0 = `conv-26`，约 199 题）

输出含按类 F1/BLEU 汇总（与 `locomo10.json` 的 `qa.category` 一致）：

```bash
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_locomo_sample_baseline.py \
  --sample-id conv-26 \
  --output outputs/membox_baseline_conv26_all.json \
  --memory-dir outputs/membox_baseline_conv26_all_memory
```

后台 `nohup` 模板见 `docs/code-audit/2026-03-28/omem-gpu-runbook-and-logged-restart-zh.md` 第 11.5 节。

## 4. 「评估」——三探针归因框架

### 4.1 单题 smoke（编码 / 检索 / 生成 + LLM 判定）

```bash
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_eval_smoke_once.py \
  --sample-id conv-26 \
  --question-index 0 \
  --output outputs/membox_eval_smoke_conv26_q0.json \
  --memory-dir outputs/membox_eval_smoke_conv26_q0_memory
```

### 4.2 单个 sample 全题归因（耗时长，与 O-Mem 全量归因同级）

```bash
conda run --no-capture-output -n omem-paper100 python -u scripts/run_membox_sample_attribution.py \
  --sample-id conv-26 \
  --output outputs/membox_attr_conv26_all.json \
  --memory-dir outputs/membox_attr_conv26_all_memory
```

结果 JSON 含每题 `probe_results`、`defects`、`summary`（缺陷统计与编码/检索/生成状态计数）。

### 4.3 通过注册表以代码方式使用

```python
from memory_eval.adapters.registry import create_adapter_by_system

adapter = create_adapter_by_system("membox_stable_eval", {
    "api_key": "...",
    "base_url": "https://.../v1",
    "llm_model": "gpt-4o-mini",
})
```

## 5. 常见问题

1. **`api_key` / `base_url` 未配置**  
   适配器会抛出 `RuntimeError`；请检查 `configs/keys.local.json` 或环境变量。

2. **`FileNotFoundError` 与空路径**  
   请使用 **`Membox_stableEval`**，不要对原版 `Membox` 做评测除非已自行合并同样一行 `TRACE_STATS_FILE` 修复。

3. **NLTK / BLEU**  
   若提示缺少 `punkt`，可手动执行：  
   `python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"`

4. **与 O-Mem 的差异**  
   Membox **不依赖本机 GPU** 即可跑 embedding（走 OpenAI 兼容 API）；O-Mem 本地 embedding 需 GPU 与 `torch`。因此 Membox 复现主要瓶颈在 **LLM 调用次数与网络**。

---

更细的技术修复说明见：`docs/code-audit/2026-03-29/membox-stableeval-repair-doc-zh.md`。
