from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .orchestrator import ParsedCommand


FINALIZE_KEYWORDS = [
    "归档",
    "归档到notion",
    "同步到notion",
    "定稿",
    "最终版",
    "终稿",
    "发布到wiki",
    "发布wiki",
    "准备上线",
    "可以归档",
    "沉淀到notion",
    "archive",
    "archive to notion",
    "final",
    "final version",
    "publish to wiki",
]

NEGATIVE_PATTERNS = [
    "不要归档",
    "先不要归档",
    "暂不归档",
    "不用归档",
    "无需归档",
    "not archive",
    "do not archive",
]


def _load_workspace_config(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "config" / "notion_workspace.json"
    return json.loads(path.read_text(encoding="utf-8"))


def should_archive_to_notion(parsed: ParsedCommand) -> bool:
    text = parsed.normalized_text.lower()
    if any(pattern in text for pattern in NEGATIVE_PATTERNS):
        return False
    return any(keyword in text for keyword in FINALIZE_KEYWORDS)


def _recommend_database(parsed: ParsedCommand, workspace_config: dict[str, Any]) -> str:
    content_map = {
        "knowledge_archive": "需求卡片库",
        "wechat_growth": "PRD 库",
        "ads_experiment": "广告实验库",
        "platform_integration": "需求卡片库",
        "daily_ops": "每日作战库",
    }
    fallback = "需求卡片库"
    preferred = content_map.get(parsed.task_type, fallback)
    for item in workspace_config.get("recommended_databases", []):
        if item.get("name") == preferred:
            return preferred
    return fallback


def build_notion_archive_payload(base_dir: Path, parsed: ParsedCommand, reply: dict[str, Any]) -> dict[str, Any]:
    workspace_config = _load_workspace_config(base_dir)
    doc_draft = reply.get("doc_draft") or {}
    return {
        "title": (doc_draft.get("title") or f"{parsed.task_type}｜{parsed.normalized_text[:32]}").strip(),
        "content_type": parsed.task_type,
        "target_database": _recommend_database(parsed, workspace_config),
        "summary": reply.get("summary", ""),
        "status": "ready_for_archive",
        "notify_channel": parsed.notify_channel,
        "source": parsed.source,
        "source_links": parsed.inputs,
        "outputs": parsed.outputs,
        "next_actions": parsed.next_actions,
        "assumptions": parsed.assumptions,
        "feishu_doc_draft": doc_draft,
        "command": asdict(parsed),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def enqueue_notion_archive(base_dir: Path, parsed: ParsedCommand, reply: dict[str, Any]) -> Path:
    queue_dir = Path(r"D:\Project\runtime\notion_queue")
    queue_dir.mkdir(parents=True, exist_ok=True)
    payload = build_notion_archive_payload(base_dir, parsed, reply)
    path = queue_dir / f"{parsed.command_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
