from __future__ import annotations

import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.feishu_client import FeishuAPIError, FeishuConfigError, fetch_tenant_access_token, load_feishu_config


def main() -> None:
    try:
        config = load_feishu_config(BASE_DIR)
        token_data = fetch_tenant_access_token(config)
    except (FeishuConfigError, FeishuAPIError) as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    print(
        json.dumps(
            {
                "ok": True,
                "app_id": config["app_id"],
                "expire": token_data.get("expire"),
                "tenant_access_token_prefix": str(token_data.get("tenant_access_token", ""))[:16],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
