"""File-based guest access store with quota management."""

from __future__ import annotations

import json
import os
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

STORE_DIR = Path(__file__).parent / "guest_accesses"
STORE_DIR.mkdir(exist_ok=True)
STORE_FILE = STORE_DIR / "guests.json"
LOG_FILE = STORE_DIR / "analytics.jsonl"


def _load() -> dict:
    if not STORE_FILE.exists():
        return {}
    try:
        return json.loads(STORE_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict) -> None:
    STORE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _log(event: str, token: str, meta: dict | None = None) -> None:
    entry = {"ts": datetime.utcnow().isoformat(), "event": event, "token": token, **(meta or {})}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def generate_token(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_guest(
    name: str,
    email: str = "",
    quota: int = 10,
    days_valid: int = 30,
    note: str = "",
) -> dict:
    token = generate_token()
    data = _load()
    expires = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    guest = {
        "token": token,
        "name": name,
        "email": email,
        "quota": quota,
        "used": 0,
        "created": datetime.utcnow().isoformat(),
        "expires": expires,
        "note": note,
        "active": True,
    }
    data[token] = guest
    _save(data)
    _log("created", token, {"name": name, "quota": quota})
    return guest


def verify_token(token: str) -> tuple[bool, str, dict | None]:
    """Returns (ok, reason, guest_dict)."""
    data = _load()
    guest = data.get(token)
    if not guest:
        return False, "token_invalid", None
    if not guest.get("active", True):
        return False, "token_disabled", guest
    expires = datetime.fromisoformat(guest["expires"])
    if datetime.utcnow() > expires:
        return False, "token_expired", guest
    if guest["used"] >= guest["quota"]:
        return False, "quota_exhausted", guest
    return True, "ok", guest


def consume_token(token: str) -> bool:
    """Decrement quota. Returns True if successful."""
    data = _load()
    guest = data.get(token)
    if not guest:
        return False
    guest["used"] = guest.get("used", 0) + 1
    _save(data)
    _log("used", token, {"used": guest["used"], "quota": guest["quota"]})
    return True


def adjust_quota(token: str, delta: int) -> dict | None:
    """Add or remove quota slots. Returns updated guest or None."""
    data = _load()
    guest = data.get(token)
    if not guest:
        return None
    guest["quota"] = max(guest.get("used", 0), guest["quota"] + delta)
    _save(data)
    _log("quota_adjusted", token, {"delta": delta, "new_quota": guest["quota"]})
    return guest


def list_guests() -> list[dict]:
    return list(_load().values())


def toggle_guest(token: str, active: bool) -> bool:
    data = _load()
    if token not in data:
        return False
    data[token]["active"] = active
    _save(data)
    return True


def get_analytics() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    lines = []
    for line in LOG_FILE.read_text().splitlines():
        try:
            lines.append(json.loads(line))
        except Exception:
            pass
    return lines
