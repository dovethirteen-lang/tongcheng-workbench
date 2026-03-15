const DRAFT_STORAGE_KEY = "tc_workbench_composer_draft";
const HISTORY_STORAGE_KEY = "tc_workbench_local_history";
const HISTORY_LIMIT = 20;

let apiAvailable = false;
let currentIntent = "";
let currentLane = "general";
let currentAction = "general";

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
  document.getElementById("btnSubmitGenerated").disabled = !apiAvailable;
  document.getElementById("modalHint").textContent = apiAvailable
    ? "当前已连接本地主控。你可以直接提交到后端，也可以保存到本地历史后再发给飞书助手。"
    : "当前是静态预览模式。你可以生成命令、保存到本地历史，或复制后发给飞书里的工作助手。";
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

function getComposerState() {
  return {
    lane: document.getElementById("composerLane").value,
    action: document.getElementById("composerAction").value,
    link: document.getElementById("composerLink").value.trim(),
    screenshot: document.getElementById("composerScreenshot").value.trim(),
    deadline: document.getElementById("composerDeadline").value.trim(),
    notes: document.getElementById("composerNotes").value.trim(),
  };
}

function saveComposerDraft() {
  const draft = getComposerState();
  localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
}

function restoreComposerDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) {
      return;
    }
    const draft = JSON.parse(raw);
    document.getElementById("composerLane").value = draft.lane || "wechat_growth";
    document.getElementById("composerAction").value = draft.action || "requirement_card";
    document.getElementById("composerLink").value = draft.link || "";
    document.getElementById("composerScreenshot").value = draft.screenshot || "";
    document.getElementById("composerDeadline").value = draft.deadline || "";
    document.getElementById("composerNotes").value = draft.notes || "";
  } catch (_error) {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
  }
}

function readLocalHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (_error) {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    return [];
  }
}

function writeLocalHistory(items) {
  localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(items.slice(0, HISTORY_LIMIT)));
}

function rememberLocalAction(item) {
  const history = readLocalHistory().filter((entry) => entry.id !== item.id);
  history.unshift(item);
  writeLocalHistory(history);
  renderLocalHistory(history);
}

function laneLabel(lane) {
  const map = {
    wechat_growth: "微信流量提效",
    ads_experiment: "广告专项",
    platform_integration: "多平台项目",
    daily_ops: "每日作战",
    general: "通用事项",
  };
  return map[lane] || "通用事项";
}

function actionLabel(action) {
  const map = {
    requirement_card: "需求卡片",
    prd_draft: "PRD 草稿",
    analysis: "分析/方案",
    todo: "待办",
    feedback: "反馈",
    alert: "数据告警",
    finalize: "确定定稿",
  };
  return map[action] || "通用动作";
}

function buildComposerCommand() {
  const draft = getComposerState();
  const prefix = `这是一个${laneLabel(draft.lane)}任务。`;
  const sourceLine = draft.link ? `资料位置：${draft.link}` : "资料位置：待补充";
  const screenshotLine = draft.screenshot ? `聊天截图：${draft.screenshot}` : "";
  const deadlineLine = draft.deadline ? `截止时间：${draft.deadline}` : "";

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

  const parts = [prefix, sourceLine];
  if (screenshotLine) {
    parts.push(screenshotLine);
    parts.push("请结合聊天截图一起理解上下文，不要只看文字摘要。");
  }
  parts.push(...(actionTemplates[draft.action] || actionTemplates.requirement_card));
  if (deadlineLine) {
    parts.push(deadlineLine);
  }
  if (draft.notes) {
    parts.push(`补充说明：${draft.notes}`);
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

function renderDocuments(items) {
  const node = document.getElementById("docList");
  if (!items.length) {
    node.innerHTML = '<p class="empty">暂无文档记录</p>';
    return;
  }
  node.innerHTML = items.map((item, index) => {
    const url = item.document_url || "";
    const revisionCount = Array.isArray(item.revisions) ? item.revisions.length : 0;
    return `
      <div class="history-card doc-card">
        <div class="history-head">
          <strong>${escapeHtml(item.title || `文档 ${index + 1}`)}</strong>
          <span class="badge">${escapeHtml(item.status || "draft")}</span>
        </div>
        <p>类型：${escapeHtml(item.task_type || "未标记")} · 修改轮次：${revisionCount}</p>
        <div class="history-meta">${escapeHtml(url)}</div>
        <div class="history-actions">
          ${url ? `<a class="ghost small link-button" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">打开文档</a>` : ""}
          ${url ? `<button type="button" class="ghost small" data-doc-revise="${escapeHtml(url)}">继续修改</button>` : ""}
          ${url ? `<button type="button" class="ghost small" data-doc-finalize="${escapeHtml(url)}">确定定稿</button>` : ""}
        </div>
      </div>
    `;
  }).join("");
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2200);
}

function openModal(title, command, intent = "", lane = "general", action = "general") {
  currentIntent = intent;
  currentLane = lane;
  currentAction = action;
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("commandText").value = command;
  document.getElementById("commandModal").classList.remove("hidden");
}

function closeModal() {
  currentIntent = "";
  currentLane = "general";
  currentAction = "general";
  document.getElementById("commandModal").classList.add("hidden");
}

function createLocalHistoryEntry(text, status, result = {}) {
  return {
    id: `local-${Date.now()}`,
    title: `${laneLabel(currentLane)} · ${actionLabel(currentAction)}`,
    lane: currentLane,
    action: currentAction,
    intent: currentIntent || currentAction,
    text,
    status,
    summary: result.summary || (status === "saved" ? "已保存到本地历史，待发送给飞书助手。" : "已记录到本地。"),
    materials: result.materials || [],
    doc_draft: result.doc_draft || null,
    wiki_handoff: result.wiki_handoff || null,
    todo_queue: result.todo_queue || null,
    feedback_queue: result.feedback_queue || null,
    alert_queue: result.alert_queue || null,
    warnings: result.warnings || [],
    errors: result.errors || [],
    created_at: new Date().toISOString(),
  };
}

async function copyCommand() {
  const text = document.getElementById("commandText").value;
  try {
    await navigator.clipboard.writeText(text);
    const entry = createLocalHistoryEntry(text, "copied");
    rememberLocalAction(entry);
    renderResult(entry);
    showToast("命令已复制，并记录到本地历史。");
  } catch (_error) {
    showToast("复制失败，请手动复制。");
  }
}

function saveLocalEntry() {
  const text = document.getElementById("commandText").value.trim();
  if (!text) {
    showToast("命令内容不能为空。");
    return;
  }
  const entry = createLocalHistoryEntry(text, "saved");
  rememberLocalAction(entry);
  renderResult(entry);
  closeModal();
  showToast("已保存到本地历史。");
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
  if (result.materials?.length) {
    parts.push("<p><strong>输入材料：</strong></p>");
    parts.push(...result.materials.map((item) => `<p>${escapeHtml(item)}</p>`));
  }
  if (result.doc_draft?.url) {
    parts.push(`<p><a class="link" href="${escapeHtml(result.doc_draft.url)}" target="_blank" rel="noopener noreferrer">打开飞书草稿</a></p>`);
  }
  if (result.wiki_handoff?.path) {
    parts.push(`<p>已生成 Wiki 中间稿：${escapeHtml(result.wiki_handoff.path)}</p>`);
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
  if (result.warnings?.length) {
    parts.push(...result.warnings.map((item) => `<p class="warn-text">警告：${escapeHtml(item)}</p>`));
  }
  if (result.errors?.length) {
    parts.push(...result.errors.map((item) => `<p class="error-text">错误：${escapeHtml(item)}</p>`));
  }
  if (result.created_at) {
    parts.push(`<p class="result-meta">更新时间：${escapeHtml(result.created_at)}</p>`);
  }
  node.className = "result-box";
  node.innerHTML = parts.join("") || "<p>已提交主控处理。</p>";
}

function renderLocalHistory(items) {
  const node = document.getElementById("localHistoryList");
  if (!node) {
    return;
  }
  if (!items.length) {
    node.innerHTML = '<p class="empty">还没有本地留痕。你复制、保存或直连提交后，会显示在这里。</p>';
    return;
  }
  node.innerHTML = items.map((item) => `
    <div class="history-card">
      <div class="history-head">
        <strong>${escapeHtml(item.title || "未命名动作")}</strong>
        <span class="badge">${escapeHtml(item.status || "saved")}</span>
      </div>
      <p>${escapeHtml(item.summary || "")}</p>
      <div class="history-meta">${escapeHtml(item.created_at || "")}</div>
      <div class="history-actions">
        <button type="button" class="ghost small" data-history-open="${escapeHtml(item.id)}">继续编辑</button>
        <button type="button" class="ghost small" data-history-copy="${escapeHtml(item.id)}">复制命令</button>
      </div>
    </div>
  `).join("");
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast("命令已复制。");
  } catch (_error) {
    showToast("复制失败，请手动复制。");
  }
}

function wireHistoryActions() {
  const node = document.getElementById("localHistoryList");
  node.addEventListener("click", async (event) => {
    const openId = event.target.getAttribute("data-history-open");
    const copyId = event.target.getAttribute("data-history-copy");
    if (!openId && !copyId) {
      return;
    }
    const history = readLocalHistory();
    const item = history.find((entry) => entry.id === (openId || copyId));
    if (!item) {
      return;
    }
    if (openId) {
      openModal(item.title || "继续编辑", item.text || "", item.intent || "", item.lane || "general", item.action || "general");
      return;
    }
    await copyText(item.text || "");
  });
}

function wireDocumentActions() {
  const node = document.getElementById("docList");
  node.addEventListener("click", (event) => {
    const reviseUrl = event.target.getAttribute("data-doc-revise");
    const finalizeUrl = event.target.getAttribute("data-doc-finalize");
    if (!reviseUrl && !finalizeUrl) {
      return;
    }
    if (reviseUrl) {
      openModal(
        "继续修改文档",
        [
          `请按我在这个飞书文档里的最新备注继续修改：${reviseUrl}`,
          "如果备注不完整，请结合文档当前内容补全修改。",
          "修改完成后把更新后的飞书文档链接回给我。",
        ].join("\n"),
        "revise_doc",
        currentLane || document.getElementById("composerLane").value || "general",
        "prd_draft"
      );
      return;
    }
    openModal(
      "确定定稿",
      [
        `这个飞书文档已经确认定稿：${finalizeUrl}`,
        "请进入 Notion 归档，并生成 Wiki 中间稿。",
        "完成后把归档结果和 Wiki 中间稿路径回给我。",
      ].join("\n"),
      "finalize",
      currentLane || document.getElementById("composerLane").value || "general",
      "finalize"
    );
  });
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

async function submitTextCommand(text, intent, lane, action) {
  const response = await fetch("/api/command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      source: "workbench_frontend",
      intent: intent || undefined,
      lane: lane || undefined,
      action: action || undefined,
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

  const entry = createLocalHistoryEntry(text, "submitted", payload);
  rememberLocalAction(entry);
  bind(payload.state);
  renderResult(payload);
  showToast("命令已提交到主控。");
  return payload;
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

  await submitTextCommand(text, currentIntent, currentLane, currentAction);
  closeModal();
}

function applyTemplatesToComposer() {
  document.getElementById("btnGenerateCommand").addEventListener("click", () => {
    saveComposerDraft();
    document.getElementById("composerOutput").value = buildComposerCommand();
    showToast("标准命令已生成。");
  });

  document.getElementById("btnSubmitGenerated").addEventListener("click", async () => {
    saveComposerDraft();
    const text = document.getElementById("composerOutput").value.trim() || buildComposerCommand();
    document.getElementById("composerOutput").value = text;
    if (!apiAvailable) {
      showToast("当前未连接本地后端，请先复制命令发送给飞书助手。");
      return;
    }
    await submitTextCommand(text, document.getElementById("composerAction").value, document.getElementById("composerLane").value, document.getElementById("composerAction").value);
  });

  document.getElementById("btnUseGenerated").addEventListener("click", () => {
    saveComposerDraft();
    const text = document.getElementById("composerOutput").value.trim() || buildComposerCommand();
    document.getElementById("composerOutput").value = text;
    openModal(
      `标准命令 · ${laneLabel(document.getElementById("composerLane").value)}`,
      text,
      document.getElementById("composerAction").value,
      document.getElementById("composerLane").value,
      document.getElementById("composerAction").value
    );
  });
}

function bindQuickButtons() {
  document.getElementById("btnNewCard").addEventListener("click", () => {
    openModal(
      "新建需求卡片",
      [
        "读取这个 Notion / 飞书文档链接，先整理成需求卡片草稿，不要归档。",
        "请输出：背景、目标、用户路径、规则、风险、待确认项。",
        "完成后把飞书文档链接回给我。"
      ].join("\n"),
      "new_card",
      document.getElementById("composerLane")?.value || "general",
      "requirement_card"
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
      "new_prd",
      document.getElementById("composerLane")?.value || "general",
      "prd_draft"
    );
  });

  document.getElementById("btnTodoFromShot").addEventListener("click", () => {
    document.getElementById("composerLane").value = "daily_ops";
    document.getElementById("composerAction").value = "todo";
    saveComposerDraft();
    openModal(
      "截图登记待办",
      [
        "登记一条新的待办。",
        "如果来源是企业微信聊天记录，请把聊天截图一起带上。",
        "请结合聊天截图和补充说明，拆成可执行的待办项。",
        "写清事项、截止时间、当前阻塞点、需要我回传的结果。",
      ].join("\n"),
      "todo_from_shot",
      "daily_ops",
      "todo"
    );
  });

  document.getElementById("btnNewTodo").addEventListener("click", () => {
    openModal(
      "登记待办",
      [
        "登记一条新的待办。",
        "如果来源是企业微信聊天记录，请把聊天截图一起带上。",
        "请写清：事项、截止时间、当前阻塞点、需要我回传的结果。",
      ].join("\n"),
      "todo",
      "daily_ops",
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
      "feedback",
      "daily_ops",
      "feedback"
    );
  });

  document.getElementById("btnViewAlerts").addEventListener("click", () => {
    scrollToSection("alertSection");
    showToast("已定位到数据告警区。");
  });

  document.getElementById("btnReload").addEventListener("click", reloadWorkbench);
}

function wireActions() {
  bindQuickButtons();
  applyTemplatesToComposer();
  wireHistoryActions();
  wireDocumentActions();

  document.querySelectorAll("#composerLane, #composerAction, #composerLink, #composerScreenshot, #composerDeadline, #composerNotes")
    .forEach((node) => {
      node.addEventListener("input", saveComposerDraft);
      node.addEventListener("change", saveComposerDraft);
    });

  document.getElementById("btnCopyCommand").addEventListener("click", copyCommand);
  document.getElementById("btnSaveLocal").addEventListener("click", saveLocalEntry);
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
  const localHistory = readLocalHistory();
  const lastResult = data.last_result && Object.keys(data.last_result).length ? data.last_result : localHistory[0] || null;

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
  renderDocuments(data.documents);
  document.getElementById("commandList").innerHTML = renderCommands(data.commands);
  document.getElementById("capabilityList").innerHTML = renderChips(data.capabilities);
  document.getElementById("releaseList").innerHTML = renderRelease(data.release_plan);
  document.getElementById("configList").innerHTML = renderConfig(data);
  document.getElementById("feedbackList").innerHTML = renderTable(data.feedback, ["title", "category", "status"], "暂无反馈");
  renderResult(lastResult);
  renderLocalHistory(localHistory);
}

wireActions();
restoreComposerDraft();

(async () => {
  try {
    await detectApi();
    const data = await getState();
    bind(data);
  } catch (error) {
    console.error(error);
    document.body.innerHTML = '<div class="app-shell"><p class="empty">前台数据加载失败，请先执行 render_feishu_frontend.py。</p></div>';
  }
})();
