# ADR-0002 · LLM gán nhãn sự kiện, code suy trạng thái cuối

- **Trạng thái:** Đã chấp nhận · 10/2026
- **Bối cảnh:** Lỗi nguy hiểm nhất là biến ý kiến trung gian thành quyết định chính thức. Nghiên cứu GADR (2026) ghi nhận LLM tự trích quyết định hay biến "thảo luận tạm thời" thành "đã chấp nhận". Mô hình Issue → Proposal → Agreement trên AMI (Fernández 2008) phát hiện quyết định tốt hơn cách gán nhãn phẳng.
- **Quyết định:** LLM chỉ trả về *sự kiện* cho từng câu (propose / object / agree / defer / assign…). Trạng thái cuối (Đã chốt / Cần xác nhận / Bị thay thế / Hoãn) do `domain/status_rules.py` suy ra bằng luật xác định.
- **Lý do:** Luật dễ đoán, có unit test, không đổi khi đổi model; lỗi khoanh vùng được (LLM gán sai nhãn hay luật sai?); replay sự kiện đã lưu để sửa luật không tốn token.
- **Đánh đổi:** Luật cứng có thể bỏ sót cách nói hiếm → bù bằng "Cần xác nhận" + người duyệt. Cần định nghĩa sự kiện cẩn thận (prompt dài hơn).
- **Kiểm chứng:** `test_eval_regression.py` — với sự kiện chuẩn, luật tái tạo đúng 100% đáp án; baseline keyword chốt nhầm 66,7%.
