from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .orchestrator import ParsedCommand, load_router


class CommandService:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.router = load_router(base_dir)
        self.project_root = Path(r"D:\Project")
        self.runtime_root = self.project_root / "runtime" / "command_bus"
        self.inbox_dir = self.runtime_root / "inbox"
        self.outbox_dir = self.runtime_root / "outbox"
        self.processed_dir = self.runtime_root / "processed"
        self.command_log_dir = base_dir / "tmp" / "commands"
        for path in [self.runtime_root, self.inbox_dir, self.outbox_dir, self.processed_dir, self.command_log_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def accept_text(
        self,
        text: str,
        source: str = "feishu_longconn",
        reply_target: dict[str, str] | None = None,
        hints: dict[str, Any] | None = None,
    ) -> tuple[ParsedCommand, Path, Path]:
        parsed = self.router.parse_command(text=text, source=source, hints=hints)
        command_path = self.router.dump_command(parsed, self.command_log_dir)
        reply_path = self._write_reply(parsed, reply_target=reply_target)
        return parsed, command_path, reply_path

    def enqueue_incoming(self, payload: dict[str, Any]) -> Path:
        message_id = payload.get("message_id") or f"msg-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        path = self.inbox_dir / f"{message_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def process_inbox(self) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for path in sorted(self.inbox_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            text = str(payload.get("text", "")).strip()
            source = str(payload.get("source", "feishu_longconn"))
            if not text:
                continue
            reply_target = {
                "sender_open_id": str(payload.get("sender_open_id", "") or ""),
                "chat_id": str(payload.get("chat_id", "") or ""),
                "source": source,
            }
            parsed, command_path, reply_path = self.accept_text(text=text, source=source, reply_target=reply_target)
            target = self.processed_dir / path.name
            path.replace(target)
            results.append(
                {
                    "message_file": str(target),
                    "command_file": str(command_path),
                    "reply_file": str(reply_path),
                    "command_id": parsed.command_id,
                }
            )
        return results

    def format_reply_text(self, reply: dict[str, Any]) -> str:
        lines = [
            reply.get("title", "主控层已收到任务"),
            reply.get("summary", ""),
            "",
            "下一步：",
        ]
        lines.extend(f"- {item}" for item in reply.get("next_actions", [])[:4])

        materials = reply.get("materials") or []
        if materials:
            lines.extend(["", "输入材料："])
            lines.extend(f"- {item}" for item in materials[:5])

        doc_draft = reply.get("doc_draft") or {}
        if doc_draft.get("url"):
            lines.extend(["", f"飞书草稿：{doc_draft['url']}"])

        revision = reply.get("revision_request") or {}
        if revision.get("document_url"):
            lines.extend(
                [
                    "",
                    f"已写入修改记录：第 {revision.get('revision_index', 0)} 轮",
                    f"当前文档：{revision['document_url']}",
                ]
            )

        notion_archive = reply.get("notion_archive") or {}
        if notion_archive.get("queue_file"):
            lines.extend(["", f"已进入 Notion 归档队列：{notion_archive['queue_file']}"])

        wiki_handoff = reply.get("wiki_handoff") or {}
        if wiki_handoff.get("path"):
            lines.extend(["", f"Wiki 中间稿：{wiki_handoff['path']}"])

        todo = reply.get("todo_item") or {}
        if todo.get("title"):
            lines.extend(["", f"已登记待办：{todo['title']}"])
        todo_queue = reply.get("todo_queue") or {}
        if todo_queue.get("path"):
            lines.extend([f"待办收口：{todo_queue['path']}"])

        feedback = reply.get("feedback_item") or {}
        if feedback.get("title"):
            lines.extend(["", f"已记录反馈：{feedback['title']}"])
        feedback_queue = reply.get("feedback_queue") or {}
        if feedback_queue.get("path"):
            lines.extend([f"反馈收口：{feedback_queue['path']}"])

        alert = reply.get("alert_item") or {}
        if alert.get("title"):
            lines.extend(["", f"已记录数据告警：{alert['title']}"])
        alert_queue = reply.get("alert_queue") or {}
        if alert_queue.get("path"):
            lines.extend([f"告警收口：{alert_queue['path']}"])

        status_page = reply.get("status_page") or {}
        if status_page.get("path"):
            lines.extend(["", f"状态页：{status_page['path']}"])

        return "\n".join(line for line in lines if line is not None).strip()

    def read_reply(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def save_reply(self, path: Path, reply: dict[str, Any]) -> None:
        path.write_text(json.dumps(reply, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_reply(self, parsed: ParsedCommand, reply_target: dict[str, str] | None = None) -> Path:
        body = {
            "command_id": parsed.command_id,
            "notify_channel": parsed.notify_channel,
            "title": "主控层已接收任务",
            "summary": self._build_summary(parsed),
            "next_actions": parsed.next_actions,
            "assumptions": parsed.assumptions,
            "materials": parsed.inputs,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "command": asdict(parsed),
            "reply_target": reply_target or {},
        }
        path = self.outbox_dir / f"{parsed.command_id}.json"
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _build_summary(self, parsed: ParsedCommand) -> str:
        route_to = "、".join(parsed.route_to)
        outputs = "、".join(parsed.outputs)
        deadline = parsed.deadline_hint or "未明确截止时间"
        return (
            f"已识别为 {parsed.task_type} 任务，主控层将分发给 {route_to}。"
            f" 预期产出包括：{outputs}。"
            f" 当前截止要求：{deadline}。"
        )
