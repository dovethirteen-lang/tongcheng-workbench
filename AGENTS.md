# 同程产品工作台指令

## 工作原则

- 所有输入先结构化，不直接开始写结论。
- 先判断任务属于广告实验、微信生态承接、多平台接入、日常管理、Notion 沉淀中的哪一类。
- 如果任务明确与 `Notion` 归档、知识沉淀、版本管理有关，优先调用 `Notion 工作台 Agent`。
- 输出优先短、结构化、可复用。
- 所有结果都必须包含下一步动作。
- 优先使用最省 token 的路径：先摘要，再分发，再按需调用专项 Agent。

## 路由规则

### 1. PDF/长图/共享文档输入

- 先转成可读需求文档
- 再补结构化需求卡片
- 默认输出到 `01_intake/`

### 2. 广告专项

- 优先走：目标 -> 假设 -> 实验方案 -> 数据口径 -> SQL -> 结果分析 -> 建议动作
- 可调用：
  - 商业分析师 Agent
  - 数据工程师 Agent
  - 实验设计 Agent

### 3. 微信生态/活动需求

- 优先走：背景 -> 目标 -> 用户路径 -> 页面/视觉/交互 -> 规则 -> 风险 -> PRD
- 可调用：
  - 增长/C 端活动产品 Agent

### 4. Notion 知识沉淀

- 优先处理结构化需求卡片、PRD 版本记录、实验归档、日报归档
- Notion 是协作与归档层，不是最终 Wiki 发布层
- 如需发 Wiki，必须补一份 Wiki 发布中间稿
- 可调用：
  - Notion 工作台 Agent

### 5. 多平台接入

- 优先走：接入背景 -> 外部接口 -> 内部依赖 -> 技术约束 -> 风险与缺口 -> 接入方案
- 可调用：
  - 平台产品 Agent

### 6. 日常管理

- 优先处理提醒、拆解、告警和优先级判断
- 不展开无关探索
- 可调用：
  - 每日作战助手 Agent

## Agent 清单

- `agents/orchestrator_pm.md`
- `agents/business_analyst.md`
- `agents/data_engineer.md`
- `agents/experiment_designer.md`
- `agents/growth_pm.md`
- `agents/platform_pm.md`
- `agents/daily_ops_assistant.md`
- `agents/notion_workspace_manager.md`
