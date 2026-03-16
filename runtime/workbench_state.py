from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .orchestrator import ParsedCommand


class WorkbenchState:
    def __init__(self) -> None:
        self.path = Path(r"D:\Project\runtime\workspace_state.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        defaults = self._defaults()
        if not self.path.exists():
            self._write(defaults)
            return

        payload = self._read()
        payload.setdefault("commands", [])
        payload.setdefault("documents", [])
        payload.setdefault("todos", [])
        payload.setdefault("feedback", [])
        payload.setdefault("alerts", [])
        payload.setdefault("last_result", {})
        payload.setdefault("activity", [])
        payload["capabilities"] = defaults["capabilities"]
        payload["release_plan"] = defaults["release_plan"]
        self._write(payload)

    def _defaults(self) -> dict[str, Any]:
        return {
            "updated_at": "",
            "commands": [],
            "documents": [],
            "todos": [],
            "feedback": [],
            "alerts": [],
            "last_result": {},
            "activity": [],
            "capabilities": {
                "feishu_entry": "ready",
                "feishu_doc_draft": "ready",
                "revision_loop": "ready",
                "notion_archive": "manual-finalize",
                "daily_ops_panel": "planned",
                "data_alerts": "basic-ready",
                "enterprise_wecom_entry": "deferred",
            },
            "release_plan": {
                "1.0": "飞书主入口 + 飞书草稿 + 定稿后归档",
                "1.1": "多轮修改闭环与定稿指令",
                "1.2": "待办、版本、能力现状与助手状态视图",
                "1.3": "反馈收集与周末迭代输入链路",
            },
        }

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def record_command(self, parsed: ParsedCommand) -> None:
        payload = self._read()
        payload["commands"] = (
            [
                {
                    "command_id": parsed.command_id,
                    "task_type": parsed.task_type,
                    "source": parsed.source,
                    "normalized_text": parsed.normalized_text,
                    "created_at": parsed.created_at,
                }
            ]
            + payload.get("commands", [])
        )[:50]
        self._write(payload)

    def record_document(self, document: dict[str, Any]) -> None:
        payload = self._read()
        docs = [doc for doc in payload.get("documents", []) if doc.get("document_id") != document.get("document_id")]
        docs.insert(0, document)
        payload["documents"] = docs[:50]
        self._write(payload)

    def append_revision(self, document_id: str, revision_text: str) -> int:
        payload = self._read()
        for doc in payload.get("documents", []):
            if doc.get("document_id") == document_id:
                revisions = doc.setdefault("revisions", [])
                revisions.append(
                    {
                        "index": len(revisions) + 1,
                        "text": revision_text,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                doc["status"] = "in_review"
                self._write(payload)
                return len(revisions)
        new_doc = {
            "document_id": document_id,
            "document_url": f"https://feishu.cn/docx/{document_id}",
            "title": f"未命名文档 {document_id}",
            "status": "in_review",
            "revisions": [
                {
                    "index": 1,
                    "text": revision_text,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            ],
        }
        payload["documents"] = [new_doc] + payload.get("documents", [])
        self._write(payload)
        return 1

    def mark_document_final(self, document_id: str) -> None:
        payload = self._read()
        for doc in payload.get("documents", []):
            if doc.get("document_id") == document_id:
                doc["status"] = "final"
                doc["finalized_at"] = datetime.now().isoformat(timespec="seconds")
                break
        self._write(payload)

    def record_todo(self, title: str, source: str, deadline_hint: str | None = None) -> dict[str, Any]:
        payload = self._read()
        item = {
            "id": f"todo-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "source": source,
            "deadline_hint": deadline_hint or "",
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        payload["todos"] = [item] + payload.get("todos", [])
        self._write(payload)
        return item

    def record_feedback(self, title: str, detail: str, source: str, category: str = "experience_issue") -> dict[str, Any]:
        payload = self._read()
        item = {
            "id": f"fb-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "detail": detail,
            "category": category,
            "source": source,
            "status": "new",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        payload["feedback"] = [item] + payload.get("feedback", [])
        self._write(payload)
        return item

    def record_alert(self, title: str, detail: str, source: str, severity: str = "medium") -> dict[str, Any]:
        payload = self._read()
        item = {
            "id": f"alert-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": title,
            "detail": detail,
            "source": source,
            "severity": severity,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        payload["alerts"] = [item] + payload.get("alerts", [])
        self._write(payload)
        return item

    def record_result(self, result: dict[str, Any]) -> None:
        payload = self._read()
        payload["last_result"] = result
        activity = payload.get("activity", [])
        activity.insert(
            0,
            {
                "created_at": result.get("created_at", ""),
                "summary": result.get("summary", ""),
                "lane": result.get("lane", ""),
                "action": result.get("action", ""),
                "task_type": result.get("task_type", ""),
                "doc_url": (result.get("doc_draft") or {}).get("url", ""),
                "wiki_path": (result.get("wiki_handoff") or {}).get("path", ""),
                "status": "done" if not result.get("errors") else "error",
            },
        )
        payload["activity"] = activity[:30]
        self._write(payload)

    def snapshot(self) -> dict[str, Any]:
        return self._read()
