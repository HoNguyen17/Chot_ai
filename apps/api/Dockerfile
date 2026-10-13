FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Sự kiện mẫu cho chế độ LEDGER_BUILDER=replay (demo không cần API key)
COPY tests/fixtures/oracle_events ./tests/fixtures/oracle_events

EXPOSE 8000
CMD ["sh", "-c", "uvicorn chot.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
