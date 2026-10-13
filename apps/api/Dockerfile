FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Sự kiện LLM đã lưu cho m01–m25: transcript mẫu replay, không tốn token (REPLAY_EVENTS_DIR)
COPY demo_events ./demo_events

# Không chạy bằng root
RUN useradd --create-home app
USER app

EXPOSE 8000
# --proxy-headers: lấy IP thật của khách sau proxy (Railway) cho giới hạn theo IP
CMD ["sh", "-c", "uvicorn chot.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
