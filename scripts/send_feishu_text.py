from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.feishu_client import FeishuAPIError, FeishuConfigError, load_feishu_config, send_text_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a text message through Feishu app.")
    parser.add_argument("--receive-id", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--receive-id-type", default="open_id")
    args = parser.parse_args()

    try:
        config = load_feishu_config(BASE_DIR)
        result = send_text_message(
            config=config,
            receive_id=args.receive_id,
            text=args.text,
            receive_id_type=args.receive_id_type,
        )
    except (FeishuConfigError, FeishuAPIError) as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
