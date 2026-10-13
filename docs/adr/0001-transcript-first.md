# ADR-0001 · Transcript là đầu vào duy nhất của v1

- **Trạng thái:** Đã chấp nhận · 10/2026
- **Bối cảnh:** Đề bài cho input tối thiểu là transcript. Có thể thêm audio, bot vào họp.
- **Quyết định:** v1 chỉ nhận transcript `.txt` theo định dạng ở DATA_DESIGN §1. Không ASR, không bot.
- **Lý do:** (1) Tách lỗi nghe (ASR) khỏi lỗi hiểu (pipeline) → đo được đúng phần khó. (2) Bot tự vào họp gây rủi ro consent — đã có phàn nàn thật về Otter tự join. (3) Thị trường đã làm tốt khâu ghi âm.
- **Đánh đổi:** Mất tín hiệu giọng điệu, nói chồng. Người dùng phải có transcript sẵn (Zoom/Meet/Teams đều xuất được).
- **Xem lại khi:** Pilot cho thấy người dùng không có transcript → thêm `apps/asr/` xuất đúng định dạng này.
