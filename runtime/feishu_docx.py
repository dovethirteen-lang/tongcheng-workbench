from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import lark_oapi as lark

from .feishu_client import load_feishu_config
from .orchestrator import ParsedCommand


class FeishuDocxError(RuntimeError):
    pass


DOCX_URL_RE = re.compile(r"https?://(?:[a-zA-Z0-9-]+\.)?feishu\.cn/docx/([A-Za-z0-9]+)")
REVISION_KEYWORDS = ["修改", "调整", "备注", "批注", "按我的备注", "修订", "优化一下", "补充一下"]


def _build_client(base_dir: Path) -> tuple[dict[str, Any], lark.Client]:
    config = load_feishu_config(base_dir)
    client = lark.Client.builder().app_id(config["app_id"]).app_secret(config["app_secret"]).build()
    return config, client


def _text_block(text: str, block_type: int = 2, field: str = "text") -> lark.docx.v1.Block:
    text_obj = (
        lark.docx.v1.Text.builder()
        .elements(
            [
                lark.docx.v1.TextElement.builder()
                .text_run(lark.docx.v1.TextRun.builder().content(text).build())
                .build()
            ]
        )
        .build()
    )
    builder = lark.docx.v1.Block.builder().block_type(block_type)
    return getattr(builder, field)(text_obj).build()


def _append_blocks(client: lark.Client, document_id: str, blocks: list[lark.docx.v1.Block]) -> None:
    append_request = (
        lark.docx.v1.CreateDocumentBlockChildrenRequest.builder()
        .document_id(document_id)
        .block_id(document_id)
        .client_token(str(uuid.uuid4()))
        .request_body(lark.docx.v1.CreateDocumentBlockChildrenRequestBody.builder().children(blocks).index(0).build())
        .build()
    )
    append_response = client.docx.v1.document_block_children.create(append_request)
    if append_response.code != 0:
        raise FeishuDocxError(f"Append blocks failed: code={append_response.code}, msg={append_response.msg}")


def extract_docx_url(text: str) -> str | None:
    match = DOCX_URL_RE.search(text)
    return match.group(0) if match else None


def extract_document_id(text: str) -> str | None:
    match = DOCX_URL_RE.search(text)
    return match.group(1) if match else None


def is_revision_request(parsed: ParsedCommand) -> bool:
    text = parsed.normalized_text
    if not extract_document_id(text):
        return False
    return any(keyword in text for keyword in REVISION_KEYWORDS)


def _build_title(parsed: ParsedCommand) -> str:
    base = parsed.normalized_text[:28].strip() or parsed.task_type
    return f"主控草稿｜{base}"


def should_create_doc_draft(parsed: ParsedCommand) -> bool:
    if is_revision_request(parsed):
        return False
    if parsed.task_type in {"wechat_growth", "platform_integration", "knowledge_archive"}:
        return True
    text = parsed.normalized_text
    return any(token in text for token in ["PRD", "prd", "文档", "评审稿", "方案", "飞书"])


def create_doc_draft(base_dir: Path, parsed: ParsedCommand, reply: dict[str, Any]) -> dict[str, Any]:
    config, client = _build_client(base_dir)
    folder_token = config.get("docx_folder_token") or None

    create_body_builder = lark.docx.v1.CreateDocumentRequestBody.builder().title(_build_title(parsed))
    if folder_token:
        create_body_builder = create_body_builder.folder_token(folder_token)

    create_request = lark.docx.v1.CreateDocumentRequest.builder().request_body(create_body_builder.build()).build()
    create_response = client.docx.v1.document.create(create_request)
    if create_response.code != 0 or not create_response.data or not create_response.data.document:
        raise FeishuDocxError(f"Create document failed: code={create_response.code}, msg={create_response.msg}")

    document = create_response.data.document
    document_id = document.document_id or ""
    if not document_id:
        raise FeishuDocxError("Create document succeeded but document_id is missing.")

    blocks = [
        _text_block(f"任务类型：{parsed.task_type}"),
        _text_block(f"任务摘要：{reply.get('summary', '')}"),
        _text_block("下一步：", block_type=3, field="heading2"),
    ]
    blocks.extend(_text_block(f"- {item}") for item in reply.get("next_actions", [])[:5])
    if reply.get("assumptions"):
        blocks.append(_text_block("默认假设：", block_type=3, field="heading2"))
        blocks.extend(_text_block(f"- {item}") for item in reply.get("assumptions", [])[:5])
    if parsed.inputs:
        blocks.append(_text_block("输入资料：", block_type=3, field="heading2"))
        blocks.extend(_text_block(f"- {item}") for item in parsed.inputs[:5])

    payload = {
        "document_id": document_id,
        "revision_id": document.revision_id,
        "title": document.title,
        "url": f"https://feishu.cn/docx/{document_id}",
        "status": "draft",
    }
    try:
        _append_blocks(client, document_id, blocks)
    except FeishuDocxError as exc:
        payload["warning"] = str(exc)
    return payload


def append_revision_request(base_dir: Path, parsed: ParsedCommand, revision_index: int) -> dict[str, Any]:
    _, client = _build_client(base_dir)
    document_id = extract_document_id(parsed.normalized_text)
    if not document_id:
        raise FeishuDocxError("Revision request is missing a Feishu docx link.")

    blocks = [
        _text_block(f"第 {revision_index} 轮修改需求", block_type=3, field="heading2"),
        _text_block(parsed.normalized_text),
    ]
    _append_blocks(client, document_id, blocks)
    return {
        "document_id": document_id,
        "document_url": f"https://feishu.cn/docx/{document_id}",
        "revision_index": revision_index,
        "status": "in_review",
    }
