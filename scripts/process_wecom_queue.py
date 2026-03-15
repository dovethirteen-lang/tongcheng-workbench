from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.command_service import CommandService


def main() -> None:
    parser = argparse.ArgumentParser(description="Process local WeCom bot inbox queue.")
    parser.add_argument("--text", help="Shortcut: submit one text command without creating inbox file manually.")
    parser.add_argument("--source", default="wecom_ai_bot")
    args = parser.parse_args()

    service = CommandService(BASE_DIR)
    if args.text:
        parsed, command_path, reply_path = service.accept_text(text=args.text, source=args.source)
        print(json.dumps(
            {
                "ok": True,
                "command_id": parsed.command_id,
                "command_file": str(command_path),
                "reply_file": str(reply_path),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return

    results = service.process_inbox()
    print(json.dumps({"ok": True, "processed": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
