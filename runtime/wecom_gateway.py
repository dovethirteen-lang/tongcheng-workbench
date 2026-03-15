from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .orchestrator import load_router


class WecomGatewayHandler(BaseHTTPRequestHandler):
    server_version = "TongchengWecomGateway/0.1"

    def _json_response(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json_response(
                {
                    "ok": True,
                    "service": "wecom_command_gateway",
                    "mode": "local-dev",
                    "message": "Gateway is running. 企业微信正式回调仍需补企业应用配置与验签。",
                }
            )
            return
        if parsed.path == "/wecom/verify":
            query = parse_qs(parsed.query)
            self._json_response(
                {
                    "ok": True,
                    "message": "第一版仅提供本地验证占位，正式企业微信 GET 验证待接入。",
                    "query": query,
                }
            )
            return
        self._json_response({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in {"/command", "/wecom/mock"}:
            self._json_response({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"ok": False, "error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        text = str(payload.get("text", "")).strip()
        source = str(payload.get("source", "wecom"))
        if not text:
            self._json_response({"ok": False, "error": "Field 'text' is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        router = self.server.router  # type: ignore[attr-defined]
        parsed_command = router.parse_command(text=text, source=source)
        output_dir = self.server.command_log_dir  # type: ignore[attr-defined]
        saved_path = router.dump_command(parsed_command, output_dir)
        self._json_response(
            {
                "ok": True,
                "message": "Command accepted by orchestrator.",
                "saved_to": str(saved_path),
                "command": asdict(parsed_command),
            }
        )


class WecomGatewayServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], base_dir: Path) -> None:
        super().__init__(server_address, WecomGatewayHandler)
        self.base_dir = base_dir
        self.router = load_router(base_dir)
        self.command_log_dir = base_dir / "tmp" / "commands"


def run_server(base_dir: Path, host: str, port: int) -> None:
    server = WecomGatewayServer((host, port), base_dir)
    print(f"WeCom gateway listening on http://{host}:{port}")
    print("Available endpoints: GET /health, POST /command, POST /wecom/mock")
    server.serve_forever()

