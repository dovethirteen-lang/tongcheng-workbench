# 飞书主入口联调说明

当前第一阶段已经切到“飞书主入口”模式：

- 你在飞书里发命令
- 主控层解析命令并落盘
- 结果先通过飞书文本消息回执
- 适合文档化的任务自动生成飞书草稿
- 只有在定稿或发布阶段，才进入 Notion 归档

## 已完成能力

- 飞书应用 `tenant_access_token` 校验通过
- 飞书长连接客户端已完成
- 飞书消息进入主控解析已完成
- 适合文档化的任务会自动生成飞书云文档草稿
- Notion 归档改成“显式触发”
- 本地命令与回执已统一落到 `D:\Project\runtime\command_bus`
- 本地长连接运行日志落到 `D:\Project\runtime\feishu_longconn`

## 本地运行命令

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
py .\scripts\validate_feishu_app.py
py .\scripts\run_feishu_longconn.py --log-level INFO
py .\scripts\generate_feishu_doc_draft.py --command-file .\tmp\commands\YOUR_COMMAND.json --reply-file D:\Project\runtime\command_bus\outbox\YOUR_REPLY.json
py .\scripts\process_notion_queue.py
```

## 飞书后台配置

在飞书开放平台的事件订阅页：

1. 选择 `使用长连接 接收事件`
2. 点击 `保存`
3. 勾选消息接收相关事件
4. 在应用权限里确认已经开通收发消息能力
5. 重新发布应用版本

## 当前工作流

### 草稿阶段

`飞书命令 -> 主控解析 -> 飞书草稿 -> 飞书回执`

这时不会归档到 Notion。

### 定稿阶段

`飞书命令(含定稿/归档/发布指令) -> 主控解析 -> Notion 队列 -> Wiki 发布准备`

## 本地产物位置

- 命令日志：`D:\CodeX\工作流设计\同程产品工作台\tmp\commands`
- 回执队列：`D:\Project\runtime\command_bus\outbox`
- 长连接日志：`D:\Project\runtime\feishu_longconn\events.log`
- 飞书草稿默认创建在应用可写的位置；如需指定文件夹，可在 `config/feishu_app.json` 里填写 `docx_folder_token`
- Notion 队列：`D:\Project\runtime\notion_queue`
- Notion Markdown 渲染目录：`D:\Project\docs\notion_queue`

## 当前边界

- 现在已经能做到“飞书收命令 -> 主控解析 -> 飞书文本回执”
- 已经能自动创建飞书云文档草稿，但还没做复杂表格和图片写入
- Notion 不再默认每次修改都归档
- 只有显式进入归档/定稿/发布阶段，才会生成 Notion 归档队列
