from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ParsedCommand:
    command_id: str
    source: str
    raw_text: str
    normalized_text: str
    route_to: list[str]
    task_type: str
    urgency: str
    inputs: list[str]
    outputs: list[str]
    deadline_hint: str | None
    notify_channel: str
    lane: str = "general"
    action: str = "general"
    assumptions: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class CommandRouter:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._config = json.loads(config_path.read_text(encoding="utf-8"))

    def parse_command(self, text: str, source: str = "feishu", hints: dict[str, Any] | None = None) -> ParsedCommand:
        normalized = re.sub(r"\s+", " ", text).strip()
        lowered = normalized.lower()
        hints = hints or {}
        matched_routes: list[dict[str, Any]] = []
        for rule in self._config.get("routing_rules", []):
          for keyword in rule.get("when", []):
              if keyword.lower() in lowered:
                  matched_routes.append(rule)
                  break

        task_type = self._infer_task_type(matched_routes)
        route_to = self._collect_routes(matched_routes)
        outputs = self._collect_outputs(matched_routes)
        lane = str(hints.get("lane") or task_type or "general")
        action = str(hints.get("action") or "general")
        task_type, route_to, outputs = self._apply_hints(lane, action, task_type, route_to, outputs)
        inputs = self._extract_inputs(normalized)
        deadline_hint = self._extract_deadline(normalized)
        urgency = self._infer_urgency(normalized, deadline_hint)

        if not route_to:
            route_to = [self._config.get("orchestrator", "Orchestrator / 主控 PM")]
        if not outputs:
            outputs = ["结构化任务说明", "下一步动作"]

        assumptions = self._build_assumptions(task_type, inputs, deadline_hint)
        next_actions = self._build_next_actions(task_type, route_to, outputs, deadline_hint)
        notify_channel = self._infer_notify_channel(source)

        return ParsedCommand(
            command_id=f"cmd-{uuid.uuid4().hex[:8]}",
            source=source,
            raw_text=text,
            normalized_text=normalized,
            route_to=route_to,
            task_type=task_type,
            urgency=urgency,
            inputs=inputs,
            outputs=outputs,
            deadline_hint=deadline_hint,
            notify_channel=notify_channel,
            lane=lane,
            action=action,
            assumptions=assumptions,
            next_actions=next_actions,
        )

    def dump_command(self, parsed: ParsedCommand, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{parsed.command_id}.json"
        path.write_text(json.dumps(asdict(parsed), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _infer_task_type(self, matched_routes: list[dict[str, Any]]) -> str:
        if not matched_routes:
            return "general"
        first_target = " ".join(matched_routes[0].get("route_to", []))
        if "实验设计" in first_target or "商业分析师" in first_target:
            return "ads_experiment"
        if "增长" in first_target:
            return "wechat_growth"
        if "平台产品" in first_target:
            return "platform_integration"
        if "Notion" in first_target:
            return "knowledge_archive"
        if "每日作战" in first_target:
            return "daily_ops"
        return "general"

    def _collect_routes(self, matched_routes: list[dict[str, Any]]) -> list[str]:
        seen: list[str] = []
        for rule in matched_routes:
            for route in rule.get("route_to", []):
                if route not in seen:
                    seen.append(route)
        return seen

    def _collect_outputs(self, matched_routes: list[dict[str, Any]]) -> list[str]:
        seen: list[str] = []
        for rule in matched_routes:
            for output in rule.get("outputs", []):
                if output not in seen:
                    seen.append(output)
        return seen

    def _apply_hints(
        self,
        lane: str,
        action: str,
        task_type: str,
        route_to: list[str],
        outputs: list[str],
    ) -> tuple[str, list[str], list[str]]:
        lane_task_map = {
            "wechat_growth": "wechat_growth",
            "ads_experiment": "ads_experiment",
            "platform_integration": "platform_integration",
            "daily_ops": "daily_ops",
            "general": "general",
        }
        task_type = lane_task_map.get(lane, task_type)

        if not route_to or lane != "general":
            route_to = {
                "wechat_growth": ["增长/C 端活动产品 Agent"],
                "ads_experiment": ["实验设计 Agent", "数据工程师 Agent", "商业分析师 Agent"],
                "platform_integration": ["平台产品 Agent"],
                "daily_ops": ["每日作战助手 Agent"],
                "general": ["Orchestrator / 主控 PM"],
            }.get(lane, route_to or ["Orchestrator / 主控 PM"])

        if action != "general":
            action_outputs = {
                "requirement_card": ["需求卡片", "待确认项", "依赖清单"],
                "prd_draft": ["PRD", "页面结构", "评审稿链接"],
                "analysis": ["分析结论", "下一步建议", "行动项"],
                "todo": ["待办记录", "deadline 提醒", "跟进项"],
                "feedback": ["反馈记录", "修复建议", "迭代输入"],
                "alert": ["异常告警", "排查动作", "风险提示"],
                "finalize": ["Notion 归档", "Wiki 中间稿", "发布准备"],
            }
            outputs = action_outputs.get(action, outputs or ["结构化任务说明", "下一步动作"])

        return task_type, route_to, outputs

    def _extract_inputs(self, text: str) -> list[str]:
        inputs: list[str] = []
        labeled_patterns = [
            r"资料位置[:：]\s*([^\r\n`]+)",
            r"聊天截图[:：]\s*([^\r\n`]+)",
        ]
        for pattern in labeled_patterns:
            for match in re.findall(pattern, text, flags=re.IGNORECASE):
                value = match.strip()
                if value and value not in inputs:
                    inputs.append(value)

        patterns = [
            r"https?://[^\s]+",
            r"[A-Za-z]:\\[^\r\n`]+",
            r"[A-Za-z]:\\[^\n]+\.(?:png|jpg|jpeg|webp|gif)",
            r"https?://[^\s]+\.(?:png|jpg|jpeg|webp|gif)",
            r"\bnotion\b",
            r"\bfeishu\b",
            r"\bpdf\b",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text, flags=re.IGNORECASE):
                value = match.strip()
                if value not in inputs:
                    inputs.append(value)
        return inputs

    def _extract_deadline(self, text: str) -> str | None:
        patterns = [
            r"(今天\s*\d{1,2}[:：]\d{2}前)",
            r"(今日\s*\d{1,2}[:：]\d{2}前)",
            r"(\d{1,2}[:：]\d{2}前)",
            r"(今天[上下]午\d{1,2}点前)",
            r"(\d{4}-\d{2}-\d{2}\s*\d{1,2}:\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _infer_urgency(self, text: str, deadline_hint: str | None) -> str:
        if deadline_hint:
            return "high"
        if any(token in text for token in ["尽快", "马上", "今天", "urgent", "立即"]):
            return "high"
        if any(token in text for token in ["本周", "这周", "周内"]):
            return "medium"
        return "normal"

    def _build_assumptions(self, task_type: str, inputs: list[str], deadline_hint: str | None) -> list[str]:
        assumptions: list[str] = []
        if not inputs:
            assumptions.append("当前命令未显式提供链接或目录，主控层需要用户补充资料位置。")
        if any(value.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")) for value in inputs):
            assumptions.append("当前任务包含截图或图片材料，主控层需要结合图片上下文与补充说明共同判断。")
        if task_type == "knowledge_archive":
            assumptions.append("默认将成品归档到 Notion，并保留来源链接和版本信息。")
        if task_type == "wechat_growth":
            assumptions.append("文档协作默认优先写回飞书云文档，便于在线批注。")
        if deadline_hint is None:
            assumptions.append("当前命令未提供明确截止时间，默认按正常优先级处理。")
        return assumptions

    def _build_next_actions(
        self, task_type: str, route_to: list[str], outputs: list[str], deadline_hint: str | None
    ) -> list[str]:
        actions = [
            "主控层先读取资料并生成结构化任务摘要。",
            f"根据任务类型分发给：{', '.join(route_to) if route_to else 'Orchestrator / 主控 PM'}。",
            f"预期产出：{', '.join(outputs)}。",
        ]
        if task_type == "ads_experiment":
            actions.append("如涉及本地数据目录，先校验文件结构和字段完整性。")
        if task_type in {"wechat_growth", "platform_integration"}:
            actions.append("如需协作评审，先生成飞书云文档草稿再通知用户。")
        if deadline_hint:
            actions.append(f"在 {deadline_hint} 前通过当前消息入口回传处理结果或阶段进度。")
        else:
            actions.append("处理完成后通过当前消息入口回传链接、摘要和待确认点。")
        return actions

    def _infer_notify_channel(self, source: str) -> str:
        lowered = source.lower()
        if "feishu" in lowered:
            return "飞书"
        if "wecom" in lowered:
            return "企业微信"
        return "当前消息入口"


def load_router(base_dir: Path) -> CommandRouter:
    return CommandRouter(base_dir / "config" / "agent_router.json")
