from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.command_service import CommandService
from runtime.feishu_docx import create_doc_draft


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Feishu doc draft from a command log.")
    parser.add_argument("--command-file", type=Path, required=True)
    parser.add_argument("--reply-file", type=Path, required=True)
    args = parser.parse_args()

    service = CommandService(BASE_DIR)
    parsed_payload = json.loads(args.command_file.read_text(encoding="utf-8"))
    reply = json.loads(args.reply_file.read_text(encoding="utf-8"))
    parsed = service.router.parse_command(parsed_payload["raw_text"], source=parsed_payload.get("source", "feishu"))
    parsed.command_id = parsed_payload.get("command_id", parsed.command_id)
    result = create_doc_draft(BASE_DIR, parsed, reply)
    reply["doc_draft"] = result
    service.save_reply(args.reply_file, reply)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
