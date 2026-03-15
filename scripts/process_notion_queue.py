from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_markdown(payload: dict) -> str:
    lines = [
        f"# {payload.get('title', 'Notion 归档草稿')}",
        "",
        f"- 内容类型：{payload.get('content_type', '')}",
        f"- 建议落库：{payload.get('target_database', '')}",
        f"- 状态：{payload.get('status', 'draft')}",
        f"- 通知渠道：{payload.get('notify_channel', '')}",
        "",
        "## 摘要",
        payload.get("summary", ""),
        "",
        "## 下一步",
    ]
    lines.extend(f"- {item}" for item in payload.get("next_actions", []))
    if payload.get("assumptions"):
        lines.extend(["", "## 默认假设"])
        lines.extend(f"- {item}" for item in payload.get("assumptions", []))
    if payload.get("source_links"):
        lines.extend(["", "## 来源链接"])
        lines.extend(f"- {item}" for item in payload.get("source_links", []))
    draft = payload.get("feishu_doc_draft") or {}
    if draft.get("url"):
        lines.extend(["", "## 飞书草稿", draft["url"]])
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render queued Notion archive payloads to Markdown.")
    parser.add_argument("--file", type=Path, help="Specific queue file to render.")
    parser.add_argument("--output-dir", type=Path, default=Path(r"D:\Project\docs\notion_queue"))
    args = parser.parse_args()

    queue_files = [args.file] if args.file else sorted(Path(r"D:\Project\runtime\notion_queue").glob("*.json"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rendered: list[str] = []
    for path in queue_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        out = args.output_dir / f"{path.stem}.md"
        out.write_text(render_markdown(payload), encoding="utf-8")
        rendered.append(str(out))

    print(json.dumps({"ok": True, "rendered": rendered}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
