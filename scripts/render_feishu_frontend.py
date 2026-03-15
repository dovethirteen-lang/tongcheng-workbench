from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.workbench_state import WorkbenchState


def main() -> None:
    frontend_dir = BASE_DIR / "09_feishu_frontend"
    data_dir = frontend_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    state = WorkbenchState().snapshot()
    notion_config = json.loads((BASE_DIR / "config" / "notion_workspace.json").read_text(encoding="utf-8"))
    feishu_config = json.loads((BASE_DIR / "config" / "feishu_app.json").read_text(encoding="utf-8"))
    payload = {
        "updated_at": state.get("updated_at", ""),
        "commands": state.get("commands", [])[:8],
        "documents": state.get("documents", [])[:8],
        "todos": state.get("todos", [])[:8],
        "feedback": state.get("feedback", [])[:8],
        "alerts": state.get("alerts", [])[:8],
        "last_result": state.get("last_result", {}),
        "capabilities": state.get("capabilities", {}),
        "release_plan": state.get("release_plan", {}),
        "notion_config": {
            "workspace_name": notion_config.get("workspace_name", ""),
            "workspace_url": notion_config.get("workspace_url", ""),
            "private_library_url": notion_config.get("private_library_url", ""),
            "prd_template_url": notion_config.get("prd_template_url", ""),
            "todo_strategy": notion_config.get("todo_strategy", {}),
            "feedback_strategy": notion_config.get("feedback_strategy", {}),
            "routing_map": notion_config.get("routing_map", {}),
        },
        "feishu_config": {
            "document_channel": feishu_config.get("document_channel", ""),
            "document_strategy": feishu_config.get("document_strategy", {}),
        },
    }

    output = data_dir / "workbench.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_output = data_dir / "workbench-summary.json"
    summary_output.write_text(
        json.dumps(
            {
                "updated_at": payload["updated_at"],
                "alert_count": len([item for item in payload["alerts"] if item.get("status") == "open"]),
                "todo_count": len([item for item in payload["todos"] if item.get("status") == "open"]),
                "feedback_count": len(payload["feedback"]),
                "document_count": len(payload["documents"]),
                "top_alert": payload["alerts"][0] if payload["alerts"] else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "summary_output": str(summary_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
