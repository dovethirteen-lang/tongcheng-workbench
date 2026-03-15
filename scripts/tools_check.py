from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "tooling.json"


def main() -> None:
    tooling = json.loads(CONFIG.read_text(encoding="utf-8"))
    report = {
        "python": shutil.which("py") or shutil.which("python"),
        "pdftoppm": shutil.which("pdftoppm") or tooling["pdf_tools"]["pdftoppm"],
        "tesseract": shutil.which("tesseract") or tooling["pdf_tools"]["tesseract"],
        "soffice": shutil.which("soffice") or tooling["pdf_tools"]["soffice"],
        "jupyter-lab": shutil.which("jupyter-lab"),
        "playwright-cli": shutil.which("playwright-cli"),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
