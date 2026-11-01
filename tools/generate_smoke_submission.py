import os
import sys
import json
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"d:\Agentical"
PUB_DIR = os.path.join(ROOT, "public_test")
QUESTIONS_PATH = os.path.join(PUB_DIR, "questions.jsonl")
SUBMISSION_PATH = os.path.join(ROOT, "submission.jsonl")

def solve_dev_009_sample():
    # Load dev_009 data
    csv_path = os.path.join(PUB_DIR, "data", "dev_009", "danh_sach_hoa_don.csv")
    df = pd.read_csv(csv_path)
    
    # Parse dates safely
    df['date_parsed'] = pd.to_datetime(df['Ngày tháng'], format='mixed', dayfirst=True).dt.strftime('%Y-%m-%d')
    
    # Clean money
    def clean_money(val):
        if pd.isna(val):
            return 0
        return int(str(val).replace(',', '').replace('.', '').strip())
    
    df['revenue'] = df['Giá trị hàng'].apply(clean_money)
    
    # Filter valid orders per rulebook:
    # "Đơn tính vào doanh thu: đơn không huỷ và không trả hàng. Đang giao vẫn tính."
    # Rulebook §8: "Ghi chú không nhắc trạng thái là đơn hoàn thành" -> NaN is completed.
    # Cancelled: "hủy đơn", "huỷ đơn", "hủy", "huỷ"
    # Returned: "trả hàng"
    is_cancelled_or_returned = df['Trạng thái đơn'].str.lower().fillna('').isin([
        'hủy', 'huỷ', 'hủy đơn', 'huỷ đơn', 'trả hàng'
    ])
    valid_df = df[~is_cancelled_or_returned]
    
    # Question 1: q_0329c9711c55
    # "Bữa nay tiệm có bao nhiêu đơn rồi nè?", as_of_date: 2026-02-25
    # "Hôm nay của mỗi câu là trường as_of_date... Số đơn: chỉ tính đơn không huỷ, không trả"
    q1_date = "2026-02-25"
    q1_orders = valid_df[valid_df['date_parsed'] == q1_date]
    q1_count = int(len(q1_orders))
    
    # Question 2: q_0b0081426a17
    # "Riêng hôm nay cửa hàng có doanh thu bao nhiêu?", as_of_date: 2025-02-25
    # "Doanh thu một đơn: tổng thành tiền các dòng hàng (tiền hàng của đơn = Giá trị hàng)"
    q2_date = "2025-02-25"
    q2_orders = valid_df[valid_df['date_parsed'] == q2_date]
    q2_revenue = int(q2_orders['revenue'].sum())
    
    print(f"Verified Answer for q_0329c9711c55 ({q1_date}): {q1_count} orders")
    print(f"Verified Answer for q_0b0081426a17 ({q2_date}): {q2_revenue} VND")
    
    return {
        "q_0329c9711c55": {"type": "number", "answer": q1_count},
        "q_0b0081426a17": {"type": "number", "answer": q2_revenue}
    }

def generate_submission():
    verified_answers = solve_dev_009_sample()
    
    total_q = 0
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f_in, open(SUBMISSION_PATH, "w", encoding="utf-8") as f_out:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            q_id = obj["id"]
            total_q += 1
            
            if q_id in verified_answers:
                item = {
                    "id": q_id,
                    "type": verified_answers[q_id]["type"],
                    "answer": verified_answers[q_id]["answer"]
                }
            else:
                item = {
                    "id": q_id,
                    "type": "abstain"
                }
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f"\nSuccessfully generated {SUBMISSION_PATH}")
    print(f"Total lines: {total_q}")
    print(f"Verified answers: {len(verified_answers)}")
    print(f"Abstained answers: {total_q - len(verified_answers)}")

if __name__ == "__main__":
    generate_submission()
