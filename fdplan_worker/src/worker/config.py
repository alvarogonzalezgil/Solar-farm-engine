"""Load worker configuration from environment / .env file."""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


REQUIRED_KEYS = (
    "APP_KEY",
    "TOKEN",
    "DATA_PARTITION",
    "ENVIRONMENT",
    "SOLAR_COMPUTE_SPEC_ID",
)


def load_config() -> dict[str, str]:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    _load_dotenv(env_path)
    missing = [k for k in REQUIRED_KEYS if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"Missing required configuration: {', '.join(missing)}")
    return {k: os.environ[k] for k in os.environ if k.isupper() or k.startswith("SOLAR_")}
