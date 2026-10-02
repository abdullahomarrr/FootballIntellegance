"""Minimal .env loader so local runs pick up optional settings without a new dependency."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path | None = None) -> None:
    """Set variables from a KEY=VALUE file without overriding the real environment."""
    target = path or Path(__file__).resolve().parents[2] / ".env"
    if not target.is_file():
        return
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip('"').strip("'")
        if name and value and name not in os.environ:
            os.environ[name] = value
