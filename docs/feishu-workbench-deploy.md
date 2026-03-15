# 飞书工作台接入说明

这份说明对应当前的正式目标形态：把工作台前台挂到飞书工作台里，而不是长期单独打开本地 HTML。

## 当前实现状态

当前已经完成：

- 一套独立前台骨架：
  - `09_feishu_frontend/index.html`
- 一套前台数据结构：
  - `09_feishu_frontend/data/workbench.json`
  - `09_feishu_frontend/data/workbench-summary.json`
- 一份飞书工作台前台配置参考：
  - `09_feishu_frontend/feishu-workbench-config.json`

## 建议接入形态

建议在飞书里创建一个工作台应用，把前台主页指向部署后的前端地址。

当前这套前端更适合承接：

- 数据告警
- 待办池
- 文档状态
- 版本进展
- 反馈池
- 快捷动作入口

命令入口仍然建议保持在飞书消息应用中。

## 当前目录用途

- `index.html`
  - 前台主页
- `styles.css`
  - 前台样式
- `app.js`
  - 前台渲染逻辑
- `data/workbench.json`
  - 全量前台数据
- `data/workbench-summary.json`
  - 轻量摘要数据

## 使用步骤

1. 生成前台数据

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
py .\scripts\render_feishu_frontend.py
```

2. 本地预览

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
.\scripts\start_feishu_frontend.ps1
```

3. 之后将 `09_feishu_frontend` 部署到可访问的静态站点

4. 在飞书工作台中创建应用，把主页地址指向部署后的 URL

## 设计原则

- 飞书工作台只承担“看板 + 快捷入口”
- 文档协作仍然在飞书云文档
- 归档仍然在 Notion
- 后台命令处理仍然在主控服务
