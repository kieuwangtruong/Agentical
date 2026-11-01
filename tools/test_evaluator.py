"""
Unit tests for evaluator.py to ensure robustness and correctness.
"""

import os
import sys
import json
import tempfile
from evaluator import evaluate, compare_answers

sys.stdout.reconfigure(encoding='utf-8')

def test_compare_answers():
    print("Testing compare_answers logic...")
    
    # 1. Number comparison
    assert compare_answers("number", 1000000, "number", 1000000)
    assert compare_answers("number", 1000000.0, "number", 1000000)
    assert not compare_answers("number", 1000001, "number", 1000000)
    
    # 2. Percent comparison
    assert compare_answers("percent", 12.4, "percent", 12.4)
    assert compare_answers("percent", 12.401, "percent", 12.40)
    assert not compare_answers("percent", 12.5, "percent", 12.4)
    
    # 3. String comparison with accents & case
    assert compare_answers("string", "Sting Dâu 330ml", "string", "Sting dâu 330ml")
    assert not compare_answers("string", "Sting dau 330ml", "string", "Sting dâu 330ml")  # missing accents
    
    # 4. String comparison with alias
    assert compare_answers("string", "SP0003", "string", "Cà phê sữa (M)", ["SP0003"])
    
    # 5. Boolean
    assert compare_answers("boolean", True, "boolean", True)
    assert not compare_answers("boolean", "true", "boolean", True)  # must be bool type
    
    # 6. Date
    assert compare_answers("date", "2026-08-15", "date", "2026-08-15")
    assert compare_answers("date", "2025-09", "date", "2025-09")
    assert not compare_answers("date", "15/08/2026", "date", "2026-08-15")
    
    # 7. Unanswerable
    assert compare_answers("unanswerable", None, "unanswerable", None)
    assert not compare_answers("number", 0, "unanswerable", None)
    
    # 8. List
    assert compare_answers("list", [1, 2, 3], "list", [1, 2, 3])
    assert compare_answers("list", ["SP0003", "Bạc xỉu"], "list", ["Cà phê sữa (M)", "Bạc xỉu"], [["SP0003"], []])
    assert not compare_answers("list", [3, 2, 1], "list", [1, 2, 3])  # order matters
    
    # 9. Table
    ref_table = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [["Chị Lan", 3200000], ["Anh Nam", 1500000]]
    }
    # Permuted row order is permitted per rulebook line 137
    pred_table_permuted = {
        "columns": ["khach_hang", "so_tien_no"],
        "rows": [["Anh Nam", 1500000], ["Chị Lan", 3200000]]
    }
    assert compare_answers("table", pred_table_permuted, "table", ref_table)
    
    print("All compare_answers unit tests PASSED!")

def test_full_evaluation_scenarios():
    print("Testing full evaluation edge scenarios...")
    with tempfile.TemporaryDirectory() as tmpdir:
        ref_file = os.path.join(tmpdir, "ref.jsonl")
        pred_abstain = os.path.join(tmpdir, "pred_abstain.jsonl")
        pred_wrong = os.path.join(tmpdir, "pred_wrong.jsonl")
        
        # Create 10 sample reference answers
        refs = [
            {"id": f"q_{i}", "type": "number", "answer": i * 100, "alias": []}
            for i in range(10)
        ]
        with open(ref_file, "w", encoding="utf-8") as f:
            for r in refs:
                f.write(json.dumps(r) + "\n")
                
        # 1. All Abstain
        with open(pred_abstain, "w", encoding="utf-8") as f:
            for r in refs:
                f.write(json.dumps({"id": r["id"], "type": "abstain"}) + "\n")
        rep_abstain = evaluate(pred_abstain, ref_file)
        assert rep_abstain.penalized_accuracy == 0.0
        assert rep_abstain.abstained == 10
        assert rep_abstain.correct == 0
        assert rep_abstain.incorrect == 0
        
        # 2. All Wrong
        with open(pred_wrong, "w", encoding="utf-8") as f:
            for r in refs:
                f.write(json.dumps({"id": r["id"], "type": "number", "answer": 999999}) + "\n")
        rep_wrong = evaluate(pred_wrong, ref_file)
        assert rep_wrong.penalized_accuracy == -1.0
        assert rep_wrong.incorrect == 10
        assert rep_wrong.correct == 0
        assert rep_wrong.abstained == 0

    print("All evaluation scenarios PASSED!")

if __name__ == "__main__":
    test_compare_answers()
    test_full_evaluation_scenarios()
