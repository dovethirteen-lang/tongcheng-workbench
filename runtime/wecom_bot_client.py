from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .command_service import CommandService
from .orchestrator import load_router


class WecomBotConfigError(RuntimeError):
    pass


def load_bot_config(base_dir: Path) -> dict[str, Any]:
    config_path = base_dir / "config" / "wecom_bot.json"
    if not config_path.exists():
        raise WecomBotConfigError(
            f"Missing config file: {config_path}. Copy config/wecom_bot.sample.json to config/wecom_bot.json first."
        )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("bot_id", "").startswith("REPLACE_") or config.get("secret", "").startswith("REPLACE_"):
        raise WecomBotConfigError("Please fill bot_id and secret in config/wecom_bot.json before starting the client.")
    return config


def simulate_incoming_command(base_dir: Path, text: str, source: str = "wecom_ai_bot") -> Path:
    router = load_router(base_dir)
    parsed = router.parse_command(text=text, source=source)
    return router.dump_command(parsed, base_dir / "tmp" / "commands")


def run_long_connection_client(base_dir: Path, dry_run: bool = False, once: bool = False) -> None:
    config = load_bot_config(base_dir)
    service = CommandService(base_dir)
    print("WeCom AI Bot long-connection client starting...")
    print(f"Bot ID: {config['bot_id']}")
    print("Mode: long connection")

    if dry_run:
      print("Dry-run mode enabled. No network connection will be created.")
      parsed, command_path, reply_path = service.accept_text(
          "读取这个 Notion 链接 https://www.notion.so/demo ，这是当前 PRD。目标：迁移成飞书评审稿，今天17:00前通知我。",
          source="wecom_ai_bot",
      )
      print(f"Demo command parsed and saved to: {command_path}")
      print(f"Reply stub generated at: {reply_path}")
      print(f"Parsed route: {', '.join(parsed.route_to)}")
      return

    print("Official long-connection handshake is not wired yet.")
    print("Current stage: config verified, orchestrator ready, waiting for Bot SDK/protocol integration.")
    if once:
        return

    while True:
        time.sleep(5)
        processed = service.process_inbox()
        if processed:
            print(f"Processed {len(processed)} local inbox message(s).")
        else:
            print("Client idle: waiting for next integration step...")
