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

## Trạng thái hiện tại (13/10/2026)
- ✅ Domain, luật, grounding, parser, baseline keyword/summary, LLM extractor, eval CLI, API, màn duyệt, 54 test.
- ✅ 5 transcript + đáp án + 15 kịch bản tổng hợp.
- ⏳ Chưa chạy LLM thật lần nào → chưa có số eval của pipeline chính.
- ⏳ `PostgresRepository` mới là khung (`adapters/persistence/postgres.py`), đang dùng InMemory.

## Việc tiếp theo (theo thứ tự)
1. Nash gán nhãn `data/gold/m01–m05` → `make agreement`.
2. `make synth` → duyệt bản nháp → thêm m06–m20.
3. `make eval-llm` + `make eval-summary` → tinh chỉnh prompt → ghi EVAL_LOG.
4. `PostgresRepository` (lưu cả `events` để replay, `review_actions` append-only).
5. Deploy theo `docs/ARCHITECTURE.md §6`.

## Không làm ở v1
ASR / audio, bot vào họp, tích hợp Jira/Notion, đăng nhập nhiều tổ chức, fine-tune, ledger xuyên cuộc họp (schema đã có `series_id`, `thread`, `supersedes`).
