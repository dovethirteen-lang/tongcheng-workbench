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


def _render_chip_map(items: dict[str, str]) -> str:
    return "".join(f"<div class='chip'>{escape(k)}：{escape(v)}</div>" for k, v in items.items())


def _build_html(state: dict) -> str:
    commands = state.get("commands", [])[:8]
    documents = state.get("documents", [])[:8]
    todos = state.get("todos", [])[:8]
    feedback = state.get("feedback", [])[:8]
    alerts = state.get("alerts", [])[:8]
    capabilities = state.get("capabilities", {})
    release_plan = state.get("release_plan", {})
    open_todos = len([x for x in todos if x.get("status") == "open"])
    open_alerts = len([x for x in alerts if x.get("status") == "open"])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>同程产品工作台总控台</title>
  <style>
    :root {{
      --bg: #08111e;
      --panel: rgba(16, 25, 43, 0.92);
      --line: #233556;
      --text: #edf4ff;
      --muted: #93a6c9;
      --brand: #66b3ff;
      --warn: #ffbf47;
      --danger: #ff6d85;
      --ok: #36d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      font: 14px/1.65 "Segoe UI", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(102,179,255,0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(255,191,71,0.12), transparent 24%),
        linear-gradient(180deg, #07101c 0%, #08111e 100%);
    }}
    .shell {{
      max-width: 1460px;
      margin: 0 auto;
      padding: 22px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 20px 55px rgba(0,0,0,0.24);
    }}
    .hero {{
      padding: 24px;
      margin-bottom: 16px;
    }}
    .hero-top {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 18px;
    }}
    h1, h2, h3 {{ margin: 0 0 10px; }}
    h1 {{ font-size: clamp(30px, 5vw, 48px); line-height: 1.05; letter-spacing: -0.04em; }}
    h2 {{ font-size: 20px; }}
    .muted {{ color: var(--muted); }}
    .brand {{
      color: var(--brand);
      font-weight: 700;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .meta {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    }}
    .metric {{
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.02);
    }}
    .metric strong {{
      display: block;
      font-size: 28px;
      margin-top: 6px;
    }}
    .metric.warn strong {{ color: var(--warn); }}
    .metric.danger strong {{ color: var(--danger); }}
    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: 1.15fr 0.85fr;
      margin-bottom: 16px;
    }}
    .stack {{
      display: grid;
      gap: 16px;
    }}
    .panel {{
      padding: 18px;
    }}
    .chip-row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .chip {{
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(102,179,255,0.25);
      background: rgba(102,179,255,0.1);
      color: var(--text);
      font-size: 12px;
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
      color: var(--text);
    }}
    .empty {{
      margin: 0;
      color: var(--muted);
    }}
    .alert-card {{
      padding: 14px;
      border-radius: 16px;
      border: 1px solid rgba(255,109,133,0.26);
      background: rgba(255,109,133,0.08);
      margin-bottom: 10px;
    }}
    .alert-card:last-child {{ margin-bottom: 0; }}
    .alert-card strong {{
      display: block;
      margin-bottom: 4px;
      color: #ffd6de;
    }}
    .section-desc {{
      margin: 0 0 12px;
      color: var(--muted);
    }}
    @media (max-width: 1024px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <div class="brand">Tongcheng Workbench</div>
          <h1>同程产品工作台总控台</h1>
          <p class="muted">这不是纯说明页了，而是当前工作台的可视化前台。你可以在这里看数据告警、待办、文档状态、反馈池和版本进展。</p>
        </div>
        <div class="muted">更新时间：{escape(state.get("updated_at", ""))}</div>
      </div>
      <div class="meta">
        <div class="metric"><span>最近命令</span><strong>{len(commands)}</strong></div>
        <div class="metric"><span>文档数量</span><strong>{len(documents)}</strong></div>
        <div class="metric"><span>打开待办</span><strong>{open_todos}</strong></div>
        <div class="metric danger"><span>数据告警</span><strong>{open_alerts}</strong></div>
        <div class="metric"><span>反馈池</span><strong>{len(feedback)}</strong></div>
      </div>
    </section>

    <div class="grid">
      <div class="stack">
        <section class="panel">
          <h2>数据告警</h2>
          <p class="section-desc">这里放广告实验、流量波动、关键指标异常下降等需要优先处理的信号。</p>
          {''.join(
              f"<div class='alert-card'><strong>{escape(str(item.get('title','')))}</strong>"
              f"<div class='muted'>级别：{escape(str(item.get('severity','')))} · 状态：{escape(str(item.get('status','')))}</div>"
              f"<div>{escape(str(item.get('detail','')))}</div></div>"
              for item in alerts
          ) or "<p class='empty'>暂无数据告警</p>"}
        </section>

        <section class="panel">
          <h2>待办池</h2>
          <p class="section-desc">早期先用单池模式收口，后续再按专项拆分。</p>
          {_render_list(todos, ["title", "deadline_hint", "status"], "暂无待办")}
        </section>

        <section class="panel">
          <h2>文档状态</h2>
          <p class="section-desc">这里看飞书草稿、修订中、已定稿的文档状态。</p>
          {_render_list(documents, ["title", "status", "document_url"], "暂无文档记录")}
        </section>
      </div>

      <div class="stack">
        <section class="panel">
          <h2>当前能力现状</h2>
          <div class="chip-row">{_render_chip_map(capabilities)}</div>
        </section>

        <section class="panel">
          <h2>版本规划</h2>
          <div class="chip-row">{_render_chip_map(release_plan)}</div>
        </section>

        <section class="panel">
          <h2>反馈池</h2>
          <p class="section-desc">工作日先在这里收口问题，周末集中做迭代。</p>
          {_render_list(feedback, ["title", "category", "status"], "暂无反馈")}
        </section>

        <section class="panel">
          <h2>最近命令</h2>
          {_render_list(commands, ["command_id", "task_type", "normalized_text"], "暂无命令记录")}
        </section>
      </div>
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    state = WorkbenchState().snapshot()
    runtime_output = Path(r"D:\Project\runtime\workbench_status.html")
    dashboard_output = BASE_DIR / "08_dashboard" / "workflow_overview.html"
    runtime_output.parent.mkdir(parents=True, exist_ok=True)
    dashboard_output.parent.mkdir(parents=True, exist_ok=True)
    html = _build_html(state)
    runtime_output.write_text(html, encoding="utf-8")
    dashboard_output.write_text(html, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "runtime_output": str(runtime_output),
                "dashboard_output": str(dashboard_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
