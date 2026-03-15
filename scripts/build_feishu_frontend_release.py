from __future__ import annotations

import shutil
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.render_feishu_frontend import main as render_feishu_frontend


def main() -> None:
    render_feishu_frontend()

    source_dir = BASE_DIR / "09_feishu_frontend"
    target_dir = BASE_DIR / "site" / "feishu-workbench"

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in source_dir.iterdir():
        if item.name.startswith("."):
            continue
        destination = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    print(target_dir)


if __name__ == "__main__":
    main()
