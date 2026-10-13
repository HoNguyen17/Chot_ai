# Nhật ký đánh giá

Mỗi lần đổi prompt, đổi model hoặc sửa luật → chạy eval và thêm một dòng. Đừng xoá dòng cũ.

| Ngày | Hệ thống | Bộ test | Chốt nhầm ⭐ | Trạng thái cuối | Supersession | Owner | Hạn | Grounding | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | keyword baseline | answer_key m01–m05 | 66,7% | 80% | 0% | 100%* | 100%* | 100% | *chỉ ghép được 3 task — recall mục 32,6% |
| 2026-10-13 | luật + sự kiện chuẩn (oracle) | answer_key m01–m05 | 0% | 100% | 100% | 100% | 100% | 100% | Kiểm tra luật khớp hướng dẫn gán nhãn — KHÔNG phải điểm của LLM |
| | llm (model?) | gold m01–m05 | | | | | | | `make eval-llm` |
| | summary baseline (model?) | gold m01–m05 | | | | | | | `make eval-summary` |
