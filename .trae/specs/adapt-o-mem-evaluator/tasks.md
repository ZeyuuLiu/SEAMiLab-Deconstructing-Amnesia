# Tasks
- [x] Task 1: 梳理并冻结 O-Mem 到评估契约的字段映射
  - [x] SubTask 1.1: 明确 `memory_view` 的来源层级与标准字段
  - [x] SubTask 1.2: 明确 `retrieved_items` 的顺序与分数字段降级策略
  - [x] SubTask 1.3: 明确 `answer_oracle` 的独立调用路径

- [x] Task 2: 实现 O-Mem 适配器骨架并接入四类协议
  - [x] SubTask 2.1: 实现会话摄取与运行上下文构建
  - [x] SubTask 2.2: 实现编码探针所需全量记忆导出与匹配入口
  - [x] SubTask 2.3: 实现检索探针原始检索导出
  - [x] SubTask 2.4: 实现生成探针 oracle 作答接口

- [x] Task 3: 新增轻量运行脚本用于 O-Mem 适配联调
  - [x] SubTask 3.1: 支持 `question_id` 与 `query` 两种定位方式
  - [x] SubTask 3.2: 支持 limit/top_k 等低成本参数
  - [x] SubTask 3.3: 输出单样本三探针结果与关键证据

- [x] Task 4: 完成安全配置接入与最小验证
  - [x] SubTask 4.1: API Key 与 Base URL 改为环境变量或本地配置读取
  - [x] SubTask 4.2: 添加缺失配置时的可读错误提示
  - [x] SubTask 4.3: 执行小样本验证并记录通过标准

- [x] Task 5: 修复编码探针下 O-Mem 记忆导出稳定匹配问题
  - [x] SubTask 5.1: 对齐 memory_view 文本格式与 f_key 的时间与说话人信息
  - [x] SubTask 5.2: 增强 find_memory_records 的时间/角色归一化匹配策略
  - [x] SubTask 5.3: 以失败样本回归验证编码探针从 MISS 收敛到 EXIST

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 2 and Task 3
- Task 5 depends on Task 2 and Task 3
