# Kế hoạch dự án: DataMate Challenge 2026 — Team Agentical

- **Team:** Agentical
- **Cuộc thi:** Zalo AI Challenge 2026 — DataMate: Talking To Your Data Through Agentic AI
- **Thời điểm khởi động:** 29/10/2026 (Hiện tại: 01/11/2026)
- **Hạn nộp Docker:** 23:59 ngày 16/11/2026 (GMT+7)
- **Hạn nộp Private Test:** 23:59 ngày 23/11/2026 (GMT+7)
- **Mục tiêu cốt lõi:** Tối đa hóa **Penalized Accuracy** ($(Đúng - Sai) / Tổng$), chạy offline 100%, dưới 15 tỷ tham số, tuân thủ chặt chẽ Docker specs.

---

## 1. Trạng thái các Phase (Cập nhật 01/11/2026)

| Phase | Nội dung chính | Thời hạn | Trạng thái | Ghi chú |
|---|---|---|---|---|
| **Phase 1** | Audit workspace, phân tích schema, xây dựng Scorer & Validation split | 29/10 – 02/11 | **IN_PROGRESS** | Đã hoàn thành audit, rulebook analysis, tools/evaluator.py (100% test pass), docs/TEAM_BRIEFING.md |
| **Phase 2** | End-to-end Baseline (Schema Loader, SQL/Execution engine, Format validator) | 03/11 – 06/11 | TODO | Xây pipeline xác định + rule/LLM engine |
| **Phase 3** | Chạy Public Test submission đầu tiên, Error Analysis trên Validation | 07/11 – 09/11 | TODO | Đảm bảo format chuẩn 100%, không dính lỗi phạt ngớ ngẩn |
| **Phase 4** | Tối ưu Semantics, Rule Engine, Time engine, Multi-table Join, Unanswerable/Abstain | 10/11 – 12/11 | TODO | Xử lý các edge cases của 6+ ngành hàng |
| **Phase 5** | Đóng gói Docker, kiểm tra Offline, Giới hạn tài nguyên & Tái lập (Reproducibility) | 13/11 – 15/11 | TODO | Kiểm tra `/data` -> `/result/submission.jsonl`, đo thời gian < 6h |
| **Phase 6** | Đóng băng nghiệm thu, kiểm tra Checksum, nộp giải pháp chính thức | 16/11 | TODO | Deadline 23:59 16/11/2026 |
| **Phase 7** | Chạy Private Test | 20/11 – 23/11 | TODO | Deadline 23:59 23/11/2026 |

---

## 2. Bảng theo dõi điểm số & Benchmark

| Phiên bản / Mốc | Ngày | Tập đánh giá | Đúng (+1) | Sai (-1) | Abstain (0) | Penalized Accuracy | Inference Time | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| *Chưa có baseline* | 01/11/2026 | Train (3000 câu) | - | - | - | - | - | Đang xây dựng bộ test nội bộ |

---

## 3. Quyết định kỹ thuật & Lý do (Design Decisions)

1. **Chiến lược tính toán xác định (Deterministic Computation over LLM Hallucination):**
   - Không để LLM tính nhẩm cộng/trừ/doanh thu trên bảng hàng chục nghìn dòng. Toàn bộ tính toán số học được nạp vào SQLite / DuckDB / Pandas và tính toán bằng SQL / Python xác định.
2. **Quy tắc Abstain như một tấm khiên phòng thủ (Defense Strategy):**
   - Cơ chế điểm: Đúng +1, Sai -1, Abstain 0.
   - Một đáp án đoán bừa nếu sai sẽ trừ mất 1 điểm của câu đúng. Khi độ tin cậy thấp hoặc không tìm thấy liên kết thực thể (entity linking fail), hệ thống sẽ chọn `abstain`.
3. **Phân tách rõ Unanswerable vs Abstain:**
   - `unanswerable`: Dữ liệu shop không có cột/bảng cần thiết, hoặc kỳ truy vấn hoàn toàn nằm ngoài khoảng thời gian dữ liệu tồn tại, hoặc câu hỏi không có căn cứ thực tế.
   - `abstain`: Dữ liệu có thể có, nhưng pipeline không phân tích được hoặc SQL không trả về kết quả đáng tin cậy.
4. **Validation Split theo Business (Leave-Businesses-Out):**
   - Tuyệt đối không chia ngẫu nhiên câu hỏi trong cùng một shop. Chia 6/30 businesses ở Train làm Holdout Validation (đại diện đủ ngành: Bán lẻ, Cà phê, Nhà thuốc, VLXD) để kiểm tra khả năng khái quát hóa sang shop chưa từng gặp (zero-shot business generalization).

---

## 4. Các rủi ro kỹ thuật chính & Biện pháp giảm thiểu

1. **Dữ liệu Excel nhiều cấu trúc lạ (Header lệch dòng, nhiều sheet, merged cells, file nhiều kỳ):**
   - Cần xây dựng Data Profiler tự động dò dòng tiêu đề thật (header row detection), tự động nối các file phân mảnh kỳ (`_2025`, `_2026`).
2. **Chênh lệch quy tắc giữa các split (Rulebook khác nhau):**
   - `public_test/rulebook.md` có thêm 3 ngành mới (Mẹ và bé, Sửa xe, Điện thoại) và nhiều định nghĩa mới. Hệ thống bắt buộc phải đọc `rulebook.md` được mount trong thư mục dữ liệu, không được hard-code rulebook của train.
3. **Thời gian chạy offline trên máy BTC (tối đa 6 giờ cho Private Test):**
   - Dữ liệu train có 252 file (~288 MB). Khi nạp vào SQLite/DuckDB cần tối ưu chỉ mục và index, tránh xử lý lặp lại cho từng câu hỏi.

