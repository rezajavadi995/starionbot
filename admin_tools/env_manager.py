from __future__ import annotations

from pathlib import Path

ENV_PATH = Path(".env")


def load_env_map() -> dict[str, str]:
    if not ENV_PATH.exists():
        return {}
    data: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def save_env_map(values: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    ENV_PATH.write_text("\n".join(lines) + "\n")


def set_env_value(key: str, value: str) -> None:
    env = load_env_map()
    env[key] = value
    save_env_map(env)


def mask(value: str, keep: int = 4) -> str:
    if len(value) <= keep:
        return "*" * len(value)
    return "*" * (len(value) - keep) + value[-keep:]
