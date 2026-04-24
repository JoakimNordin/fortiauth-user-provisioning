from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_DIR = Path.home() / ".local" / "state" / "fauth"
AUDIT_LOG = AUDIT_DIR / "audit.log"


def log_event(command: str, instance: str, result: str, details: dict[str, Any] | None = None) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": os.environ.get("USER", "unknown"),
        "host": os.uname().nodename,
        "instance": instance,
        "command": command,
        "result": result,
    }
    if details:
        entry["details"] = details
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
