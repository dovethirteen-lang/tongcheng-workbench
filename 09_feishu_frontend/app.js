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

function renderTable(items, fields, emptyText) {
  if (!items.length) {
    return `<p class="empty">${emptyText}</p>`;
  }
  const rows = items.map((item) => {
    const cols = fields.map((field) => {
      const value = item[field] ?? "";
      if (field.toLowerCase().includes("url")) {
        return `<td><span class="link">${value}</span></td>`;
      }
      return `<td>${value}</td>`;
    }).join("");
    return `<tr>${cols}</tr>`;
  }).join("");
  return `<table><tbody>${rows}</tbody></table>`;
}

function renderChips(obj) {
  return Object.entries(obj)
    .map(([key, value]) => `<div class="chip">${key}：${value}</div>`)
    .join("");
}

function renderRelease(obj) {
  return Object.entries(obj)
    .map(([key, value]) => `<div class="release-card"><strong>${key}</strong><span>${value}</span></div>`)
    .join("");
}

function renderAlerts(items) {
  if (!items.length) {
    return `<p class="empty">暂无数据告警</p>`;
  }
  return items.map((item) => `
    <div class="alert-card">
      <strong>${item.title || ""}</strong>
      <div class="alert-meta">级别：${item.severity || ""} · 状态：${item.status || ""}</div>
      <div>${item.detail || ""}</div>
    </div>
  `).join("");
}

function bind(data) {
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

loadData()
  .then(bind)
  .catch((error) => {
    console.error(error);
    document.body.innerHTML = `<div class="app-shell"><p class="empty">前台数据加载失败，请先执行 render_feishu_frontend.py。</p></div>`;
  });
