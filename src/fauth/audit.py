from __future__ import annotations

import getpass
import json
import platform
import socket
from datetime import datetime, timezone
from typing import Any

from fauth.config import state_dir


def _audit_log_path():
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "audit.log"


def log_event(command: str, instance: str, result: str, details: dict[str, Any] | None = None) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "os": platform.system(),
        "instance": instance,
        "command": command,
        "result": result,
    }
    if details:
        entry["details"] = details
    with _audit_log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
