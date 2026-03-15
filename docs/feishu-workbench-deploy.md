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

3. 构建可发布静态站点

```powershell
cd D:\CodeX\工作流设计\同程产品工作台
py .\scripts\build_feishu_frontend_release.py
```

构建产物会输出到：

- `site/feishu-workbench`

4. 将 `site/feishu-workbench` 部署到可访问的静态站点

当前仓库已经补了 GitHub Pages 工作流：

- `.github/workflows/deploy-feishu-workbench.yml`

5. 在 GitHub 仓库里启用 Pages 后，就可以拿到一个公开 URL

6. 在飞书工作台中创建应用，把主页地址指向部署后的 URL

## 设计原则

- 飞书工作台只承担“看板 + 快捷入口”
- 文档协作仍然在飞书云文档
- 归档仍然在 Notion
- 后台命令处理仍然在主控服务

## 当前最短落地路径

1. 用当前仓库生成前台数据和静态站点
2. 用 GitHub Pages 暴露一个可访问 URL
3. 在飞书工作台里创建自建应用
4. 把应用主页配置到该 URL

这样你就能先以最低成本把这套前台挂进飞书工作台。
