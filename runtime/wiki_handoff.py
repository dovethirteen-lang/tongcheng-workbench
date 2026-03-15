from __future__ import annotations

from pathlib import Path

from .orchestrator import ParsedCommand


def create_wiki_handoff(parsed: ParsedCommand, reply: dict) -> Path:
    output_dir = Path(r"D:\Project\docs\wiki_handoff")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{parsed.command_id}.md"

    doc_draft = reply.get("doc_draft") or {}
    title = doc_draft.get("title") or f"{parsed.task_type} 发布中间稿"
    summary = reply.get("summary", "")
    next_actions = reply.get("next_actions", [])
    assumptions = reply.get("assumptions", [])

    content = f"""# {title}

## 摘要

{summary or "待补充摘要。"}

## 来源资料

""" + "\n".join(f"- {item}" for item in (parsed.inputs or ["待补充来源链接"])) + f"""

## 当前产出

- 任务类型：{parsed.task_type}
- 飞书草稿：{doc_draft.get('url', '待补充')}
- 截止时间：{parsed.deadline_hint or '未明确'}

## 下一步

""" + "\n".join(f"- {item}" for item in (next_actions or ["待补充下一步"])) + f"""

## 默认假设

""" + "\n".join(f"- {item}" for item in (assumptions or ["待补充默认假设"])) + """

## Wiki 发布检查

- 文案是否已定稿
- 图片是否补齐
- 表格是否需要拆分粘贴
- 链接是否替换为正式地址
"""

    path.write_text(content, encoding="utf-8")
    return path
