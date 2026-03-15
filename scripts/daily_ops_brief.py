from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    content = f"""# 每日作战简报 - {args.date}

## 今日主线

1. 
2. 
3. 

## 今日插单

- 

## 告警与 deadline

- 告警：
- 截止事项：

## 竞品摘要入口

- OTA：
- 微信生态：

## 收盘提醒

- 今天必须收口的事项：
- 明天要提前准备的事项：
"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Wrote daily brief to {args.output}")


if __name__ == "__main__":
    main()
