from __future__ import annotations

import os
from pathlib import Path


def load_local_env() -> None:
    """Load key=value pairs from local env files without overriding existing env."""

    root_dir = Path(__file__).resolve().parent.parent
    for filename in (".env", ".env.local"):
        env_path = root_dir / filename
        if env_path.exists():
            _load_env_file(env_path)


def _load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ[key] = value
