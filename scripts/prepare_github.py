#!/usr/bin/env python3
"""Remove non-essential API details before committing the public state."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "fruitflow-state.json"
if path.exists():
    state = json.loads(path.read_text(encoding="utf-8"))
    clean = {
        "used": sorted(set(state.get("used", []))),
        "scheduled": [
            {"video": item["video"], "dueAt": item["dueAt"]}
            for item in state.get("scheduled", [])
            if "video" in item and "dueAt" in item
        ],
    }
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Historique nettoyé pour GitHub.")
else:
    print("Aucun historique local à nettoyer.")
