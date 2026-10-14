# Chốt

**Demo: https://chot.nashng.dev** · Bài nộp Mission 2: [docs/MISSION2.md](docs/MISSION2.md) · Kịch bản video: [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md)

**Biên bản họp có bằng chứng cho SME Việt Nam.** Dán transcript → Chốt tìm ra điều gì *thật sự đã chốt*, ai làm gì, hạn nào, điều gì còn treo. Mỗi dòng trỏ về đúng câu nói gốc.

> Đầu họp đề xuất VNPay, giữa họp "tạm thời đi MoMo", cuối họp "chốt MoMo, VNPay để phase 2" → Chốt ghi **MoMo = Đã chốt**, **VNPay = Bị thay thế**, không có mục "tạm thời" nào bị ghi thành quyết định.

Trên demo, chọn "Dùng transcript mẫu…" (m01–m05): kết quả là sự kiện của một lần gọi LLM thật (`apps/api/demo_events/`) chạy qua luật hiện tại, không tốn token. Transcript mới thì gọi LLM, có giới hạn 20.000 ký tự và số lượt mỗi giờ.

## Kết quả

25 cuộc họp có cài bẫy (m01–m25), nhãn gold của Nash, cùng model gpt-4.1-mini.

| Hệ thống | Chốt nhầm ⭐ | Phương án cũ được gắn "bị thay thế" | Precision / Recall mục |
|---|---|---|---|
| Lọc keyword | 57,6% (19/33) | 0% | 87,5% / 20,0% |
| 1 prompt tóm tắt | 54,3% (25/46) | 0% | 81,5% / 33,7% |
| Chốt (LLM gán sự kiện + luật), chạy đầu-cuối | 4,8% (1/21) | 78,9% | 73,8% / 51,7% |
| Chốt, cùng sự kiện qua luật hiện tại (replay) | **0% (0/20)** | 78,9% | 73,8% / 51,7% |

"Chốt nhầm" = trong các mục hệ thống ghi "Đã chốt", tỷ lệ mục thật ra chưa chốt. Mục tiêu ≤ 5%. Lỗi duy nhất của lần chạy đầu-cuối là LLM coi "Ừ." là đồng ý; luật mới chặn lỗi này, dòng cuối là cùng sự kiện đó chạy lại. Recall còn thấp: vướng mắc chỉ bắt được 7/74. Chi tiết, test case và lỗi còn lại: [docs/MISSION2.md](docs/MISSION2.md) · lịch sử từng lần đo: [docs/EVAL_LOG.md](docs/EVAL_LOG.md).

## Chạy local (không cần API key)

Cần: [uv](https://docs.astral.sh/uv/) (tự tải Python 3.12), Node 20+, `make`.

**Mac / Linux**

```bash
cp .env.example .env    # LEDGER_BUILDER=replay: m01–m05 dùng sự kiện LLM đã lưu
make install            # venv Python + npm
make test               # 74 test, < 1 giây
make dev-api            # terminal 1 → http://localhost:8000/docs
make dev-web            # terminal 2 → http://localhost:3000 → "Dùng transcript mẫu…"
```

**Windows:** chạy đúng các lệnh trên trong **Git Bash** (không dùng PowerShell). Cài `make` một lần:

```bash
winget install ezwinports.make
```

**Docker**

```bash
cp .env.example .env
make up                 # api + web bằng docker compose
```

Chạy pipeline thật: điền `LLM_*` trong `.env`, đặt `LEDGER_BUILDER=llm`. Đo lại: `make eval-llm`, `make eval-summary`, `make eval-keyword` (xem `make help`).

## Đã làm / Chưa làm

**Đã làm**
- Pipeline: transcript → sự kiện (LLM) → Decision Ledger (luật) → grounding chặn trích dẫn không khớp.
- 25 transcript có bẫy + nhãn gold + 13 quy ước gán nhãn ([LABELING_GUIDE](docs/LABELING_GUIDE.md)).
- Eval so với 2 baseline (keyword, tóm tắt); 3 vòng tinh chỉnh prompt/luật, ghi trong [EVAL_LOG](docs/EVAL_LOG.md).
- Màn duyệt: khoá xuất bản khi còn mục "Cần xác nhận"; xuất biên bản .md, task .csv, ledger .json.
- Deploy demo công khai, có giới hạn ký tự và rate limit.

**Chưa làm**
- Lưu trữ lâu dài: `PostgresRepository` mới là khung, đang lưu trong RAM.
- Bắt vướng mắc và quyết định nằm trong câu giao việc (xem case 8, 10 trong MISSION2).
- Người chấm grounding tầng 2; người gán nhãn thứ hai.
- ASR / audio, bot vào họp, tích hợp Jira/Notion, đăng nhập, ledger xuyên cuộc họp.

## Cấu trúc

```
chot/
├── CLAUDE.md                 hướng dẫn cho Claude Code (đọc trước khi code)
├── docs/
│   ├── MISSION2.md           bài nộp Mission 2: ánh xạ yêu cầu, 3 câu hỏi, test case, hạn chế
│   ├── VIDEO_SCRIPT.md       kịch bản video demo
│   ├── PRD.md                Mission 1: vấn đề, người dùng, giải pháp, rủi ro
│   ├── ARCHITECTURE.md       clean architecture, pipeline, API, deploy, lộ trình mở rộng
│   ├── DATA_DESIGN.md        transcript → events → ledger, luật trạng thái, DB, metric
│   ├── DESIGN_SYSTEM.md      token, component, màn hình, câu chữ
│   ├── LABELING_GUIDE.md     cách gán nhãn bộ test
│   ├── EVAL_LOG.md           nhật ký kết quả eval
│   └── adr/                  các quyết định kiến trúc và lý do
├── data/                     transcript, nhãn, đáp án, kịch bản tổng hợp (xem data/README.md)
├── apps/
│   ├── api/                  FastAPI + pipeline + eval (Python)
│   │   ├── demo_events/      sự kiện LLM thật của m01–m05, dùng cho demo
│   │   └── src/chot/
│   │       ├── domain/       luật thuần: models, status_rules, grounding, dates, text
│   │       ├── usecases/     điều phối: build_ledger, meetings, ports
│   │       ├── adapters/     parsing · llm · baselines · persistence · export
│   │       ├── api/          FastAPI routes + composition root
│   │       ├── eval/         metrics + CLI
│   │       └── prompts/      prompt LLM (.md)
│   └── web/                  Next.js: upload + màn hình duyệt
├── db/migrations/            SQL cho Postgres / Supabase
├── scripts/                  sinh dữ liệu tổng hợp, wizard deploy
├── docker-compose.yml
└── Makefile                  `make help`
```

## Deploy

Web: **https://chot.nashng.dev** (Vercel) · API: **https://api.chot.nashng.dev** (Railway, Docker). Không có DB — lưu trong RAM, restart là mất.

```bash
bash scripts/deploy_wizard.sh
```

Wizard chỉ in hướng dẫn từng bước trên dashboard và kiểm tra bằng curl/nslookup, không tự tạo gì trên dịch vụ nào. Chi tiết và biến môi trường: [docs/ARCHITECTURE.md §6](docs/ARCHITECTURE.md#6-deploy).
**Chi phí:** Vercel Hobby miễn phí. Railway hết trial thì cần gói Hobby (https://railway.com/pricing). LLM tính theo token — đặt budget tháng ở OpenAI project.
