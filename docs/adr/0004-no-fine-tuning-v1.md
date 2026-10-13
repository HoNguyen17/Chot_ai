# ADR-0004 · Không fine-tune ở v1

- **Trạng thái:** Đã chấp nhận · 10/2026
- **Quyết định:** v1 dùng prompt + JSON schema + luật. Không fine-tune.
- **Lý do:** (1) Chỉ có ~20 transcript, quá ít để fine-tune có ý nghĩa. (2) Bộ test không được dùng làm dữ liệu train, nếu không eval mất giá trị (data leakage). (3) Phần lớn độ chính xác đến từ thiết kế (sự kiện + luật + grounding), không phải trọng số model.
- **Khi nào xem lại:** Khi `review_actions` tích luỹ vài trăm lần người duyệt sửa nhãn trên cuộc họp thật — đó là dữ liệu train đúng phân phối. Tách hẳn tập train/test theo thời gian.
