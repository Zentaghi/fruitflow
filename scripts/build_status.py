#!/usr/bin/env python3
"""Build the public, non-sensitive status consumed by the Pages site."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
state_path = ROOT / "fruitflow-state.json"
output_path = ROOT / "docs" / "status.json"
state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"used": [], "scheduled": []}
now = datetime.now(ZoneInfo("Europe/Paris"))
future = sorted(
    (item for item in state.get("scheduled", []) if datetime.fromisoformat(item["dueAt"]) > now),
    key=lambda item: item["dueAt"],
)
payload = {
    "updatedAt": now.isoformat(timespec="minutes"),
    "usedCount": len(set(state.get("used", []))),
    "queueCount": len(future),
    "nextPost": future[0]["dueAt"] if future else None,
}
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
