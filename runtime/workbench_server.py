from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

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
            self._send_json(self.state.snapshot())
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
            if not text:
                self._send_json({"ok": False, "error": "text is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            result = self.pipeline.process_text(
                text=text,
                source=source,
                reply_target={"source": source},
                create_remote_artifacts=True,
            )
            self._send_json(
                {
                    "ok": True,
                    "command_id": result.parsed.command_id,
                    "summary": result.reply.get("summary", ""),
                    "reply_text": self.pipeline.command_service.format_reply_text(result.reply),
                    "doc_draft": result.reply.get("doc_draft"),
                    "revision_request": result.reply.get("revision_request"),
                    "notion_archive": result.reply.get("notion_archive"),
                    "wiki_handoff": result.reply.get("wiki_handoff"),
                    "warnings": result.reply.get("warnings", []),
                    "errors": result.reply.get("errors", []),
                    "todo_item": result.reply.get("todo_item"),
                    "feedback_item": result.reply.get("feedback_item"),
                    "alert_item": result.reply.get("alert_item"),
                    "state": self.state.snapshot(),
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
