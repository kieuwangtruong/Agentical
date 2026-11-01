"""
DataMate Challenge 2026 - Official Evaluator & Scorer
Team: Agentical

Implements exact competition rules:
- Penalized Accuracy = (Correct - Incorrect) / Total
- Correct = +1
- Incorrect = -1
- Abstain / Missing = 0
- Type-aware matching (number, percent, date, boolean, string, list, table, unanswerable)
- Alias handling (SKU code, customer code, store name variations)
"""

import sys
import json
import math
import unicodedata
import re
from typing import Dict, Any, List, Tuple, Optional

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def normalize_string(s: str) -> str:
    """Normalize string per rulebook:
    Case-insensitive, strip whitespace, ignore surrounding punctuation,
    preserve Vietnamese accents.
    """
    if not isinstance(s, str):
        return str(s)
    s = unicodedata.normalize("NFC", s)
    s = s.strip().lower()
    # Normalize multiple whitespace into single space
    s = re.sub(r"\s+", " ", s)
    # Strip common enclosing punctuation
    s = s.strip("\"'.,-()[]{}")
    return s


def compare_numbers(pred: Any, target: Any, is_percent: bool = False) -> bool:
    """Compare numbers with floating point tolerance."""
    try:
        p_val = float(pred)
        t_val = float(target)
    except (ValueError, TypeError):
        return False

    if is_percent:
        # Percents are rounded to 2 decimal places
        return abs(p_val - t_val) <= 0.015 or math.isclose(p_val, t_val, abs_tol=1e-4)

    # If target is integer (e.g. VND, count)
    if isinstance(target, int) or (isinstance(target, float) and target.is_integer()):
        return round(p_val) == round(t_val) and abs(p_val - t_val) < 0.5
    
    # Float comparisons
    return math.isclose(p_val, t_val, rel_tol=1e-4, abs_tol=1e-4)


def match_single_string(pred_str: str, target_str: str, aliases: Optional[List[str]] = None) -> bool:
    """Match string against canonical target and any valid aliases."""
    norm_p = normalize_string(pred_str)
    if norm_p == normalize_string(target_str):
        return True
    
    if aliases:
        for alias in aliases:
            if isinstance(alias, str) and norm_p == normalize_string(alias):
                return True
    return False


def compare_answers(pred_type: str, pred_ans: Any, ref_type: str, ref_ans: Any, ref_alias: Optional[List[Any]] = None) -> bool:
    """Compare a prediction against ground truth according to type."""
    # Type mismatch is automatically incorrect
    if pred_type != ref_type:
        return False

    if ref_type == "unanswerable":
        return pred_type == "unanswerable"

    if ref_type == "number":
        return isinstance(pred_ans, (int, float)) and compare_numbers(pred_ans, ref_ans, is_percent=False)

    if ref_type == "percent":
        return isinstance(pred_ans, (int, float)) and compare_numbers(pred_ans, ref_ans, is_percent=True)

    if ref_type == "boolean":
        return isinstance(pred_ans, bool) and pred_ans == ref_ans

    if ref_type == "date":
        if not isinstance(pred_ans, str) or not isinstance(ref_ans, str):
            return False
        return pred_ans.strip() == ref_ans.strip()

    if ref_type == "string":
        if not isinstance(pred_ans, str):
            return False
        return match_single_string(pred_ans, str(ref_ans), ref_alias)

    if ref_type == "list":
        if not isinstance(pred_ans, list) or not isinstance(ref_ans, list):
            return False
        if len(pred_ans) != len(ref_ans):
            return False
        
        for i, (p_item, r_item) in enumerate(zip(pred_ans, ref_ans)):
            aliases_for_item = ref_alias[i] if (ref_alias and i < len(ref_alias) and isinstance(ref_alias[i], list)) else None
            
            if isinstance(r_item, (int, float)):
                if not isinstance(p_item, (int, float)) or not compare_numbers(p_item, r_item):
                    return False
            elif isinstance(r_item, str):
                if not isinstance(p_item, str) or not match_single_string(p_item, r_item, aliases_for_item):
                    return False
            else:
                if p_item != r_item:
                    return False
        return True

    if ref_type == "table":
        # Structure: {"columns": [...], "rows": [[...], ...]}
        if not isinstance(pred_ans, dict) or not isinstance(ref_ans, dict):
            return False
        
        ref_rows = ref_ans.get("rows", [])
        pred_rows = pred_ans.get("rows", [])
        if len(ref_rows) != len(pred_rows):
            return False

        # In tables, row order does not matter (per rulebook line 137)
        # Each row: [entity, measurement1, measurement2...]
        matched_pred_indices = set()
        for r_idx, r_row in enumerate(ref_rows):
            aliases_for_row = ref_alias[r_idx] if (ref_alias and r_idx < len(ref_alias) and isinstance(ref_alias[r_idx], list)) else None
            row_matched = False
            
            for p_idx, p_row in enumerate(pred_rows):
                if p_idx in matched_pred_indices or len(p_row) != len(r_row):
                    continue
                
                # Check entity
                p_entity, r_entity = p_row[0], r_row[0]
                if isinstance(r_entity, str):
                    if not isinstance(p_entity, str) or not match_single_string(p_entity, r_entity, aliases_for_row):
                        continue
                elif p_entity != r_entity:
                    continue
                
                # Check measurements
                measurements_ok = True
                for m_p, m_r in zip(p_row[1:], r_row[1:]):
                    if isinstance(m_r, (int, float)):
                        if not isinstance(m_p, (int, float)) or not compare_numbers(m_p, m_r):
                            measurements_ok = False
                            break
                    elif m_p != m_r:
                        measurements_ok = False
                        break
                
                if measurements_ok:
                    matched_pred_indices.add(p_idx)
                    row_matched = True
                    break
            
            if not row_matched:
                return False
        return True

    return False


class EvaluationReport:
    def __init__(self, total_questions: int):
        self.total = total_questions
        self.correct = 0
        self.incorrect = 0
        self.abstained = 0
        self.type_stats = {}  # type -> {"total": int, "correct": int, "incorrect": int, "abstained": int}
        self.errors = []      # list of error dicts for error analysis

    def record(self, q_id: str, is_correct: bool, is_abstain: bool, ref_type: str, pred_type: Optional[str], ref_ans: Any, pred_ans: Any, error_reason: str = ""):
        if ref_type not in self.type_stats:
            self.type_stats[ref_type] = {"total": 0, "correct": 0, "incorrect": 0, "abstained": 0}
        
        self.type_stats[ref_type]["total"] += 1
        
        if is_abstain:
            self.abstained += 1
            self.type_stats[ref_type]["abstained"] += 1
        elif is_correct:
            self.correct += 1
            self.type_stats[ref_type]["correct"] += 1
        else:
            self.incorrect += 1
            self.type_stats[ref_type]["incorrect"] += 1
            self.errors.append({
                "id": q_id,
                "ref_type": ref_type,
                "pred_type": pred_type,
                "ref_answer": ref_ans,
                "pred_answer": pred_ans,
                "reason": error_reason
            })

    @property
    def penalized_accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.correct - self.incorrect) / self.total

    @property
    def coverage(self) -> float:
        """Percentage of questions attempted (not abstained)."""
        if self.total == 0:
            return 0.0
        return (self.correct + self.incorrect) / self.total * 100

    @property
    def precision(self) -> float:
        """Accuracy strictly on attempted questions."""
        attempted = self.correct + self.incorrect
        if attempted == 0:
            return 0.0
        return self.correct / attempted * 100

    def print_summary(self):
        print("\n" + "=" * 65)
        print("          DATAMATE 2026 — EVALUATION BENCHMARK REPORT")
        print("=" * 65)
        print(f"Total Questions    : {self.total}")
        print(f"Correct (+1)       : {self.correct} ({self.correct/self.total*100:.2f}%)")
        print(f"Incorrect (-1)     : {self.incorrect} ({self.incorrect/self.total*100:.2f}%)")
        print(f"Abstained / Missing: {self.abstained} ({self.abstained/self.total*100:.2f}%)")
        print("-" * 65)
        print(f"Coverage           : {self.coverage:.2f}% (attempted)")
        print(f"Precision on Att.  : {self.precision:.2f}%")
        print(f"PENALIZED ACCURACY : {self.penalized_accuracy:.4f} (Score: {self.correct - self.incorrect} / {self.total})")
        print("-" * 65)
        print("Breakdown by Answer Type:")
        print(f"{'Type':<15} | {'Total':<6} | {'Correct':<8} | {'Incorrect':<9} | {'Abstain':<8} | {'Acc (%)':<8}")
        print("-" * 65)
        for t, st in sorted(self.type_stats.items(), key=lambda x: -x[1]["total"]):
            acc = (st["correct"] / st["total"] * 100) if st["total"] > 0 else 0.0
            print(f"{t:<15} | {st['total']:<6} | {st['correct']:<8} | {st['incorrect']:<9} | {st['abstained']:<8} | {acc:>6.1f}%")
        print("=" * 65)


def evaluate(predictions_path: str, reference_path: str) -> EvaluationReport:
    """Evaluate predictions JSONL file against reference answers JSONL file."""
    # Load reference answers
    refs = {}
    with open(reference_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            refs[obj["id"]] = obj

    # Load predictions
    preds = {}
    with open(predictions_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            preds[obj["id"]] = obj

    report = EvaluationReport(total_questions=len(refs))

    for q_id, ref in refs.items():
        ref_type = ref.get("type")
        ref_ans = ref.get("answer")
        ref_alias = ref.get("alias", [])

        if q_id not in preds:
            report.record(q_id, is_correct=False, is_abstain=True, ref_type=ref_type, pred_type=None, ref_ans=ref_ans, pred_ans=None, error_reason="Missing prediction line")
            continue

        pred = preds[q_id]
        pred_type = pred.get("type")
        pred_ans = pred.get("answer")

        # Check abstain
        if pred_type == "abstain":
            report.record(q_id, is_correct=False, is_abstain=True, ref_type=ref_type, pred_type="abstain", ref_ans=ref_ans, pred_ans=pred_ans, error_reason="Model abstained")
            continue

        # Evaluate correctness
        is_correct = compare_answers(pred_type, pred_ans, ref_type, ref_ans, ref_alias)
        error_msg = "" if is_correct else ("Type mismatch" if pred_type != ref_type else "Value mismatch")
        report.record(q_id, is_correct=is_correct, is_abstain=False, ref_type=ref_type, pred_type=pred_type, ref_ans=ref_ans, pred_ans=pred_ans, error_reason=error_msg)

    return report


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python evaluator.py <predictions.jsonl> <reference_answers.jsonl>")
        sys.exit(1)

    pred_file = sys.argv[1]
    ref_file = sys.argv[2]
    rep = evaluate(pred_file, ref_file)
    rep.print_summary()
