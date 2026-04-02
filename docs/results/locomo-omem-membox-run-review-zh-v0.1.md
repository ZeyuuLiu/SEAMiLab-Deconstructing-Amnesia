# LOCOMO 上 O-Mem / Mem-box 运行结果复核与分析（v0.1）

## 1. 文档目标

这份文档用于复核当前仓库里 O-Mem 与 Mem-box 在 LOCOMO 上的真实运行结果，并回答三个问题：

1. 哪些任务已经正确跑完。
2. 哪些结果可以作为当前有效结果。
3. 这些结果反映了什么现象，以及下一步应该做什么。

## 2. 总结结论

当前可以确认：

1. **O-Mem baseline：成功**
2. **O-Mem eval：成功**
3. **Mem-box baseline：成功**
4. **Mem-box eval：未成功形成结果文件**

因此，当前仓库里可以用于分析的主结果是：

1. `outputs/o_mem_baseline_0331.json`
2. `outputs/o_mem_stable_eval_0331.json`
3. `outputs/membox_stable_eval_conv26_baseline.json`

而：

4. `outputs/membox_eval_Sample0_0331.json`

当前不存在，不能视为已完成评估结果。

## 3. 正确运行复核

## 3.1 O-Mem baseline

结果文件：

- `outputs/o_mem_baseline_0331.json`

日志文件：

- `outputs/nohup_omem_conv26_baseline_0331.log`

成功标志：

1. 存在结构完整的结果 JSON
2. 日志末尾包含：
   - `{"ok": true, "memory_system": "o_mem_stable_eval", "mode": "baseline", ...}`

结论：

- O-Mem baseline 已经正确运行完成。

## 3.2 O-Mem eval

结果文件：

- `outputs/o_mem_stable_eval_0331.json`

日志文件：

- `outputs/nohup_omem_eval_0331.log`

成功标志：

1. 存在结构完整的评估 JSON
2. `summary.total = 10`
3. `summary.ok = 10`
4. `summary.errors = 0`
5. 日志末尾包含：
   - `{"ok": true, "memory_system": "o_mem_stable_eval", "mode": "eval", ...}`

结论：

- O-Mem eval 已经正确运行完成。

## 3.3 Mem-box baseline

结果文件：

- `outputs/membox_stable_eval_conv26_baseline.json`

日志文件：

- `outputs/nohup_membox_conv26_baseline.log`

成功标志：

1. 存在结构完整的结果 JSON
2. 日志中完成了：
   - BUILD
   - Trace
   - Trace linking
3. 日志末尾包含：
   - `{"ok": true, "memory_system": "membox_stable_eval", "mode": "baseline", ...}`

结论：

- Mem-box baseline 已经正确运行完成。

## 3.4 Mem-box eval

日志文件：

- `outputs/nohup_membox_conv26_eval_0331.log`

当前现象：

1. 日志只有 `nohup: 忽略输入`
2. 未产出 `outputs/membox_eval_Sample0_0331.json`

结论：

- Mem-box eval 当前**不能视为正确运行完成**。

## 4. baseline 结果分析

## 4.1 O-Mem baseline

摘要：

1. `count = 199`
2. `correct = 35`
3. `accuracy = 0.17587939698492464`

进一步统计：

1. `POS = 154`
2. `NEG = 45`
3. `POS correct = 35`
4. `NEG correct = 0`

解释：

1. O-Mem 在当前样本 `conv-26` 上的 baseline 整体正确率约为 **17.6%**
2. 所有正确题目都来自 POS
3. 所有 NEG 题都没有被判为正确

这说明当前 baseline 的主要问题不是“完全取不到信息”，而是：

1. 对可回答问题有一定能力，但仍较弱
2. 对应拒答类问题的行为几乎不可用

## 4.2 Mem-box baseline

摘要：

1. `count = 199`
2. `correct = 18`
3. `accuracy = 0.09045226130653267`

进一步统计：

1. `POS = 154`
2. `NEG = 45`
3. `POS correct = 18`
4. `NEG correct = 0`

解释：

1. Mem-box 在当前样本 `conv-26` 上 baseline 正确率约为 **9.0%**
2. 同样全部正确题目都来自 POS
3. 同样所有 NEG 题都没有正确拒答

## 4.3 O-Mem 与 Mem-box baseline 对比

在当前这批结果里：

1. O-Mem baseline 准确率约 **17.6%**
2. Mem-box baseline 准确率约 **9.0%**

也就是说，在 `conv-26` 这 199 题上：

1. O-Mem 明显优于 Mem-box
2. 但两者在 baseline 模式下都还远没有达到高质量问答水平
3. 两者在 NEG 题上的拒答能力都非常差

## 5. O-Mem eval 结果分析

评估文件：

- `outputs/o_mem_stable_eval_0331.json`

当前这次评估只覆盖：

1. `total = 10`
2. `POS = 10`
3. `NEG = 0`

因此这次 eval 是：

> **针对 conv-26 前 10 个 POS 问题的三探针归因评估**

不是全量 199 题评估。

## 5.1 三层状态统计

### 编码层

1. `EXIST = 5`
2. `MISS = 3`
3. `CORRUPT_WRONG = 2`

解释：

1. 只有一半样本能确认目标证据被正确存入
2. 有 3 题属于根本没写进去
3. 还有 2 题属于“写了但写错了”

这说明：

> O-Mem 当前最明显的问题首先发生在编码层。

### 检索层

1. `HIT = 6`
2. `MISS = 4`

解释：

1. 检索成功率略高于一半
2. 但仍有 4 题在原生检索阶段没有把关键证据取出来

### 生成层

1. `PASS = 4`
2. `FAIL = 6`

解释：

1. 即使给定当前链路条件，生成层仍然失败占多数
2. 说明 O-Mem 的问题不只出在上游存取，也出在最终回答阶段

## 5.2 缺陷统计

缺陷计数：

1. `EM = 3`
2. `EW = 2`
3. `RF = 1`
4. `LATE = 1`
5. `NOI = 2`
6. `GF = 1`
7. `GRF = 5`

解释：

1. **编码层缺陷（EM/EW）显著**
   - 表明“未存入”或“存错”是主要问题
2. **生成层缺陷以 GRF 为主**
   - 说明很多题并不是纯幻觉，而是更像“有上下文但推理/使用失败”
3. **检索层也存在 NOI / RF / LATE**
   - 表明检索质量并不稳定，但不是当前第一大矛盾

## 5.3 综合判断

对这次 O-Mem eval，我的判断是：

1. 编码层问题最重
2. 生成层问题次之
3. 检索层有问题，但相对不是最主导瓶颈

也就是说，当前 O-Mem 在这 10 道题上的主要故障链更像：

> **先有部分事实没存进去 / 存错，再叠加部分生成使用失败。**

## 6. 运行正确但仍存在的异常迹象

虽然 O-Mem 的 baseline/eval 都成功落盘，但日志中仍存在异常信号：

1. `RuntimeWarning: Mean of empty slice`
2. `invalid value encountered in scalar divide`
3. 局部 JSON 解析失败重试
4. 局部超时重试

这说明：

1. 运行成功不等于运行完全干净
2. O-Mem 真实系统仍存在一些内部数值稳定性与生成解析鲁棒性问题

但因为最终结果文件完整落盘，当前可以把它视为：

- **成功运行，但伴随告警**

## 7. 当前最重要的额外问题：输出文件里曾写入密钥

本次复查还发现：

1. 旧结果文件里曾包含明文 API key

目前已做处理：

1. 现有几份主要结果文件已手动改成 `***REDACTED***`
2. pipeline 与 adapter manifest 的后续输出逻辑也已加入脱敏

但建议你后续仍然：

1. 不要把旧结果文件直接外发
2. 重新生成正式归档结果

## 8. 当前可以对外怎么表述

如果你现在要对这轮运行做项目内部说明，我建议口径如下：

1. **评估框架已成功接入并真实运行 O-Mem 与 Mem-box**
2. **O-Mem baseline / eval 已成功跑通**
3. **Mem-box baseline 已成功跑通**
4. **Mem-box eval 当前尚未成功形成结果文件，需要单独补跑**

如果你要说结果质量，则可以进一步表述为：

1. O-Mem 在当前 sample 上 baseline 表现优于 Mem-box
2. 两者 baseline 在 NEG 题上的拒答能力都很弱
3. O-Mem 的三探针评估显示主要瓶颈在编码层，其次在生成层

## 9. 下一步建议

### 必做

1. 重新补跑 Mem-box eval

### 建议

1. 把 O-Mem eval 的 limit 从 10 扩到更大范围
2. 单独统计 NEG 题的 eval 结果
3. 为 Mem-box 也跑出对应的 eval 文件，形成可对比三探针分析

## 10. 结论

当前已经可以确认：

1. **O-Mem：baseline 成功，eval 成功**
2. **Mem-box：baseline 成功，eval 未完成**

并且从结果上看：

1. O-Mem baseline 整体优于 Mem-box baseline
2. 两个系统在 NEG 题上的拒答行为都明显不足
3. O-Mem 的三探针归因显示，当前主要瓶颈是编码层而非单纯检索层
