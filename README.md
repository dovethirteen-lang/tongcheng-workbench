# 同程产品工作台 1.0

这是一套围绕你当前工作方式搭建的产品工作台，`1.0` 版本已经明确采用：

- `飞书` 作为主命令入口和回执入口
- `飞书云文档` 作为需求卡片、PRD 草稿和多轮批注协作区
- `Notion` 作为定稿后的沉淀与归档层
- `Wiki` 作为最终发布层
- `D:\Project` 作为本地过程资产目录

## 1.0 工作流

### 草稿阶段

`飞书发命令 -> 主控解析 -> 飞书草稿 -> 你批注 -> 我继续修改`

这一阶段不会归档到 Notion。

### 定稿阶段

当你明确发出这些指令时，才进入归档链路：

- `归档`
- `归档到Notion`
- `同步到Notion`
- `定稿`
- `最终版`
- `终稿`
- `发布到Wiki`
- `准备上线`

此时链路变成：

`飞书发命令 -> 主控解析 -> Notion 归档队列 -> Wiki 发布准备`

## 当前已完成能力

- 飞书长连接收消息
- 飞书文本回执
- 主控命令解析
- 自动生成飞书云文档草稿
- 显式触发的 Notion 归档队列
- 本地命令日志与运行日志

## 当前目录

- `00_inbox`：原始输入
- `01_intake`：转写和结构化输入
- `02_ads_experiments`：广告实验
- `03_wechat_growth`：微信生态与活动需求
- `04_platform_integration`：多平台接入
- `05_daily_ops`：每日作战
- `06_templates`：模板
- `07_output`：导出产物
- `08_dashboard`：辅助可视化页面
- `agents`：Agent 规则
- `config`：配置
- `docs`：说明文档
- `runtime`：运行时逻辑
- `scripts`：脚本
- `tmp`：临时日志和命令记录

## 本地资产目录

统一使用：

- `D:\Project\docs`
- `D:\Project\data`
- `D:\Project\scripts`
- `D:\Project\runtime`

## 关键脚本

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
py .\scripts\validate_feishu_app.py
py .\scripts\run_feishu_longconn.py --log-level INFO
py .\scripts\generate_feishu_doc_draft.py --command-file .\tmp\commands\YOUR_COMMAND.json --reply-file D:\Project\runtime\command_bus\outbox\YOUR_REPLY.json
py .\scripts\process_notion_queue.py
```

## 说明文档

- `docs/feishu-entry.md`
- `docs/notion-workflow.md`
- `docs/wiki-publish-checklist.md`
- `docs/workflow-map.md`

## 版本定位

这是 `1.0` 版本：

- 主入口先走飞书
- 不强行接企业微信
- 不把 Notion 放在每次草稿生成的实时链路里
- 后续企业微信能力开放后，再升级成 `2.0`
