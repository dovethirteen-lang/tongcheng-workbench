from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .command_service import CommandService
from .feishu_docx import (
    FeishuDocxError,
    append_revision_request,
    extract_document_id,
    is_revision_request,
    should_create_doc_draft,
    create_doc_draft,
)
from .notion_archive import enqueue_notion_archive, enqueue_workspace_capture, should_archive_to_notion
from .orchestrator import ParsedCommand
from .wiki_handoff import create_wiki_handoff
from .workbench_state import WorkbenchState


TODO_KEYWORDS = ["待办", "todo", "提醒", "deadline", "排期", "跟进"]
FEEDBACK_KEYWORDS = ["反馈", "bug", "问题", "优化建议", "迭代", "不好用"]
ALERT_KEYWORDS = ["告警", "异常", "波动", "下降", "暴跌", "预警", "监控"]


@dataclass
class TaskPipelineResult:
    parsed: ParsedCommand
    command_path: Path
    reply_path: Path
    reply: dict[str, Any]


class TaskPipeline:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.command_service = CommandService(base_dir)
        self.state = WorkbenchState()
        self.runtime_root = Path(r"D:\Project\runtime\feishu_longconn")
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def process_text(
        self,
        text: str,
        source: str,
        reply_target: dict[str, str] | None = None,
        create_remote_artifacts: bool = True,
        intent: str | None = None,
        lane: str | None = None,
        action: str | None = None,
    ) -> TaskPipelineResult:
        parsed, command_path, reply_path = self.command_service.accept_text(
            text=text,
            source=source,
            reply_target=reply_target,
            hints={"lane": lane, "action": action},
        )
        self.state.record_command(parsed)
        reply = self.command_service.read_reply(reply_path)

        if create_remote_artifacts and should_create_doc_draft(parsed):
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
                if doc_draft.get("warning"):
                    reply.setdefault("warnings", []).append(doc_draft["warning"])
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
                reply.setdefault("errors", []).append(str(exc))
                self._write_runtime_log({"level": "error", "stage": "doc_draft", "message": str(exc)})

        if create_remote_artifacts and is_revision_request(parsed):
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
                    reply.setdefault("errors", []).append(str(exc))
                    self._write_runtime_log({"level": "error", "stage": "revision", "message": str(exc)})

        todo_item = self._maybe_capture_todo(parsed, intent=intent)
        if todo_item:
            reply["todo_item"] = todo_item
            reply["todo_queue"] = {"path": str(enqueue_workspace_capture(self.base_dir, "todo", todo_item))}

        feedback_item = self._maybe_capture_feedback(parsed, intent=intent)
        if feedback_item:
            reply["feedback_item"] = feedback_item
            reply["feedback_queue"] = {"path": str(enqueue_workspace_capture(self.base_dir, "feedback", feedback_item))}

        alert_item = self._maybe_capture_alert(parsed, intent=intent)
        if alert_item:
            reply["alert_item"] = alert_item
            reply["alert_queue"] = {"path": str(enqueue_workspace_capture(self.base_dir, "alert", alert_item))}

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
        self.state.record_result(
            {
                "command_id": parsed.command_id,
                "task_type": parsed.task_type,
                "lane": parsed.lane,
                "action": parsed.action,
                "summary": reply.get("summary", ""),
                "materials": reply.get("materials", []),
                "doc_draft": reply.get("doc_draft"),
                "revision_request": reply.get("revision_request"),
                "notion_archive": reply.get("notion_archive"),
                "wiki_handoff": reply.get("wiki_handoff"),
                "todo_item": reply.get("todo_item"),
                "feedback_item": reply.get("feedback_item"),
                "alert_item": reply.get("alert_item"),
                "todo_queue": reply.get("todo_queue"),
                "feedback_queue": reply.get("feedback_queue"),
                "alert_queue": reply.get("alert_queue"),
                "warnings": reply.get("warnings", []),
                "errors": reply.get("errors", []),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._write_runtime_log(
            {
                "level": "info",
                "stage": "pipeline_complete",
                "command_id": parsed.command_id,
                "command_file": str(command_path),
                "reply_file": str(reply_path),
            }
        )
        return TaskPipelineResult(parsed=parsed, command_path=command_path, reply_path=reply_path, reply=reply)

    def _maybe_capture_todo(self, parsed: ParsedCommand, intent: str | None = None) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        if intent != "todo" and not any(keyword in text for keyword in TODO_KEYWORDS):
            return None
        return self.state.record_todo(
            title=parsed.normalized_text[:80],
            source=parsed.source,
            deadline_hint=parsed.deadline_hint,
        )

    def _maybe_capture_feedback(self, parsed: ParsedCommand, intent: str | None = None) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        matched = next((keyword for keyword in FEEDBACK_KEYWORDS if keyword in text), None)
        if intent == "feedback":
            matched = matched or "feedback"
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

    def _maybe_capture_alert(self, parsed: ParsedCommand, intent: str | None = None) -> dict[str, Any] | None:
        text = parsed.normalized_text.lower()
        if intent != "alert" and not any(keyword in text for keyword in ALERT_KEYWORDS):
            return None
        severity = "high" if any(token in text for token in ["暴跌", "异常", "预警"]) else "medium"
        return self.state.record_alert(
            title=parsed.normalized_text[:60],
            detail=parsed.normalized_text,
            source=parsed.source,
            severity=severity,
        )

    def _write_runtime_log(self, payload: dict[str, Any]) -> None:
        path = self.runtime_root / "events.log"
        entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), **payload}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
