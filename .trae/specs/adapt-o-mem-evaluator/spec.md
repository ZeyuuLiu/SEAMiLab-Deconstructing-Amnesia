# O-Mem 适配评估框架 Spec

## Why
当前评估框架已完成三探针核心与数据集构建，但尚未接入真实记忆系统适配器。为保证后续跨系统评估可用性与稳定性，需要先完成 O-Mem 到 `memory_eval` 的标准化适配，并提供低成本可复现实验入口。

## What Changes
- 新增 O-Mem 适配层实现，满足 `EvalAdapterProtocol`、`EncodingAdapterProtocol`、`RetrievalAdapterProtocol`、`GenerationAdapterProtocol` 的调用契约。
- 新增 O-Mem 结果标准化逻辑，将 O-Mem 内部记忆与检索结构映射为评估核心可消费的 `memory_view`、`retrieved_items`、`answer_oracle`。
- 新增 O-Mem 轻量运行脚本，用于单样本/小样本联调（避免全量 benchmark）。
- 新增最小验证流程：可从 LOCOMO 样本构建输入，运行 O-Mem 适配器并输出单条 `AttributionResult`。
- 增加配置约束：API Key 与 Base URL 仅通过本地配置或环境变量读取，不在仓库中硬编码。

## Impact
- Affected specs: 适配器协议实现、三探针运行输入一致性、低成本验证流程
- Affected code:
  - `src/memory_eval/eval_core/adapter_protocol.py`
  - `src/memory_eval/eval_core/models.py`
  - `src/memory_eval/dataset/locomo_builder.py`
  - `system/O-Mem/memory_chain/memory.py`
  - `system/O-Mem/memory_chain/memory_manager.py`
  - `system/O-Mem/config.yaml.example`
  - `scripts/`（新增 O-Mem 适配联调脚本）

## ADDED Requirements
### Requirement: O-Mem 适配器实现
系统 SHALL 提供一个 O-Mem 适配器，实现评估核心所需的统一接口，并可对单 query 输出完整 `AdapterTrace`。

#### Scenario: 生成评估输入
- **WHEN** 给定 `EvalSample(question, oracle_context, f_key)` 与已构建的 O-Mem 运行上下文
- **THEN** 适配器返回包含 `memory_view`、`retrieved_items`、`answer_oracle` 的 `AdapterTrace`
- **THEN** 返回字段满足评估核心当前数据类型要求（可直接传入 `ParallelThreeProbeEvaluator.evaluate`）

### Requirement: O-Mem 记忆与检索标准化
系统 SHALL 将 O-Mem 的多层记忆结构和检索输出标准化为稳定、可追踪的评估输入结构。

#### Scenario: 记忆导出标准化
- **WHEN** 编码探针请求全量记忆导出
- **THEN** 适配器输出统一列表项，至少包含可读文本字段与来源元信息（层级/轮次/角色）
- **THEN** 输出可被编码探针匹配逻辑稳定消费

#### Scenario: 检索结果标准化
- **WHEN** 检索探针请求原始检索序列
- **THEN** 适配器输出有序条目，包含文本与可用分数（缺失分数时提供可审计降级策略）
- **THEN** 条目可映射为 `RetrievedItem` 列表，保持原始顺序

### Requirement: Oracle 作答路径
系统 SHALL 为生成探针提供“给定 oracle_context 的作答”调用路径，以隔离检索因素。

#### Scenario: 生成探针调用
- **WHEN** 生成探针调用 `generate_oracle_answer`
- **THEN** O-Mem 侧模型基于传入 `oracle_context` 生成答案
- **THEN** 输出用于 `P_gen` 判定，不复用常规检索拼接上下文

### Requirement: 轻量联调脚本
系统 SHALL 提供一个可控成本的运行脚本，支持单样本或小样本适配验证。

#### Scenario: 单样本联调
- **WHEN** 用户以参数指定 `question_id` 或 `query`，并设置小 `limit`
- **THEN** 脚本仅处理目标样本并输出三探针结果与关键证据
- **THEN** 默认不触发全量 benchmark

### Requirement: 凭据安全读取
系统 SHALL 通过本地配置文件或环境变量读取 API 凭据，避免明文写入代码与版本库。

#### Scenario: 凭据注入
- **WHEN** 用户提供 API Key 与 Base URL
- **THEN** 运行时从环境变量或本地未跟踪配置加载
- **THEN** 缺失凭据时给出明确错误提示，不回退到硬编码

## MODIFIED Requirements
### Requirement: 评估流程从 Mock 适配器扩展到真实系统适配器
现有流程以脚本内 Mock 观测值验证探针逻辑。修改后流程需支持真实 O-Mem 运行结果接入，且保持评估核心接口与缺陷归因规则不变。

## REMOVED Requirements
### Requirement: 无
**Reason**: 本次仅新增适配能力，不移除既有能力。  
**Migration**: 无迁移需求。
