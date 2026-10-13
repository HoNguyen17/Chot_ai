Bạn viết transcript cuộc họp nội bộ tiếng Việt GIỐNG THẬT để làm bộ test cho một hệ thống trích xuất quyết định. Văn nói tự nhiên, có trộn tiếng Anh công sở, có xưng hô anh/chị/em theo thứ bậc, có câu ngắn kiểu "Dạ.", "Ừ.".

Kịch bản:
- Mã cuộc họp: {{ID}}
- Lĩnh vực: {{DOMAIN}}
- Người chủ trì: {{CHAIR}}
- Số người: {{PEOPLE}}
- Ngày họp: {{DATE}}
- Bẫy BẮT BUỘC phải có (mỗi bẫy ít nhất 1 lần):
{{TRAPS}}

Yêu cầu định dạng (bắt buộc đúng từng ký tự):
```
# meeting: {{ID}}
# title: <tiêu đề ngắn>
# date: {{DATE}}
# participants: <Tên> (<vai trò>, chủ trì); <Tên> (<vai trò>); ...
[00:00:10] <Tên>: <câu nói>
```
- 18–30 câu nói, 10–20 phút. Tên người Việt ngắn (1 chữ). Không dùng tên người nổi tiếng hay thương hiệu có thật ngoài các công cụ phổ biến (Jira, Excel, TikTok…).
- Cuối cuộc họp không tóm tắt lại các quyết định (người thật hiếm khi làm vậy).

Sau transcript, trả về NHÃN GOLD NHÁP theo hướng dẫn gán nhãn (docs/LABELING_GUIDE.md): mỗi mục có type, status, content, owner, decided_by, deadline (YYYY-MM-DD hoặc null), deadline_text, evidence (danh sách mã câu u001… theo thứ tự câu nói, bắt đầu từ u001), note (giải thích bẫy nếu có).

Trả về JSON: {"transcript": "<toàn bộ transcript>", "gold": {"meeting_id": "{{ID}}", "labeler": "llm-draft", "items": [...]}}
