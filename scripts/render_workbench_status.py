from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.workbench_state import WorkbenchState


def _render_list(items: list[dict], fields: list[str], empty: str) -> str:
    if not items:
        return f"<p class='empty'>{escape(empty)}</p>"
    rows = []
    for item in items:
        cols = "".join(f"<td>{escape(str(item.get(field, '')))}</td>" for field in fields)
        rows.append(f"<tr>{cols}</tr>")
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def main() -> None:
    state = WorkbenchState().snapshot()
    output_path = Path(r"D:\Project\runtime\workbench_status.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    commands = state.get("commands", [])[:8]
    documents = state.get("documents", [])[:8]
    todos = state.get("todos", [])[:8]
    feedback = state.get("feedback", [])[:8]
    alerts = state.get("alerts", [])[:8]
    capabilities = state.get("capabilities", {})
    release_plan = state.get("release_plan", {})

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>同程产品工作台状态页</title>
  <style>
    :root {{
      --bg: #09111f;
      --panel: #111c31;
      --line: #243452;
      --text: #eaf1ff;
      --muted: #93a4c7;
      --accent: #60a5fa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 24px;
      background: radial-gradient(circle at top, #17284a, var(--bg) 48%);
      color: var(--text);
      font: 14px/1.6 "Segoe UI", "Microsoft YaHei", sans-serif;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      margin-top: 18px;
    }}
    .panel {{
      background: rgba(17, 28, 49, 0.92);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
    }}
    .chip {{
      display: inline-block;
      margin: 0 8px 8px 0;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(96, 165, 250, 0.14);
      border: 1px solid rgba(96, 165, 250, 0.35);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    td {{
      border-top: 1px solid var(--line);
      padding: 10px 8px;
      vertical-align: top;
    }}
    .empty {{ color: var(--muted); margin: 0; }}
    .meta {{
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      margin-top: 18px;
    }}
    .meta-card {{
      padding: 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--line);
    }}
    .meta-card strong {{
      display: block;
      font-size: 22px;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <h1>同程产品工作台状态页</h1>
  <p class="muted">更新时间：{escape(state.get("updated_at", ""))}</p>
  <div class="meta">
    <div class="meta-card">最近命令<strong>{len(commands)}</strong></div>
    <div class="meta-card">文档数量<strong>{len(documents)}</strong></div>
    <div class="meta-card">打开待办<strong>{len([x for x in todos if x.get("status") == "open"])}</strong></div>
    <div class="meta-card">反馈池<strong>{len(feedback)}</strong></div>
    <div class="meta-card">数据告警<strong>{len(alerts)}</strong></div>
  </div>
  <div class="grid">
    <section class="panel">
      <h2>版本规划</h2>
      {"".join(f"<div class='chip'>{escape(k)} · {escape(v)}</div>" for k, v in release_plan.items())}
    </section>
    <section class="panel">
      <h2>当前能力现状</h2>
      {"".join(f"<div class='chip'>{escape(k)}：{escape(v)}</div>" for k, v in capabilities.items())}
    </section>
    <section class="panel">
      <h2>最近命令</h2>
      {_render_list(commands, ["command_id", "task_type", "normalized_text"], "暂无命令记录")}
    </section>
    <section class="panel">
      <h2>文档状态</h2>
      {_render_list(documents, ["title", "status", "document_url"], "暂无文档记录")}
    </section>
    <section class="panel">
      <h2>待办池</h2>
      {_render_list(todos, ["title", "deadline_hint", "status"], "暂无待办")}
    </section>
    <section class="panel">
      <h2>反馈池</h2>
      {_render_list(feedback, ["title", "status", "source"], "暂无反馈")}
    </section>
    <section class="panel">
      <h2>数据告警</h2>
      {_render_list(alerts, ["title", "severity", "status"], "暂无数据告警")}
    </section>
  </div>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
