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
    #             Cuộc họp có file sự kiện ở REPLAY_EVENTS_DIR → replay, không gọi LLM.
    # "replay"  = luật chạy trên sự kiện đã lưu ở REPLAY_EVENTS_DIR (demo m01–m25 không cần key);
    #             cuộc họp không có file sự kiện → rơi về baseline keyword.
    # "keyword" = baseline lọc keyword.
    ledger_builder: str = field(default_factory=lambda: _env("LEDGER_BUILDER", "keyword"))
    replay_events_dir: str = field(default_factory=lambda: _env("REPLAY_EVENTS_DIR", "demo_events"))
    llm_base_url: str | None = field(default_factory=lambda: _env("LLM_BASE_URL"))
    llm_api_key: str | None = field(default_factory=lambda: _env("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "gpt-4.1-mini"))
    max_transcript_chars: int = field(
        default_factory=lambda: int(_env("MAX_TRANSCRIPT_CHARS", "20000"))
    )
    # M3: họp dài > CHUNK_SIZE câu → bản đồ chủ đề + gán nhãn theo đoạn (song song)
    chunk_size: int = field(default_factory=lambda: int(_env("CHUNK_SIZE", "100")))
    chunk_context: int = field(default_factory=lambda: int(_env("CHUNK_CONTEXT", "10")))
    llm_max_concurrency: int = field(default_factory=lambda: int(_env("LLM_MAX_CONCURRENCY", "4")))
    llm_rate_limit_per_hour: int = field(
        default_factory=lambda: int(_env("LLM_RATE_LIMIT_PER_HOUR", "10"))
    )
    llm_global_limit_per_hour: int = field(
        default_factory=lambda: int(_env("LLM_GLOBAL_LIMIT_PER_HOUR", "60"))
    )
    # Tạo nhóm họp (POST /series) ghi DB, không cần mã → giới hạn theo IP
    series_rate_limit_per_hour: int = field(
        default_factory=lambda: int(_env("SERIES_RATE_LIMIT_PER_HOUR", "20"))
    )
    # Mã truy cập để gọi LLM (header X-Access-Code); transcript mẫu replay không cần.
    # Không đặt + PUBLIC_DEMO=true → từ chối mọi lượt gọi LLM.
    llm_access_code: str | None = field(default_factory=lambda: _env("LLM_ACCESS_CODE"))
    # Demo công khai: tắt GET /meetings (lộ cuộc họp của người khác) và /docs.
    public_demo: bool = field(
        default_factory=lambda: (_env("PUBLIC_DEMO", "false") or "").lower() == "true"
    )
    database_url: str | None = field(default_factory=lambda: _env("DATABASE_URL"))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            (_env("CORS_ORIGINS", "http://localhost:3000") or "").split(",")
        )
    )


def get_settings() -> Settings:
    return Settings()
