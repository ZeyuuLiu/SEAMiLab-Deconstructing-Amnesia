# 毕业论文摘要候选版本（v0.1）

## 说明

下面给出 4 组中英文摘要候选版本，分别强调不同侧重点。当前论文主稿中默认写入的是“版本 A（推荐版）”。

## 版本 A：问题导向 + 框架贡献（推荐）

### 中文摘要

随着大语言模型从单轮问答逐步迈向跨会话、长时程交互，长期记忆系统已成为智能体保持连续性、个性化与任务一致性的关键基础设施。然而，现有评测大多停留在最终答题正确率层面，难以进一步回答错误究竟来源于记忆未被正确写入、运行时未能有效检索，还是生成阶段没有忠实利用证据。针对这一问题，本文面向长期记忆智能体评测场景，设计并实现了一套统一的细粒度归因评测框架。本文在调研大量记忆系统与评测文献的基础上，将异构记忆系统统一抽象为编码、检索、生成三个核心层面，并据此构建三个并行评测探针及一个最终归因代理，用于定位系统失效来源。围绕该框架，本文进一步设计统一数据契约、统一适配器协议、统一语义判分机制以及结构化结果落盘方式，使不同记忆系统能够在同一评测层下进行对齐分析。本文同时完成了框架工程实现，并预留了实验结果留白区域，以支持后续持续补充量化结果与跨系统对比。该工作为长期记忆系统的统一评测、问题定位与后续扩展提供了可复用基础。

### 英文摘要

As large language models move from single-turn question answering to cross-session and long-horizon interaction, long-term memory systems have become a critical infrastructure for maintaining continuity, personalization, and task consistency in intelligent agents. However, most existing evaluations remain at the level of final answer accuracy, and cannot further determine whether a failure is caused by incorrect memory encoding, ineffective runtime retrieval, or unfaithful answer generation. To address this problem, this thesis designs and implements a unified fine-grained attribution framework for evaluating long-term memory agents. Based on an extensive survey of memory systems and evaluation literature, heterogeneous memory systems are abstracted into three core layers, namely encoding, retrieval, and generation. On this basis, the framework introduces three parallel evaluation probes together with a final attribution agent for locating the source of failures. Around this design, the thesis further establishes a unified data contract, a unified adapter protocol, a unified semantic judgement mechanism, and a structured result persistence scheme, enabling different memory systems to be analyzed under the same evaluation layer. The engineering implementation of the framework is completed, while placeholders are reserved for pending experimental results and future cross-system comparisons. This work provides a reusable foundation for unified evaluation, failure diagnosis, and extensible benchmarking of long-term memory systems.

## 版本 B：方法导向 + 三层抽象

### 中文摘要

长期记忆系统已经成为大模型智能体的重要组成部分，但不同系统在内部结构、记忆组织与运行方式上差异较大，导致现有评测方法难以在统一标准下对其进行细粒度比较。本文通过系统调研发现，尽管现有记忆系统表现形式多样，但其核心链路普遍可以抽象为记忆编码、运行检索与答案生成三个阶段。基于这一认识，本文提出一套三层并行评测框架：编码探针用于判断关键信息是否被正确写入，检索探针用于判断运行时是否命中有效证据，生成探针用于判断系统是否基于证据给出正确回答，最终归因代理则负责对三层结果进行统一收敛。为提升框架的鲁棒性与可扩展性，本文进一步设计了统一适配器协议、统一样本组织方式、统一 CorrectnessJudge 语义判分机制以及逐题结果落盘结构。本文完成了该框架的工程实现，并以未来可持续接入更多记忆系统为目标进行了通用化设计。实验结果部分暂留待后续真实运行后补写。

### 英文摘要

Long-term memory systems have become an essential component of LLM-based agents, yet existing systems vary greatly in their internal structures, memory organization strategies, and runtime workflows. As a result, current evaluation methods often struggle to compare them under a unified and fine-grained standard. Through a systematic survey, this thesis observes that despite their diversity, most memory systems can be abstracted into three key stages: memory encoding, runtime retrieval, and answer generation. Based on this insight, a three-layer parallel evaluation framework is proposed. The encoding probe evaluates whether critical information is properly stored, the retrieval probe evaluates whether relevant evidence is effectively retrieved at runtime, and the generation probe evaluates whether the final answer is correctly produced from the evidence. A final attribution agent then consolidates the outputs of the three probes into a unified diagnosis. To improve robustness and extensibility, the thesis further introduces a unified adapter protocol, a standardized sample organization scheme, a shared CorrectnessJudge for semantic judgement, and a per-question structured result persistence format. The framework has been fully implemented with the explicit goal of supporting future integration of additional memory systems. The experimental result section is intentionally left as a placeholder until real runs are completed.

## 版本 C：工程导向 + 系统实现

### 中文摘要

面向长期交互场景的记忆系统评测不仅是一个算法判分问题，更是一个涉及统一接口、运行流程、错误定位与结果组织的系统工程问题。针对当前长期记忆系统评测中存在的黑箱化、不可归因和复现困难等问题，本文设计并实现了一套面向真实系统的评测基础设施。该框架以 LoCoMo 等长对话任务为背景，围绕编码、检索、生成三个核心环节组织评测逻辑，支持统一数据样本构建、异构系统适配、语义判分、逐题日志输出以及结构化结果落盘。与仅返回最终正确率的传统评测方式相比，本文方法能够进一步指出问题究竟发生在哪一层，并为记忆系统调试提供直接依据。本文同时强调框架的通用性与鲁棒性，避免把评测逻辑绑定到单个系统内部结构，为后续接入更多记忆系统保留了扩展空间。当前论文已经完成方法、系统与实验设计部分，实验结果待后续补充。

### 英文摘要

Evaluating long-term memory systems for persistent interactive agents is not merely a problem of answer scoring, but a systems engineering problem involving unified interfaces, execution workflows, failure diagnosis, and result organization. To address the black-box nature, weak attribution capability, and reproducibility challenges of existing evaluations, this thesis designs and implements an evaluation infrastructure for real memory systems. Grounded in long-conversation tasks such as LoCoMo, the framework organizes its evaluation logic around three core stages: encoding, retrieval, and generation. It supports unified sample construction, heterogeneous system adaptation, semantic judgement, per-question logging, and structured result persistence. Compared with traditional evaluations that only report final correctness, the proposed method can further identify at which layer a failure occurs, thereby providing direct guidance for memory system debugging. The framework also emphasizes generality and robustness, avoiding tight coupling between evaluation logic and any single system’s internal structure, and leaving room for future integration of additional memory systems. The thesis has completed the method, system, and experiment design sections, while quantitative results are reserved for future completion.

## 版本 D：论文型叙事 + 研究意义

### 中文摘要

长期记忆能力是智能体走向真实持续交互的重要前提，但当前研究更多关注记忆系统本身的架构创新，而对评测层的统一抽象与问题归因重视不足。本文认为，若无法在统一框架下解释错误来源，就难以对不同记忆系统进行公平比较，也难以支持后续有针对性的系统优化。基于这一认识，本文在综合记忆系统调研与评测文献分析的基础上，提出一种面向长期记忆智能体的三层归因评测框架。本文首先将异构记忆系统统一抽象为编码、检索与生成三个层次，然后围绕这三个层次构建并行探针和最终归因机制，进一步设计统一适配器协议、统一语义判分和统一结果组织方式，从而在方法上实现对不同记忆系统的细粒度对齐分析。本文同时完成了该框架的工程实现，并为实验结果、案例分析与后续扩展留下了规范化接口与记录位置。该工作有助于把长期记忆系统研究从单纯追求分数提升，推进到可解释、可复现、可诊断的系统化评测阶段。

### 英文摘要

Long-term memory is a prerequisite for intelligent agents to achieve realistic and persistent interaction, yet current research focuses more on architectural innovation of memory systems than on unified evaluation abstraction and failure attribution. This thesis argues that without a unified framework for explaining where failures come from, it is difficult both to compare different memory systems fairly and to support targeted optimization afterward. Based on this motivation, and grounded in a combined survey of memory systems and evaluation literature, this thesis proposes a three-layer attribution framework for evaluating long-term memory agents. Heterogeneous memory systems are first abstracted into three layers: encoding, retrieval, and generation. Parallel probes and a final attribution mechanism are then designed around these layers. In addition, a unified adapter protocol, a unified semantic judgement scheme, and a unified result organization method are introduced to enable fine-grained aligned analysis across different memory systems. The engineering implementation of the framework has been completed, and standardized placeholders are reserved for experimental results, case analysis, and future extensions. This work helps move long-term memory system research from score-oriented comparison toward systematic evaluation that is interpretable, reproducible, and diagnosable.
