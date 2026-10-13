PY := apps/api/.venv/bin/python
API := apps/api

.PHONY: help install test lint dev-api dev-web up down eval-keyword eval-oracle eval-llm eval-summary agreement synth

help:            ## Liệt kê lệnh
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install:         ## Cài API (venv) + web
	python3 -m venv $(API)/.venv
	$(PY) -m pip install -q -e "$(API)[dev]"
	cd apps/web && npm install --no-audit --no-fund

test:            ## Chạy toàn bộ test API
	cd $(API) && .venv/bin/python -m pytest -q

lint:            ## Lint + kiểm tra format + typecheck web
	cd $(API) && .venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
	cd apps/web && npx tsc --noEmit

dev-api:         ## API ở :8000 (đọc .env)
	cd $(API) && set -a && . ../../.env 2>/dev/null; set +a; .venv/bin/uvicorn chot.api.main:app --reload --port 8000

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
