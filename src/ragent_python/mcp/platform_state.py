from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragent_python.config import get_settings


def _get_platform_state_path() -> Path | None:
    settings = get_settings()
    raw_path = settings.platform_state_path.strip() or settings.legacy_platform_state_path.strip()
    if not raw_path:
        return None

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _read_platform_state() -> dict[str, Any]:
    path = _get_platform_state_path()
    if path is None or not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_scoped_setting(key: str, tenant_id: str | None, org_id: str | None) -> dict[str, Any] | None:
    state = _read_platform_state()
    items = state.get("settings")
    if not isinstance(items, list):
        return None

    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("key") != key:
            continue
        if tenant_id is not None and item.get("tenantId") != tenant_id:
            continue
        if org_id is not None and item.get("orgId") != org_id:
            continue
        return item

    return None
