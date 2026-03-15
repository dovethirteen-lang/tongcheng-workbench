from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.command_service import CommandService
from runtime.feishu_docx import is_revision_request, should_create_doc_draft
from runtime.notion_archive import should_archive_to_notion


def main() -> None:
    service = CommandService(BASE_DIR)

    draft_command, _, draft_reply_path = service.accept_text(
        text="读取这个 Notion 链接，先整理成需求卡片草稿，不要归档。",
        source="feishu_longconn",
    )
    revision_command, _, revision_reply_path = service.accept_text(
        text="按照我的备注修改这个飞书文档 https://feishu.cn/docx/AbCdEf123456，补充缺失的图和规则说明。",
        source="feishu_longconn",
    )
    final_command, _, final_reply_path = service.accept_text(
        text="这个 PRD 已经定稿，归档到 Notion，并准备发布到 Wiki。",
        source="feishu_longconn",
    )

    draft_reply = service.read_reply(draft_reply_path)
    revision_reply = service.read_reply(revision_reply_path)
    final_reply = service.read_reply(final_reply_path)

    result = {
        "ok": True,
        "draft_stage": {
            "notify_channel": draft_command.notify_channel,
            "should_create_doc_draft": should_create_doc_draft(draft_command),
            "should_archive_to_notion": should_archive_to_notion(draft_command),
            "reply_title": draft_reply.get("title"),
        },
        "revision_stage": {
            "is_revision_request": is_revision_request(revision_command),
            "should_create_doc_draft": should_create_doc_draft(revision_command),
            "should_archive_to_notion": should_archive_to_notion(revision_command),
            "reply_title": revision_reply.get("title"),
        },
        "final_stage": {
            "notify_channel": final_command.notify_channel,
            "should_create_doc_draft": should_create_doc_draft(final_command),
            "should_archive_to_notion": should_archive_to_notion(final_command),
            "reply_title": final_reply.get("title"),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
