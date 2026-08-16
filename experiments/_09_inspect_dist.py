# -*- coding: utf-8 -*-
"""看 score 分布 + 评估阈值"""
import pandas as pd
import numpy as np

df = pd.read_csv(r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\final_match.csv", encoding="utf-8-sig")

print("=== Score 分布 ===", flush=True)
bins = [0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
labels = ["<0.3", "0.3-0.5", "0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
df["bucket"] = pd.cut(df["score"], bins=bins, labels=labels, right=False, include_lowest=True)
print(df["bucket"].value_counts().sort_index(), flush=True)

print("\n=== 按 type 看 matched 比例 (score>=0.7) ===", flush=True)
for t in ["L","K","S","T"]:
    sub = df[df["type"]==t]
    matched = (sub["score"]>=0.7).sum()
    print(f"  {t}: {matched}/{len(sub)} = {matched/len(sub)*100:.1f}%", flush=True)
