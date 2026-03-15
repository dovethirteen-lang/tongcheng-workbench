let currentData = null;

async function loadData() {
  const response = await fetch("./data/workbench.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load frontend data");
  }
  return response.json();
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

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.classList.add("hidden");
  }, 2400);
}

function openModal(title, command) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("commandText").value = command;
  document.getElementById("commandModal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("commandModal").classList.add("hidden");
}

async function copyCommand() {
  const text = document.getElementById("commandText").value;
  try {
    await navigator.clipboard.writeText(text);
    showToast("命令已复制，可以直接发给飞书助手。");
  } catch (error) {
    console.error(error);
    showToast("复制失败，请手动复制。");
  }
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function reloadWorkbench() {
  try {
    const data = await loadData();
    bind(data);
    showToast("工作台数据已刷新。");
  } catch (error) {
    console.error(error);
    showToast("刷新失败，请稍后重试。");
  }
}

function wireActions() {
  document.getElementById("btnNewCard").addEventListener("click", () => {
    openModal(
      "新建需求卡片",
      [
        "读取这个 Notion / 飞书文档链接，先整理成需求卡片草稿，不要归档。",
        "请输出：背景、目标、用户路径、规则、风险、待确认项。",
        "完成后把飞书文档链接回给我。"
      ].join("\n")
    );
  });

  document.getElementById("btnNewPrd").addEventListener("click", () => {
    openModal(
      "生成 PRD 草稿",
      [
        "按照这个需求卡片生成 PRD 草稿，不要归档。",
        "PRD 结构按我的 Notion 模板来写。",
        "生成到飞书文档，完成后把链接回给我。"
      ].join("\n")
    );
  });

  document.getElementById("btnViewAlerts").addEventListener("click", () => {
    scrollToSection("alertSection");
    showToast("已定位到数据告警区。");
  });

  document.getElementById("btnReload").addEventListener("click", reloadWorkbench);
  document.getElementById("btnCopyCommand").addEventListener("click", copyCommand);
  document.getElementById("btnCloseModal").addEventListener("click", closeModal);
  document.getElementById("btnDismissModal").addEventListener("click", closeModal);

  document.getElementById("commandModal").addEventListener("click", (event) => {
    if (event.target.id === "commandModal") {
      closeModal();
    }
  });
}

function bind(data) {
  currentData = data;
  document.getElementById("updatedAt").textContent = `更新时间 ${data.updated_at || "-"}`;
  document.getElementById("metrics").innerHTML = [
    metric("最近命令", data.commands.length),
    metric("文档数量", data.documents.length),
    metric("打开待办", data.todos.filter((x) => x.status === "open").length),
    metric("数据告警", data.alerts.filter((x) => x.status === "open").length),
    metric("反馈池", data.feedback.length),
  ].join("");

  document.getElementById("alertCount").textContent = String(data.alerts.length);
  document.getElementById("todoCount").textContent = String(data.todos.length);
  document.getElementById("docCount").textContent = String(data.documents.length);
  document.getElementById("feedbackCount").textContent = String(data.feedback.length);

  document.getElementById("alertList").innerHTML = renderAlerts(data.alerts);
  document.getElementById("todoList").innerHTML = renderTable(data.todos, ["title", "deadline_hint", "status"], "暂无待办");
  document.getElementById("docList").innerHTML = renderTable(data.documents, ["title", "status", "document_url"], "暂无文档记录");
  document.getElementById("capabilityList").innerHTML = renderChips(data.capabilities);
  document.getElementById("releaseList").innerHTML = renderRelease(data.release_plan);
  document.getElementById("feedbackList").innerHTML = renderTable(data.feedback, ["title", "category", "status"], "暂无反馈");
}

wireActions();

loadData()
  .then(bind)
  .catch((error) => {
    console.error(error);
    document.body.innerHTML = `<div class="app-shell"><p class="empty">前台数据加载失败，请先执行 render_feishu_frontend.py。</p></div>`;
  });
