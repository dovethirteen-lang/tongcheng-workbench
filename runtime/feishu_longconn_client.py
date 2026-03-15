from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import lark_oapi as lark

from .command_service import CommandService
from .feishu_client import FeishuAPIError, load_feishu_config, send_text_message
from .feishu_docx import (
    FeishuDocxError,
    append_revision_request,
    create_doc_draft,
    extract_document_id,
    is_revision_request,
    should_create_doc_draft,
)
from .notion_archive import enqueue_notion_archive, should_archive_to_notion
from .wiki_handoff import create_wiki_handoff
from .workbench_state import WorkbenchState


TODO_KEYWORDS = ["待办", "todo", "提醒", "deadline", "排期", "跟进"]
FEEDBACK_KEYWORDS = ["反馈", "bug", "问题", "优化建议", "迭代", "不好用"]
ALERT_KEYWORDS = ["告警", "异常", "波动", "下降", "暴跌", "预警", "监控"]


def _extract_text(content: str | None) -> str:
    if not content:
        return ""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return content.strip()
    return str(payload.get("text", "")).strip()


class FeishuLongConnectionApp:
    def __init__(self, base_dir: Path, log_level: str = "INFO") -> None:
        self.base_dir = base_dir
        self.config = load_feishu_config(base_dir)
        self.command_service = CommandService(base_dir)
        self.state = WorkbenchState()
        self.runtime_root = Path(r"D:\Project\runtime\feishu_longconn")
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.log_level = getattr(lark.LogLevel, log_level.upper(), lark.LogLevel.INFO)
        self.ws_client = lark.ws.Client(
            self.config["app_id"],
            self.config["app_secret"],
            event_handler=self._build_event_handler(),
            log_level=self.log_level,
        )
        self._write_runtime_log({"level": "info", "stage": "init", "message": "Feishu long connection client initialized."})

    def _build_event_handler(self) -> lark.EventDispatcherHandler:
        return (
            lark.EventDispatcherHandler.builder("", "", self.log_level)
            .register_p2_im_message_receive_v1(self._on_message_received)
            .build()
        )

    def _on_message_received(self, data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        event = data.event
        if event is None or event.message is None:
            self._write_runtime_log({"level": "warning", "stage": "receive", "message": "Empty event payload received."})
            return

        message = event.message
        if message.message_type != "text":
            self._write_runtime_log(
                {
                    "level": "info",
                    "stage": "receive",
                    "message": "Ignored non-text message.",
                    "message_type": message.message_type or "",
                }
            )
            return

        sender_open_id = ""
        if event.sender and event.sender.sender_id and event.sender.sender_id.open_id:
            sender_open_id = event.sender.sender_id.open_id

        text = _extract_text(message.content)
        if not text:
            self._write_runtime_log({"level": "warning", "stage": "receive", "message": "Received empty text content."})
            return

        self._write_runtime_log(
            {
                "level": "info",
                "stage": "receive",
                "message": "Text message received from Feishu.",
                "sender_open_id": sender_open_id,
                "chat_id": message.chat_id or "",
                "text": text,
            }
        )

        reply_target = {
            "sender_open_id": sender_open_id,
            "chat_id": message.chat_id or "",
            "source": "feishu_longconn",
        }
        parsed, command_path, reply_path = self.command_service.accept_text(
            text=text,
            source="feishu_longconn",
            reply_target=reply_target,
        )
        self.state.record_command(parsed)

        reply = self.command_service.read_reply(reply_path)

        if should_create_doc_draft(parsed):
            try:
                doc_draft = create_doc_draft(self.base_dir, parsed, reply)
                reply["doc_draft"] = doc_draft
                self.state.record_document(
                    {
                        "document_id": doc_draft["document_id"],
                        "document_url": doc_draft["url"],
                        "title": doc_draft["title"],
                        "task_type": parsed.task_type,
                        "status": "draft",
                        "created_at": parsed.created_at,
                        "source_command_id": parsed.command_id,
                        "revisions": [],
                    }
                )
                self._write_runtime_log(
                    {
                        "level": "info",
                        "stage": "doc_draft",
                        "message": "Feishu doc draft created.",
                        "document_id": doc_draft["document_id"],
                        "url": doc_draft["url"],
                    }
                )
            except FeishuDocxError as exc:
                self._write_runtime_log({"level": "error", "stage": "doc_draft", "message": str(exc)})

        if is_revision_request(parsed):
            document_id = extract_document_id(parsed.normalized_text)
            if document_id:
                try:
                    revision_index = self.state.append_revision(document_id, parsed.normalized_text)
                    reply["revision_request"] = append_revision_request(self.base_dir, parsed, revision_index)
                    self._write_runtime_log(
                        {
                            "level": "info",
                            "stage": "revision",
                            "message": "Revision request appended to Feishu doc.",
                            "document_id": document_id,
                            "revision_index": revision_index,
                        }
                    )
                except FeishuDocxError as exc:
                    self._write_runtime_log({"level": "error", "stage": "revision", "message": str(exc)})

        todo_item = self._maybe_capture_todo(parsed)
        if todo_item:
            reply["todo_item"] = todo_item

        feedback_item = self._maybe_capture_feedback(parsed)
        if feedback_item:
            reply["feedback_item"] = feedback_item

        alert_item = self._maybe_capture_alert(parsed)
        if alert_item:
            reply["alert_item"] = alert_item

        if should_archive_to_notion(parsed):
            queue_path = enqueue_notion_archive(self.base_dir, parsed, reply)
            reply["notion_archive"] = {"queue_file": str(queue_path)}
            reply["wiki_handoff"] = {"path": str(create_wiki_handoff(parsed, reply))}
            document_id = extract_document_id(parsed.normalized_text)
            if document_id:
                self.state.mark_document_final(document_id)
            self._write_runtime_log(
                {
                    "level": "info",
                    "stage": "notion_archive",
                    "message": "Notion archive payload queued.",
                    "queue_file": str(queue_path),
                }
            )

        status_page = Path(r"D:\Project\runtime\workbench_status.html")
        if status_page.exists():
            reply["status_page"] = {"path": str(status_page)}

        self.command_service.save_reply(reply_path, reply)

        self._write_runtime_log(
            {
                "command_id": parsed.command_id,
                "command_file": str(command_path),
                "reply_file": str(reply_path),
                "sender_open_id": sender_open_id,
                "chat_id": message.chat_id or "",
            }
        )
        if sender_open_id:
            self._send_reply(sender_open_id, reply)

    def _maybe_capture_todo(self, parsed: Any) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        if not any(keyword in text for keyword in TODO_KEYWORDS):
            return None
        return self.state.record_todo(
            title=parsed.normalized_text[:80],
            source=parsed.source,
            deadline_hint=parsed.deadline_hint,
        )

    def _maybe_capture_feedback(self, parsed: Any) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        matched = next((keyword for keyword in FEEDBACK_KEYWORDS if keyword in text), None)
        if not matched:
            return None
        category = "bug" if "bug" in text else "experience_issue"
        if "新需求" in parsed.normalized_text:
            category = "new_requirement"
        return self.state.record_feedback(
            title=parsed.normalized_text[:60],
            detail=parsed.normalized_text,
            source=parsed.source,
            category=category,
        )

    def _maybe_capture_alert(self, parsed: Any) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        if not any(keyword in text for keyword in ALERT_KEYWORDS):
            return None
        severity = "high" if any(token in text for token in ["暴跌", "异常", "预警"]) else "medium"
        return self.state.record_alert(
            title=parsed.normalized_text[:60],
            detail=parsed.normalized_text,
            source=parsed.source,
            severity=severity,
        )

    def _send_reply(self, receive_id: str, reply: dict[str, Any]) -> None:
        text = self.command_service.format_reply_text(reply)
        try:
            send_text_message(self.config, receive_id=receive_id, text=text, receive_id_type="open_id")
        except FeishuAPIError as exc:
            self._write_runtime_log({"level": "error", "error": str(exc), "stage": "send_reply"})

    def _write_runtime_log(self, payload: dict[str, Any]) -> None:
        path = self.runtime_root / "events.log"
        line = json.dumps(payload, ensure_ascii=False)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def start(self) -> None:
        self._write_runtime_log({"level": "info", "stage": "start", "message": "Feishu long connection client starting."})
        self.ws_client.start()

    async def connect_and_hold(self) -> None:
        self._write_runtime_log(
            {
                "level": "info",
                "stage": "connect_hold",
                "message": "Feishu long connection probe connecting.",
            }
        )
        await self.ws_client._connect()
        self._write_runtime_log(
            {
                "level": "info",
                "stage": "connected",
                "message": "Feishu long connection established and held for platform verification.",
                "conn_url": self.ws_client._conn_url,
            }
        )
        try:
            while True:
                await asyncio.sleep(5)
        finally:
            await self.ws_client._disconnect()
