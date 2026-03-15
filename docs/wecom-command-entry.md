# 企业微信命令入口

这是企业微信入口开发骨架的说明文档。

## 当前目标

当前路线已经从“应用回调”切换为“企业微信智能机器人长连接模式”，因为你现在有机器人权限，但没有创建应用权限。

先把这条链路跑起来：

- 企业微信智能机器人作为主命令入口
- 主控层解析命令
- 将解析结果沉淀到本地
- 后续再补正式长连接收发消息、飞书写入和 Notion 归档

## 当前已实现

- 本地企业微信命令解析骨架
- 主控命令解析器
- 路由规则复用 `config/agent_router.json`
- 解析结果自动写入 `tmp/commands/`
- 长连接模式本地配置模板
- 长连接客户端启动骨架
- 本地 inbox / outbox 消息处理骨架

## 你现在先做什么

1. 在企业微信机器人后台刷新 `Secret`
2. 把 `config/wecom_bot.sample.json` 复制为 `config/wecom_bot.json`
3. 将新的 `Bot ID` 和 `Secret` 填入本地配置文件
4. 不要把新的 `Secret` 发到聊天里

## 本地验证

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
Copy-Item .\config\wecom_bot.sample.json .\config\wecom_bot.json
py .\scripts\run_wecom_bot_client.py --dry-run
```

## 本地消息处理

即使正式长连接协议还没接上，现在也可以验证主控链路：

```powershell
py .\scripts\process_wecom_queue.py --text "读取这个 Notion 链接，这是当前 PRD。目标：迁移成飞书评审稿，今天17:00前通知我。"
```

这会生成：

- `tmp/commands/*.json`
- `D:\Project\runtime\wecom_bot\outbox\*.json`

## 当前可用脚本

- `scripts/run_wecom_bot_client.py`
  - 验证本地机器人配置
  - 模拟一条企业微信命令进入主控层

- `scripts/process_wecom_queue.py`
  - 处理本地 inbox 队列
  - 生成回执 stub

- `scripts/run_wecom_gateway.py`
  - 旧的 HTTP 骨架
  - 保留作本地调试参考

## 当前状态

- 企业微信智能机器人路线已确认
- 长连接模式已确认
- 配置模板已就位
- 主控解析已就位
- 回执生成已就位
- 正式收发消息还没接上

## 当前限制

- 还没有接正式企业微信机器人长连接 SDK / 协议
- 还没有回写企业微信机器人消息
- 还没有直接写入飞书云文档
- 还没有直接写入 Notion

## 下一步

1. 接企业微信机器人长连接正式收发消息
2. 补企业微信机器人回执消息
3. 接飞书文档写入
4. 接 Notion 归档
