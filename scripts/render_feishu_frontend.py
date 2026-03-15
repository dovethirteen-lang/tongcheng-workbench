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
    payload = {
        "updated_at": state.get("updated_at", ""),
        "commands": state.get("commands", [])[:8],
        "documents": state.get("documents", [])[:8],
        "todos": state.get("todos", [])[:8],
        "feedback": state.get("feedback", [])[:8],
        "alerts": state.get("alerts", [])[:8],
        "capabilities": state.get("capabilities", {}),
        "release_plan": state.get("release_plan", {}),
    }

    output = data_dir / "workbench.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
