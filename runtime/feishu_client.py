from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FeishuConfigError(RuntimeError):
    pass


class FeishuAPIError(RuntimeError):
    pass


def load_feishu_config(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "config" / "feishu_app.json"
    if not path.exists():
        raise FeishuConfigError(
            f"Missing config file: {path}. Copy config/feishu_app.sample.json to config/feishu_app.json first."
        )
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("app_id", "").startswith("REPLACE_") or config.get("app_secret", "").startswith("REPLACE_"):
        raise FeishuConfigError("Please fill app_id and app_secret in config/feishu_app.json before starting.")
    return config


def fetch_tenant_access_token(config: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(
        {"app_id": config["app_id"], "app_secret": config["app_secret"]},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FeishuAPIError(f"HTTP error while fetching tenant_access_token: {exc.code}") from exc
    except URLError as exc:
        raise FeishuAPIError(f"Network error while fetching tenant_access_token: {exc.reason}") from exc

    if data.get("code") != 0:
        raise FeishuAPIError(f"Feishu API returned code={data.get('code')}, msg={data.get('msg')}")
    return data


def send_text_message(config: dict[str, Any], receive_id: str, text: str, receive_id_type: str = "open_id") -> dict[str, Any]:
    token_data = fetch_tenant_access_token(config)
    payload = json.dumps(
        {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token_data['tenant_access_token']}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise FeishuAPIError(f"HTTP error while sending message: {exc.code}") from exc
    except URLError as exc:
        raise FeishuAPIError(f"Network error while sending message: {exc.reason}") from exc

    if data.get("code") != 0:
        raise FeishuAPIError(f"Feishu message API returned code={data.get('code')}, msg={data.get('msg')}")
    return data
