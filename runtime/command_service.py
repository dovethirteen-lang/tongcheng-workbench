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
        source: str = "wecom_ai_bot",
        reply_target: dict[str, str] | None = None,
    ) -> tuple[ParsedCommand, Path, Path]:
        parsed = self.router.parse_command(text=text, source=source)
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
            source = str(payload.get("source", "wecom_ai_bot"))
            if not text:
                continue
            reply_target = {
                "sender_open_id": str(payload.get("sender_open_id", "") or ""),
                "chat_id": str(payload.get("chat_id", "") or ""),
                "source": source,
            }
            parsed, command_path, reply_path = self.accept_text(
                text=text,
                source=source,
                reply_target=reply_target,
            )
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
        lines.extend(f"- {item}" for item in reply.get("next_actions", [])[:3])
        doc_draft = reply.get("doc_draft") or {}
        if doc_draft.get("url"):
            lines.extend(["", f"飞书草稿：{doc_draft['url']}"])
        notion_archive = reply.get("notion_archive") or {}
        if notion_archive.get("queue_file"):
            lines.extend(["", f"Notion 归档队列：{notion_archive['queue_file']}"])
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
