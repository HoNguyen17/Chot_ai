# CLAUDE.md — Chốt

Đọc file này trước khi sửa code. Tài liệu chi tiết ở `docs/`.

## Sản phẩm trong 3 dòng
- Input: transcript cuộc họp tiếng Việt (trộn Anh). Output: **Decision Ledger** — quyết định, task, vướng mắc… mỗi mục có trạng thái cuối và trích dẫn.
- Bài toán khó: không biến ý kiến trung gian thành quyết định (A đề xuất, B được chốt → chỉ B là quyết định).
- Người dùng: PM / trưởng nhóm SME họp dự án định kỳ. North-star: **tỷ lệ chốt nhầm ≤ 5%**.

## 5 luật vàng
1. **LLM gán nhãn, code quyết định.** LLM chỉ trả sự kiện (`propose/agree/assign…`). Trạng thái cuối chỉ được suy ra trong `apps/api/src/chot/domain/status_rules.py`. Không bao giờ để LLM trả về `status`.
2. **Không bằng chứng thì không xuất.** Mọi mục phải có `quote` khớp transcript (grounding tầng 1). Đừng nới `domain/grounding.py` để "cho qua test".
3. **Precision > recall cho "Đã chốt".** Không chắc → `needs_confirmation`. Không bao giờ suy đoán owner / deadline / người quyết.
4. **Domain thuần.** `domain/` không import adapter, FastAPI, OpenAI hay I/O. Use case chỉ dùng port trong `usecases/ports.py`. Chỉ `api/deps.py` nối adapter cụ thể.
5. **Không dùng bộ test làm ví dụ / dữ liệu train.** Few-shot trong prompt chỉ lấy từ `data/examples/m00`. Không fine-tune ở v1 (ADR-0004).

## Lệnh
```bash
make install        # venv + npm
make test           # pytest (phải xanh trước khi commit)
make lint           # ruff + format check + tsc
make dev-api        # :8000   (đọc .env)
make dev-web        # :3000
make eval-keyword   # baseline, không cần key
make eval-oracle    # luật trên sự kiện chuẩn — PHẢI 100%
make eval-llm       # pipeline thật, lưu vào data/runs/<time>-llm/
make agreement      # nhãn data/gold vs data/answer_key
```

## Bản đồ code
| Muốn… | Sửa ở |
|---|---|
| Đổi cách suy trạng thái | `domain/status_rules.py` + test `tests/test_status_rules.py` |
| Thêm tín hiệu rào đón / backchannel | `domain/text.py` + `tests/test_text_and_dates.py` |
| Đổi quy ước hạn chót | `domain/dates.py` + `docs/DATA_DESIGN.md §3.4` |
| Sửa prompt | `prompts/extract_events.md` → chạy `make eval-llm`, ghi `docs/EVAL_LOG.md` |
| Đổi model / nhà cung cấp LLM | `.env` (`LLM_BASE_URL`, `LLM_MODEL`) — không sửa code |
| Thêm nơi lưu trữ | `adapters/persistence/` + nối trong `api/deps.py` |
| Thêm định dạng xuất | `adapters/export/` + route trong `api/main.py` |
| Thêm field cho mục | `domain/models.py` **và** `apps/web/src/lib/types.ts` **và** `db/migrations/` **và** `docs/DATA_DESIGN.md` |
| Đổi màu / chữ | `apps/web/src/app/globals.css` **và** `docs/DESIGN_SYSTEM.md` |

## Quy trình khi sửa luật hoặc prompt
1. Viết/sửa test trước (luật) hoặc ghi giả thuyết (prompt).
2. `make test` + `make eval-oracle` phải xanh (luật không lệch hướng dẫn gán nhãn).
3. Sửa prompt: `make eval-llm`; chỉ sửa luật: replay sự kiện đã lưu — `python -m chot.eval.run --system replay --events data/runs/<run>/events --gold data/gold` (không tốn token).
4. Thêm một dòng vào `docs/EVAL_LOG.md`. Chốt nhầm tăng → không merge.

## Quy ước
- Python 3.12, type hints đầy đủ, Pydantic v2, `ruff` (line 100). Tên biến/hàm tiếng Anh; docstring, comment, thông báo cho người dùng tiếng Việt.
- TypeScript strict. Không thêm thư viện UI lớn; dùng token CSS sẵn có.
- Commit nhỏ, message dạng `feat(rules): …`, `fix(grounding): …`, `docs: …`, `eval: …`.

## Trạng thái hiện tại (15/10/2026)
- ✅ Domain, luật, grounding, parser, baseline keyword/summary, LLM extractor, eval CLI, API, màn duyệt, 74 test.
- ✅ 25 transcript kịch bản (m01–m05 Nash tự viết, m06–m25 tổng hợp; chưa có họp thật) + gold của Nash + answer_key + oracle events; 13 quy ước gán nhãn trong `docs/LABELING_GUIDE.md`.
- ✅ Eval trên gold m01–m25 (gpt-4.1-mini): chốt nhầm 4,8% đầu-cuối (`data/runs/20261014-042208-llm`), 0% khi replay qua luật hiện tại (`20261014-042750-replay`). Keyword 57,6%, tóm tắt 54,3%. Recall mục 51,7%, vướng mắc 7/74.
- ✅ Demo https://chot.nashng.dev (Vercel) + api.chot.nashng.dev (Railway); m01–m05 replay `apps/api/demo_events/` (= events của `042208-llm`).
- ✅ Bản nháp nộp Mission 2: `docs/MISSION2.md`, `docs/VIDEO_SCRIPT.md`.
- ⏳ Chưa chạy lại LLM đầu-cuối sau luật `ccf3042` ("Ừ." → needs_confirmation).
- ⏳ `PostgresRepository` mới là khung (`adapters/persistence/postgres.py`), đang dùng InMemory.

## Việc tiếp theo (theo thứ tự)
1. Quay video theo `docs/VIDEO_SCRIPT.md`, nộp Mission 2.
2. Vướng mắc: luật sinh `blocker` từ `object` có nội dung cụ thể (quy ước 1–2) → `make eval-oracle` + replay.
3. Prompt: quyết định trong câu giao việc (m03 u016), `commit` cho câu nhận việc ("Ok anh, … em gửi" — m04, m14, m25), không gộp key 2 phương án (m02 D3) → `make eval-llm` vài lần để đo độ ổn định.
4. `PostgresRepository` (lưu cả `events` để replay, `review_actions` append-only).
5. Người chấm grounding tầng 2 + người gán nhãn thứ hai.

## Không làm ở v1
ASR / audio, bot vào họp, tích hợp Jira/Notion, đăng nhập nhiều tổ chức, fine-tune, ledger xuyên cuộc họp (schema đã có `series_id`, `thread`, `supersedes`).
