# DATAMATE CHALLENGE 2026 — BẢN TỔNG QUAN CHIẾN LƯỢC DÀNH CHO TEAM AGENTICAL

> **Dự án:** Zalo AI Challenge 2026 — DataMate: Talking To Your Data Through Agentic AI  
> **Team:** Agentical  
> **Repository:** [https://github.com/kieuwangtruong/Agentical](https://github.com/kieuwangtruong/Agentical)  
> **Thời điểm công bố:** Tháng 11/2026  
> **Phương châm hành động:** *Inspect → Plan → Implement → Test → Evaluate → Improve → Package → Submit*

---

## 1. Mục tiêu và Bản chất cuộc thi

Mục tiêu của cuộc thi là xây dựng một hệ thống **Natural Language to Tabular Data / SQL Agent** có khả năng trả lời các câu hỏi kinh doanh bằng tiếng Việt dựa trên bộ dữ liệu hỗn hợp (CSV, Excel, SQLite) của nhiều doanh nghiệp khác nhau.

### Chỉ số cốt lõi: Penalized Accuracy
Điểm số của bài thi được tính theo công thức phạt nghiêm ngặt:
$$\text{Penalized Accuracy} = \frac{\text{Số câu đúng} - \text{Số câu sai}}{\text{Tổng số câu hỏi}}$$

- **Đáp án đúng:** $+1$ điểm.
- **Đáp án sai:** $-1$ điểm.
- **Bỏ trống / Abstain:** $0$ điểm.
- **Trả lời một câu thực sự không trả lời được (`unanswerable`):** Tính là sai ($-1$ điểm). Nếu nhận diện đúng câu không trả lời được và trả về `unanswerable`, nhận $+1$ điểm.

> ⚠️ **Quy tắc sống còn:** Một đáp án đoán mò bị sai sẽ triệt tiêu một câu làm đúng! Chiến lược phòng thủ bằng **Abstain** khi độ tin cậy thấp là yếu tố quyết định thứ hạng trên bảng xếp hạng (Leaderboard).

### Ràng buộc kỹ thuật bắt buộc
1. **Offline 100%:** Khi inference trong Docker không có internet, không gọi API thương mại bên ngoài (OpenAI, Anthropic...).
2. **Giới hạn Model:** Tổng tham số của tất cả mô hình $\le$ 15 tỷ (15B params, tính cả embedding, reranker, MoE). Phải phát hành trước 01/10/2026.
3. **Thời gian chạy:** Toàn bộ Private Test phải chạy xong trong tối đa **6 giờ**.
4. **Zero-shot Business Generalization:** Private Test chứa các loại hình kinh doanh hoàn toàn mới chưa từng xuất hiện ở Train hay Public Test. Tuyệt đối không hard-code theo ID hay luật riêng của train.
5. **Đóng gói Docker chuẩn:** Nhận input mount tại `/data`, xuất kết quả ra `/result/submission.jsonl`, log tại `/result/logs/`.

---

## 2. Kết quả Audit dữ liệu thực tế (Train & Public Test)

Sau khi kiểm tra trực tiếp 100% dữ liệu:

| Chỉ số | Tập Train | Tập Public Test |
|---|---|---|
| Số câu hỏi | **3.000 câu** (`questions.jsonl`) | **1.000 câu** (`questions.jsonl`) |
| Số doanh nghiệp | **30 businesses** (`biz_101` – `biz_130`) | **14 businesses** (`dev_001` – `dev_014`) |
| Số lượng file | 107 xlsx, 20 csv, 1 sqlite, 30 README | 69 xlsx, 10 csv, 1 sqlite, 14 README |
| Tổng dung lượng | ~180 MB | ~108 MB |
| Ngành hàng trong Rulebook | Cà phê, Nhà thuốc, VLXD | Thêm: **Mẹ & bé**, **Sửa xe**, **Điện thoại** |

### Các dị biệt dữ liệu cần đặc biệt lưu ý:
1. **File Excel đa dạng và có "bẫy" header:** Nhiều file Excel dòng đầu tiên là tiêu đề báo cáo hoặc ghi chú (như `biz_121`), dòng tiêu đề cột thật sự nằm ở dòng 1 hoặc dòng 2.
2. **Dữ liệu phân mảnh theo kỳ:** Một số shop tách bảng bán hàng thành nhiều file (`BanHang_2025.xlsx`, `BanHang_2026.xlsx` hoặc từng tháng ở `dev_002`, `dev_005`).
3. **Phân bố đáp án ở Train:**
   - `number`: **62.8%** (1.884 câu — tiền, số lượng, ngày công, giờ).
   - `percent`: **19.3%** (578 câu — tỷ lệ hủy, tăng trưởng, thị phần).
   - `list`: **6.4%** (193 câu — top k hàng, chuỗi doanh thu).
   - `date`: **4.8%** (145 câu — ngày cao điểm, ngày hết hạn).
   - `string`: **2.9%** (88 câu — tên món, tên khách).
   - `unanswerable`: **2.3%** (70 câu — dữ liệu không có thông tin hoặc kỳ ngoài khoảng ngày của shop).
   - `boolean`: **0.8%** (23 câu — tăng liên tục True/False).
   - `table`: **0.6%** (19 câu — bảng công nợ khách hàng).
4. **Cơ chế Alias (5.6% câu hỏi):** Hệ thống chấm chấp nhận cả tên đầy đủ lẫn mã (ví dụ: chấp nhận cả tên thuốc lẫn mã SKU `SP0003`, mã khách `KH0124`).

---

## 3. Kiến trúc giải pháp: "Deterministic-First Tabular Reasoning Engine"

Team Agentical sẽ tiếp cận theo mô hình kết hợp **Suy luận xác định (Deterministic Execution) + AI Agent điều hướng + Khiên phòng thủ điểm phạt**:

```
                       [ Câu hỏi tiếng Việt + as_of_date ]
                                       │
                                       ▼
                     [ Time Virtualizer & Rulebook Parser ]
                       (calendar.csv + rulebook.md động)
                                       │
                                       ▼
                     [ Question Intent & Schema Linker ]
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
       [ Phát hiện Unanswerable ]                     [ SQL / Code Generator ]
       (Thiếu bảng/cột, ngoài kỳ)                     (Local LLM < 15B params)
                │                                             │
                ▼                                             ▼
       {"type": "unanswerable"}                       [ In-Memory SQLite DB ]
       (Ăn chắc +1 điểm)                               (Thực thi tính toán 100%)
                                                              │
                                                              ▼
                                                     [ Result Verifier ]
                                               ┌──────────────┴──────────────┐
                                               ▼                             ▼
                                        [ Hợp lệ & tin cậy ]          [ Lỗi / Không chắc ]
                                               │                             │
                                               ▼                             ▼
                                        [ Định dạng JSONL ]           {"type": "abstain"}
                                        (number, percent...)          (Bảo toàn 0 điểm)
```

### 4 Khối chức năng nòng cốt:

1. **Khối Ảo hóa Dữ liệu (Universal Data Ingestion):**
   - Tự động nhận diện định dạng CSV, XLSX, SQLite.
   - Tự động phát hiện dòng header thật (loại bỏ dòng tiêu đề rác).
   - Chuẩn hóa ngày tháng, tiền tệ, nạp toàn bộ vào in-memory SQLite để tối ưu tốc độ.
2. **Khối Thời gian & Nghiệp vụ động (Time Virtualizer & Rule Engine):**
   - Giải mã các từ ngữ thời gian tương đối dựa vào `calendar.csv`: *"tuần này"*, *"tháng trước"*, *"dịp Tết"*, *"ca sáng"*, *"ca chiều"*.
   - Đọc trực tiếp `rulebook.md` của split đầu vào để lấy quy định về doanh thu (bỏ đơn hủy, trừ đơn trả hàng), cách xếp hạng, cách tính công nợ.
3. **Khối Sinh truy vấn (Neuro-Symbolic NL2SQL):**
   - Sử dụng mô hình mã nguồn mở tối ưu (dưới 15B params như Qwen2.5-Coder-7B / 14B hoặc Llama-3.1-8B) để chuyển câu hỏi sang câu lệnh SQLite Query.
   - Thực thi trên SQLite để đảm bảo tính toán số học chính xác 100%, không bị sai lệch từng đồng.
4. **Khối Khiên phòng ngự (The Abstain & Unanswerable Shield):**
   - Nhận diện các câu hỏi thiếu căn cứ để trả về `unanswerable` (+1 điểm).
   - Nếu SQL sinh lỗi, kết quả rỗng bất thường, hoặc không khớp entity, chủ động kích hoạt `abstain` (0 điểm) để không bị trừ điểm oan.

---

## 4. Kế hoạch hành động & Mốc thời gian (Roadmap)

| Giai đoạn | Thời gian | Mục tiêu chính | Đầu ra (Deliverables) |
|---|---|---|---|
| **Phase 1** | 29/10 – 02/11 | Audit dữ liệu, xây dựng Evaluator, chia tập Validation cố định | `tools/evaluator.py`, split validation 6 businesses |
| **Phase 2** | 03/11 – 06/11 | Xây dựng Data Ingestion Engine & End-to-end Baseline Pipeline | Baseline chạy được từ đầu đến cuối trên validation |
| **Phase 3** | 07/11 – 09/11 | Chạy Public Test submission đầu tiên, thiết lập Error Analysis | Submission hợp lệ nộp thử, báo cáo lỗi chi tiết |
| **Phase 4** | 10/11 – 12/11 | Nâng cấp Semantic Parser, Rulebook Engine, Time Engine | Cải thiện Penalized Accuracy trên validation |
| **Phase 5** | 13/11 – 15/11 | Đóng gói Docker, kiểm thử offline, tối ưu tốc độ < 6h | Docker image hoàn chỉnh, test ngắt mạng 100% |
| **Phase 6** | **16/11** | **HẠN CHÓT NỘP GIẢI PHÁP DOCKER (23:59 GMT+7)** | Nộp Docker image và tài liệu kỹ thuật |
| **Phase 7** | **20/11 – 23/11** | **THỰC THI PRIVATE TEST (Hạn chót: 23:59 ngày 23/11)** | Nộp kết quả Private Test |

---

## 5. Hướng dẫn làm việc nội bộ cho thành viên

### Cách lấy mã nguồn mới nhất:
```bash
git clone https://github.com/kieuwangtruong/Agentical.git
cd Agentical
```

### Cách tự đánh giá điểm số mô hình bằng Evaluator nội bộ:
Bộ chấm điểm chuẩn thể lệ đã được hoàn thiện tại [tools/evaluator.py](file:///d:/Agentical/tools/evaluator.py). Mỗi khi xuất file dự đoán `submission.jsonl`, hãy chạy:
```bash
python tools/evaluator.py path/to/submission.jsonl path/to/answers.jsonl
```
Kết quả sẽ xuất ra bảng phân tích chi tiết:
- Điểm tổng Penalized Accuracy.
- Số câu đúng, sai, abstain.
- Độ chính xác theo từng kiểu dữ liệu (`number`, `percent`, `list`, `date`, `string`, `table`, `boolean`, `unanswerable`).

### Nguyên tắc phối hợp nhóm:
1. **Mọi cải tiến phải được đo lường:** Không đưa code mới vào nếu không chứng minh được điểm Penalized Accuracy trên tập Validation tăng lên.
2. **Không commit dữ liệu thô:** File `.gitignore` đã được cấu hình chặn file `.zip` và thư mục `train/`, `public_test/` để tránh nặng repo.
3. **Tuân thủ đúng chuẩn Docker:** Code phải luôn đảm bảo chạy offline hoàn toàn và không phụ thuộc vào đường dẫn tuyệt đối của máy cá nhân.
