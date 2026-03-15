from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.wecom_bot_client import WecomBotConfigError, run_long_connection_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the WeCom AI Bot long-connection client.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and run a local command simulation.")
    parser.add_argument("--once", action="store_true", help="Exit after initial boot log.")
    args = parser.parse_args()

    try:
        run_long_connection_client(base_dir=BASE_DIR, dry_run=args.dry_run, once=args.once)
    except WecomBotConfigError as exc:
        print(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
