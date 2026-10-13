# Chốt

**Biên bản họp có bằng chứng cho SME Việt Nam.** Dán transcript → Chốt tìm ra điều gì *thật sự đã chốt*, ai làm gì, hạn nào, điều gì còn treo. Mỗi dòng trỏ về đúng câu nói gốc.

> Đầu họp đề xuất VNPay, giữa họp "tạm thời đi MoMo", cuối họp "chốt MoMo, VNPay để phase 2" → Chốt ghi **MoMo = Đã chốt**, **VNPay = Bị thay thế**, không có mục "tạm thời" nào bị ghi thành quyết định.

## Chạy thử trong 2 phút (không cần API key)

```bash
cp .env.example .env          # LEDGER_BUILDER=replay: demo m01–m05 bằng sự kiện có sẵn
make install                  # Python venv + npm
make test                     # 54 test, < 1 giây
make dev-api                  # terminal 1 → http://localhost:8000/docs
make dev-web                  # terminal 2 → http://localhost:3000 → "Dùng transcript mẫu"
```

**Windows:** chạy trong **Git Bash** (không dùng PowerShell). Cài một lần: `winget install ezwinports.make` và [uv](https://docs.astral.sh/uv/) — uv tự tải Python 3.12, không cần Python hệ thống.

Hoặc `make up` để chạy db + api + web bằng Docker.

Chạy pipeline thật: điền `LLM_*` trong `.env`, đặt `LEDGER_BUILDER=llm`.

## Cấu trúc

```
chot/
├── CLAUDE.md                 hướng dẫn cho Claude Code (đọc trước khi code)
├── docs/
│   ├── PRD.md                vấn đề, người dùng, giải pháp, rủi ro, 3 câu trả lời
│   ├── ARCHITECTURE.md       clean architecture, pipeline, API, deploy, lộ trình mở rộng
│   ├── DATA_DESIGN.md        transcript → events → ledger, luật trạng thái, DB, metric
│   ├── DESIGN_SYSTEM.md      token, component, màn hình, câu chữ
│   ├── LABELING_GUIDE.md     cách gán nhãn bộ test
│   ├── EVAL_LOG.md           nhật ký kết quả eval
│   └── adr/                  các quyết định kiến trúc và lý do
├── data/                     transcript, nhãn, đáp án, kịch bản tổng hợp (xem data/README.md)
├── apps/
│   ├── api/                  FastAPI + pipeline + eval (Python)
│   │   └── src/chot/
│   │       ├── domain/       luật thuần: models, status_rules, grounding, dates, text
│   │       ├── usecases/     điều phối: build_ledger, meetings, ports
│   │       ├── adapters/     parsing · llm · baselines · persistence · export
│   │       ├── api/          FastAPI routes + composition root
│   │       ├── eval/         metrics + CLI
│   │       └── prompts/      prompt LLM (.md)
│   └── web/                  Next.js: upload + màn hình duyệt
├── db/migrations/            SQL cho Postgres / Supabase
├── scripts/                  sinh dữ liệu tổng hợp
├── docker-compose.yml
└── Makefile                  `make help`
```

## Kế hoạch 2 ngày

**Ngày 1 — dữ liệu & lõi**
- [ ] Đọc `docs/LABELING_GUIDE.md` + ví dụ `data/examples/m00`
- [ ] Tự gán nhãn `data/gold/m01–m05.json` → `make agreement`
- [ ] `make synth` → duyệt 10–15 bản nháp → chép sang `data/raw` + `data/gold`
- [ ] Điền `LLM_*` → `make eval-llm` → chỉnh `prompts/extract_events.md` tới khi chốt nhầm ≤ 5%
- [ ] `make eval-summary` để có baseline thứ hai → ghi `docs/EVAL_LOG.md`

**Ngày 2 — dùng được & deploy**
- [ ] `PostgresRepository` + Supabase
- [ ] Chỉnh màn duyệt, thử luồng duyệt → xuất bản → export
- [ ] Deploy: web → Vercel, api → Render/Railway, db → Supabase (`docs/ARCHITECTURE.md#6-deploy`)
- [ ] README cập nhật số eval cuối cùng

## Kết quả hiện tại

| Hệ thống | Bộ test | Chốt nhầm ⭐ | Phương án cũ được gắn "bị thay thế" |
|---|---|---|---|
| Lọc keyword | answer_key m01–m05 | 66,7% | 0% |
| Luật + sự kiện chuẩn | answer_key m01–m05 | 0% | 100% |
| LLM + luật (gpt-4.1-mini) — trước tinh chỉnh | gold m01–m25 | 17,6% | 42,1% |
| LLM + luật (gpt-4.1-mini) — sau P3 (prompt + luật) | gold m01–m25 | **0%** | 78,9% |
| 1 prompt tóm tắt (gpt-4.1-mini) | gold m01–m25 | 54,3% | 0% |

Dòng thứ hai chỉ chứng minh luật khớp hướng dẫn gán nhãn; điểm thật của sản phẩm là dòng thứ ba. Dòng LLM đo trên 25 cuộc họp (5 thật + 20 kịch bản bẫy), gold theo quy ước của Nash (`docs/LABELING_GUIDE.md`, quy tắc 1–13) — một phần lỗi là quy ước chưa có trong luật/prompt. Dòng "sau P3" là sự kiện của lần chạy LLM thật gần nhất đi qua luật cuối (replay); lần chạy đầu-cuối trước vòng luật cuối là 4,8%. Chi tiết: [docs/EVAL_LOG.md](docs/EVAL_LOG.md).
