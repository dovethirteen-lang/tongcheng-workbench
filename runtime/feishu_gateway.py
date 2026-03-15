from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .command_service import CommandService


class FeishuGatewayHandler(BaseHTTPRequestHandler):
    server_version = "TongchengFeishuGateway/0.2"

    def _json_response(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json_response(
                {
                    "ok": True,
                    "service": "feishu_command_gateway",
                    "mode": "local-dev",
                    "message": "Gateway is running. 飞书正式事件订阅和长连接都可接入当前主控内核。",
                }
            )
            return
        self._json_response({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"ok": False, "error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            return

        if self.path == "/feishu/event":
            if payload.get("type") == "url_verification":
                self._json_response({"challenge": payload.get("challenge", "")})
                return

            event = payload.get("event", {})
            sender = event.get("sender", {}).get("sender_id", {})
            message = event.get("message", {})
            text = ""
            content = message.get("content")
            if isinstance(content, str):
                try:
                    decoded = json.loads(content)
                    text = str(decoded.get("text", "")).strip()
                except json.JSONDecodeError:
                    text = content.strip()

            service = self.server.command_service  # type: ignore[attr-defined]
            inbox_payload = {
                "message_id": message.get("message_id"),
                "source": "feishu",
                "sender_open_id": sender.get("open_id"),
                "chat_id": message.get("chat_id"),
                "text": text,
                "raw": payload,
            }
            inbox_path = service.enqueue_incoming(inbox_payload)
            results = service.process_inbox()
            self._json_response({"ok": True, "saved_to": str(inbox_path), "processed": results})
            return

        if self.path == "/feishu/mock":
            text = str(payload.get("text", "")).strip()
            if not text:
                self._json_response({"ok": False, "error": "Field 'text' is required"}, status=HTTPStatus.BAD_REQUEST)
                return
            service = self.server.command_service  # type: ignore[attr-defined]
            reply_target = {
                "sender_open_id": str(payload.get("sender_open_id", "") or ""),
                "chat_id": str(payload.get("chat_id", "") or ""),
                "source": "feishu",
            }
            parsed, command_path, reply_path = service.accept_text(
                text=text,
                source="feishu",
                reply_target=reply_target,
            )
            self._json_response(
                {
                    "ok": True,
                    "command_id": parsed.command_id,
                    "command_file": str(command_path),
                    "reply_file": str(reply_path),
                }
            )
            return

        self._json_response({"ok": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)


class FeishuGatewayServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], base_dir: Path) -> None:
        super().__init__(server_address, FeishuGatewayHandler)
        self.base_dir = base_dir
        self.command_service = CommandService(base_dir)


def run_server(base_dir: Path, host: str, port: int) -> None:
    server = FeishuGatewayServer((host, port), base_dir)
    print(f"Feishu gateway listening on http://{host}:{port}")
    print("Available endpoints: GET /health, POST /feishu/event, POST /feishu/mock")
    server.serve_forever()
