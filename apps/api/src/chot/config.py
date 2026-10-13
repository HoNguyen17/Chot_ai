"""Cấu hình đọc từ biến môi trường (.env). Không có giá trị bí mật mặc định."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class Settings:
    # "llm"     = pipeline chính: LLM gán sự kiện + luật (cần LLM_*).
    # "replay"  = luật chạy trên sự kiện đã lưu ở REPLAY_EVENTS_DIR (demo m01–m05 không cần key);
    #             cuộc họp không có file sự kiện → rơi về baseline keyword.
    # "keyword" = baseline lọc keyword.
    ledger_builder: str = field(default_factory=lambda: _env("LEDGER_BUILDER", "keyword"))
    replay_events_dir: str = field(
        default_factory=lambda: _env("REPLAY_EVENTS_DIR", "tests/fixtures/oracle_events")
    )
    llm_base_url: str | None = field(default_factory=lambda: _env("LLM_BASE_URL"))
    llm_api_key: str | None = field(default_factory=lambda: _env("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "gpt-4.1-mini"))
    database_url: str | None = field(default_factory=lambda: _env("DATABASE_URL"))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            (_env("CORS_ORIGINS", "http://localhost:3000") or "").split(",")
        )
    )


def get_settings() -> Settings:
    return Settings()
