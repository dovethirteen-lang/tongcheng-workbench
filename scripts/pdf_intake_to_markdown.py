from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
from pathlib import Path

import fitz
import pytesseract
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "tooling.json"


def load_tool(name: str) -> str:
    tooling = json.loads(CONFIG.read_text(encoding="utf-8"))
    return shutil.which(name) or tooling["pdf_tools"].get(name, "")


def extract_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    parts: list[str] = []
    for page in doc:
        text = page.get_text("text").strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def run_pdftotext(pdf_path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return ""
    result = subprocess.run(
        [pdftotext, str(pdf_path), "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    return result.stdout.strip()


def run_ocr(pdf_path: Path) -> str:
    tesseract = load_tool("tesseract")
    if not tesseract or not Path(tesseract).exists():
        return ""

    pytesseract.pytesseract.tesseract_cmd = tesseract
    doc = fitz.open(pdf_path)
    parts: list[str] = []

    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(image, lang="chi_sim+eng").strip()
        if text:
            parts.append(text)

    return "\n\n".join(parts)


def build_markdown(title: str, source: Path, text: str) -> str:
    return f"""# {title}

## 来源信息

- 来源文件：`{source.name}`
- 来源路径：`{source}`

## 原始内容摘要

请在这里补一句话摘要。

## 可读转写

{text if text else "未成功提取文字，请补 OCR 或人工整理。"}

## 关键信息摘录

- 核心目标：
- 涉及用户：
- 关键动作：
- 关键规则：
- 关键时间：
- 待确认点：

## 下一步

- 补结构化需求卡片
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = extract_text(args.input_pdf)
    if len(text.strip()) < 50:
        fallback = run_pdftotext(args.input_pdf)
        if fallback:
            text = fallback
    if len(text.strip()) < 50:
        ocr_text = run_ocr(args.input_pdf)
        if ocr_text:
            text = ocr_text

    title = args.input_pdf.stem
    markdown = build_markdown(title, args.input_pdf, text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote markdown to {args.output}")


if __name__ == "__main__":
    main()
