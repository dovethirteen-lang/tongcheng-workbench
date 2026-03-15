from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.feishu_longconn_client import FeishuLongConnectionApp


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Feishu long connection command client.")
    parser.add_argument("--log-level", default="INFO", help="DEBUG / INFO / WARNING / ERROR")
    args = parser.parse_args()

    print("Starting Feishu long connection client...")
    print("Keep this process running, then go back to Feishu Open Platform and click Save.")
    app = FeishuLongConnectionApp(base_dir=BASE_DIR, log_level=args.log_level)
    app.start()


if __name__ == "__main__":
    main()
