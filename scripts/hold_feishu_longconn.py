from __future__ import annotations

import asyncio
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.feishu_longconn_client import FeishuLongConnectionApp


def main() -> None:
    print("Connecting to Feishu long connection service...")
    print("Wait until you see CONNECTED, then go back to Feishu Open Platform and click Save.")
    print("Keep this window open until the platform saves successfully.")
    app = FeishuLongConnectionApp(base_dir=BASE_DIR, log_level="INFO")

    async def runner() -> None:
        await app.connect_and_hold()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
