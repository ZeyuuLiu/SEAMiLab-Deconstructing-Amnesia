# O-Mem Real Run Sample0 Report v0.5.2

## 1. Goal / 目标

**CN**  
在真实 O-Mem 运行模式下（非 lightweight fallback），对 LOCOMO `sample0` 执行完整评测，并通过三探针评估框架输出归因结果。

**EN**  
Run LOCOMO `sample0` with the real O-Mem runtime (not lightweight fallback), then evaluate it through the three-probe framework and produce attribution output.

## 2. Environment Setup / 环境搭建

### 2.1 Conda environment / Conda 环境

**CN**
1. 创建环境：`conda create -n omem-eval python=3.10 -y`
2. 安装本项目：`conda run -n omem-eval python -m pip install -e .`
3. 安装 O-Mem 依赖：`conda run -n omem-eval python -m pip install -r system/O-Mem/requirements.txt`

**EN**
1. Create env: `conda create -n omem-eval python=3.10 -y`
2. Install this project: `conda run -n omem-eval python -m pip install -e .`
3. Install O-Mem deps: `conda run -n omem-eval python -m pip install -r system/O-Mem/requirements.txt`

### 2.2 Extra fixes discovered during setup / 安装阶段发现的额外修复

**CN**
1. 缺失 `nltk`：补装 `conda run -n omem-eval python -m pip install nltk`
2. `FlagEmbedding` 与 `transformers` 版本冲突（`is_torch_fx_available` 导入失败）
   - 修复：降级到兼容线  
   `conda run -n omem-eval python -m pip install "transformers<5,>=4.41.0" "tokenizers<0.20"`

**EN**
1. Missing `nltk`: installed via `conda run -n omem-eval python -m pip install nltk`
2. `FlagEmbedding` / `transformers` incompatibility (`is_torch_fx_available` import error)
   - Fix: pin compatible versions  
   `conda run -n omem-eval python -m pip install "transformers<5,>=4.41.0" "tokenizers<0.20"`

## 3. Runtime Validation Before Evaluation / 评测前运行校验

**CN**
通过 `scripts/audit_o_mem_adapter.py` 校验：
1. 适配器协议实现完整（encoding/retrieval/generation 三协议均命中 `OMemAdapter`）。
2. 真实 O-Mem 运行时可导入（`runtime_import_check.return_code = 0`）。

**EN**
Validation by `scripts/audit_o_mem_adapter.py`:
1. Full adapter protocol coverage (encoding/retrieval/generation all implemented by `OMemAdapter`).
2. Real O-Mem runtime importable (`runtime_import_check.return_code = 0`).

## 4. Execution Flow / 实际执行流程

### 4.1 High-level flow / 总体流程

**CN**
1. 读取 `data/locomo10.json`，按 `limit=1` 仅取 `sample0`（`conv-26:0`）。
2. 由 `OMemAdapter(use_real_omem=True)` 构建真实 O-Mem 运行态：
   - 初始化 `MemoryChain` 与 `MemoryManager`
   - 加载 `SentenceTransformer("all-MiniLM-L6-v2")`
   - 写入完整对话并更新工作记忆/情节记忆/角色画像
3. Pipeline 调用三探针并行评估：
   - Encoding: `export_full_memory` + `find_memory_records`
   - Retrieval: `retrieve_original(top_k=5)`
   - Generation: `generate_oracle_answer(oracle_context)`
4. 汇总归因并输出 JSON 报告。

**EN**
1. Load `data/locomo10.json` and run only `sample0` with `limit=1` (`conv-26:0`).
2. Build real O-Mem runtime via `OMemAdapter(use_real_omem=True)`:
   - Initialize `MemoryChain` and `MemoryManager`
   - Load `SentenceTransformer("all-MiniLM-L6-v2")`
   - Ingest full conversation and update working/episodic/persona memories
3. Pipeline executes three probes in parallel:
   - Encoding: `export_full_memory` + `find_memory_records`
   - Retrieval: `retrieve_original(top_k=5)`
   - Generation: `generate_oracle_answer(oracle_context)`
4. Merge attribution and write JSON report.

### 4.2 Embedding model note / Embedding 模型说明

**CN**
embedding 不是仓库内静态文件，而是由 `sentence-transformers` 运行时自动下载并缓存。  
缓存目录已确认存在：`C:\Users\24256\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2`。

**EN**
The embedding model is not a checked-in repo file; it is auto-downloaded and cached by `sentence-transformers` at runtime.  
Cache location confirmed: `C:\Users\24256\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2`.

## 5. Errors and Handling Timeline / 报错与处理时间线

### Error A: PowerShell command chaining / PowerShell 命令连接符错误

**CN**
- 现象：使用 `&&` 在 PowerShell 中执行失败（`InvalidEndOfLine`）。
- 处理：改为 `;` 顺序执行。

**EN**
- Symptom: `&&` chaining failed in PowerShell (`InvalidEndOfLine`).
- Fix: switched to sequential `;`.

### Error B: Missing runtime dependency / 缺少依赖

**CN**
- 现象：`ModuleNotFoundError: No module named 'nltk'`
- 处理：安装 `nltk`。

**EN**
- Symptom: `ModuleNotFoundError: No module named 'nltk'`
- Fix: installed `nltk`.

### Error C: FlagEmbedding/Transformers incompatibility / 版本不兼容

**CN**
- 现象：`ImportError: cannot import name 'is_torch_fx_available'`
- 根因：`FlagEmbedding` 与已装 `transformers` 版本不匹配。
- 处理：将 `transformers` 降至 4.x 兼容线并匹配 `tokenizers`。

**EN**
- Symptom: `ImportError: cannot import name 'is_torch_fx_available'`
- Root cause: version mismatch between `FlagEmbedding` and installed `transformers`.
- Fix: pinned `transformers` to compatible 4.x line with matching `tokenizers`.

### Error D: Adapter JSON arg quoting / 适配器 JSON 参数转义

**CN**
- 现象：CLI 传 `--adapter-config-json` 时 JSON 解析失败。
- 处理：改为 Python 入口直接构建 `OMemAdapterConfig` 对象执行。

**EN**
- Symptom: JSON decode failure when passing `--adapter-config-json`.
- Fix: switched to Python-entry execution with direct `OMemAdapterConfig` construction.

### Runtime warnings in O-Mem internals / O-Mem 内部运行告警

**CN**
- 现象：长日志中多次出现 `JSONDecodeError`（`wm_to_em_router*`）。
- 说明：这是 O-Mem 内部对 LLM JSON输出解析时的失败重试日志；本次任务最终 `exit_code=0` 并成功产出结果。

**EN**
- Symptom: repeated `JSONDecodeError` in `wm_to_em_router*` paths.
- Note: these are O-Mem internal parse/retry events for LLM JSON outputs; this run still completed with `exit_code=0` and produced outputs.

## 6. Final Outputs / 最终产物

**CN**
1. 评测结果：`outputs/eval_pipeline_omem_real_sample0.json`
2. 真实 O-Mem 记忆缓存：`outputs/omem_real_memory/conv-26`
3. 审计结果（通过）：`scripts/audit_o_mem_adapter.py` 运行输出

**EN**
1. Evaluation output: `outputs/eval_pipeline_omem_real_sample0.json`
2. Real O-Mem memory cache: `outputs/omem_real_memory/conv-26`
3. Audit (pass): output from `scripts/audit_o_mem_adapter.py`

## 7. Result Interpretation (sample0) / sample0 结果解读

### 7.1 Summary / 汇总

**CN**
- 总样本：1
- 任务类型：POS=1, NEG=0
- 状态：
  - Encoding: `MISS`
  - Retrieval: `MISS`
  - Generation: `PASS`
- 缺陷集合：`[EM]`

**EN**
- Total samples: 1
- Task type: POS=1, NEG=0
- States:
  - Encoding: `MISS`
  - Retrieval: `MISS`
  - Generation: `PASS`
- Defects: `[EM]`

### 7.2 Probe-level evidence / 各探针证据

**CN**
1. Encoding (`MISS`, `EM`)
   - 证据：`No key-fact match in candidate records`
   - `candidate_count=410`
   - 未匹配事实为带 `Caroline` 说话人前缀的时间事实。
2. Retrieval (`MISS`, 无缺陷)
   - 未命中 `f_key`，但因编码层是 `MISS`，`RF` 被归因收敛规则抑制。
   - `decision_trace`: `Suppressed RF because encoding state is MISS.`
3. Generation (`PASS`)
   - `answer_oracle="7 May 2023"` 与 `answer_gold="7 May 2023"` 一致。

**EN**
1. Encoding (`MISS`, `EM`)
   - Evidence: `No key-fact match in candidate records`
   - `candidate_count=410`
   - Unmatched fact is the time-aware key fact with `Caroline` speaker prefix.
2. Retrieval (`MISS`, no defect)
   - No `f_key` hit, but `RF` is suppressed because encoding is `MISS`.
   - `decision_trace`: `Suppressed RF because encoding state is MISS.`
3. Generation (`PASS`)
   - `answer_oracle="7 May 2023"` matches `answer_gold="7 May 2023"`.

## 8. Why this attribution happened / 本次归因为何是这样

**CN**
核心原因是事实字符串规范化不一致：  
`f_key` 使用说话人名 `Caroline`，而 O-Mem 记忆条目中部分同义内容使用 `User` 标识，导致 encoding/retrieval 的严格匹配未命中；但在给定 `oracle_context` 的生成阶段，答案是正确的。

**EN**
The main reason is normalization mismatch in fact strings:  
`f_key` uses speaker name `Caroline`, while some O-Mem memory entries represent equivalent content with `User`; strict matching misses in encoding/retrieval, while generation remains correct under `oracle_context`.

## 9. Next Improvements / 下一步改进建议

**CN**
1. 在 `find_memory_records` 与 `rank_and_hit` 前增加 speaker alias 归一化（`User` ↔ 真实用户名）。
2. 为 O-Mem 路由 JSON 输出增加更严格的 schema 与重试退避策略，减少 `JSONDecodeError` 噪声。
3. 将真实 O-Mem 评测扩展到更多样本（例如 limit=10 或全量），并输出缺陷分布对比。

**EN**
1. Add speaker-alias normalization (`User` ↔ real username) before fact matching and retrieval-hit checks.
2. Strengthen O-Mem JSON output schema/retry-backoff to reduce `JSONDecodeError` noise.
3. Scale real O-Mem evaluation to larger slices (e.g., limit=10 or full set) and compare defect distributions.
