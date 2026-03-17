from __future__ import annotations

import json
import re
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
from .lobster_bridge import discover_lobster_tasks


TODO_KEYWORDS = ["待办", "todo", "提醒", "deadline", "排期", "跟进"]
FEEDBACK_KEYWORDS = ["反馈", "bug", "问题", "优化建议", "迭代", "不好用"]
ALERT_KEYWORDS = ["告警", "异常", "波动", "下降", "暴跌", "预警", "监控"]
PROTOTYPE_SPEC_PATH = (
    r"D:\Docspace\Desktop\Product prototype html(1)\Product prototype html\【规范】HTML原型文件出图要求.md"
)
H2D_REFERENCE_PATH = (
    r"D:\CodeX\Database\Product prototype html(1)\_D_Docspace_Desktop_Product_20prototype_20html_1_Product_20prototype_20html_buchong2_1912w_default.h2d"
)


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
        workflow_instance = self._build_workflow_instance(parsed, reply)
        self.state.upsert_workflow_instance(workflow_instance)

        if create_remote_artifacts and should_create_doc_draft(parsed):
            try:
                doc_draft = create_doc_draft(self.base_dir, parsed, reply)
                reply["doc_draft"] = doc_draft
                reply["feishu_doc"] = doc_draft
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
                workflow_instance = self._build_workflow_instance(parsed, reply)
                self.state.upsert_workflow_instance(workflow_instance)
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
        elif parsed.task_type == "daily_ops" and parsed.action == "analysis" and not reply.get("doc_draft"):
            reply.setdefault("warnings", []).append("日常简报尚未生成飞书草稿，请检查飞书文档权限或配置。")

        if create_remote_artifacts and is_revision_request(parsed):
            document_id = extract_document_id(parsed.normalized_text)
            if document_id:
                try:
                    revision_index = self.state.append_revision(document_id, parsed.normalized_text)
                    reply["revision_request"] = append_revision_request(self.base_dir, parsed, revision_index)
                    workflow_instance = self._build_workflow_instance(parsed, reply)
                    self.state.upsert_workflow_instance(workflow_instance)
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
            workflow_instance = self._build_workflow_instance(parsed, reply)
            self.state.upsert_workflow_instance(workflow_instance)
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

        reply["workflow_instance"] = workflow_instance
        reply["normalized_source"] = workflow_instance.get("normalized_source")
        reply["local_artifacts"] = workflow_instance.get("local_artifacts")
        reply["prototype_package"] = workflow_instance.get("prototype_package")
        reply["prototype_task"] = workflow_instance.get("prototype_task")
        reply["prototype_spec_path"] = workflow_instance.get("prototype_spec_path")
        reply["h2d_reference_path"] = workflow_instance.get("h2d_reference_path")
        reply["rendered_assets"] = workflow_instance.get("rendered_assets")
        reply["experiment_payload"] = workflow_instance.get("experiment_payload")
        reply["experiment_result"] = workflow_instance.get("experiment_result")
        reply["executor"] = workflow_instance.get("executor")
        reply["priority_quadrant"] = workflow_instance.get("priority_quadrant")
        reply["run_status"] = workflow_instance.get("run_status")
        reply["trigger_source"] = workflow_instance.get("trigger_source")
        reply["lobster_task_name"] = workflow_instance.get("lobster_task_name")
        reply["latest_output"] = workflow_instance.get("latest_output")
        reply["error_summary"] = workflow_instance.get("error_summary")
        reply["next_action"] = workflow_instance.get("next_action")
        reply["needs_human_confirm"] = workflow_instance.get("needs_human_confirm")
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
                "normalized_source": workflow_instance.get("normalized_source"),
                "local_artifacts": workflow_instance.get("local_artifacts"),
                "prototype_package": workflow_instance.get("prototype_package"),
                "prototype_task": workflow_instance.get("prototype_task"),
                "rendered_assets": workflow_instance.get("rendered_assets"),
                "experiment_payload": workflow_instance.get("experiment_payload"),
                "experiment_result": workflow_instance.get("experiment_result"),
                "executor": workflow_instance.get("executor"),
                "priority_quadrant": workflow_instance.get("priority_quadrant"),
                "run_status": workflow_instance.get("run_status"),
                "trigger_source": workflow_instance.get("trigger_source"),
                "lobster_task_name": workflow_instance.get("lobster_task_name"),
                "latest_output": workflow_instance.get("latest_output"),
                "error_summary": workflow_instance.get("error_summary"),
                "feishu_doc": reply.get("feishu_doc") or reply.get("doc_draft"),
                "workflow_instance": workflow_instance,
                "next_action": workflow_instance.get("next_action"),
                "needs_human_confirm": workflow_instance.get("needs_human_confirm"),
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

    def _build_workflow_instance(self, parsed: ParsedCommand, reply: dict[str, Any]) -> dict[str, Any]:
        entry_type = self._infer_entry_type(parsed)
        artifact_type = self._infer_artifact_type(parsed)
        executor = self._select_executor(parsed, artifact_type)
        priority_quadrant = self._infer_priority_quadrant(parsed, artifact_type, executor)
        local_artifacts = self._build_local_artifacts(parsed)
        rendered_assets = self._build_rendered_assets(parsed)
        prototype_package = self._build_prototype_package(parsed, local_artifacts)
        prototype_task = self._build_prototype_task(parsed, prototype_package, local_artifacts)
        experiment_payload = self._extract_experiment_payload(parsed, local_artifacts)
        experiment_result = self._build_experiment_result(parsed, reply, experiment_payload)
        feishu_doc = reply.get("feishu_doc") or reply.get("doc_draft")

        workflow_stage = "created"
        local_exec_status = "pending"
        feishu_doc_status = "none"
        archive_status = "idle"
        needs_human_confirm = bool(reply.get("revision_request"))
        run_status = "queued" if executor == "lobster" else "running"
        trigger_source = "feishu_openclaw" if "openclaw" in parsed.source.lower() else parsed.source
        lobster_task_name, latest_output = self._match_lobster_task(parsed)
        if executor == "lobster" and not lobster_task_name:
            lobster_tasks = discover_lobster_tasks()
            if lobster_tasks:
                lobster_task_name = str(lobster_tasks[0].get("name", ""))
                latest_outputs = lobster_tasks[0].get("latest_outputs") or []
                latest_output = latest_outputs[0] if latest_outputs else ""
        error_summary = (reply.get("errors") or [""])[0]

        if executor in {"codex", "lobster"}:
            workflow_stage = "routed"
            local_exec_status = "running"

        if local_artifacts or rendered_assets or prototype_package or experiment_result:
            workflow_stage = "running"
            local_exec_status = "done"
            run_status = "success" if executor == "lobster" else run_status

        if feishu_doc or reply.get("revision_request"):
            workflow_stage = "waiting_human"
            feishu_doc_status = "draft"
            needs_human_confirm = True

        if reply.get("revision_request"):
            workflow_stage = "waiting_human"
            feishu_doc_status = "revising"
            needs_human_confirm = True

        if reply.get("notion_archive"):
            workflow_stage = "archived"
            archive_status = "archived"
            feishu_doc_status = "finalized" if feishu_doc else feishu_doc_status
            needs_human_confirm = False
        elif parsed.action == "finalize":
            workflow_stage = "archive_ready"
            archive_status = "ready"
            feishu_doc_status = "finalized" if feishu_doc else feishu_doc_status

        if workflow_stage in {"running", "routed"} and not needs_human_confirm and not reply.get("errors"):
            workflow_stage = "completed"

        if reply.get("errors"):
            workflow_stage = "failed"
            local_exec_status = "failed"
            run_status = "failed" if executor == "lobster" else run_status

        if workflow_stage in {"completed", "archive_ready", "archived"} and executor == "lobster" and run_status != "failed":
            run_status = "success"

        return {
            "workflow_id": parsed.command_id,
            "entry_type": entry_type,
            "lane": parsed.lane,
            "task_type": parsed.task_type,
            "artifact_type": artifact_type,
            "executor": executor,
            "priority_quadrant": priority_quadrant,
            "workflow_stage": workflow_stage,
            "feishu_doc_status": feishu_doc_status,
            "local_exec_status": local_exec_status,
            "archive_status": archive_status,
            "trigger_source": trigger_source,
            "lobster_task_name": lobster_task_name,
            "run_status": run_status if executor == "lobster" else "none",
            "latest_output": latest_output,
            "error_summary": error_summary,
            "normalized_source": {
                "source": parsed.source,
                "materials": parsed.inputs,
                "deadline_hint": parsed.deadline_hint,
            },
            "local_artifacts": local_artifacts,
            "prototype_package": prototype_package,
            "prototype_spec_path": PROTOTYPE_SPEC_PATH,
            "h2d_reference_path": H2D_REFERENCE_PATH,
            "prototype_task": prototype_task,
            "rendered_assets": rendered_assets,
            "experiment_payload": experiment_payload,
            "experiment_result": experiment_result,
            "feishu_doc": feishu_doc,
            "next_action": self._infer_next_action(workflow_stage, artifact_type),
            "needs_human_confirm": needs_human_confirm,
            "created_at": parsed.created_at,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _infer_entry_type(self, parsed: ParsedCommand) -> str:
        has_link = any(item.startswith("http://") or item.startswith("https://") for item in parsed.inputs)
        has_local = any(":\\" in item for item in parsed.inputs)
        has_image = any(item.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")) for item in parsed.inputs)

        types: list[str] = []
        if parsed.source.startswith("feishu"):
            types.append("bot_command")
        if has_link:
            types.append("link")
        if has_local:
            types.append("local_path")
        if has_image:
            types.append("screenshot")

        if len(types) > 1:
            return "mixed"
        if types:
            return types[0]
        return "bot_command"

    def _infer_artifact_type(self, parsed: ParsedCommand) -> str:
        mapping = {
            "requirement_card": "requirement_card",
            "prd_draft": "prd",
            "analysis": "analysis",
            "todo": "todo",
            "feedback": "todo",
            "alert": "alert",
            "finalize": "prd",
        }
        artifact_type = mapping.get(parsed.action, "analysis" if parsed.task_type == "daily_ops" else "requirement_card")
        if self._is_prototype_request(parsed):
            return "prototype_package"
        return artifact_type

    def _select_executor(self, parsed: ParsedCommand, artifact_type: str) -> str:
        text = parsed.normalized_text.lower()
        if any(token in text for token in ["日报", "周报", "定时", "schedule", "监控", "lobster"]):
            return "lobster"
        if parsed.lane == "ads_experiment":
            return "codex"
        if artifact_type in {"prd", "prototype_package", "requirement_card"}:
            return "codex"
        if parsed.lane == "daily_ops" and parsed.action in {"todo", "feedback"}:
            return "openclaw"
        if "openclaw" in parsed.source.lower():
            return "openclaw"
        return "codex"

    def _infer_priority_quadrant(self, parsed: ParsedCommand, artifact_type: str, executor: str) -> str:
        urgent_tokens = ["紧急", "马上", "立即", "asap", "today", "今天", "告警", "异常"]
        urgent = parsed.urgency == "high" or any(token in parsed.normalized_text.lower() for token in urgent_tokens)
        important = parsed.lane in {"ads_experiment", "wechat_growth", "platform_integration"} or artifact_type in {
            "prd",
            "analysis",
            "alert",
        }
        if executor == "lobster":
            important = True
        if parsed.lane == "daily_ops" and any(token in parsed.normalized_text for token in ["日报", "周报", "监控"]):
            important = True
        if important and urgent:
            return "Q1_important_urgent"
        if important and not urgent:
            return "Q2_important_not_urgent"
        if not important and urgent:
            return "Q3_not_important_urgent"
        return "Q4_not_important_not_urgent"

    def _build_local_artifacts(self, parsed: ParsedCommand) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for item in parsed.inputs:
            if ":\\" in item:
                artifacts.append({"kind": "local_path", "path": item})
            elif item.startswith("http://") or item.startswith("https://"):
                artifacts.append({"kind": "remote_link", "path": item})
        return artifacts

    def _build_rendered_assets(self, parsed: ParsedCommand) -> list[dict[str, Any]]:
        return [
            {"kind": "image", "path": item}
            for item in parsed.inputs
            if item.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))
        ]

    def _build_prototype_package(self, parsed: ParsedCommand, local_artifacts: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not self._is_prototype_request(parsed):
            return None

        preferred_path = ""
        for item in local_artifacts:
            path = str(item.get("path", ""))
            if path.lower().endswith((".html", ".htm", ".tsx", ".jsx", ".js")):
                preferred_path = path
                break

        return {
            "name": f"{parsed.command_id}-prototype",
            "status": "ready_for_local_exec",
            "path": preferred_path or str(Path(r"D:\Project\docs") / "prototype_packages" / parsed.command_id),
        }

    def _build_prototype_task(
        self,
        parsed: ParsedCommand,
        prototype_package: dict[str, Any] | None,
        local_artifacts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not self._is_prototype_request(parsed):
            return None
        text = parsed.normalized_text.lower()
        source_link = next((item for item in parsed.inputs if item.startswith("http")), "")
        h2d_path = next(
            (item.get("path", "") for item in local_artifacts if str(item.get("path", "")).lower().endswith(".h2d")),
            "",
        )
        round_match = re.search(r"(第\s*\d+\s*轮|round\s*\d+)", text, flags=re.IGNORECASE)
        needs_figma_refine = "yes" if any(token in text for token in ["figma", "精修", "待优化"]) else "no"
        return {
            "source_link": source_link,
            "prompt": parsed.normalized_text[:300],
            "prototype_path": (prototype_package or {}).get("path", ""),
            "preview_status": "ready" if prototype_package else "pending",
            "design_round": round_match.group(1) if round_match else "第1轮",
            "needs_figma_refine": needs_figma_refine,
            "h2d_status": "ready" if h2d_path else "deferred",
            "h2d_path": h2d_path or H2D_REFERENCE_PATH,
            "figma_import_status": "pending" if needs_figma_refine == "yes" else "deferred",
        }

    def _extract_experiment_payload(
        self, parsed: ParsedCommand, local_artifacts: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        if parsed.lane != "ads_experiment":
            return None
        text = parsed.normalized_text
        experiment_name = self._extract_labeled_field(text, ["实验名称", "实验名", "experiment_name"])
        if not experiment_name:
            experiment_name = text[:36]
        experiment_spec_link = self._extract_labeled_field(text, ["实验方案", "方案链接", "experiment_spec_link"])
        if not experiment_spec_link:
            experiment_spec_link = next((item for item in parsed.inputs if item.startswith("http")), "")
        sql_reference = self._extract_labeled_field(text, ["sql参考", "sql", "sql_reference"])
        if not sql_reference:
            sql_reference = next(
                (
                    item.get("path", "")
                    for item in local_artifacts
                    if str(item.get("path", "")).lower().endswith((".sql", ".csv", ".xlsx"))
                ),
                "",
            )
        metric_definition = self._extract_labeled_field(text, ["指标口径", "口径", "metric_definition"])
        result_file_path = self._extract_labeled_field(text, ["结果路径", "结果文件", "result_file_path"])
        if not result_file_path:
            result_file_path = next(
                (
                    item.get("path", "")
                    for item in local_artifacts
                    if str(item.get("path", "")).lower().endswith((".csv", ".xlsx", ".json", ".parquet"))
                ),
                "",
            )
        return {
            "experiment_name": experiment_name,
            "experiment_spec_link": experiment_spec_link,
            "sql_reference": sql_reference,
            "metric_definition": metric_definition,
            "deadline": parsed.deadline_hint or "",
            "result_file_path": result_file_path,
        }

    def _build_experiment_result(
        self, parsed: ParsedCommand, reply: dict[str, Any], experiment_payload: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not experiment_payload:
            return None
        metric_definition = experiment_payload.get("metric_definition", "")
        key_metrics = [item.strip() for item in re.split(r"[，,;；\|/]", metric_definition) if item.strip()][:6]
        pending: list[str] = []
        if not experiment_payload.get("sql_reference"):
            pending.append("补充 SQL 参考或可执行脚本路径")
        if not experiment_payload.get("metric_definition"):
            pending.append("补充实验指标口径定义")
        if not experiment_payload.get("result_file_path"):
            pending.append("补充结果文件路径（CSV/XLSX）")
        if not experiment_payload.get("deadline"):
            pending.append("补充回收截止时间")
        return {
            "analysis_summary": reply.get("summary", ""),
            "key_metrics": key_metrics,
            "confidence_note": "当前为1.0自动分析结果，请在定稿前确认样本量、口径一致性与异常点解释。",
            "next_actions": parsed.next_actions[:4],
            "pending_confirmations": pending,
        }

    def _extract_labeled_field(self, text: str, labels: list[str]) -> str:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]\s*([^\r\n]+)"
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _is_prototype_request(self, parsed: ParsedCommand) -> bool:
        text = parsed.normalized_text.lower()
        return any(token in text for token in ["prototype", "react", "html", "原型", "线框", "htm to design"])

    def _infer_next_action(self, workflow_stage: str, artifact_type: str) -> str:
        if workflow_stage == "routed":
            return "start_execution"
        if workflow_stage == "running":
            return "wait_for_execution_result"
        if workflow_stage == "waiting_human":
            return "wait_for_human_comments"
        if workflow_stage == "completed":
            return "ready_for_review"
        if workflow_stage == "archive_ready":
            return "ready_for_archive"
        if workflow_stage == "archived":
            return "archived"
        if workflow_stage == "failed":
            return "check_error_and_retry"
        if artifact_type == "todo":
            return "wait_for_follow_up"
        return "prepare_local_execution"

    def _match_lobster_task(self, parsed: ParsedCommand) -> tuple[str, str]:
        text = parsed.normalized_text.lower()
        tasks = discover_lobster_tasks()
        for task in tasks:
            name = str(task.get("name", ""))
            name_lower = name.lower()
            name_tokens = [token for token in re.split(r"[^0-9a-z\u4e00-\u9fff]+", name_lower) if len(token) >= 2]
            if name and (name_lower in text or text in name_lower or any(token in text for token in name_tokens)):
                latest_outputs = task.get("latest_outputs") or []
                latest_output = latest_outputs[0] if latest_outputs else ""
                return name, latest_output
        if "lobster" in text and tasks:
            fallback = tasks[0]
            latest_outputs = fallback.get("latest_outputs") or []
            latest_output = latest_outputs[0] if latest_outputs else ""
            return str(fallback.get("name", "")), latest_output
        return "", ""

    def _write_runtime_log(self, payload: dict[str, Any]) -> None:
        path = self.runtime_root / "events.log"
        entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), **payload}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
