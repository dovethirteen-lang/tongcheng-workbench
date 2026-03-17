from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOBSTER_WORKFLOW_DIR = Path(r"D:\CodeX\lobster-workflow")
LOBSTER_DATA_DIR = Path(r"D:\CodeX\lobster-data")


@dataclass
class LobsterTask:
    name: str
    description: str
    schedule_type: str
    schedule_expression: str
    working_directory: str
    notify_platforms: list[str]
    source_file: str
    data_dir: str
    output_dir: str
    latest_outputs: list[str]
    lane: str
    artifact_type: str
    executor: str = "lobster"
    status: str = "scheduled"


def discover_lobster_tasks() -> list[dict[str, Any]]:
    if not LOBSTER_WORKFLOW_DIR.exists():
        return []

    deduped: dict[str, tuple[float, LobsterTask]] = {}
    for path in sorted(LOBSTER_WORKFLOW_DIR.glob("*.json")):
        payload = _safe_load_json(path)
        if not payload or not payload.get("name") or not payload.get("schedule"):
            continue

        task = _build_task(path, payload)
        if not task:
            continue

        current = deduped.get(task.name)
        mtime = path.stat().st_mtime
        if current is None or mtime >= current[0]:
            deduped[task.name] = (mtime, task)

    return [task.__dict__ for _, task in sorted(deduped.values(), key=lambda item: item[1].name)]


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _build_task(path: Path, payload: dict[str, Any]) -> LobsterTask | None:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    schedule = payload.get("schedule") or {}
    schedule_type = str(schedule.get("type", "cron")).strip() or "cron"
    schedule_expression = str(schedule.get("expression", "")).strip()
    working_directory = str(payload.get("workingDirectory", "")).strip()
    notify_platforms = [str(item) for item in payload.get("notifyPlatforms", [])]

    lane = _infer_lane(name, description)
    artifact_type = _infer_artifact_type(name, description)
    data_dir, output_dir = _resolve_data_dirs(name, working_directory)
    latest_outputs = _latest_outputs(Path(output_dir)) if output_dir else []

    return LobsterTask(
        name=name,
        description=description,
        schedule_type=schedule_type,
        schedule_expression=schedule_expression,
        working_directory=working_directory,
        notify_platforms=notify_platforms,
        source_file=str(path),
        data_dir=data_dir,
        output_dir=output_dir,
        latest_outputs=latest_outputs,
        lane=lane,
        artifact_type=artifact_type,
    )


def _infer_lane(name: str, description: str) -> str:
    text = f"{name} {description}"
    if any(token in text for token in ["日报", "周报", "告警", "运营"]):
        return "daily_ops"
    if any(token in text for token in ["广告", "T+0", "投放"]):
        return "ads_experiment"
    return "general"


def _infer_artifact_type(name: str, description: str) -> str:
    text = f"{name} {description}"
    if "周报" in text:
        return "analysis"
    if "日报" in text:
        return "analysis"
    return "general"


def _resolve_data_dirs(name: str, working_directory: str) -> tuple[str, str]:
    lower_name = name.lower()
    lower_working = working_directory.lower()

    if "weekly" in lower_name or "周报" in name or "weekly" in lower_working:
        root = LOBSTER_DATA_DIR / "weekly-report"
    else:
        root = LOBSTER_DATA_DIR / "daily-report"

    data_dir = str(root / "1_Input")
    output_dir = str(root / "2_Output")
    return data_dir, output_dir


def _latest_outputs(output_dir: Path, limit: int = 3) -> list[str]:
    if not output_dir.exists():
        return []

    files = [path for path in output_dir.iterdir() if path.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return [str(path) for path in files[:limit]]
