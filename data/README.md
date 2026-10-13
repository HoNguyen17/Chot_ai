# Dữ liệu

```
data/
├── examples/      m00 — ví dụ ĐÃ gán nhãn, dùng để học cách gán và làm few-shot trong prompt
├── raw/           m01–m05 — transcript thô, BẠN tự gán nhãn
├── gold/          nhãn của bạn: m01.json … (copy từ TEMPLATE.json)
├── answer_key/    đáp án tham khảo cho m01–m05 — CHỈ MỞ SAU KHI tự gán xong
├── synthetic/     scenarios.json (15 kịch bản m06–m20) + drafts/ (bản nháp do LLM sinh, chưa duyệt)
└── runs/          kết quả eval (git ignore)
```

## Bẫy trong 5 transcript

| Cuộc họp | Lĩnh vực | Bẫy chính |
|---|---|---|
| m01 | App giao hàng | A→B có tạm chốt ở giữa và bị lật lại; "Dạ, để em xem lại"; quyết định của người không chủ trì; ngày launch bị hoãn |
| m02 | Agency marketing | Tạm chốt không xác nhận lại; "thích … hơn"; chốt → phản biện → giữ nguyên; "Dạ vâng" khi được giao việc; request của khách |
| m03 | Phần mềm | Đổi ý 2 lần (chủ trì đã nói "ok dời" rồi bị lật); "nếu chốt…", "chưa chốt được"; lỗi ASR "Gia ra" |
| m04 | Xưởng gỗ | Nhân viên nói "mình chốt … đi anh"; chuyển cho giám đốc vắng mặt; "ai đó check giúp"; "Ừ." trước một đề xuất |
| m05 | Chuỗi F&B | "Ok chốt" rồi "thôi khoan"; câu hỏi không kết luận; hạn "thứ Tư" khi họp thứ Sáu |

## Lệnh

```bash
make agreement      # nhãn của bạn vs đáp án
make eval-keyword   # baseline keyword vs đáp án
make synth          # sinh 15 bản nháp (cần GEN_* hoặc LLM_* trong .env)
```

Sinh xong phải **tự duyệt** từng bản nháp (transcript tự nhiên chưa? nhãn đúng hướng dẫn chưa?) rồi mới chép sang `raw/` và `gold/`.
