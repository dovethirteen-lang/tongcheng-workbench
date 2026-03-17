from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .lobster_bridge import discover_lobster_tasks
from .task_pipeline import TaskPipeline
from .workbench_state import WorkbenchState


class WorkbenchRequestHandler(SimpleHTTPRequestHandler):
    server_version = "TongchengWorkbench/1.0"

    def __init__(self, *args, base_dir: Path, site_dir: Path, **kwargs) -> None:
        self.base_dir = base_dir
        self.site_dir = site_dir
        self.pipeline = TaskPipeline(base_dir)
        self.state = WorkbenchState()
        super().__init__(*args, directory=str(site_dir), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "mode": "local-api"})
            return
        if parsed.path == "/api/state":
            self._send_json(self._build_state_payload())
            return
        if parsed.path == "/api/lobster/tasks":
            self._send_json({"tasks": discover_lobster_tasks()})
            return
        if parsed.path == "/api/templates":
            self._send_json(
                {
                    "new_card": [
                        "读取这个 Notion / 飞书文档链接，先整理成需求卡片草稿，不要归档。",
                        "请输出：背景、目标、用户路径、规则、风险、待确认项。",
                        "完成后把飞书文档链接回给我。",
                    ],
                    "new_prd": [
                        "按照这个需求卡片生成 PRD 草稿，不要归档。",
                        "PRD 结构按我的 Notion 模板来写。",
                        "生成到飞书文档，完成后把链接回给我。",
                    ],
                    "record_alert": [
                        "记录一条数据告警。",
                        "请写清：异常指标、波动情况、初步判断、下一步排查动作。",
                    ],
                    "new_todo": [
                        "登记一条新的待办。",
                        "如果来源是企业微信聊天记录，请把聊天截图一起带上。",
                        "请写清：事项、截止时间、当前阻塞点、需要我回传的结果。",
                    ],
                    "new_feedback": [
                        "记录一条工作台反馈。",
                        "请说明：问题现象、复现方式、期望结果、优先级。",
                    ],
                }
            )
            return
        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/command":
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(body)
            text = str(payload.get("text", "")).strip()
            source = str(payload.get("source", "workbench_frontend"))
            intent = str(payload.get("intent", "") or "").strip() or None
            lane = str(payload.get("lane", "") or "").strip() or None
            action = str(payload.get("action", "") or "").strip() or None
            if not text:
                self._send_json({"ok": False, "error": "text is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = self.pipeline.process_text(
                text=text,
                source=source,
                reply_target={"source": source},
                create_remote_artifacts=True,
                intent=intent,
                lane=lane,
                action=action,
            )
            self._send_json(
                {
                    "ok": True,
                    "intent": intent,
                    "lane": lane,
                    "action": action,
                    "command_id": result.parsed.command_id,
                    "summary": result.reply.get("summary", ""),
                    "materials": result.reply.get("materials", []),
                    "reply_text": self.pipeline.command_service.format_reply_text(result.reply),
                    "doc_draft": result.reply.get("doc_draft"),
                    "revision_request": result.reply.get("revision_request"),
                    "notion_archive": result.reply.get("notion_archive"),
                    "wiki_handoff": result.reply.get("wiki_handoff"),
                    "warnings": result.reply.get("warnings", []),
                    "errors": result.reply.get("errors", []),
                    "todo_item": result.reply.get("todo_item"),
                    "feedback_item": result.reply.get("feedback_item"),
                    "feedback_queue": result.reply.get("feedback_queue"),
                    "alert_item": result.reply.get("alert_item"),
                    "alert_queue": result.reply.get("alert_queue"),
                    "todo_queue": result.reply.get("todo_queue"),
                    "state": self._build_state_payload(),
                }
            )
            return

        self._send_json({"ok": False, "error": "unsupported endpoint"}, status=HTTPStatus.NOT_FOUND)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _build_state_payload(self) -> dict:
        state = self.state.snapshot()
        notion_config = json.loads((self.base_dir / "config" / "notion_workspace.json").read_text(encoding="utf-8"))
        feishu_config = json.loads((self.base_dir / "config" / "feishu_app.json").read_text(encoding="utf-8"))
        state["notion_config"] = {
            "workspace_name": notion_config.get("workspace_name", ""),
            "workspace_url": notion_config.get("workspace_url", ""),
            "private_library_url": notion_config.get("private_library_url", ""),
            "prd_template_url": notion_config.get("prd_template_url", ""),
            "todo_strategy": notion_config.get("todo_strategy", {}),
            "feedback_strategy": notion_config.get("feedback_strategy", {}),
            "routing_map": notion_config.get("routing_map", {}),
        }
        state["feishu_config"] = {
            "document_channel": feishu_config.get("document_channel", ""),
            "document_strategy": feishu_config.get("document_strategy", {}),
        }
        state["workflow_instances"] = state.get("workflow_instances", [])[:12]
        state["lobster_tasks"] = discover_lobster_tasks()[:12]
        return state


def run_workbench_server(base_dir: Path, host: str = "127.0.0.1", port: int = 4390) -> None:
    site_dir = base_dir / "site" / "feishu-workbench"
    site_dir.mkdir(parents=True, exist_ok=True)

    def handler(*args, **kwargs):
        return WorkbenchRequestHandler(*args, base_dir=base_dir, site_dir=site_dir, **kwargs)

    server = ThreadingHTTPServer((host, port), handler)
    print(f"Workbench server running at http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    run_workbench_server(Path(__file__).resolve().parents[1])
