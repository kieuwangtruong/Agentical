import os
import sys
import glob
import json
import sqlite3
import pandas as pd
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"d:\Agentical"
TRAIN_DIR = os.path.join(ROOT, "train")
PUB_DIR = os.path.join(ROOT, "public_test")

def inspect_unanswerable():
    print("=== UNANSWERABLE QUESTIONS ANALYSIS ===")
    q_map = {}
    with open(os.path.join(TRAIN_DIR, "questions.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            q_map[obj["id"]] = obj
            
    unans = []
    with open(os.path.join(TRAIN_DIR, "answers.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj["type"] == "unanswerable":
                unans.append((q_map[obj["id"]], obj))
                
    print(f"Total unanswerable: {len(unans)}")
    print("Sample unanswerable questions (first 10):")
    for q, a in unans[:10]:
        print(f"  [{q['business_id']} | as_of:{q['as_of_date']}]: {q['question']}")

def inspect_biz_121():
    print("\n=== BIZ_121 CHECK ===")
    biz_path = os.path.join(TRAIN_DIR, "data", "biz_121", "DonHang_ChiTiet.xlsx")
    df = pd.read_excel(biz_path)
    print("biz_121 columns:", list(df.columns))
    for col in df.columns:
        if "ngày" in col.lower() or "ngay" in col.lower():
            print(f"Column '{col}' min: {df[col].min()}, max: {df[col].max()}")

def inspect_file_sizes():
    print("\n=== FILE SIZES AND ROW COUNTS (SAMPLE) ===")
    total_size = 0
    all_files = []
    for split in ["train", "public_test"]:
        split_dir = os.path.join(ROOT, split, "data")
        for root, dirs, files in os.walk(split_dir):
            for file in files:
                p = os.path.join(root, file)
                sz = os.path.getsize(p)
                total_size += sz
                all_files.append((sz, p))
    all_files.sort(reverse=True)
    print(f"Total data size: {total_size / (1024*1024):.2f} MB across {len(all_files)} files")
    print("Top 10 largest data files:")
    for sz, p in all_files[:10]:
        rel = os.path.relpath(p, ROOT)
        print(f"  {rel}: {sz / (1024*1024):.2f} MB")

if __name__ == "__main__":
    inspect_unanswerable()
    inspect_biz_121()
    inspect_file_sizes()
