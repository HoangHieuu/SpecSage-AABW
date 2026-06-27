from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
import os


FALSE_VALUES = {"0", "false", "no", "off"}
TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MAX_TOKENS = 700


@dataclass(frozen=True)
class OpenRouterSettings:
    api_key: str | None = field(default=None, repr=False)
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    site_url: str = "http://localhost:3000"
    app_name: str = "PC Build Copilot"
    timeout_seconds: float = 12.0
    max_tokens: int = DEFAULT_OPENROUTER_MAX_TOKENS
    enabled: bool = False


def load_env_file(path: Path | None = None) -> dict[str, str]:
    env_path = path or default_env_file()
    if not env_path or not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _strip_quotes(value.strip())
    return values


def default_env_file() -> Path | None:
    candidates = [Path.cwd(), *Path.cwd().parents]
    package_root = Path(__file__).resolve().parents[4]
    candidates.append(package_root)
    for base in candidates:
        env_path = base / ".env"
        if env_path.exists():
            return env_path
    return Path.cwd() / ".env"


def openrouter_settings(
    env: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> OpenRouterSettings:
    file_values = load_env_file(env_file)
    merged = {**file_values, **os.environ}
    if env is not None:
        merged.update(env)

    api_key = _empty_to_none(merged.get("OPENROUTER_API_KEY"))
    enabled = _enabled_from_env(merged.get("LLM_AGENT_ENABLED"), api_key)
    return OpenRouterSettings(
        api_key=api_key,
        model=merged.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL,
        base_url=(merged.get("OPENROUTER_BASE_URL") or DEFAULT_OPENROUTER_BASE_URL).rstrip("/"),
        site_url=merged.get("OPENROUTER_SITE_URL") or "http://localhost:3000",
        app_name=merged.get("OPENROUTER_APP_NAME") or "PC Build Copilot",
        timeout_seconds=_float_value(merged.get("OPENROUTER_TIMEOUT_SECONDS"), 12.0),
        max_tokens=_int_value(merged.get("OPENROUTER_MAX_TOKENS"), DEFAULT_OPENROUTER_MAX_TOKENS),
        enabled=enabled,
    )


def _enabled_from_env(raw_value: str | None, api_key: str | None) -> bool:
    if raw_value is None:
        return bool(api_key)
    normalized = raw_value.strip().lower()
    if normalized in FALSE_VALUES:
        return False
    if normalized in TRUE_VALUES:
        return bool(api_key)
    return bool(api_key)


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _float_value(value: str | None, fallback: float) -> float:
    if value is None:
        return fallback
    try:
        parsed = float(value)
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


def _int_value(value: str | None, fallback: int) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(value)
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback
