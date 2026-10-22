API := apps/api
# uv chạy được trên Windows (Git Bash) / Mac / Linux; --no-sync: dùng venv do `make install` tạo, không sinh uv.lock
UV := uv run --no-sync
PY := $(UV) --project $(API) python
# Console Windows mặc định cp1252 → in tiếng Việt bị UnicodeEncodeError
export PYTHONUTF8 := 1

.PHONY: help install test lint dev-api dev-web up down eval-keyword eval-oracle eval-llm eval-summary agreement synth

help:            ## Liệt kê lệnh
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install:         ## Cài API (venv) + web
	uv venv --python 3.12 $(API)/.venv
	uv pip install -q --python $(API)/.venv -e "$(API)[dev]"
	cd apps/web && npm install --no-audit --no-fund

test:            ## Chạy toàn bộ test API
	cd $(API) && $(UV) python -m pytest -q

lint:            ## Lint + kiểm tra format + typecheck web
	cd $(API) && $(UV) ruff check src tests && $(UV) ruff format --check src tests
	cd apps/web && npx tsc --noEmit

dev-api:         ## API ở :8000 (đọc .env)
	cd $(API) && $(UV) uvicorn chot.api.main:app --reload --port 8000 --env-file ../../.env

dev-web:         ## Web ở :3000
	cd apps/web && npm run dev

up:              ## Docker compose: db + api + web
	docker compose up --build

down:
	docker compose down

eval-keyword:    ## Baseline keyword vs đáp án (không cần key)
	$(PY) -m chot.eval.run --system keyword --gold data/answer_key --show-errors

eval-oracle:     ## Luật trên sự kiện chuẩn — phải đạt 100% (kiểm tra luật khớp hướng dẫn gán nhãn)
	$(PY) -m chot.eval.run --system replay --events $(API)/tests/fixtures/oracle_events --gold data/answer_key

eval-llm:        ## Pipeline chính (cần LLM_* trong .env), lưu kết quả vào data/runs
	set -a && . ./.env && set +a && $(PY) -m chot.eval.run --system llm --gold data/gold --save data/runs --show-errors

eval-summary:    ## Baseline "1 prompt tóm tắt" (cần LLM_*)
	set -a && . ./.env && set +a && $(PY) -m chot.eval.run --system summary --gold data/gold --save data/runs --show-errors

agreement:       ## So nhãn bạn tự gán (data/gold) với đáp án (data/answer_key)
	$(PY) -m chot.eval.run --system labels --pred data/gold --gold data/answer_key --show-errors

synth:           ## Sinh 15 transcript nháp (cần GEN_* hoặc LLM_*)
	set -a && . ./.env && set +a && $(PY) scripts/generate_synthetic.py
