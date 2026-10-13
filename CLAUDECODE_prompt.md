# Prompt cho Claude Code — Chốt · Mission 2

Mỗi phase dùng **1 prompt**. Mở Claude Code ở gốc repo `chot/` rồi dán prompt vào. Claude Code làm xong một phase sẽ dừng lại báo cáo. Nash kiểm tra xong mới dán prompt phase tiếp theo.

> ⚠️ Claude Code là agent có quyền thật trên máy: sửa file và chạy lệnh được. Trước khi dán prompt, đọc kỹ 3 mục: Scope, Action Boundaries và điều kiện DỪNG.

**Mục tiêu Mission 2:** chứng minh vòng lõi *Transcript → hiểu diễn biến → trích xuất có cấu trúc → bằng chứng*, đo bằng **tỷ lệ chốt nhầm**. Bài nộp gồm repo public có README, demo `chot.nashng.dev`, video ≤5 phút, ≥5 test case và 3 câu trả lời.

**Đã chốt, không bàn lại:**
- **Hạn:** 1–2 ngày.
- **LLM:** OpenAI `gpt-4.1-mini` qua `OpenAICompatibleClient` có sẵn.
- **Gold:** Nash tự gán nhãn m01–m05, thêm 5 kịch bản bẫy sinh tự động.
- **Deploy:** Vercel cho web, Railway cho API, DNS ở Porkbun.
- **Lưu trữ:** không dùng Postgres, chỉ InMemory.
- **Không làm:** CI.

---

## 0. Chuẩn bị một lần (Windows)

1. Cài `make`, mở **Git Bash** (không dùng PowerShell cho `make`):
   ```bash
   winget install ezwinports.make
   ```
   uv, Docker Desktop và Node đã có sẵn. Python 3.14 trên máy **không** dùng. uv tự tải 3.12 ở Phase 0.
2. Tạo file `.env` rồi điền key theo mục 3:
   ```bash
   cp .env.example .env
   ```
3. Chạy `claude update`, mở `claude` ở gốc repo, rồi gõ `/model opusplan` và `/effort medium`.

## 1. Chọn model và effort theo phase

| Phase | Việc | Model | Effort |
|---|---|---|---|
| P0 | Chạy được trên Windows | `sonnet` | medium |
| P1 | Kiểm tra nhãn gold Nash tự gán | `haiku` | low |
| P2 | Eval LLM lần đầu | `sonnet` | medium |
| P3 | Tinh chỉnh prompt (vòng lặp eval) | `opusplan` | high (thêm `ultrathink` nếu kẹt 2 vòng) |
| P4 | Sinh 5 kịch bản bẫy | `sonnet` | medium |
| P5 | Demo an toàn: replay + rate limit | `opusplan` | medium |
| P6 | Deploy | `opus` | high |
| P7 | Tài liệu nộp bài | `sonnet` | medium |
| P8 | Review cuối (mở **session mới**) | `opus` | high |

Có 2 ngoại lệ:
- Sửa nhỏ như lint, đổi tên hay sửa typo docs thì dùng `/model haiku`.
- Bug đã thử 2 lần không ra thì chạy `mattpocock-skills:diagnosing-bugs` trước. Vẫn chưa được mới chuyển `/model fable`.

## 1b. Chọn skill theo phase

Thứ tự ưu tiên: **ponytail → mattpocock-skills → skill khác**.
- `ponytail` tự bật mỗi session. Nó không được cắt bớt validation, bảo mật, test hay grounding.
- Riêng dự án này: **5 luật vàng trong `CLAUDE.md` thắng mọi skill.**

| Phase | Lúc plan | Lúc code | Cuối phase (trước commit) |
|---|---|---|---|
| P0 | — | ponytail | `ponytail:ponytail-review`, `/verify` |
| P1 | — | — | — |
| P2 | — | `mattpocock-skills:diagnosing-bugs` (khi pipeline lỗi) | — |
| P3 | `mattpocock-skills:grilling` (hỏi vặn giả thuyết sửa prompt) | ponytail + `mattpocock-skills:tdd` (chỉ khi đụng luật) | `ponytail:ponytail-review` |
| P4 | — | ponytail | — |
| P5 | `mattpocock-skills:grilling` (ranh giới replay/LLM, IP sau proxy) | ponytail + `mattpocock-skills:tdd` | `ponytail:ponytail-review`, `mattpocock-skills:code-review`, `/security-review` |
| P6 | `ponytail:ponytail-audit` | ponytail | `/security-review`, `mattpocock-skills:wizard` (script hướng dẫn dashboard) |
| P7 | — | `anthropic-skills:vietnamese`, `anthropic-skills:humanizer` | — |
| P8 | — | — | `mattpocock-skills:code-review` + `ponytail:ponytail-review` + `/security-review` |

---

## 2. Thứ tự làm (1–2 ngày)

```
Ngày 1 sáng   P0 (30') → P1 Nash gán nhãn tay (1–1,5h) → P2 (20')
Ngày 1 chiều  P3 (2–3h, tối đa 3 vòng) → P4 (sinh 15', Nash duyệt + gán nhãn 1h)
Ngày 2 sáng   P5 (1,5h) → P6 (1h code + 30' Nash làm dashboard)
Ngày 2 chiều  P7 (1h) → P8 review → Nash quay video
```

---

## 3. Lấy API key cho `.env`

Dự án gọi LLM qua chuẩn OpenAI (`apps/api/src/chot/adapters/llm/client.py`). Chỉ cần **1 key OpenAI**.

### 3.1 OpenAI (bắt buộc cho P2–P5)
1. Vào https://platform.openai.com, đăng nhập hoặc đăng ký.
2. Settings → **Billing**:
   - Add payment method, nạp **$5** (mức tối thiểu).
   - Tắt auto-recharge.
3. Settings → **Limits**: đặt **monthly budget $10** và email cảnh báo ở $5. Lớp này chặn tiền nếu demo công khai bị spam.
4. Settings → **Projects** → Create project `chot`.
5. Trong project `chot`, vào **API keys** → Create new secret key:
   - Owned by: You. Project: `chot`.
   - Permissions: **Restricted**, chỉ bật **Model capabilities → Write**.
   - Copy key **một lần** (dạng `sk-proj-…`), dán vào `.env`.
6. Kiểm tra tên model còn hợp lệ ở https://platform.openai.com/docs/models. Chọn `GEN_MODEL` là model **khác và mạnh hơn** `LLM_MODEL`, ví dụ `gpt-4.1`. Dùng model khác để model sinh dữ liệu không "học tủ" model được chấm.

### 3.2 Nội dung `.env` local

```dotenv
LEDGER_BUILDER=llm
REPLAY_EVENTS_DIR=tests/fixtures/oracle_events   # P5 sẽ đổi sang demo_events

LLM_BASE_URL=                 # để trống = OpenAI chính chủ
LLM_API_KEY=sk-proj-...       # key ở bước 3.1
LLM_MODEL=gpt-4.1-mini

GEN_BASE_URL=
GEN_API_KEY=                  # để trống = dùng LLM_API_KEY
GEN_MODEL=gpt-4.1             # khác LLM_MODEL

DATABASE_URL=                 # để trống — v1 dùng InMemory
CORS_ORIGINS=http://localhost:3000

# Thêm ở P5
MAX_TRANSCRIPT_CHARS=20000
LLM_RATE_LIMIT_PER_HOUR=10
```

### 3.3 Không cần
- Không cần key Anthropic, Supabase hay `DATABASE_URL`.
- **Railway:** dán `LLM_API_KEY` vào **Variables** trên dashboard. Không ghi key vào file nào trong repo.
- **Vercel:** chỉ cần `NEXT_PUBLIC_API_URL=https://api.chot.nashng.dev`. Biến này public, không phải secret.
- **Porkbun:** không cần API key, chỉ thêm 2 bản ghi CNAME bằng tay (xem P6).

### 3.4 Chi phí ước tính
- m01–m10 mỗi cuộc họp 20–30 câu, nên một lần `make eval-llm` dùng chưa tới vài chục nghìn token, khoảng **< $0.05**.
- Cả 2 ngày (P2–P4 khoảng 10 lần chạy + sinh 5 kịch bản) tốn khoảng **< $1**.
- Thêm phần demo công khai, có giới hạn ở P5.

> 🔐 Nếu lỡ dán key vào chat, commit hay screenshot: vào API keys → **Revoke** ngay, rồi tạo key mới.

---

## 4. Prompt Phase 0 — Chạy được trên Windows

```markdown
## Objective
Làm cho `make install / test / lint / dev-api / dev-web / eval-*` chạy được trong Git Bash trên Windows (và vẫn chạy trên Mac/Linux), không phụ thuộc Python hệ thống.

## Context (carry forward — đã chốt, không bàn lại)
- Đọc trước: CLAUDE.md, README.md, Makefile, apps/api/pyproject.toml.
- Máy: Windows 11, Git Bash, có `uv`, `make` (ezwinports), Docker, Node. Python hệ thống là 3.14 — KHÔNG dùng; dự án cần 3.12.
- Makefile hiện dùng `python3` và `apps/api/.venv/bin/python` → hỏng trên Windows (venv ở `Scripts/`).

## Target State
- Makefile dùng uv: `install` = `uv venv --python 3.12 apps/api/.venv` + `uv pip install --python apps/api/.venv -e "apps/api[dev]"` + npm install; các lệnh python khác gọi qua `uv run --project apps/api ...` (hoặc cách uv tương đương chạy được cả 2 OS) thay cho đường dẫn `.venv/bin`.
- `set -a; . ./.env; set +a` giữ nguyên (chạy được trong Git Bash).
- README: thêm mục "Windows" 3 dòng (Git Bash + `winget install ezwinports.make` + uv).

## Scope
- Chỉ sửa Makefile và README.md. KHÔNG sửa code trong apps/.

## Constraints
- Không thêm dependency mới. Không thêm script .ps1 / task runner khác.
- Trả lời tôi bằng tiếng Việt; commit message theo quy ước CLAUDE.md (`chore(make): …`).

## Acceptance Criteria
- [ ] `make install` tạo venv Python 3.12 (`uv run --project apps/api python --version` in 3.12.x)
- [ ] `make test` xanh (54 test) và `make lint` xanh
- [ ] `make eval-keyword` và `make eval-oracle` chạy, oracle 100%
- [ ] `make dev-api` mở được http://localhost:8000/docs

## Skills
- ponytail suốt phase: diff ngắn nhất, không thêm target "để sau".
- Trước commit: `ponytail:ponytail-review` trên diff → `/verify`.

## Action Boundaries
- Làm trước: trình bày diff Makefile dự kiến → CHỜ TÔI DUYỆT.
- Dừng và hỏi trước khi: xoá file, cài thứ ngoài uv/npm.
- KHÔNG git push. Lỗi lặp 3 lần → dừng, báo lỗi + đã thử gì.

## Progress Evidence
✅ sau mỗi bước + output thật của lệnh. Kết thúc: commit, liệt kê lệnh tôi tự chạy lại, rồi DỪNG.
```

---

## 5. Phase 1 — Gold m01–m05 (Nash làm tay, Claude chỉ kiểm tra)

**Nash tự làm** (1–1,5 giờ). Không giao việc gán nhãn cho Claude. Nhãn gold là thứ đo LLM, AI không được tự chấm bài của AI.
1. Đọc `docs/LABELING_GUIDE.md` và ví dụ `data/examples/m00.txt` + `m00.gold.json`.
2. Với mỗi `data/raw/m0X.txt`, copy `data/gold/TEMPLATE.json` thành `data/gold/m0X.json` rồi gán nhãn.
3. **Không mở `data/answer_key/`** trong lúc gán nhãn.

Gán nhãn xong, dán prompt sau với `/model haiku`:

```markdown
## Objective
Kiểm tra định dạng nhãn gold tôi vừa tự gán và đo độ đồng thuận với đáp án.

## Context
- data/gold/m01–m05.json do tôi gán tay theo docs/LABELING_GUIDE.md, khuôn data/gold/TEMPLATE.json.

## Việc cần làm
1. Kiểm tra mỗi file: JSON hợp lệ, đúng field như TEMPLATE.json, `type`/`status` thuộc enum trong apps/api/src/chot/domain/enums.py, mọi `quote` có thật nguyên văn trong data/raw tương ứng.
2. Chạy `make agreement`, tóm tắt các chỗ lệch (CHỐT NHẦM / BỎ SÓT / SAI OWNER / SAI HẠN).
3. Thêm 1 dòng vào docs/EVAL_LOG.md: hệ thống "nhãn Nash vs answer_key".

## Action Boundaries
- CHỈ báo lỗi định dạng và chỗ lệch. KHÔNG tự sửa nhãn, KHÔNG đề xuất nhãn "đúng" — tôi tự quyết theo LABELING_GUIDE.
- Sửa được: docs/EVAL_LOG.md. Commit `eval: agreement gold m01–m05`. Rồi DỪNG.
```

Chỗ nào lệch thì Nash đọc lại guide và tự quyết sửa gold hay giữ. Lệch có lý do là tư liệu tốt cho câu hỏi 3 của Mission 2.

---

## 6. Prompt Phase 2 — Eval LLM lần đầu

```markdown
## Objective
Có số eval thật đầu tiên của pipeline chính (LLM gán sự kiện + luật) và baseline "1 prompt tóm tắt" trên gold m01–m05.

## Context
- Đọc: CLAUDE.md (5 luật vàng + quy trình sửa luật/prompt), docs/DATA_DESIGN.md §4 (metric), docs/EVAL_LOG.md, apps/api/src/chot/eval/run.py.
- .env đã có LLM_API_KEY, LLM_MODEL=gpt-4.1-mini, LEDGER_BUILDER=llm.

## Target State
- `make eval-llm` và `make eval-summary` chạy xong, kết quả lưu ở data/runs/<time>-llm/ và data/runs/<time>-summary/.
- docs/EVAL_LOG.md có 2 dòng mới, điền đủ cột (ghi rõ model).
- README bảng "Kết quả hiện tại": thay dòng "chạy make eval-llm" bằng số thật + thêm dòng summary.
- Một bảng phân loại lỗi của run llm: mỗi lỗi = meeting / item / loại lỗi (chốt nhầm, bỏ sót, sai trạng thái, sai owner, sai hạn, quote không khớp) / câu transcript liên quan / giả thuyết nguyên nhân (prompt hay luật). Ghi vào data/runs/<run>/ERRORS.md (không commit data/runs — chỉ để tôi đọc) và tóm tắt top-5 trong câu trả lời.

## Scope
- KHÔNG sửa prompt, luật hay code ở phase này — chỉ đo và phân loại.

## Constraints
- Mỗi system chạy tối đa 2 lần. Lỗi JSON/schema/API → dừng, chẩn đoán, báo tôi trước khi sửa code.
- Không in API key ra log/terminal.

## Acceptance Criteria
- [ ] Có report.json cho cả 2 run; EVAL_LOG có 2 dòng; README có số thật
- [ ] grounding_tier1 = 100% (nếu không → đây là lỗi nghiêm trọng, báo riêng)
- [ ] Bảng phân loại lỗi đủ cho mọi dòng CHỐT NHẦM và BỎ SÓT

## Skills
- Pipeline lỗi (exception, JSON hỏng, schema reject): `mattpocock-skills:diagnosing-bugs`, không sửa mò.

## Action Boundaries
- Được tự: chạy make eval-*, sửa docs/EVAL_LOG.md + README.md. Commit `eval: first llm + summary run`. Rồi DỪNG.
```

---

## 7. Prompt Phase 3 — Tinh chỉnh prompt (vòng lặp có kỷ luật)

```markdown
## Objective
Giảm tỷ lệ chốt nhầm của pipeline LLM về ≤ 5% trên gold m01–m05 mà không làm tụt supersession recall và grounding. Tối đa 3 vòng.

## Context
- Phase 2 đã xong: đọc docs/EVAL_LOG.md, run llm mới nhất trong data/runs/, bảng lỗi ERRORS.md.
- Đọc lại: CLAUDE.md (5 luật vàng, quy trình sửa luật/prompt), apps/api/src/chot/prompts/extract_events.md, domain/status_rules.py, domain/text.py, docs/LABELING_GUIDE.md, docs/adr/0002 + 0003.
- **Gold m01–m05 theo "Quy ước bổ sung (Nash)" trong LABELING_GUIDE** — lệch với luật/prompt hiện tại ở 4 chỗ, eval sẽ báo BỎ SÓT cho tới khi xử lý:
  1. Phản biện cụ thể → `blocker` (+ `knowledge` nếu là số liệu/ràng buộc). Hiện `object` không sinh mục nào.
  2. Tạm chốt trung gian bị chốt cuối thay → `option · superseded`, kể cả cùng phương án với decision. Hiện phương án được chọn không sinh option.
  3. Chốt rồi bị lật thành hoãn → mọi phương án `option · open`. Hiện deferred không sinh option.
  4. Chủ trì "Ừ." / đồng ý gián tiếp sau một đề xuất → `decision · needs_confirmation`. Hiện "Ừ." là backchannel (domain/text.py).
  Mỗi chỗ: hỏi tôi chọn sửa luật (TDD + oracle 100% — lưu ý answer_key/oracle_events theo quy ước cũ, phải cập nhật cùng) hay chấp nhận làm case thất bại. Đồng thời cập nhật `data/examples/m00.gold.json` (few-shot) cho khớp quy ước 1.

## Quy trình mỗi vòng
1. Chọn 1 nhóm lỗi lớn nhất. Ghi giả thuyết 1–2 câu: lỗi ở **prompt** (LLM gán sai sự kiện) hay **luật** (sự kiện đúng mà trạng thái sai)? Kiểm chứng bằng cách đọc events/<meeting>.json của run.
2. Nếu là prompt: sửa prompts/extract_events.md (giải thích rõ hơn kind, thêm tín hiệu rào đón…) → `make eval-llm`.
3. Nếu là luật: viết test đỏ trong tests/ trước → sửa domain/ → `make test` + `make eval-oracle` (PHẢI 100%) → replay không tốn token:
   `uv run --project apps/api python -m chot.eval.run --system replay --events data/runs/<run>/events --gold data/gold --show-errors`
4. Thêm 1 dòng docs/EVAL_LOG.md (ghi giả thuyết ở cột Ghi chú). Chốt nhầm tăng → revert thay đổi đó.

## Constraints (luật vàng — vi phạm là sai)
- Few-shot CHỈ lấy từ data/examples/m00. KHÔNG chép câu/tình huống từ data/raw m01–m05 vào prompt (đó là bộ test).
- KHÔNG cho LLM trả `status`. KHÔNG nới domain/grounding.py để qua test. Không chắc → needs_confirmation.
- KHÔNG đổi model ở phase này (giữ biến số là prompt).

## Acceptance Criteria
- [ ] Mỗi vòng có 1 dòng EVAL_LOG với giả thuyết + kết quả
- [ ] Chốt nhầm không tăng so với P2; grounding_tier1 = 100%; `make test` + `make eval-oracle` xanh
- [ ] Nếu sau 3 vòng vẫn > 5%: DỪNG, ghi lại lỗi còn lại — đó là "case thất bại" thật cho Mission 2, KHÔNG cố ép

## Skills
- Đầu phase: `mattpocock-skills:grilling` — hỏi vặn tôi về giả thuyết vòng 1 trước khi sửa.
- Đụng luật: `mattpocock-skills:tdd`. Cuối phase: `ponytail:ponytail-review` trên diff prompt/luật.

## Action Boundaries
- Plan mode trước (trình bày giả thuyết vòng 1) → CHỜ TÔI DUYỆT. Sau mỗi vòng: báo số, hỏi tôi có chạy vòng tiếp không.
- Mỗi vòng 1 commit: `feat(prompt): …` hoặc `fix(rules): …` kèm số eval trong message. KHÔNG push.
- Kết thúc: liệt kê run tốt nhất (đường dẫn data/runs/...), lỗi còn lại, rồi DỪNG.
```

---

## 8. Prompt Phase 4 — 5 kịch bản bẫy (m07, m08, m10, m11, m12)

5 kịch bản này phủ được các bẫy khó nhất:

| ID | Bẫy |
|---|---|
| m07 | Tạm chốt không xác nhận lại, owner "ai đó", trộn Anh–Việt |
| m08 | "Thích" ≠ quyết định, yêu cầu khách hàng, "nếu mà" |
| m10 | Đổi ý 3 lần, keyword "chưa chốt", sai tên do ASR |
| m11 | "Thôi khoan" mở lại, tự nhận việc, "thứ X tuần sau" |
| m12 | Người không chủ trì nói "chốt", phản đối rồi khẳng định lại, blocker |

```markdown
## Objective
Sinh 5 transcript bẫy m07, m08, m10, m11, m12 từ data/synthetic/scenarios.json để mở rộng bộ test lên 10 cuộc họp.

## Context
- Đọc: scripts/generate_synthetic.py, apps/api/src/chot/prompts/generate_transcript.md, data/README.md, docs/LABELING_GUIDE.md.
- .env có GEN_MODEL khác LLM_MODEL.

## Target State
- Chạy: `set -a; . ./.env; set +a; uv run --project apps/api python scripts/generate_synthetic.py --only m07 m08 m10 m11 m12 --start-date 2026-10-13`
- Bản nháp ở data/synthetic/drafts/. Với mỗi bản: kiểm tra transcript đúng định dạng parser (`tests/test_parser.py`, docs/DATA_DESIGN.md §1) và bẫy khai báo có thật xuất hiện trong lời thoại. Báo bảng: id / bẫy có xuất hiện không / dòng chứa bẫy / vấn đề.

## Scope
- KHÔNG chép nháp sang data/raw hay data/gold — tôi tự duyệt, sửa và gán nhãn.
- `.gold.json` do script sinh ra chỉ là gợi ý; tôi sẽ gán lại theo LABELING_GUIDE.

## Action Boundaries
- Tối đa 2 lần chạy script. Không sinh thêm kịch bản ngoài 5 id trên. Báo cáo rồi DỪNG.
```

**Nash tự làm** (khoảng 1 giờ):
1. Đọc 5 bản nháp, sửa câu thiếu tự nhiên.
2. Chép sang `data/raw/<id>.txt`.
3. Gán nhãn `data/gold/<id>.json`, có thể tham khảo `.gold.json` nháp nhưng tự quyết.

Xong thì dán prompt ngắn sau:

```markdown
Tôi đã thêm data/raw + data/gold cho m07, m08, m10, m11, m12. Kiểm tra định dạng gold như Phase 1 (không sửa nhãn), rồi chạy `make eval-llm` trên toàn bộ data/gold (10 cuộc họp) với prompt tốt nhất hiện tại. Thêm 1 dòng EVAL_LOG, cập nhật bảng README, liệt kê mọi lỗi theo meeting. Commit `eval: 10 meetings`. Rồi DỪNG.
```

---

## 9. Prompt Phase 5 — Demo công khai: đúng và an toàn

```markdown
## Objective
Chuẩn bị API/web cho demo công khai: transcript mẫu hiển thị kết quả **thật của LLM đã lưu** (không tốn token), transcript mới đi qua LLM với giới hạn độ dài và tần suất.

## Context
- Đọc: apps/api/src/chot/api/deps.py (FallbackBuilder L18, make_builder L32), usecases/build_ledger.py (DirectoryReplayExtractor đọc <dir>/<meeting_id>.json), api/schemas.py (CreateMeetingIn), api/main.py, config.py, apps/api/Dockerfile, apps/web/src/app/page.tsx (nút "Dùng transcript mẫu"), apps/web/public/samples/.
- Run LLM tốt nhất từ P3/P4: data/runs/<run>/events/ (data/runs bị gitignore).

## Target State
- **Trung thực:** copy events của run LLM tốt nhất cho m01–m05 vào `apps/api/demo_events/` (commit), Dockerfile COPY thư mục này. KHÔNG dùng oracle_events cho demo — oracle là đáp án, dùng nó là "làm đẹp" demo.
- `make_builder` khi LEDGER_BUILDER=llm: `FallbackBuilder(RulesLedgerBuilder(DirectoryReplayExtractor(REPLAY_EVENTS_DIR)), llm_builder)` — có events theo meeting_id thì replay, không có thì gọi LLM. Tái dùng class sẵn có, không viết builder mới.
- `MAX_TRANSCRIPT_CHARS` (mặc định 20000): validate trong schema/config → 422/413 với thông báo tiếng Việt rõ ràng.
- Rate limit `LLM_RATE_LIMIT_PER_HOUR` (mặc định 10) theo IP, CHỈ áp cho request thực sự gọi LLM; in-memory, đánh dấu `# ponytail: in-memory, 1 instance — đổi sang Redis nếu scale`. Trả 429 + thông báo tiếng Việt. IP thật sau proxy Railway: uvicorn chạy với `--proxy-headers --forwarded-allow-ips='*'` trong Dockerfile.
- Web: chọn mẫu m01–m05 (copy data/raw vào apps/web/public/samples/, gửi kèm meeting_id), dòng chú thích "Kết quả mẫu là output đã lưu của LLM (gpt-4.1-mini, ngày …), không phải đáp án". Hiển thị lỗi 413/422/429 thân thiện.
- .env.example + config.py thêm 2 biến mới; REPLAY_EVENTS_DIR trỏ `demo_events`.

## Scope
- Chỉ: api/deps.py, api/schemas.py, api/main.py (nếu cần), config.py, Dockerfile, apps/api/demo_events/, apps/web (page + samples + hiển thị lỗi), .env.example, tests.
- KHÔNG sửa domain/, prompts/, luật.

## Constraints
- Không thêm dependency (rate limit tự viết ~15 dòng, stdlib).
- domain/ không import gì mới (luật vàng 4).

## Acceptance Criteria
- [ ] Test: transcript > MAX_TRANSCRIPT_CHARS bị từ chối; request LLM thứ (N+1)/giờ từ cùng IP → 429; meeting_id m01 dùng replay và KHÔNG gọi LLM (client giả đếm số lần gọi)
- [ ] `make test` + `make lint` xanh; `make eval-oracle` vẫn 100%
- [ ] `docker build apps/api` + `docker run -p 8000:8000 --env-file .env` → /health 200, POST m01 trả ledger không tốn token

## Skills
- Plan: `mattpocock-skills:grilling` (hỏi tôi về ranh giới replay/LLM, cách lấy IP, thông báo lỗi).
- Code: ponytail + `mattpocock-skills:tdd` (viết 3 test acceptance trước).
- Trước commit: `ponytail:ponytail-review` → `mattpocock-skills:code-review` → `/security-review` (endpoint public, chi phí, lộ key).

## Action Boundaries
- Plan mode trước → CHỜ DUYỆT. Lỗi lặp 3 lần → dừng. KHÔNG push.
- Kết thúc: commit `feat(api): demo replay + limits`, hướng dẫn tôi tự test bằng web local, rồi DỪNG.
```

---

## 10. Prompt Phase 6 — Deploy lên nashng.dev

```markdown
## Objective
Chuẩn bị deploy: web → https://chot.nashng.dev (Vercel), API → https://api.chot.nashng.dev (Railway, Docker), và script hướng dẫn tôi tự làm trên dashboard.

## Context
- Đọc: docs/ARCHITECTURE.md §6, apps/api/Dockerfile (đã đọc $PORT), apps/web/Dockerfile, apps/web/next.config.ts (output standalone), apps/web/src/lib/api.ts (NEXT_PUBLIC_API_URL), config.py (CORS_ORIGINS).
- DNS của nashng.dev quản lý ở **Porkbun**. Không có DB (InMemory — restart là mất danh sách cuộc họp, chấp nhận cho demo).

## Target State
- Báo cáo `ponytail:ponytail-audit` + `/security-review` ngắn dạng bảng (vấn đề / mức / file / đề xuất); sửa mục mức cao sau khi tôi đồng ý.
- Kiểm tra local: build cả 2 image, chạy web image trỏ vào api image, luồng dán transcript chạy.
- docs/ARCHITECTURE.md §6 cập nhật: Render/Supabase → Railway + nashng.dev, không DB.
- `mattpocock-skills:wizard` tạo `scripts/deploy_wizard.sh` hướng dẫn TỪNG BƯỚC (script chỉ in hướng dẫn + chờ tôi Enter + kiểm tra bằng curl/nslookup, KHÔNG gọi API của dịch vụ):
  1. Railway: New Project → Deploy from GitHub repo → Root Directory `apps/api` (Dockerfile) → Variables: LEDGER_BUILDER=llm, REPLAY_EVENTS_DIR=demo_events, LLM_API_KEY, LLM_MODEL, MAX_TRANSCRIPT_CHARS, LLM_RATE_LIMIT_PER_HOUR, CORS_ORIGINS=https://chot.nashng.dev → Settings → Networking → Custom Domain `api.chot.nashng.dev` → ghi lại CNAME target Railway đưa.
  2. Vercel: Add New Project → import repo → Root Directory `apps/web` → Env `NEXT_PUBLIC_API_URL=https://api.chot.nashng.dev` → Deploy → Settings → Domains → thêm `chot.nashng.dev` → ghi lại giá trị CNAME Vercel hiển thị.
  3. Porkbun: Domain Management → nashng.dev → DNS → thêm 2 bản ghi CNAME: host `chot` → giá trị Vercel; host `api.chot` → giá trị Railway (TTL 600). Không đụng bản ghi cũ.
  4. Chờ DNS + SSL (5–30'), kiểm tra: `curl https://api.chot.nashng.dev/health`, mở https://chot.nashng.dev ở cửa sổ ẩn danh, bấm mẫu m01, dán 1 transcript mới.
- Ghi chú chi phí: Railway hết trial cần gói Hobby (xem railway.com/pricing); Vercel Hobby miễn phí.

## Scope
- Được sửa: Dockerfile, docs/ARCHITECTURE.md, README (mục Deploy), scripts/deploy_wizard.sh, code sửa lỗi bảo mật đã duyệt.
- KHÔNG tạo tài khoản, project, domain, DNS record, secret trên bất kỳ dịch vụ nào; KHÔNG deploy; KHÔNG dùng MCP Vercel/GitHub để thay đổi gì. Tôi tự làm theo wizard.

## Acceptance Criteria
- [ ] 2 image build + chạy local, /health 200, CORS chỉ cho origin đã khai báo
- [ ] Không còn mục bảo mật mức cao chưa xử lý (hoặc tôi đã chấp nhận bằng văn bản)
- [ ] `bash scripts/deploy_wizard.sh` chạy được trong Git Bash

## Action Boundaries
- Báo cáo audit trước → chờ tôi chọn mục sửa. Dừng và hỏi trước mọi thao tác ngoài repo. Lỗi lặp 3 lần → dừng.
- Kết thúc: commit `chore(deploy): …`, danh sách việc tôi làm trên dashboard theo thứ tự, rồi DỪNG.
```

---

## 11. Prompt Phase 7 — Tài liệu nộp bài

```markdown
## Objective
Soạn bản nháp đầy đủ cho bài nộp Mission 2: README, docs/MISSION2.md (3 câu hỏi + bộ test case), docs/VIDEO_SCRIPT.md. Mọi con số lấy từ run thật.

## Context
- Đề Mission 2 yêu cầu: core loop Transcript → diễn biến → cấu trúc → bằng chứng; nhóm quyết định / công việc / vướng mắc / yêu cầu–phản hồi / chưa chốt / evidence; bắt buộc tình huống "ý kiến ban đầu thay đổi → giữ kết luận cuối"; ≥5 test case gồm ≥1 làm tốt, ≥1 khó/mơ hồ, ≥1 chưa xử lý tốt/thất bại; format: **Kỳ vọng → Kết quả thực tế → Đạt/Chưa đạt → Điều học được**.
- Đọc: docs/PRD.md (Mission 1, đặc biệt §5 kế hoạch và §6 Q1–Q3), docs/EVAL_LOG.md, git log (từ commit `314420f`), data/runs/<run tốt nhất>/report.json + ledgers/ + events/, data/gold, docs/adr/.

## Target State
1. **docs/MISSION2.md**
   - Bảng ánh xạ yêu cầu đề → nơi trong sản phẩm (ItemType/Status, file, màn hình). Ghi thẳng: "chưa chốt" = status needs_confirmation/deferred/open + type open_question.
   - 3 câu hỏi bắt buộc:
     - Q1 phần quan trọng nhất + vì sao chứng minh được tính khả thi (dẫn số chốt nhầm LLM vs keyword vs summary).
     - Q2 thay đổi so với Mission 1: đối chiếu PRD §5 (kế hoạch 3 ngày, "tách chủ đề", grounding tầng 2…) với thứ thực tế đã làm/bỏ/đổi qua git log + EVAL_LOG; mỗi thay đổi kèm "điều gì khiến đổi". Mục nào không chắc → đánh dấu [Nash xác nhận].
     - Q3 loại thông tin dễ sai nhất (lấy từ thống kê lỗi thật theo nhóm) + các lớp chống bịa: LLM chỉ gán sự kiện, luật quyết trạng thái, grounding tầng 1 chặn cứng, owner ngoài danh sách bị bỏ, không chắc → Cần xác nhận, màn duyệt + publish bị chặn.
   - **Bộ test ≥7 case**, mỗi case 1 khối theo đúng format đề, có: transcript + dòng (u0xx), kỳ vọng (từ gold), kết quả thực tế (từ ledger của run, kèm quote), Đạt/Chưa đạt, Điều học được. Bắt buộc: A→B (m01 hoặc tương đương), đổi ý 3 lần (m10), tạm chốt không xác nhận, "thôi khoan", yêu cầu/phản hồi khách, ≥1 mơ hồ, ≥1 THẤT BẠI THẬT lấy từ lỗi còn lại của run (không dàn dựng). Thêm bảng tổng hợp + so 3 hệ thống.
   - Mục "Hạn chế đã biết" thẳng thắn: InMemory, bộ test nhỏ do 1 người gán, dữ liệu tổng hợp, chưa có ASR, server nước ngoài (Luật 91/2025), rate limit 1 instance.
2. **README.md**: link demo https://chot.nashng.dev ở đầu, cập nhật bảng kết quả, mục chạy local (Windows Git Bash + Mac/Linux + Docker), link docs/MISSION2.md, bỏ checklist "Kế hoạch 2 ngày" cũ (chuyển thành "Đã làm / Chưa làm").
3. **docs/VIDEO_SCRIPT.md**: ≤5 phút, 5 cảnh có mốc giờ: Bài toán (0:00–0:40) → Phần chọn chứng minh (0:40–1:20) → Demo m01 A→B + evidence (1:20–2:50) → Tình huống khó + case thất bại (2:50–4:00) → Hạn chế + bước tiếp (4:00–4:50). Mỗi cảnh: lời thoại + màn hình cần quay.
4. CLAUDE.md mục "Trạng thái hiện tại" + "Việc tiếp theo" cập nhật.
5. Quét secret: `git log -p --all | grep -nE "sk-[A-Za-z0-9_-]{20,}|sk-proj-"` và kiểm tra .env không được track.

## Constraints
- Văn tiếng Việt tự nhiên, ngắn, không sáo rỗng. Mọi số liệu phải trích được từ file trong repo/run — không ước lượng. Không che lỗi.

## Skills
- `anthropic-skills:vietnamese` khi viết; `anthropic-skills:humanizer` rà lại MISSION2.md và VIDEO_SCRIPT.md.

## Action Boundaries
- Chỉ sửa: README.md, CLAUDE.md, docs/. Commit `docs: mission 2 submission draft`. KHÔNG push. Rồi DỪNG, liệt kê các chỗ [Nash xác nhận].
```

---

## 12. Prompt Phase 8 — Review cuối (session mới, `/model opus`, `/effort high`)

```markdown
Review toàn bộ thay đổi từ commit 314420f đến HEAD so với CLAUDE.md (5 luật vàng), yêu cầu Mission 2 (trong docs/MISSION2.md) và docs/DATA_DESIGN.md.
Chỉ đọc, KHÔNG sửa file.
Ưu tiên kiểm tra:
1. Vi phạm luật vàng: LLM trả status, nới grounding, few-shot lấy từ data/raw/gold, domain import adapter.
2. Demo dùng oracle/answer_key thay vì output LLM thật.
3. Lộ API key (code, git history, log, Dockerfile, NEXT_PUBLIC_*), rate limit bypass, transcript quá dài.
4. Số liệu trong README/MISSION2 không khớp report.json.
5. Test case thiếu format "Kỳ vọng → Kết quả thực tế → Đạt/Chưa đạt → Điều học được".
Trả về bảng: vấn đề / mức độ (cao-trung-thấp) / file:dòng / bằng chứng / đề xuất. Không chắc thì ghi [chưa chắc].
Skills: `mattpocock-skills:code-review` + `ponytail:ponytail-review` + `/security-review`. Gộp một bảng.
```

## 13. Prompt khi muốn đổi thiết kế

```markdown
Tôi muốn thay đổi: <mô tả>.
Trước khi code: (1) liệt kê docs, luật, prompt, endpoint, test bị ảnh hưởng; (2) đề xuất cập nhật docs (và ADR mới trong docs/adr/ nếu là quyết định kiến trúc); (3) chờ tôi đồng ý.
Skills: `mattpocock-skills:grilling` hỏi vặn thay đổi trước; `mattpocock-skills:domain-modeling` khi cần ghi ADR.
Sau khi đồng ý: sửa docs + code cùng commit, chạy `make test` + `make lint` + `make eval-oracle`, rồi DỪNG.
```

---

## 14. Checklist nộp bài (Nash tự tick)

- [ ] `make test`, `make lint`, `make eval-oracle` xanh. EVAL_LOG có đủ các dòng llm, summary, 10 meetings.
- [ ] `.env` không bị track: `git ls-files | grep -c "^.env$"` phải ra 0. Quét secret ở P7 sạch.
- [ ] Repo `HoNguyen17/Chot_ai` để **Public** (Settings → General → Danger Zone → Change visibility).
- [ ] https://chot.nashng.dev mở được ở cửa sổ ẩn danh. Mẫu m01 hiện MoMo = Đã chốt, VNPay = Bị thay thế, có quote. Dán transcript mới chạy được.
- [ ] OpenAI đã đặt budget limit.
- [ ] `docs/MISSION2.md` có ≥5 test case, gồm ≥1 đạt, ≥1 mơ hồ, ≥1 thất bại thật, và 3 câu trả lời (không còn chỗ [Nash xác nhận]).
- [ ] Video ≤5 phút theo `docs/VIDEO_SCRIPT.md`, link để public/unlisted, gắn vào README.
- [ ] Sau khi chấm xong, có thể hạ budget OpenAI hoặc revoke key.
