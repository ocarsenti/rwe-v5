"""File-based pageview counter — simple hit counts, not unique-visitor analytics."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STORE_DIR = Path(__file__).parent / "guest_accesses"
STORE_DIR.mkdir(exist_ok=True)
LOG_FILE = STORE_DIR / "visits.jsonl"


def record_visit(path: str) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "path": path}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_visits() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    visits = []
    for line in LOG_FILE.read_text().splitlines():
        try:
            visits.append(json.loads(line))
        except Exception:
            pass
    return visits


def get_visit_stats() -> dict:
    visits = _load_visits()
    today = datetime.now(timezone.utc).date().isoformat()

    by_path = Counter(v["path"] for v in visits)
    by_day = Counter(v["ts"][:10] for v in visits)
    today_count = by_day.get(today, 0)

    last_14_days = sorted(by_day.items())[-14:]

    return {
        "total": len(visits),
        "today": today_count,
        "by_path": dict(sorted(by_path.items(), key=lambda kv: -kv[1])),
        "by_day": [{"date": d, "count": c} for d, c in last_14_days],
    }
