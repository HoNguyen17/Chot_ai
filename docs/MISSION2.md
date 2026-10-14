# Mission 2 · Chốt: bản nộp

> Demo: **https://chot.nashng.dev** → bấm "Dùng transcript mẫu" (m01–m05 chạy lại sự kiện của một lần gọi LLM thật, không cần key).
> Số liệu trong file này lấy từ `data/runs/` (không commit vì có thể chứa nội dung họp) và [EVAL_LOG.md](EVAL_LOG.md). Run chính: `20261014-042750-replay` = sự kiện của lần chạy LLM thật `20261014-042208-llm` (gpt-4.1-mini) đi qua bộ luật hiện tại. Sự kiện m01–m05 của run đó được commit ở `apps/api/demo_events/` để ai cũng kiểm lại được.
>
> Chỗ đánh dấu **[Nash xác nhận]** là chỗ mình chưa chắc, cần Nash sửa trước khi nộp.

## 1. Đề yêu cầu gì → nằm ở đâu trong sản phẩm

| Yêu cầu của đề | Trong Chốt | Ở đâu |
|---|---|---|
| Transcript (đầu vào) | Dán text `[mm:ss] Tên: câu nói` + dòng `# participants` | màn hình chính, `adapters/parsing/` |
| Diễn biến | Mỗi câu được LLM gán **sự kiện** (`propose / object / agree / revise / defer / reopen / assign / commit / decline / …`), theo chủ đề (`thread`) | `domain/enums.py` (`EventKind`), `prompts/extract_events.md` |
| Cấu trúc | **Decision Ledger**: mỗi mục có `type` + `status` + owner / hạn / người quyết | `domain/models.py` (`Item`), `domain/status_rules.py` |
| Bằng chứng | `Item.evidence` = mã câu (`u019`) + trích dẫn + giờ + người nói. Trích dẫn không khớp transcript thì mục bị bỏ | `domain/grounding.py` |
| Quyết định | `type = decision` (phương án được chọn) và `option` (phương án không được chọn) | `domain/enums.py` |
| Công việc | `type = task`, có `owner`, `deadline` | như trên |
| Vướng mắc | `type = blocker` | như trên |
| Yêu cầu – phản hồi | `type = request` / `feedback` | như trên |
| **Chưa chốt** | `status = needs_confirmation` (tạm chốt, mơ hồ, owner chưa nhận) / `deferred` (hoãn, chờ người khác quyết) / `open` + `type = open_question` | `domain/enums.py` (`Status`) |
| Ý kiến ban đầu thay đổi → giữ kết luận cuối | Phương án cũ thành `option · superseded`, mục chốt có `supersedes` trỏ về nó và flag "đã đổi ý trong cuộc họp — xem timeline" | `domain/status_rules.py` |
| Người kiểm lại | Màn duyệt: nút "Duyệt & xuất bản" bị khoá khi còn mục "Cần xác nhận" | `apps/web/src/app/meetings/[id]/page.tsx` |
| Dùng tiếp | Xuất biên bản Markdown, task list CSV, JSON | `adapters/export/exporters.py` |

## 2. Ba câu hỏi bắt buộc

### Q1 · Phần quan trọng nhất đã làm, và vì sao nó chứng minh được tính khả thi?

**Phần quan trọng nhất: tách việc "gán nhãn" khỏi việc "kết luận".** LLM chỉ nói câu này là đề xuất, phản đối hay đồng ý. Trạng thái cuối do luật trong code suy ra (`status_rules.py`, [ADR-0002](adr/0002-llm-labels-code-decides.md)). Bài toán khó của đề (ý kiến đổi nhiều lần) nằm đúng ở chỗ này: một câu "Ok vậy đi email" giữa họp trông rất giống quyết định.

Vì sao chứng minh được: cùng 25 cuộc họp, cùng nhãn gold, cùng model gpt-4.1-mini.

| Hệ thống | Chốt nhầm ⭐ | Phương án cũ được gắn "bị thay thế" | Trạng thái cuối đúng | Precision / Recall mục |
|---|---|---|---|---|
| Lọc keyword ("chốt", "ok"…) | 57,6% (19/33) | 0% | 63,6% | 87,5% / 20,0% |
| 1 prompt tóm tắt | 54,3% (25/46) | 0% | 95,5% | 81,5% / 33,7% |
| **Chốt**, chạy đầu-cuối `042208-llm` | **4,8% (1/21)** | 78,9% | 90,9% | 73,8% / 51,7% |
| **Chốt**, cùng sự kiện, luật hiện tại `042750-replay` | **0% (0/20)** | 78,9% | 90,9% | 73,8% / 51,7% |

"Chốt nhầm" = trong các mục hệ thống ghi "Đã chốt", bao nhiêu mục gold nói là chưa chốt. Hai baseline cứ thấy "chốt"/"ok" là ghi quyết định, nên sai hơn một nửa và không bao giờ biết phương án nào đã bị thay. Chốt ghi ít "Đã chốt" hơn (20–21 so với 22 trong gold) nhưng gần như không ghi nhầm. Đó đúng là đánh đổi mình chọn ([ADR-0003](adr/0003-precision-over-recall.md)): bỏ sót thì người duyệt bổ sung được, ghi nhầm thì cả nhóm làm sai.

Trạng thái cuối của tóm tắt cao (95,5%) vì nó gắn "đã chốt" cho gần như mọi thứ nên trúng phần lớn mục thật sự đã chốt. Chỉ số này phải đọc cùng chỉ số chốt nhầm.

### Q2 · Đã thay đổi gì so với Mission 1, và vì sao?

So [PRD §5 "Kế hoạch 3 ngày"](PRD.md) với git log từ `314420f` (codebase ban đầu, 13/10 23:34) tới `ee29649` (deploy, 14/10 05:15) và [EVAL_LOG](EVAL_LOG.md).

| Kế hoạch Mission 1 | Thực tế | Điều gì khiến đổi |
|---|---|---|
| 3 ngày: dữ liệu → lõi → dùng được | Lõi (domain, luật, parser, baseline, API, màn duyệt) có sẵn trong `314420f`. Phần Mission 2 là dữ liệu, eval, tinh chỉnh, deploy: 17 commit trong khoảng 6 giờ | Hạn nộp ngắn. Ưu tiên có số eval thật hơn thêm tính năng |
| Bộ test 15–20 transcript | **25**: m01–m05 + m06–m20 sinh từ 15 kịch bản bẫy (`make synth`, `data/synthetic/scenarios.json`) + m21–m25 viết thêm cho bẫy còn thiếu (quyết định ngầm, 2 đồng chủ trì, nhắc quyết định họp trước, giao việc cho người vắng mặt) | Chỉ m01–m05 thì gold có rất ít quyết định "đã chốt", sai một mục là tỷ lệ nhảy 20%. 25 cuộc họp cho 22 quyết định final, đủ để đọc được tỷ lệ. [Nash xác nhận lý do; và m01–m05 là họp thật có consent hay kịch bản tự viết?] |
| Gán nhãn theo LABELING_GUIDE | Thêm **13 quy ước** (Nash, 14/10) trong lúc gán nhãn | Đo nhãn gold so với đáp án tham khảo: lần đầu lệch 16,7% (m01–m05), có quy ước rồi còn 4,5% (m01–m25). Nhãn chưa thống nhất thì đo LLM cũng vô nghĩa |
| "Tách chủ đề" là một bước riêng trước khi trích sự kiện | Gộp vào **một lời gọi LLM**: prompt trả cả `threads` lẫn `events`, mỗi phương án có một `key` cố định | Lỗi lớn nhất ở run đầu (`033444-llm`) là LLM đặt key/thread khác nhau cho cùng một phương án → luật ghép sai cặp đề xuất–đồng ý. Sửa trong prompt: chốt nhầm 17,6% → 5,3% (`cef2354`). [Nash xác nhận: có phải ngay từ đầu đã định gộp, hay đổi sau run đầu?] |
| Model: PRD dẫn GPT-5 mini | **gpt-4.1-mini** qua adapter OpenAI-compatible có sẵn | Có cân nhắc Claude Haiku nhưng bỏ: cần viết adapter mới và trả lỗi 400 với `temperature=0`. Đổi model chỉ cần sửa `.env` |
| Tinh chỉnh sau eval (PRD không nói làm ở prompt hay ở luật) | Cải thiện chủ yếu nhờ **luật** | Prompt: 17,6% → 5,3%. Luật (replay, 0 token): 5,3% → 0%. Chạy lại đầu-cuối thì LLM gán `agree` cho câu "Ừ." dù prompt đã cấm → lên lại 4,8%. Thêm luật chặn (`ccf3042`) → 0%. LLM không ổn định giữa các lần chạy, nên chỗ nào quan trọng phải có luật giữ |
| Grounding 2 tầng: tầng 1 chặn cứng, tầng 2 người chấm ≥ 95% | Tầng 1 làm đúng như kế hoạch (100% ở mọi run). Tầng 2 **chưa có người chấm**. Thay bằng kiểm tra tự động: người chốt phải là chủ trì, câu chốt mới nhất phải của đúng người đó, không có rào đón, owner phải có trong danh sách | Không có người chấm thứ hai trong thời gian này. Kiểm tra tự động bắt được phần "cấu trúc", chưa bắt được trường hợp trích dẫn đúng câu nhưng sai ý |
| Màn duyệt, export md/JSON/CSV, eval so 2 baseline | Làm đủ. Baseline keyword ban đầu chỉ đo trên m01–m05, nay đo lại trên gold m01–m25 | Để ba hệ thống so trên cùng một bộ |
| Không có trong kế hoạch | **Deploy demo công khai** (Vercel + Railway), demo m01–m05 replay sự kiện LLM thật, transcript mới gọi LLM có giới hạn ký tự và rate limit | Mission 2 cần demo chạy được. Replay để không tốn token và để kết quả trên demo truy được về một run thật |
| PostgresRepository + Supabase | **Chưa làm**, vẫn InMemory | Hết thời gian; không ảnh hưởng tới câu hỏi chính là "chốt có đúng không" |
| Phỏng vấn 3–5 trưởng nhóm SME, pilot 4 tuần | Chưa làm | Ngoài phạm vi Mission 2. [Nash xác nhận: đã phỏng vấn ai chưa?] |

### Q3 · Loại thông tin nào dễ sai nhất, và làm sao để không bịa?

**Theo số lượng lỗi** (run `042750-replay`, so với gold):

| Nhóm | Precision | Recall | Hệ thống ra / gold |
|---|---|---|---|
| Task | 95,7% | 88,2% | 70 / 76 |
| Quyết định + phương án | 80,2% | 82,3% | 81 / 79 |
| Yêu cầu + phản hồi | 45,5% | 22,7% | 11 / 22 |
| Kiến thức (thông tin, ràng buộc) | 36,5% | 29,7% | 52 / 64 |
| **Vướng mắc** | 100% | **9,5%** | 7 / 74 |

Vướng mắc sai nhiều nhất: gold có 74, hệ thống chỉ ra 7. Nguyên nhân chính: theo quy ước 1–2 của Nash, một câu phản biện có số liệu cụ thể ("tích hợp mất ba tuần, không kịp launch") vừa là vướng mắc vừa là kiến thức. Còn prompt hiện tại gán câu đó là `object` trong chuỗi quyết định, và luật không sinh mục `blocker` từ `object`. Lỗ hổng này đã được ghi trong [LABELING_GUIDE](LABELING_GUIDE.md) từ trước và chưa sửa. Task và owner thì gần đúng hết: owner đúng 100%, hạn đúng 100%.

**Theo mức độ gây hại** thì trạng thái quyết định vẫn là chỗ nguy hiểm nhất: chỉ một lần chạy lại, LLM đã biến "Ừ." thành đồng ý (case 6). Nên các lớp dưới đây đều nhắm vào quyết định:

1. **LLM chỉ gán sự kiện, không trả `status`.** Không có đường nào để LLM tự ghi "Đã chốt".
2. **Luật quyết trạng thái.** "Đã chốt" cần: người chủ trì đồng ý, không rào đón ("tạm thời", "nếu mà"), không bị lật sau đó. Đồng ý chỉ bằng "Ừ."/"Dạ." → Cần xác nhận. Đồng chủ trì chưa đồng ý → Cần xác nhận.
3. **Grounding tầng 1 chặn cứng.** Trích dẫn phải nằm trong đúng câu được trỏ tới; không khớp thì bỏ mục. 100% ở mọi run.
4. **Không bịa người.** Owner không có trong danh sách người tham gia (gồm cả người vắng mặt được ghi tên) bị xoá khỏi mục và gắn cờ; mục "Đã chốt" vi phạm kiểm tra tầng 2 bị hạ xuống Cần xác nhận. Số người bịa: 0 ở mọi run.
5. **Không chắc → "Cần xác nhận"** kèm lý do (flag) cho người duyệt, ví dụ "owner chưa xác nhận nhận việc", "đồng thuận có rào đón".
6. **Màn duyệt khoá xuất bản** khi còn mục Cần xác nhận. Người chủ trì phải bấm từng mục.

## 3. Bộ test case

Mỗi case ghi theo format của đề. "Kết quả thực tế" là ledger của run `042750-replay` (trừ khi ghi khác). `uNNN` = câu thứ NNN trong `data/raw/mXX.txt`.

### Case 1 · Đổi ý A → B, có tạm chốt ở giữa (m01)

- **Transcript:** m01, họp sync app giao hàng. u002 Minh đề xuất VNPay → u005 Lan đề xuất MoMo → u008 Hùng (chủ trì): "Thôi tạm thời đi MoMo nhé, để kịp launch đã." → u017 Minh: "Vậy hay là quay lại VNPay cho chắc?" → u019 Hùng: "Ok. Vậy chốt nhé: launch tháng 11 dùng MoMo, VNPay để phase 2."
- **Kỳ vọng:** D1 "MoMo cho launch, VNPay phase 2" = **Đã chốt**, bằng chứng u019 + u005. VNPay = **Bị thay thế**. "Tạm thời đi MoMo" (u008) = phương án tạm, **Bị thay thế**.
- **Kết quả thực tế:** D1 `final`, bằng chứng u019 "Vậy chốt nhé: launch tháng 11 dùng MoMo, VNPay để phase 2" + u005, flag "đã đổi ý trong cuộc họp — xem timeline". O1 VNPay `superseded` (u002, u017). Không có mục riêng cho lần tạm chốt u008.
- **Đạt.** Kết luận cuối đúng, phương án cũ được giữ làm lịch sử. Thiếu mục "tạm chốt" nên supersession của m01 là 50%.
- **Điều học được:** câu "tạm thời…" của chính người chủ trì không bị ghi thành quyết định, vì luật coi đó là đồng ý có rào đón. Muốn hiện được "đã từng tạm chốt MoMo" thì cần luật sinh `option` cho lần tạm chốt (quy ước 3), hiện chưa có.

### Case 2 · Đổi ý 3 lần, có khách tham gia (m10)

- **Transcript:** m10, họp với khách về đăng nhập app. u002 Tuyết (khách): OTP SMS → u004 Kim: email + mật khẩu → u005 Nam (chủ trì): "Ok vậy đi email với mật khẩu." → u006 Tuyết: khách ít dùng email → u007 Đức: Zalo → u008 Hòa: duyệt Zalo mất ba tuần → u009 Tuyết: "Thôi quay lại OTP SMS, nhưng chỉ gửi OTP khi đăng nhập trên máy mới thôi." → u011 Nam: "Được. Chốt đăng nhập OTP SMS, chỉ gửi khi đăng nhập trên thiết bị mới. Email và Zalo bỏ."
- **Kỳ vọng:** D1 OTP SMS chỉ khi thiết bị mới = **Đã chốt** (u011, u009). OTP mọi lần, email, Zalo đều **Bị thay thế**.
- **Kết quả thực tế:** D1 `final`, bằng chứng u011 "Chốt đăng nhập OTP SMS, chỉ gửi khi đăng nhập trên thiết bị mới. Email và Zalo bỏ" + u009. O1 OTP SMS, O2 email (u004), O3 Zalo (u007) đều `superseded`. Câu "Ok em." của khách (u012) không làm thay đổi gì.
- **Đạt** cho chuỗi quyết định. Ngoài chuỗi này thì thiếu 3 vướng mắc (chi phí SMS, khách ít dùng email, chờ duyệt Zalo) và task của Tuyết "hỏi lại sếp về lịch nghỉ lễ" (u016).
- **Điều học được:** "Ok vậy đi email" ở u005 là câu nguy hiểm nhất của bộ test: chủ trì nói rõ, không rào đón. Luật vẫn đúng vì có sự kiện sau đó lật lại. Hệ thống tóm tắt 1 prompt không có khái niệm "bị thay thế" nên không làm được loại này.

### Case 3 · Tạm chốt, không ai xác nhận lại (m07)

- **Transcript:** m07, kho vận. u003 Hải đề xuất dời hàng fast-moving lên dock 1 → u004, u005 nêu chi phí mapping SKU và quy định PCCC → u006 Tâm (chủ trì): "Tạm thời mình đi phương án dời fast-moving lên dock 1 nha, để anh xem lại mặt bằng đã." Hết họp không nhắc lại.
- **Kỳ vọng:** D1 = **Cần xác nhận** (u006, u003).
- **Kết quả thực tế:** D1 `needs_confirmation`, flag "đồng thuận có rào đón", bằng chứng u006 + u003.
- **Đạt.**
- **Điều học được:** "tạm thời" + "để anh xem lại" là rào đón kép. Chỉ cần một tín hiệu là đủ hạ xuống Cần xác nhận; danh sách tín hiệu nằm ở `domain/text.py`.

### Case 4 · "Thôi khoan": đã chốt rồi bị lật (m11)

- **Transcript:** m11, marketing shop thời trang. u004 Trúc: mua 2 tặng 1 áo thun → u005 Linh (chủ trì): "Ok chốt mua 2 tặng 1 áo thun cho 11.11." → u006 Khôi: kho chỉ còn 300 áo → u007 Linh: "Ờ thôi khoan. Vậy khuyến mãi 11.11 chưa chốt được, đợi Khôi báo số hàng về rồi tính."
- **Kỳ vọng:** D1 khuyến mãi 11.11 = **Hoãn** (u007). Hai phương án (giảm 30%, mua 2 tặng 1) = `option · open` (quy ước 4).
- **Kết quả thực tế:** D1 `deferred`, bằng chứng u007, flag "đã có đồng thuận nhưng bị lật lại". Không có mục phương án nào.
- **Đạt một phần.** Không ghi "mua 2 tặng 1" thành đã chốt, tức là đúng phần quan trọng nhất. Nhưng người đọc biên bản không thấy hai phương án đang cân nhắc.
- **Điều học được:** cùng loại bẫy này, ở m20 hệ thống ra `open_question` "Chọn mặt bằng chi nhánh thứ 5" thay vì quyết định `deferred`. Vẫn không chốt nhầm, nhưng cách trình bày "chưa chốt" chưa nhất quán giữa các cuộc họp.

### Case 5 · Yêu cầu của khách → việc phải làm (m02)

- **Transcript:** m02, agency marketing. u018 Phát: "À, bên khách có request làm thêm bản tiếng Anh cho landing page, cho nhà phân phối nước ngoài." → u019 Ngọc (chủ trì): "Cái đó tính thêm phí, để chị báo giá lại với khách."
- **Kỳ vọng:** R1 yêu cầu của khách = `request · open` (u018). T4 Ngọc báo giá lại = `task · open`, owner Ngọc (u019).
- **Kết quả thực tế:** R1 `request open`, quote u018 "bên khách có request làm thêm bản tiếng Anh cho landing page". T2 `task open`, owner Ngọc, quote u019 "để chị báo giá lại với khách".
- **Đạt.**
- **Điều học được:** yêu cầu nói thẳng ra thì bắt được. Nhưng trên cả 25 cuộc họp, nhóm yêu cầu/phản hồi chỉ bắt được 22,7%. Yêu cầu nói gián tiếp thì hay bị bỏ sót (m01 u024 "bên marketing hỏi ngày cụ thể" không thành mục nào), góp ý thì hay bị ghi thành câu hỏi mở (m01 u012 "nút 'Tiếp tục' hơi nhỏ").

### Case 6 · Mơ hồ: chủ trì chỉ đáp "Ừ." (m04)

- **Transcript:** m04, xưởng gỗ. u014 Mỹ: "Em có ý này, phiếu xuất kho viết tay hay sai số, mình chuyển qua file Excel cho dễ đối chiếu." → u015 Sơn (chủ trì): "Ừ." → u016: "Ok vậy thôi, giải tán."
- **Kỳ vọng:** D3 chuyển sang Excel = **Cần xác nhận** (quy ước 5: "Ừ." là đồng ý gián tiếp).
- **Kết quả thực tế:**
  - Lần chạy đầu-cuối `042208-llm`: LLM gán `agree` cho u015 (quote "Ừ") dù prompt đã dặn không làm vậy → luật tin → D3 `final`. **Đây là chốt nhầm thật**, lỗi duy nhất làm run đó lên 4,8%.
  - Sau khi thêm luật "agree trên câu chỉ có Ừ/Dạ là đồng ý gián tiếp" (`ccf3042`), cùng sự kiện đó → D3 `needs_confirmation`, flag "chủ trì chỉ đáp 'Ừ.' — đồng ý gián tiếp, cần xác nhận".
- **Đạt (sau khi sửa luật).** Chưa đạt ở lần chạy đầu-cuối.
- **Điều học được:** không thể dựa vào prompt để chặn lỗi quan trọng. Lần chạy trước LLM gán đúng, lần sau gán sai, cùng prompt. Luật thì lần nào cũng chặn.

### Case 7 · Mơ hồ: "Dạ, để em xem lại ạ." khi được giao việc (m01)

- **Transcript:** m01 u022 Hùng: "Minh tìm hiểu phí VNPay cho phase 2, gửi anh bảng so sánh tuần sau nhé?" → u023 Minh: "Dạ, để em xem lại ạ."
- **Kỳ vọng:** T2 = **Cần xác nhận**, owner Minh, không có hạn cụ thể.
- **Kết quả thực tế:** T3 `needs_confirmation`, owner Minh, hạn để trống, flag "owner từ chối hoặc trì hoãn" + "hạn chót chưa cụ thể", bằng chứng u022 + u023.
- **Đạt.**
- **Điều học được:** "Dạ" trong tiếng Việt thường chỉ là lịch sự. Hệ thống không suy ra "tuần sau" thành một ngày cụ thể, vì đoán sai hạn còn tệ hơn để trống.

### Case 8 · THẤT BẠI: quyết định nằm trong câu giao việc (m03)

- **Transcript:** m03, sprint planning. u015 Bảo: "server staging hết dung lượng, deploy bản mới lên không được." → u016 Quân (chủ trì): "Bảo tạo ticket trên Gia ra, anh duyệt nâng cấp ổ đĩa. Mai làm luôn nhé." → u017 Bảo: "Dạ để em xem lại cấu hình rồi báo anh."
- **Kỳ vọng:** D2 nâng cấp ổ đĩa staging = **Đã chốt** (u016, quy ước 6). T2 tạo ticket = Cần xác nhận, owner Bảo.
- **Kết quả thực tế:** không có quyết định nào về ổ đĩa. LLM chỉ gán `assign` cho u016 → chỉ ra T2 `needs_confirmation` "Giao Bảo tạo ticket Gia ra, anh duyệt nâng cấp ổ đĩa, làm ngày mai" và một câu hỏi mở "Server staging". Ngoài ra còn sinh thừa D2 "Đồng ý bỏ export PDF để kịp 15/11" (`needs_confirmation`, u011 "Em ok, scope nhỏ lại thì test kịp"), gold không có mục này.
- **Chưa đạt.** Bỏ sót 1 quyết định đã chốt + 1 mục thừa.
- **Điều học được:** prompt vòng 1 đã thêm hướng dẫn "quyết + giao việc trong một câu → `agree` + `assign`", nhưng ở câu này LLM vẫn không làm theo. Lỗi theo hướng an toàn (không chốt nhầm), nhưng biên bản thiếu một quyết định thật. Cần thêm ví dụ kiểu này vào few-shot (m00) hoặc một luật nhận "anh duyệt…" của chủ trì.

### Case 9 · THẤT BẠI: chốt rồi giữ nguyên, nhưng bị hạ xuống "Cần xác nhận" (m02)

- **Transcript:** m02 u009 Ngọc (chủ trì): "Rồi, budget split. Chốt: 60% Facebook ads, 40% TikTok." → u010 Hân phản biện CPM TikTok tăng → u011 Ngọc: "Chị biết, nhưng vẫn giữ 60-40 nha, sang tháng 1 mình review lại theo số thực tế."
- **Kỳ vọng:** D2 = **Đã chốt** (u011, u009). "Review lại tháng 1" là kế hoạch kiểm tra, không phải rào đón.
- **Kết quả thực tế:** D2 `needs_confirmation`, flag "đồng thuận có rào đón", bằng chứng u011. LLM tự đặt `hedged = true` cho u011 dù câu không chứa tín hiệu rào đón nào trong `domain/text.py`.
- **Chưa đạt.** Bỏ sót một quyết định đã chốt.
- **Điều học được:** đây là cái giá của "precision trước recall": một quyết định thật bị đẩy cho người duyệt. Có thể bỏ trường `hedged` của LLM và chỉ tin danh sách tín hiệu trong code, nhưng như vậy sẽ mất khả năng bắt rào đón kiểu mới. Chưa quyết, cần thêm dữ liệu.

### Case 10 · THẤT BẠI hệ thống: gần như không bắt được vướng mắc

- **Transcript:** ví dụ m01 u004 Lan: "Em thấy VNPay phí giao dịch cao hơn, mà tích hợp theo doc của họ chắc mất tầm ba tuần, không kịp launch." · u006 Minh: khách lớn tuổi quen chuyển khoản · u015 Lan: "sandbox MoMo thì đang lỗi, callback trả về sai mã giao dịch."
- **Kỳ vọng:** 3 vướng mắc B1–B3 `open` (quy ước 1–2).
- **Kết quả thực tế:** m01 không có mục `blocker` nào. LLM gán cả u004, u006, u015 là `object` trong chuỗi thanh toán, và luật không sinh mục nào từ `object`. Trên 25 cuộc họp: 7/74 vướng mắc.
- **Chưa đạt.**
- **Điều học được:** lỗi nằm ở thiết kế, không phải do LLM. Một câu phản biện vừa là bước trong chuỗi quyết định, vừa là vướng mắc cần theo dõi; schema hiện tại chỉ cho nó là một. Cách sửa dự kiến: luật sinh thêm `blocker` từ `object` có nội dung cụ thể (chi phí, thời gian, rủi ro).

### Tổng hợp

| # | Tình huống | Cuộc họp | Kết quả |
|---|---|---|---|
| 1 | Đổi ý A→B có tạm chốt | m01 | Đạt (thiếu mục tạm chốt) |
| 2 | Đổi ý 3 lần, có khách | m10 | Đạt |
| 3 | Tạm chốt không xác nhận | m07 | Đạt |
| 4 | "Thôi khoan" | m11 | Đạt một phần |
| 5 | Yêu cầu của khách | m02 | Đạt |
| 6 | "Ừ." của chủ trì | m04 | Đạt sau sửa luật / chưa đạt ở run đầu-cuối |
| 7 | "Dạ, để em xem lại" | m01 | Đạt |
| 8 | Quyết định trong câu giao việc | m03 | **Chưa đạt** |
| 9 | Chốt giữ nguyên bị hạ | m02 | **Chưa đạt** |
| 10 | Vướng mắc | m01 + 25 cuộc họp | **Chưa đạt** |

Cả 6 lỗi còn lại của run (`ERRORS.md` trong run, không commit) đều theo hướng "ghi thiếu" hoặc "đẩy cho người duyệt", không có lỗi ghi nhầm thành đã chốt: m02 D2 (case 9), m03 D2 (case 8), m02 D3 (key gộp, "thích concept 2" ra `open`), và ba task m04 / m14 / m25 mà LLM không gán `commit` cho câu nhận việc ("Ok anh, sáng thứ Hai em gửi") nên bị để Cần xác nhận.

## 4. Hạn chế đã biết

- **Lưu trong RAM.** Không có DB; tối đa 500 cuộc họp, server restart là mất. `PostgresRepository` mới là khung.
- **Bộ test nhỏ, một người gán.** 25 cuộc họp, 315 mục, 22 quyết định đã chốt. Một lỗi chốt nhầm = khoảng 5 điểm %. Nhãn do Nash gán, chưa có người thứ hai để đo độ đồng thuận.
- **Phần lớn là dữ liệu tổng hợp.** m06–m25 là kịch bản tổng hợp, viết với sự hỗ trợ của LLM rồi duyệt tay. Họp thật có nhiều người nói chen, câu cụt, lỗi ASR hơn. [Nash xác nhận nguồn gốc m01–m05.]
- **Recall thấp: 51,7%.** Vướng mắc, kiến thức, phản hồi bị bỏ sót nhiều (Q3). Biên bản hiện đáng tin ở quyết định và task, chưa đầy đủ ở phần còn lại.
- **LLM không ổn định giữa các lần chạy.** Số 0% là replay sự kiện của một lần chạy qua luật mới; lần chạy đầu-cuối gần nhất là 4,8%. Chưa chạy lại đầu-cuối sau khi sửa luật.
- **Chưa có ASR.** Đầu vào phải là transcript text có tên người nói.
- **Dữ liệu đi ra nước ngoài.** API chạy trên Railway, LLM là OpenAI, nên transcript rời khỏi Việt Nam. Với dữ liệu họp thật của doanh nghiệp cần xem lại theo Luật Bảo vệ dữ liệu cá nhân (Luật 91/2025/QH15) [Nash xác nhận số hiệu và điều khoản áp dụng]. Bản demo chỉ nên dùng transcript mẫu.
- **Rate limit chỉ đúng với 1 instance.** Bộ đếm (10 lượt/giờ/IP, 60 lượt/giờ toàn hệ thống) nằm trong RAM; scale ra nhiều instance thì mỗi instance đếm riêng.
- **Kết quả eval không commit.** `data/runs/` bị gitignore; người ngoài chỉ kiểm lại được m01–m05 qua `apps/api/demo_events/`.
