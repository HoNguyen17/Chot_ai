# ADR-0003 · Ưu tiên precision hơn recall cho "Đã chốt"

- **Trạng thái:** Đã chấp nhận · 10/2026
- **Quyết định:** Chỉ gán "Đã chốt" khi đủ 3 điều kiện (chủ trì · không rào đón · không bị lật). Mọi trường hợp khác → "Cần xác nhận" và người chủ trì duyệt trước khi xuất bản (API trả 409 nếu còn mục chưa duyệt).
- **Lý do:** Ghi sai một quyết định khiến cả nhóm làm theo phương án đã bị bỏ — đắt hơn nhiều so với tốn thêm 30 giây xác nhận. North-star metric là *tỷ lệ chốt nhầm* ≤ 5%.
- **Đánh đổi:** Nhiều mục "Cần xác nhận" hơn → tăng thời gian duyệt. Theo dõi bằng *edit rate* và *thời gian tới biên bản đã duyệt* (< 10 phút); nếu quá cao thì nới luật dựa trên dữ liệu duyệt.
