# 评测框架代码改造说明与运行指南（v0.3）

## 1. 文档目标

这份文档对应本轮“按照现有方案直接修改代码”的实现结果。

目标有四个：

1. 说明本轮到底改了哪些代码
2. 解释这些改动分别解决了什么问题
3. 说明本轮复查时发现的漏洞与风险点
4. 给出可以直接复现的运行与检查指令

***

## 2. 本轮改造结论

本轮已经完成的核心改造包括：

1. **Correctness Judge 真源收敛**
   - generation 在线答案与 oracle 答案的 correctness 判分都统一走 `CorrectnessJudge`
   - online 判分只看 `retrieved_context`
   - oracle 判分只看 `oracle_context`
2. **POS / NEG 判分逻辑补强**
   - POS 题中显式拒答会被硬否决
   - NEG 题继续保留 refusal-aware 判定空间
   - 中文拒答表达现在也会被识别
3. **编码层输入补强**
   - 编码层除全量 memory export 外
   - 还会合并当前 `question` 的原生检索 shadow
   - 还会合并 `f_key` 定向检索 shadow
   - 并把两类 shadow 统计写入 coverage report
4. **baseline 输出结构补齐**
   - baseline 现在支持逐题 JSON 落盘
   - 支持 `run_summary.json`
   - 支持 `question_index.json`
   - 支持 per-question `artifact_refs`
   - 支持单题异常隔离与 errors 汇总
5. **MemBox 透明性补强**
   - MemBox worker 内部原先吞掉的 embedding / chat 异常
   - 现在会记录到 `runtime_warnings`
   - 后续可在 artifact / trace 中看到对应告警

***

## 3. 本轮具体修改

## 3.1 Correctness Judge 相关

### `src/memory_eval/eval_core/prompts.py`

本轮把 correctness prompt 改成了更接近 TiMem 风格的宽松语义判分：

1. 新增 `judge_mode`
   - `online`
   - `oracle`
2. 明确 online 判分约束
   - online 只能使用 `question`
   - `gold answer`
   - `generated answer`
   - `retrieved_context`
   - 不允许利用 `oracle_context` 补答案
3. 明确 POS / NEG 差异
   - POS：如果回答本质上是拒答，必须判错
   - NEG：重点检查是否拒答以及是否编造
4. 输出 JSON 更结构化
   - `label`
   - `reason`
   - `semantic_match`
   - `temporal_match`
   - `refusal_expected`
   - `refusal_present`
   - `fabricated`

### `src/memory_eval/eval_core/llm_assist.py`

1. `llm_judge_answer_correctness()` 现在透传 `judge_mode`
2. 统一补齐结构化字段
3. 把 `label` 规范成 `CORRECT|WRONG`
4. 生成 `correct` 布尔字段，供下游统一消费

### `src/memory_eval/eval_core/correctness_judge.py`

这是本轮最关键的逻辑修复之一。

原先存在两个问题：

1. 只要打开 LLM correctness judge，若 LLM 返回空，系统就会把结果直接当错
2. 即使用户允许 rule fallback，也不会真正回退

本轮修复后：

1. 如果 LLM judge 可用，就采用 LLM 结果
2. 如果 LLM judge 不可用，且没有要求必须成功，就自动回退到规则判分
3. `judge_payload` 中新增：
   - `hard_veto`
   - `llm_available`
   - `judge_mode`
   - `rule_correct`

这避免了一个很隐蔽但非常致命的问题：

- **在未配置可用 judge API 时，baseline / eval 会把本来可由规则正确判定的样本全部压成错误**

### `src/memory_eval/eval_core/utils.py`

`is_abstain()` 增加了中文拒答模式：

1. `不知道`
2. `不清楚`
3. `无法判断`
4. `无法回答`
5. `没有提到`
6. `未提及`
7. `没有相关信息`

这修复了另一个实际漏洞：

- **POS 样本里中文“拒答”不会触发 hard veto**

***

## 3.2 Generation 相关

### `src/memory_eval/eval_core/generation.py`

本轮的 generation 改造主要是为了完成“judge 真源统一”和“online/oracle 隔离”。

#### 已完成内容

1. `GenerationProbeInput` 新增 `retrieved_context`
2. `evaluate_generation_probe_with_adapter()` 会主动调用原系统 `retrieve_original()`
3. online correctness 判分只传 `retrieved_context`
4. oracle correctness 判分只传 `oracle_context`
5. evidence 中补入：
   - `online_correctness`
   - `oracle_correctness`
   - `judge_payload`
   - `retrieved_context`

#### 本轮顺带修复

本文件在之前修改中残留了一处字典结构拼接错误，导致语法异常。该问题已修复并通过测试。

***

## 3.3 Encoding 相关

### `src/memory_eval/eval_core/encoding_agent.py`

编码层这次的关键改造是把“原系统 query-facing evidence”真正纳入候选束。

#### 现在的合并逻辑

若开启 `encoding_merge_native_retrieval`：

1. 先用 `sample.question` 调 `retrieve_original()`
2. 再把 `f_key` 压成检索串
3. 用这个 `f_key query` 再调一次 `retrieve_original()`
4. 把两次结果都合并进编码候选集合
5. 同时保留为 `native_retrieval_shadow`

#### coverage report 新增指标

1. `query_retrieval_shadow_count`
2. `f_key_retrieval_shadow_count`
3. `used_native_retrieval_shadow`

这项改动的目的不是把检索层硬塞进编码层，而是让编码层能看到：

- **这个系统面对当前 query 时，自己能拿出什么记忆**
- **如果 query 太自然，还能否通过 f\_key 定向把关键事实重新打出来**

这更符合 MemBox 这种摘要化记忆系统的观察方式。

***

## 3.4 baseline 脚本相关

### `scripts/run_real_memory_eval.py`

baseline 模式本轮做了实质性补齐。

#### 新增输出布局

现在 `--output` 如果是：

1. `xxx.json`
   - 主 bundle 写入 `xxx.json`
   - 逐题目录写入 `xxx/`
2. `xxx/`
   - 主 bundle 写入 `xxx/result_bundle.json`
   - 逐题目录仍在 `xxx/`

#### 新增能力

1. 单题 try/except 异常隔离
2. baseline 阶段拉取 `retrieved_context`
3. per-question JSON 落盘
4. `run_summary.json`
5. `question_index.json`
6. `errors` 汇总
7. `artifact_refs` 记录
8. 顶层结构化失败输出

这意味着 baseline 不再只是一个“只看最终 accuracy 的黑盒脚本”，而是已经具备和 eval 接近的可观测性。

***

## 3.5 MemBox 透明性相关

### `src/memory_eval/adapters/membox_adapter.py`

本轮没有强行把 MemBox 改成“遇错就抛异常退出”，因为这会直接破坏现有 reproducer 行为。

但针对之前最危险的“静默吞异常”问题，已经先补了一层透明化：

1. embedding 请求失败会记录 warning
2. embedding 响应结构异常会记录 warning
3. chat completion 失败会记录 warning
4. `run_ctx` 中新增 `runtime_warnings`
5. `export_build_artifact()` 与 `build_trace_for_query()` 中会带出 `runtime_warnings`

因此现在至少可以区分：

1. 系统真的检不到
2. 还是远端模型/embedding 失败后被降级成空结果

***

## 4. 本轮复查发现并修复的漏洞

本轮不是只改功能，也专门做了一次漏洞式复查。实际修掉的问题有：

### 4.1 correctness fallback 失效

问题：

- 配置允许 correctness rule fallback 时，LLM judge 一旦返回空，系统仍会把结果直接判成错误

影响：

- 在 judge API 不可用时，baseline / eval 结果会被系统性压低

处理：

- 只有在 LLM payload 真正可用时才采用 LLM correctness
- 否则自动回退到 rule correctness

### 4.2 中文拒答未被识别

问题：

- `hard_veto` 依赖 `is_abstain()`，但原先几乎只覆盖英文拒答

影响：

- POS 样本里如果模型输出“我不知道”“未提及”之类中文拒答，可能不会被强制判错

处理：

- 扩充中文拒答模式

### 4.3 generation.py 残留语法错误

问题：

- 之前修改过程中残留字典拼接错误

影响：

- 直接导致模块无法导入，测试收集失败

处理：

- 修正结构并重新跑测试

### 4.4 测试入口不稳定

问题：

- `tests/test_adapters_registry.py` 缺少稳定的 `src/` 路径注入
- mock pipeline 测试没有断言 `errors == []`

影响：

- 测试可能“表面通过”，但实际包含隐藏错误

处理：

- 补齐路径注入
- 强化 mock pipeline 断言

***

## 5. 本轮新增测试与验证结果

本轮新增或补强了以下验证：

1. `tests/test_eval_agents.py`
   - correctness judge 的 POS refusal hard veto
   - LLM 不可用时 correctness 回退到规则判分
   - 编码层同时纳入 question shadow 与 f\_key shadow
2. `tests/test_run_real_memory_eval.py`
   - baseline bundle 输出
   - `run_summary.json`
   - `question_index.json`
   - per-question JSON
   - `retrieved_context`
   - `judge_payload`
3. `scripts/test_eval_pipeline_mock.py`
   - 增加 `errors == []` 断言
4. `tests/test_adapters_registry.py`
   - 修复导入路径，保证可稳定执行

### 本地实际验证结果

已执行：

```bash
python -m pytest tests/test_eval_agents.py tests/test_run_real_memory_eval.py tests/test_adapters_registry.py -q
python scripts/test_eval_pipeline_mock.py
python scripts/run_real_memory_eval.py --help
```

结果：

1. `14 passed`
2. mock pipeline 通过
3. CLI 帮助正常输出

***

## 6. 运行指令指南

下面给出的是当前建议的运行方式。

## 6.1 先做轻量检查

在项目根目录执行：

```bash
python -m pytest tests/test_eval_agents.py tests/test_run_real_memory_eval.py tests/test_adapters_registry.py -q
python scripts/test_eval_pipeline_mock.py
python scripts/run_real_memory_eval.py --help
```

如果这三步都通过，说明：

1. 核心评测逻辑可导入
2. baseline/eval 落盘结构没有被改坏
3. CLI 参数入口正常

***

## 6.2 O-Mem 运行命令

### baseline

```bash
nohup conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_baseline_0407.json \
  > outputs/nohup_o_mem_conv26_baseline_0407.log 2>&1 &
```

### eval

```bash
nohup conda run -n memeval-omem-v1 python scripts/run_real_memory_eval.py \
  --memory-system o_mem_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --embedding-model-path /home/4T/liuzeyu/memory-eval/SEAMiLab-Deconstructing-Amnesia/Qwen/Qwen3-Embedding-0.6B \
  --output outputs/o_mem_conv26_eval_0407.json \
  > outputs/nohup_o_mem_conv26_eval_0407.log 2>&1 &
```

***

## 6.3 MemBox 运行命令

### build

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode build \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_build_manifest_0407.json \
  > outputs/nohup_membox_conv26_build_0407.log 2>&1 &
```

### baseline

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode baseline \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --build-manifest outputs/membox_conv26_build_manifest_0407.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_baseline_0407.json \
  > outputs/nohup_membox_conv26_baseline_0407.log 2>&1 &
```

### eval

```bash
nohup conda run -n memeval-membox-v1 python scripts/run_real_memory_eval.py \
  --memory-system membox_stable_eval \
  --mode eval \
  --dataset data/locomo10.json \
  --sample-id conv-26 \
  --build-manifest outputs/membox_conv26_build_manifest_0407.json \
  --keys-path configs/keys.local.json \
  --request-timeout-sec 120 \
  --output outputs/membox_conv26_eval_0407.json \
  > outputs/nohup_membox_conv26_eval_0407.log 2>&1 &
```

***

## 6.4 实时查看运行状态

### 查看日志尾部

```bash
tail -n 60 outputs/nohup_o_mem_conv26_baseline_0407.log
tail -n 60 outputs/nohup_o_mem_conv26_eval_0407.log
tail -n 60 outputs/nohup_membox_conv26_build_0407.log
tail -n 60 outputs/nohup_membox_conv26_baseline_0407.log
tail -n 60 outputs/nohup_membox_conv26_eval_0407.log
```

### 查看主结果文件

```bash
python -m json.tool outputs/o_mem_conv26_baseline_0407.json | head -n 80
python -m json.tool outputs/o_mem_conv26_eval_0407.json | head -n 80
python -m json.tool outputs/membox_conv26_baseline_0407.json | head -n 80
python -m json.tool outputs/membox_conv26_eval_0407.json | head -n 80
```

### 查看 baseline 逐题目录

```bash
find outputs/o_mem_conv26_baseline_0407 -maxdepth 2 -type f | sort
find outputs/membox_conv26_baseline_0407 -maxdepth 2 -type f | sort
```

### 查看某一题的逐题 JSON

```bash
python -m json.tool outputs/o_mem_conv26_baseline_0407/conv-26/conv-26_0.json
python -m json.tool outputs/membox_conv26_baseline_0407/conv-26/conv-26_0.json
```

如果你的 question 文件名不是这个名字，可以先看 `question_index.json`：

```bash
python -m json.tool outputs/o_mem_conv26_baseline_0407/question_index.json | head -n 80
python -m json.tool outputs/membox_conv26_baseline_0407/question_index.json | head -n 80
```

***

## 6.5 重点检查哪些字段

### baseline 主 bundle

重点看：

1. `summary.final_accuracy`
2. `summary.errors`
3. `question_index`
4. `errors`

### 逐题 JSON

重点看：

1. `answer_online`
2. `retrieved_context`
3. `final_correct`
4. `judge_label`
5. `judge_reason`
6. `judge_payload`
7. `artifact_refs`

### eval 结果

重点看：

1. `states.enc`
2. `states.ret`
3. `states.gen`
4. `probe_results.enc.evidence.coverage_report`
5. `probe_results.gen.evidence.online_correctness`
6. `probe_results.gen.evidence.oracle_correctness`

对于 MemBox，尤其要重点看：

1. `query_retrieval_shadow_count`
2. `f_key_retrieval_shadow_count`
3. `runtime_warnings`

***

## 7. 目前仍然建议继续补的内容

本轮已经把关键逻辑打通，但还不是最终终态。

仍建议继续补：

1. **MemBox runtime warning 的结果侧透传**
   - 当前 warning 已进入 `run_ctx` / artifact
   - 但还可以继续在最终评测结果里显式汇总
2. **真实 O-Mem / MemBox 端到端回归**
   - 本轮没有直接长时间重跑真实 0407 命令
   - 建议按上面命令由你在目标环境执行
3. **judge 可观测性继续加强**
   - 后续可继续记录 prompt version
   - judge raw response
   - online/oracle 分路统计
4. **更细的 MemBox 失败分类**
   - 当前已能看到 warning
   - 后续可继续区分 embedding 失败、chat 失败、retriever 空返回、box 内容缺失

***

## 8. 最终结论

本轮改造已经把你前面方案中最关键的四个要求真正落到了代码里：

1. judge 真源统一
2. online / oracle 隔离
3. 编码层纳入 query 与 f\_key 双路原生检索证据
4. baseline 具备逐题落盘与异常隔离

同时，本轮复查还额外修掉了几个会直接污染结果可信度的问题：

1. LLM judge fallback 失效
2. 中文拒答不识别
3. generation 语法残留错误
4. 测试入口不稳定

因此，从“方案已经落地到可验证代码”这个角度看，这一轮已经达到可继续跑真实实验的状态。
