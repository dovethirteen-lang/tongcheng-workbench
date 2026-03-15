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
    routing_map = workspace_config.get("routing_map", {})
    route = routing_map.get(parsed.task_type) or routing_map.get("general", {})
    preferred = route.get("database", "Inbox收件箱")
    for item in workspace_config.get("recommended_databases", []):
        if item.get("name") == preferred:
            return preferred
    return preferred


def _recommend_route(task_type: str, workspace_config: dict[str, Any]) -> dict[str, Any]:
    routing_map = workspace_config.get("routing_map", {})
    return routing_map.get(task_type) or routing_map.get("general", {})


def build_notion_archive_payload(base_dir: Path, parsed: ParsedCommand, reply: dict[str, Any]) -> dict[str, Any]:
    workspace_config = _load_workspace_config(base_dir)
    doc_draft = reply.get("doc_draft") or {}
    route = _recommend_route(parsed.task_type, workspace_config)
    return {
        "title": (doc_draft.get("title") or f"{route.get('entry_prefix', parsed.task_type)}｜{parsed.normalized_text[:32]}").strip(),
        "content_type": parsed.task_type,
        "target_database": _recommend_database(parsed, workspace_config),
        "target_stage": route.get("stage", ""),
        "workspace_url": workspace_config.get("workspace_url", ""),
        "private_library_url": workspace_config.get("private_library_url", ""),
        "template_url": workspace_config.get("prd_template_url", ""),
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


def enqueue_workspace_capture(base_dir: Path, entry_type: str, payload: dict[str, Any]) -> Path:
    workspace_config = _load_workspace_config(base_dir)
    queue_dir = Path(r"D:\Project\runtime\notion_workspace_queue") / entry_type
    queue_dir.mkdir(parents=True, exist_ok=True)

    if entry_type == "todo":
        strategy = workspace_config.get("todo_strategy", {})
        target_database = strategy.get("database", "工作分区")
        target_entry = strategy.get("entry_name", "待办池")
    elif entry_type == "feedback":
        strategy = workspace_config.get("feedback_strategy", {})
        target_database = strategy.get("database", "Inbox收件箱")
        target_entry = strategy.get("entry_name", "工作台反馈")
    else:
        strategy = {}
        target_database = "工作分区"
        target_entry = "数据告警"

    record = {
        "entry_type": entry_type,
        "target_database": target_database,
        "target_entry": target_entry,
        "workspace_url": workspace_config.get("workspace_url", ""),
        "private_library_url": workspace_config.get("private_library_url", ""),
        "payload": payload,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": strategy.get("notes", ""),
    }
    path = queue_dir / f"{entry_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
