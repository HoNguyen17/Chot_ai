# Nhật ký đánh giá

Mỗi lần đổi prompt, đổi model hoặc sửa luật → chạy eval và thêm một dòng. Đừng xoá dòng cũ.

| Ngày | Hệ thống | Bộ test | Chốt nhầm ⭐ | Trạng thái cuối | Supersession | Owner | Hạn | Grounding | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | keyword baseline | answer_key m01–m05 | 66,7% | 80% | 0% | 100%* | 100%* | 100% | *chỉ ghép được 3 task — recall mục 32,6% |
| 2026-10-13 | luật + sự kiện chuẩn (oracle) | answer_key m01–m05 | 0% | 100% | 100% | 100% | 100% | 100% | Kiểm tra luật khớp hướng dẫn gán nhãn — KHÔNG phải điểm của LLM |
| 2026-10-14 | nhãn gold (Claude soạn nháp, Nash duyệt) vs answer_key | answer_key m01–m05 | 16,7% | 100% | 75% | 100% | 100% | — | Đo độ đồng thuận nhãn, KHÔNG phải điểm LLM. 1/6 "final" lệch: m03 D2 staging (quy tắc 6 của Nash, answer_key coi là T2 needs_confirmation). Hụt: m03 O2 "15/11 đủ scope" (superseded), m04 R1 Excel (answer_key: request open; gold: D3 needs_confirmation theo quy tắc 5). Item recall 95,7%, precision 62,9% (gold có O/B/K nhiều hơn answer_key). `make` chưa chạy trong máy nên gọi trực tiếp `chot.eval.run --system labels` |
| 2026-10-14 | nhãn Nash vs answer_key | answer_key m01–m25 | 4,5% | 91,3% | 89,5% | 98,6% | 100% | — | Đo độ đồng thuận nhãn, KHÔNG phải điểm LLM. Chốt nhầm 1: m03 D2 đĩa server (quy tắc 6). Bỏ sót: m23 D1 (quy tắc 10, gold needs_confirmation), m24 D2 (quy tắc 9, gold K1). Sai owner 1: m25 T3 Phương vs null (quy tắc 12). Item precision 73,7%, recall 98,7%. Lỗi định dạng: 18 mục K/B thiếu note ở m02–m05 (TEMPLATE chỉ có note ở D/O/T/Q). m01 quote u002 "đi VNPay" không khớp raw đang sửa dở (chưa commit). `make` chưa chạy trong máy nên gọi trực tiếp `chot.eval.run --system labels` |
| | llm (model?) | gold m01–m05 | | | | | | | `make eval-llm` |
| | summary baseline (model?) | gold m01–m05 | | | | | | | `make eval-summary` |
