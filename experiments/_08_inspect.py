# -*- coding: utf-8 -*-
"""看 matched / review / no_match 三档样本"""
import pandas as pd
df = pd.read_csv(r"D:\ProjectforMM\出海调研大数据\span_type_escoid_linkage\final_match.csv", encoding="utf-8-sig")

print("=== 各档样本 (每档 15 条) ===\n", flush=True)
for status in ["matched", "review", "no_match"]:
    print(f"--- {status} (n={(df['status']==status).sum()}) ---", flush=True)
    sub = df[df["status"] == status].sort_values("score", ascending=(status!="matched")).head(15)
    for _, r in sub.iterrows():
        print(f"  {r['score']:.3f}  [{r['type']}] {r['span']!r}", flush=True)
        print(f"       → {r['esco_label_en']!r}", flush=True)
    print(flush=True)
