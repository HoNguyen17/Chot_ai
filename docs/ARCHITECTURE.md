# Kiến trúc — Chốt

> Một câu: **LLM gán nhãn, code quyết định, người duyệt chốt.** Mọi thứ khác là adapter thay được.

## 1. Bức tranh tổng thể

```mermaid
flowchart LR
  U["👤 PM / trưởng nhóm"] --> WEB["Next.js<br/>Upload · Duyệt · Export"]
  WEB -->|REST JSON| API["FastAPI<br/>MeetingService"]
  API --> PIPE["Pipeline<br/>parse → extract → rules → grounding"]
  PIPE -->|1 lần gọi / cuộc họp| LLM["LLM<br/>OpenAI-compatible"]
  API --> DB[("PostgreSQL<br/>Supabase")]
  API --> EXP["Export<br/>Biên bản .md · Task .csv · Ledger .json"]
```

| Thành phần | Công nghệ | Nơi chạy (dev → prod) |
|---|---|---|
| Web | Next.js 16 (App Router), TypeScript, CSS tokens | `npm run dev` → **Vercel** |
| API | FastAPI, Pydantic v2, Python 3.12 | `uvicorn` → **Render / Railway** (Docker) |
| DB | PostgreSQL 16 + pgvector | Docker → **Supabase** |
| LLM | Bất kỳ endpoint OpenAI-compatible | OpenAI / Gemini / OpenRouter → tự host Qwen/Gemma bằng vLLM |
| Eval | Python CLI `chot.eval.run` | Chạy local, không deploy |

## 2. Clean Architecture

```mermaid
flowchart TB
  subgraph L4["Frameworks & drivers — api/, Next.js, Postgres"]
    direction LR
    fa["FastAPI routes<br/>api/main.py"]
    deps["Composition root<br/>api/deps.py"]
  end
  subgraph L3["Adapters — adapters/"]
    direction LR
    parse["parsing/<br/>.txt → Transcript"]
    llm["llm/<br/>client + event_extractor"]
    base["baselines/<br/>keyword · summary"]
    per["persistence/<br/>memory · postgres"]
    exp["export/<br/>md · csv · json"]
  end
  subgraph L2["Use cases — usecases/"]
    direction LR
    uc1["RulesLedgerBuilder"]
    uc2["MeetingService<br/>process · review · publish"]
  end
  subgraph L1["Domain — domain/ (thuần Python, không I/O)"]
    direction LR
    m["models · enums"]
    r["status_rules"]
    g["grounding"]
    t["text · dates"]
  end
  L4 --> L3 --> L2 --> L1
```

**Luật phụ thuộc:** mũi tên chỉ đi vào trong. `domain/` không import gì ngoài stdlib + pydantic. `usecases/` chỉ biết các *port* trong `usecases/ports.py`. Chỉ `api/deps.py` được nối adapter cụ thể vào use case.

**Hệ quả có lợi:** đổi LLM (OpenAI → Qwen tự host) = đổi `.env`; đổi DB = thêm 1 adapter; luật chốt test được không cần mạng (54 test chạy < 1 giây).

## 3. Pipeline xử lý một cuộc họp

```mermaid
sequenceDiagram
  autonumber
  participant W as Web
  participant S as MeetingService
  participant P as Parser
  participant X as LLMEventExtractor
  participant R as status_rules
  participant G as grounding
  W->>S: POST /meetings (transcript)
  S->>P: parse_transcript()
  P-->>S: Transcript (u001…, người tham gia, chủ trì)
  S->>X: extract(transcript)
  X-->>S: threads + events (propose/agree/assign…, có quote)
  S->>R: build_ledger(events)
  R-->>S: Ledger (status suy từ chuỗi sự kiện)
  S->>G: apply_grounding()
  G-->>S: Ledger đã kiểm (bỏ quote bịa, hạ FINAL sai)
  S-->>W: Meeting + Ledger (mục "Cần xác nhận" lên đầu)
  W->>S: PATCH item (duyệt / sửa)
  W->>S: POST publish (chặn nếu còn mục chưa duyệt)
```

| Bước | Ai làm | Vì sao không giao cho LLM / vì sao giao |
|---|---|---|
| Parse | Code | Định dạng cố định, cần ID câu ổn định cho trích dẫn |
| Tách chủ đề + gán sự kiện | **LLM** | Cần hiểu ngữ nghĩa, ngữ dụng tiếng Việt |
| Suy trạng thái cuối | **Code** (`status_rules.py`) | Phải dễ đoán, test được, không đổi khi đổi model — [ADR-0002](adr/0002-llm-labels-code-decides.md) |
| Grounding 2 tầng | **Code** (`grounding.py`) | String match + luật ngữ cảnh, chặn cứng |
| Duyệt | **Người** | Chịu trách nhiệm cuối cùng; dữ liệu sửa = dữ liệu eval |

## 4. Các "builder" (cùng interface `LedgerBuilder`)

| `LEDGER_BUILDER` | Làm gì | Khi nào dùng |
|---|---|---|
| `keyword` | Câu có "chốt/thống nhất/quyết định/đồng ý" → Đã chốt | Baseline để so sánh (cố tình ngây thơ) |
| `summary` (chỉ eval) | 1 prompt "liệt kê quyết định + action items" | Baseline giống đa số tutorial/sản phẩm |
| `replay` | Luật chạy trên sự kiện đã lưu, thiếu thì rơi về keyword | Demo m01–m05 không cần key; sửa luật không tốn token |
| `llm` | LLM gán sự kiện → luật → grounding | **Pipeline chính** |

## 5. API

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | Phiên bản + builder đang dùng |
| POST | `/meetings` | `{transcript_text, meeting_id?}` → xử lý và trả Ledger |
| GET | `/meetings` | Danh sách cuộc họp |
| GET | `/meetings/{id}` | Transcript + Ledger + trạng thái duyệt |
| PATCH | `/meetings/{id}/items/{item_id}` | Sửa `status/owner/deadline/content/decided_by` hoặc `approved` |
| POST | `/meetings/{id}/publish` | 409 nếu còn mục "Cần xác nhận" chưa duyệt |
| GET | `/meetings/{id}/export?format=md\|csv\|json` | Biên bản / task list / ledger |

OpenAPI tự sinh tại `http://localhost:8000/docs`.

## 6. Deploy

```mermaid
flowchart LR
  GH["GitHub repo"] -->|root: apps/web| V["Vercel<br/>NEXT_PUBLIC_API_URL"]
  GH -->|Dockerfile: apps/api| RD["Render / Railway<br/>LLM_*, DATABASE_URL, CORS_ORIGINS"]
  RD --> SB[("Supabase Postgres<br/>chạy db/migrations/001_init.sql")]
  RD --> L["LLM API"]
  V -->|HTTPS| RD
```

1. **Supabase:** tạo project → SQL editor → chạy `db/migrations/001_init.sql` → lấy connection string (`?sslmode=require`).
2. **API (Render/Railway):** New service từ repo, Docker, root `apps/api`. Env: `LEDGER_BUILDER=llm`, `LLM_*`, `DATABASE_URL`, `CORS_ORIGINS=https://<app>.vercel.app`.
3. **Web (Vercel):** Import repo, Root Directory = `apps/web`. Env: `NEXT_PUBLIC_API_URL=https://<api>.onrender.com`.

> **Vì sao API không đặt trên Vercel?** Một cuộc họp 90 phút có thể mất 20–60 giây gọi LLM; serverless function dễ vượt giới hạn thời gian. Khi cần chạy nền: thêm hàng đợi (Inngest / Celery + Redis) như một adapter mới.
>
> **Lưu ý dữ liệu:** Vercel, Render, Supabase và LLM API quốc tế đặt server ở nước ngoài → theo Luật 91/2025/QH15 đây là chuyển dữ liệu ra nước ngoài. Chỉ dùng cho demo / pilot có consent. Bán cho khách thật: host tại VN + model tự host (xem [PRD §4](PRD.md#4-quyết-định--rủi-ro)).

## 7. Lộ trình mở rộng — cắm vào đâu?

| Giai đoạn | Thêm gì | Cắm vào | Không phải sửa |
|---|---|---|---|
| **v1 (2–3 ngày)** | Lõi Ledger + eval + màn duyệt | — | — |
| **Pilot** | `PostgresRepository`, đăng nhập (Supabase Auth), chạy nền | `adapters/persistence/postgres.py`, `api/deps.py` | domain, usecases |
| **v2** | Ledger xuyên cuộc họp: `series_id`, việc treo → brief kỳ sau, tìm kiếm pgvector + `bge-m3` | `usecases/brief.py` mới, bảng `meeting_series`, cột `items.embedding` (đã có) | status_rules |
| **v3** | ASR tiếng Việt (PhoWhisper / API trong nước) | `apps/asr/` (service mới) → xuất đúng định dạng transcript | toàn bộ pipeline |
| **v3** | Tích hợp Jira / Sheets / Base.vn | `adapters/export/<tool>.py` | domain |
| **v3** | Model tự host (Qwen3.6-27B / Gemma 4 31B qua vLLM) | `.env` (`LLM_BASE_URL`) | code |

Định dạng transcript là "hợp đồng" giữa ASR và pipeline: bất cứ nguồn nào (upload, ASR, bot) chỉ cần xuất đúng định dạng ở [DATA_DESIGN §1](DATA_DESIGN.md#1-transcript).
