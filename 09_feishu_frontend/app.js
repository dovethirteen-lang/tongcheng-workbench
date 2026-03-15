let apiAvailable = false;
let currentCommandTemplate = "";
let currentIntent = "";

async function loadStaticData() {
  const response = await fetch("./data/workbench.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load frontend data");
  }
  return response.json();
}

async function loadApiState() {
  const response = await fetch("/api/state", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load API state");
  }
  return response.json();
}

async function detectApi() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    apiAvailable = response.ok;
  } catch (_error) {
    apiAvailable = false;
  }
  renderApiStatus();
}

function renderApiStatus() {
  const node = document.getElementById("apiStatus");
  node.className = `pill ${apiAvailable ? "success" : "neutral"}`;
  node.textContent = apiAvailable ? "后端状态：已连接" : "后端状态：静态预览";
  document.getElementById("btnSubmitCommand").disabled = !apiAvailable;
  document.getElementById("modalHint").textContent = apiAvailable
    ? "当前已连接本地主控。你可以直接提交到后端，也可以复制后发给飞书助手。"
    : "当前是静态预览模式。你可以先复制下面这条命令，发给飞书里的工作助手。";
}

function metric(label, value, suffix = "") {
  return `
    <div class="metric">
      <span class="metric-label">${label}</span>
      <strong class="metric-value">${value}${suffix}</strong>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderCell(field, value) {
  if (!value) {
    return "<td>-</td>";
  }
  if (field.toLowerCase().includes("url")) {
    return `<td><a class="link" href="${escapeHtml(value)}" target="_blank" rel="noopener noreferrer">打开链接</a></td>`;
  }
  return `<td>${escapeHtml(value)}</td>`;
}

function renderTable(items, fields, emptyText) {
  if (!items.length) {
    return `<p class="empty">${emptyText}</p>`;
  }
  const rows = items.map((item) => {
    const cols = fields.map((field) => renderCell(field, item[field])).join("");
    return `<tr>${cols}</tr>`;
  }).join("");
  return `<table><tbody>${rows}</tbody></table>`;
}

function renderChips(obj) {
  return Object.entries(obj)
    .map(([key, value]) => `<div class="chip"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span></div>`)
    .join("");
}

function renderRelease(obj) {
  return Object.entries(obj)
    .map(([key, value]) => `<div class="release-card"><strong>${escapeHtml(key)}</strong><span>${escapeHtml(value)}</span></div>`)
    .join("");
}

function buildComposerCommand() {
  const lane = document.getElementById("composerLane").value;
  const action = document.getElementById("composerAction").value;
  const link = document.getElementById("composerLink").value.trim();
  const deadline = document.getElementById("composerDeadline").value.trim();
  const notes = document.getElementById("composerNotes").value.trim();

  const laneLabelMap = {
    wechat_growth: "微信流量提效",
    ads_experiment: "广告专项",
    platform_integration: "多平台项目",
    daily_ops: "每日作战",
    general: "通用事项",
  };

  const prefix = `这是一个${laneLabelMap[lane] || "通用事项"}任务。`;
  const sourceLine = link ? `资料位置：${link}` : "资料位置：待补充";
  const deadlineLine = deadline ? `截止时间：${deadline}` : "";

  const actionTemplates = {
    requirement_card: [
      "请先整理成需求卡片草稿，不要归档。",
      "输出：背景、目标、用户路径、规则、风险、待确认项。",
      "完成后把飞书文档链接回给我。",
    ],
    prd_draft: [
      "请按照当前需求卡片生成 PRD 草稿，不要归档。",
      "PRD 结构按我的 Notion 模板来写。",
      "完成后把飞书文档链接回给我。",
    ],
    analysis: [
      "请输出结构化分析结果。",
      "需要给出问题判断、下一步建议和可执行动作。",
      "如果适合文档化，请生成飞书文档草稿。",
    ],
    todo: [
      "请登记一条新的待办。",
      "写清事项、阻塞点、回传结果。",
    ],
    feedback: [
      "请记录一条工作台反馈。",
      "写清问题现象、复现方式、期望结果、优先级。",
    ],
    alert: [
      "请记录一条数据告警。",
      "写清异常指标、波动情况、初步判断、下一步排查动作。",
    ],
    finalize: [
      "确定定稿。",
      "请进入 Notion 归档并生成 Wiki 中间稿。",
    ],
  };

  const parts = [prefix, sourceLine, ...actionTemplates[action]];
  if (deadlineLine) {
    parts.push(deadlineLine);
  }
  if (notes) {
    parts.push(`补充说明：${notes}`);
  }
  return parts.filter(Boolean).join("\n");
}

function renderConfig(data) {
  const notion = data.notion_config || {};
  const feishu = data.feishu_config || {};
  const route = notion.routing_map || {};
  const cards = [];

  if (notion.workspace_url) {
    cards.push(`
      <div class="release-card">
        <strong>Notion 工作空间</strong>
        <span><a class="link" href="${escapeHtml(notion.workspace_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(notion.workspace_name || "打开工作空间")}</a></span>
      </div>
    `);
  }

  if (notion.prd_template_url) {
    cards.push(`
      <div class="release-card">
        <strong>PRD 模板</strong>
        <span><a class="link" href="${escapeHtml(notion.prd_template_url)}" target="_blank" rel="noopener noreferrer">打开 Notion 模板</a></span>
      </div>
    `);
  }

  cards.push(`
    <div class="release-card">
      <strong>飞书文档策略</strong>
      <span>${escapeHtml(feishu.document_channel || "飞书云文档")} · ${escapeHtml(feishu.document_strategy?.default_folder_label || "默认目录")}</span>
    </div>
  `);

  if (notion.todo_strategy?.entry_name) {
    cards.push(`
      <div class="release-card">
        <strong>待办收口</strong>
        <span>${escapeHtml(notion.todo_strategy.database || "")} / ${escapeHtml(notion.todo_strategy.entry_name || "")}</span>
      </div>
    `);
  }

  if (notion.feedback_strategy?.entry_name) {
    cards.push(`
      <div class="release-card">
        <strong>反馈收口</strong>
        <span>${escapeHtml(notion.feedback_strategy.database || "")} / ${escapeHtml(notion.feedback_strategy.entry_name || "")}</span>
      </div>
    `);
  }

  if (route.wechat_growth?.database || route.ads_experiment?.database || route.platform_integration?.database) {
    cards.push(`
      <div class="release-card">
        <strong>业务路由</strong>
        <span>微信 -> ${escapeHtml(route.wechat_growth?.database || "-")}；广告 -> ${escapeHtml(route.ads_experiment?.database || "-")}；多平台 -> ${escapeHtml(route.platform_integration?.database || "-")}</span>
      </div>
    `);
  }

  return cards.join("");
}

function renderAlerts(items) {
  if (!items.length) {
    return `<p class="empty">暂无数据告警</p>`;
  }
  return items.map((item) => `
    <div class="alert-card">
      <strong>${escapeHtml(item.title || "")}</strong>
      <div class="alert-meta">级别：${escapeHtml(item.severity || "")} · 状态：${escapeHtml(item.status || "")}</div>
      <div>${escapeHtml(item.detail || "")}</div>
    </div>
  `).join("");
}

function renderCommands(items) {
  return renderTable(items, ["task_type", "source", "created_at"], "暂无命令记录");
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2200);
}

function openModal(title, command, intent = "") {
  currentCommandTemplate = command;
  currentIntent = intent;
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("commandText").value = command;
  document.getElementById("commandModal").classList.remove("hidden");
}

function closeModal() {
  currentIntent = "";
  document.getElementById("commandModal").classList.add("hidden");
}

async function copyCommand() {
  const text = document.getElementById("commandText").value;
  try {
    await navigator.clipboard.writeText(text);
    showToast("命令已复制。");
  } catch (_error) {
    showToast("复制失败，请手动复制。");
  }
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function getState() {
  if (apiAvailable) {
    return loadApiState();
  }
  return loadStaticData();
}

function renderResult(result) {
  const node = document.getElementById("resultBox");
  if (!result) {
    node.className = "result-box empty";
    node.textContent = "还没有执行记录。";
    return;
  }
  const parts = [];
  if (result.summary) {
    parts.push(`<p>${escapeHtml(result.summary)}</p>`);
  }
  if (result.doc_draft?.url) {
    parts.push(`<p><a class="link" href="${escapeHtml(result.doc_draft.url)}" target="_blank" rel="noopener noreferrer">打开飞书草稿</a></p>`);
  }
  if (result.warnings?.length) {
    parts.push(...result.warnings.map((item) => `<p class="warn-text">警告：${escapeHtml(item)}</p>`));
  }
  if (result.errors?.length) {
    parts.push(...result.errors.map((item) => `<p class="error-text">错误：${escapeHtml(item)}</p>`));
  }
  if (result.wiki_handoff?.path) {
    parts.push(`<p>已生成 Wiki 中间稿：${escapeHtml(result.wiki_handoff.path)}</p>`);
  }
  if (result.alert_item?.title) {
    parts.push(`<p>已登记数据告警：${escapeHtml(result.alert_item.title)}</p>`);
  }
  if (result.todo_queue?.path) {
    parts.push(`<p>待办收口文件：${escapeHtml(result.todo_queue.path)}</p>`);
  }
  if (result.feedback_queue?.path) {
    parts.push(`<p>反馈收口文件：${escapeHtml(result.feedback_queue.path)}</p>`);
  }
  if (result.alert_queue?.path) {
    parts.push(`<p>告警收口文件：${escapeHtml(result.alert_queue.path)}</p>`);
  }
  node.className = "result-box";
  node.innerHTML = parts.join("") || "<p>已提交主控处理。</p>";
}

async function reloadWorkbench() {
  try {
    await detectApi();
    const data = await getState();
    bind(data);
    showToast("工作台数据已刷新。");
  } catch (error) {
    console.error(error);
    showToast("刷新失败，请稍后重试。");
  }
}

async function submitCommand() {
  if (!apiAvailable) {
    showToast("当前未连接本地后端，请先复制命令发送给飞书助手。");
    return;
  }

  const text = document.getElementById("commandText").value.trim();
  if (!text) {
    showToast("命令内容不能为空。");
    return;
  }

  const response = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source: "workbench_frontend",
      intent: currentIntent || undefined,
    }),
  });

  if (!response.ok) {
    showToast("提交失败，请查看后端日志。");
    return;
  }

  const payload = await response.json();
  if (!payload.ok) {
    showToast(payload.error || "提交失败。");
    return;
  }

  closeModal();
  bind(payload.state);
  renderResult(payload);
  showToast("命令已提交到主控。");
}

function wireActions() {
  document.getElementById("btnNewCard").addEventListener("click", () => {
    openModal(
      "新建需求卡片",
      [
        "读取这个 Notion / 飞书文档链接，先整理成需求卡片草稿，不要归档。",
        "请输出：背景、目标、用户路径、规则、风险、待确认项。",
        "完成后把飞书文档链接回给我。"
      ].join("\n"),
      "new_card"
    );
  });

  document.getElementById("btnNewPrd").addEventListener("click", () => {
    openModal(
      "生成 PRD 草稿",
      [
        "按照这个需求卡片生成 PRD 草稿，不要归档。",
        "PRD 结构按我的 Notion 模板来写。",
        "生成到飞书文档，完成后把链接回给我。"
      ].join("\n"),
      "new_prd"
    );
  });

  document.getElementById("btnNewTodo").addEventListener("click", () => {
    openModal(
      "登记待办",
      [
        "登记一条新的待办。",
        "请写清：事项、截止时间、当前阻塞点、需要我回传的结果。",
      ].join("\n"),
      "todo"
    );
  });

  document.getElementById("btnNewFeedback").addEventListener("click", () => {
    openModal(
      "提交反馈",
      [
        "记录一条工作台反馈。",
        "请说明：问题现象、复现方式、期望结果、优先级。",
      ].join("\n"),
      "feedback"
    );
  });

  document.getElementById("btnViewAlerts").addEventListener("click", () => {
    scrollToSection("alertSection");
    showToast("已定位到数据告警区。");
  });

  document.getElementById("btnReload").addEventListener("click", reloadWorkbench);
  document.getElementById("btnGenerateCommand").addEventListener("click", () => {
    document.getElementById("composerOutput").value = buildComposerCommand();
    showToast("标准命令已生成。");
  });
  document.getElementById("btnUseGenerated").addEventListener("click", () => {
    const text = document.getElementById("composerOutput").value.trim() || buildComposerCommand();
    document.getElementById("composerOutput").value = text;
    openModal("标准命令", text, document.getElementById("composerAction").value);
  });
  document.getElementById("btnCopyCommand").addEventListener("click", copyCommand);
  document.getElementById("btnSubmitCommand").addEventListener("click", submitCommand);
  document.getElementById("btnCloseModal").addEventListener("click", closeModal);
  document.getElementById("btnDismissModal").addEventListener("click", closeModal);
  document.getElementById("commandModal").addEventListener("click", (event) => {
    if (event.target.id === "commandModal") {
      closeModal();
    }
  });
}

function bind(data) {
  document.getElementById("updatedAt").textContent = `更新时间 ${data.updated_at || "-"}`;
  document.getElementById("metrics").innerHTML = [
    metric("最近命令", data.commands.length),
    metric("文档数量", data.documents.length),
    metric("打开待办", data.todos.filter((item) => item.status === "open").length),
    metric("数据告警", data.alerts.filter((item) => item.status === "open").length),
    metric("反馈池", data.feedback.length),
  ].join("");

  document.getElementById("alertCount").textContent = String(data.alerts.length);
  document.getElementById("todoCount").textContent = String(data.todos.length);
  document.getElementById("docCount").textContent = String(data.documents.length);
  document.getElementById("feedbackCount").textContent = String(data.feedback.length);

  document.getElementById("alertList").innerHTML = renderAlerts(data.alerts);
  document.getElementById("todoList").innerHTML = renderTable(data.todos, ["title", "deadline_hint", "status"], "暂无待办");
  document.getElementById("docList").innerHTML = renderTable(data.documents, ["title", "status", "document_url"], "暂无文档记录");
  document.getElementById("commandList").innerHTML = renderCommands(data.commands);
  document.getElementById("capabilityList").innerHTML = renderChips(data.capabilities);
  document.getElementById("releaseList").innerHTML = renderRelease(data.release_plan);
  document.getElementById("configList").innerHTML = renderConfig(data);
  document.getElementById("feedbackList").innerHTML = renderTable(data.feedback, ["title", "category", "status"], "暂无反馈");
}

wireActions();

(async () => {
  try {
    await detectApi();
    const data = await getState();
    bind(data);
    renderResult(null);
  } catch (error) {
    console.error(error);
    document.body.innerHTML = '<div class="app-shell"><p class="empty">前台数据加载失败，请先执行 render_feishu_frontend.py。</p></div>';
  }
})();
