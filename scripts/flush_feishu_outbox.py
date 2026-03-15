from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.command_service import CommandService
from runtime.feishu_client import FeishuAPIError, FeishuConfigError, load_feishu_config, send_text_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Flush one Feishu reply from local outbox.")
    parser.add_argument("--file", type=Path, required=True, help="Path to outbox JSON file.")
    args = parser.parse_args()

    service = CommandService(BASE_DIR)
    reply = json.loads(args.file.read_text(encoding="utf-8"))
    target = reply.get("reply_target", {})
    open_id = target.get("sender_open_id")
    if not open_id:
        print("reply_target.sender_open_id is missing, cannot send to Feishu.")
        raise SystemExit(1)

    try:
        config = load_feishu_config(BASE_DIR)
        text = service.format_reply_text(reply)
        result = send_text_message(config=config, receive_id=open_id, text=text, receive_id_type="open_id")
    except (FeishuConfigError, FeishuAPIError) as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
