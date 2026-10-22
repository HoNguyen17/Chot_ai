# Mission 3 · Chốt: bản nộp

> Demo: **https://chot.nashng.dev/s/mau-chot-m01-m05**. Đây là nhóm họp mẫu, chỉ xem: 5 buổi m01–m05 chạy lại sự kiện của một lần gọi LLM thật qua bộ luật M3, không cần key.
> Số liệu lấy từ `data/runs/` (không commit) và [EVAL_LOG.md](EVAL_LOG.md). Bốn run tổng kết dưới đây chấm lại sự kiện LLM đã lưu bằng luật và metrics hiện tại (replay, 0 token):
> - `20261022-135049-replay-p8-m2-short`: M2, m01–m25, sự kiện của `20261021-142711-llm-m2`
> - `20261022-135050-replay-p8-m3-short`: M3, m01–m25, sự kiện của `20261022-121440-llm-m3-c100-r2b`
> - `20261022-135052-replay-p8-m2-long`: M2, L1–L4, sự kiện của `20261021-143047-llm-m2-long`
> - `20261022-135053-replay-p8-m3-long`: M3, L1–L4, sự kiện của `20261021-153854-llm-m3-long-c100-r2`
>
> Model: gpt-4.1-mini ở mọi run.

## 1. Đề yêu cầu gì → nằm ở đâu trong sản phẩm

| Yêu cầu | Trong Chốt | Ở đâu |
|---|---|---|
| Họp dài (150–300 câu) | Extractor hai lượt. Lượt 1 dựng **bản đồ chủ đề** cho cả buổi. Lượt 2 gán sự kiện theo đoạn 100 câu, kèm 10 câu ngữ cảnh chỉ đọc, các đoạn chạy song song. Họp ≤ 100 câu vẫn chỉ 1 lần gọi như M2 | `adapters/llm/topic_mapper.py`, `domain/chunking.py`, `prompts/map_topics.md` |
| Chủ đề bị cắt rồi quay lại | Mọi đoạn dùng chung bản đồ chủ đề, nên câu ở phút 10 và phút 50 về cùng một chủ đề mang cùng `thread`/`key`. Thread lạ → mã `THREAD_UNMAPPED`, hỏi người | `adapters/llm/event_extractor.py` |
| Mơ hồ → hỏi đúng chỗ | Luật trả **mã lý do** (`NOT_CHAIR`, `HEDGED`, `NOD_ONLY`, `OWNER_MISSING`, `DEADLINE_VAGUE`…). Câu hỏi sinh từ mã. Mục không có mã hỏi thì tự chấp nhận | `domain/reasons.py`, `domain/review.py` |
| Trạng thái hợp với từng loại mục | Bảng trạng thái theo type: task "Đã nhận", tri thức "Ghi nhận", phương án "Còn treo". Người duyệt chỉ Xác nhận / Bác bỏ / để họp sau; trạng thái mới tra từ bảng | `domain/status_table.py` |
| Người kiểm lại | Màn duyệt mới: **Cần bạn trả lời (n)** chỉ gồm mục vướng. **Kết quả — tự chấp nhận** thu gọn, mở ra có "Vì sao" (diễn biến từng câu). Bấm trích dẫn → transcript cuộn tới đúng câu. Bỏ dropdown 6 trạng thái của M2 | `apps/web/src/app/meetings/[id]/page.tsx` (= `/m/[id]`) |
| Họp định kỳ, dùng lại | **Nhóm họp** mở bằng link bí mật: Buổi họp · Kho tri thức · Việc treo | `/s/[id]`, `POST /series` |
| Tri thức dùng lâu dài | Tri thức có phạm vi `meeting` / `durable`. Chỉ mục `durable` người duyệt đã xác nhận mới vào Kho khi xuất bản | `domain/status_rules.py`, `usecases/meetings.py` |
| Lưu bền, truy vết | Postgres (Supabase). Lưu cả sự kiện LLM và bản đồ chủ đề để replay khi sửa luật. `review_actions` chỉ thêm, có trigger chặn sửa / xoá, bật RLS | `db/migrations/002_m3.sql`, `adapters/persistence/postgres.py` |
| Học từ sai sót | Xuất các lần người duyệt bác bỏ / sửa owner / hạn / nội dung ra `data/corrections/` để gán nhãn lại. **Không** đưa vào prompt | `python -m chot.eval.export_corrections` |

## 2. Before → After

### 2.1 Họp dài: một lần gọi → hai lượt (bản đồ chủ đề + đoạn)

- **M2 trước:** cả transcript đi vào một lần gọi LLM.
- **Vấn đề:** trên L1–L4 (148–200 câu, chủ đề bị cắt rồi quay lại sau ≥ 40 câu), M2 chốt nhầm **25% (6/24)** (`20261021-143047-llm-m2-long`) và bỏ sót 13 quyết định đã chốt. Có cả m03.D1, m10.D1, m17.D1, những quyết định mà chính M2 bắt được khi họp đứng riêng. Output khoảng 10k token mỗi buổi.
- **Đổi gì:** thêm lượt 1 (bản đồ chủ đề) và chunker thuần trong `domain/`. Mỗi câu thuộc đúng một đoạn. Sự kiện ở câu ngữ cảnh bị bỏ khi gộp.
- **Giữ nguyên:** LLM vẫn chỉ gán nhãn, luật vẫn quyết định. Grounding giữ nguyên. Họp ngắn vẫn một lần gọi.
- **Chọn `CHUNK_SIZE`:** thử 50 / 70 / 100, mỗi cỡ 3 vòng prompt (EVAL_LOG 21–22/10).
  - Chọn 100: thấp nhất trên prompt hiện tại (vòng 2, `-final`: c50 5,6%, c70 5,3%, c100 4,8%).
  - Loại 50: nó làm mất quyết định MoMo của khối m01 trong L1 ở cả 3/3 lần chạy (T1 đỏ).
- **M3 sau (L1–L4):**

| Chỉ số | M2 `p8-m2-long` | M3 `p8-m3-long` |
|---|---|---|
| Chốt nhầm ⭐ | 13% (3/23) | **4,8% (1/21)** |
| Nhất quán thread | 94,3% | **100%** |
| Việc nhầm (task "Đã nhận" sai) | 5,7% | **3,3%** |
| Trạng thái cuối đúng | 64,5% | 64,5% |
| Phương án cũ được gắn "bị thay thế" | **52,4%** | 38,1% |
| Precision / recall mục | 69,4% / 49,9% | 67,5% / 48,4% |

  13% ở cột M2 là sự kiện M2 đi qua **luật mới**. Với luật cũ, M2 là 25%.
- **Giới hạn:**
  - Supersession **giảm** 52,4% → 38,1%: M3 nối "B thay A" kém M2. Chưa phân tích nguyên nhân, chưa sửa.
  - Nhiễu giữa các lần chạy là ±5–8 điểm, lớn hơn chênh lệch giữa 3 kích thước đoạn. Với c100, 3 vòng cho 4,8% · 9,1% · 4,8%.

### 2.2 Luật: gật đầu cho một việc ≠ quyết định

- **M2 trước:** luật tin nhãn `agree` của LLM.
- **Vấn đề:**
  - Trong L4, chủ trì nói "Ừ, gửi trước khi áp dụng" (u087) cho một việc vừa có người nhận. LLM gán `agree` → luật ghi thành quyết định đã chốt.
  - Sửa prompt hai vòng không chặn được: u087 vẫn `agree` ở c50 và c100 vòng 2 (`153318-…-r2`, `153854-…-r2`).
- **Đổi gì** (Nash duyệt 22/10):
  - `agree` trên key của việc đã giao / nhận ở câu trước → không phải quyết định.
  - `FALLBACK_KEPT` xét mọi câu đồng ý cùng key và đọc cả câu gốc, nên "Chốt B. Nếu… thì quay về A" không mất vế sau khi đồng chủ trì nói "Ok".
- **Giữ nguyên:** mọi luật M2. Oracle vẫn 100%.
- **Sau:** replay 10 run L1–L4: c100 4,8 / 9,1 / 4,8% (`<run>-final`). m01–m25 không đổi: 0% ở cả M2 và M3.
- **Giới hạn:** luật chỉ chặn được dạng lỗi đã thấy. Dạng mới vẫn phải đi qua hàng đợi câu hỏi.

### 2.3 Lý do chữ tự do → mã lý do; trạng thái theo type

- **M2 trước:** `flags` là chuỗi chữ, mọi type dùng chung 6 trạng thái. Task đã nhận hiện "Đang mở".
- **Đổi gì:** `domain/reasons.py` có 11 mã hỏi và 4 mã thông tin. `domain/status_table.py` định nghĩa trạng thái cho phép, `ON_CONFIRM`, `ON_REJECT` và nhãn UI theo từng type. Ngoài bảng → `ValueError`.
- **Giữ nguyên:** kết luận của luật. `flags` vẫn có trong API, chữ y như M2, để export cũ không vỡ.
- **Bằng chứng:**
  - Replay `20261021-145424-replay-v2`: mọi chỉ số trùng mốc M2 (`131042-replay-m2baseline`), 221/221 mục cùng id + status + flags.
  - Khác duy nhất: 4 tri thức thêm `DURABLE_KNOWLEDGE` (m03, m07, m15, m21). Cả 4 đúng là ràng buộc lâu dài.
- **Giới hạn:** chưa có gold cho phạm vi tri thức, nên "phân loại meeting / durable đúng" **chưa đo**.

### 2.4 Màn duyệt: duyệt mọi mục → chỉ trả lời câu hỏi

- **M2 trước:**
  - Mọi mục có nút "Duyệt" và dropdown 6 trạng thái. Người duyệt tự gõ trạng thái, trái luật vàng #1.
  - Transcript nằm cuối trang.
- **Đổi gì:**
  - Hàng đợi "Cần bạn trả lời" lấy câu hỏi từ mã lý do, kèm 1–2 trích dẫn. Trả lời bằng Xác nhận / Bác bỏ / để họp sau. Có chip chọn người khi thiếu owner, ô chọn ngày khi hạn mơ hồ.
  - Mục chắc chắn được tự chấp nhận, thu gọn theo loại, mở ra có "Vì sao".
  - Transcript ở cột phải (mobile: tab).
  - Xuất bản bị khoá khi còn câu hỏi, nút ghi "Còn n câu hỏi".
- **Bằng chứng:**
  - Buổi họp ngắn: `p8-m3-short` 1,0 mục `needs_confirmation`/buổi, 76% trong đó gold cũng coi là cần xác nhận. M2 `p8-m2-short`: 1,16 và 79,3%.
  - Toàn bộ mục chờ trả lời (gồm cả hạn mơ hồ và tri thức lâu dài): 37/221 = **1,48 câu hỏi/buổi** (`145424-replay-v2`).
  - Họp dài: 11 mục có mã hỏi/buổi trên M3 so với 7 trên M2 (EVAL_LOG, "P4 chốt").
- **Giới hạn:**
  - Họp dài hỏi nhiều: 11 câu/buổi. Chưa gộp câu hỏi cùng chủ đề.
  - Chưa đo thời gian duyệt thật.

### 2.5 RAM → Postgres, nhóm họp, Kho tri thức

- **M2 trước:** InMemory, tối đa 500 buổi, restart là mất.
- **Đổi gì:**
  - `PostgresRepository` lưu transcript, sự kiện, bản đồ chủ đề, mục và nhật ký duyệt.
  - Nhóm họp có id ngẫu nhiên 22 ký tự (`secrets.token_urlsafe(16)`). Id buổi họp cũng vậy.
  - Nhóm mẫu `mau-chot-m01-m05` chỉ xem: trả lời / sửa / xuất bản / thêm buổi → 403.
  - Xuất bản đẩy tri thức lâu dài đã xác nhận vào Kho. Gọi lại không nhân đôi.
- **Giữ nguyên:** mọi route M2. Transcript mới vẫn cần mã truy cập, rate limit giữ nguyên.
- **Bằng chứng:**
  - Test API: `tests/test_api_series.py`, 9 test.
  - Round-trip Postgres + trigger chặn UPDATE: `tests/test_postgres_repo.py`, chạy trên postgres:16 local.
  - Phần này không có số eval.
- **Giới hạn:**
  - Mỗi thao tác mở 1 kết nối, không dùng pool.
  - Hai người duyệt cùng lúc: nhật ký đủ cả hai, nhưng mục thì người lưu sau thắng.
  - **Lỗi đã biết:** "Hoàn tác câu trả lời" chỉ đưa mục về hàng đợi, không khôi phục trạng thái / phạm vi cũ. Hai hậu quả:
    - task đã xác nhận rồi hoàn tác, sau đó để họp sau, vẫn hiện "Đã nhận";
    - tri thức bị bác rồi hoàn tác, xác nhận lại, **không vào Kho**.

## 3. Bộ test

### 3.1 Regression M2
- Oracle (luật trên sự kiện chuẩn): 100%.
- m01–m25: chốt nhầm 0% ở cả M2 (`p8-m2-short`) và M3 (`p8-m3-short`).
- Chạy đầu-cuối M3 `20261021-154425-llm-m3-c100-r2` từng ra 4,8% (m24 u011 "như đã chốt" bị gán `agree`). Chạy lại `20261022-121440-…-r2b` thì không lặp lại → dao động của LLM. Gold m24 đã thống nhất theo nhãn Nash.

### 3.2 Test bắt buộc

| # | Loại | Test | Kết quả |
|---|---|---|---|
| T1 | Regression | m01 đứng riêng (`154425`) vs m01 nằm trong L1 (`153854-…-c100-r2`), qua chunking: MoMo Đã chốt, VNPay Bị thay thế, cùng mã lý do | ✅ `tests/test_long_acceptance.py`. c100 đạt 3/3 vòng; c50 0/3 (lý do loại c50) |
| T2 | Edge case | L4: 0 chốt nhầm; "Ok vậy đi" đầu đoạn (u071) hiểu đúng; tri thức có rào đón không vào Kho khi chưa xác nhận; task không owner → `OWNER_MISSING` | ✅ 3/4. ❌ `OWNER_MISSING` (xfail strict): LLM gán câu "Ai đó gửi lại bản vẽ…" vào u121 thay vì u124, grounding loại task → không còn mục để hỏi. Ở 10 run, LLM đúng 8 lần |
| T3 | Change Request | — | **Chưa làm.** Chưa nhận Change Request. Danh sách CR dự kiến ở [CHANGE_REQUEST_BANK](mission3/CHANGE_REQUEST_BANK.md) |

### 3.3 Unit test
`make test`: **77 passed** (mốc M2) → **265 passed, 1 skipped, 1 xfailed**.
- Bị skip: test Postgres, cần `TEST_DATABASE_URL`.
- Xfail: `OWNER_MISSING` ở T2.

Test mới bao gồm:
- chunker: mọi câu thuộc đúng 1 đoạn, ngữ cảnh ≤ 10, họp ngắn là 1 đoạn;
- gộp: sự kiện ngữ cảnh bị bỏ, thread lạ → `THREAD_UNMAPPED`;
- mỗi mã lý do sinh đúng câu hỏi;
- `answer()` theo bảng `ON_CONFIRM` / `ON_REJECT`; bước ngoài bảng bị chặn;
- tri thức chỉ vào Kho sau xác nhận + xuất bản;
- xuất bản khoá khi còn câu hỏi;
- nhóm mẫu chỉ xem;
- nhật ký duyệt append-only;
- `export_corrections`.

### 3.4 Chỉ số trước / sau

| Chỉ số | m01–m25 M2 | m01–m25 M3 | L1–L4 M2 | L1–L4 M3 |
|---|---|---|---|---|
| Chốt nhầm ⭐ | 0% (0/20) | 0% (0/20) | 13% (3/23) | **4,8% (1/21)** |
| Trạng thái cuối đúng | 90,9% | 90,9% | 64,5% | 64,5% |
| Bị thay thế (supersession) | 78,9% | **84,2%** | **52,4%** | 38,1% |
| Việc nhầm | 4% | **0%** | 5,7% | **3,3%** |
| Nhất quán thread | **91,4%** | 87,1% | 94,3% | **100%** |
| Mục cần xác nhận / buổi | 1,16 | 1,0 | 5,25 | 6 |
| … trong đó gold cũng cần hỏi | 79,3% | 76% | 85,7% | 75% |
| Owner / hạn đúng | 100% / 100% | 100% / 98,5% | 98,8% / 96,4% | 98,7% / 93,5% |
| Precision / recall mục | 75,9% / 53% | 72,6% / 52,1% | 69,4% / 49,9% | 67,5% / 48,4% |
| Grounding tầng 1 | 100% | 100% | 100% | 100% |
| Phạm vi tri thức đúng | chưa đo | chưa đo | chưa đo | chưa đo |

Run: `p8-m2-short`, `p8-m3-short`, `p8-m2-long`, `p8-m3-long` (tên đầy đủ ở đầu file).
- Một mục chốt nhầm ≈ 5 điểm %.
- Trên L1–L4, chênh lệch giữa các lần chạy cùng cấu hình là ±5–8 điểm.

## 4. Chi phí đo thật

Thay bảng ước tính ở RECAP §6. Số lấy từ `usage` trong `report.json`. Giá gpt-4.1-mini: $0,40 / 1M token vào, $1,60 / 1M token ra.

| Bộ | M2 (1 lần gọi) | M3 (hai lượt) | M3 / M2 |
|---|---|---|---|
| m01–m25 (25 buổi, ≤ 100 câu) | `20261021-142711-llm-m2`: 25 lần gọi, 70.008 vào / 31.642 ra, **$0,0786** → $0,0031/buổi | `20261022-121440-llm-m3-c100-r2b`: 25 lần gọi, 87.883 vào / 36.747 ra, **$0,0939** → $0,0038/buổi | 1,2× (prompt dài hơn; họp ngắn không chia đoạn) |
| L1–L4 (4 buổi, 148–200 câu) | `20261021-143047-llm-m2-long`: 4 lần gọi, 28.133 vào / 41.480 ra, **$0,0776** → $0,019/buổi | `20261021-153854-llm-m3-long-c100-r2`: 12 lần gọi, 74.528 vào / 53.089 ra, **$0,1148** → $0,029/buổi | 1,5× |

- Ước tính ở RECAP là 1,8×. Đo thật ra 1,5× trên họp dài.
- Output vẫn chiếm phần lớn: $0,085 trên $0,115 ở M3 L1–L4.
- Tổng chi phí các run LLM của P4 ≈ $1,23 (EVAL_LOG, dòng "P4 chốt").
- Chưa đo: prompt caching, độ trễ, quy đổi VNĐ.

## 5. Ba câu hỏi bắt buộc

### a) Ưu tiên thay đổi gì, chủ động chưa làm gì, vì sao?

**Ưu tiên:** sửa cái làm hỏng lời hứa chính, tức "Đã chốt" phải đúng, trước khi thêm tính năng.

1. **Họp dài.** Bộ test M2 chỉ có buổi ngắn, tối đa vài chục câu. Đo trước khi sửa: M2 chốt nhầm 25% trên L1–L4, gấp 5 lần ngưỡng 5%. Không sửa phần này thì mọi thứ khác chỉ đúng trên demo.
2. **Mơ hồ → hỏi người, theo mã lý do.** M2 bắt người duyệt tự chọn trạng thái cho mọi mục. M3 chỉ hỏi chỗ luật không chắc, câu hỏi nói rõ vì sao.
3. **Lưu bền + nhóm họp + Kho tri thức.** Họp định kỳ cần nhớ buổi trước. RAM thì restart là mất.

**Chủ động chưa làm** (đưa vào [CHANGE_REQUEST_BANK](mission3/CHANGE_REQUEST_BANK.md)):
- **Ghi âm / ASR (CR1, CR2).** Thêm một nguồn lỗi mới (nhận sai người nói, sai chữ) trong khi lõi chưa đạt trên họp dài. Chi phí ASR chưa đo.
- **Đăng nhập Google + dashboard nhiều nhóm (CR3).** Link bí mật đủ cho demo và một nhóm dùng thử. Login không làm "Đã chốt" đúng hơn.
- **Ledger xuyên buổi (CR4).** Schema đã có `series_id`, `thread`, `supersedes`. Chỉ làm khi đã có họp thật, vì cần biết người dùng muốn nối quyết định giữa các buổi thế nào.
- **Change Request của reviewer (T3).** Chưa nhận. Thiết kế M3 cố tình đặt các điểm hay đổi vào bảng cấu hình (`status_table.py`, `reasons.py`) để CR kiểu "thêm loại mục" chỉ cần sửa bảng + test.

### b) Thay đổi nào tạo khác biệt lớn nhất? Bằng chứng?

**Extractor hai lượt (bản đồ chủ đề + đoạn) cộng luật P4, trên họp dài.**

| Bước | Chốt nhầm L1–L4 | Run |
|---|---|---|
| M2 nguyên trạng | 25% (6/24) | `20261021-143047-llm-m2-long` |
| Sự kiện M2, luật + metrics mới | 13% (3/23) | `20261022-135052-replay-p8-m2-long` |
| M3 hai lượt, c100, luật + metrics mới | **4,8% (1/21)** | `20261022-135053-replay-p8-m3-long` |

Cùng lúc:
- nhất quán thread 94,3% → 100%;
- việc nhầm 5,7% → 3,3%;
- T1 xanh: m01 cho cùng kết quả dù đứng riêng hay nằm trong L1.

Khoảng 12 điểm (25 → 13%) đến từ luật, 8 điểm (13 → 4,8%) từ cách gán sự kiện theo bản đồ chủ đề. M2 đã cho thấy điều này: chỗ nào quan trọng thì phải có luật giữ, vì LLM dao động giữa các lần chạy.

Cái giá:
- supersession giảm (52,4% → 38,1%);
- chi phí 1,5×;
- 1/21 vẫn là trên một lần chạy. Ba vòng c100 cho 4,8 / 9,1 / 4,8%, tức chưa ổn định dưới 5%.

### c) Rủi ro lớn nhất nếu đưa người dùng thật ngày mai, và xử lý theo thứ tự nào?

| # | Rủi ro | Vì sao lớn | Xử lý |
|---|---|---|---|
| 1 | **Chưa có cuộc họp thật nào** | 25 + 4 buổi đều là kịch bản (m01–m05 Nash viết, phần còn lại tổng hợp rồi duyệt tay). Họp thật có nói chen, câu cụt, lỗi ASR. Số 4,8% có thể lạc quan | Xin 3–5 biên bản thật có consent → gán nhãn → chạy eval trước khi mở cho ai. Bật `export_corrections` để mỗi lần người duyệt bác / sửa thành case gán nhãn lại |
| 2 | **Một người gán nhãn** | Gold là nhãn của Nash. Đồng thuận với answer_key 4,5% lệch (m01–m25), nhưng chưa có người thứ hai. m24 từng có hai bộ nhãn trái nhau | Người gán thứ hai cho ít nhất L1–L4 + 10 buổi ngắn, đo đồng thuận. Lệch thì thêm quy ước vào `LABELING_GUIDE.md` |
| 3 | **Link bí mật ≠ bảo mật** | Ai có link nhóm là xem được toàn bộ biên bản, Kho tri thức, transcript. Link dễ lộ qua chat, lịch sử trình duyệt, ảnh chụp màn hình. Transcript còn đi qua Railway + OpenAI ra nước ngoài | Ngày mai: ghi rõ trên UI (đã có), chỉ dùng cho dữ liệu không nhạy cảm. Sau đó: CR3 (login + quyền theo nhóm), CR12 (che PII trước khi gửi LLM) |
| 4 | **gpt-4.1-mini sắp bị deprecated** | Mọi số đo gắn với model này. Đổi model là đổi phân bố nhãn sự kiện | Đổi model chỉ cần sửa `.env`, nhưng phải chạy lại toàn bộ eval (m01–m25 + L1–L4, ~$0,21/lượt) và ghi EVAL_LOG trước khi đổi trên production |
| 5 | **LLM dao động + lỗi đã biết** | Cùng cấu hình, chốt nhầm L1–L4 4,8–9,1%. Lỗi hoàn tác (§2.5) có thể làm mất tri thức khỏi Kho | Sửa lỗi hoàn tác trước (nhỏ, có test). Chạy eval nhiều lần, báo trung bình thay vì một run. Dạng lỗi lặp lại → thêm luật, không chỉ sửa prompt |

**Thứ tự:** 1 → 3 → 5 → 2 → 4.
- Chưa có họp thật thì không biết các con số còn đúng không.
- Lộ dữ liệu là lỗi không rút lại được.
- Lỗi hoàn tác rẻ, sửa ngay.
- Người gán thứ hai và đổi model quan trọng nhưng không gây hại ngay ngày đầu.
