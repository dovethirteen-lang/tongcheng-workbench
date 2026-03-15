from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from runtime.workbench_server import run_workbench_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local workbench server with API and frontend.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4390)
    args = parser.parse_args()
    run_workbench_server(base_dir=BASE_DIR, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
