from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import urllib.request


BASE_DIR = Path(__file__).resolve().parents[1]
API_BASE = "http://127.0.0.1:4390"
OUTPUT_PATH = Path(r"D:\Project\runtime\mvp_10_regression_latest.json")


def post_command(payload: dict) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}/api/command",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    cases = [
        {
            "name": "hotel_experiment_recovery",
            "payload": {
                "text": (
                    "这是一个广告专项任务。实验名称：酒店老客补贴实验MVP。"
                    "实验方案链接：https://www.notion.so/hotel-exp-mvp。"
                    "sql参考：D:\\Project\\sql\\hotel_exp_mvp.sql。"
                    "指标口径：转化率,ROI,老客占比。截止时间：今天17:00前。"
                ),
                "source": "feishu_openclaw",
                "lane": "ads_experiment",
                "action": "analysis",
                "intent": "analysis",
            },
            "expect": {
                "executor": "codex",
                "has_experiment_result": True,
            },
        },
        {
            "name": "openclaw_lobster_dispatch",
            "payload": {
                "text": "请通过 Lobster 运行任务：同程广告承接侧 T+0 周报，并回传最新输出。",
                "source": "feishu_openclaw",
                "lane": "daily_ops",
                "action": "analysis",
                "intent": "analysis",
            },
            "expect": {
                "executor": "lobster",
                "run_status_in": ["queued", "running", "success"],
            },
        },
        {
            "name": "prototype_fast_path",
            "payload": {
                "text": (
                    "根据这个需求生成HTML原型。资料位置：https://www.notion.so/proto-mvp。"
                    "输出HTML并本地浏览器预览，Figma待优化。"
                ),
                "source": "workbench_frontend",
                "lane": "wechat_growth",
                "action": "prd_draft",
                "intent": "analysis",
            },
            "expect": {
                "executor": "codex",
                "has_prototype_task": True,
            },
        },
    ]

    results: list[dict] = []
    overall_ok = True

    for case in cases:
        response = post_command(case["payload"])
        wi = ((response.get("state") or {}).get("workflow_instances") or [{}])[0]
        item = {
            "case": case["name"],
            "workflow_id": wi.get("workflow_id"),
            "executor": wi.get("executor"),
            "workflow_stage": wi.get("workflow_stage"),
            "priority_quadrant": wi.get("priority_quadrant"),
            "run_status": wi.get("run_status"),
            "has_experiment_result": bool(wi.get("experiment_result")),
            "has_prototype_task": bool(wi.get("prototype_task")),
            "ok": True,
            "errors": [],
        }

        expect = case["expect"]
        if item["executor"] != expect["executor"]:
            item["ok"] = False
            item["errors"].append(f"executor expected={expect['executor']} actual={item['executor']}")
        if expect.get("has_experiment_result") and not item["has_experiment_result"]:
            item["ok"] = False
            item["errors"].append("missing experiment_result")
        if expect.get("has_prototype_task") and not item["has_prototype_task"]:
            item["ok"] = False
            item["errors"].append("missing prototype_task")
        if expect.get("run_status_in") and item["run_status"] not in expect["run_status_in"]:
            item["ok"] = False
            item["errors"].append(
                f"run_status expected in {expect['run_status_in']} actual={item['run_status']}"
            )

        if not item["ok"]:
            overall_ok = False
        results.append(item)

    report = {
        "ok": overall_ok,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "api_base": API_BASE,
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not overall_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"mvp_10_regression failed: {exc}")
        raise
