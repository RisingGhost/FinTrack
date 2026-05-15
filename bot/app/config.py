import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    tg_token: str
    tg_whitelist_tg_id: int
    database_url: str
    queries_dir: str


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required env var: {name}")
    return value


def load_settings() -> Settings:
    whitelist_raw = _get_required_env("TG_WHITELIST_TG_ID")
    try:
        whitelist_id = int(whitelist_raw)
    except ValueError as exc:
        raise ValueError("TG_WHITELIST_TG_ID must be an integer") from exc

    return Settings(
        tg_token=_get_required_env("TG_TOKEN"),
        tg_whitelist_tg_id=whitelist_id,
        database_url=_get_required_env("DATABASE_URL"),
        queries_dir=_get_required_env("QUERIES_DIR"),
    )
