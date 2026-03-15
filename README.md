# 同程产品工作台

这是围绕你当前工作方式搭建的一套产品工作台。当前版本按 `飞书优先 + Notion 沉淀 + Wiki 发布` 运行：

- `飞书` 作为主命令入口和回执入口
- `飞书云文档` 作为需求卡片、PRD 草稿和多轮批注协作区
- `Notion` 只在定稿后进入归档链路
- `Wiki` 作为最终发布层
- `D:\Project` 作为本地过程资产目录

## 当前版本路线

- `1.0`：飞书主入口、飞书草稿、定稿后归档
- `1.1`：多轮修改闭环与定稿指令
- `1.2`：待办、版本、能力现状与助手状态视图
- `1.3`：反馈收集与周末迭代输入链路

详细规划见：[version-roadmap.md](D:\CodeX\工作流设计\同程产品工作台\docs\version-roadmap.md)

## 工作流

### 草稿阶段

`飞书发命令 -> 主控解析 -> 飞书草稿 -> 你批注 -> 主控继续修改`

这一步不会进入 Notion。

### 定稿阶段

当你明确发出这些指令时，才进入归档链路：

- `归档`
- `归档到 Notion`
- `同步到 Notion`
- `定稿`
- `最终版`
- `终稿`
- `发布到 Wiki`
- `准备上线`

此时链路变成：

`飞书发命令 -> 主控解析 -> Notion 归档队列 -> Wiki 发布准备`

## 已完成能力

- 飞书长连接接收消息
- 飞书文本回执
- 主控命令解析与路由
- 自动生成飞书云文档草稿
- 多轮修改请求写回飞书文档
- 显式触发的 Notion 归档队列
- 本地命令日志与运行时状态
- 待办、反馈、能力状态本地收口

## 目录说明

- `00_inbox`：原始输入
- `01_intake`：转写与结构化输入
- `02_ads_experiments`：广告实验材料
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
py .\scripts\render_workbench_status.py
py .\scripts\smoke_test.py
```

## 常见命令示例

```text
读取这个 Notion 链接，先整理成需求卡片草稿，不要归档。
```

```text
按照我的备注修改这个飞书文档 https://feishu.cn/docx/xxxx ，补充缺失规则。
```

```text
这个 PRD 已经定稿，归档到 Notion，并准备发布到 Wiki。
```
