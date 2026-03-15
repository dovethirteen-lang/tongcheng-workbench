from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    content = f"""# {args.title}

## 摘要

请补一句话摘要。

## 1. 背景

请补背景。

## 2. 目标

请补目标。

## 3. 核心方案

请补方案。

## 4. 规则说明

请补规则说明。

## 5. 数据与埋点

请补数据与埋点。

## 6. 风险与依赖

请补风险与依赖。

## 7. 上线与排期

请补上线与排期。

## 表格粘贴说明

- 可直接粘贴的表格：
- 需要拆开的表格：

## 图片占位

- 图片 1：
- 图片 2：
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote wiki handoff to {args.output}")


if __name__ == "__main__":
    main()
