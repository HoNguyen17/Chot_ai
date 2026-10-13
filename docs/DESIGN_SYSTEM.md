# Design system — Chốt

> Cảm hứng: **tờ biên bản và con dấu đỏ.** Nền giấy ấm, chữ mực, và chỉ một màu đỏ son dành cho thứ quan trọng nhất: *đã chốt*. Mọi thứ khác lùi lại.

Nguồn sự thật của token: `apps/web/src/app/globals.css`. Sửa token → sửa cả file này.

## 1. Nguyên tắc

| # | Nguyên tắc | Nghĩa là |
|---|---|---|
| 1 | **Bằng chứng trước, kết luận sau** | Mỗi thẻ luôn hiện trích dẫn + mốc thời gian; bấm vào nhảy tới câu gốc |
| 2 | **Không chắc thì nói không chắc** | "Cần xác nhận" có màu riêng, đứng **đầu** trang, kèm lý do (flags) |
| 3 | **Duyệt trong 5 phút** | Việc cần người xử lý lên trước; mỗi thẻ 1 nút "Duyệt" + 1 ô đổi trạng thái |
| 4 | **Đỏ son chỉ cho "Đã chốt"** | Không dùng đỏ cho lỗi trang trí; lỗi dùng nền đỏ nhạt + chữ |
| 5 | **Tiếng Việt trước** | Font hỗ trợ dấu tốt (Be Vietnam Pro), câu chữ ngắn, đúng giọng công sở VN |

## 2. Token

### Màu

| Token | Sáng | Tối | Dùng cho |
|---|---|---|---|
| `--paper` | `#f7f5f0` | `#15140f` | Nền trang |
| `--surface` | `#ffffff` | `#1e1c17` | Thẻ, ô nhập |
| `--ink` / `--ink-2` / `--ink-3` | `#1d1b16` / `#57534a` / `#8a857a` | `#f1ede4` / `#bdb7aa` / `#8c8679` | Chữ chính / phụ / mờ |
| `--line` / `--line-strong` | `#e4e0d6` / `#cfc9bb` | `#2e2b24` / `#403c33` | Viền |
| `--seal` | `#b8321e` | `#ff8a73` | Thương hiệu, **Đã chốt**, nút chính |
| `--seal-bg` | `#fbeae6` | `#3a1d17` | Nền huy hiệu Đã chốt, nền cảnh báo |
| `--focus` | `#2d5bd7` | `#8fb0ff` | Viền focus bàn phím |

### Trạng thái → hình thức

| Trạng thái | Huy hiệu | Thẻ | Lý do |
|---|---|---|---|
| **Đã chốt** | Viền đỏ son, CHỮ IN HOA, góc vuông — như con dấu | Bình thường | Thứ duy nhất "được đóng dấu" |
| **Cần xác nhận** | Nền vàng đất `--st-confirm-bg`, chữ `--st-confirm` | Viền trái 3px vàng | Kéo mắt, nhưng không báo động như lỗi |
| **Hoãn** | Nền xanh xám `--st-deferred-bg` | Bình thường | Trung tính, "để sau" |
| **Đang mở** | Nền ngà `--st-open-bg` | Bình thường | Thông tin, không cần làm gì |
| **Bị thay thế / Bị bác** | Viền nét đứt, chữ mờ | Nội dung **gạch ngang** | Lịch sử, không phải hành động |

Trạng thái luôn có **chữ**, không chỉ màu (người mù màu vẫn đọc được).

### Chữ

| Vai trò | Font | Cỡ / độ đậm |
|---|---|---|
| Tiêu đề trang (h1) | Be Vietnam Pro | 26px / 700 (mobile 22px) |
| Tiêu đề nhóm (h2) | Be Vietnam Pro | 17px / 700 |
| Nội dung mục | Be Vietnam Pro | 16px / 500 |
| Thân chữ | Be Vietnam Pro | 15px / 400, line-height 1.6 |
| Mốc thời gian, ID, số | JetBrains Mono | 12–12.5px |

### Khoảng cách & bo góc

Thang 4px: `--s-1` 4 · `--s-2` 8 · `--s-3` 12 · `--s-4` 16 · `--s-5` 24 · `--s-6` 32 · `--s-7` 48. Bo góc: `--r-sm` 6px (nút, ô nhập, huy hiệu Đã chốt) · `--r-md` 10px (thẻ). Khổ nội dung tối đa 880px.

## 3. Component

### `StatusBadge`
`<StatusBadge status="final" />` → huy hiệu theo bảng trên. Không có biến thể khác.

### `ItemCard` — giải phẫu

```text
┌───────────────────────────────────────────────────────────┐
│ [ĐÃ CHỐT]  QUYẾT ĐỊNH · D1                    ✓ đã duyệt  │ ← trạng thái · loại · ID
│                                                           │
│ Launch tháng 11 dùng MoMo; VNPay để phase 2               │ ← nội dung (16/500)
│ Chốt bởi: Hùng      Hạn: —                                │ ← meta
│ • đã đổi ý trong cuộc họp — xem timeline                  │ ← flags (màu vàng đất)
│ ┌───────────────────────────────────────────────────────┐ │
│ │ 14:20  Hùng: “Vậy chốt nhé: launch tháng 11 dùng…”    │ │ ← bằng chứng → #u019
│ │ 03:15  Lan: “Em đề xuất MoMo”                         │ │
│ └───────────────────────────────────────────────────────┘ │
│ [Duyệt]   Đổi trạng thái [Đã chốt ▾]                      │ ← hành động
└───────────────────────────────────────────────────────────┘
```

- `data-status` trên thẻ điều khiển viền trái (Cần xác nhận) và gạch ngang (Bị thay thế).
- Task: luôn hiện "Phụ trách: …", nếu `owner = null` hiện **"chưa rõ"** (không để trống).
- "Chốt bởi" chỉ dùng khi `final`; còn lại là "Đồng ý bởi".

### Nút
- `btn-primary` (đỏ son): **một** hành động chính mỗi màn hình — "Chốt biên bản", "Duyệt & xuất bản".
- `btn`: hành động phụ (export). `btn-sm`: hành động trên thẻ.
- Nút bị chặn phải nói vì sao: "Còn 3 mục cần duyệt" thay vì chỉ mờ đi.

## 4. Màn hình

### Upload `/`
Tiêu đề → 1 câu giải thích → ô dán transcript (font mono) → [Chọn file] [Dùng mẫu] ……… **[Chốt biên bản]** → danh sách cuộc họp gần đây.

### Duyệt `/meetings/[id]`

```text
05/10/2026 · chủ trì: Hùng · rules-v1+llm-events
Weekly sync — App giao hàng
  1 quyết định đã chốt   5 công việc   2 chờ bạn xác nhận
[Còn 2 mục cần duyệt]  [Biên bản .md] [Task .csv] [Ledger .json]

Cần bạn xác nhận (2)        ← luôn đứng đầu
Đã chốt (1)
Công việc đã nhận (2)
Hoãn & còn bỏ ngỏ (2)
Ghi nhận khác (2)
Lịch sử: phương án bị thay thế (1)
Transcript (26 câu)          ← đích của mọi link bằng chứng; câu được trỏ tới tô vàng (:target)
```

Thứ tự theo **mức cần hành động**, không theo thứ tự thời gian của cuộc họp.

### Sắp có (v2)
- **Decision timeline** theo chủ đề: `Đề xuất VNPay → phản biện → tạm chốt MoMo → blocker → Đã chốt MoMo` — chính là sơ đồ trong PRD §2.
- **Brief kỳ sau**: danh sách mục Cần xác nhận / Hoãn / task quá hạn của cuộc họp trước.

## 5. Câu chữ (microcopy)

| Nên | Không nên | Vì sao |
|---|---|---|
| "Cần bạn xác nhận" | "Độ tin cậy thấp (0.42)" | Người dùng cần biết phải làm gì, không cần con số |
| "chưa rõ ai nhận việc" | "owner: null" | Tiếng người |
| "Còn 2 mục cần duyệt" | (nút mờ không giải thích) | Nói lý do bị chặn |
| "Đồng ý bởi: Minh" | "Chốt bởi: Minh" (khi chưa chốt) | Không nói quá sự thật |
| "Đang phân tích…" | "Loading…" | Tiếng Việt nhất quán |

## 6. Accessibility

- Tương phản chữ thường ≥ 4.5:1 ở cả hai chế độ sáng/tối.
- Mọi hành động dùng được bằng bàn phím; `:focus-visible` có viền `--focus`.
- Trạng thái có chữ + hình (viền đứt, gạch ngang), không chỉ màu.
- `lang="vi"` trên `<html>` để trình đọc màn hình đọc đúng dấu.
