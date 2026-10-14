# Kịch bản video demo (≤ 5 phút)

Quay màn hình https://chot.nashng.dev + repo. Cả 3 cuộc họp dùng trong video (m01, m03, m04) đều có trong mục "Dùng transcript mẫu…", chạy lại sự kiện của một lần gọi LLM thật nên kết quả lần nào cũng giống nhau.

Chuẩn bị trước: mở sẵn 3 tab: demo, `docs/MISSION2.md` (bảng 3 hệ thống), `docs/EVAL_LOG.md`.

---

## Cảnh 1 · Bài toán (0:00–0:40)

**Màn hình:** trang chủ Chốt ("Họp xong rồi. Giờ chốt lại."). Cuộn chậm transcript m01 trong ô dán.

**Lời thoại:**
> Họp dự án ở SME Việt Nam hay có một kiểu: đầu họp đề xuất A, giữa họp "tạm thời đi B", cuối họp mới chốt hẳn. Biên bản viết tay, hoặc AI tóm tắt, thường ghi luôn cái "tạm thời" thành quyết định. Rồi cả nhóm làm theo một thứ chưa ai chốt.
> Chốt nhận transcript và trả về đúng ba thứ: cái gì thật sự đã chốt, ai làm gì hạn nào, cái gì còn treo. Dòng nào cũng trỏ về câu nói gốc.

## Cảnh 2 · Phần chọn chứng minh (0:40–1:20)

**Màn hình:** bảng "Q1" trong `docs/MISSION2.md`, 4 dòng keyword / tóm tắt / Chốt đầu-cuối / Chốt replay.

**Lời thoại:**
> Phần mình chọn chứng minh là: không biến ý kiến trung gian thành quyết định. Cách làm: LLM chỉ gán nhãn từng câu: đề xuất, phản đối hay đồng ý. Còn "đã chốt hay chưa" thì luật trong code quyết.
> Đo trên 25 cuộc họp có cài bẫy. Lọc keyword ghi nhầm 57,6% số quyết định. Một prompt tóm tắt ghi nhầm 54,3%. Chốt: 4,8% ở lần chạy đầu-cuối, và 0% sau khi sửa luật cho đúng lỗi đó. Hai cách kia cũng không bao giờ đánh dấu được phương án nào đã bị thay thế.

## Cảnh 3 · Demo m01: đổi ý A → B, có bằng chứng (1:20–2:50)

**Màn hình, theo thứ tự:**
1. Chọn "Dùng transcript mẫu…" → m01 → bấm tạo. (Chỉ vào 3 ô số: quyết định đã chốt / công việc / chờ bạn xác nhận.)
2. Mục "Đã chốt": D1 "Chốt launch tháng 11 dùng MoMo, VNPay cho phase 2", flag "đã đổi ý trong cuộc họp — xem timeline".
3. Bấm bằng chứng **14:20 Hùng** → trang nhảy xuống câu u019 trong transcript. Cuộn lên cho thấy 05:30 "Thôi tạm thời đi MoMo nhé" và 12:30 "Vậy hay là quay lại VNPay cho chắc?".
4. Mục "Lịch sử: phương án bị thay thế": VNPay.
5. Mục "Cần bạn xác nhận": task của Minh, câu trả lời "Dạ, để em xem lại ạ.", 2 flag. Chỉ vào nút "Còn … mục cần duyệt" đang bị khoá.
6. Bấm "Duyệt" vài mục → bấm "Biên bản .md".

**Lời thoại:**
> Đây là cuộc họp chọn cổng thanh toán. Minh đề xuất VNPay, Lan đề xuất MoMo. Phút thứ năm anh Hùng nói "thôi tạm thời đi MoMo". Phút mười hai Minh lại muốn quay về VNPay. Phút mười bốn anh Hùng mới chốt.
> Chốt chỉ ghi một quyết định, là câu ở phút mười bốn, và bấm vào là thấy đúng câu đó. Câu "tạm thời" không được tính, vì đó là đồng ý có rào đón. VNPay nằm ở phần lịch sử, không mất đi.
> Còn đây là chỗ hệ thống không chắc: anh Hùng giao việc cho Minh, Minh trả lời "Dạ, để em xem lại ạ". Trong tiếng Việt câu này chưa phải là nhận việc, nên Chốt để ở "Cần xác nhận" và khoá nút xuất bản cho tới khi người chủ trì duyệt.

## Cảnh 4 · Tình huống khó + case thất bại (2:50–4:00)

**Màn hình, theo thứ tự:**
1. Mở m04 → mục "Cần bạn xác nhận": "Đề xuất chuyển phiếu xuất kho viết tay sang file Excel", bằng chứng **Sơn: Ừ**, flag "chủ trì chỉ đáp 'Ừ.' — đồng ý gián tiếp, cần xác nhận".
2. Mở `docs/EVAL_LOG.md`, chỉ vào dòng "chạy thật xác nhận" (4,8%) và dòng ngay dưới (0%).
3. Mở m03 → mục "Cần bạn xác nhận": task "Giao Bảo tạo ticket Gia ra, anh duyệt nâng cấp ổ đĩa…". Mục "Đã chốt" chỉ có quyết định release 15/11, không có ổ đĩa.

**Lời thoại:**
> Tình huống khó: nhân viên đề xuất chuyển sang Excel, người chủ trì chỉ nói "Ừ." rồi kết thúc họp. Ở lần chạy thật, LLM coi "Ừ" là đồng ý dù prompt đã dặn không được, và hệ thống ghi đó là đã chốt. Đó là lỗi chốt nhầm duy nhất của lần chạy ấy. Mình không sửa prompt thêm nữa mà thêm một luật: đồng ý mà chỉ có "Ừ" hay "Dạ" thì là cần xác nhận. Cùng dữ liệu đó, giờ ra đúng.
> Và đây là chỗ Chốt còn sai: anh Quân nói "anh duyệt nâng cấp ổ đĩa", là một quyết định thật, nằm lẫn trong câu giao việc. LLM chỉ thấy câu giao việc, nên biên bản thiếu quyết định này. Lỗi theo hướng thiếu chứ không phải ghi nhầm, nhưng vẫn là lỗi. Ngoài ra Chốt còn bỏ sót rất nhiều vướng mắc: 25 cuộc họp có 74 vướng mắc, nó chỉ bắt được 7.

## Cảnh 5 · Hạn chế + bước tiếp (4:00–4:50)

**Màn hình:** mục "4. Hạn chế đã biết" trong `docs/MISSION2.md`, rồi mục "Việc tiếp theo" trong `CLAUDE.md`.

**Lời thoại:**
> Hạn chế cần nói thẳng. Bộ test mới có 25 cuộc họp, phần lớn là kịch bản tổng hợp, và chỉ một người gán nhãn. Dữ liệu chỉ lưu trong RAM. Chưa có ASR, phải dán transcript. Server và LLM ở nước ngoài, nên với họp thật của doanh nghiệp cần xem lại luật bảo vệ dữ liệu cá nhân trước khi dùng.
> Bước tiếp theo: sửa để bắt được vướng mắc và quyết định nằm trong câu giao việc, chạy lại đầu-cuối nhiều lần để đo độ ổn định, thêm Postgres, rồi thử với 3 đến 5 nhóm thật.

---

**Tổng thời lượng dự kiến:** 4:50. Nếu quá giờ thì cắt bước 6 của cảnh 3 (export) trước.
